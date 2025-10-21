#!/usr/bin/env python3
"""
اسکریپت هوشمند نصب و تشخیص ffmpeg
این اسکریپت به طور خودکار ffmpeg را در سیستم‌های ویندوز و اوبونتو پیدا و نصب می‌کند
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

def run_command(command, check=True):
    """اجرای دستور و بازگرداندن نتیجه"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=check)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def is_ffmpeg_installed():
    """بررسی نصب بودن ffmpeg"""
    return shutil.which("ffmpeg") is not None

def get_ffmpeg_path():
    """یافتن مسیر ffmpeg"""
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path
    
    # جستجو در مسیرهای معمول
    common_paths = [
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg", 
        "/opt/homebrew/bin/ffmpeg",
        "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",
        "C:\\ffmpeg\\bin\\ffmpeg.exe"
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    return None

def install_ffmpeg_ubuntu():
    """نصب ffmpeg روی اوبونتو"""
    print("📦 در حال نصب ffmpeg روی اوبونتو...")
    
    # به‌روزرسانی مخازن
    success, stdout, stderr = run_command("sudo apt update")
    if not success:
        print(f"❌ خطا در به‌روزرسانی مخازن: {stderr}")
        return False
    
    # نصب ffmpeg
    success, stdout, stderr = run_command("sudo apt install -y ffmpeg")
    if not success:
        print(f"❌ خطا در نصب ffmpeg: {stderr}")
        return False
    
    print("✅ ffmpeg با موفقیت روی اوبونتو نصب شد")
    return True

def install_ffmpeg_windows():
    """نصب ffmpeg روی ویندوز"""
    print("📦 در حال نصب ffmpeg روی ویندوز...")
    
    # دانلود و نصب ffmpeg از طریق chocolatey یا scoop
    try:
        # ابتدا chocolatey را بررسی می‌کنیم
        if shutil.which("choco"):
            success, stdout, stderr = run_command("choco install ffmpeg -y")
            if success:
                print("✅ ffmpeg با موفقیت از طریق Chocolatey نصب شد")
                return True
        
        # سپس scoop را بررسی می‌کنیم
        if shutil.which("scoop"):
            success, stdout, stderr = run_command("scoop install ffmpeg")
            if success:
                print("✅ ffmpeg با موفقیت از طریق Scoop نصب شد")
                return True
        
        # اگر هیچ‌کدام نبود، از git bash استفاده می‌کنیم
        git_bash_path = shutil.which("git") 
        if git_bash_path and "git" in git_bash_path.lower():
            print("⚠️  لطفاً ffmpeg را به صورت دستی نصب کنید یا Chocolatey/Scoop را نصب نمایید")
            print("📖 راهنمای نصب: https://ffmpeg.org/download.html")
            return False
            
    except Exception as e:
        print(f"❌ خطا در نصب ffmpeg: {e}")
        return False
    
    return False

def setup_ffmpeg_environment():
    """تنظیم متغیرهای محیطی برای ffmpeg"""
    ffmpeg_path = get_ffmpeg_path()
    if not ffmpeg_path:
        print("❌ ffmpeg پیدا نشد")
        return False
    
    # اضافه کردن به PATH اگر لازم باشد
    ffmpeg_dir = os.path.dirname(ffmpeg_path)
    current_path = os.environ.get('PATH', '')
    
    if ffmpeg_dir not in current_path:
        os.environ['PATH'] = ffmpeg_dir + os.pathsep + current_path
        print(f"✅ مسیر ffmpeg به PATH اضافه شد: {ffmpeg_dir}")
    
    # تنظیم متغیر محیطی FFMPEG_PATH
    os.environ['FFMPEG_PATH'] = ffmpeg_path
    print(f"✅ متغیر محیطی FFMPEG_PATH تنظیم شد: {ffmpeg_path}")
    
    return True

def main():
    """تابع اصلی"""
    print("🔍 در حال بررسی نصب بودن ffmpeg...")
    
    if is_ffmpeg_installed():
        ffmpeg_path = get_ffmpeg_path()
        print(f"✅ ffmpeg از قبل نصب است: {ffmpeg_path}")
        setup_ffmpeg_environment()
        return True
    
    print("❌ ffmpeg نصب نیست. در حال نصب...")
    
    system = platform.system().lower()
    
    if system == "linux" or "ubuntu" in platform.platform().lower():
        success = install_ffmpeg_ubuntu()
    elif system == "windows":
        success = install_ffmpeg_windows()
    else:
        print(f"❌ سیستم‌عامل پشتیبانی نمی‌شود: {system}")
        success = False
    
    if success:
        setup_ffmpeg_environment()
        print("🎉 ffmpeg با موفقیت نصب و پیکربندی شد!")
        
        # تست نصب
        success, stdout, stderr = run_command("ffmpeg -version", check=False)
        if success:
            print("✅ تست ffmpeg موفقیت‌آمیز بود")
            print(stdout.split('\n')[0])  # نمایش نسخه
        else:
            print("⚠️  ffmpeg نصب شده اما تست ناموفق بود")
    else:
        print("❌ نصب ffmpeg ناموفق بود")
        print("📖 لطفاً ffmpeg را به صورت دستی نصب کنید: https://ffmpeg.org/download.html")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)