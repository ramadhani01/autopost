# main.py — TikTok Auto Poster
# login pake username, upload 3x sehari jam FYP

import os
import sys
import time
import random
import subprocess
import schedule
import requests
import numpy as np
import urllib.request
from PIL import Image, ImageEnhance
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# ============================================================
# KONFIGURASI
# ============================================================

TIKTOK_USERNAME = os.environ.get("TIKTOK_USERNAME", "")
TIKTOK_PASS     = os.environ.get("TIKTOK_PASS", "")
PHOTO_URL       = os.environ.get("PHOTO_URL", "")

BASE_DIR     = "/app/data"
OUTPUT_DIR   = f"{BASE_DIR}/variants"
AUDIO_DIR    = f"{BASE_DIR}/audio"
READY_DIR    = f"{BASE_DIR}/ready"
LOG_FILE     = f"{BASE_DIR}/upload_log.txt"
SOURCE_PHOTO = f"{BASE_DIR}/foto.jpg"

UPLOAD_TIMES   = ["07:00", "12:00", "20:00"]
SLIDE_DURATION = 10

CAPTIONS = [
    "caption 1 #fyp #viral #trend",
    "caption 2 #masukberanda #adekvskakak",
    "caption 3 #adekkakak #viral #fyp",
    "caption 4 #fyp #terbaru #trend",
    "caption 5 #viral #foryou #masukberanda",
    "caption 6 #tiktok #fyp #viralvideo",
]

upload_counter = [0]

# ============================================================
# SETUP DIREKTORI
# ============================================================

for d in [BASE_DIR, OUTPUT_DIR, AUDIO_DIR, READY_DIR]:
    os.makedirs(d, exist_ok=True)

# ============================================================
# DOWNLOAD FOTO SUMBER
# ============================================================

def download_source_photo():
    if not PHOTO_URL:
        print("[PHOTO] PHOTO_URL kosong — pastikan sudah di-set di secrets")
        return False
    if os.path.exists(SOURCE_PHOTO):
        print(f"[PHOTO] sudah ada: {SOURCE_PHOTO}")
        return True
    try:
        print(f"[PHOTO] download dari {PHOTO_URL}")
        urllib.request.urlretrieve(PHOTO_URL, SOURCE_PHOTO)
        print("[PHOTO] selesai")
        return True
    except Exception as e:
        print(f"[PHOTO] gagal download: {e}")
        return False

# ============================================================
# GENERATE VARIANT FOTO
# ============================================================

def generate_photo_variant(source, output_path):
    img = Image.open(source).convert("RGB")
    w, h = img.size

    mx = random.randint(5, 18)
    my = random.randint(5, 18)
    img = img.crop((mx, my, w - mx, h - my))
    img = img.resize((w, h), Image.LANCZOS)

    img = ImageEnhance.Brightness(img).enhance(random.uniform(0.96, 1.04))
    img = ImageEnhance.Contrast(img).enhance(random.uniform(0.97, 1.03))
    img = ImageEnhance.Color(img).enhance(random.uniform(0.97, 1.05))
    img = ImageEnhance.Sharpness(img).enhance(random.uniform(0.9, 1.1))

    arr  = np.array(img, dtype=np.int16)
    noise = np.random.randint(-4, 4, arr.shape, dtype=np.int16)
    arr  = np.clip(arr + noise, 0, 255).astype(np.uint8)
    img  = Image.fromarray(arr)

    img = img.resize((1080, 1920), Image.LANCZOS)
    img.save(output_path, "JPEG", quality=random.randint(87, 95))
    print(f"[PHOTO] variant → {output_path}")
    return output_path

# ============================================================
# SCRAPE AUDIO TRENDING
# ============================================================

def scrape_trending_audio():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.tiktok.com/"
    }

    try:
        url = "https://www.tiktok.com/api/music/trending/?count=20&aid=1988"
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()

        for item in data.get("musicList", []):
            play_url = item.get("playUrl", "")
            title    = item.get("title", f"audio_{int(time.time())}")
            if not play_url:
                continue

            safe  = "".join(c for c in title if c.isalnum() or c in " _-")[:40]
            out   = os.path.join(AUDIO_DIR, f"{safe}.mp3")

            if os.path.exists(out):
                print(f"[AUDIO] cache: {out}")
                return out

            r = requests.get(play_url, headers=headers, timeout=15)
            if r.status_code == 200:
                with open(out, "wb") as f:
                    f.write(r.content)
                print(f"[AUDIO] downloaded: {out}")
                return out

    except Exception as e:
        print(f"[AUDIO] scrape gagal: {e}")

    # fallback audio lokal
    local = list(Path(AUDIO_DIR).glob("*.mp3"))
    if local:
        pick = random.choice(local)
        print(f"[AUDIO] fallback: {pick}")
        return str(pick)

    print("[AUDIO] tidak ada audio")
    return None

# ============================================================
# MERGE FOTO + AUDIO → VIDEO
# ============================================================

def merge_photo_audio(photo_path, audio_path, output_path, duration=10):
    if audio_path and os.path.exists(audio_path):
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", photo_path,
            "-i", audio_path,
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-t", str(duration),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output_path
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", photo_path,
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-t", str(duration),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output_path
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[MERGE ERROR] {result.stderr[-300:]}")
        return False

    print(f"[MERGE] video siap → {output_path}")
    return True

# ============================================================
# LOGIN TIKTOK
# ============================================================

def login_tiktok(page):
    print("[LOGIN] mencoba login...")

    # tunggu halaman load
    time.sleep(3)

    # coba klik tab "Use phone / email / username"
    try:
        btn = page.locator('text=Use phone / email / username').first
        if btn:
            btn.click()
            time.sleep(2)
    except:
        pass

    # coba klik tab "Email / Username" kalau ada pilihan
    try:
        tab = page.locator('text=Email atau nama pengguna').first
        if tab:
            tab.click()
            time.sleep(1)
    except:
        pass

    try:
        tab = page.locator('text=Email or username').first
        if tab:
            tab.click()
            time.sleep(1)
    except:
        pass

    # isi username
    try:
        page.fill('input[name="username"]', TIKTOK_USERNAME)
        time.sleep(1)
        page.fill('input[type="password"]', TIKTOK_PASS)
        time.sleep(1)
        page.click('button[type="submit"]')
        time.sleep(8)
        print("[LOGIN] berhasil")
        return True
    except Exception as e:
        print(f"[LOGIN] gagal: {e}")
        return False

# ============================================================
# UPLOAD KE TIKTOK
# ============================================================

def upload_to_tiktok(video_path, caption):
    from playwright.sync_api import sync_playwright

    print(f"[UPLOAD] mulai: {video_path}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )

        ctx  = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
        page = ctx.new_page()

        # load cookies kalau ada
        cookie_file = f"{BASE_DIR}/cookies.json"
        if os.path.exists(cookie_file):
            import json
            with open(cookie_file) as f:
                cookies = json.load(f)
            ctx.add_cookies(cookies)
            print("[COOKIE] cookies dimuat")

        try:
            page.goto("https://www.tiktok.com/tiktokstudio/upload", timeout=30000)
            time.sleep(4)

            # cek apakah perlu login
            if "login" in page.url.lower() or "signup" in page.url.lower():
                page.goto("https://www.tiktok.com/login", timeout=30000)
                login_tiktok(page)

                # save cookies setelah login
                import json
                cookies = ctx.cookies()
                with open(cookie_file, "w") as f:
                    json.dump(cookies, f)
                print("[COOKIE] cookies disimpan")

                # balik ke upload
                page.goto("https://www.tiktok.com/tiktokstudio/upload", timeout=30000)
                time.sleep(4)

            # upload file
            file_input = page.locator('input[type="file"]').first
            file_input.set_input_files(os.path.abspath(video_path))
            print("[UPLOAD] file dipilih, processing...")
            time.sleep(20)

            # isi caption
            try:
                cap_box = page.locator('[data-e2e="caption-input"]').first
                cap_box.click()
                time.sleep(1)
                cap_box.fill(caption)
                time.sleep(2)
            except:
                try:
                    cap_box = page.locator('div[contenteditable="true"]').first
                    cap_box.click()
                    time.sleep(1)
                    cap_box.type(caption)
                    time.sleep(2)
                except Exception as e:
                    print(f"[CAPTION] gagal isi caption: {e}")

            # klik post
            try:
                page.click('button:has-text("Post")', timeout=10000)
            except:
                try:
                    page.click('button:has-text("Posting")', timeout=5000)
                except:
                    page.click('button[data-e2e="post-button"]', timeout=5000)

            time.sleep(5)
            print(f"[UPLOAD] sukses: {caption}")
            log_upload(video_path, caption, "SUCCESS")

        except Exception as e:
            print(f"[UPLOAD ERROR] {e}")
            log_upload(video_path, caption, f"FAILED: {e}")

            # screenshot buat debug
            try:
                ss = f"{BASE_DIR}/error_{int(time.time())}.png"
                page.screenshot(path=ss)
                print(f"[DEBUG] screenshot: {ss}")
            except:
                pass

        finally:
            browser.close()

# ============================================================
# LOG
# ============================================================

def log_upload(path, caption, status):
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {status} | {path} | {caption}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    print(f"[LOG] {line.strip()}")

# ============================================================
# CLEANUP FILE LAMA
# ============================================================

def cleanup_old_files(folder, days=3):
    cutoff = time.time() - (days * 86400)
    for f in Path(folder).glob("*"):
        if f.is_file() and f.stat().st_mtime < cutoff:
            f.unlink()
            print(f"[CLEANUP] hapus: {f.name}")

# ============================================================
# JOB UTAMA
# ============================================================

def run_upload_job():
    print(f"\n[JOB] mulai job: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if not os.path.exists(SOURCE_PHOTO):
        ok = download_source_photo()
        if not ok:
            print("[JOB] foto tidak ada, skip")
            return

    ts = int(time.time())

    # generate variant
    photo_variant = os.path.join(OUTPUT_DIR, f"photo_{ts}.jpg")
    generate_photo_variant(SOURCE_PHOTO, photo_variant)

    # ambil audio
    audio = scrape_trending_audio()

    # merge
    video_out = os.path.join(READY_DIR, f"video_{ts}.mp4")
    ok = merge_photo_audio(photo_variant, audio, video_out, SLIDE_DURATION)

    if not ok:
        print("[JOB] merge gagal, skip upload")
        return

    # caption
    cap = CAPTIONS[upload_counter[0] % len(CAPTIONS)]
    upload_counter[0] += 1

    # upload
    upload_to_tiktok(video_out, cap)

    # cleanup
    cleanup_old_files(READY_DIR)
    cleanup_old_files(OUTPUT_DIR)

    print(f"[JOB] selesai: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# ============================================================
# SCHEDULER
# ============================================================

def start_scheduler():
    print("=" * 50)
    print("[SCHEDULER] TikTok Auto Poster aktif")
    print(f"[SCHEDULER] upload jam: {', '.join(UPLOAD_TIMES)} WIB")
    print(f"[SCHEDULER] username: {TIKTOK_USERNAME}")
    print("=" * 50)

    for jam in UPLOAD_TIMES:
        schedule.every().day.at(jam).do(run_upload_job)

    while True:
        schedule.run_pending()
        time.sleep(30)

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    # validasi env
    if not TIKTOK_USERNAME:
        print("[ERROR] TIKTOK_USERNAME belum di-set di secrets")
        sys.exit(1)
    if not TIKTOK_PASS:
        print("[ERROR] TIKTOK_PASS belum di-set di secrets")
        sys.exit(1)

    # download foto pertama kali
    download_source_photo()

    if "--test" in sys.argv:
        print("[TEST] jalanin 1x sekarang...")
        run_upload_job()
    else:
        start_scheduler()
