from yt_dlp import YoutubeDL
from pathlib import Path

url = "https://www.youtube.com/watch?v=LSH2W6Aw-7A"
print("[YDL] Initializing (Android client emulation)...")
output_dir = Path("Downloads")
output_dir.mkdir(exist_ok=True)
opts = {
    'outtmpl': str(output_dir / '%(title)s.%(ext)s'),
    'format': 'bv*+ba/best',
    'merge_output_format': 'mp4',
    'quiet': False,
    'noplaylist': True,
    'geo_bypass': True,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 12; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Mobile Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    },
    'extractor_args': {
        'youtube': {
            'player_client': ['android']
        }
    }
}
with YoutubeDL(opts) as ydl:
    info = ydl.extract_info(url, download=True)
    print("[YDL] Downloaded:", info.get('title'), info.get('ext'))