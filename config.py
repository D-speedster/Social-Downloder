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
APP_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")

# Validate required environment variables
if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN environment variable is required")
    sys.exit(1)
    
if not APP_ID:
    print("ERROR: API_ID environment variable is required")
    sys.exit(1)
    
if not API_HASH:
    print("ERROR: API_HASH environment variable is required")
    sys.exit(1)

# Convert API_ID to int with error handling
try:
    APP_ID = int(APP_ID)
except (ValueError, TypeError):
    print("ERROR: API_ID must be a valid integer")
    sys.exit(1)

youtube_next_fetch = 1  # time in minute

EDIT_TIME = 5