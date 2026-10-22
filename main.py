import os
import urllib.request

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# ambil dari environment variable fly.io
TIKTOK_USERNAME   = os.environ.get("TIKTOK_USERNAME", "")
TIKTOK_PASS    = os.environ.get("TIKTOK_PASS", "")
PHOTO_URL      = os.environ.get("PHOTO_URL", "")

BASE_DIR     = "/app/data"
OUTPUT_DIR   = f"{BASE_DIR}/variants"
AUDIO_DIR    = f"{BASE_DIR}/audio"
READY_DIR    = f"{BASE_DIR}/ready"
LOG_FILE     = f"{BASE_DIR}/upload_log.txt"
SOURCE_PHOTO = f"{BASE_DIR}/foto.jpg"

UPLOAD_TIMES = ["07:00", "12:00", "20:00"]

CAPTIONS = [
    "caption 1 #fyp #viral #trend",
    "caption 2 #masukberanda #foryoupage",
    "caption 3 #viralvideo #viral #fyp",
]

def download_source_photo():
    os.makedirs(BASE_DIR, exist_ok=True)
    if PHOTO_URL and not os.path.exists(SOURCE_PHOTO):
        print(f"[PHOTO] download dari {PHOTO_URL}")
        urllib.request.urlretrieve(PHOTO_URL, SOURCE_PHOTO)
        print("[PHOTO] selesai")

if __name__ == "__main__":
    download_source_photo()
    start_scheduler()
