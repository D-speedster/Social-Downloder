import asyncio
import os
import shutil
import sys
import aiohttp
import requests
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
# from plugins.settings import (
#     RAPIDAPI_KEY,
# )

# Direct API key definition
RAPIDAPI_KEY = "d51a95d960mshb5f65a8e122bb7fp11b675jsn63ff66cbc6cf"
from plugins.media_utils import send_advertisement, download_stream_to_file
from plugins.universal_downloader import handle_universal_link

# Logging setup
instagram_logger = logging.getLogger(__name__)
instagram_logger.setLevel(logging.DEBUG)
instagram_handler = logging.FileHandler('./logs/instagram.log', encoding='utf-8')
instagram_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
instagram_logger.addHandler(instagram_handler)

instaregex = r"https?:\/\/(www\.)?instagram\.com\/(p|reel|tv)\/([a-zA-Z0-9_-]+)"

async def get_instagram_data(url: str):
    """Get Instagram data using RapidAPI with SSL error handling and retry mechanism"""
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            instagram_logger.debug(f"شروع درخواست API برای URL: {url} (تلاش {attempt + 1}/{max_retries})")
            
            payload = {"url": url}
            
            headers = {
                'x-rapidapi-key': RAPIDAPI_KEY,
                'x-rapidapi-host': "social-download-all-in-one.p.rapidapi.com",
                'Content-Type': "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://social-download-all-in-one.p.rapidapi.com/v1/social/autolink",
                    json=payload,
                    headers=headers,
                    timeout=30,
                ) as response:
                    instagram_logger.debug(f"وضعیت پاسخ API: {response.status}")
                    
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        instagram_logger.error(f"خطای API: وضعیت {response.status}, پاسخ: {error_text[:500]}")
                        if attempt == max_retries - 1:
                            return {"status": "error", "message": f"API request failed with status {response.status}"}

        except aiohttp.ClientError as e:
            instagram_logger.error(f"AIOHTTP Client Error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                return {"status": "error", "message": "A network error occurred."}
        
        await asyncio.sleep(2)  # Wait before retrying
    
    return {"status": "error", "message": "All API request attempts failed."}

@Client.on_message(filters.regex(instaregex) & filters.private)
async def download_instagram_new(_: Client, message: Message):
    url = message.text.strip()
    user_id = message.from_user.id
    instagram_logger.info(f"درخواست دانلود اینستاگرام از کاربر {user_id}: {url}")

    # Use the universal downloader directly for Instagram links
    return await handle_universal_link(_, message)