from instaloader import Instaloader, Post
from urllib.parse import urlparse
from pathlib import Path

URL = "https://www.instagram.com/reel/DJrEhnhikBH/?igsh=MTNnNmM5N2xvczRyYw=="
print("[IG] Initializing Instaloader...")
L = Instaloader(dirname_pattern="Downloads/instagram", download_video_thumbnails=False, save_metadata=False)

def extract_shortcode(url: str) -> str:
    p = urlparse(url)
    parts = [x for x in p.path.split('/') if x]
    # Expect like ['reel', '<shortcode>']
    return parts[1] if len(parts) >= 2 else ""

shortcode = extract_shortcode(URL)
if not shortcode:
    raise SystemExit("[IG] Could not parse shortcode from URL")

print(f"[IG] Shortcode: {shortcode}")
try:
    post = Post.from_shortcode(L.context, shortcode)
    Path("Downloads/instagram").mkdir(parents=True, exist_ok=True)
    L.download_post(post, target="Downloads/instagram")
    print("[IG] Download complete.")
except Exception as e:
    print("[IG] Download failed:", e)
    raise