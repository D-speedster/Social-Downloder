#!/bin/bash
# تشخیص مشکل Instagram

echo "=========================================="
echo "🔍 تشخیص مشکل Instagram"
echo "=========================================="
echo ""

cd /root/Social-Downloder

echo "1️⃣ بررسی نسخه yt-dlp:"
echo "------------------------------------------"
source venv/bin/activate
yt-dlp --version
echo ""

echo "2️⃣ بررسی وجود cookies:"
echo "------------------------------------------"
if [ -f "instagram_cookies.txt" ]; then
    echo "✅ فایل instagram_cookies.txt وجود دارد"
    echo "📊 تعداد خطوط: $(wc -l < instagram_cookies.txt)"
    echo "📅 تاریخ آخرین تغییر: $(stat -c %y instagram_cookies.txt)"
else
    echo "❌ فایل instagram_cookies.txt وجود ندارد!"
fi
echo ""

echo "3️⃣ تست دانلود با yt-dlp (بدون cookie):"
echo "------------------------------------------"
yt-dlp --no-warnings --skip-download \
    "https://www.instagram.com/p/DQjfEYBDVKE/" \
    2>&1 | head -20
echo ""

echo "4️⃣ تست دانلود با yt-dlp (با cookie):"
echo "------------------------------------------"
if [ -f "instagram_cookies.txt" ]; then
    yt-dlp --no-warnings --skip-download \
        --cookies instagram_cookies.txt \
        "https://www.instagram.com/p/DQjfEYBDVKE/" \
        2>&1 | head -20
else
    echo "⚠️ فایل cookies یافت نشد"
fi
echo ""

echo "5️⃣ بررسی لاگ بات:"
echo "------------------------------------------"
if [ -f "logs/insta_fetch.log" ]; then
    echo "📋 آخرین 10 خط:"
    tail -10 logs/insta_fetch.log
else
    echo "⚠️ فایل لاگ یافت نشد"
fi
echo ""

echo "=========================================="
echo "✅ تشخیص تمام شد"
echo "=========================================="
echo ""
echo "💡 راه‌حل‌های احتمالی:"
echo "  1. بروز کردن yt-dlp: pip install -U yt-dlp"
echo "  2. بروز کردن cookies: export جدید از browser"
echo "  3. صبر کردن (rate-limit): 1-2 ساعت"
echo "  4. تست با لینک دیگه"
echo ""
