from overlay import OverlayBase
import atexit
import keyboard
from tkinter import Tk
from app_ui import OCRTranslatorApp
from cache_manager import load_all_caches, save_all_caches

def main():
    global root
    root = Tk() #tk()로 gui 창 생성
    app = OCRTranslatorApp(root) #앱 로드

    load_all_caches() #캐시 데이터 로딩
    atexit.register(save_all_caches)

    def on_close(): #메인 창 종료 시 호출
        save_all_caches()
        root.destroy() # 캐시 저장 후 root.destroy()로 창 종료

    root.protocol("WM_DELETE_WINDOW", on_close)
    listen_esc_key()
    root.mainloop()

def listen_esc_key():#esc 키 입력 시 오버레이 전체 토글
    keyboard.add_hotkey('esc', OverlayBase.toggle_all_overlays)

if __name__ == '__main__':
    main()
