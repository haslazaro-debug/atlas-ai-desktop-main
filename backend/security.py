import cv2
import threading
import time
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_photo_alert(image_bytes: bytes, caption: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        response = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
            files={"photo": ("alert.jpg", image_bytes, "image/jpeg")},
            timeout=15,
        )
        response.raise_for_status()
        return True
    except Exception as exc:
        print(f"[TELEGRAM ALERT ERROR] {exc}")
        return False

class SecuritySentinel:
    def __init__(self):
        self.is_armed = False
        self.thread = None
        self.cooldown_seconds = 45
        self.last_alert_time = 0
        self.stop_event = threading.Event()

    def arm(self, cooldown_seconds=45):
        if self.is_armed:
            return
        self.cooldown_seconds = cooldown_seconds
        self.is_armed = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.thread.start()
        print("[SENTINEL] Armed.")

    def disarm(self):
        self.is_armed = False
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)
        print("[SENTINEL] Disarmed.")

    def status(self):
        return "ARMED" if self.is_armed else "DISARMED"

    def snapshot_once(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[SENTINEL] Cannot open camera for snapshot.")
            return None
        ret, frame = cap.read()
        cap.release()
        if ret:
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                return buffer.tobytes()
        return None

    def shutdown(self):
        self.disarm()

    def _detection_loop(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[SENTINEL] Cannot open camera.")
            self.is_armed = False
            return

        fgbg = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=False)

        # Allow camera to warm up and bg subtractor to initialize
        for _ in range(30):
            ret, frame = cap.read()
            if not ret:
                break
            fgbg.apply(frame)
            time.sleep(0.05)

        while not self.stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                time.sleep(1)
                continue

            fgmask = fgbg.apply(frame)
            
            # Count non-zero pixels
            motion_pixels = cv2.countNonZero(fgmask)
            
            # Simple threshold for motion
            if motion_pixels > 5000:
                current_time = time.time()
                if current_time - self.last_alert_time > self.cooldown_seconds:
                    print("[SENTINEL] Motion detected! Sending alert.")
                    ret, buffer = cv2.imencode('.jpg', frame)
                    if ret:
                        send_photo_alert(buffer.tobytes(), "🚨 ATLAS SENTINEL: Motion detected!")
                    self.last_alert_time = current_time

            time.sleep(0.2) # ~5 FPS check rate

        cap.release()

sentinel = SecuritySentinel()
