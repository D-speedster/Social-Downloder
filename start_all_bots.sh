#!/bin/bash

# 🤖 اجرای همزمان هر دو ربات با screen

echo "=================================="
echo "🚀 Starting All Bots"
echo "=================================="
echo ""

# بررسی screen
if ! command -v screen &> /dev/null; then
    echo "❌ Error: screen not found!"
    echo "💡 Install screen: sudo apt-get install screen"
    exit 1
fi

# بررسی فایل .env
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found!"
    echo "💡 Please create .env file from .env.example"
    exit 1
fi

# اجرای ربات اصلی
echo "🤖 Starting Main Bot in screen session 'mainbot'..."
screen -dmS mainbot bash -c "python3 bot.py"
sleep 2

# اجرای ربات دوم
echo "🤖 Starting Delivery Bot in screen session 'deliverybot'..."
screen -dmS deliverybot bash -c "python3 bot2.py"
sleep 2

# نمایش وضعیت
echo ""
echo "✅ Both bots started successfully!"
echo ""
echo "📋 Screen sessions:"
screen -ls
echo ""
echo "💡 Commands:"
echo "  - View main bot: screen -r mainbot"
echo "  - View delivery bot: screen -r deliverybot"
echo "  - Detach from screen: Ctrl+A, D"
echo "  - Stop bot: screen -X -S mainbot quit"
echo ""
