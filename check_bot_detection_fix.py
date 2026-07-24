#!/usr/bin/env python3
"""
بررسی سریع اینکه آیا fallback strategy در کد موجود است یا خیر
"""

import sys

def check_files():
    """بررسی وجود تغییرات در فایل‌ها"""
    
    print("="*60)
    print("بررسی وجود fallback strategy برای bot detection")
    print("="*60 + "\n")
    
    checks_passed = 0
    total_checks = 0
    
    # بررسی 1: youtube_downloader.py
    print("1. بررسی youtube_downloader.py...")
    total_checks += 1
    try:
        with open('plugins/youtube_downloader.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_strings = [
            'use_bot_bypass',
            'sign in',
            'player_client',
            'remote_components'
        ]
        
        missing = []
        for s in required_strings:
            if s not in content:
                missing.append(s)
        
        if not missing:
            print("   ✅ fallback strategy موجود است")
            checks_passed += 1
        else:
            print(f"   ❌ کد قدیمی است! موارد زیر یافت نشد: {missing}")
            print("   لطفاً git pull origin main را اجرا کنید")
            
    except FileNotFoundError:
        print("   ❌ فایل یافت نشد!")
    except Exception as e:
        print(f"   ❌ خطا: {e}")
    
    # بررسی 2: youtube_handler.py
    print("\n2. بررسی youtube_handler.py...")
    total_checks += 1
    try:
        with open('plugins/youtube_handler.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'ydl_opts_fallback' in content and 'ydl_opts_default' in content:
            print("   ✅ fallback strategy موجود است")
            checks_passed += 1
        else:
            print("   ❌ کد قدیمی است!")
            print("   لطفاً git pull origin main را اجرا کنید")
            
    except FileNotFoundError:
        print("   ❌ فایل یافت نشد!")
    except Exception as e:
        print(f"   ❌ خطا: {e}")
    
    # نتیجه
    print("\n" + "="*60)
    print(f"نتیجه: {checks_passed}/{total_checks} بررسی موفق")
    print("="*60 + "\n")
    
    if checks_passed == total_checks:
        print("✅ کد به‌روز است و fallback strategy موجود است!")
        print("\nاگر هنوز خطا می‌گیرید، لاگ را بررسی کنید:")
        print("   tail -f logs/youtube_downloader.log")
        return True
    else:
        print("❌ کد قدیمی است!")
        print("\nلطفاً دستورات زیر را اجرا کنید:")
        print("   git pull origin main")
        print("   pkill -f bot.py")
        print("   python bot.py")
        return False


if __name__ == "__main__":
    success = check_files()
    sys.exit(0 if success else 1)
