# app_ui.py (keyboard 모듈 기반 단축키로 복귀)
import tkinter as tk
from tkinter import ttk
from select_area import select_screen_area
from overlay import MainOverlay, SelectOverlay, OverlayBase
from config import save_config, load_layout
import queue
import keyboard  #복원: 전역 단축키 모듈
from PIL import Image, ImageTk
from thread.start_workers import start_workers

def load_resized_icon(path, size=(32, 32)):
    try:
        img = Image.open(path)
        img = img.resize(size, Image.Resampling.LANCZOS)  # ✅ 최신 방식
        return ImageTk.PhotoImage(img)
    except Exception as e:
        print(f"⚠️ 아이콘 로딩 실패: {path}, {e}")
        return None

class OCRTranslatorApp:

    ocr_delay = 1.0  # 초 단위

    #UI 초기화, 핫키 등록, 레이아웃 로딩
    def __init__(self, root):
        self.root = root #tkinter 메인 창 객체
        self.root.title("OCR Translator")
        self.root.geometry("500x400")

        config = load_layout()
        self.toggle_key = config.get("toggle_key", "f8") #오버레이 숨김/표시 단축키 (기본: f8)
        self.region = config.get("region", None) #	OCR 영역 좌표

        self.main_overlay = MainOverlay(font_size=14) #실시간 번역을 보여주는 메인 오버레이
        self.select_overlays = [] #선택지 번역용 서브 오버레이 리스트

        self.api_var = tk.StringVar(value="google") #번역 API 선택 (google, deepl, local) 기본값은 google
        self.font_size = tk.IntVar(value=14) #번역 텍스트 폰트 크기 변수

        self.translation_queue = queue.Queue() #OCR → 번역 → 오버레이로 전달될 메시지 큐
        self.is_translating = False #실시간 번역 여부 상태 플래그
        self.ocr_thread = None #백그라운드 작업자 스레드1 (실시간 OCR)
        self.translate_thread = None #백그라운드 작업자 스레드2 (번역 실행)

        self.build_ui() #UI 초기화, 핫키 등록, 레이아웃 로딩

        # keyboard 모듈 충돌 회피 처리
        try:
            keyboard.clear_all_hotkeys()
        except AttributeError:
            print("⚠️ keyboard 모듈 내부 핫키 초기화 실패. 무시하고 계속 진행.")

        keyboard.add_hotkey(self.toggle_key, OverlayBase.toggle_all_overlays)
        self.load_saved_layout()

    #Tkinter 위젯들(버튼, 콤보박스 등) 구성
    def build_ui(self):

        # 아이콘 로딩 (32x32 또는 24x24)
        self.translate_icon = load_resized_icon("icons/translate.png", size=(32, 32))
        self.region_icon = load_resized_icon("icons/crop.png", size=(32, 32))
        self.hotkey_icon = load_resized_icon("icons/keyboard.png", size=(24, 24))

        # 툴바 프레임 (상단 핵심 버튼)
        toolbar = tk.Frame(self.root)
        toolbar.pack(fill="x", padx=5, pady=5)

        # 번역 실행 버튼 (저장 필요)
        self.translation_btn = tk.Button(toolbar, text="번역 실행", image=self.translate_icon, compound="left",
                                         command=self.run_translation)
        self.translation_btn.pack(side="left", padx=5)

        # 영역 선택 버튼
        tk.Button(toolbar, text="영역 선택", image=self.region_icon, compound="left",
                  command=self.select_area).pack(side="left", padx=5)

        self.key_setting_btn = tk.Button(toolbar, image=self.hotkey_icon, command=self.wait_for_key)
        self.key_setting_btn.pack(side="right", padx=5)

        # 설정 영역
        tk.Label(self.root, text="번역 API 선택").pack()
        api_combo = ttk.Combobox(self.root, textvariable=self.api_var, values=["google", "deepl", "local"])
        api_combo.pack(pady=5)

        # ✅ 콤보박스 선택 시 바로 config 저장
        def on_api_change(event):
            self.save_layout()  # 현재 self.api_var 값이 config에 저장됨
            print(f"✅ 번역 API 변경됨: {self.api_var.get()} → 저장 완료")

        api_combo.bind("<<ComboboxSelected>>", on_api_change)

        tk.Label(self.root, text="글자 크기 조정").pack()
        tk.Scale(self.root, from_=10, to=36, orient="horizontal", variable=self.font_size,
                 command=self.update_font_size).pack(pady=5)

        # 기능 버튼들
        tk.Button(self.root, text="실시간 번역 내용 초기화", command=self.main_overlay.clear_text).pack(pady=5)
        tk.Button(self.root, text="실시간 오버레이 숨김/표시", command=self.main_overlay.toggle_visibility).pack(pady=5)

        tk.Label(self.root, text="").pack(pady=7)

        tk.Button(self.root, text="레이아웃 저장", command=self.save_layout).pack(pady=5)
        tk.Button(self.root, text="선택지 번역 오버레이 추가", command=self.create_select_overlay).pack(pady=5)

        tk.Label(self.root, text="").pack(pady=7)

    def run_translation(self):
        if not self.region:
            print("먼저 번역 영역을 선택해주세요.")
            return

        # 번역 중이면 → 종료 처리
        if self.is_translating:
            print("실시간 번역 중지 요청됨")
            self.is_translating = False
            self.translation_btn.config(text="실시간 번역 실행")

            # 기존 스레드 종료 대기
            if self.ocr_thread and self.ocr_thread.is_alive():
                self.ocr_thread.join(timeout=1)
            if self.translate_thread and self.translate_thread.is_alive():
                self.translate_thread.join(timeout=1)

            self.ocr_thread = None
            self.translate_thread = None
            return

        # 번역 시작
        print("▶실시간 번역 시작")
        self.is_translating = True
        self.translation_btn.config(text="실시간 번역 중")

        # OCR 중복 제거: 이전 텍스트 초기화
        from ocr import text_buffer
        text_buffer["text"] = None
        text_buffer["start_time"] = 0

        def is_translating_flag():
            return self.is_translating

        self.ocr_thread, self.translate_thread = start_workers(
            region=self.region,
            translation_queue=self.translation_queue,
            update_callback=self.main_overlay.update_text,
            is_translating_flag=is_translating_flag,
        )

    def select_area(self):
        def after_select(region):
            # 기존 번역 중이면 먼저 종료
            if self.is_translating:
                print("영역 재선택 중 → 기존 실시간 번역 종료")
                self.is_translating = False
                self.translation_btn.config(text="실시간 번역 실행")

                # 기존 스레드 종료 대기
                if self.ocr_thread and self.ocr_thread.is_alive():
                    self.ocr_thread.join(timeout=1)
                if self.translate_thread and self.translate_thread.is_alive():
                    self.translate_thread.join(timeout=1)

                self.ocr_thread = None
                self.translate_thread = None

            # 새 영역 반영
            self.region = region
            print(f"선택 완료: {self.region}")

        select_screen_area(after_select)

    #오버레이 글자 크기 실시간 반영
    def update_font_size(self, event=None):
        self.main_overlay.update_font_size(self.font_size.get())

    #UI/오버레이 위치 및 설정 값 저장 ->config.json으로 저장
    def save_layout(self):
        data = {
            "region": self.region,
            "font_size": self.font_size.get(),
            "api": self.api_var.get(),
            "toggle_key": self.toggle_key,
            "overlays": [
                {
                    "region": overlay.region,
                    "font_size": overlay.font_size,
                    "x": overlay.root.winfo_x(),
                    "y": overlay.root.winfo_y(),
                    "width": overlay.root.winfo_width(),
                    "height": overlay.root.winfo_height(),
                }
                for overlay in self.select_overlays
            ],
            "main_overlay_position": {
                "x": self.main_overlay.root.winfo_x(),
                "y": self.main_overlay.root.winfo_y(),
                "width": self.main_overlay.root.winfo_width(),
                "height": self.main_overlay.root.winfo_height()
            }
        }
        save_config(data)
        print("✅ 레이아웃 및 설정 + 위치 저장 완료")

    #UI/오버레이 위치 및 설정 값 복원 <- config.json에서 가져오기
    def load_saved_layout(self):
        config = load_layout()

        if "region" in config:
            self.region = config["region"]
        if "font_size" in config:
            self.font_size.set(config["font_size"])
            self.main_overlay.update_font_size(self.font_size.get())
        if "api" in config:
            self.api_var.set(config["api"])

        for overlay_data in config.get("overlays", []):
            overlay = SelectOverlay(
                font_size=overlay_data.get("font_size", 14),
                region=overlay_data.get("region"),
                app=self
            )
            if "x" in overlay_data and "y" in overlay_data:
                w = overlay_data.get("width", 600)
                h = overlay_data.get("height", 120)
                overlay.root.geometry(f"{w}x{h}+{overlay_data['x']}+{overlay_data['y']}")
            self.select_overlays.append(overlay)

        if "main_overlay_position" in config:
            pos = config["main_overlay_position"]
            w = pos.get("width", 600)
            h = pos.get("height", 120)
            self.main_overlay.root.geometry(f"{w}x{h}+{pos['x']}+{pos['y']}")

    #선택지 오버레이 생성 및 리스트에 추가
    def create_select_overlay(self):
        print("선택지 전용 오버레이 생성")
        overlay = SelectOverlay(font_size=self.font_size.get(), region=self.region, app=self)
        self.select_overlays.append(overlay)

    #모든 선택지 오버레이 숨김/표시 토글
    def toggle_select_overlay_visibility(self, event=None):
        if not self.select_overlays:
            print("선택지 전용 오버레이가 없습니다.")
            return

        visible_count = sum(overlay.is_visible for overlay in self.select_overlays)

        if visible_count > 0:
            print("단축키 → 모든 선택지 오버레이 숨김 처리")
            for overlay in self.select_overlays:
                if overlay.is_visible:
                    overlay.toggle_visibility()
        else:
            print("단축키 → 모든 선택지 오버레이 표시 처리")
            for overlay in self.select_overlays:
                overlay.toggle_visibility()

    #사용자 입력 기반 단축키 변경 기능
    def wait_for_key(self):
        print("🔧 새로운 단축키를 입력하세요...")

        self.key_setting_btn.config(text="입력 대기 중...")

        def wait_and_set():
            event = keyboard.read_event()  # ✅ 딱 1번만 키 입력 대기
            if event.event_type == "down":  # 키 누른 순간만 반응
                new_key = event.name.lower()
                print(f"✅ 새 단축키: {new_key}")

                keyboard.clear_all_hotkeys()

                self.toggle_key = new_key
                keyboard.add_hotkey(self.toggle_key, OverlayBase.toggle_all_overlays)
                self.key_setting_btn.config(text=f"단축키 변경 (현재: {self.toggle_key.upper()})")

                self.save_layout()

        import threading
        threading.Thread(target=wait_and_set, daemon=True).start()  # 💬 별도 스레드로 키 입력 대기
