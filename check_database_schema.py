#!/usr/bin/env python3
"""
بررسی ساختار دیتابیس و جداول موجود
"""

import sqlite3
import os

def check_database_schema():
    """بررسی ساختار دیتابیس"""
    
    db_path = os.path.join("plugins", "bot_database.db")
    
    if not os.path.exists(db_path):
        print(f"❌ فایل دیتابیس {db_path} وجود ندارد")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # دریافت لیست جداول
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print("📋 جداول موجود در دیتابیس:")
        print("-" * 40)
        
        for table in tables:
            table_name = table[0]
            print(f"\n🔍 جدول: {table_name}")
            
            # دریافت ساختار جدول
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            if columns:
                print("   ستون‌ها:")
                for col in columns:
                    col_id, col_name, col_type, not_null, default_val, pk = col
                    nullable = "NOT NULL" if not_null else "NULL"
                    primary = " (PRIMARY KEY)" if pk else ""
                    default = f" DEFAULT {default_val}" if default_val else ""
                    print(f"     - {col_name}: {col_type} {nullable}{default}{primary}")
            else:
                print("   هیچ ستونی یافت نشد")
            
            # شمارش رکوردها
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"   تعداد رکوردها: {count}")
        
        conn.close()
        print("\n✅ بررسی دیتابیس تمام شد")
        
    except sqlite3.Error as e:
        print(f"❌ خطا در بررسی دیتابیس: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("🔍 بررسی ساختار دیتابیس")
    print("=" * 50)
    check_database_schema()