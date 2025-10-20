#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اسکریپت اجرای YouTube Downloader در محیط سرور لینوکس
با حل مشکلات DNS و تنظیمات بهینه
"""

import os
import sys
import socket
import asyncio
import urllib3
import platform
from pathlib import Path

# اضافه کردن مسیر پروژه
sys.path.append(str(Path(__file__).parent))

from plugins.youtube_advanced_downloader import youtube_downloader
from plugins.logger_config import get_logger

# تنظیم logger
server_logger = get_logger('linux_server_runner')

class LinuxServerRunner:
    def __init__(self):
        self.is_linux = platform.system().lower() == 'linux'
        self.test_url = "https://www.youtube.com/watch?v=dL_r_PPlFtI"
        
    def setup_environment(self):
        """تنظیم محیط برای سرور لینوکس"""
        server_logger.info("تنظیم محیط سرور لینوکس...")
        
        try:
            # تنظیمات DNS و شبکه
            os.environ.update({
                'PYTHONHTTPSVERIFY': '0',
                'CURL_CA_BUNDLE': '',
                'REQUESTS_CA_BUNDLE': '',
                'SOCKET_TIMEOUT': '60',
                'CONNECT_TIMEOUT': '45',
                'READ_TIMEOUT': '120',
                'PYTHONUNBUFFERED': '1',
                'PYTHONDONTWRITEBYTECODE': '1',
                'RES_OPTIONS': 'timeout:5 attempts:3 rotate single-request-reopen'
            })
            
            # تنظیم socket timeout
            socket.setdefaulttimeout(60)
            
            # غیرفعال کردن هشدارهای SSL
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            server_logger.info("✅ محیط سرور تنظیم شد")
            return True
            
        except Exception as e:
            server_logger.error(f"❌ خطا در تنظیم محیط: {e}")
            return False
    
    async def test_connection(self):
        """تست اتصال و DNS"""
        server_logger.info("تست اتصال و DNS...")
        
        try:
            # تست DNS resolution
            socket.gethostbyname('youtube.com')
            server_logger.info("✅ DNS resolution موفق")
            
            # تست دریافت اطلاعات ویدیو
            video_info = await youtube_downloader.get_video_info(self.test_url)
            
            if video_info:
                server_logger.info("✅ دریافت اطلاعات ویدیو موفق")
                server_logger.info(f"عنوان: {video_info.get('title', 'نامشخص')}")
                return True
            else:
                server_logger.error("❌ دریافت اطلاعات ویدیو ناموفق")
                return False
                
        except Exception as e:
            server_logger.error(f"❌ خطا در تست اتصال: {e}")
            return False
    
    async def download_video(self, url: str, quality: str = "720p"):
        """دانلود ویدیو با تنظیمات بهینه سرور"""
        server_logger.info(f"شروع دانلود ویدیو: {url}")
        
        try:
            # دریافت اطلاعات ویدیو
            video_info = await youtube_downloader.get_video_info(url)
            if not video_info:
                server_logger.error("❌ عدم دریافت اطلاعات ویدیو")
                return None
            
            # دریافت کیفیت‌های موجود
            qualities = youtube_downloader.get_mergeable_qualities(video_info)
            if not qualities:
                server_logger.error("❌ کیفیت‌های موجود یافت نشد")
                return None
            
            # انتخاب کیفیت مناسب
            selected_quality = None
            for q in qualities:
                if quality in str(q.get('quality', '')):
                    selected_quality = q
                    break
            
            if not selected_quality:
                selected_quality = qualities[0]  # انتخاب اولین کیفیت موجود
                server_logger.info(f"کیفیت درخواستی یافت نشد، انتخاب: {selected_quality.get('quality')}")
            
            # شروع دانلود
            def progress_callback(d):
                if d['status'] == 'downloading':
                    percent = d.get('_percent_str', 'N/A')
                    speed = d.get('_speed_str', 'N/A')
                    server_logger.info(f"دانلود: {percent} - سرعت: {speed}")
                elif d['status'] == 'finished':
                    server_logger.info(f"✅ دانلود کامل شد: {d['filename']}")
            
            result = await youtube_downloader.download_and_merge(
                url, 
                selected_quality, 
                callback=progress_callback
            )
            
            if result.get('success'):
                server_logger.info(f"✅ دانلود موفق: {result.get('output_path')}")
                return result
            else:
                server_logger.error(f"❌ دانلود ناموفق: {result.get('error')}")
                return None
                
        except Exception as e:
            server_logger.error(f"❌ خطا در دانلود: {e}")
            return None
    
    async def run_interactive_mode(self):
        """حالت تعاملی برای دانلود"""
        server_logger.info("🚀 حالت تعاملی YouTube Downloader")
        
        while True:
            try:
                print("\n" + "="*50)
                print("YouTube Downloader - Linux Server Mode")
                print("="*50)
                print("1. دانلود ویدیو")
                print("2. تست اتصال")
                print("3. خروج")
                
                choice = input("\nانتخاب کنید (1-3): ").strip()
                
                if choice == '1':
                    url = input("URL ویدیو را وارد کنید: ").strip()
                    if not url:
                        print("❌ URL نامعتبر")
                        continue
                    
                    quality = input("کیفیت مورد نظر (720p/480p/360p یا Enter برای پیش‌فرض): ").strip()
                    if not quality:
                        quality = "720p"
                    
                    print(f"\n🔄 شروع دانلود با کیفیت {quality}...")
                    result = await self.download_video(url, quality)
                    
                    if result:
                        print(f"✅ دانلود موفق!")
                        print(f"📁 مسیر فایل: {result.get('output_path')}")
                    else:
                        print("❌ دانلود ناموفق")
                
                elif choice == '2':
                    print("\n🔄 تست اتصال...")
                    success = await self.test_connection()
                    if success:
                        print("✅ اتصال موفق")
                    else:
                        print("❌ اتصال ناموفق")
                
                elif choice == '3':
                    print("👋 خروج...")
                    break
                
                else:
                    print("❌ انتخاب نامعتبر")
                    
            except KeyboardInterrupt:
                print("\n👋 خروج...")
                break
            except Exception as e:
                server_logger.error(f"خطا: {e}")
    
    async def run_batch_mode(self, urls: list, quality: str = "720p"):
        """حالت دانلود دسته‌ای"""
        server_logger.info(f"🚀 شروع دانلود دسته‌ای {len(urls)} ویدیو")
        
        results = []
        for i, url in enumerate(urls, 1):
            server_logger.info(f"📹 دانلود {i}/{len(urls)}: {url}")
            
            result = await self.download_video(url, quality)
            results.append({
                'url': url,
                'success': result is not None,
                'result': result
            })
            
            # استراحت بین دانلودها
            if i < len(urls):
                await asyncio.sleep(2)
        
        # گزارش نهایی
        successful = sum(1 for r in results if r['success'])
        server_logger.info(f"📊 گزارش نهایی: {successful}/{len(urls)} موفق")
        
        return results

async def main():
    """تابع اصلی"""
    runner = LinuxServerRunner()
    
    # تنظیم محیط
    if not runner.setup_environment():
        print("❌ خطا در تنظیم محیط")
        return 1
    
    # بررسی آرگومان‌های خط فرمان
    if len(sys.argv) > 1:
        if sys.argv[1] == 'test':
            # حالت تست
            print("🔄 تست اتصال...")
            success = await runner.test_connection()
            return 0 if success else 1
            
        elif sys.argv[1] == 'download' and len(sys.argv) > 2:
            # حالت دانلود مستقیم
            url = sys.argv[2]
            quality = sys.argv[3] if len(sys.argv) > 3 else "720p"
            
            print(f"🔄 دانلود: {url}")
            result = await runner.download_video(url, quality)
            return 0 if result else 1
            
        elif sys.argv[1] == 'batch' and len(sys.argv) > 2:
            # حالت دانلود دسته‌ای
            urls_file = sys.argv[2]
            quality = sys.argv[3] if len(sys.argv) > 3 else "720p"
            
            try:
                with open(urls_file, 'r') as f:
                    urls = [line.strip() for line in f if line.strip()]
                
                results = await runner.run_batch_mode(urls, quality)
                successful = sum(1 for r in results if r['success'])
                return 0 if successful > 0 else 1
                
            except Exception as e:
                print(f"❌ خطا در خواندن فایل: {e}")
                return 1
    
    # حالت تعاملی (پیش‌فرض)
    await runner.run_interactive_mode()
    return 0

if __name__ == "__main__":
    print("🌐 YouTube Downloader - Linux Server Edition")
    print("=" * 50)
    
    if len(sys.argv) == 1:
        print("💡 استفاده:")
        print("  python3 run_on_linux_server.py                    # حالت تعاملی")
        print("  python3 run_on_linux_server.py test               # تست اتصال")
        print("  python3 run_on_linux_server.py download <URL>     # دانلود مستقیم")
        print("  python3 run_on_linux_server.py batch <file>       # دانلود دسته‌ای")
        print()
    
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 لغو شد")
        sys.exit(0)
    except Exception as e:
        print(f"❌ خطای غیرمنتظره: {e}")
        sys.exit(1)