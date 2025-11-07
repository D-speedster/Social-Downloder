#!/usr/bin/env python3
"""
اجرای ربات با debug mode کامل
این فایل تمام خطاها را catch می‌کند و نشان می‌دهد
"""
import sys
import traceback
import asyncio

print("=" * 70)
print("🐛 DEBUG MODE - شروع ربات با حالت دیباگ کامل")
print("=" * 70)

try:
    # Import bot.py
    print("\n📦 در حال import ماژول‌ها...")
    import bot
    
    print("✅ تمام imports موفق بود")
    print("\n🚀 در حال اجرای main()...")
    
    # اجرای main
    asyncio.run(bot.main())
    
except KeyboardInterrupt:
    print("\n\n⏹️ ربات توسط کاربر متوقف شد (Ctrl+C)")
    sys.exit(0)
    
except Exception as e:
    print("\n\n" + "=" * 70)
    print("💥 کرش شناسایی شد!")
    print("=" * 70)
    
    print(f"\n❌ نوع خطا: {type(e).__name__}")
    print(f"❌ پیام خطا: {e}")
    
    print("\n📋 Stack Trace کامل:")
    print("-" * 70)
    traceback.print_exc()
    print("-" * 70)
    
    print("\n🔍 اطلاعات اضافی:")
    print(f"   • Python: {sys.version}")
    print(f"   • Platform: {sys.platform}")
    
    # بررسی خطاهای رایج
    error_str = str(e).lower()
    
    if "token" in error_str or "unauthorized" in error_str:
        print("\n💡 احتمالاً مشکل در BOT_TOKEN است:")
        print("   1. بررسی کنید که BOT_TOKEN در .env صحیح است")
        print("   2. توکن را از @BotFather دوباره بگیرید")
        
    elif "api_id" in error_str or "api_hash" in error_str:
        print("\n💡 احتمالاً مشکل در API_ID یا API_HASH است:")
        print("   1. بررسی کنید که API_ID و API_HASH در .env صحیح است")
        print("   2. از https://my.telegram.org دوباره بگیرید")
        
    elif "connection" in error_str or "network" in error_str:
        print("\n💡 احتمالاً مشکل در اتصال شبکه است:")
        print("   1. بررسی اتصال اینترنت")
        print("   2. بررسی فایروال")
        print("   3. اگر از پروکسی استفاده می‌کنید، تنظیمات را چک کنید")
        
    elif "module" in error_str or "import" in error_str:
        print("\n💡 احتمالاً یک ماژول نصب نشده:")
        print("   1. اجرا کنید: pip install -r requirements.txt")
        print("   2. بررسی کنید که virtual environment فعال است")
        
    elif "permission" in error_str or "access" in error_str:
        print("\n💡 احتمالاً مشکل دسترسی فایل است:")
        print("   1. بررسی دسترسی‌های پوشه")
        print("   2. اجرا کنید: chmod +x bot.py")
        
    else:
        print("\n💡 برای یافتن مشکل:")
        print("   1. لاگ را بررسی کنید: cat logs/bot.log")
        print("   2. تست ساده را اجرا کنید: python test_bot_startup.py")
        print("   3. requirements را دوباره نصب کنید")
    
    print("\n📁 فایل‌های لاگ:")
    print("   • logs/bot.log")
    print("   • logs/crash_report.log (اگر وجود دارد)")
    
    sys.exit(1)
