#!/usr/bin/env python3
"""
اجرای کامل راه‌حل احراز هویت کوکی YouTube
Complete YouTube Cookie Authentication Solution Runner
"""

import sys
import subprocess
import os
from pathlib import Path
import argparse
import logging

def setup_logging():
    """تنظیم سیستم لاگ"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('solution_runner.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def print_banner():
    """چاپ بنر شروع"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                   🎬 YouTube Downloader                      ║
║              راه‌حل کامل احراز هویت کوکی                      ║
║                Complete Cookie Auth Solution                 ║
╚══════════════════════════════════════════════════════════════╝
    """)

def check_dependencies():
    """بررسی وابستگی‌ها"""
    logger = logging.getLogger(__name__)
    print("🔍 بررسی وابستگی‌ها...")
    
    required_modules = ['yt_dlp', 'requests']
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module} - ناموجود")
            missing_modules.append(module)
    
    if missing_modules:
        print(f"\n⚠️ ماژول‌های ناموجود: {', '.join(missing_modules)}")
        print("📦 نصب وابستگی‌ها:")
        print("pip install yt-dlp requests")
        return False
    
    return True

def setup_cookies():
    """تنظیم کوکی‌ها"""
    logger = logging.getLogger(__name__)
    print("\n🍪 تنظیم کوکی‌ها...")
    
    # بررسی فایل‌های کوکی موجود
    cookie_files = ['youtube_cookies.txt', 'cookies.txt']
    existing_cookies = [f for f in cookie_files if Path(f).exists()]
    
    if existing_cookies:
        print(f"✅ فایل‌های کوکی موجود: {', '.join(existing_cookies)}")
        return True
    
    # تلاش برای استخراج خودکار
    if Path('auto_cookie_manager.py').exists():
        print("🔄 استخراج خودکار کوکی‌ها...")
        try:
            result = subprocess.run(
                [sys.executable, 'auto_cookie_manager.py', 'auto'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print("✅ کوکی‌ها استخراج شدند")
                return True
            else:
                print(f"❌ خطا در استخراج: {result.stderr}")
        except Exception as e:
            print(f"❌ خطا: {str(e)}")
    
    # راهنمایی دستی
    print("\n💡 راه‌حل‌های دستی:")
    print("1. مرورگر را باز کنید و به YouTube وارد شوید")
    print("2. دستور زیر را اجرا کنید:")
    print("   python3 auto_cookie_manager.py extract")
    print("3. یا از --cookies-from-browser استفاده کنید")
    
    return False

def test_connection():
    """تست اتصال"""
    print("\n🌐 تست اتصال...")
    
    if Path('emergency_youtube_downloader.py').exists():
        try:
            result = subprocess.run(
                [sys.executable, 'emergency_youtube_downloader.py', 'test'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print("✅ اتصال موفق")
                return True
            else:
                if "Sign in to confirm" in result.stderr:
                    print("⚠️ اتصال موفق، نیاز به احراز هویت")
                    return True
                else:
                    print(f"❌ خطا در اتصال: {result.stderr}")
                    return False
        except Exception as e:
            print(f"❌ خطا: {str(e)}")
            return False
    
    return False

def download_video(url, quality='720p'):
    """دانلود ویدیو"""
    logger = logging.getLogger(__name__)
    print(f"\n📥 شروع دانلود: {url}")
    
    if Path('emergency_youtube_downloader.py').exists():
        try:
            cmd = [sys.executable, 'emergency_youtube_downloader.py', 'download', url, quality]
            
            print(f"🚀 اجرای دستور: {' '.join(cmd)}")
            
            # اجرای دستور با نمایش خروجی زنده
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # نمایش خروجی زنده
            for line in process.stdout:
                print(line.rstrip())
            
            process.wait()
            
            if process.returncode == 0:
                print("✅ دانلود موفق")
                return True
            else:
                print("❌ دانلود ناموفق")
                return False
                
        except Exception as e:
            print(f"❌ خطا: {str(e)}")
            return False
    else:
        print("❌ فایل emergency_youtube_downloader.py یافت نشد")
        return False

def run_quick_test():
    """اجرای تست سریع"""
    print("\n🧪 تست سریع...")
    
    if Path('quick_cookie_test.py').exists():
        try:
            subprocess.run([sys.executable, 'quick_cookie_test.py'], check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    else:
        print("❌ فایل quick_cookie_test.py یافت نشد")
        return False

def run_complete_test():
    """اجرای تست کامل"""
    print("\n🧪 تست کامل...")
    
    if Path('test_complete_solution.py').exists():
        try:
            subprocess.run([sys.executable, 'test_complete_solution.py'], check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    else:
        print("❌ فایل test_complete_solution.py یافت نشد")
        return False

def show_help():
    """نمایش راهنما"""
    print("""
📖 راهنمای استفاده:

🔧 دستورات اصلی:
  python3 run_complete_solution.py setup     - تنظیم اولیه
  python3 run_complete_solution.py test      - تست سریع
  python3 run_complete_solution.py fulltest  - تست کامل
  python3 run_complete_solution.py download <URL> - دانلود ویدیو

📥 مثال‌های دانلود:
  python3 run_complete_solution.py download "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  python3 run_complete_solution.py download "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 1080p

🍪 مدیریت کوکی‌ها:
  python3 auto_cookie_manager.py auto        - استخراج خودکار
  python3 auto_cookie_manager.py extract     - استخراج دستی
  python3 auto_cookie_manager.py test        - تست کوکی‌ها

🚨 حل مشکلات:
  python3 quick_cookie_test.py               - تست سریع کوکی‌ها
  python3 test_complete_solution.py          - تست کامل سیستم

📚 مستندات:
  cat COOKIE_AUTHENTICATION_GUIDE.md        - راهنمای کامل
    """)

def main():
    """تابع اصلی"""
    logger = setup_logging()
    
    parser = argparse.ArgumentParser(description='YouTube Cookie Authentication Solution')
    parser.add_argument('command', nargs='?', choices=['setup', 'test', 'fulltest', 'download', 'help'], 
                       default='help', help='Command to execute')
    parser.add_argument('url', nargs='?', help='YouTube URL to download')
    parser.add_argument('quality', nargs='?', default='720p', help='Video quality (default: 720p)')
    
    args = parser.parse_args()
    
    print_banner()
    
    if args.command == 'help':
        show_help()
        return
    
    elif args.command == 'setup':
        print("🔧 تنظیم اولیه...")
        
        if not check_dependencies():
            sys.exit(1)
        
        if not setup_cookies():
            print("\n⚠️ تنظیم کوکی‌ها ناکامل. لطفاً دستورالعمل‌ها را دنبال کنید.")
        
        if test_connection():
            print("\n🎉 تنظیم اولیه موفق!")
        else:
            print("\n⚠️ مشکل در اتصال. ممکن است نیاز به تنظیم بیشتر باشد.")
    
    elif args.command == 'test':
        if not run_quick_test():
            print("\n❌ تست سریع ناموفق")
            sys.exit(1)
    
    elif args.command == 'fulltest':
        if not run_complete_test():
            print("\n❌ تست کامل ناموفق")
            sys.exit(1)
    
    elif args.command == 'download':
        if not args.url:
            print("❌ لطفاً URL ویدیو را وارد کنید")
            print("مثال: python3 run_complete_solution.py download 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'")
            sys.exit(1)
        
        if not download_video(args.url, args.quality):
            print("\n❌ دانلود ناموفق")
            sys.exit(1)
    
    print("\n✅ عملیات تکمیل شد!")

if __name__ == "__main__":
    main()