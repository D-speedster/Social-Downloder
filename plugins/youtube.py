from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from plugins.start import step, join
from plugins.db_wrapper import DB
from datetime import datetime
from yt_dlp import YoutubeDL
from plugins import constant
import os
import json
import asyncio

txt = constant.TEXT


@Client.on_message(filters.regex(r"^(?:https?://)?(?:www\.)?(?:m\.)?(?:youtube\.com|youtu\.be)/") & filters.private & join)
async def show_video(client: Client, message: Message):
    user_id = message.from_user.id
    now = datetime.now()

    # Enforce daily limit: if user is currently blocked, stop here
    try:
        blocked_until_str = DB().get_blocked_until(user_id)
        if blocked_until_str:
            bu = None
            try:
                bu = datetime.fromisoformat(blocked_until_str)
            except Exception:
                try:
                    bu = datetime.strptime(blocked_until_str, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    bu = None
            if bu and now < bu:
                seconds = int((bu - now).total_seconds())
                await message.reply_text(txt['rate_limit'].format(seconds=seconds))
                return
    except Exception as e:
        print(f"Error checking blocked_until: {e}")

    url = message.text
    processing_message = await message.reply_text("در حال پردازش لینک یوتیوب...")

    try:
        # Configure yt-dlp with cookies for authentication (conditionally)
        cookies_path = os.path.join(os.getcwd(), 'cookies', 'youtube.txt')
        use_cookies = os.path.exists(cookies_path)
        if not use_cookies:
            print(f"Warning: YouTube cookies file not found at {cookies_path}")

        ydl_opts = {
            'quiet': True,
            'ffmpeg_location': "C:\\ffmpeg\\bin\\ffmpeg.exe",
            'simulate': True,
            'extractor_retries': 3,
            'fragment_retries': 3,
            'retry_sleep_functions': {'http': lambda n: min(4 ** n, 60)}
        }
        if use_cookies:
            ydl_opts['cookiefile'] = cookies_path

        # Run extraction in a background thread to avoid blocking the event loop
        info = await asyncio.to_thread(lambda: YoutubeDL(ydl_opts).extract_info(url, download=False))
        with open("yt_dlp_info.json", "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=4)
        print("Extracted info written to yt_dlp_info.json")
        step['link'] = info
        step['title'] = info.get('title', 'Unknown Title')
        step['duration'] = info.get('duration', 0)
        step['thumbnail'] = info.get('thumbnail', None)

        keyboard = [
            [InlineKeyboardButton(txt['video'], callback_data='1')],
            [InlineKeyboardButton(txt['sound'], callback_data='2')],
            [InlineKeyboardButton(txt['cover'], callback_data='3')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await processing_message.edit_text(txt['select_type'], reply_markup=reply_markup)

    except Exception as e:
        print(f"Error processing YouTube link: {e}")
        # If cookies are invalid or verification is required, show explicit error
        if "Sign in to confirm you’re not a bot" in str(e) or "account cookies are no longer valid" in str(e) or "cookies" in str(e).lower():
            await processing_message.edit_text("کوکی‌های یوتیوب نامعتبر است. فایل cookies/youtube.txt را به‌روزرسانی کنید.")
            return
        # Try alternative extraction methods without cookies
        try:
            fallback_opts = {
                'quiet': True,
                'simulate': True,
                'extractor_retries': 3,
                'fragment_retries': 3,
                'retry_sleep_functions': {'http': lambda n: min(4 ** n, 60)}
            }
            info = await asyncio.to_thread(lambda: YoutubeDL(fallback_opts).extract_info(url, download=False))
            with open("yt_dlp_info_fallback.json", "w", encoding="utf-8") as f:
                json.dump(info, f, ensure_ascii=False, indent=4)
            print("Fallback extracted info written to yt_dlp_info_fallback.json")
            step['link'] = info
            step['title'] = info.get('title', 'Unknown Title')
            step['duration'] = info.get('duration', 0)
            step['thumbnail'] = info.get('thumbnail', None)

            keyboard = [
                [InlineKeyboardButton(txt['video'], callback_data='1')],
                [InlineKeyboardButton(txt['sound'], callback_data='2')],
                [InlineKeyboardButton(txt['cover'], callback_data='3')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await processing_message.edit_text(txt['select_type'], reply_markup=reply_markup)
        except Exception as fallback_error:
            print(f"Fallback extraction also failed: {fallback_error}")
            await processing_message.edit_text(txt['youtube_error'])
            return
