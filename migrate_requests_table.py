#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اسکریپت Migration برای جدول requests
این اسکریپت جدول requests رو میسازه اگر وجود نداشته باشه
"""

import sys
import io
# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from plugins.db_wrapper import DB
from datetime import datetime

print("=" * 60)
print("🔄 Migration جدول requests")
print("=" * 60)
print(f"⏰ زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

try:
    # اتصال به دیتابیس
    print("📊 اتصال به دیتابیس...")
    db = DB()
    print(f"✅ متصل شد به: {db.db_type}\n")
    
    # بررسی وجود جدول
    print("🔍 بررسی وجود جدول requests...")
    
    if db.db_type == 'mysql':
        db.cursor.execute("SHOW TABLES LIKE 'requests'")
        table_exists = db.cursor.fetchone() is not None
    else:
        db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='requests'")
        table_exists = db.cursor.fetchone() is not None
    
    if table_exists:
        print("✅ جدول requests وجود دارد")
        
        # بررسی تعداد رکوردها
        db.cursor.execute("SELECT COUNT(*) FROM requests")
        count = db.cursor.fetchone()[0]
        print(f"📊 تعداد رکوردها: {count}")
        
        if count == 0:
            print("\n⚠️  جدول خالی است!")
            print("💡 بعد از اجرای ربات، درخواست‌ها ثبت خواهند شد")
        else:
            print("\n✅ جدول دارای داده است")
            
            # نمایش آمار
            print("\n📊 آمار پلتفرم‌ها:")
            for platform in ['youtube', 'aparat', 'adult', 'universal']:
                if db.db_type == 'mysql':
                    db.cursor.execute("SELECT COUNT(*) FROM requests WHERE platform = %s", (platform,))
                else:
                    db.cursor.execute("SELECT COUNT(*) FROM requests WHERE platform = ?", (platform,))
                count = db.cursor.fetchone()[0]
                print(f"  {platform}: {count}")
    
    else:
        print("⚠️  جدول requests وجود ندارد")
        print("🔨 در حال ساخت جدول...\n")
        
        if db.db_type == 'mysql':
            # MySQL
            db.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT UNSIGNED NOT NULL,
                    platform VARCHAR(64) NOT NULL,
                    url TEXT,
                    status VARCHAR(32) NOT NULL,
                    created_at VARCHAR(32) NOT NULL,
                    completed_at VARCHAR(32),
                    processing_time DOUBLE,
                    error_message TEXT,
                    INDEX idx_requests_platform (platform),
                    INDEX idx_requests_created_at (created_at),
                    INDEX idx_requests_status (status)
                ) CHARACTER SET `utf8` COLLATE `utf8_general_ci`
                """
            )
            db.mydb.commit()
            print("✅ جدول requests ساخته شد (MySQL)")
            
        else:
            # SQLite
            db.cursor.execute(
                """CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    platform TEXT NOT NULL,
                    url TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    processing_time REAL,
                    error_message TEXT
                )"""
            )
            
            # ساخت index ها
            db.cursor.execute(
                """CREATE INDEX IF NOT EXISTS idx_requests_platform 
                ON requests(platform)"""
            )
            db.cursor.execute(
                """CREATE INDEX IF NOT EXISTS idx_requests_created_at 
                ON requests(created_at)"""
            )
            db.cursor.execute(
                """CREATE INDEX IF NOT EXISTS idx_requests_status 
                ON requests(status)"""
            )
            
            db.mydb.commit()
            print("✅ جدول requests ساخته شد (SQLite)")
            print("✅ Index ها ساخته شدند")
    
    # بررسی ساختار جدول
    print("\n📋 ساختار جدول:")
    
    if db.db_type == 'mysql':
        db.cursor.execute("DESCRIBE requests")
        columns = db.cursor.fetchall()
        for col in columns:
            print(f"  {col[0]}: {col[1]}")
    else:
        db.cursor.execute("PRAGMA table_info(requests)")
        columns = db.cursor.fetchall()
        for col in columns:
            print(f"  {col[1]}: {col[2]}")
    
    # تست توابع
    print("\n🧪 تست توابع آماری:")
    
    try:
        total = db.get_total_requests()
        print(f"  ✅ get_total_requests(): {total}")
    except Exception as e:
        print(f"  ❌ get_total_requests(): {e}")
    
    try:
        youtube = db.get_requests_by_platform('youtube')
        print(f"  ✅ get_requests_by_platform('youtube'): {youtube}")
    except Exception as e:
        print(f"  ❌ get_requests_by_platform(): {e}")
    
    try:
        success = db.get_successful_requests()
        print(f"  ✅ get_successful_requests(): {success}")
    except Exception as e:
        print(f"  ❌ get_successful_requests(): {e}")
    
    try:
        failed = db.get_failed_requests()
        print(f"  ✅ get_failed_requests(): {failed}")
    except Exception as e:
        print(f"  ❌ get_failed_requests(): {e}")
    
    print("\n" + "=" * 60)
    print("✅ Migration با موفقیت انجام شد!")
    print("=" * 60)
    print("\n💡 مراحل بعدی:")
    print("  1. ربات را restart کنید")
    print("  2. چند درخواست تست بزنید")
    print("  3. دستور /debugstats را اجرا کنید")
    print("  4. پنل آمار را بررسی کنید")
    print()

except Exception as e:
    print("\n" + "=" * 60)
    print("❌ خطا در Migration!")
    print("=" * 60)
    print(f"\n{str(e)}\n")
    
    import traceback
    traceback.print_exc()
    
    print("\n💡 راهنمایی:")
    print("  1. مطمئن شوید دیتابیس در دسترس است")
    print("  2. بررسی کنید permission ها درست هستند")
    print("  3. config.py را بررسی کنید")
    print()
    
    sys.exit(1)
