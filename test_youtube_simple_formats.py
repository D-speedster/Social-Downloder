#!/usr/bin/env python3
"""
تست ساده عملکرد YouTube با فرمت‌های مختلف
"""

import asyncio
import json
import os
import sys
import yt_dlp

# تنظیمات تست
TEST_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # Me at the zoo - اولین ویدیو یوتیوب

async def list_available_formats(url):
    """لیست فرمت‌های موجود"""
    print(f"📋 لیست فرمت‌های موجود برای: {url}")
    
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
        
        if info and 'formats' in info:
            print(f"✅ عنوان: {info.get('title', 'نامشخص')}")
            print(f"✅ تعداد فرمت‌ها: {len(info['formats'])}")
            print("\n📋 فرمت‌های موجود:")
            
            # نمایش فرمت‌های مختلف
            for fmt in info['formats'][:10]:  # نمایش 10 فرمت اول
                format_id = fmt.get('format_id', 'نامشخص')
                ext = fmt.get('ext', 'نامشخص')
                resolution = fmt.get('resolution', fmt.get('height', 'audio only'))
                filesize = fmt.get('filesize', 'نامشخص')
                url_available = 'url' in fmt and fmt['url'] is not None
                
                print(f"   - {format_id}: {ext} - {resolution} - URL: {'✅' if url_available else '❌'}")
            
            return info['formats']
        else:
            print("❌ نتوانست فرمت‌ها را دریافت کند")
            return []
            
    except Exception as e:
        print(f"❌ خطا در دریافت فرمت‌ها: {e}")
        return []

async def test_format_url(url, format_id):
    """تست دریافت URL برای فرمت مشخص"""
    try:
        ydl_opts = {
            'format': format_id,
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
        
        if info and 'url' in info:
            print(f"✅ فرمت {format_id}: URL موجود است")
            return True
        else:
            print(f"❌ فرمت {format_id}: URL موجود نیست")
            return False
            
    except Exception as e:
        print(f"❌ فرمت {format_id}: خطا - {e}")
        return False

async def test_youtube_formats():
    """تست فرمت‌های مختلف YouTube"""
    
    print("🚀 شروع تست فرمت‌های YouTube...")
    print("=" * 60)
    
    # دریافت لیست فرمت‌ها
    formats = await list_available_formats(TEST_URL)
    
    if not formats:
        print("❌ نتوانست فرمت‌ها را دریافت کند")
        return
    
    print("\n🧪 تست فرمت‌های مختلف:")
    print("-" * 40)
    
    # تست فرمت‌های پیش‌فرض
    default_formats = ["best", "worst", "bestaudio", "bestvideo"]
    
    for fmt in default_formats:
        print(f"🔍 تست فرمت: {fmt}")
        success = await test_format_url(TEST_URL, fmt)
        if success:
            print(f"✅ فرمت {fmt} کار می‌کند!")
            break
    
    print("\n🔍 تست فرمت‌های خاص:")
    
    # تست چند فرمت خاص که URL دارند
    formats_with_url = [fmt for fmt in formats if 'url' in fmt and fmt['url']][:5]
    
    for fmt in formats_with_url:
        format_id = fmt.get('format_id')
        if format_id:
            success = await test_format_url(TEST_URL, format_id)
            if success:
                print(f"✅ فرمت {format_id} کار می‌کند!")

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 تست فرمت‌های YouTube")
    print("=" * 60)
    
    asyncio.run(test_youtube_formats())
    
    print("=" * 60)
    print("🏁 تست تمام شد")