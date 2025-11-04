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
import plugins.youtube_handler
import plugins.youtube_callback
import plugins.sponsor_admin
import plugins.radiojavan_handler  # 🎵 RadioJavan downloader
import plugins.aparat_handler  # 🎬 Aparat downloader
import plugins.aparat_callback  # 🎬 Aparat callback
from plugins.cookie_validator import start_cookie_validator, stop_cookie_validator
from plugins.health_monitor import start_health_monitor, stop_health_monitor, get_health_monitor

# 🔥 CRITICAL: تنظیمات بهینه Pyrogram قبل از import
print("🔧 در حال اعمال بهینه‌سازی‌های Pyrogram...")
try:
    import pyrogram
    
    # 🔥 تنظیم chunk size برای آپلود سریع
    OPTIMAL_CHUNK_SIZE = 2 * 1024 * 1024  # 2MB
    
    # تلاش برای patch کردن ماژول‌های Pyrogram
    try:
        import pyrogram.file_id
        if hasattr(pyrogram.file_id, 'CHUNK_SIZE'):
            pyrogram.file_id.CHUNK_SIZE = OPTIMAL_CHUNK_SIZE
            print(f"✅ Chunk size set to {OPTIMAL_CHUNK_SIZE / (1024*1024):.1f}MB")
    except Exception as e:
        print(f"⚠️ Could not patch chunk size: {e}")
    
    print("✅ Pyrogram optimizations applied")
except Exception as e:
    print(f"⚠️ Pyrogram optimization warning: {e}")

# سیستم تشخیص خطا
try:
    from error_detector import setup_crash_handler, quick_environment_check, get_error_detector
    setup_crash_handler()
    print("🔍 سیستم تشخیص خطا فعال شد")
except ImportError as e:
    print(f"⚠️ خطا در بارگذاری سیستم تشخیص خطا: {e}")
except Exception as e:
    print(f"⚠️ خطای غیرمنتظره در سیستم تشخیص خطا: {e}")

# بررسی سریع محیط
print("🔍 در حال بررسی محیط سیستم...")
try:
    if not quick_environment_check():
        print("❌ مشکلات حیاتی در محیط شناسایی شد.")
        input("برای ادامه Enter را فشار دهید یا Ctrl+C برای خروج...")
    else:
        print("✅ بررسی محیط با موفقیت انجام شد")
except Exception as e:
    print(f"⚠️ خطا در بررسی محیط: {e}")

# Wizard تنظیمات
if not os.path.exists('.env'):
    print("فایل .env یافت نشد. راه‌اندازی wizard...")
    try:
        from setup_wizard import run_setup_wizard
        run_setup_wizard()
        print("تنظیمات با موفقیت انجام شد.")
    except ImportError:
        print("خطا: فایل setup_wizard.py یافت نشد.")
        sys.exit(1)
    except Exception as e:
        print(f"خطا در راه‌اندازی wizard: {e}")
        sys.exit(1)

load_dotenv()

from config import (
    BOT_TOKEN, API_ID, API_HASH, USE_MYSQL, db_config,
    RECOVER_JOBS_ON_STARTUP, RECOVERY_NOTIFY_USERS, TELEGRAM_THROTTLING
)
import config as config

# Validate configuration
try:
    BOT_TOKEN = config.BOT_TOKEN
    API_ID = config.API_ID
    API_HASH = config.API_HASH
except AttributeError as e:
    print(f"Configuration error: {e}")
    sys.exit(1)

# Create directories
DOWNLOAD_LOCATION = "./downloads"
try:
    os.makedirs(DOWNLOAD_LOCATION, exist_ok=True)
except Exception as e:
    print(f"Warning: Could not create downloads directory: {e}")

# Logging
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
os.makedirs('./logs', exist_ok=True)

basicConfig(
    level=INFO,
    format=log_format,
    filename='./logs/bot.log',
    filemode='a',
    encoding='utf-8'
)

import logging
logger = logging.getLogger(__name__)
logger.info("Bot starting up...")
logger.info(f"Python version: {sys.version}")
logger.info(f"Working directory: {os.getcwd()}")

plugins = dict(root="plugins")

# Initialize database
try:
    db = DB()
    db.setup()
    logger.info("Database initialized successfully")
    
    def cleanup_database():
        try:
            if db:
                db.close()
                logger.info("Database connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing database: {e}")
    
    atexit.register(cleanup_database)
    signal.signal(signal.SIGTERM, lambda signum, frame: cleanup_database())
    signal.signal(signal.SIGINT, lambda signum, frame: cleanup_database())
    
except Exception as e:
    logger.error(f"Database initialization failed: {e}")
    sys.exit(1)

# 🔥 Workers بهینه‌سازی شده برای production
# محاسبه خودکار بر اساس CPU cores
def calculate_optimal_workers():
    cpu_count = os.cpu_count() or 2
    # هر core می‌تواند 8-16 worker handle کند
    optimal = cpu_count * 8
    # حداقل 16، حداکثر 64
    return max(16, min(optimal, 64))

MAX_WORKERS = calculate_optimal_workers()
logger.info(f"🚀 Using {MAX_WORKERS} workers (optimized for {os.cpu_count() or 2} CPU cores)")
print(f"⚡ Workers: {MAX_WORKERS}")

async def main():
    client = None
    try:
        print("🚀 در حال راه‌اندازی کلاینت ربات...")
        
        # 🔥 تنظیمات بهینه شده نهایی برای آپلود فوق‌سریع
        client_config = {
            "name": "ytdownloader3_dev2",
            "bot_token": BOT_TOKEN,
            "api_id": API_ID,
            "api_hash": API_HASH,
            "plugins": plugins,
            
            # 🔥 تنظیمات کلیدی برای سرعت
            "workers": MAX_WORKERS,  # استفاده از محاسبه شده
            "sleep_threshold": 10,   # 🔥 کاهش از 30 به 10 (خیلی مهم!)
            
            # تنظیمات اضافی
            "test_mode": False,
            "ipv6": False,
            "no_updates": False,
            "takeout": False,
        }
        
        # Proxy configuration
        if config.PROXY_HOST and config.PROXY_PORT:
            proxy_config = {
                "scheme": "socks5",
                "hostname": config.PROXY_HOST,
                "port": config.PROXY_PORT,
            }
            
            if config.PROXY_USERNAME and config.PROXY_PASSWORD:
                proxy_config["username"] = config.PROXY_USERNAME
                proxy_config["password"] = config.PROXY_PASSWORD
            
            client_config["proxy"] = proxy_config
            print(f"🔧 استفاده از پروکسی: {config.PROXY_HOST}:{config.PROXY_PORT}")
        
        client = Client(**client_config)
        
        # 🔥 بهینه‌سازی اضافی بعد از ساخت client
        try:
            from plugins.youtube_uploader import optimize_client_for_upload
            optimize_client_for_upload(client)
            print("✅ Client optimized for ultra-fast uploads")
        except Exception as e:
            logger.warning(f"Could not apply additional optimizations: {e}")
        
        logger.info("Starting bot client...")
        print("🔗 در حال اتصال به تلگرام...")
        await client.start()
        
        # 🔥 Record startup in database
        try:
            db.record_startup()
            logger.info("Startup recorded in database")
        except Exception as e:
            logger.warning(f"Could not record startup: {e}")
        
        # Initialize job queue
        await init_job_queue(client)
        
        # 🔥 Start Auto-cleanup Service
        try:
            from plugins.auto_cleanup import start_auto_cleanup
            asyncio.create_task(start_auto_cleanup())
            logger.info("Auto-cleanup service started")
            print("🧹 سرویس پاکسازی خودکار راه‌اندازی شد")
        except Exception as e:
            logger.warning(f"Could not start auto-cleanup: {e}")
            print(f"⚠️ خطا در راه‌اندازی پاکسازی خودکار: {e}")
        
        # 🔥 Start Periodic Metrics Logging
        try:
            from plugins.simple_metrics import metrics
            asyncio.create_task(metrics.start_periodic_logging(interval=300))  # هر 5 دقیقه
            logger.info("Periodic metrics logging started")
            print("📊 لاگ‌گیری دوره‌ای آمار راه‌اندازی شد")
        except Exception as e:
            logger.warning(f"Could not start metrics logging: {e}")
            print(f"⚠️ خطا در راه‌اندازی لاگ‌گیری: {e}")
        
        # Retry Queue removed - using simpler inline retry logic
        logger.info("Using inline retry logic (no background queue)")
        print("✅ استفاده از retry logic ساده (بدون صف پس‌زمینه)")
        
        # Start Cookie Validator Service
        try:
            from plugins.admin import ADMIN
            await start_cookie_validator(client, ADMIN)
            logger.info("Cookie Validator service started")
            print("🍪 سرویس بررسی کوکی راه‌اندازی شد")
        except Exception as e:
            logger.error(f"Failed to start Cookie Validator: {e}")
            print(f"⚠️ خطا در راه‌اندازی سرویس کوکی: {e}")
        
        # 🔥 Start Health Monitor
        try:
            from plugins.admin import ADMIN
            asyncio.create_task(start_health_monitor(client, ADMIN))
            logger.info("Health Monitor started")
            print("🏥 سیستم نظارت سلامت راه‌اندازی شد")
        except Exception as e:
            logger.warning(f"Could not start health monitor: {e}")
        
        # 🧠 Start Memory Monitor
        try:
            from plugins.admin import ADMIN
            from plugins.memory_monitor import start_memory_monitor
            asyncio.create_task(start_memory_monitor(client, ADMIN))
            logger.info("Memory Monitor started")
            print("🧠 سیستم نظارت حافظه راه‌اندازی شد")
        except Exception as e:
            logger.warning(f"Could not start memory monitor: {e}")
            print(f"⚠️ خطا در راه‌اندازی health monitor: {e}")
        
        logger.info("Bot started successfully")
        print("✅ ربات با موفقیت راه‌اندازی شد!")
        print("=" * 70)
        print("⚡ تنظیمات بهینه‌سازی فعال:")
        print(f"   • Workers: {MAX_WORKERS}")
        print(f"   • Sleep Threshold: 10 seconds")
        print(f"   • Chunk Size: 2MB")
        print("=" * 70)
        print("🔄 ربات در حال اجرا است... (Ctrl+C برای توقف)")
        
        await idle()
        
    except KeyboardInterrupt:
        print("\n⏹️ ربات توسط کاربر متوقف شد")
        logger.info("Bot stopped by user")
    except Exception as e:
        print(f"\n❌ خطا در راه‌اندازی ربات: {e}")
        logger.error(f"Bot startup failed: {e}")
        
        try:
            error_detector = get_error_detector()
            print("\n📋 در حال تولید گزارش خطا...")
            error_detector.log_crash(type(e), e, e.__traceback__)
            print("📁 گزارش خطا در فایل logs/crash_report.log ذخیره شد")
        except Exception as report_error:
            print(f"⚠️ خطا در تولید گزارش: {report_error}")
        
        raise
    finally:
        # 🔥 Record shutdown in database
        try:
            if 'db' in globals():
                db.record_shutdown()
                logger.info("Shutdown recorded in database")
                print("📝 زمان توقف ثبت شد")
        except Exception as e:
            logger.warning(f"Could not record shutdown: {e}")
        
        # Stop Cookie Validator Service
        try:
            print("🍪 در حال توقف سرویس بررسی کوکی...")
            await stop_cookie_validator()
            logger.info("Cookie Validator service stopped")
            print("✅ سرویس کوکی با موفقیت متوقف شد")
        except Exception as e:
            print(f"⚠️ خطا در توقف سرویس کوکی: {e}")
            logger.error(f"Error stopping Cookie Validator: {e}")
        
        try:
            if client is not None:
                print("🔌 در حال قطع اتصال کلاینت...")
                await client.stop()
                logger.info("Bot client stopped")
                print("✅ کلاینت با موفقیت متوقف شد")
        except Exception as e:
            print(f"⚠️ خطا در توقف کلاینت: {e}")
            logger.error(f"Error stopping client: {e}")
        
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
        
        try:
            error_detector = get_error_detector()
            print("\n📋 در حال تولید گزارش نهایی خطا...")
            error_detector.log_crash(type(e), e, e.__traceback__)
            print("📁 گزارش کامل خطا در فایل logs/crash_report.log ذخیره شد")
        except Exception as report_error:
            print(f"⚠️ خطا در تولید گزارش نهایی: {report_error}")
        
        print("\n🔍 برای بررسی دقیق‌تر خطا، فایل‌های لاگ را مطالعه کنید:")
        print("   - logs/crash_report.log")
        print("   - logs/bot.log")
        
        sys.exit(1)