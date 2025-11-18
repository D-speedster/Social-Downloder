#!/bin/bash
# بررسی خطاهای سرور

echo "=========================================="
echo "📊 بررسی خطاهای دانلود"
echo "=========================================="
echo ""

cd /root/Social-Downloder
source venv/bin/activate

python3 check_errors.py

echo ""
echo "=========================================="
echo "📋 لاگ‌های اخیر:"
echo "=========================================="
echo ""

echo "🔴 YouTube (آخرین 5 خط):"
tail -5 logs/youtube_handler.log 2>/dev/null || echo "  لاگ یافت نشد"
echo ""

echo "🔴 Universal (آخرین 5 خط):"
tail -5 logs/universal_downloader.log 2>/dev/null || echo "  لاگ یافت نشد"
echo ""

echo "🔴 Instagram (آخرین 5 خط):"
tail -5 logs/insta_fetch.log 2>/dev/null || echo "  لاگ یافت نشد"
echo ""

echo "=========================================="
echo "✅ بررسی تمام شد"
echo "=========================================="
