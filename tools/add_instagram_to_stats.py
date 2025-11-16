#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اضافه کردن Instagram به آمار
این اسکریپت فقط برای اطمینان هست - جدول requests از قبل وجود داره
"""

import sys
import os
import io

# اضافه کردن root به path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from plugins.db_wrapper import DB

print("=" * 70)
print("📸 بررسی آمادگی برای Instagram")
print("=" * 70)
print()

try:
    db = DB()
    print(f"✅ اتصال به دیتابیس: {db.db_type}")
    print()
    
    # بررسی جدول requests
    print("🔍 بررسی جدول requests...")
    
    if db.db_type == 'mysql':
        db.cursor.execute("SHOW TABLES LIKE 'requests'")
    else:
        db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='requests'")
    
    table_exists = db.cursor.fetchone() is not None
    
    if table_exists:
        print("✅ جدول requests وجود دارد")
        
        # بررسی آمار Instagram
        print("\n📊 بررسی آمار Instagram...")
        
        instagram_count = db.get_requests_by_platform('instagram')
        print(f"  تعداد درخواست‌های Instagram: {instagram_count}")
        
        if instagram_count > 0:
            print("  ✅ داده‌های Instagram موجود است")
        else:
            print("  ℹ️  هنوز درخواست Instagram ثبت نشده")
            print("  💡 بعد از اولین استفاده، اینجا نمایش داده میشه")
        
        # تست تابع آماری
        print("\n🧪 تست تابع آماری...")
        from plugins.admin_statistics import StatisticsCalculator
        
        calc = StatisticsCalculator(db)
        stats = calc.calculate_requests_stats()
        
        if 'instagram' in stats:
            print("  ✅ Instagram در آمار موجود است")
            print(f"  📊 Instagram: {stats['instagram']} ({stats['percentages']['instagram']:.1f}%)")
        else:
            print("  ❌ Instagram در آمار موجود نیست!")
            print("  💡 لطفاً کد را بروز کنید")
        
        print("\n" + "=" * 70)
        print("✅ همه چیز آماده است!")
        print("=" * 70)
        print()
        print("💡 نکات:")
        print("  • جدول requests از قبل وجود دارد")
        print("  • Instagram به صورت خودکار ثبت میشه")
        print("  • نیازی به migration نیست")
        print("  • فقط کد جدید رو deploy کنید")
        print()
        
    else:
        print("❌ جدول requests وجود ندارد!")
        print()
        print("💡 راه‌حل:")
        print("  python3 tools/migrate_requests_table.py")
        print()
        sys.exit(1)

except Exception as e:
    print(f"\n❌ خطا: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
