#!/bin/bash
# ============================================================
# entrypoint.sh — Social-Downloader
# Phase 1: Proper error handling without silencing failures
# ============================================================

set -e

echo "============================================================"
echo " Social-Downloader — Container Startup"
echo " Service: ${SERVICE_NAME:-unknown}"
echo " Phase 1: Enhanced Error Handling"
echo "============================================================"

# ============================================================
# Phase 1: Create secure directories with proper permissions
# ============================================================
echo "[entrypoint] Creating required directories..."
mkdir -p /app/logs
mkdir -p /app/downloads
mkdir -p /app/data
mkdir -p /app/data/cookies_tmp
mkdir -p /app/data/sessions
mkdir -p /app/data/cookies
mkdir -p /var/lib/social-db

echo "[entrypoint] ✅ Required directories created."

# ============================================================
# Phase 1: Symlink for delivery_bot.session
# ============================================================
SESSION_REAL="/app/data/sessions/delivery_bot.session"
SESSION_LINK="/app/delivery_bot.session"

if [ ! -L "${SESSION_LINK}" ]; then
    # اگر قبلاً یک فایل واقعی (نه symlink) آنجا بود، به مسیر واقعی منتقل کن
    if [ -f "${SESSION_LINK}" ]; then
        echo "[entrypoint] Moving existing session file into data/sessions/ ..."
        mv "${SESSION_LINK}" "${SESSION_REAL}"
    fi
    ln -s "${SESSION_REAL}" "${SESSION_LINK}"
    echo "[entrypoint] ✅ Symlink created: ${SESSION_LINK} -> ${SESSION_REAL}"
else
    echo "[entrypoint] ℹ️ Symlink already exists: ${SESSION_LINK}"
fi

# ============================================================
# Phase 1: Validate ffmpeg installation
# ============================================================
echo "[entrypoint] Checking ffmpeg..."
if ! command -v ffmpeg > /dev/null 2>&1; then
    echo "[entrypoint] ❌ ERROR: ffmpeg not found in PATH!"
    echo "[entrypoint] Please install ffmpeg or check FFMPEG_PATH"
    exit 1
fi
echo "[entrypoint] ✅ ffmpeg OK: $(ffmpeg -version 2>&1 | head -1)"

# ============================================================
# Phase 1: Validate required environment variables
# ============================================================
echo "[entrypoint] Validating environment variables..."

if [ -z "${BOT_TOKEN}" ]; then
    echo "[entrypoint] ❌ ERROR: BOT_TOKEN is not set."
    echo "[entrypoint] Please set BOT_TOKEN in .env file"
    exit 1
fi

if [ -z "${API_ID}" ]; then
    echo "[entrypoint] ❌ ERROR: API_ID is not set."
    echo "[entrypoint] Please set API_ID in .env file"
    exit 1
fi

if [ -z "${API_HASH}" ]; then
    echo "[entrypoint] ❌ ERROR: API_HASH is not set."
    echo "[entrypoint] Please set API_HASH in .env file"
    exit 1
fi

# Phase 1: Validate admin configuration
if [ -z "${ADMIN_IDS}" ]; then
    echo "[entrypoint] ⚠️ WARNING: ADMIN_IDS is not set."
    echo "[entrypoint] Admin panel will be disabled."
else
    echo "[entrypoint] ✅ Admin IDs configured"
fi

# Phase 1: Validate RapidAPI configuration
if [ -z "${RAPIDAPI_KEY}" ]; then
    echo "[entrypoint] ⚠️ WARNING: RAPIDAPI_KEY is not set."
    echo "[entrypoint] Universal downloader may not work correctly."
else
    echo "[entrypoint] ✅ RapidAPI key configured"
fi

echo "[entrypoint] ✅ Required environment variables validated."

# ============================================================
# Phase 1: Database migration with PROPER error handling
# ============================================================
echo "[entrypoint] Running database migration..."

# Check if migration script exists
if [ ! -f "/app/tools/migrate_requests_table.py" ]; then
    echo "[entrypoint] ⚠️ WARNING: Migration script not found"
    echo "[entrypoint] Skipping migration (file does not exist)"
else
    # Run migration with proper error handling
    PYTHONPATH=/app python3 -m tools.migrate_requests_table
    
    MIGRATION_EXIT_CODE=$?
    
    if [ $MIGRATION_EXIT_CODE -eq 0 ]; then
        echo "[entrypoint] ✅ Database migration completed successfully"
    else
        echo "[entrypoint] ❌ ERROR: Database migration failed with exit code $MIGRATION_EXIT_CODE"
        echo "[entrypoint] This may cause issues with the bot operation"
        
        # Phase 1 Fix: Don't silence errors with || true
        # Instead, provide clear error message and continue with warning
        echo "[entrypoint] ⚠️ Continuing startup despite migration failure"
        echo "[entrypoint] Please check database manually if bot fails to start"
    fi
fi

# ============================================================
# Phase 1: Display configuration summary
# ============================================================
echo "============================================================"
echo "📋 Configuration Summary:"
echo "============================================================"
echo "Service: ${SERVICE_NAME:-unknown}"
echo "Bot Token: ${BOT_TOKEN:0:10}..." # Show only first 10 chars for security
echo "API ID: ${API_ID}"
echo "Admin IDs: ${ADMIN_IDS:-Not configured}"
echo "RapidAPI: ${RAPIDAPI_KEY:+Configured}"
echo "FFmpeg: $(which ffmpeg)"
echo "Python: $(python3 --version)"
echo "============================================================"

# ============================================================
# Phase 1: Start the service
# ============================================================
echo "[entrypoint] Starting service: $@"
echo "============================================================"

# اجرای دستور اصلی
exec "$@"
