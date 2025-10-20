#!/usr/bin/env python3
"""
اسکریپت تست ساده برای بررسی بهبودهای DNS resolution
"""

import os
import sys
import time
from pathlib import Path

print("🚀 شروع تست DNS resolution")
print(f"📁 مسیر کاری: {os.getcwd()}")

# اضافه کردن مسیر پروژه به sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
print(f"📂 مسیر پروژه: {project_root}")

try:
    print("📦 در حال import کردن ماژول‌ها...")
    from plugins.youtube_advanced_downloader import YouTubeAdvancedDownloader
    print("✅ YouTubeAdvancedDownloader import شد")
    
    from plugins.logger_config import get_logger
    print("✅ logger_config import شد")
    
    # تنظیم logger
    test_logger = get_logger('dns_test')
    print("✅ Logger تنظیم شد")
    
except Exception as e:
    print(f"❌ خطا در import: {e}")
    sys.exit(1)

def test_network_connectivity():
    """تست اتصال شبکه"""
    print("\n=== تست اتصال شبکه ===")
    
    import socket
    import urllib.request
    
    # تست DNS resolution
    try:
        result = socket.gethostbyname('youtube.com')
        print(f"✅ DNS resolution برای youtube.com موفق: {result}")
        dns_status = 'success'
    except Exception as e:
        print(f"❌ DNS resolution شکست: {e}")
        dns_status = 'failed'
    
    # تست اتصال HTTP
    try:
        response = urllib.request.urlopen('https://www.youtube.com', timeout=10)
        if response.getcode() == 200:
            print("✅ اتصال HTTP به YouTube موفق")
            http_status = 'success'
        else:
            print(f"⚠️ کد پاسخ غیرمنتظره: {response.getcode()}")
            http_status = 'warning'
    except Exception as e:
        print(f"❌ اتصال HTTP شکست: {e}")
        http_status = 'failed'
    
    return dns_status, http_status

def test_youtube_downloader():
    """تست YouTubeAdvancedDownloader"""
    print("\n=== تست YouTubeAdvancedDownloader ===")
    
    try:
        downloader = YouTubeAdvancedDownloader()
        print("✅ YouTubeAdvancedDownloader ایجاد شد")
        
        # تست URL ساده
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        print(f"🔍 تست URL: {test_url}")
        
        # تست get_video_info (sync version)
        print("📡 در حال دریافت اطلاعات ویدیو...")
        start_time = time.time()
        
        # استفاده از asyncio برای اجرای async function
        import asyncio
        
        async def get_info():
            return await downloader.get_video_info(test_url)
        
        info = asyncio.run(get_info())
        end_time = time.time()
        
        if info:
            print(f"✅ اطلاعات ویدیو دریافت شد")
            print(f"📝 عنوان: {info.get('title', 'نامشخص')}")
            print(f"⏱️ زمان: {end_time - start_time:.2f} ثانیه")
            
            # تست کیفیت‌ها
            qualities = downloader.get_mergeable_qualities(info)
            print(f"🎬 تعداد کیفیت‌ها: {len(qualities)}")
            
            if qualities:
                print("📋 کیفیت‌های موجود:")
                for i, quality in enumerate(qualities[:3]):  # نمایش 3 کیفیت اول
                    print(f"  {i+1}. {quality.get('quality', 'نامشخص')}: {quality.get('format_id', 'نامشخص')}")
            
            return True
        else:
            print("❌ اطلاعات ویدیو دریافت نشد")
            return False
            
    except Exception as e:
        print(f"❌ خطا در تست downloader: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_yt_dlp_settings():
    """تست تنظیمات yt-dlp"""
    print("\n=== تست تنظیمات yt-dlp ===")
    
    try:
        import yt_dlp
        print("✅ yt-dlp import شد")
        
        # تست تنظیمات بهبود یافته
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'simulate': True,  # شبیه‌سازی بدون دانلود
            'socket_timeout': 30,
            'connect_timeout': 20,
            'retries': 5,
            'fragment_retries': 5,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        }
        
        # اضافه کردن کوکی در صورت وجود
        if os.path.exists('cookie_youtube.txt'):
            ydl_opts['cookiefile'] = 'cookie_youtube.txt'
            print("✅ فایل کوکی اضافه شد")
        else:
            print("ℹ️ فایل کوکی یافت نشد")
        
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        print(f"🔍 تست شبیه‌سازی دانلود: {test_url}")
        
        start_time = time.time()
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([test_url])
        
        end_time = time.time()
        print(f"✅ شبیه‌سازی دانلود موفق")
        print(f"⏱️ زمان: {end_time - start_time:.2f} ثانیه")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در تست yt-dlp: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """تابع اصلی"""
    print("🎯 شروع تست‌های جامع DNS resolution")
    
    results = []
    
    # تست اتصال شبکه
    dns_status, http_status = test_network_connectivity()
    results.append(('Network DNS', dns_status))
    results.append(('Network HTTP', http_status))
    
    # تست YouTubeAdvancedDownloader
    downloader_result = test_youtube_downloader()
    results.append(('YouTube Downloader', 'success' if downloader_result else 'failed'))
    
    # تست yt-dlp
    ytdlp_result = test_yt_dlp_settings()
    results.append(('yt-dlp Settings', 'success' if ytdlp_result else 'failed'))
    
    # خلاصه نتایج
    print("\n" + "="*50)
    print("📊 خلاصه نتایج:")
    print("="*50)
    
    successful = 0
    total = len(results)
    
    for test_name, status in results:
        icon = "✅" if status == 'success' else "❌" if status == 'failed' else "⚠️"
        print(f"{icon} {test_name}: {status}")
        if status == 'success':
            successful += 1
    
    print(f"\n📈 نتیجه کلی: {successful}/{total} تست موفق ({(successful/total)*100:.1f}%)")
    
    if successful == total:
        print("🎉 همه تست‌ها موفق! بهبودهای DNS resolution کار می‌کنند.")
    else:
        print("⚠️ برخی تست‌ها ناموفق. لطفاً لاگ‌ها را بررسی کنید.")
    
    print("🏁 تست‌ها تمام شد")

if __name__ == "__main__":
    main()