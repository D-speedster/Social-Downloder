#!/usr/bin/env python3
import subprocess

# لینک ویدیو
video_url = "https://www.youtube.com/watch?v=SpktCnwLvIE"

# پراکسی
proxy = "socks5h://127.0.0.1:1082"

# فایل کوکی
cookies_file = "cookie_youtube.txt"

print(f"🔍 Downloading {video_url} using proxy {proxy} and cookies {cookies_file}")

# اجرای yt-dlp مثل CLI
cmd = [
    "yt-dlp",
    "--proxy", proxy,
    "--cookies", cookies_file,
    video_url
]

# اجرای دستور و نمایش خروجی مستقیم در ترمینال
result = subprocess.run(cmd)

# بررسی نتیجه
if result.returncode == 0:
    print("✅ Download completed successfully!")
else:
    print("❌ Download failed. Check proxy and cookies.")
