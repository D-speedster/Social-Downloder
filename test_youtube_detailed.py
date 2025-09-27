#!/usr/bin/env python3
"""
تست جامع عملکرد YouTube با URL های مختلف
"""

import asyncio
import json
import os
import sys
import yt_dlp
from plugins.youtube_helpers import download_youtube_file, get_direct_download_url

# تنظیمات تست
TEST_URLS = [
    "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # Me at the zoo - اولین ویدیو یوتیوب
    "https://www.youtube.com/watch?v=9bZkp7q19f0",  # PSY - Gangnam Style
    "https://www.youtube.com/watch?v=kJQP7kiw5Fk",  # Luis Fonsi - Despacito
]

async def test_video_info_extraction(url):
    """تست استخراج اطلاعات ویدیو"""
    print(f"📋 تست استخراج اطلاعات برای: {url}")
    
    try:
        ydl_opts = {
            'quiet': True,
            'simulate': True,
            'noplaylist': True,
            'extract_flat': False,
        }
        
        # Add cookies if available
        cookie_path = os.path.join(os.getcwd(), 'cookies', 'youtube.txt')
        if os.path.exists(cookie_path):
            ydl_opts['cookiefile'] = cookie_path
        
        def extract_sync():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        
        info = await asyncio.to_thread(extract_sync)
        
        if info:
            print(f"✅ عنوان: {info.get('title', 'نامشخص')}")
            print(f"✅ مدت زمان: {info.get('duration', 'نامشخص')} ثانیه")
            print(f"✅ تعداد فرمت‌ها: {len(info.get('formats', []))}")
            
            # نمایش چند فرمت اول
            formats = info.get('formats', [])[:5]
            for fmt in formats:
                print(f"   - فرمت {fmt.get('format_id')}: {fmt.get('ext')} - {fmt.get('resolution', 'audio only')}")
            
            return info
        else:
            print("❌ نتوانست اطلاعات ویدیو را استخراج کند")
            return None
            
    except Exception as e:
        print(f"❌ خطا در استخراج اطلاعات: {e}")
        return None

async def test_direct_url_extraction(url, format_id="best"):
    """تست دریافت لینک مستقیم"""
    print(f"🔗 تست دریافت لینک مستقیم برای فرمت {format_id}")
    
    try:
        direct_url = await get_direct_download_url(url, format_id)
        
        if direct_url:
            print(f"✅ لینک مستقیم دریافت شد: {direct_url[:100]}...")
            return True
        else:
            print("❌ نتوانست لینک مستقیم دریافت کند")
            return False
            
    except Exception as e:
        print(f"❌ خطا در دریافت لینک مستقیم: {e}")
        return False

async def test_youtube_comprehensive():
    """تست جامع عملکرد YouTube"""
    
    print("🚀 شروع تست جامع YouTube...")
    print("=" * 60)
    
    success_count = 0
    total_tests = len(TEST_URLS)
    
    for i, url in enumerate(TEST_URLS, 1):
        print(f"\n📹 تست {i}/{total_tests}: {url}")
        print("-" * 40)
        
        try:
            # تست استخراج اطلاعات
            info = await test_video_info_extraction(url)
            
            if info:
                # تست دریافت لینک مستقیم با فرمت‌های مختلف
                formats_to_test = ["best", "worst", "bestaudio", "bestvideo"]
                
                for fmt in formats_to_test:
                    success = await test_direct_url_extraction(url, fmt)
                    if success:
                        success_count += 1
                        break  # اگر یک فرمت کار کرد، به بعدی برو
            
            print("✅ تست این ویدیو تمام شد")
            
        except Exception as e:
            print(f"❌ خطای کلی در تست: {e}")
        
        print("-" * 40)
    
    print(f"\n📊 نتایج نهایی:")
    print(f"✅ تست‌های موفق: {success_count}/{total_tests}")
    print(f"❌ تست‌های ناموفق: {total_tests - success_count}/{total_tests}")
    
    if success_count > 0:
        print("🎉 حداقل یک تست موفق بود - عملکرد YouTube کار می‌کند!")
    else:
        print("⚠️ هیچ تستی موفق نبود - ممکن است مشکلی وجود داشته باشد")

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
        return True
        
    except Exception as e:
        print(f"❌ خطا در import: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 تست جامع عملکرد YouTube")
    print("=" * 60)
    
    # تست import ها
    if not test_imports():
        print("❌ تست import ها ناموفق - خروج از برنامه")
        sys.exit(1)
    
    print("=" * 60)
    
    # تست عملکرد YouTube
    asyncio.run(test_youtube_comprehensive())
    
    print("=" * 60)
    print("🏁 تست تمام شد")