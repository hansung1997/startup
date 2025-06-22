import mss
import numpy as np
import cv2

def capture_screen(region=None):
    with mss.mss() as sct:
        try:
            if region:
                x, y, w, h = region
                if w <= 0 or h <= 0:
                    print("[캡처 오류] 잘못된 영역 크기:", region)
                    return None
                monitor = {"top": y, "left": x, "width": w, "height": h}
            else:
                monitor = sct.monitors[1]
            screenshot = sct.grab(monitor)
            img_np = np.array(screenshot)
            if img_np is None or img_np.size == 0:
                print("[캡처 오류] 이미지가 비어 있음:", region)
                return None
            return cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)
        except Exception as e:
            print(f"[캡처 예외] {e}")
            return None
