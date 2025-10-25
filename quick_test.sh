#!/bin/bash

echo "🔍 تست سریع تنظیمات ربات"
echo "================================"

# بررسی فایل‌های تغییر یافته
echo ""
echo "📁 بررسی فایل‌های تغییر یافته:"

if grep -q "workers.*32" bot.py; then
    echo "✅ bot.py - workers افزایش یافته"
else
    echo "❌ bot.py - workers افزایش نیافته"
fi

if grep -q "max_concurrent_transmissions.*16" bot.py; then
    echo "✅ bot.py - max_concurrent_transmissions افزایش یافته"
else
    echo "❌ bot.py - max_concurrent_transmissions افزایش نیافته"
fi

if ! grep -q "supports_streaming.*True" plugins/youtube_callback_query.py; then
    echo "✅ youtube_callback_query.py - supports_streaming حذف شده"
else
    echo "❌ youtube_callback_query.py - supports_streaming هنوز موجود است!"
fi

if grep -q "client.send_video" plugins/youtube_callback_query.py; then
    echo "✅ youtube_callback_query.py - استفاده مستقیم از client.send_video"
else
    echo "❌ youtube_callback_query.py - استفاده مستقیم از client.send_video نیست"
fi

# بررسی سرعت اینترنت
echo ""
echo "🌐 بررسی سرعت اینترنت سرور:"
echo "(این ممکن است چند ثانیه طول بکشد...)"

if command -v speedtest-cli &> /dev/null; then
    speedtest-cli --simple
else
    echo "⚠️ speedtest-cli نصب نیست"
    echo "برای نصب: pip install speedtest-cli"
fi

# بررسی منابع سیستم
echo ""
echo "💻 منابع سیستم:"
echo "CPU Cores: $(nproc)"
echo "RAM Total: $(free -h | awk '/^Mem:/ {print $2}')"
echo "RAM Available: $(free -h | awk '/^Mem:/ {print $7}')"

# بررسی فضای دیسک
echo ""
echo "💾 فضای دیسک:"
df -h | grep -E '^/dev/|Filesystem'

# بررسی پروسس ربات
echo ""
echo "🤖 وضعیت ربات:"
if pgrep -f "main.py" > /dev/null; then
    echo "✅ ربات در حال اجرا است"
    echo "PID: $(pgrep -f main.py)"
else
    echo "❌ ربات در حال اجرا نیست"
fi

echo ""
echo "================================"
echo "✅ تست تکمیل شد"
echo ""
echo "💡 برای ری‌استارت ربات:"
echo "   pkill -f main.py && python3 main.py"