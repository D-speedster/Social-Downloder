#!/bin/bash

# 🚀 اسکریپت نصب خودکار ربات تلگرام
# این اسکریپت تمام وابستگی‌ها را نصب می‌کند

echo "=================================="
echo "🚀 نصب ربات تلگرام"
echo "=================================="
echo ""

# بررسی Python
echo "🐍 بررسی Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✅ $PYTHON_VERSION یافت شد"
else
    echo "❌ Python3 یافت نشد!"
    echo "لطفاً Python 3.8 یا بالاتر را نصب کنید"
    exit 1
fi

# بررسی pip
echo ""
echo "📦 بررسی pip..."
if command -v pip3 &> /dev/null; then
    PIP_VERSION=$(pip3 --version)
    echo "✅ $PIP_VERSION یافت شد"
else
    echo "❌ pip3 یافت نشد!"
    echo "در حال نصب pip..."
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python3 get-pip.py
    rm get-pip.py
fi

# نصب وابستگی‌ها
echo ""
echo "📚 نصب وابستگی‌ها..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ وابستگی‌ها با موفقیت نصب شدند"
else
    echo "❌ خطا در نصب وابستگی‌ها"
    echo "💡 سعی کنید: pip3 install --user -r requirements.txt"
    exit 1
fi

# بررسی نصب python-telegram-bot
echo ""
echo "🤖 بررسی python-telegram-bot..."
python3 -c "import telegram; print('✅ python-telegram-bot نسخه:', telegram.__version__)" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "❌ python-telegram-bot نصب نشد"
    echo "در حال نصب دستی..."
    pip3 install python-telegram-bot>=20.0
fi

# ساخت پوشه‌های لازم
echo ""
echo "📁 ساخت پوشه‌های لازم..."
mkdir -p logs
mkdir -p downloads
mkdir -p data
echo "✅ پوشه‌ها ساخته شدند"

# بررسی فایل .env
echo ""
echo "🔐 بررسی فایل .env..."
if [ -f ".env" ]; then
    echo "✅ فایل .env موجود است"
else
    echo "⚠️  فایل .env یافت نشد"
    if [ -f ".env.example" ]; then
        echo "📋 کپی از .env.example..."
        cp .env.example .env
        echo "✅ فایل .env ساخته شد"
        echo "⚠️  لطفاً توکن‌های خود را در .env وارد کنید"
    else
        echo "❌ فایل .env.example هم یافت نشد!"
    fi
fi

# تنظیم دسترسی‌ها
echo ""
echo "🔒 تنظیم دسترسی‌ها..."
chmod 600 .env 2>/dev/null
chmod +x start_bot.sh 2>/dev/null
chmod +x start_bot2.sh 2>/dev/null
echo "✅ دسترسی‌ها تنظیم شدند"

# بررسی ffmpeg
echo ""
echo "🎬 بررسی ffmpeg..."
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version | head -n1)
    echo "✅ ffmpeg یافت شد"
else
    echo "⚠️  ffmpeg یافت نشد"
    echo "💡 برای دانلود ویدیو، ffmpeg را نصب کنید:"
    echo "   Ubuntu/Debian: sudo apt-get install ffmpeg"
    echo "   CentOS/RHEL: sudo yum install ffmpeg"
fi

# خلاصه نهایی
echo ""
echo "=================================="
echo "✅ نصب با موفقیت انجام شد!"
echo "=================================="
echo ""
echo "📝 مراحل بعدی:"
echo "1. فایل .env را ویرایش کنید و توکن‌ها را وارد کنید"
echo "2. ربات اصلی را اجرا کنید: python3 bot.py"
echo "3. ربات دوم را اجرا کنید: python3 bot2.py"
echo ""
echo "📚 برای اطلاعات بیشتر: cat SERVER_SETUP.md"
echo ""
