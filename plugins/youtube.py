from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from plugins.start import step, join
from plugins.sqlite_db_wrapper import DB
from datetime import datetime
from yt_dlp import YoutubeDL
from plugins import constant
import os
import json
import asyncio
import shutil
import time
import logging

# Configure logging for performance monitoring
import os
log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'youtube_performance.log')

# Create performance logger with specific handler
performance_logger = logging.getLogger('youtube_performance')
performance_logger.setLevel(logging.INFO)

# Remove any existing handlers to avoid duplicates
for handler in performance_logger.handlers[:]:
    performance_logger.removeHandler(handler)

# Add file handler for performance logging
file_handler = logging.FileHandler(log_path, encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
performance_logger.addHandler(file_handler)

# Prevent propagation to root logger
performance_logger.propagate = False

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
        # Continue execution even if blocked_until check fails
        pass

    url = message.text
    
    # Start timing the process
    start_time = time.time()
    performance_logger.info(f"[USER:{user_id}] YouTube link processing started for: {url}")
    
    # Get custom waiting message from database
    db = DB()
    custom_message_data = db.get_waiting_message_full('youtube')
    
    # Send initial processing message with timing
    if custom_message_data and custom_message_data.get('type') == 'gif':
        processing_message = await message.reply_animation(
            animation=custom_message_data['content'],
            caption="در حال پردازش لینک یوتیوب..."
        )
    elif custom_message_data and custom_message_data.get('type') == 'sticker':
        await message.reply_sticker(sticker=custom_message_data['content'])
        processing_message = await message.reply_text("در حال پردازش لینک یوتیوب...")
    else:
        # Text message (default or custom)
        waiting_text = custom_message_data.get('content', "در حال پردازش لینک یوتیوب...") if custom_message_data else "در حال پردازش لینک یوتیوب..."
        processing_message = await message.reply_text(waiting_text)
    
    message_sent_time = time.time()
    performance_logger.info(f"[USER:{user_id}] Processing message sent after: {message_sent_time - start_time:.2f} seconds")

    try:
        # Configure yt-dlp with cookies for authentication (conditionally)
        cookies_path = os.path.join(os.getcwd(), 'cookies', 'youtube.txt')
        use_cookies = os.path.exists(cookies_path)
        if not use_cookies:
            print(f"Warning: YouTube cookies file not found at {cookies_path}")

        # Security: Use environment variable for ffmpeg path or auto-detect
        ffmpeg_path = os.environ.get('FFMPEG_PATH')
        if not ffmpeg_path:
            # Try common locations
            common_paths = [
                "C:\\ffmpeg\\bin\\ffmpeg.exe",
                "ffmpeg",  # If in PATH
                "/usr/bin/ffmpeg",  # Linux
                "/usr/local/bin/ffmpeg"  # macOS
            ]
            for path in common_paths:
                if shutil.which(path) or os.path.exists(path):
                    ffmpeg_path = path
                    break
        
        ydl_opts = {
            'quiet': True,
            'simulate': True,
            'extractor_retries': 0,  # No retries for maximum speed
            'fragment_retries': 0,   # No retries for maximum speed
            'socket_timeout': 8,     # Aggressive timeout for speed
            'connect_timeout': 5,    # Connection timeout
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
            'format': 'best[height<=480]/best',  # Prioritize lower quality for faster extraction
            'ignoreerrors': True,
            'no_check_certificate': True,
            'prefer_insecure': True, # Skip HTTPS when possible for speed
            'youtube_include_dash_manifest': False,  # Skip DASH manifest for speed
            'writesubtitles': False, # Skip subtitle extraction
            'writeautomaticsub': False, # Skip auto subtitles
            'writethumbnail': False, # Skip thumbnail download
            'writeinfojson': False,  # Skip info json writing
        }
        
        if ffmpeg_path:
            ydl_opts['ffmpeg_location'] = ffmpeg_path
            
        if use_cookies:
            ydl_opts['cookiefile'] = cookies_path

        # Run extraction in a background thread to avoid blocking the event loop
        extraction_start = time.time()
        performance_logger.info(f"[USER:{user_id}] Starting yt-dlp extraction...")
        
        info = await asyncio.to_thread(lambda: YoutubeDL(ydl_opts).extract_info(url, download=False))
        
        extraction_end = time.time()
        extraction_time = extraction_end - extraction_start
        performance_logger.info(f"[USER:{user_id}] yt-dlp extraction completed in: {extraction_time:.2f} seconds")
        
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
        
        # Send the selection message and log total time
        await processing_message.edit_text(txt['select_type'], reply_markup=reply_markup)
        
        end_time = time.time()
        total_time = end_time - start_time
        performance_logger.info(f"[USER:{user_id}] TOTAL PROCESSING TIME: {total_time:.2f} seconds")
        performance_logger.info(f"[USER:{user_id}] Breakdown - Message: {message_sent_time - start_time:.2f}s, Extraction: {extraction_time:.2f}s, UI: {end_time - extraction_end:.2f}s")
        
        # Alert if processing time exceeds target
        if total_time > 8.0:
            performance_logger.warning(f"[USER:{user_id}] ⚠️ SLOW PROCESSING: {total_time:.2f}s (Target: <8s)")
        else:
            performance_logger.info(f"[USER:{user_id}] ✅ GOOD PERFORMANCE: {total_time:.2f}s (Target: <8s)")

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
                'extractor_retries': 0,  # No retries for maximum speed
                'fragment_retries': 0,   # No retries for maximum speed
                'socket_timeout': 5,     # Very aggressive timeout for fallback
                'connect_timeout': 3,    # Fast connection timeout
                'extract_flat': False,
                'skip_download': True,
                'ignoreerrors': True,
                'no_check_certificate': True,
                'prefer_insecure': True,
                'youtube_include_dash_manifest': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'writethumbnail': False,
                'writeinfojson': False,
                'format': 'worst/best'  # Use worst quality for fastest fallback
            }
            fallback_start = time.time()
            performance_logger.info(f"[USER:{user_id}] Starting fallback extraction...")
            
            info = await asyncio.to_thread(lambda: YoutubeDL(fallback_opts).extract_info(url, download=False))
            
            fallback_end = time.time()
            fallback_time = fallback_end - fallback_start
            performance_logger.info(f"[USER:{user_id}] Fallback extraction completed in: {fallback_time:.2f} seconds")
            
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
            
            # Log fallback total time
            end_time = time.time()
            total_time = end_time - start_time
            performance_logger.info(f"[USER:{user_id}] FALLBACK TOTAL TIME: {total_time:.2f} seconds")
            performance_logger.info(f"[USER:{user_id}] Fallback breakdown - Message: {message_sent_time - start_time:.2f}s, Extraction: {fallback_time:.2f}s")
            
            if total_time > 8.0:
                performance_logger.warning(f"[USER:{user_id}] ⚠️ SLOW FALLBACK: {total_time:.2f}s (Target: <8s)")
            else:
                performance_logger.info(f"[USER:{user_id}] ✅ GOOD FALLBACK: {total_time:.2f}s (Target: <8s)")
        except Exception as fallback_error:
            print(f"Fallback extraction also failed: {fallback_error}")
            await processing_message.edit_text(txt['youtube_error'])
            return
