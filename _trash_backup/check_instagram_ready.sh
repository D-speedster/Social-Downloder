#!/bin/bash
# بررسی آمادگی Instagram

echo "========================================================================"
echo "📸 بررسی آمادگی Instagram"
echo "========================================================================"
echo ""

# بررسی فایل‌ها
echo "📁 بررسی فایل‌ها..."
if [ -f "plugins/insta_fetch.py" ]; then
    echo "  ✅ plugins/insta_fetch.py"
else
    echo "  ❌ plugins/insta_fetch.py - فایل وجود ندارد!"
    exit 1
fi

if [ -f "plugins/admin_statistics.py" ]; then
    echo "  ✅ plugins/admin_statistics.py"
else
    echo "  ❌ plugins/admin_statistics.py"
    exit 1
fi

if grep -q "import plugins.insta_fetch" main.py; then
    echo "  ✅ main.py (import اضافه شده)"
else
    echo "  ❌ main.py (import اضافه نشده!)"
    exit 1
fi

echo ""
echo "🔍 بررسی دیتابیس..."

# اجرای Python script
python3 << 'EOF'
from plugins.db_wrapper import DB
from plugins.admin_statistics import StatisticsCalculator

try:
    db = DB()
    print(f"  ✅ اتصال به دیتابیس: {db.db_type}")
    
    # بررسی جدول
    if db.db_type == 'mysql':
        db.cursor.execute("SHOW TABLES LIKE 'requests'")
    else:
        db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='requests'")
    
    if db.cursor.fetchone():
        print("  ✅ جدول requests موجود است")
        
        # بررسی Instagram
        instagram_count = db.get_requests_by_platform('instagram')
        print(f"  📊 Instagram: {instagram_count} درخواست")
        
        # تست آمار
        calc = StatisticsCalculator(db)
        stats = calc.calculate_requests_stats()
        
        if 'instagram' in stats:
            print("  ✅ Instagram در آمار موجود است")
        else:
            print("  ❌ Instagram در آمار موجود نیست!")
            exit(1)
    else:
        print("  ❌ جدول requests وجود ندارد!")
        print("  💡 اجرا کنید: python3 tools/migrate_requests_table.py")
        exit(1)
        
except Exception as e:
    print(f"  ❌ خطا: {e}")
    exit(1)
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================================================"
    echo "✅ همه چیز آماده است!"
    echo "========================================================================"
    echo ""
    echo "💡 مراحل بعدی:"
    echo "  1. Restart ربات: sudo systemctl restart bot"
    echo "  2. تست: لینک Instagram بفرستید"
    echo "  3. بررسی: /debugstats"
    echo ""
else
    echo ""
    echo "========================================================================"
    echo "❌ مشکلی وجود دارد!"
    echo "========================================================================"
    echo ""
    exit 1
fi
