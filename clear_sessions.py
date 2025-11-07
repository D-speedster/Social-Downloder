#!/usr/bin/env python3
"""
پاکسازی تمام session ها و cache توکن
استفاده: python clear_sessions.py
"""
import os
import glob

print("=" * 70)
print("🧹 پاکسازی Session ها و Cache")
print("=" * 70)

# 1. حذف session ها (در پوشه فعلی و downloads)
session_files = glob.glob("*.session*") + glob.glob("downloads/*.session*")
if session_files:
    print(f"\n📁 {len(session_files)} فایل session یافت شد:")
    for f in session_files:
        print(f"   - {f}")
    
    confirm = input("\n⚠️ آیا می‌خواهید تمام session ها را حذف کنید؟ (yes/no): ")
    if confirm.lower() in ['yes', 'y', 'بله']:
        for f in session_files:
            try:
                os.remove(f)
                print(f"✅ حذف شد: {f}")
            except Exception as e:
                print(f"❌ خطا در حذف {f}: {e}")
        print("\n✅ تمام session ها پاک شدند")
    else:
        print("\n⏭️ لغو شد")
else:
    print("\n✅ هیچ session یافت نشد")

# 2. حذف cache توکن
token_cache = ".token_cache"
if os.path.exists(token_cache):
    print(f"\n📁 فایل cache توکن یافت شد: {token_cache}")
    try:
        os.remove(token_cache)
        print(f"✅ حذف شد: {token_cache}")
    except Exception as e:
        print(f"❌ خطا در حذف {token_cache}: {e}")
else:
    print("\n✅ هیچ cache توکن یافت نشد")

print("\n" + "=" * 70)
print("✅ پاکسازی تمام شد!")
print("=" * 70)
print("\n💡 حالا می‌توانید ربات را اجرا کنید:")
print("   python start_bot.py")
print("=" * 70)
