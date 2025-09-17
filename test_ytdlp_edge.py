from yt_dlp import YoutubeDL
from pathlib import Path

URL = "https://www.youtube.com/watch?v=7fJ36M4H_wc"
OUTPUT = Path("Downloads"); OUTPUT.mkdir(exist_ok=True)

for br in ("edge", "chrome"):
    print(f"[YDL] Trying cookies from {br}...")
    opts = {
        'outtmpl': str(OUTPUT / '%(title)s.%(ext)s'),
        'format': 'mp4/best',
        'cookiesfrombrowser': (br,),
        'quiet': False,
    }
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(URL, download=True)
            print("[YDL] OK:", info.get('title'))
            break
    except Exception as e:
        print(f"[YDL] Failed with {br}: {e}")
else:
    raise SystemExit("[YDL] Could not download with Edge or Chrome cookies. Please login to YouTube in Edge/Chrome and retry.")