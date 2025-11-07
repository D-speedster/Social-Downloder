#!/usr/bin/env python3
"""
اسکریپت راه‌اندازی ربات با پاکسازی خودکار
برای Windows و Linux
"""
import os
import sys
import glob
import time
import subprocess

def print_header(text):
    print("=" * 70)
    print(f"🔹 {text}")
    print("=" * 70)

def print_success(text):
    print(f"✅ {text}")

def print_warning(text):
    print(f"⚠️ {text}")

def print_error(text):
    print(f"❌ {text}")

def check_venv():
    """بررسی virtual environment"""
    print_header("بررسی Virtual Environment")
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print_success("Virtual environment فعال است")
        return True
    else:
        print_warning("Virtual environment فعال نیست")
        return False

def kill_old_processes():
    """توقف پروسس‌های قدیمی"""
    print_header("بررسی پروسس‌های قدیمی")
    try:
        import psutil
        current_pid = os.getpid()
        killed = 0
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and 'bot.py' in ' '.join(cmdline) and proc.info['pid'] != current_pid:
                    print_warning(f"پروسس قدیمی یافت شد: PID {proc.info['pid']}")
                    proc.terminate()
                    proc.wait(timeout=5)
                    killed += 1
                    print_success(f"پروسس {proc.info['pid']} متوقف شد")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                pass
        
        if killed > 0:
            print_success(f"{killed} پروسس قدیمی متوقف شد")
            time.sleep(2)
        else:
            print_success("هیچ پروسس قدیمی یافت نشد")
        
        return True
    except ImportError:
        print_warning("psutil نصب نیست - بررسی پروسس‌ها غیرفعال است")
        return False
    except Exception as e:
        print_error(f"خطا در بررسی پروسس‌ها: {e}")
        return False

def cleanup_sessions():
    """پاکسازی session های قفل شده"""
    print_header("پاکسازی Session های قفل شده")
    
    journal_files = glob.glob("*.session-journal")
    
    if journal_files:
        print_warning(f"{len(journal_files)} session قفل شده یافت شد")
        
        for journal_file in journal_files:
            try:
                os.remove(journal_file)
                print_success(f"حذف شد: {journal_file}")
                
                session_file = journal_file.replace("-journal", "")
                if os.path.exists(session_file):
                    file_age = time.time() - os.path.getmtime(session_file)
                    if file_age > 60:  # بیشتر از 1 دقیقه
                        os.remove(session_file)
                        print_success(f"حذف شد: {session_file}")
                    else:
                        print_warning(f"نگه داشته شد: {session_file} (تازه است)")
            except Exception as e:
                print_error(f"خطا در حذف {journal_file}: {e}")
        
        print_success("پاکسازی session ها تمام شد")
        time.sleep(0.5)
    else:
        print_success("هیچ session قفل شده‌ای یافت نشد")

def check_files():
    """بررسی فایل‌های ضروری"""
    print_header("بررسی فایل‌های ضروری")
    
    required_files = ['.env', 'bot.py', 'config.py']
    all_exist = True
    
    for file in required_files:
        if os.path.exists(file):
            print_success(f"{file} موجود است")
        else:
            print_error(f"{file} یافت نشد!")
            all_exist = False
    
    return all_exist

def create_directories():
    """ساخت پوشه‌های ضروری"""
    print_header("بررسی پوشه‌ها")
    
    dirs = ['logs', 'downloads']
    for dir_name in dirs:
        os.makedirs(dir_name, exist_ok=True)
        print_success(f"{dir_name}/ آماده است")

def run_bot():
    """اجرای ربات"""
    print_header("شروع ربات")
    print()
    
    try:
        # اجرای bot.py
        result = subprocess.run([sys.executable, 'bot.py'], check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n⏹️ ربات توسط کاربر متوقف شد")
        return 0
    except Exception as e:
        print_error(f"خطا در اجرای ربات: {e}")
        return 1

def main():
    print()
    print("=" * 70)
    print("🚀 راه‌اندازی ربات تلگرام")
    print("=" * 70)
    print()
    
    # 1. بررسی venv
    check_venv()
    print()
    
    # 2. توقف پروسس‌های قدیمی
    kill_old_processes()
    print()
    
    # 3. پاکسازی sessions
    cleanup_sessions()
    print()
    
    # 4. بررسی فایل‌ها
    if not check_files():
        print()
        print_error("فایل‌های ضروری یافت نشد!")
        return 1
    print()
    
    # 5. ساخت پوشه‌ها
    create_directories()
    print()
    
    # 6. اجرای ربات
    exit_code = run_bot()
    
    # نتیجه
    print()
    print("=" * 70)
    if exit_code == 0:
        print_success("ربات با موفقیت خاتمه یافت")
    else:
        print_error(f"ربات با خطا خاتمه یافت (Exit Code: {exit_code})")
        print()
        print("💡 برای بررسی خطا:")
        print("   - Windows: type logs\\bot.log")
        print("   - Linux: cat logs/bot.log")
    print("=" * 70)
    
    return exit_code

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⏹️ متوقف شد")
        sys.exit(0)
