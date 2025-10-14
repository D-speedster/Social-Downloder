import os
import json
from .db_path_manager import db_path_manager

PATH = os.path.dirname(os.path.realpath(__file__))
TEXT = json.loads(open(PATH + '/txt.json', encoding='utf-8').read())

# Use external database path for JSON database
db_path_manager.ensure_database_directory()
db_path_manager.migrate_existing_database()
json_db_path = db_path_manager.get_json_db_path()

# Create empty JSON database if it doesn't exist
if not os.path.exists(json_db_path):
    with open(json_db_path, 'w', encoding='utf-8') as f:
        json.dump({}, f)

DATA = json.loads(open(json_db_path, encoding='utf-8').read())
# INSTA_DATA = json.loads(open(PATH + '/instagram_acc.json', encoding='utf-8').read())