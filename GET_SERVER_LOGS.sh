#!/bin/bash
# اسکریپت دریافت لاگ‌های مهم از سرور برای آنالیز

echo "📊 دریافت لاگ‌های مهم از سرور..."
echo "=================================="

# تاریخ امروز
TODAY=$(date +%Y-%m-%d)

echo ""
echo "1️⃣ آمار کلی سیستم (آخرین 100 خط)"
echo "-----------------------------------"
tail -n 100 logs/bot.log

echo ""
echo "2️⃣ عملکرد YouTube (آخرین 50 خط)"
echo "-----------------------------------"
tail -n 50 logs/youtube_callback.log

echo ""
echo "3️⃣ سرعت دانلود YouTube (فقط موارد موفق)"
echo "-----------------------------------"
grep "Download completed" logs/youtube_downloader.log | tail -n 20

echo ""
echo "4️⃣ خطاهای مهم (آخرین 30 خط)"
echo "-----------------------------------"
grep -i "error\|exception\|failed" logs/bot.log | tail -n 30

echo ""
echo "5️⃣ آمار کاربران جدید (امروز)"
echo "-----------------------------------"
grep "New user.*registering" logs/start_main.log | grep "$TODAY" | wc -l

echo ""
echo "6️⃣ تعداد درخواست‌های موفق (آخرین ساعت)"
echo "-----------------------------------"
grep "Total:" logs/youtube_callback.log | tail -n 20

echo ""
echo "7️⃣ وضعیت Health Monitor"
echo "-----------------------------------"
tail -n 20 logs/health_monitor.log

echo ""
echo "8️⃣ استفاده از حافظه و CPU"
echo "-----------------------------------"
ps aux | grep python | grep -v grep

echo ""
echo "9️⃣ فضای دیسک"
echo "-----------------------------------"
df -h | grep -E "Filesystem|/$"

echo ""
echo "🔟 آمار فایل‌های موقت"
echo "-----------------------------------"
du -sh downloads/ 2>/dev/null || echo "پوشه downloads وجود ندارد"
ls -lh downloads/ 2>/dev/null | wc -l || echo "0"

echo ""
echo "=================================="
echo "✅ دریافت لاگ‌ها تکمیل شد!"
