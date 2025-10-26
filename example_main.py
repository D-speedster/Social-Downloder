"""
نمونه فایل اصلی ربات با سیستم جدید یوتیوب
"""

from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN

# ایجاد کلاینت
app = Client(
    "youtube_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Import handlers
# سیستم جدید یوتیوب (فقط 2 خط!)
import plugins.youtube_handler
import plugins.youtube_callback

# سایر handlers
import plugins.start
import plugins.universal_downloader
# ... سایر imports

if __name__ == "__main__":
    print("🚀 ربات در حال راه‌اندازی...")
    print("✅ سیستم جدید یوتیوب فعال است")
    app.run()
