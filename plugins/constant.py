import os
import json

PATH = os.path.dirname(os.path.realpath(__file__))
TEXT = json.loads(open(PATH + '/txt.json', encoding='utf-8').read())

# ✅ Use local database.json in plugins directory
json_db_path = os.path.join(PATH, 'database.json')

# Create empty JSON database if it doesn't exist
if not os.path.exists(json_db_path):
    with open(json_db_path, 'w', encoding='utf-8') as f:
        json.dump({}, f)

DATA = json.loads(open(json_db_path, encoding='utf-8').read())
# INSTA_DATA = json.loads(open(PATH + '/instagram_acc.json', encoding='utf-8').read())