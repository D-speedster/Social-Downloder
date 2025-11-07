#!/usr/bin/env python3
"""
نسخه minimal ربات - فقط برای تست
بدون هیچ سرویس اضافی
"""
from pyrogram import Client, idle
import asyncio
import logging
from dotenv import load_dotenv
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

from config import BOT_TOKEN, API_ID, API_HASH

logger.info("=" * 70)
logger.info("🚀 شروع ربات Minimal (بدون سرویس‌های اضافی)")
logger.info("=" * 70)

async def main():
    try:
        logger.info("📦 در حال ساخت Client...")
        
        client_config = {
            "name": "minimal_test",
            "bot_token": BOT_TOKEN,
            "api_id": API_ID,
            "api_hash": API_HASH,
            "workers": 4,
            "plugins": dict(root="plugins"),  # فقط plugin ها
        }
        
        logger.info("🔗 در حال اتصال به تلگرام...")
        
        async with Client(**client_config) as client:
            logger.info("✅ اتصال موفق!")
            
            me = await client.get_me()
            logger.info(f"✅ Bot: @{me.username}")
            logger.info(f"✅ Bot ID: {me.id}")
            
            logger.info("=" * 70)
            logger.info("✅ ربات آماده است!")
            logger.info("🔄 در حال ورود به حالت idle...")
            logger.info("   (برای توقف: Ctrl+C)")
            logger.info("=" * 70)
            
            await idle()
            
            logger.info("⚠️ idle() تمام شد")
    
    except KeyboardInterrupt:
        logger.info("⏹️ ربات توسط کاربر متوقف شد")
    except Exception as e:
        logger.error(f"❌ خطا: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
        logger.info("👋 ربات با موفقیت خاتمه یافت")
    except KeyboardInterrupt:
        logger.info("👋 خروج")
    except Exception as e:
        logger.error(f"💥 کرش: {e}", exc_info=True)
