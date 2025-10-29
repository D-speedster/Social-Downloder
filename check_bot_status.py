#!/usr/bin/env python3
"""
بررسی وضعیت بات و نمایش اطلاعات مفید
"""
import os
import sys
import subprocess
import time

def check_bot_process():
    """بررسی اینکه آیا بات در حال اجرا است"""
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        bot_processes = [line for line in result.stdout.split('\n') if 'bot.py' in line and 'grep' not in line]
        
        if bot_processes:
            print("✅ بات در حال اجرا است:")
            for proc in bot_processes:
                print(f"   {proc}")
            return True
        else:
            print("❌ بات در حال اجرا نیست")
            return False
    except Exception as e:
        print(f"❌ خطا در بررسی process: {e}")
        return False

def check_log_files():
    """بررسی فایل‌های لاگ"""
    log_dir = './logs'
    if not os.path.exists(log_dir):
        print(f"❌ دایرکتوری لاگ وجود ندارد: {log_dir}")
        return
    
    print("\n📁 فایل‌های لاگ:")
    log_files = [
        'youtube_uploader.log',
        'stream_utils.log',
        'youtube_callback.log',
        'universal_downloader.log'
    ]
    
    for log_file in log_files:
        log_path = os.path.join(log_dir, log_file)
        if os.path.exists(log_path):
            size = os.path.getsize(log_path)
            mtime = os.path.getmtime(log_path)
            mtime_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
            print(f"   ✅ {log_file}: {size} bytes (آخرین تغییر: {mtime_str})")
        else:
            print(f"   ❌ {log_file}: وجود ندارد")

def check_recent_logs():
    """نمایش آخرین لاگ‌ها"""
    log_files = [
        './logs/youtube_uploader.log',
        './logs/stream_utils.log'
    ]
    
    print("\n📋 آخرین لاگ‌ها:")
    for log_file in log_files:
        if os.path.exists(log_file):
            print(f"\n--- {os.path.basename(log_file)} ---")
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # نمایش 5 خط آخر
                    for line in lines[-5:]:
                        print(f"   {line.strip()}")
            except Exception as e:
                print(f"   ❌ خطا در خواندن: {e}")

def check_code_changes():
    """بررسی تاریخ تغییرات کد"""
    files_to_check = [
        'plugins/youtube_uploader.py',
        'plugins/stream_utils.py',
        'plugins/youtube_callback.py'
    ]
    
    print("\n🔧 تاریخ تغییرات فایل‌های کد:")
    for file_path in files_to_check:
        if os.path.exists(file_path):
            mtime = os.path.getmtime(file_path)
            mtime_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
            print(f"   {file_path}: {mtime_str}")
        else:
            print(f"   ❌ {file_path}: وجود ندارد")

def main():
    print("=" * 60)
    print("🔍 بررسی وضعیت بات دانلودر")
    print("=" * 60)
    
    # بررسی process
    is_running = check_bot_process()
    
    # بررسی فایل‌های لاگ
    check_log_files()
    
    # بررسی تغییرات کد
    check_code_changes()
    
    # نمایش آخرین لاگ‌ها
    check_recent_logs()
    
    print("\n" + "=" * 60)
    if is_running:
        print("💡 نکته: اگر تغییراتی در کد ایجاد کرده‌اید، حتماً بات را restart کنید!")
        print("   دستور: Ctrl+C در ترمینال بات، سپس: python bot.py")
    else:
        print("💡 نکته: بات در حال اجرا نیست. برای اجرا:")
        print("   دستور: python bot.py")
    print("=" * 60)

if __name__ == "__main__":
    main()
