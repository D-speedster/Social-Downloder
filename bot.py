from pyrogram import Client
from plugins.sqlite_db_wrapper import DB
import config as config
from logging import basicConfig, ERROR, INFO
import os
import sys
import atexit
import signal
from dotenv import load_dotenv
import os
load_dotenv()
# Security: Validate configuration before starting
try:
    BOT_TOKEN = config.BOT_TOKEN
    APP_ID = config.APP_ID
    API_HASH = config.API_HASH
except AttributeError as e:
    print(f"Configuration error: {e}")
    print("Please ensure all required environment variables are set.")
    sys.exit(1)

# Create downloads directory with proper permissions
DOWNLOAD_LOCATION = "./Downloads"
try:
    os.makedirs(DOWNLOAD_LOCATION, mode=0o750, exist_ok=True)
except Exception as e:
    print(f"Warning: Could not create downloads directory: {e}")

# Enhanced logging with rotation and better format
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
basicConfig(
    level=INFO,  # Changed to INFO for better debugging
    format=log_format,
    filename='./loader.log',
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

try:
    client = Client(
        "ytdownloader3_dev2",
        bot_token=BOT_TOKEN,
        api_id=APP_ID,
        api_hash=API_HASH,
        plugins=plugins,
        workers=MAX_WORKERS,
        sleep_threshold=60,  # Add sleep threshold to prevent flood
    )
    
    logger.info("Starting bot client...")
    client.run()
except KeyboardInterrupt:
    logger.info("Bot stopped by user")
except Exception as e:
    logger.error(f"Bot startup failed: {e}")
    sys.exit(1)
finally:
    # Ensure database is closed
    try:
        if 'db' in locals():
            db.close()
            logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database in finally block: {e}")
