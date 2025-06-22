# overlay.py (keyboard 전역 단축키 방식과 호환, ESC 바인딩 없음)
import tkinter as tk
import screeninfo


class OverlayBase:
    instances = []

    def __init__(self, font_size=14, region=None):
        OverlayBase.instances.append(self)

        self.region = region if region else (100, 100, 400, 200)
        self.font_size = font_size
        self.is_visible = True
        self.offset_x = 0
        self.offset_y = 0

        self.root = tk.Toplevel()
        self.root.title("번역 결과")
        self.root.geometry(self._region_geometry())
        self.root.configure(bg='black')
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.75)
        self.root.overrideredirect(True)
        self.root.resizable(True, True)
        self.root.bind("<Configure>", self.resize_wraplength)

        self.label = tk.Label(
            self.root,
            text="선택지 영역 번역 준비 중...",
            fg="white",
            bg="black",
            font=("Arial", self.font_size),
            wraplength=self.region[2] - 20,
            justify="left"
        )
        self.label.pack(expand=True, fill="both", padx=10, pady=10)

        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)

        self.resize_grip = tk.Label(self.root, bg="gray", cursor="bottom_right_corner")
        self.resize_grip.place(relx=1.0, rely=1.0, anchor="se", width=20, height=20)
        self.resize_grip.bind("<Button-1>", self.start_resize)
        self.resize_grip.bind("<B1-Motion>", self.do_resize)

    def _region_geometry(self):
        screen = screeninfo.get_monitors()[0]
        width, height = 600, 120
        x = (screen.width - width) // 2
        y = screen.height - height - 60
        return f"{width}x{height}+{x}+{y}"

    def start_move(self, event):
        self.offset_x = event.x
        self.offset_y = event.y

    def do_move(self, event):
        x = self.root.winfo_x() + event.x - self.offset_x
        y = self.root.winfo_y() + event.y - self.offset_y
        self.root.geometry(f"+{x}+{y}")

    def update_text(self, new_text):
        self.label.config(text=new_text)

    def update_font_size(self, size):
        self.font_size = size
        self.label.config(font=("Arial", self.font_size))

    def clear_text(self):
        self.label.config(text="")

    def toggle_visibility(self):
        if self.is_visible:
            self.root.withdraw()
        else:
            self.root.deiconify()
        self.is_visible = not self.is_visible

    def resize_wraplength(self, event):
        self.label.config(wraplength=self.root.winfo_width() - 20)

    def start_resize(self, event):
        self.fixed_x = self.root.winfo_x()
        self.fixed_y = self.root.winfo_y()

    def do_resize(self, event):
        mouse_x = self.root.winfo_pointerx()
        mouse_y = self.root.winfo_pointery()

        new_width = max(mouse_x - self.fixed_x, 300)
        new_height = max(mouse_y - self.fixed_y, 120)

        screen = screeninfo.get_monitors()[0]
        max_width = screen.width - self.fixed_x
        max_height = screen.height - self.fixed_y

        new_width = min(new_width, max_width)
        new_height = min(new_height, max_height)

        self.root.geometry(f"{new_width}x{new_height}+{self.fixed_x}+{self.fixed_y}")

    @staticmethod
    def toggle_all_overlays(event=None):
        print("단축키로 선택지 오버레이 토글")
        for overlay in OverlayBase.instances:
            if isinstance(overlay, SelectOverlay):
                overlay.toggle_visibility()


class MainOverlay(OverlayBase):
    def __init__(self, font_size=14, region=None):
        super().__init__(font_size, region)


class SelectOverlay(OverlayBase):
    def __init__(self, font_size=14, region=None, app=None):
        super().__init__(font_size, region)
        self.app = app

        self.buttons_frame = tk.Frame(self.root, bg='black')
        self.buttons_frame.pack(side="bottom", pady=5)

        self.toggle_setting_btn = tk.Button(self.root, text="설정 활성화", command=self.toggle_setting_buttons)
        self.toggle_setting_btn.pack(side="bottom", pady=2)

        self.buttons = []
        self.create_buttons()
        self.setting_buttons_visible = False

    def create_buttons(self):
        delete_btn = tk.Button(self.buttons_frame, text="오버레이 삭제", command=self.delete_overlay)
        select_area_btn = tk.Button(self.buttons_frame, text="영역 설정", command=self.select_new_area)
        translate_btn = tk.Button(self.buttons_frame, text="선택지 번역", command=self.manual_translate)
        add_overlay_btn = tk.Button(self.buttons_frame, text="오버레이 추가", command=self.add_new_overlay)

        for btn in [delete_btn, select_area_btn, translate_btn, add_overlay_btn]:
            self.buttons.append(btn)

    def toggle_setting_buttons(self):
        if self.setting_buttons_visible:
            for btn in self.buttons:
                btn.grid_forget()
            self.setting_buttons_visible = False
        else:
            for idx, btn in enumerate(self.buttons):
                btn.grid(row=0, column=idx, padx=5)
            self.setting_buttons_visible = True

    def delete_overlay(self):
        if len(self.app.select_overlays) <= 1:
            print("❌ 마지막 오버레이는 삭제할 수 없습니다.")
            return
        print("오버레이 삭제")
        self.app.select_overlays.remove(self)
        OverlayBase.instances.remove(self)  # ✅ 여기서도 제거
        self.root.destroy()

    def select_new_area(self):
        from select_area import select_screen_area

        def after_select(new_region):
            self.region = new_region
            print(f"[선택지 오버레이] 새 영역 설정 완료: {self.region}")

        select_screen_area(after_select)

    def manual_translate(self):
        from capture import capture_screen
        from ocr import extract_text
        from translator import translate_text

        img = capture_screen(region=self.region)
        if img is None:
            self.update_text("화면 캡처 실패: 이미지가 없습니다.")
            return

        text = extract_text(img)
        if not text:
            self.update_text("OCR 실패: 텍스트를 인식하지 못했습니다.")
            return

        try:
            translated = translate_text(text)
            self.update_text(translated)
        except Exception as e:
            self.update_text(f"번역 중 오류 발생: {e}")

    def add_new_overlay(self):
        print("새로운 선택지 오버레이 추가")
        self.app.create_select_overlay()
