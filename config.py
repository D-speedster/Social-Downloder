import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# ============================================================
# DATABASE CONFIGURATION
# ============================================================
# Set this to True only if you have a MySQL server running and reachable.
USE_MYSQL = False

db_config = {
    'host': os.environ.get("DB_HOST", "localhost"),
    'user': os.environ.get("DB_USER", "admin"),
    'password': os.environ.get("DB_PASSWORD", ""),  # No default password for security
    'database': os.environ.get("DB_NAME", "bot_db"),
}


# ============================================================
# SECURITY: CORE CREDENTIALS (NO HARDCODED VALUES)
# ============================================================
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


# ============================================================
# SECURITY: ADMIN CONFIGURATION (FROM ENVIRONMENT)
# ============================================================
# Phase 1 Security Fix: Admin IDs moved from hardcoded to environment variables
# Format: ADMIN_IDS="123456789,987654321,555666777"
ADMIN_IDS_STR = os.environ.get("ADMIN_IDS", "")
ADMIN = []

if ADMIN_IDS_STR:
    try:
        ADMIN = [int(x.strip()) for x in ADMIN_IDS_STR.split(",") if x.strip().isdigit()]
        if ADMIN:
            print(f"✅ Loaded {len(ADMIN)} admin ID(s) from environment")
        else:
            print("WARNING: ADMIN_IDS is set but contains no valid IDs")
    except Exception as e:
        print(f"WARNING: Error parsing ADMIN_IDS: {e}")
        ADMIN = []
else:
    print("WARNING: ADMIN_IDS environment variable is not set. Admin panel will be disabled.")

# Single admin ID for notifications (backward compatibility)
ADMIN_ID = os.environ.get("ADMIN_ID")
NOTIFY_ADMIN_ON_ERROR = str(os.environ.get("NOTIFY_ADMIN_ON_ERROR", "false")).strip().lower() in ("1", "true", "yes")

if ADMIN_ID:
    try:
        ADMIN_ID = int(ADMIN_ID)
        # Auto-add to ADMIN list if not already there
        if ADMIN_ID not in ADMIN:
            ADMIN.append(ADMIN_ID)
            print(f"✅ Added ADMIN_ID {ADMIN_ID} to admin list")
    except (ValueError, TypeError):
        print("WARNING: ADMIN_ID must be a valid integer, admin notifications disabled")
        ADMIN_ID = None


# ============================================================
# FILE PATHS CONFIGURATION (SECURE LOCATIONS)
# ============================================================
# Phase 1 Security Fix: Move cookies to secure isolated directory
COOKIE_BASE_DIR = os.environ.get("COOKIE_BASE_DIR", "./data/cookies")
os.makedirs(COOKIE_BASE_DIR, exist_ok=True)

COOKIE_FILE_PATH = os.path.join(COOKIE_BASE_DIR, "youtube_cookies.txt")
INSTAGRAM_COOKIE_PATH = os.path.join(COOKIE_BASE_DIR, "instagram_cookies.txt")

# FFMPEG path
FFMPEG_PATH = os.environ.get("FFMPEG_PATH", "ffmpeg")


# ============================================================
# PROXY CONFIGURATION (OPTIONAL)
# ============================================================
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


# ============================================================
# JOB RECOVERY CONTROLS
# ============================================================
# Disable recovery by default to avoid spamming on test runs
RECOVER_JOBS_ON_STARTUP = str(os.environ.get("RECOVER_JOBS_ON_STARTUP", "false")).strip().lower() in ("1", "true", "yes")
# If recovery is enabled, control whether to notify users for recovered items
RECOVERY_NOTIFY_USERS = str(os.environ.get("RECOVERY_NOTIFY_USERS", "false")).strip().lower() in ("1", "true", "yes")

youtube_next_fetch = 1  # time in minute

EDIT_TIME = 5


# ============================================================
# TELEGRAM THROTTLING CONFIGURATION
# ============================================================
# Optimized for high-speed uploads
TELEGRAM_THROTTLING = {
    'sleep_threshold': int(os.environ.get("TELEGRAM_SLEEP_THRESHOLD", "600")),  # 10 minutes
    'flood_sleep_threshold': int(os.environ.get("TELEGRAM_FLOOD_SLEEP_THRESHOLD", "60")),  # 1 minute
    'max_concurrent_transmissions': int(os.environ.get("TELEGRAM_MAX_CONCURRENT", "4")),
    'max_workers': min(8, int(os.environ.get("TELEGRAM_MAX_WORKERS", "8"))),
    'upload_delay_small': float(os.environ.get("TELEGRAM_UPLOAD_DELAY_SMALL", "0.0")),
    'upload_delay_medium': float(os.environ.get("TELEGRAM_UPLOAD_DELAY_MEDIUM", "0.0")),
    'upload_delay_large': float(os.environ.get("TELEGRAM_UPLOAD_DELAY_LARGE", "0.1")),
    'retry_attempts': int(os.environ.get("TELEGRAM_RETRY_ATTEMPTS", "2")),
    'base_retry_delay': float(os.environ.get("TELEGRAM_BASE_RETRY_DELAY", "0.5")),
}


# ============================================================
# YOUTUBE CONFIGURATION
# ============================================================
# با توجه به نتایج عملی، فایل نهایی معمولاً حدود 30-35% از مجموع ویدیو+صدا است
YOUTUBE_FILESIZE_CORRECTION_FACTOR = float(os.environ.get("YOUTUBE_FILESIZE_CORRECTION_FACTOR", "0.30"))


# ============================================================
# RAPIDAPI CONFIGURATION (UNIVERSAL DOWNLOADER)
# ============================================================
# Phase 1 Security Fix: Add rate limiting configuration
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")

if not RAPIDAPI_KEY:
    print("WARNING: RAPIDAPI_KEY environment variable is not set. Universal downloader might not function correctly.")

# Rate limiting for RapidAPI calls (requests per minute)
RAPIDAPI_RATE_LIMIT = int(os.environ.get("RAPIDAPI_RATE_LIMIT", "30"))  # 30 requests per minute default
RAPIDAPI_RATE_WINDOW = int(os.environ.get("RAPIDAPI_RATE_WINDOW", "60"))  # 60 seconds window

print(f"✅ RapidAPI Rate Limit: {RAPIDAPI_RATE_LIMIT} requests per {RAPIDAPI_RATE_WINDOW} seconds")


# ============================================================
# CONFIGURATION SUMMARY
# ============================================================
print("=" * 70)
print("📋 Configuration Summary:")
print("=" * 70)
print(f"✅ Bot Token: {'Set' if BOT_TOKEN else 'Missing'}")
print(f"✅ API ID: {API_ID}")
print(f"✅ API Hash: {'Set' if API_HASH else 'Missing'}")
print(f"✅ Admin IDs: {len(ADMIN)} configured")
print(f"✅ RapidAPI Key: {'Set' if RAPIDAPI_KEY else 'Missing'}")
print(f"✅ Cookie Directory: {COOKIE_BASE_DIR}")
print(f"✅ FFmpeg Path: {FFMPEG_PATH}")
print(f"✅ Proxy: {'Enabled' if PROXY_HOST else 'Disabled'}")
print("=" * 70)
