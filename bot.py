from pyrogram import Client
from plugins.db_wrapper import DB
import config as config
from logging import basicConfig, ERROR

DOWNLOAD_LOCATION = "./Downloads"
BOT_TOKEN = config.BOT_TOKEN

APP_ID = config.APP_ID
API_HASH = config.API_HASH

# Logging
basicConfig(
    level=ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='./loader.log'
)

plugins = dict(
    root="plugins",
)

# proxies = dict(
#         hostname="192.111.129.145",
#         port=16894,
#     )
DB().setup()
Client(
    "ytdownloader3_dev2",
    bot_token=BOT_TOKEN,
    api_id=APP_ID,
    api_hash=API_HASH,
    plugins=plugins,
    workers=16,
 
).run()
