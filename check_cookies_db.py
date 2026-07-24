"""بررسی کوکی‌های موجود در دیتابیس"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from plugins.db_wrapper import DB

db = DB()
cookies = db.cursor.execute('SELECT id, name, status, use_count, fail_count FROM cookies LIMIT 10').fetchall()

print("=" * 70)
print("🍪 کوکی‌های موجود در دیتابیس:")
print("=" * 70)

if cookies:
    for c in cookies:
        print(f"ID: {c[0]} | Name: {c[1]} | Status: {c[2]} | Use: {c[3]} | Fail: {c[4]}")
else:
    print("❌ هیچ کوکی در دیتابیس وجود ندارد!")
    print("\n💡 برای اضافه کردن کوکی:")
    print("   1. از پنل ادمین استفاده کنید: /admin → مدیریت کوکی")
    print("   2. یا از test_add_cookie.py استفاده کنید")

print("=" * 70)
