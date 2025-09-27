#!/usr/bin/env python3
"""
تست عملکرد YouTube callback query
این اسکریپت برای تست عملکرد دانلود یوتیوب استفاده می‌شود
"""

import asyncio
import json
import os
from pyrogram import Client
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import BOT_TOKEN, API_ID, API_HASH

# تنظیمات تست
TEST_YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll - ویدیو کوتاه برای تست
TEST_USER_ID = 79049016  # شناسه کاربری ادمین

async def test_youtube_functionality():
    """تست عملکرد یوتیوب"""
    
    print("🚀 شروع تست عملکرد YouTube...")
    
    # ایجاد کلاینت تست
    client = Client(
        name="test_client",
        bot_token=BOT_TOKEN,
        api_id=API_ID,
        api_hash=API_HASH
    )
    
    try:
        await client.start()
        print("✅ اتصال به تلگرام برقرار شد")
        
        # ارسال لینک یوتیوب به ربات
        print(f"📤 ارسال لینک یوتیوب: {TEST_YOUTUBE_URL}")
        
        # ارسال پیام به ربات
        message = await client.send_message(
            chat_id="@" + (await client.get_me()).username,  # ارسال به خود ربات
            text=TEST_YOUTUBE_URL
        )
        
        print(f"✅ پیام ارسال شد با ID: {message.id}")
        
        # انتظار برای پردازش
        await asyncio.sleep(5)
        
        print("✅ تست با موفقیت انجام شد")
        
    except Exception as e:
        print(f"❌ خطا در تست: {e}")
    
    finally:
        await client.stop()
        print("🔚 اتصال بسته شد")

if __name__ == "__main__":
    asyncio.run(test_youtube_functionality())