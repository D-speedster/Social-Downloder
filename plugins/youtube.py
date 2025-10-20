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
from plugins.cookie_manager import get_rotated_cookie_file, mark_cookie_used, get_cookie_file_with_fallback
from plugins.youtube_helpers import safe_extract_info

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

# تنظیم لاگ‌گذاری اصلی برای یوتیوب
os.makedirs('./logs', exist_ok=True)
youtube_logger = logging.getLogger('youtube_main')
youtube_handler = logging.FileHandler('./logs/youtube_main.log', encoding='utf-8')
youtube_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
youtube_handler.setFormatter(youtube_formatter)
youtube_logger.addHandler(youtube_handler)
youtube_logger.setLevel(logging.DEBUG)

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
    
    youtube_logger.info(f"درخواست پردازش یوتیوب از کاربر {user_id}")
    youtube_logger.debug(f"URL دریافتی: {message.text}")

    # Enforce daily limit: if user is currently blocked, stop here
    try:
        blocked_until_str = DB().get_blocked_until(user_id)
        youtube_logger.debug(f"بررسی محدودیت برای کاربر {user_id}")
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
                youtube_logger.warning(f"کاربر {user_id} محدود شده تا {bu}")
                await message.reply_text(txt['rate_limit'].format(seconds=seconds))
                return
    except Exception as e:
        youtube_logger.error(f"خطا در بررسی محدودیت: {e}")
        print(f"Error checking blocked_until: {e}")
        # Continue execution even if blocked_until check fails
        pass

    url = message.text
    
    # Start timing the process
    start_time = time.time()
    performance_logger.info(f"[USER:{user_id}] YouTube link processing started for: {url}")
    youtube_logger.info(f"شروع پردازش لینک یوتیوب برای کاربر {user_id}")
    
    # Get custom waiting message from database
    db = DB()
    custom_message_data = db.get_waiting_message_full('youtube')
    youtube_logger.debug(f"پیام انتظار سفارشی: {custom_message_data}")
    
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
    youtube_logger.debug(f"پیام پردازش ارسال شد در {message_sent_time - start_time:.2f} ثانیه")

    try:
        # Security: Use environment variable for ffmpeg path or auto-detect (kept for future use)
        ffmpeg_path = os.environ.get('FFMPEG_PATH')
        try:
            if (not ffmpeg_path) and sys.platform.startswith('linux') and os.path.exists('/usr/bin/ffmpeg'):
                ffmpeg_path = '/usr/bin/ffmpeg'
        except Exception:
            pass
        if not ffmpeg_path:
            # Try common locations
            from config import FFMPEG_PATH
            common_paths = [
                FFMPEG_PATH,
                "ffmpeg",  # If in PATH
                "/usr/local/bin/ffmpeg"  # macOS
            ]
            for path in common_paths:
                if shutil.which(path) or os.path.exists(path):
                    ffmpeg_path = path
                    break
        youtube_logger.debug(f"مسیر ffmpeg: {ffmpeg_path}")
        
        # Run extraction in a background thread via safe wrapper
        extraction_start = time.time()
        performance_logger.info(f"[USER:{user_id}] Starting safe info extraction...")
        youtube_logger.debug("شروع استخراج اطلاعات ویدیو با safe_extract_info")
        
        info = await safe_extract_info(url, base_opts={'format': 'best[height>=720]/best[height>=480]/best'})
        if not info:
            raise RuntimeError("اطلاعاتی از yt-dlp دریافت نشد")
        youtube_logger.debug(f"استخراج اطلاعات موفق: عنوان={info.get('title', 'نامشخص')}, مدت={info.get('duration', 0)} ثانیه")
        
        extraction_end = time.time()
        extraction_time = extraction_end - extraction_start
        performance_logger.info(f"[USER:{user_id}] info extraction completed in: {extraction_time:.2f} seconds")
        youtube_logger.debug(f"استخراج اطلاعات تکمیل شد در {extraction_time:.2f} ثانیه")
        
        if info:
            with open("yt_dlp_info.json", "w", encoding="utf-8") as f:
                json.dump(info, f, ensure_ascii=False, indent=4)
            print("Extracted info written to yt_dlp_info.json")
            step['link'] = info
            step['title'] = info.get('title', 'Unknown Title')
            step['duration'] = info.get('duration', 0)
            step['thumbnail'] = info.get('thumbnail', None)
            youtube_logger.debug(f"اطلاعات ویدیو ذخیره شد: {step['title']}")

        # Download and display cover with video info
        youtube_logger.debug("شروع نمایش اطلاعات ویدیو و کاور")
        await display_video_info_with_cover(client, processing_message, info)
        youtube_logger.debug("نمایش اطلاعات ویدیو تکمیل شد")
        
        end_time = time.time()
        total_time = end_time - start_time
        performance_logger.info(f"[USER:{user_id}] TOTAL PROCESSING TIME: {total_time:.2f} seconds")
        performance_logger.info(f"[USER:{user_id}] Breakdown - Message: {message_sent_time - start_time:.2f}s, Extraction: {extraction_time:.2f}s, UI: {end_time - extraction_end:.2f}s")
        youtube_logger.info(f"زمان کل پردازش: {total_time:.2f} ثانیه")
        
        # Alert if processing time exceeds target
        if total_time > 8.0:
            performance_logger.warning(f"[USER:{user_id}] ⚠️ SLOW PROCESSING: {total_time:.2f}s (Target: <8s)")
            youtube_logger.warning(f"پردازش کند: {total_time:.2f} ثانیه (هدف: کمتر از 8 ثانیه)")
        else:
            performance_logger.info(f"[USER:{user_id}] ✅ GOOD PERFORMANCE: {total_time:.2f}s (Target: <8s)")
            youtube_logger.info(f"عملکرد خوب: {total_time:.2f} ثانیه")

    except Exception as e:
        err_text = str(e)
        performance_logger.error(f"[USER:{user_id}] info extraction failed: {err_text}")
        youtube_logger.error(f"خطا در استخراج اطلاعات: {err_text}")
        print(f"Error processing YouTube link: {err_text}")
        
        try:
            await processing_message.edit_text(
                "❌ **خطا در پردازش لینک یوتیوب**\n\n"
                "امکان دریافت اطلاعات ویدیو وجود ندارد.\n"
                "راهکارها: استفاده از کوکی معتبر، بررسی پراکسی سیستم، یا تلاش دوباره.",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            await processing_message.edit_text("خطا در پردازش لینک یوتیوب. لطفاً دوباره تلاش کنید.")
        return
