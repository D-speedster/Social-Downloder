#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اسکریپت بررسی وضعیت دیتابیس
این اسکریپت وضعیت کامل دیتابیس رو نشون میده
"""

import sys
import io
# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from plugins.db_wrapper import DB
from datetime import datetime
import os

print("=" * 70)
print("📊 بررسی وضعیت دیتابیس")
print("=" * 70)
print(f"⏰ زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

try:
    # اتصال به دیتابیس
    print("🔌 اتصال به دیتابیس...")
    db = DB()
    print(f"✅ نوع دیتابیس: {db.db_type}")
    
    # اطلاعات فایل (برای SQLite)
    if db.db_type == 'sqlite':
        db_file = 'database.db'  # یا مسیر دیگه
        if os.path.exists(db_file):
            size = os.path.getsize(db_file)
            size_mb = size / (1024 * 1024)
            print(f"📁 فایل دیتابیس: {db_file}")
            print(f"📏 حجم: {size_mb:.2f} MB ({size:,} bytes)")
        else:
            print(f"⚠️  فایل دیتابیس پیدا نشد: {db_file}")
    
    print("\n" + "=" * 70)
    print("📋 لیست جداول")
    print("=" * 70)
    
    # لیست جداول
    if db.db_type == 'mysql':
        db.cursor.execute("SHOW TABLES")
        tables = [row[0] for row in db.cursor.fetchall()]
    else:
        db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in db.cursor.fetchall()]
    
    print(f"\n📊 تعداد جداول: {len(tables)}")
    for table in tables:
        print(f"  • {table}")
    
    # بررسی جدول requests
    print("\n" + "=" * 70)
    print("🔍 بررسی جدول requests")
    print("=" * 70)
    
    if 'requests' in tables:
        print("\n✅ جدول requests وجود دارد")
        
        # تعداد کل رکوردها
        db.cursor.execute("SELECT COUNT(*) FROM requests")
        total = db.cursor.fetchone()[0]
        print(f"\n📊 تعداد کل رکوردها: {total:,}")
        
        if total > 0:
            # آمار پلتفرم‌ها
            print("\n📱 آمار پلتفرم‌ها:")
            platforms = ['youtube', 'aparat', 'adult', 'universal', 'instagram']
            for platform in platforms:
                if db.db_type == 'mysql':
                    db.cursor.execute("SELECT COUNT(*) FROM requests WHERE platform = %s", (platform,))
                else:
                    db.cursor.execute("SELECT COUNT(*) FROM requests WHERE platform = ?", (platform,))
                count = db.cursor.fetchone()[0]
                if count > 0:
                    percentage = (count / total) * 100
                    print(f"  • {platform:12} : {count:6,} ({percentage:5.1f}%)")
            
            # آمار وضعیت‌ها
            print("\n📊 آمار وضعیت‌ها:")
            statuses = ['pending', 'success', 'failed']
            for status in statuses:
                if db.db_type == 'mysql':
                    db.cursor.execute("SELECT COUNT(*) FROM requests WHERE status = %s", (status,))
                else:
                    db.cursor.execute("SELECT COUNT(*) FROM requests WHERE status = ?", (status,))
                count = db.cursor.fetchone()[0]
                if count > 0:
                    percentage = (count / total) * 100
                    print(f"  • {status:12} : {count:6,} ({percentage:5.1f}%)")
            
            # آخرین درخواست‌ها
            print("\n📝 آخرین 5 درخواست:")
            if db.db_type == 'mysql':
                db.cursor.execute("""
                    SELECT id, user_id, platform, status, created_at 
                    FROM requests 
                    ORDER BY id DESC 
                    LIMIT 5
                """)
            else:
                db.cursor.execute("""
                    SELECT id, user_id, platform, status, created_at 
                    FROM requests 
                    ORDER BY id DESC 
                    LIMIT 5
                """)
            
            rows = db.cursor.fetchall()
            for row in rows:
                print(f"  ID {row[0]:4} | User {row[1]:10} | {row[2]:10} | {row[3]:8} | {row[4]}")
            
            # اولین درخواست
            print("\n📝 اولین درخواست:")
            if db.db_type == 'mysql':
                db.cursor.execute("""
                    SELECT id, user_id, platform, status, created_at 
                    FROM requests 
                    ORDER BY id ASC 
                    LIMIT 1
                """)
            else:
                db.cursor.execute("""
                    SELECT id, user_id, platform, status, created_at 
                    FROM requests 
                    ORDER BY id ASC 
                    LIMIT 1
                """)
            
            row = db.cursor.fetchone()
            if row:
                print(f"  ID {row[0]:4} | User {row[1]:10} | {row[2]:10} | {row[3]:8} | {row[4]}")
        
        else:
            print("\n⚠️  جدول خالی است!")
            print("💡 بعد از اجرای ربات و ارسال درخواست، داده‌ها ثبت خواهند شد")
    
    else:
        print("\n❌ جدول requests وجود ندارد!")
        print("💡 برای ساخت جدول، اسکریپت migrate_requests_table.py را اجرا کنید:")
        print("   python3 migrate_requests_table.py")
    
    # بررسی جدول users
    print("\n" + "=" * 70)
    print("👥 بررسی جدول users")
    print("=" * 70)
    
    if 'users' in tables:
        db.cursor.execute("SELECT COUNT(*) FROM users")
        user_count = db.cursor.fetchone()[0]
        print(f"\n✅ تعداد کاربران: {user_count:,}")
        
        # آخرین کاربر (ساده شده)
        if user_count > 0:
            try:
                db.cursor.execute("SELECT user_id FROM users LIMIT 1")
                row = db.cursor.fetchone()
                if row:
                    print(f"👤 نمونه user_id: {row[0]}")
            except Exception:
                pass  # اگر خطا داد، نادیده بگیر
    else:
        print("\n⚠️  جدول users وجود ندارد")
    
    # تست توابع آماری
    print("\n" + "=" * 70)
    print("🧪 تست توابع آماری")
    print("=" * 70)
    
    tests = [
        ("get_total_requests", lambda: db.get_total_requests()),
        ("get_requests_by_platform('youtube')", lambda: db.get_requests_by_platform('youtube')),
        ("get_requests_by_platform('aparat')", lambda: db.get_requests_by_platform('aparat')),
        ("get_requests_by_platform('adult')", lambda: db.get_requests_by_platform('adult')),
        ("get_requests_by_platform('universal')", lambda: db.get_requests_by_platform('universal')),
        ("get_successful_requests", lambda: db.get_successful_requests()),
        ("get_failed_requests", lambda: db.get_failed_requests()),
        ("get_avg_processing_time", lambda: db.get_avg_processing_time()),
    ]
    
    print()
    for test_name, test_func in tests:
        try:
            result = test_func()
            if isinstance(result, float):
                print(f"  ✅ {test_name:40} : {result:.2f}")
            else:
                print(f"  ✅ {test_name:40} : {result:,}")
        except Exception as e:
            print(f"  ❌ {test_name:40} : {str(e)[:30]}")
    
    # خلاصه
    print("\n" + "=" * 70)
    print("📊 خلاصه")
    print("=" * 70)
    
    summary = []
    
    if 'requests' in tables:
        db.cursor.execute("SELECT COUNT(*) FROM requests")
        req_count = db.cursor.fetchone()[0]
        if req_count > 0:
            summary.append(f"✅ جدول requests: {req_count:,} رکورد")
        else:
            summary.append("⚠️  جدول requests خالی است")
    else:
        summary.append("❌ جدول requests وجود ندارد")
    
    if 'users' in tables:
        db.cursor.execute("SELECT COUNT(*) FROM users")
        user_count = db.cursor.fetchone()[0]
        summary.append(f"✅ جدول users: {user_count:,} کاربر")
    
    print()
    for item in summary:
        print(f"  {item}")
    
    print("\n" + "=" * 70)
    print("✅ بررسی تکمیل شد")
    print("=" * 70)
    print()

except Exception as e:
    print("\n" + "=" * 70)
    print("❌ خطا در بررسی دیتابیس!")
    print("=" * 70)
    print(f"\n{str(e)}\n")
    
    import traceback
    traceback.print_exc()
    print()
