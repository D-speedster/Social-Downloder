#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست عملکرد ربات برای شناسایی باگ‌های موجود
"""

import asyncio
from pyrogram import Client
import config
from dotenv import load_dotenv
import time

load_dotenv()

# تنظیمات تست
TEST_CHAT_ID = None  # باید با chat_id واقعی جایگزین شود
TEST_YOUTUBE_LINK = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # لینک تست

async def test_bot_functionality():
    """
    تست کامل عملکرد ربات
    """
    print("🔍 شروع تست عملکرد ربات...")
    
    # ایجاد کلاینت تست
    test_client = Client(
        "test_session",
        bot_token=config.BOT_TOKEN,
        api_id=config.APP_ID,
        api_hash=config.API_HASH
    )
    
    async with test_client:
        print("✅ اتصال به تلگرام برقرار شد")
        
        # دریافت اطلاعات ربات
        me = await test_client.get_me()
        print(f"🤖 نام ربات: {me.first_name}")
        print(f"🆔 آیدی ربات: @{me.username}")
        
        if TEST_CHAT_ID:
            print(f"\n📤 ارسال لینک تست به چت {TEST_CHAT_ID}...")
            
            # ارسال دستور /start
            await test_client.send_message(TEST_CHAT_ID, "/start")
            await asyncio.sleep(2)
            
            # ارسال لینک یوتیوب
            await test_client.send_message(TEST_CHAT_ID, TEST_YOUTUBE_LINK)
            
            print("✅ لینک تست ارسال شد")
            print("⏳ منتظر پاسخ ربات...")
            
            # منتظر ماندن برای مشاهده پاسخ
            await asyncio.sleep(10)
            
        else:
            print("⚠️ TEST_CHAT_ID تنظیم نشده - تست خودکار امکان‌پذیر نیست")
            print("💡 برای تست دستی، لینک زیر را در ربات ارسال کنید:")
            print(f"🔗 {TEST_YOUTUBE_LINK}")

if __name__ == "__main__":
    print("🚀 اجرای تست ربات...")
    asyncio.run(test_bot_functionality())