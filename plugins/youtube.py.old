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
        # تنظیم yt-dlp بدون وابستگی به کوکی‌ها
        youtube_logger.debug("شروع تنظیم yt-dlp بدون کوکی")
        use_cookies = False

        # Security: Use environment variable for ffmpeg path or auto-detect
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
        
        # Helper: pick proxy from environment if available
        def _get_env_proxy():
            return os.environ.get('PROXY') or os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')

        env_proxy = _get_env_proxy()

        ydl_opts = {
            'quiet': True,
            'simulate': True,
            'cookies': 'cookie_youtube.txt',
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
            # استفاده از کلاینت mweb که به PO Token نیاز دارد
            'extractor_args': {
                'player_client': ['mweb'],
            },
            # تنظیمات اضافی برای مدیریت rate limit
            'sleep_interval': 5,     # تأخیر 5 ثانیه بین درخواست‌ها
            'max_sleep_interval': 10,
            'sleep_interval_requests': 1,
        }
        if env_proxy:
            ydl_opts['proxy'] = env_proxy
        
        if ffmpeg_path:
            ydl_opts['ffmpeg_location'] = ffmpeg_path
            
        # همیشه ابتدا سعی کن از فایل کوکی استفاده کنی
        cookie_id_used = None
        try:
            cookiefile, cid = get_cookie_file_with_fallback(None)
            if cookiefile:
                ydl_opts['cookiefile'] = cookiefile
                cookie_id_used = cid
                if cid == -1:
                    youtube_logger.info("استفاده از کوکی اصلی cookie_youtube.txt برای استخراج اطلاعات")
                else:
                    youtube_logger.info(f"استفاده از کوکی استخر برای استخراج اطلاعات: id={cid}")
        except Exception:
            pass

        # Run extraction in a background thread to avoid blocking the event loop
        extraction_start = time.time()
        performance_logger.info(f"[USER:{user_id}] Starting yt-dlp extraction...")
        youtube_logger.debug("شروع استخراج اطلاعات ویدیو با yt-dlp")
        
        try:
            info = await asyncio.to_thread(lambda: YoutubeDL(ydl_opts).extract_info(url, download=False))
            if not info:
                raise RuntimeError("اطلاعاتی از yt-dlp دریافت نشد")
            youtube_logger.debug(f"استخراج اطلاعات موفق: عنوان={info.get('title', 'نامشخص')}, مدت={info.get('duration', 0)} ثانیه")
            
            # اگر از کوکی استفاده شد و موفق بود، ثبت کن
            if cookie_id_used:
                try:
                    mark_cookie_used(cookie_id_used, True)
                except Exception:
                    pass
                
        finally:
            # وابستگی کوکی حذف شده است؛ نیازی به پاک‌سازی فایل کوکی نیست
            pass
        
        extraction_end = time.time()
        extraction_time = extraction_end - extraction_start
        performance_logger.info(f"[USER:{user_id}] yt-dlp extraction completed in: {extraction_time:.2f} seconds")
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
        performance_logger.error(f"[USER:{user_id}] yt-dlp extraction failed: {err_text}")
        youtube_logger.error(f"خطا در استخراج اطلاعات: {err_text}")
        print(f"Error processing YouTube link: {err_text}")

        # Helper to determine if a cookie might be needed
        def _needs_cookie(msg: str) -> bool:
            msg_l = (msg or '').lower()
            hints = ['login required', 'sign in', 'age', 'restricted', 'private', 'consent', 'unavailable']
            return any(h in msg_l for h in hints)

        # Helper function for cookie-based extraction with retries
        async def _extract_info_with_cookie_retry(url, ydl_opts, env_proxy, user_id, max_retries=3):
            info = None
            last_error = None
            
            for attempt in range(max_retries):
                current_cookiefile = None
                current_cookie_id = None
                try:
                    # Always try to get a new rotated cookie for each attempt
                    current_cookiefile, current_cookie_id = get_rotated_cookie_file(None)
                    
                    if current_cookiefile:
                        opts = dict(ydl_opts)
                        opts['cookiefile'] = current_cookiefile
                        if env_proxy:
                            opts['proxy'] = env_proxy
                        
                        performance_logger.info(f"[USER:{user_id}] Retrying with cookie (attempt {attempt+1}/{max_retries}), cookie_id={current_cookie_id}...")
                        youtube_logger.debug(f"تلاش مجدد با کوکی (تلاش {attempt+1}/{max_retries})")
                        
                        info = await asyncio.to_thread(lambda: YoutubeDL(opts).extract_info(url, download=False))
                        
                        if info:
                            mark_cookie_used(current_cookie_id, True)
                            youtube_logger.debug(f"استخراج اطلاعات با کوکی موفق: عنوان={info.get('title', 'نامشخص')}")
                            return info # Success, return info
                        else:
                            # If info is None but no exception, mark cookie as bad
                            mark_cookie_used(current_cookie_id, False)
                            last_error = "اطلاعاتی از yt-dlp دریافت نشد با کوکی"
                    else:
                        last_error = "کوکی معتبری برای تلاش مجدد یافت نشد"
                        youtube_logger.warning(f"کوکی معتبری برای تلاش مجدد یافت نشد در تلاش {attempt+1}")

                except Exception as ce:
                    last_error = str(ce)
                    youtube_logger.error(f"خطا در تلاش با کوکی (تلاش {attempt+1}): {ce}")
                    if current_cookie_id:
                        try:
                            mark_cookie_used(current_cookie_id, False)
                        except Exception:
                            pass
                
                # Small delay before next retry
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0 * (attempt + 1)) # Exponential backoff

            # If all retries fail
            if last_error:
                raise RuntimeError(f"تمام تلاش‌ها برای استخراج با کوکی شکست خورد: {last_error}")
            return None # Should not reach here if max_retries > 0 and no info found

        info = None
        
        # If the initial error suggests a cookie is needed, or if it's a general failure, try with rotated cookies.
        # We will try up to 3 times with different cookies if available.
        if _needs_cookie(err_text) or "اطلاعاتی از yt-dlp دریافت نشد" in err_text or "HTTP Error 403" in err_text or "HTTP Error 401" in err_text:
            try:
                info = await _extract_info_with_cookie_retry(url, ydl_opts, env_proxy, user_id, max_retries=3)
            except RuntimeError as re:
                youtube_logger.error(f"خطا در تلاش‌های جایگزین با کوکی: {re}")
                err_text = str(re) # Update error text for final message
            except Exception as ce:
                youtube_logger.error(f"خطا در تابع _extract_info_with_cookie_retry: {ce}")
                err_text = str(ce) # Update error text for final message

        if info:
            # Successful fallback
            with open("yt_dlp_info_fallback.json", "w", encoding="utf-8") as f:
                json.dump(info, f, ensure_ascii=False, indent=4)
            print("Fallback extracted info written to yt_dlp_info_fallback.json")
            step['link'] = info
            step['title'] = info.get('title', 'Unknown Title')
            step['duration'] = info.get('duration', 0)
            step['thumbnail'] = info.get('thumbnail', None)

            await display_video_info_with_cover(client, processing_message, info)

            end_time = time.time()
            total_time = end_time - start_time
            performance_logger.info(f"[USER:{user_id}] FALLBACK TOTAL TIME: {total_time:.2f} seconds")
            if total_time > 8.0:
                performance_logger.warning(f"[USER:{user_id}] ⚠️ SLOW FALLBACK: {total_time:.2f}s (Target: <8s)")
            else:
                performance_logger.info(f"[USER:{user_id}] ✅ GOOD PERFORMANCE: {total_time:.2f}s (Target: <8s)")
        else:
            # Fallback also failed
            performance_logger.error(f"[USER:{user_id}] Fallback extraction also failed: {err_text}")
            youtube_logger.error("استخراج جایگزین نیز ناکام ماند؛ info=None")
            try:
                await processing_message.edit_text(
                    "❌ **خطا در پردازش لینک یوتیوب**\n\n"
                    f"امکان دریافت اطلاعات ویدیو وجود ندارد. جزئیات: {err_text}\n"
                    "راهکارها: استفاده از کوکی معتبر، بررسی پراکسی سیستم، یا تلاش دوباره.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                await processing_message.edit_text("خطا در پردازش لینک یوتیوب. لطفاً دوباره تلاش کنید.")
            return
