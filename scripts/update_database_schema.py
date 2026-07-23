#!/usr/bin/env python3
"""
به‌روزرسانی ساختار جدول jobs در دیتابیس
"""

import sqlite3
import os

def update_jobs_table():
    """به‌روزرسانی ساختار جدول jobs"""
    
    db_path = os.path.join("plugins", "bot_database.db")
    
    if not os.path.exists(db_path):
        print(f"❌ فایل دیتابیس {db_path} وجود ندارد")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 بررسی ساختار فعلی جدول jobs...")
        
        # بررسی ساختار فعلی
        cursor.execute("PRAGMA table_info(jobs);")
        current_columns = cursor.fetchall()
        
        print("ستون‌های فعلی:")
        for col in current_columns:
            print(f"  - {col[1]}: {col[2]}")
        
        # بررسی وجود ستون‌های مورد نیاز
        column_names = [col[1] for col in current_columns]
        
        missing_columns = []
        if 'url' not in column_names:
            missing_columns.append(('url', 'TEXT NOT NULL DEFAULT ""'))
        if 'format_id' not in column_names:
            missing_columns.append(('format_id', 'TEXT NOT NULL DEFAULT ""'))
        if 'progress' not in column_names:
            missing_columns.append(('progress', 'INTEGER NOT NULL DEFAULT 0'))
        
        if missing_columns:
            print(f"\n🔧 اضافه کردن {len(missing_columns)} ستون جدید...")
            
            for col_name, col_def in missing_columns:
                try:
                    cursor.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_def}")
                    print(f"✅ ستون {col_name} اضافه شد")
                except sqlite3.Error as e:
                    print(f"❌ خطا در اضافه کردن ستون {col_name}: {e}")
            
            conn.commit()
            print("✅ تغییرات ذخیره شد")
        else:
            print("✅ همه ستون‌های مورد نیاز موجود است")
        
        # نمایش ساختار جدید
        print("\n🔍 ساختار جدید جدول jobs:")
        cursor.execute("PRAGMA table_info(jobs);")
        new_columns = cursor.fetchall()
        
        for col in new_columns:
            col_id, col_name, col_type, not_null, default_val, pk = col
            nullable = "NOT NULL" if not_null else "NULL"
            primary = " (PRIMARY KEY)" if pk else ""
            default = f" DEFAULT {default_val}" if default_val else ""
            print(f"  - {col_name}: {col_type} {nullable}{default}{primary}")
        
        conn.close()
        print("\n✅ به‌روزرسانی جدول jobs تمام شد")
        
    except sqlite3.Error as e:
        print(f"❌ خطا در به‌روزرسانی دیتابیس: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("🔧 به‌روزرسانی ساختار جدول jobs")
    print("=" * 50)
    update_jobs_table()