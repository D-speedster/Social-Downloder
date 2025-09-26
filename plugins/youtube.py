from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from pyrogram.enums import ParseMode
from plugins.start import step, join
from plugins.sqlite_db_wrapper import DB
from datetime import datetime
from yt_dlp import YoutubeDL
import yt_dlp
from plugins import constant
import os
import json
import asyncio
import shutil
import time
import logging
import sys

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


async def display_video_info_with_cover(client: Client, message, info):
    """Display video cover, title, duration and download options"""
    try:
        # Get video information
        title = info.get('title', 'عنوان نامشخص')
        duration = info.get('duration', 0)
        thumbnail_url = info.get('thumbnail', None)
        uploader = info.get('uploader', 'نامشخص')
        view_count = info.get('view_count', 0)
        
        # Format duration
        if duration:
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            seconds = duration % 60
            if hours > 0:
                duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                duration_str = f"{minutes:02d}:{seconds:02d}"
        else:
            duration_str = "نامشخص"
        
        # Format view count
        if view_count:
            if view_count >= 1000000:
                view_str = f"{view_count/1000000:.1f}M"
            elif view_count >= 1000:
                view_str = f"{view_count/1000:.1f}K"
            else:
                view_str = str(view_count)
        else:
            view_str = "نامشخص"
        
        # Create caption with video info
        caption = f"🎬 **{title}**\n\n"
        caption += f"⏱ مدت زمان: {duration_str}\n"
        caption += f"👤 کانال: {uploader}\n"
        caption += f"👁 بازدید: {view_str}\n\n"
        caption += "📥 **گزینه دانلود را انتخاب کنید:**"
        
        # Create glass-style buttons
        keyboard = [
            [InlineKeyboardButton("🎥 ویدیو (با صدا)", callback_data='1')],
            [InlineKeyboardButton("🔊 فقط صدا", callback_data='2')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send photo with caption if thumbnail exists
        if thumbnail_url:
            try:
                await message.edit_text("در حال دانلود کاور...")
                # Send photo and store the new message
                photo_message = await client.send_photo(
                    chat_id=message.chat.id,
                    photo=thumbnail_url,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
                # Delete the original message after sending photo
                try:
                    await message.delete()
                except:
                    pass  # Ignore if message is already deleted
            except Exception as e:
                print(f"Error sending photo: {e}")
                # Fallback to text message if photo fails
                try:
                    await message.edit_text(
                        text=caption,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception:
                    # If edit fails, send new message
                    await client.send_message(
                        chat_id=message.chat.id,
                        text=caption,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    try:
                        await message.delete()
                    except:
                        pass

        else:
            # No thumbnail, send text message
            try:
                await message.edit_text(caption, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            except Exception as edit_error:
                print(f"Error editing message: {edit_error}")
                # Send new message if edit fails
                await client.send_message(
                    chat_id=message.chat.id,
                    text=caption,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            
    except Exception as e:
        print(f"Error in display_video_info_with_cover: {e}")
        # Fallback to simple message
        keyboard = [
            [InlineKeyboardButton("🎥 ویدیو (با صدا)", callback_data='download_video')],
            [InlineKeyboardButton("🔊 فقط صدا", callback_data='download_audio')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await message.edit_text("نوع فایل را انتخاب کنید:", reply_markup=reply_markup)


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
        # Configure yt-dlp with cookies from cookie pool
        from cookie_manager import cookie_manager
        
        # Get a cookie from the pool
        cookie_content = cookie_manager.get_cookie('youtube')
        use_cookies = cookie_content is not None
        
        if not use_cookies:
            print("Warning: No YouTube cookies available in pool")

        # Security: Use environment variable for ffmpeg path or auto-detect
        ffmpeg_path = os.environ.get('FFMPEG_PATH')
        try:
            if (not ffmpeg_path) and sys.platform.startswith('linux') and os.path.exists('/usr/bin/ffmpeg'):
                ffmpeg_path = '/usr/bin/ffmpeg'
        except Exception:
            pass
        if not ffmpeg_path:
            # Try common locations
            common_paths = [
                "C:\\ffmpeg\\bin\\ffmpeg.exe",
                "ffmpeg",  # If in PATH
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
            'format': 'best[height>=720]/best[height>=480]/best',  # Prioritize higher quality (720p+, then 480p+)
            'ignoreerrors': True,
            'no_check_certificate': True,
            'prefer_insecure': True, # Skip HTTPS when possible for speed
            'youtube_include_dash_manifest': False,  # Skip DASH manifest for speed
            'writesubtitles': False, # Skip subtitle extraction
            'writeautomaticsub': False, # Skip auto subtitles
            'writethumbnail': True, # Skip thumbnail download
            'writeinfojson': False,  # Skip info json writing
        }
        
        if ffmpeg_path:
            ydl_opts['ffmpeg_location'] = ffmpeg_path
            
        if use_cookies:
            # Write cookie content to temporary file
            import tempfile
            temp_cookie_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            temp_cookie_file.write(cookie_content)
            temp_cookie_file.close()
            ydl_opts['cookiefile'] = temp_cookie_file.name

        # Run extraction in a background thread to avoid blocking the event loop
        extraction_start = time.time()
        performance_logger.info(f"[USER:{user_id}] Starting yt-dlp extraction...")
        
        temp_cookie_file_path = None
        try:
            info = await asyncio.to_thread(lambda: YoutubeDL(ydl_opts).extract_info(url, download=False))
            
            # Update cookie usage stats
            if use_cookies:
                # Find cookie ID to update usage
                cookies = cookie_manager.get_cookies('youtube', active_only=True)
                for cookie in cookies:
                    if cookie.get('data') == cookie_content:
                        cookie_manager.update_usage('youtube', cookie['id'])
                        break
                
        finally:
            # Clean up temporary cookie file
            if use_cookies and 'temp_cookie_file' in locals():
                temp_cookie_file_path = temp_cookie_file.name
                try:
                    os.unlink(temp_cookie_file_path)
                except:
                    pass
        
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

        # Download and display cover with video info
        await display_video_info_with_cover(client, processing_message, info)
        
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
        performance_logger.error(f"[USER:{user_id}] yt-dlp extraction failed: {str(e)}")
        print(f"Error processing YouTube link: {e}")
        
        # Mark cookie as invalid if extraction failed with cookies
        if use_cookies:
            # Find cookie ID to mark as invalid
            cookies = cookie_manager.get_cookies('youtube', active_only=True)
            for cookie in cookies:
                if cookie.get('data') == cookie_content:
                    cookie_manager.mark_invalid('youtube', cookie['id'])
                    break
        
        error_msg = str(e).lower()
        # If cookies are invalid or verification is required, show explicit error
        if any(keyword in error_msg for keyword in ["sign in to confirm", "not a bot", "cookies", "authentication", "login"]):
            try:
                await processing_message.edit_text(
                    "⚠️ **مشکل احراز هویت یوتیوب**\n\n"
                    "کوکی‌های یوتیوب نامعتبر یا منقضی شده است.\n"
                    "لطفاً فایل `cookies/youtube.txt` را به‌روزرسانی کنید.\n\n"
                    "📝 **راهنمای به‌روزرسانی کوکی:**\n"
                    "1. وارد حساب یوتیوب خود شوید\n"
                    "2. کوکی‌های جدید را استخراج کنید\n"
                    "3. فایل cookies/youtube.txt را جایگزین کنید",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                await processing_message.edit_text("کوکی‌های یوتیوب نامعتبر است. فایل cookies/youtube.txt را به‌روزرسانی کنید.")
            return
        
        # Try alternative extraction methods with different cookie or without cookies
        try:
            performance_logger.info(f"[USER:{user_id}] Attempting fallback extraction...")
            
            # Try with a different cookie first
            fallback_cookie = cookie_manager.get_cookie('youtube')
            
            fallback_opts = {
                'quiet': True,
                'simulate': True,
                'extractor_retries': 0,  # No retries for maximum speed
                'fragment_retries': 0,   # No retries for maximum speed
                'socket_timeout': 5,     # Very aggressive timeout for fallback
                'connect_timeout': 3,    # Fast connection timeout
                'extract_flat': False,
                'ignoreerrors': True,
                'no_check_certificate': True,
                'prefer_insecure': True,
                'youtube_include_dash_manifest': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'writethumbnail': True,
                'writeinfojson': False,
                'format': 'best[height>=720]/best[height>=480]/best'  # Maintain quality preference even in fallback
            }
            
            if ffmpeg_path:
                fallback_opts['ffmpeg_location'] = ffmpeg_path
            
            temp_fallback_file = None
            if fallback_cookie:
                # Write fallback cookie content to temporary file
                import tempfile
                temp_fallback_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                temp_fallback_file.write(fallback_cookie)
                temp_fallback_file.close()
                fallback_opts['cookiefile'] = temp_fallback_file.name
            
            fallback_start = time.time()
            performance_logger.info(f"[USER:{user_id}] Starting fallback extraction...")
            
            try:
                info = await asyncio.to_thread(lambda: YoutubeDL(fallback_opts).extract_info(url, download=False))
                
                # Update cookie usage stats for successful fallback
                if fallback_cookie:
                    # Find cookie ID to update usage
                    cookies = cookie_manager.get_cookies('youtube', active_only=True)
                    for cookie in cookies:
                        if cookie.get('data') == fallback_cookie:
                            cookie_manager.update_usage('youtube', cookie['id'])
                            break
                    
            finally:
                # Clean up temporary fallback cookie file
                if temp_fallback_file:
                    try:
                        os.unlink(temp_fallback_file.name)
                    except:
                        pass
            
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

            # Download and display cover with video info (fallback)
            await display_video_info_with_cover(client, processing_message, info)
            
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
            performance_logger.error(f"[USER:{user_id}] Fallback extraction also failed: {str(fallback_error)}")
            print(f"Fallback extraction also failed: {fallback_error}")
            try:
                await processing_message.edit_text(
                    "❌ **خطا در پردازش لینک یوتیوب**\n\n"
                    "متأسفانه امکان دریافت اطلاعات ویدیو وجود ندارد.\n"
                    "لطفاً موارد زیر را بررسی کنید:\n\n"
                    "🔗 لینک معتبر باشد\n"
                    "🌐 اتصال اینترنت برقرار باشد\n"
                    "🔒 ویدیو در دسترس عموم باشد\n\n"
                    "در صورت تکرار مشکل، لطفاً دوباره تلاش کنید.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                await processing_message.edit_text("خطا در پردازش لینک یوتیوب. لطفاً دوباره تلاش کنید.")
            return
