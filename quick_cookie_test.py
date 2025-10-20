#!/usr/bin/env python3
"""
تست سریع کوکی‌های YouTube
Quick YouTube Cookie Test
"""

import subprocess
import sys
import os
from pathlib import Path
import logging

def setup_logging():
    """تنظیم لاگ"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def test_with_browser_cookies():
    """تست با کوکی‌های مرورگر"""
    logger = setup_logging()
    
    print("🍪 تست سریع کوکی‌های YouTube")
    print("="*50)
    
    # URL تست
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    # مرورگرهای پشتیبانی شده
    browsers = ['chrome', 'firefox', 'edge', 'chromium']
    
    for browser in browsers:
        print(f"\n🌐 تست با {browser}...")
        
        try:
            # تست با --cookies-from-browser
            cmd = [
                'yt-dlp',
                '--cookies-from-browser', browser,
                '--simulate',
                '--quiet',
                '--no-warnings',
                test_url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(f"✅ {browser}: موفق - کوکی‌ها معتبر هستند")
                logger.info(f"Success with {browser} cookies")
                return browser  # اولین مرورگر موفق را برگردان
            else:
                if "Sign in to confirm" in result.stderr:
                    print(f"❌ {browser}: نیاز به احراز هویت")
                elif "No such browser" in result.stderr:
                    print(f"⚠️ {browser}: مرورگر یافت نشد")
                else:
                    print(f"❌ {browser}: خطا - {result.stderr[:100]}...")
                    
        except subprocess.TimeoutExpired:
            print(f"⏰ {browser}: زمان انتظار تمام شد")
        except Exception as e:
            print(f"❌ {browser}: خطا - {str(e)}")
    
    return None

def test_with_cookie_file():
    """تست با فایل کوکی"""
    print(f"\n📁 تست با فایل کوکی...")
    
    cookie_files = ['youtube_cookies.txt', 'cookies.txt']
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    for cookie_file in cookie_files:
        if Path(cookie_file).exists():
            print(f"🔍 تست {cookie_file}...")
            
            try:
                cmd = [
                    'yt-dlp',
                    '--cookies', cookie_file,
                    '--simulate',
                    '--quiet',
                    '--no-warnings',
                    test_url
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    print(f"✅ {cookie_file}: موفق")
                    return cookie_file
                else:
                    print(f"❌ {cookie_file}: ناموفق")
                    
            except Exception as e:
                print(f"❌ {cookie_file}: خطا - {str(e)}")
        else:
            print(f"⚠️ {cookie_file}: فایل وجود ندارد")
    
    return None

def extract_cookies_automatically():
    """استخراج خودکار کوکی‌ها"""
    print(f"\n🔄 استخراج خودکار کوکی‌ها...")
    
    if Path('auto_cookie_manager.py').exists():
        try:
            result = subprocess.run(
                [sys.executable, 'auto_cookie_manager.py', 'auto'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print("✅ کوکی‌ها با موفقیت استخراج شدند")
                return True
            else:
                print(f"❌ خطا در استخراج: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ خطا: {str(e)}")
            return False
    else:
        print("⚠️ فایل auto_cookie_manager.py یافت نشد")
        return False

def main():
    """تابع اصلی"""
    print("🚀 شروع تست سریع کوکی‌های YouTube")
    
    # تست 1: کوکی‌های مرورگر
    successful_browser = test_with_browser_cookies()
    
    if successful_browser:
        print(f"\n🎉 موفقیت! از مرورگر {successful_browser} استفاده کنید:")
        print(f"yt-dlp --cookies-from-browser {successful_browser} [URL]")
        return
    
    # تست 2: فایل کوکی
    successful_file = test_with_cookie_file()
    
    if successful_file:
        print(f"\n🎉 موفقیت! از فایل {successful_file} استفاده کنید:")
        print(f"yt-dlp --cookies {successful_file} [URL]")
        return
    
    # تست 3: استخراج خودکار
    print(f"\n🔧 تلاش برای حل مشکل...")
    
    if extract_cookies_automatically():
        # تست مجدد با فایل جدید
        successful_file = test_with_cookie_file()
        if successful_file:
            print(f"\n🎉 مشکل حل شد! از فایل {successful_file} استفاده کنید:")
            print(f"yt-dlp --cookies {successful_file} [URL]")
            return
    
    # راهنمایی نهایی
    print(f"\n❌ هیچ کوکی معتبری یافت نشد!")
    print(f"\n💡 راه‌حل‌های پیشنهادی:")
    print(f"1. مرورگر را باز کنید و به YouTube وارد شوید")
    print(f"2. دستور زیر را اجرا کنید:")
    print(f"   python3 auto_cookie_manager.py extract")
    print(f"3. یا از دستور زیر استفاده کنید:")
    print(f"   yt-dlp --cookies-from-browser chrome [URL]")
    print(f"\n📖 برای راهنمای کامل:")
    print(f"   cat COOKIE_AUTHENTICATION_GUIDE.md")

if __name__ == "__main__":
    main()