import threading
import time
import queue
from capture import capture_screen
from ocr import extract_text
from translator import translate_text

def start_workers(region, translation_queue, update_callback, is_translating_flag, delay=1.0):
    def ocr_worker():
        while is_translating_flag():
            try:
                img = capture_screen(region=region)
                text = extract_text(img, delay=delay)  # ✅ 전달
                if text:  # None 방지
                    translation_queue.put(text)
                time.sleep(0.2)  # OCR 실행 주기 (짧게 유지)
            except Exception as e:
                print(f"[OCR 오류] {e}")

    def translate_worker():
        while is_translating_flag():
            try:
                text = translation_queue.get(timeout=1)
                translated = translate_text(text)
                update_callback(translated)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[번역 오류] {e}")

    ocr_thread = threading.Thread(target=ocr_worker, daemon=True)
    translate_thread = threading.Thread(target=translate_worker, daemon=True)
    ocr_thread.start()
    translate_thread.start()
    return ocr_thread, translate_thread