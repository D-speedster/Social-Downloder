from pyrogram import Client, idle
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
import plugins.admin_retry_callback  # 🔄 Admin retry callback handler
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

# سیستم تشخیص خطا (بعد از تعریف logger)
error_detector = None
try:
    from error_detector import setup_crash_handler, quick_environment_check, get_error_detector
    setup_crash_handler()
    error_detector = get_error_detector()
    logger.info("🔍 سیستم تشخیص خطا فعال شد")
except ImportError as e:
    logger.warning(f"⚠️ خطا در بارگذاری سیستم تشخیص خطا: {e}")
except Exception as e:
    logger.warning(f"⚠️ خطای غیرمنتظره در سیستم تشخیص خطا: {e}")

# بررسی سریع محیط
logger.info("🔍 در حال بررسی محیط سیستم...")
try:
    if 'quick_environment_check' in globals():
        if not quick_environment_check():
            logger.warning("❌ مشکلات حیاتی در محیط شناسایی شد.")
            input("برای ادامه Enter را فشار دهید یا Ctrl+C برای خروج...")
        else:
            logger.info("✅ بررسی محیط با موفقیت انجام شد")
except Exception as e:
    logger.warning(f"⚠️ خطا در بررسی محیط: {e}")

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
# محاسبه خودکار بر اساس CPU cores و RAM
def calculate_optimal_workers():
    cpu_count = os.cpu_count() or 2
    
    # بررسی RAM برای محدود کردن workers
    try:
        import psutil
        ram_gb = psutil.virtual_memory().total / (1024**3)
        # هر worker حدود 50-100MB RAM مصرف می‌کند
        max_by_ram = int(ram_gb * 8)  # 8 workers per GB
        logger.info(f"RAM: {ram_gb:.1f}GB, max workers by RAM: {max_by_ram}")
    except ImportError:
        # اگر psutil نصب نیست، از CPU استفاده کن
        max_by_ram = cpu_count * 8
        logger.warning("psutil not installed, using CPU-based calculation")
    
    # هر core می‌تواند 8 worker handle کند
    optimal = min(cpu_count * 8, max_by_ram)
    # حداقل 4، حداکثر 64
    return max(4, min(optimal, 64))

MAX_WORKERS = calculate_optimal_workers()
logger.info(f"🚀 Using {MAX_WORKERS} workers (optimized for {os.cpu_count() or 2} CPU cores)")
logger.info(f"⚡ Workers: {MAX_WORKERS}")

async def main():
    client = None
    background_tasks = []  # لیست برای مدیریت background tasks
    
    try:
        logger.info("🚀 در حال راه‌اندازی کلاینت ربات...")
        
        # 🔥 تنظیمات بهینه شده نهایی برای آپلود فوق‌سریع
        client_config = {
            "name": "ytdownloader3_dev2",
            "bot_token": BOT_TOKEN,
            "api_id": API_ID,
            "api_hash": API_HASH,
            "plugins": plugins,
            "workdir": DOWNLOAD_LOCATION,  # مسیر ذخیره فایل‌های موقت
            
            # 🔥 تنظیمات کلیدی برای سرعت
            "workers": MAX_WORKERS,  # استفاده از محاسبه شده
            "sleep_threshold": 10,   # 🔥 کاهش از 30 به 10 (خیلی مهم!)
            
            # تنظیمات اضافی
            "test_mode": False,
            "ipv6": False,
            "no_updates": False,
            "takeout": False,
        }
        
        # Proxy configuration با fallback
        proxy_host = getattr(config, "PROXY_HOST", None)
        proxy_port = getattr(config, "PROXY_PORT", None)
        
        if proxy_host and proxy_port:
            proxy_config = {
                "scheme": "socks5",
                "hostname": proxy_host,
                "port": proxy_port,
            }
            
            proxy_username = getattr(config, "PROXY_USERNAME", None)
            proxy_password = getattr(config, "PROXY_PASSWORD", None)
            
            if proxy_username and proxy_password:
                proxy_config["username"] = proxy_username
                proxy_config["password"] = proxy_password
            
            client_config["proxy"] = proxy_config
            logger.info(f"🔧 استفاده از پروکسی: {proxy_host}:{proxy_port}")
        else:
            logger.debug("No proxy configured")
        
        # استفاده از async context manager برای مدیریت خودکار client
        async with Client(**client_config) as client:
            # 🔥 بهینه‌سازی اضافی بعد از ساخت client
            try:
                from plugins.youtube_uploader import optimize_client_for_upload
                optimize_client_for_upload(client)
                logger.info("✅ Client optimized for ultra-fast uploads")
            except Exception as e:
                logger.warning(f"Could not apply additional optimizations: {e}")
            
            logger.info("Bot client started successfully")
            logger.info("🔗 متصل به تلگرام شد")
            
            # 🔥 Record startup in database
            if hasattr(db, "record_startup"):
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
                task = asyncio.create_task(start_auto_cleanup())
                background_tasks.append(task)
                logger.info("Auto-cleanup service started")
                logger.info("🧹 سرویس پاکسازی خودکار راه‌اندازی شد")
            except Exception as e:
                logger.warning(f"Could not start auto-cleanup: {e}")
            
            # 🔥 Start Periodic Metrics Logging
            try:
                from plugins.simple_metrics import metrics
                task = asyncio.create_task(metrics.start_periodic_logging(interval=300))  # هر 5 دقیقه
                background_tasks.append(task)
                logger.info("Periodic metrics logging started")
                logger.info("📊 لاگ‌گیری دوره‌ای آمار راه‌اندازی شد")
            except Exception as e:
                logger.warning(f"Could not start metrics logging: {e}")
            
            # Retry Queue removed - using simpler inline retry logic
            logger.info("Using inline retry logic (no background queue)")
            logger.info("✅ استفاده از retry logic ساده (بدون صف پس‌زمینه)")
            
            # Start Cookie Validator Service
            try:
                from plugins.admin import ADMIN
                await start_cookie_validator(client, ADMIN)
                logger.info("Cookie Validator service started")
                logger.info("🍪 سرویس بررسی کوکی راه‌اندازی شد")
            except Exception as e:
                logger.error(f"Failed to start Cookie Validator: {e}")
            
            # 🔥 Start Health Monitor
            try:
                from plugins.admin import ADMIN
                task = asyncio.create_task(start_health_monitor(client, ADMIN))
                background_tasks.append(task)
                logger.info("Health Monitor started")
                logger.info("🏥 سیستم نظارت سلامت راه‌اندازی شد")
            except Exception as e:
                logger.warning(f"Could not start health monitor: {e}")
            
            # 🧠 Start Memory Monitor
            try:
                from plugins.admin import ADMIN
                from plugins.memory_monitor import start_memory_monitor
                task = asyncio.create_task(start_memory_monitor(client, ADMIN))
                background_tasks.append(task)
                logger.info("Memory Monitor started")
                logger.info("🧠 سیستم نظارت حافظه راه‌اندازی شد")
            except Exception as e:
                logger.warning(f"Could not start memory monitor: {e}")
            
            logger.info("Bot started successfully")
            logger.info("✅ ربات با موفقیت راه‌اندازی شد!")
            logger.info("=" * 70)
            logger.info("⚡ تنظیمات بهینه‌سازی فعال:")
            logger.info(f"   • Workers: {MAX_WORKERS}")
            logger.info(f"   • Sleep Threshold: 10 seconds")
            logger.info(f"   • Chunk Size: 2MB")
            logger.info("=" * 70)
            logger.info("🔄 ربات در حال اجرا است... (Ctrl+C برای توقف)")
            
            await idle()
        
    except KeyboardInterrupt:
        logger.info("\n⏹️ ربات توسط کاربر متوقف شد")
    except Exception as e:
        logger.error(f"\n❌ خطا در راه‌اندازی ربات: {e}", exc_info=True)
        
        # استفاده از error_detector که در ابتدا تعریف شده
        if error_detector:
            try:
                logger.info("\n📋 در حال تولید گزارش خطا...")
                error_detector.log_crash(type(e), e, e.__traceback__)
                logger.info("📁 گزارش خطا در فایل logs/crash_report.log ذخیره شد")
            except Exception as report_error:
                logger.error(f"⚠️ خطا در تولید گزارش: {report_error}")
    finally:
        # لغو تمام background tasks
        if background_tasks:
            logger.info(f"🛑 در حال لغو {len(background_tasks)} background task...")
            for task in background_tasks:
                task.cancel()
            # منتظر ماندن برای اتمام tasks
            await asyncio.gather(*background_tasks, return_exceptions=True)
            logger.info("✅ تمام background tasks متوقف شدند")
        
        # 🔥 Record shutdown in database
        if hasattr(db, "record_shutdown"):
            try:
                db.record_shutdown()
                logger.info("Shutdown recorded in database")
                logger.info("📝 زمان توقف ثبت شد")
            except Exception as e:
                logger.warning(f"Could not record shutdown: {e}")
        
        # Stop Cookie Validator Service
        try:
            logger.info("🍪 در حال توقف سرویس بررسی کوکی...")
            await stop_cookie_validator()
            logger.info("Cookie Validator service stopped")
            logger.info("✅ سرویس کوکی با موفقیت متوقف شد")
        except Exception as e:
            logger.error(f"Error stopping Cookie Validator: {e}")
        
        # client.stop() خودکار توسط async context manager فراخوانی می‌شود
        logger.info("🔌 کلاینت توسط context manager متوقف شد")
        
        # بستن database
        try:
            if 'db' in globals():
                logger.info("🗄️ در حال بستن اتصال پایگاه داده...")
                db.close()
                logger.info("Database connection closed")
                logger.info("✅ پایگاه داده با موفقیت بسته شد")
        except Exception as e:
            logger.error(f"Error closing database in finally block: {e}")

if __name__ == "__main__":
    try:
        logger.info("🎯 شروع اجرای ربات...")
        asyncio.run(main())
        logger.info("👋 ربات با موفقیت خاتمه یافت")
    except KeyboardInterrupt:
        logger.info("\n👋 ربات توسط کاربر متوقف شد")
    except Exception as e:
        logger.error(f"\n💥 کرش ربات: {e}", exc_info=True)
        
        # استفاده از error_detector که در ابتدا تعریف شده
        if error_detector:
            try:
                logger.info("\n📋 در حال تولید گزارش نهایی خطا...")
                error_detector.log_crash(type(e), e, e.__traceback__)
                logger.info("📁 گزارش کامل خطا در فایل logs/crash_report.log ذخیره شد")
            except Exception as report_error:
                logger.error(f"⚠️ خطا در تولید گزارش نهایی: {report_error}")
        
        logger.info("\n🔍 برای بررسی دقیق‌تر خطا، فایل‌های لاگ را مطالعه کنید:")
        logger.info("   - logs/crash_report.log")
        logger.info("   - logs/bot.log")
        
        sys.exit(1)