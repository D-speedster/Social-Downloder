from yt_dlp import YoutubeDL
from pathlib import Path

url = "https://www.youtube.com/watch?v=7fJ36M4H_wc"
print("[YDL] Initializing...")
output_dir = Path("Downloads")
output_dir.mkdir(exist_ok=True)
opts = {
    'outtmpl': str(output_dir / '%(title)s.%(ext)s'),
    'format': 'mp4/bestaudio/best',
    'quiet': False,
}
with YoutubeDL(opts) as ydl:
    info = ydl.extract_info(url, download=True)
    print("[YDL] Downloaded:", info.get('title'), info.get('ext'))