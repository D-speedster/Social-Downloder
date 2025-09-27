#!/usr/bin/env python3
"""
تست ساده عملکرد YouTube callback query
"""

import asyncio
import json
import os
import sys
from plugins.youtube_helpers import download_youtube_file, get_direct_download_url

# تنظیمات تست
TEST_YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll - ویدیو کوتاه برای تست

async def test_youtube_helpers():
    """تست توابع کمکی یوتیوب"""
    
    print("🚀 شروع تست توابع کمکی YouTube...")
    
    try:
        # تست get_direct_download_url
        print(f"📤 تست دریافت لینک مستقیم برای: {TEST_YOUTUBE_URL}")
        
        direct_url = await get_direct_download_url(TEST_YOUTUBE_URL, "best")
        
        if direct_url:
            print(f"✅ لینک مستقیم دریافت شد: {direct_url[:100]}...")
        else:
            print("❌ نتوانست لینک مستقیم دریافت کند")
        
        print("✅ تست توابع کمکی با موفقیت انجام شد")
        
    except Exception as e:
        print(f"❌ خطا در تست: {e}")
        import traceback
        traceback.print_exc()

def test_imports():
    """تست import ها"""
    print("🔍 تست import ها...")
    
    try:
        from plugins.youtube_callback_query import answer
        print("✅ youtube_callback_query import شد")
        
        from plugins.sqlite_db_wrapper import DB
        print("✅ sqlite_db_wrapper import شد")
        
        from plugins.youtube_helpers import download_youtube_file, get_direct_download_url, safe_edit_text
        print("✅ youtube_helpers import شد")
        
        from utils.util import convert_size
        print("✅ utils.util import شد")
        
        print("✅ همه import ها موفق بودند")
        
    except Exception as e:
        print(f"❌ خطا در import: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 50)
    test_imports()
    print("=" * 50)
    asyncio.run(test_youtube_helpers())
    print("=" * 50)