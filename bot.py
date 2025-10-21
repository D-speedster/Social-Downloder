from pyrogram import Client, idle
from pyrogram.storage import MemoryStorage
from plugins.sqlite_db_wrapper import DB
from plugins.job_queue import init_job_queue
from logging import basicConfig, ERROR, INFO
import os
import sys
import atexit
import signal
import asyncio
from dotenv import load_dotenv

# وارد کردن سیستم تشخیص خطا
try:
    from error_detector import setup_crash_handler, quick_environment_check, get_error_detector
    # تنظیم هندلر کرش سراسری
    setup_crash_handler()
    print("🔍 سیستم تشخیص خطا فعال شد")
except ImportError as e:
    print(f"⚠️ خطا در بارگذاری سیستم تشخیص خطا: {e}")
    print("ربات بدون سیستم تشخیص خطا ادامه می‌یابد...")
except Exception as e:
    print(f"⚠️ خطای غیرمنتظره در سیستم تشخیص خطا: {e}")

# بررسی سریع محیط قبل از شروع
print("🔍 در حال بررسی محیط سیستم...")
try:
    if not quick_environment_check():
        print("❌ مشکلات حیاتی در محیط شناسایی شد. لطفاً مشکلات را حل کنید.")
        input("برای ادامه Enter را فشار دهید یا Ctrl+C برای خروج...")
    else:
        print("✅ بررسی محیط با موفقیت انجام شد")
except Exception as e:
    print(f"⚠️ خطا در بررسی محیط: {e}")
    print("ربات بدون بررسی محیط ادامه می‌یابد...")

# اجرای wizard تنظیمات اولیه در صورت عدم وجود .env
if not os.path.exists('.env'):
    print("فایل .env یافت نشد. راه‌اندازی wizard تنظیمات اولیه...")
    try:
        from setup_wizard import run_setup_wizard
        run_setup_wizard()
        print("تنظیمات با موفقیت انجام شد. در حال راه‌اندازی ربات...")
    except ImportError:
        print("خطا: فایل setup_wizard.py یافت نشد.")
        sys.exit(1)
    except Exception as e:
        print(f"خطا در راه‌اندازی wizard: {e}")
        sys.exit(1)

# بارگذاری متغیرهای محیطی از .env
load_dotenv()

# وارد کردن config پس از بارگذاری .env
from config import (
    BOT_TOKEN, API_ID, API_HASH, USE_MYSQL, db_config,
    RECOVER_JOBS_ON_STARTUP, RECOVERY_NOTIFY_USERS, TELEGRAM_THROTTLING
)
import config as config

# Security: Validate configuration before starting
try:
    BOT_TOKEN = config.BOT_TOKEN
    API_ID = config.API_ID  # Changed from APP_ID to API_ID
    API_HASH = config.API_HASH
except AttributeError as e:
    print(f"Configuration error: {e}")
    print("Please ensure all required environment variables are set.")
    sys.exit(1)

# Create downloads directory with proper permissions
DOWNLOAD_LOCATION = "./downloads"
try:
    os.makedirs(DOWNLOAD_LOCATION, exist_ok=True)
except Exception as e:
    print(f"Warning: Could not create downloads directory: {e}")

# Enhanced logging with rotation and better format
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'

# Create logs directory if it doesn't exist
os.makedirs('./logs', exist_ok=True)

basicConfig(
    level=INFO,  # Changed to INFO for better debugging
    format=log_format,
    filename='./logs/bot.log',
    filemode='a',  # Append mode
    encoding='utf-8'  # Ensure UTF-8 encoding
)

# Log startup information
import logging
logger = logging.getLogger(__name__)
logger.info("Bot starting up...")
logger.info(f"Python version: {sys.version}")
logger.info(f"Working directory: {os.getcwd()}")

plugins = dict(
    root="plugins",
)

# Initialize database with error handling
try:
    db = DB()
    db.setup()
    logger.info("Database initialized successfully")
    
    # Register cleanup function
    def cleanup_database():
        try:
            if db:
                db.close()
                logger.info("Database connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing database: {e}")
    
    # Register cleanup for normal exit and signals
    atexit.register(cleanup_database)
    signal.signal(signal.SIGTERM, lambda signum, frame: cleanup_database())
    signal.signal(signal.SIGINT, lambda signum, frame: cleanup_database())
    
except Exception as e:
    logger.error(f"Database initialization failed: {e}")
    sys.exit(1)

# Security: Limit workers to prevent resource exhaustion
MAX_WORKERS = min(16, os.cpu_count() * 2) if os.cpu_count() else 8
logger.info(f"Using {MAX_WORKERS} workers")

async def main():
    client = None
    try:
        print("🚀 در حال راه‌اندازی کلاینت ربات...")
        
        # Prepare client configuration with optimized throttling settings
        client_config = {
            "name": "ytdownloader3_dev2",
            "bot_token": BOT_TOKEN,
            "api_id": API_ID,
            "api_hash": API_HASH,
            "plugins": plugins,
            "workers": TELEGRAM_THROTTLING['max_workers'],
            "sleep_threshold": TELEGRAM_THROTTLING['sleep_threshold'],
            "max_concurrent_transmissions": TELEGRAM_THROTTLING['max_concurrent_transmissions'],
            "test_mode": False,  # Use production servers
            "ipv6": False,       # Disable IPv6 to avoid connection issues
        }
        
        # Add proxy configuration if available
        if config.PROXY_HOST and config.PROXY_PORT:
            from pyrogram.types import ProxyType
            proxy_config = {
                "scheme": "socks5",  # Default to SOCKS5
                "hostname": config.PROXY_HOST,
                "port": config.PROXY_PORT,
            }
            
            # Add authentication if provided
            if config.PROXY_USERNAME and config.PROXY_PASSWORD:
                proxy_config["username"] = config.PROXY_USERNAME
                proxy_config["password"] = config.PROXY_PASSWORD
            
            client_config["proxy"] = proxy_config
            print(f"🔧 استفاده از پروکسی: {config.PROXY_HOST}:{config.PROXY_PORT}")
        
        client = Client(**client_config)
        
        logger.info("Starting bot client...")
        print("🔗 در حال اتصال به تلگرام...")
        await client.start()
        # Initialize job queue and recover any pending/incomplete jobs
        await init_job_queue(client)
        logger.info("Bot started successfully")
        print("✅ ربات با موفقیت راه‌اندازی شد!")
        print("🔄 ربات در حال اجرا است... (Ctrl+C برای توقف)")
        
        # Keep the bot running reliably
        await idle()
        
    except KeyboardInterrupt:
        print("\n⏹️ ربات توسط کاربر متوقف شد")
        logger.info("Bot stopped by user")
    except Exception as e:
        print(f"\n❌ خطا در راه‌اندازی ربات: {e}")
        logger.error(f"Bot startup failed: {e}")
        
        # تولید گزارش تفصیلی خطا
        try:
            error_detector = get_error_detector()
            print("\n📋 در حال تولید گزارش خطا...")
            error_detector.log_crash(type(e), e, e.__traceback__)
            print("📁 گزارش خطا در فایل logs/crash_report.log ذخیره شد")
        except Exception as report_error:
            print(f"⚠️ خطا در تولید گزارش: {report_error}")
        
        raise
    finally:
        # Ensure client is stopped
        try:
            if client is not None:
                print("🔌 در حال قطع اتصال کلاینت...")
                await client.stop()
                logger.info("Bot client stopped")
                print("✅ کلاینت با موفقیت متوقف شد")
        except Exception as e:
            print(f"⚠️ خطا در توقف کلاینت: {e}")
            logger.error(f"Error stopping client: {e}")
        
        # Ensure database is closed
        try:
            if 'db' in globals():
                print("🗄️ در حال بستن اتصال پایگاه داده...")
                db.close()
                logger.info("Database connection closed")
                print("✅ پایگاه داده با موفقیت بسته شد")
        except Exception as e:
            print(f"⚠️ خطا در بستن پایگاه داده: {e}")
            logger.error(f"Error closing database in finally block: {e}")

if __name__ == "__main__":
    try:
        print("🎯 شروع اجرای ربات...")
        asyncio.run(main())
        print("👋 ربات با موفقیت خاتمه یافت")
    except KeyboardInterrupt:
        print("\n👋 ربات توسط کاربر متوقف شد")
        logger.info("Bot stopped by user")
    except Exception as e:
        print(f"\n💥 کرش ربات: {e}")
        logger.error(f"Bot failed: {e}")
        
        # تولید گزارش نهایی خطا
        try:
            error_detector = get_error_detector()
            print("\n📋 در حال تولید گزارش نهایی خطا...")
            error_detector.log_crash(type(e), e, e.__traceback__)
            print("📁 گزارش کامل خطا در فایل logs/crash_report.log ذخیره شد")
            print("📄 گزارش تفصیلی در فایل logs/detailed_error_report.json موجود است")
        except Exception as report_error:
            print(f"⚠️ خطا در تولید گزارش نهایی: {report_error}")
        
        print("\n🔍 برای بررسی دقیق‌تر خطا، فایل‌های لاگ را مطالعه کنید:")
        print("   - logs/crash_report.log")
        print("   - logs/detailed_error_report.json")
        print("   - logs/bot.log")
        
        sys.exit(1)
