import  os


# database config
# Set this to True only if you have a MySQL server running and reachable.
USE_MYSQL = False

db_config = {
    'host': "localhost",
    'user': "admin",
    'password': "VK@b0L]JGr*7",
    'database': "bot_db",
}


BOT_TOKEN = os.environ.get("BOT_TOKEN","5039797268:AAFPTcbAFnU_bAI3hM2NYtxwwKNsTaW9BcU")
APP_ID = int(os.environ.get("API_ID",240370))
API_HASH = os.environ.get("API_HASH","72d80cacfb03c0fb102cad46f8471519")

youtube_next_fetch = 1  # time in minute

EDIT_TIME = 5