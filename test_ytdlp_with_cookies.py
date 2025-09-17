from yt_dlp import YoutubeDL
from pathlib import Path

URL = "https://www.youtube.com/watch?v=7fJ36M4H_wc"
OUTPUT = Path("Downloads"); OUTPUT.mkdir(exist_ok=True)

browsers = ["chrome", "edge", "brave", "firefox"]
last_err = None
for br in browsers:
    print(f"[YDL] Trying browser cookies from: {br}")
    ydl_opts = {
        'outtmpl': str(OUTPUT / '%(title)s.%(ext)s'),
        'format': 'mp4/best',
        'cookiesfrombrowser': (br,),
        'quiet': False,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(URL, download=True)
            print("[YDL] OK:", info.get('title'))
            break
    except Exception as e:
        last_err = e
        print(f"[YDL] Failed with {br}: {e}")
else:
    print("[YDL] All browsers failed.")
    if last_err:
        raise last_err