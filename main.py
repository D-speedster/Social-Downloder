# ===================================================================
# در اولین خطوط فایل اصلی بات (قبل از همه چیز) این را اضافه کنید
# ===================================================================
import plugins.youtube_handler
import plugins.youtube_callback
import os
import sys

# CRITICAL: پاکسازی کامل تمام متغیرهای proxy
print("=" * 70)
print("Cleaning proxy environment variables...")
print("=" * 70)

# لیست کامل متغیرهای proxy
proxy_vars = [
    'HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy',
    'ALL_PROXY', 'all_proxy', 'PROXY', 'proxy',
    'NO_PROXY', 'no_proxy', 'SOCKS_PROXY', 'socks_proxy',
    'FTP_PROXY', 'ftp_proxy', 'RSYNC_PROXY', 'rsync_proxy'
]

cleaned = []
for var in proxy_vars:
    if var in os.environ:
        value = os.environ[var]
        del os.environ[var]
        cleaned.append(f"{var}={value}")
        print(f"❌ Cleared: {var} = {value}")

# همچنین تمام متغیرهایی که شامل 'proxy' هستند را پاک کن
for var in list(os.environ.keys()):
    if 'proxy' in var.lower():
        value = os.environ[var]
        del os.environ[var]
        if var not in proxy_vars:
            cleaned.append(f"{var}={value}")
            print(f"❌ Cleared (detected): {var} = {value}")

if cleaned:
    print(f"\n✅ Cleaned {len(cleaned)} proxy variable(s)")
else:
    print("\n✅ No proxy variables found")

print("=" * 70)
print()

# حالا می‌توانید بقیه imports را بنویسید
from pyrogram import Client, filters
# ... بقیه imports
#!/usr/bin/env python3
"""
Main entry point for the Telegram Bot
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the bot
from bot import main
import asyncio

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Bot failed: {e}")
        sys.exit(1)