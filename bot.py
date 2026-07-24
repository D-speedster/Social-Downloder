#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Fix Unicode encoding for Windows console
import sys
import os
if sys.platform == 'win32':
    # Only set console to UTF-8, don't wrap stdout/stderr
    os.system('chcp 65001 >nul 2>&1')
    # Set environment variable for Python
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from pyrogram import Client, idle
from plugins.sqlite_db_wrapper import DB
from plugins.job_queue import init_job_queue
from logging import basicConfig, ERROR, INFO
import atexit
import signal
import asyncio
from dotenv import load_dotenv
# Handler imports moved after Client creation to ensure proper registration
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

# Logging with both file and console output
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
os.makedirs('./logs', exist_ok=True)

# CRITICAL FIX: Add console handler for Docker logs visibility
import logging

# Check environment variable for console logging
LOG_TO_CONSOLE = os.getenv('LOG_TO_CONSOLE', '1').strip().lower() in ('1', 'true', 'yes')

# Create handlers
handlers = [
    logging.FileHandler('./logs/bot.log', mode='a', encoding='utf-8')
]

# Add console handler (CRITICAL for Docker)
if LOG_TO_CONSOLE:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.ERROR)  # At minimum, ERROR to console
    console_handler.setFormatter(logging.Formatter(log_format))
    handlers.append(console_handler)

basicConfig(
    level=INFO,
    format=log_format,
    handlers=handlers
)

logger = logging.getLogger(__name__)

# Log configuration
if LOG_TO_CONSOLE:
    logger.info("✅ Console logging enabled (LOG_TO_CONSOLE=1)")
    logger.info("✅ ERROR and above will be visible in Docker logs")
else:
    logger.warning("⚠️ Console logging disabled - only file logging active")

# 🔥 بررسی و توقف پروسس‌های قدیمی
def check_and_stop_old_instances():
    """بررسی و توقف نمونه‌های قدیمی ربات"""
    try:
        import psutil
        current_pid = os.getpid()
        bot_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and 'bot.py' in ' '.join(cmdline) and proc.info['pid'] != current_pid:
                    bot_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if bot_processes:
            logger.warning(f"⚠️ {len(bot_processes)} نمونه قدیمی ربات در حال اجراست")
            for proc in bot_processes:
                try:
                    logger.info(f"🛑 توقف پروسس قدیمی: PID {proc.pid}")
                    proc.terminate()
                    proc.wait(timeout=5)
                    logger.info(f"✅ پروسس {proc.pid} متوقف شد")
                except Exception as e:
                    logger.warning(f"⚠️ خطا در توقف پروسس {proc.pid}: {e}")
                    try:
                        proc.kill()
                    except:
                        pass
            
            import time
            time.sleep(2)  # صبر برای آزاد شدن منابع
            logger.info("✅ تمام پروسس‌های قدیمی متوقف شدند")
        else:
            logger.info("✅ هیچ پروسس قدیمی یافت نشد")
            
    except ImportError:
        logger.warning("⚠️ psutil نصب نیست - بررسی پروسس‌ها غیرفعال است")
    except Exception as e:
        logger.warning(f"⚠️ خطا در بررسی پروسس‌ها: {e}")

# 🔥 بررسی تغییر توکن و پاکسازی session
def check_token_change():
    """بررسی تغییر توکن و پاکسازی session در صورت نیاز"""
    import glob
    import hashlib
    
    logger.info("🔑 بررسی تغییر توکن...")
    
    try:
        # محاسبه hash توکن فعلی
        current_token_hash = hashlib.md5(BOT_TOKEN.encode()).hexdigest()
        token_cache_file = ".token_cache"
        
        # بررسی توکن قبلی
        if os.path.exists(token_cache_file):
            with open(token_cache_file, 'r') as f:
                old_token_hash = f.read().strip()
            
            if old_token_hash != current_token_hash:
                logger.warning("⚠️ توکن ربات تغییر کرده است!")
                logger.info("🧹 در حال پاکسازی session های قدیمی...")
                
                # حذف تمام session ها (در پوشه فعلی و downloads)
                session_files = glob.glob("*.session*") + glob.glob("downloads/*.session*")
                for session_file in session_files:
                    try:
                        os.remove(session_file)
                        logger.info(f"✅ حذف شد: {session_file}")
                    except Exception as e:
                        logger.error(f"❌ خطا در حذف {session_file}: {e}")
                
                logger.info("✅ تمام session های قدیمی پاک شدند")
            else:
                logger.info("✅ توکن تغییری نکرده است")
        else:
            logger.info("ℹ️ اولین اجرا - ذخیره توکن")
        
        # ذخیره hash توکن جدید
        with open(token_cache_file, 'w') as f:
            f.write(current_token_hash)
        
    except Exception as e:
        logger.warning(f"⚠️ خطا در بررسی تغییر توکن: {e}")

# 🔥 پاکسازی خودکار session های قفل شده
def cleanup_locked_sessions():
    """پاکسازی فایل‌های session قفل شده قبل از شروع"""
    import glob
    import time
    
    logger.info("🧹 بررسی session های قفل شده...")
    
    # پیدا کردن تمام فایل‌های session-journal (نشانه قفل بودن)
    # در پوشه فعلی و downloads
    journal_files = glob.glob("*.session-journal") + glob.glob("downloads/*.session-journal")
    
    if journal_files:
        logger.warning(f"⚠️ {len(journal_files)} session قفل شده پیدا شد")
        
        for journal_file in journal_files:
            try:
                # حذف فایل journal
                os.remove(journal_file)
                logger.info(f"✅ حذف شد: {journal_file}")
                
                # حذف فایل session مربوطه
                session_file = journal_file.replace("-journal", "")
                if os.path.exists(session_file):
                    # فقط اگر خیلی قدیمی است حذف کن
                    file_age = time.time() - os.path.getmtime(session_file)
                    if file_age > 60:  # بیشتر از 1 دقیقه
                        os.remove(session_file)
                        logger.info(f"✅ حذف شد: {session_file}")
                    else:
                        logger.info(f"⏭️ نگه داشته شد: {session_file} (تازه است)")
                    
            except Exception as e:
                logger.error(f"❌ خطا در حذف {journal_file}: {e}")
        
        logger.info("✅ پاکسازی session ها تمام شد")
        time.sleep(0.5)  # کمی صبر کنیم
    else:
        logger.info("✅ هیچ session قفل شده‌ای یافت نشد")

# اجرای بررسی و پاکسازی
logger.info("=" * 70)
logger.info("🔍 بررسی و پاکسازی قبل از شروع")
logger.info("=" * 70)
check_and_stop_old_instances()
check_token_change()  # بررسی تغییر توکن
cleanup_locked_sessions()
logger.info("=" * 70)

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
    global plugins  # Access global plugins variable
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
        
        # ساخت client
        client = Client(**client_config)
        
        # 🔥 CRITICAL: Import handlers AFTER Client creation
        logger.info("📥 Importing handlers...")
        import plugins.youtube_handler
        import plugins.youtube_callback
        import plugins.pornhub_handler  # 🔞 Adult content downloader
        import plugins.adult_content_admin  # 🔞 Adult content admin panel
        import plugins.sponsor_admin
        import plugins.radiojavan_handler  # 🎵 RadioJavan downloader
        import plugins.aparat_handler  # 🎬 Aparat downloader
        import plugins.aparat_callback  # 🎬 Aparat callback
        import plugins.admin_retry_callback  # 🔄 Admin retry callback handler
        import plugins.universal_downloader  # 🌐 Universal downloader (Instagram, etc.)
        logger.info("✅ All handlers imported and registered")
        
        # ========================================================
        # CRITICAL FIX: Start client with SessionRevoked handling
        # ========================================================
        max_retries = 2
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"🔄 Starting client (attempt {attempt}/{max_retries})...")
                await client.start()
                logger.info("Bot client started successfully")
                logger.info("🔗 متصل به تلگرام شد")
                break  # Success - exit retry loop
                
            except Exception as e:
                import traceback
                error_type = type(e).__name__
                
                # 🔥 Special handling for SessionRevoked
                if 'SessionRevoked' in error_type or 'SessionRevoked' in str(e):
                    error_msg = (
                        f"❌ CRITICAL: Session has been revoked by Telegram\n"
                        f"This usually happens when:\n"
                        f"  1. Bot token was regenerated via @BotFather\n"
                        f"  2. Session file is corrupted\n"
                        f"  3. Authorization was terminated\n"
                    )
                    
                    # Print to stdout for Docker logs
                    print(error_msg, file=sys.stdout, flush=True)
                    logger.error(error_msg)
                    
                    # Cleanup session file
                    session_file = f"{DOWNLOAD_LOCATION}/ytdownloader3_dev2.session"
                    if os.path.exists(session_file):
                        try:
                            os.remove(session_file)
                            cleanup_msg = f"✅ Removed corrupted session: {session_file}"
                            print(cleanup_msg, file=sys.stdout, flush=True)
                            logger.info(cleanup_msg)
                            
                            # Retry once after cleanup
                            if attempt < max_retries:
                                retry_msg = f"🔄 Retrying with fresh session (attempt {attempt + 1}/{max_retries})..."
                                print(retry_msg, file=sys.stdout, flush=True)
                                logger.info(retry_msg)
                                continue
                        except Exception as cleanup_error:
                            cleanup_error_msg = f"⚠️ Could not remove session file: {cleanup_error}"
                            print(cleanup_error_msg, file=sys.stdout, flush=True)
                            logger.warning(cleanup_error_msg)
                    
                    # Failed after retries
                    final_error = (
                        f"❌ FATAL: Could not start bot after {attempt} attempts\n"
                        f"Please check:\n"
                        f"  1. BOT_TOKEN is valid and not revoked\n"
                        f"  2. Regenerate token via @BotFather if needed\n"
                        f"  3. Remove all .session files and restart\n"
                    )
                    print(final_error, file=sys.stdout, flush=True)
                    logger.critical(final_error)
                    
                    # Exit with error code for Docker
                    sys.exit(1)
                
                # Other errors
                else:
                    error_details = (
                        f"❌ ERROR starting client: {error_type}\n"
                        f"Message: {str(e)}\n"
                        f"Traceback:\n{traceback.format_exc()}"
                    )
                    print(error_details, file=sys.stdout, flush=True)
                    logger.error(error_details)
                    
                    # Retry for other errors too
                    if attempt < max_retries:
                        retry_msg = f"🔄 Retrying... (attempt {attempt + 1}/{max_retries})"
                        print(retry_msg, file=sys.stdout, flush=True)
                        logger.info(retry_msg)
                        await asyncio.sleep(2)
                        continue
                    else:
                        # Failed after all retries
                        final_msg = f"❌ FATAL: Could not start client after {max_retries} attempts"
                        print(final_msg, file=sys.stdout, flush=True)
                        logger.critical(final_msg)
                        sys.exit(1)
        
        try:
            # 🔥 بهینه‌سازی اضافی بعد از ساخت client
            try:
                from plugins.youtube_uploader import optimize_client_for_upload
                optimize_client_for_upload(client)
                logger.info("✅ Client optimized for ultra-fast uploads")
            except Exception as e:
                logger.warning(f"Could not apply additional optimizations: {e}")
            
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
            logger.info("🔄 تلاش برای راه‌اندازی Cookie Validator...")
            try:
                from plugins.admin import ADMIN
                await start_cookie_validator(client, ADMIN)
                logger.info("✅ Cookie Validator service started")
            except Exception as e:
                logger.warning(f"⚠️ Cookie Validator غیرفعال شد: {e}")
            
            # 🔥 Start Health Monitor
            logger.info("🔄 تلاش برای راه‌اندازی Health Monitor...")
            try:
                from plugins.admin import ADMIN
                task = asyncio.create_task(start_health_monitor(client, ADMIN))
                background_tasks.append(task)
                logger.info("✅ Health Monitor started")
            except Exception as e:
                logger.warning(f"⚠️ Health Monitor غیرفعال شد: {e}")
            
            # 🧠 Start Memory Monitor
            logger.info("🔄 تلاش برای راه‌اندازی Memory Monitor...")
            try:
                from plugins.admin import ADMIN
                from plugins.memory_monitor import start_memory_monitor
                task = asyncio.create_task(start_memory_monitor(client, ADMIN))
                background_tasks.append(task)
                logger.info("✅ Memory Monitor started")
            except Exception as e:
                logger.warning(f"⚠️ Memory Monitor غیرفعال شد: {e}")
            
            logger.info("Bot started successfully")
            logger.info("✅ ربات با موفقیت راه‌اندازی شد!")
            logger.info("=" * 70)
            logger.info("⚡ تنظیمات بهینه‌سازی فعال:")
            logger.info(f"   • Workers: {MAX_WORKERS}")
            logger.info(f"   • Sleep Threshold: 10 seconds")
            logger.info(f"   • Chunk Size: 2MB")
            logger.info("=" * 70)
            logger.info("🔄 ربات در حال اجرا است... (Ctrl+C برای توقف)")
            logger.info("⏳ در حال ورود به حالت idle...")
            
            await idle()
            
            logger.info("⚠️ idle() تمام شد - این نباید اتفاق بیفتد!")
        
        finally:
            # cleanup داخل try block
            logger.info("🧹 شروع cleanup...")
            
            # لغو background tasks
            if background_tasks:
                logger.info(f"🛑 در حال لغو {len(background_tasks)} background task...")
                for task in background_tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*background_tasks, return_exceptions=True)
                logger.info("✅ Background tasks متوقف شدند")
            
            # Stop Cookie Validator
            try:
                logger.info("🍪 در حال توقف Cookie Validator...")
                await stop_cookie_validator()
                logger.info("✅ Cookie Validator متوقف شد")
            except Exception as e:
                logger.warning(f"خطا در توقف Cookie Validator: {e}")
            
            # Stop client
            try:
                logger.info("🔌 در حال توقف Client...")
                await client.stop()
                logger.info("✅ Client متوقف شد")
            except Exception as e:
                logger.error(f"خطا در توقف Client: {e}")
        
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
        # 🔥 Record shutdown in database
        if hasattr(db, "record_shutdown"):
            try:
                db.record_shutdown()
                logger.info("Shutdown recorded in database")
            except Exception as e:
                logger.warning(f"Could not record shutdown: {e}")
        
        # بستن database
        try:
            if 'db' in globals():
                logger.info("🗄️ در حال بستن اتصال پایگاه داده...")
                db.close()
                logger.info("✅ پایگاه داده بسته شد")
        except Exception as e:
            logger.error(f"خطا در بستن database: {e}")

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