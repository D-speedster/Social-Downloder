import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# database config
# Set this to True only if you have a MySQL server running and reachable.
USE_MYSQL = False

db_config = {
    'host': os.environ.get("DB_HOST", "localhost"),
    'user': os.environ.get("DB_USER", "admin"),
    'password': os.environ.get("DB_PASSWORD", ""),  # No default password for security
    'database': os.environ.get("DB_NAME", "bot_db"),
}

# Security: No hardcoded tokens - must be set via environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")

# Validate required environment variables
if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN environment variable is required")
    sys.exit(1)
    
if not API_ID:
    print("ERROR: API_ID environment variable is required")
    sys.exit(1)
    
if not API_HASH:
    print("ERROR: API_HASH environment variable is required")
    sys.exit(1)

# Convert API_ID to int with error handling
try:
    API_ID = int(API_ID)
except (ValueError, TypeError):
    print("ERROR: API_ID must be a valid integer")
    sys.exit(1)

# Keep APP_ID for backward compatibility
APP_ID = API_ID

# File paths configuration
COOKIE_FILE_PATH = os.environ.get("COOKIE_FILE_PATH", "./cookie.txt")
FFMPEG_PATH = os.environ.get("FFMPEG_PATH", "ffmpeg")

# Proxy configuration (optional)
PROXY_HOST = os.environ.get("PROXY_HOST")
PROXY_PORT = os.environ.get("PROXY_PORT")
PROXY_USERNAME = os.environ.get("PROXY_USERNAME")
PROXY_PASSWORD = os.environ.get("PROXY_PASSWORD")

# Convert proxy port to int if provided
if PROXY_PORT:
    try:
        PROXY_PORT = int(PROXY_PORT)
    except (ValueError, TypeError):
        print("WARNING: PROXY_PORT must be a valid integer, ignoring proxy settings")
        PROXY_HOST = None
        PROXY_PORT = None

# --- Job recovery controls ---
# Disable recovery by default to avoid spamming on test runs
RECOVER_JOBS_ON_STARTUP = str(os.environ.get("RECOVER_JOBS_ON_STARTUP", "false")).strip().lower() in ("1", "true", "yes")
# If recovery is enabled, control whether to notify users for recovered items
RECOVERY_NOTIFY_USERS = str(os.environ.get("RECOVERY_NOTIFY_USERS", "false")).strip().lower() in ("1", "true", "yes")

youtube_next_fetch = 1  # time in minute

EDIT_TIME = 5

# Telegram throttling configuration
TELEGRAM_THROTTLING = {
    'sleep_threshold': int(os.environ.get("TELEGRAM_SLEEP_THRESHOLD", "300")),  # 5 minutes
    'flood_sleep_threshold': int(os.environ.get("TELEGRAM_FLOOD_SLEEP_THRESHOLD", "120")),  # 2 minutes
    'max_concurrent_transmissions': int(os.environ.get("TELEGRAM_MAX_CONCURRENT", "2")),
    'max_workers': min(4, int(os.environ.get("TELEGRAM_MAX_WORKERS", "4"))),  # Reduced workers
    'upload_delay_small': float(os.environ.get("TELEGRAM_UPLOAD_DELAY_SMALL", "0.1")),  # 100ms
    'upload_delay_medium': float(os.environ.get("TELEGRAM_UPLOAD_DELAY_MEDIUM", "0.2")),  # 200ms
    'upload_delay_large': float(os.environ.get("TELEGRAM_UPLOAD_DELAY_LARGE", "0.5")),  # 500ms
    'retry_attempts': int(os.environ.get("TELEGRAM_RETRY_ATTEMPTS", "3")),
    'base_retry_delay': float(os.environ.get("TELEGRAM_BASE_RETRY_DELAY", "1.0")),  # 1 second
}

# YouTube file size correction factor
# با توجه به نتایج عملی، فایل نهایی معمولاً حدود 30-35% از مجموع ویدیو+صدا است
# این مقدار برای تخمین دقیق‌تر اندازه نهایی خروجی پس از merge/encode تنظیم شد
YOUTUBE_FILESIZE_CORRECTION_FACTOR = float(os.environ.get("YOUTUBE_FILESIZE_CORRECTION_FACTOR", "0.30"))

# RapidAPI Key for Universal Downloader (security: load from environment)
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")

if not RAPIDAPI_KEY:
    print("WARNING: RAPIDAPI_KEY environment variable is not set. Universal downloader might not function correctly.")
