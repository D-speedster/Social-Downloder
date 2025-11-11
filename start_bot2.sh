#!/bin/bash

# 🤖 اجرای ربات دوم (Delivery Bot)

echo "=================================="
echo "🚀 Starting Delivery Bot"
echo "=================================="
echo ""

# بررسی فایل .env
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found!"
    echo "💡 Please create .env file from .env.example"
    exit 1
fi

# بررسی Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python3 not found!"
    exit 1
fi

# اجرای ربات
echo "⏳ Starting bot2.py..."
python3 bot2.py
