#!/usr/bin/env python3
"""
تست ساده اتصال پایروگرام
"""
import asyncio
from pyrogram import Client
import config

async def test_connection():
    print("🔍 شروع تست اتصال پایروگرام...")
    
    # نمایش تنظیمات
    print(f"API_ID: {config.API_ID}")
    print(f"API_HASH: {config.API_HASH[:10]}...")
    print(f"BOT_TOKEN: {config.BOT_TOKEN[:20]}...")
    
    try:
        # ایجاد کلاینت با تنظیمات اتصال
        client_config = {
            "name": "test_bot",
            "api_id": config.API_ID,
            "api_hash": config.API_HASH,
            "bot_token": config.BOT_TOKEN,
            "test_mode": False,
            "ipv6": False,  # غیرفعال کردن IPv6
        }
        
        # اضافه کردن پروکسی در صورت وجود
        if hasattr(config, 'PROXY_HOST') and config.PROXY_HOST:
            proxy_config = {
                "scheme": "socks5",
                "hostname": config.PROXY_HOST,
                "port": config.PROXY_PORT
            }
            if hasattr(config, 'PROXY_USERNAME') and config.PROXY_USERNAME:
                proxy_config["username"] = config.PROXY_USERNAME
                proxy_config["password"] = config.PROXY_PASSWORD
            client_config["proxy"] = proxy_config
            print(f"🔗 استفاده از پروکسی: {config.PROXY_HOST}:{config.PROXY_PORT}")
        
        print("🔌 در حال اتصال...")
        client = Client(**client_config)
        
        async with client:
            me = await client.get_me()
            print(f"✅ اتصال موفق! نام ربات: {me.first_name}")
            print(f"📱 نام کاربری: @{me.username}")
            print(f"🆔 شناسه: {me.id}")
            
            # تست ارسال پیام به خودم (اختیاری)
            try:
                await client.send_message("me", "🤖 تست اتصال موفق!")
                print("✅ تست ارسال پیام موفق!")
            except Exception as e:
                print(f"⚠️ خطا در ارسال پیام تست: {e}")
            
        print("🎉 تست اتصال کامل شد!")
        return True
        
    except Exception as e:
        print(f"❌ خطا در اتصال: {e}")
        print(f"نوع خطا: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    if success:
        print("\n✅ پایروگرام آماده است!")
    else:
        print("\n❌ مشکل در اتصال پایروگرام!")