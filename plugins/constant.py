import os
import json

PATH = os.path.dirname(os.path.realpath(__file__))
TEXT = json.loads(open(PATH + '/txt.json', encoding='utf-8').read())
DATA = json.loads(open(PATH + '/database.json', encoding='utf-8').read())
# INSTA_DATA = json.loads(open(PATH + '/instagram_acc.json', encoding='utf-8').read())