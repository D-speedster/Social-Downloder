from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo
from plugins import constant
from plugins.sqlite_db_wrapper import DB
from datetime import datetime
from dateutil import parser
import os, re, time, asyncio
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import MessageNotModified
import os
from utils.util import convert_size
from plugins.start import join
import http.client
import json
import urllib.request
import random
import subprocess
import shutil
import sys
import requests
import logging

# Configure Instagram logger
instagram_logger = logging.getLogger('instagram_main')
instagram_logger.setLevel(logging.DEBUG)

# Create logs directory if it doesn't exist
os.makedirs('./logs', exist_ok=True)

instagram_handler = logging.FileHandler('./logs/instagram_main.log', encoding='utf-8')
instagram_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
instagram_handler.setFormatter(instagram_formatter)
instagram_logger.addHandler(instagram_handler)

# Advertisement function
async def send_advertisement(client: Client, user_id: int):
    """Send advertisement to user based on database settings"""
    try:
        # Load advertisement settings from database
        with open(PATH + '/database.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        ad_settings = data.get('advertisement', {})
        
        # Check if advertisement is enabled
        if not ad_settings.get('enabled', False):
            return
        
        content_type = ad_settings.get('content_type', 'text')
        content = ad_settings.get('content', '')
        file_id = ad_settings.get('file_id', '')
        caption = ad_settings.get('caption', '')
        
        # Send advertisement based on content type
        if content_type == 'text' and content:
            await client.send_message(
                chat_id=user_id,
                text=content
            )
        elif content_type == 'photo' and file_id:
            try:
                # If the file_id is a URL, download locally to avoid WEBPAGE_MEDIA_EMPTY
                if isinstance(file_id, str) and (file_id.startswith('http://') or file_id.startswith('https://')):
                    temp_name = f"ad_photo_{int(time.time())}.jpg"
                    temp_path = os.path.join(PATH, temp_name)
                    try:
                        resp = requests.get(file_id, stream=True, timeout=20)
                        if resp.status_code == 200:
                            with open(temp_path, 'wb') as f:
                                for chunk in resp.iter_content(8192):
                                    if chunk:
                                        f.write(chunk)
                            if os.path.getsize(temp_path) > 0:
                                await client.send_photo(
                                    chat_id=user_id,
                                    photo=temp_path,
                                    caption=caption
                                )
                            else:
                                raise Exception("Downloaded advertisement photo is empty")
                        else:
                            raise Exception(f"Ad photo download failed: status {resp.status_code}")
                    finally:
                        try:
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                        except Exception:
                            pass
                else:
                    # Telegram file_id or local path
                    await client.send_photo(
                        chat_id=user_id,
                        photo=file_id,
                        caption=caption
                    )
            except Exception as photo_error:
                print(f"Error sending photo: {photo_error}")
                # Fallback to text message if photo fails
                if caption:
                    await client.send_message(
                        chat_id=user_id,
                        text=f"📢 تبلیغ\n\n{caption}"
                    )
        elif content_type == 'video' and file_id:
            await client.send_video(
                chat_id=user_id,
                video=file_id,
                caption=caption
            )
        elif content_type == 'gif' and file_id:
            await client.send_animation(
                chat_id=user_id,
                animation=file_id,
                caption=caption
            )
        elif content_type == 'sticker' and file_id:
            await client.send_sticker(
                chat_id=user_id,
                sticker=file_id
            )
        elif content_type == 'audio' and file_id:
            await client.send_audio(
                chat_id=user_id,
                audio=file_id,
                caption=caption
            )
        
    except Exception as e:
        print(f"Advertisement send error: {e}")
        pass

PATH = constant.PATH
txt = constant.TEXT
instaregex = r"^((?:https?:)?\/\/)?((?:www|m)\.)?((?:instagram\.com))(\/(?:p\/|reel\/|tv\/|stories\/))([\w\-]+)(\S+)?$"

# Instagram API functions
async def get_instagram_data_from_api(url):
    """Get Instagram data using RapidAPI with SSL error handling and retry mechanism"""
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            instagram_logger.debug(f"شروع درخواست API برای URL: {url} (تلاش {attempt + 1}/{max_retries})")
            
            payload = {"url": url}
            
            headers = {
                'x-rapidapi-key': "d51a95d960mshb5f65a8e122bb7fp11b675jsn63ff66cbc6cf",
                'x-rapidapi-host': "social-download-all-in-one.p.rapidapi.com",
                'Content-Type': "application/json"
            }
            
            # Make request with SSL verification disabled and timeout
            response = requests.post(
                "https://social-download-all-in-one.p.rapidapi.com/v1/social/autolink",
                json=payload,
                headers=headers,
                verify=False,  # Disable SSL verification to avoid SSL errors
                timeout=30,
                allow_redirects=True
            )
            
            instagram_logger.debug(f"وضعیت پاسخ API: {response.status_code}")
            print(f"Instagram API Response Status: {response.status_code}")
            
            if response.status_code != 200:
                instagram_logger.error(f"خطای API: وضعیت {response.status_code}, پاسخ: {response.text[:500]}")
                print(f"API Error: Status {response.status_code}, Response: {response.text[:500]}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return None
            
            response_data = response.json()
            print(f"Instagram API Response Data: {str(response_data)[:500]}...")  # Log first 500 chars
            
            # Validate response structure
            if not response_data or 'medias' not in response_data:
                instagram_logger.error(f"ساختار پاسخ API نامعتبر: {response_data}")
                print(f"Invalid API response structure: {response_data}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return None
            
            instagram_logger.debug(f"دریافت موفق اطلاعات از API - تعداد رسانه: {len(response_data.get('medias', []))}")
            return response_data
            
        except requests.exceptions.SSLError as e:
            instagram_logger.error(f"خطای SSL در تلاش {attempt + 1}: {e}")
            print(f"SSL Error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
        except requests.exceptions.RequestException as e:
            instagram_logger.error(f"خطای درخواست در تلاش {attempt + 1}: {e}")
            print(f"Request Error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
        except Exception as e:
            instagram_logger.error(f"خطای عمومی API اینستاگرام در تلاش {attempt + 1}: {e}")
            print(f"General Instagram API Error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
    
    instagram_logger.error(f"همه تلاش‌ها ناموفق بود برای URL: {url}")
    print(f"All retry attempts failed for URL: {url}")
    return None

def _fetch_og_media_instagram(url: str):
    """Fallback: fetch media via OpenGraph tags for Instagram pages (video/image)."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=12)
        html = resp.text
        # Try og:video first
        vid = re.search(r'<meta[^>]*property=["\"]og:video["\"][^>]*content=["\"]([^"\"]+)["\"]', html, flags=re.IGNORECASE)
        title_m = re.search(r'<meta[^>]*property=["\"]og:title["\"][^>]*content=["\"]([^"\"]+)["\"]', html, flags=re.IGNORECASE)
        if vid:
            vurl = vid.group(1)
            ext = 'mp4'
            return { 'url': vurl, 'extension': ext, 'type': 'video', 'title': title_m.group(1) if title_m else None }
        img = re.search(r'<meta[^>]*property=["\"]og:image["\"][^>]*content=["\"]([^"\"]+)["\"]', html, flags=re.IGNORECASE)
        if img:
            iurl = img.group(1)
            ext = 'jpg'
            if '.png' in iurl:
                ext = 'png'
            elif '.webp' in iurl:
                ext = 'webp'
            return { 'url': iurl, 'extension': ext, 'type': 'image', 'title': title_m.group(1) if title_m else None }
        return None
    except Exception as e:
        instagram_logger.warning(f"OG fetch fallback failed for Instagram {url}: {e}")
        return None

async def download_file_with_progress(url, file_path, status_msg, title, type_label):
    """Download file with progress updates"""
    try:
        instagram_logger.debug(f"شروع دانلود فایل از URL: {url}")
        import asyncio
        
        # Get file size first
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            instagram_logger.debug(f"حجم کل فایل: {total_size} bytes")
            
        # Download with progress
        downloaded = 0
        chunk_size = 8192
        last_update = 0
        
        with urllib.request.urlopen(url) as response:
            with open(file_path, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Update progress every 1MB or 10%
                    if downloaded - last_update > 1024*1024 or (total_size > 0 and downloaded - last_update > total_size * 0.1):
                        last_update = downloaded
                        if total_size > 0:
                            percent = int(downloaded * 100 / total_size)
                            size_mb = f"{(int(total_size)/1024/1024):.2f}"
                        else:
                            percent = 0
                            size_mb = "نامشخص"
                        
                        instagram_logger.debug(f"پیشرفت دانلود: {percent}% - {downloaded}/{total_size} bytes")
                        text = _format_status_text(title, type_label, size_mb, "در حال دانلود ...")
                        kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"🚀 پیشرفت: {percent}٪", callback_data="ignore")]])
                        
                        try:
                            await status_msg.edit_text(text, reply_markup=kb)
                        except Exception:
                            pass
        
        instagram_logger.debug(f"دانلود کامل - فایل ذخیره شد در: {file_path}")
        return file_path, total_size
        
    except Exception as e:
        instagram_logger.error(f"خطای دانلود فایل: {e}")
        print(f"Download error: {e}")
        raise e

def _format_status_text(title, type_label, size_mb, status):
    """Format status text for progress updates"""
    return f"""📥 **دانلود از اینستاگرام**

📝 **عنوان:** {title[:50]}{'...' if len(title) > 50 else ''}
📊 **نوع:** {type_label}
📏 **حجم:** {size_mb} مگابایت
⏳ **وضعیت:** {status}"""

@Client.on_message(filters.regex(instaregex) & filters.private & join)
async def download_instagram(_: Client, message: Message):
    user_id = message.from_user.id
    url = message.text.strip()
    
    instagram_logger.info(f"درخواست دانلود اینستاگرام از کاربر {user_id}: {url}")
    
    # Check if user is in database
    db = DB()
    if not db.check_user_register(user_id):
        instagram_logger.warning(f"کاربر {user_id} در دیتابیس ثبت نشده")
        await message.reply_text(txt['first_message'].format(message.from_user.first_name), reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 شروع مجدد", callback_data="start")]
        ]))
        return
    
    # Check if user is blocked (banned/daily limit)
    from datetime import datetime as _dt
    blocked_until_str = db.get_blocked_until(user_id)
    if blocked_until_str:
        try:
            blocked_until = _dt.fromisoformat(blocked_until_str)
            if blocked_until > _dt.now():
                instagram_logger.warning(f"کاربر {user_id} مسدود است تا {blocked_until}")
                await message.reply_text("⛔ شما به دلیل تجاوز از حد مجاز روزانه موقتاً مسدود شده‌اید.\n\n⏰ لطفاً بعداً تلاش کنید.")
                return
        except Exception:
            pass
    
    # Send initial status message
    instagram_logger.debug(f"ارسال پیام وضعیت اولیه برای کاربر {user_id}")
    status_msg = await message.reply_text(
        "🔍 **در حال بررسی لینک اینستاگرام...**\n\n⏳ لطفاً صبر کنید...",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏳ در حال پردازش...", callback_data="ignore")]])
    )
    
    try:
        # Get Instagram data from API
        instagram_logger.debug(f"شروع دریافت اطلاعات از API برای URL: {url}")
        api_data = await get_instagram_data_from_api(url)
        title = None
        medias = None
        post_type = 'single'

        if api_data and api_data.get('medias'):
            # Extract media information from API
            title = api_data.get('title', 'Instagram Media')
            medias = api_data.get('medias', [])
            post_type = api_data.get('type', 'single')
            # Sanitize medias: dedupe and correctly detect single vs multiple
            try:
                from urllib.parse import urlparse
                path_lower = urlparse(url).path.lower()
                is_reel = ('/reel/' in path_lower)

                # Deduplicate by URL first
                seen = set()
                medias = [m for m in medias if m.get('url') and (m.get('url') not in seen and not seen.add(m.get('url')))]

                # Smart detection for single content posts (reels, posts with video+audio)
                # Check if this is a single content post with video+audio combination
                videos = [m for m in medias if (m.get('type') == 'video') and m.get('url')]
                audios = [m for m in medias if (m.get('type') == 'audio') and m.get('url')]
                images = [m for m in medias if (m.get('type') in ('image','photo')) and m.get('url')]
                
                # If we have exactly 1 video + 1 audio (common for reels/single posts), treat as single
                # Or if it's a reel with video+audio, treat as single
                is_single_with_audio = (len(videos) == 1 and len(audios) == 1 and len(images) == 0)
                is_reel_with_media = is_reel and len(videos) >= 1
                
                if is_single_with_audio or is_reel_with_media:
                    # For single content posts, only keep the video (ignore separate audio files)
                    if videos:
                        medias = [videos[0]]
                        post_type = 'single'
                        instagram_logger.debug(f"تشخیص پست تک‌محتوا: ویدیو انتخاب شد، فایل‌های صوتی نادیده گرفته شدند")
                    else:
                        # Fallback to first available media
                        medias = [medias[0]] if medias else []
                        post_type = 'single'
                elif len(medias) > 1 and not is_reel:
                    # True multiple media (carousel/gallery)
                    post_type = 'multiple'
                else:
                    # Single media (image or video)
                    if videos:
                        medias = [videos[0]]
                    elif images:
                        medias = [images[0]]
                    else:
                        medias = [medias[0]] if medias else []
                    post_type = 'single'
            except Exception:
                # If sanitization fails, fall back to original medias
                pass
        else:
            # API failed or returned no medias: try OG fallback
            instagram_logger.warning(f"API خالی یا ناموفق؛ تلاش fallback OG برای URL: {url}")
            og = _fetch_og_media_instagram(url)
            if og:
                title = og.get('title') or 'Instagram Media'
                medias = [ { 'url': og.get('url'), 'type': og.get('type') } ]
            else:
                instagram_logger.error(f"OG fallback ناموفق برای URL: {url}")
                await status_msg.edit_text(
                    "❌ **خطا در دریافت اطلاعات**\n\n🔍 لینک اینستاگرام معتبر نیست یا در دسترس نمی‌باشد.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 تلاش مجدد", callback_data="start")]])
                )
                return
        
        instagram_logger.debug(f"اطلاعات استخراج شد: عنوان={title}, تعداد رسانه={len(medias)}, نوع={post_type}")
        
        if not medias:
            instagram_logger.warning(f"هیچ رسانه‌ای یافت نشد برای URL: {url}")
            await status_msg.edit_text(
                "❌ **فایل قابل دانلود یافت نشد**\n\n🔍 این پست ممکن است حاوی محتوای قابل دانلود نباشد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 تلاش مجدد", callback_data="start")]])
            )
            return
        
        # Note: create_safe_caption function is now defined at the bottom of the file
        
        # Check advertisement settings for position
        try:
            with open(PATH + '/database.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            ad_settings = data.get('advertisement', {})
            ad_enabled = ad_settings.get('enabled', False)
            ad_position = ad_settings.get('position', 'after')
        except:
            ad_enabled = False
            ad_position = 'after'
        
        # Send advertisement before content if position is 'before' and enabled
        if ad_enabled and ad_position == 'before':
            await send_advertisement(_, user_id)
        
        # Handle multiple media (carousel/gallery)
        if post_type == 'multiple' and len(medias) > 1:
            instagram_logger.debug(f"پردازش چندین رسانه (کاروسل) - تعداد: {len(medias)}")
            await handle_multiple_media(_, message, status_msg, medias, title, user_id)
        else:
            # Handle single media
            instagram_logger.debug("پردازش رسانه تکی")
            await handle_single_media(_, message, status_msg, medias[0], title, user_id)
        
        # Send advertisement after content if position is 'after' and enabled
        if ad_enabled and ad_position == 'after':
            instagram_logger.debug("ارسال تبلیغ بعد از محتوا")
            await send_advertisement(_, user_id)
        
        # Update user download count
        db.increment_request(user_id, datetime.now().isoformat())
        instagram_logger.debug(f"شمارنده دانلود کاربر {user_id} افزایش یافت")
        
        # Delete status message
        try:
            await status_msg.delete()
            instagram_logger.debug("پیام وضعیت حذف شد")
        except Exception:
            instagram_logger.warning("خطا در حذف پیام وضعیت")
            pass
    
    except Exception as e:
        error_msg = str(e)
        instagram_logger.error(f"خطا در دانلود اینستاگرام: {error_msg}")
        print(f"Instagram download error: {error_msg}")
        
        # Handle specific errors
        if "API Error" in error_msg:
            error_text = "❌ **خطا در ارتباط با سرور**\n\n🔍 لطفاً بعداً تلاش کنید."
        elif "Download error" in error_msg:
            error_text = "❌ **خطا در دانلود فایل**\n\n🔍 ممکن است فایل در دسترس نباشد."
        else:
            error_text = "❌ **خطای غیرمنتظره**\n\n🔍 لطفاً لینک را بررسی کرده و مجدداً تلاش کنید."
        
        try:
            await status_msg.edit_text(
                error_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 تلاش مجدد", callback_data="start")]])
            )
        except Exception:
            pass
        
        # Clean up any partial files
        try:
            if 'downloaded_file_path' in locals() and os.path.exists(downloaded_file_path):
                os.remove(downloaded_file_path)
            elif 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass


async def handle_single_media(client, message, status_msg, media, title, user_id):
    """Handle single media download and upload"""
    try:
        instagram_logger.debug(f"شروع پردازش رسانه تکی برای کاربر {user_id}")
        download_url = media.get('url')
        if not download_url:
            instagram_logger.error("URL دانلود یافت نشد")
            raise Exception("Download URL not found")
        
        # Determine file type and extension
        media_type = media.get('type', 'unknown')
        instagram_logger.debug(f"نوع رسانه: {media_type}")
        if media_type == 'video':
            type_label = "🎥 ویدیو"
            ext = 'mp4'
        elif media_type == 'image' or media_type == 'photo':
            type_label = "🖼️ عکس"
            ext = 'jpg'
        else:
            type_label = "📄 فایل"
            ext = 'mp4'  # default
        
        # Create filename
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()[:50]
        filename = f"{safe_title}_{int(time.time())}.{ext}"
        file_path = os.path.join(PATH, filename)
        instagram_logger.debug(f"مسیر فایل: {file_path}")
        
        # Update status
        await status_msg.edit_text(
            _format_status_text(title, type_label, "محاسبه...", "آماده‌سازی دانلود..."),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏳ در حال آماده‌سازی...", callback_data="ignore")]])
        )
        
        # Download file
        instagram_logger.debug(f"شروع دانلود از URL: {download_url}")
        downloaded_file_path, total_bytes = await download_file_with_progress(download_url, file_path, status_msg, title, type_label)

        if not os.path.exists(downloaded_file_path):
            instagram_logger.error(f"فایل دانلود شده یافت نشد: {downloaded_file_path}")
            raise Exception("Downloaded file not found")

        total_mb_text = f"{(total_bytes/1024/1024):.2f}" if total_bytes else "نامشخص"
        instagram_logger.debug(f"دانلود کامل - حجم: {total_mb_text} MB")
        
        # Create safe caption
        safe_caption = create_safe_caption(title, 1)
        
        # If video, enforce resolution & generate thumbnail (optimized for speed)
        thumb_path = None
        width_arg = None
        height_arg = None
        final_path = downloaded_file_path
        
        # Update status for processing
        await status_msg.edit_text(
            _format_status_text(title, type_label, total_mb_text, "بررسی فایل..."),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔍 در حال بررسی...", callback_data="ignore")]])
        )
        
        try:
            if media_type == 'video':
                # Fast path: skip re-encode and thumbnail for files under 10MB to reduce latency
                if total_bytes and total_bytes <= 10 * 1024 * 1024:
                    instagram_logger.debug("ویدیو کم‌حجم شناسایی شد؛ صرف‌نظر از re-encode و تولید thumbnail برای سرعت بیشتر")
                    thumb_path = None
                    final_path = downloaded_file_path
                    
                    # Update status for direct upload
                    await status_msg.edit_text(
                        _format_status_text(title, type_label, total_mb_text, "آماده برای ارسال سریع..."),
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚡ ارسال سریع...", callback_data="ignore")]])
                    )
                else:
                    # Update status for processing
                    await status_msg.edit_text(
                        _format_status_text(title, type_label, total_mb_text, "پردازش ویدیو..."),
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ در حال پردازش...", callback_data="ignore")]])
                    )
                    
                    instagram_logger.debug("شروع پردازش ویدیو و تولید thumbnail")
                    # Detect ffmpeg path (similar to youtube module)
                    ffmpeg_path = os.environ.get('FFMPEG_PATH')
                    try:
                        if (not ffmpeg_path) and sys.platform.startswith('linux') and os.path.exists('/usr/bin/ffmpeg'):
                            ffmpeg_path = '/usr/bin/ffmpeg'
                    except Exception:
                        pass
                    if not ffmpeg_path:
                        from config import FFMPEG_PATH
                        candidates = [
                            FFMPEG_PATH,
                            "ffmpeg",
                            "/usr/local/bin/ffmpeg"
                        ]
                        for p in candidates:
                            if shutil.which(p) or os.path.exists(p):
                                ffmpeg_path = p
                                break
                    
                    instagram_logger.debug(f"مسیر ffmpeg: {ffmpeg_path}")
                    
                    # Prefer 1280x720 as primary
                    target_w, target_h = 1280, 720
                    # Re-encode
                    base_noext, _ = os.path.splitext(downloaded_file_path)
                    enforced_path = f"{base_noext}_{target_w}x{target_h}.mp4"
                    try:
                        instagram_logger.debug(f"شروع re-encode ویدیو به {target_w}x{target_h}")
                        vf = f"scale=w={target_w}:h={target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1"
                        cmd = [ffmpeg_path or 'ffmpeg', '-y', '-i', downloaded_file_path, '-vf', vf,
                               '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22',
                               '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart',
                               enforced_path]
                        await asyncio.to_thread(lambda: subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
                        if os.path.exists(enforced_path):
                            try:
                                os.remove(downloaded_file_path)
                            except Exception:
                                pass
                            final_path = enforced_path
                            width_arg, height_arg = target_w, target_h
                            instagram_logger.debug(f"re-encode موفق - فایل جدید: {enforced_path}")
                    except Exception as ee:
                        instagram_logger.error(f"خطای FFmpeg re-encode: {ee}")
                        print(f"FFmpeg re-encode (IG) failed: {ee}")
                        final_path = downloaded_file_path
                    
                    # Thumbnail (<=320px, <=200KB)
                    thumb_path = f"{base_noext}_thumb.jpg"
                    try:
                        instagram_logger.debug("شروع تولید thumbnail")
                        def make_thumb(q):
                            vf_thumb = 'scale=320:-2:force_original_aspect_ratio=decrease'
                            cmd_t = [ffmpeg_path or 'ffmpeg', '-y', '-ss', '2', '-i', final_path, '-frames:v', '1', '-vf', vf_thumb, '-q:v', str(q), thumb_path]
                            subprocess.run(cmd_t, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        for q in [5,6,7,8,9,10]:
                            try:
                                await asyncio.to_thread(make_thumb, q)
                                if os.path.exists(thumb_path) and os.path.getsize(thumb_path) <= 200*1024:
                                    instagram_logger.debug(f"thumbnail تولید شد با کیفیت {q}")
                                    break
                            except Exception:
                                continue
                    except Exception as te:
                        instagram_logger.error(f"خطای تولید thumbnail: {te}")
                        print(f"IG thumbnail error: {te}")
                        thumb_path = None
            elif media_type == 'image' or media_type == 'photo':
                instagram_logger.debug("شروع پردازش تصویر")
                
                # Check if image is already in a good format (JPG/JPEG) and reasonable size
                base_noext, ext0 = os.path.splitext(downloaded_file_path)
                ext_lower = ext0.lower()
                file_size = os.path.getsize(downloaded_file_path) if os.path.exists(downloaded_file_path) else 0
                
                # Fast path: skip normalization for JPG/JPEG files under 10MB
                if ext_lower in ['.jpg', '.jpeg'] and file_size <= 10 * 1024 * 1024:
                    instagram_logger.debug("تصویر JPG کم‌حجم شناسایی شد؛ صرف‌نظر از normalize برای سرعت بیشتر")
                    final_path = downloaded_file_path
                    
                    # Update status for direct upload
                    await status_msg.edit_text(
                        _format_status_text(title, type_label, total_mb_text, "آماده برای ارسال سریع..."),
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚡ ارسال سریع...", callback_data="ignore")]])
                    )
                else:
                    # Update status for processing
                    await status_msg.edit_text(
                        _format_status_text(title, type_label, total_mb_text, "پردازش تصویر..."),
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ در حال پردازش...", callback_data="ignore")]])
                    )
                    
                    # Normalize images to JPEG to avoid IMAGE_PROCESS_FAILED (e.g., WEBP/PNG)
                    ffmpeg_path = os.environ.get('FFMPEG_PATH')
                    try:
                        if (not ffmpeg_path) and sys.platform.startswith('linux') and os.path.exists('/usr/bin/ffmpeg'):
                            ffmpeg_path = '/usr/bin/ffmpeg'
                    except Exception:
                        pass
                    if not ffmpeg_path:
                        from config import FFMPEG_PATH
                        candidates = [
                            FFMPEG_PATH,
                            "ffmpeg",
                            "/usr/local/bin/ffmpeg"
                        ]
                        for p in candidates:
                            if shutil.which(p) or os.path.exists(p):
                                ffmpeg_path = p
                                break
                    
                    instagram_logger.debug(f"مسیر ffmpeg برای تصویر: {ffmpeg_path}")
                    
                    normalized_path = f"{base_noext}_norm.jpg"
                    try:
                        instagram_logger.debug("شروع normalize کردن تصویر")
                        cmd_img = [ffmpeg_path or 'ffmpeg', '-y', '-i', downloaded_file_path,
                                   '-vf', 'scale=1280:-2:force_original_aspect_ratio=decrease,setsar=1',
                                   '-q:v', '2', normalized_path]
                        await asyncio.to_thread(lambda: subprocess.run(cmd_img, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
                        if os.path.exists(normalized_path) and os.path.getsize(normalized_path) > 0:
                            try:
                                os.remove(downloaded_file_path)
                            except Exception:
                                pass
                            final_path = normalized_path
                            instagram_logger.debug(f"normalize تصویر موفق - فایل جدید: {normalized_path}")
                    except Exception as norm_e:
                        instagram_logger.error(f"خطای normalize تصویر: {norm_e}")
                        print(f"Single image normalization failed: {norm_e}")
                        final_path = downloaded_file_path
        except Exception as ie:
            instagram_logger.error(f"خطای pipeline پردازش: {ie}")
            print(f"IG enforce pipeline error: {ie}")
            thumb_path = None
            final_path = downloaded_file_path
        
        # Upload file
        instagram_logger.debug(f"شروع ارسال فایل - نوع: {media_type}")
        if media_type == 'video':
            # Verify video file exists and has content
            if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                instagram_logger.error(f"فایل ویدیو خالی یا موجود نیست: {final_path}")
                raise Exception("Video file is empty or doesn't exist")
            
            # Send video without width/height to avoid IMAGE_PROCESS_FAILED
            try:
                instagram_logger.debug("شروع ارسال ویدیو")
                sent_msg = await message.reply_video(
                    video=final_path,
                    caption=safe_caption,
                    thumb=thumb_path,
                    progress=lambda current, total: None  # Simple progress without updates
                )
            except Exception as video_error:
                instagram_logger.error(f"خطای ارسال ویدیو: {video_error}")
                print(f"Video upload failed: {video_error}")
                # Fallback: send as document if video upload fails
                instagram_logger.debug("تلاش برای ارسال به عنوان document")
                sent_msg = await message.reply_document(
                    document=final_path,
                    caption=safe_caption,
                    thumb=thumb_path
                )
        elif media_type == 'image' or media_type == 'photo':
            # Verify image file exists and has content
            if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                instagram_logger.error(f"فایل تصویر خالی یا موجود نیست: {final_path}")
                raise Exception("Image file is empty or doesn't exist")
            try:
                instagram_logger.debug("شروع ارسال تصویر")
                sent_msg = await message.reply_photo(
                    photo=final_path,
                    caption=safe_caption
                )
            except Exception as photo_err:
                instagram_logger.error(f"خطای ارسال تصویر: {photo_err}")
                print(f"Photo upload failed: {photo_err}")
                # Fallback: send as document
                instagram_logger.debug("تلاش برای ارسال تصویر به عنوان document")
                sent_msg = await message.reply_document(
                    document=final_path,
                    caption=safe_caption
                )
        else:
            # Unknown type: send as document
            if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                instagram_logger.error(f"فایل نامشخص خالی یا موجود نیست: {final_path}")
                raise Exception("File is empty or doesn't exist")
            instagram_logger.debug("ارسال به عنوان document")
            sent_msg = await message.reply_document(
                document=final_path,
                caption=safe_caption
            )
        
        instagram_logger.debug("ارسال فایل موفق - شروع پاکسازی")
        # No delay needed - proceed directly to cleanup for faster user experience
        
        # Clean up file
        try:
            if os.path.exists(final_path):
                os.remove(final_path)
                instagram_logger.debug(f"فایل اصلی پاک شد: {final_path}")
            if final_path != downloaded_file_path and os.path.exists(downloaded_file_path):
                os.remove(downloaded_file_path)
                instagram_logger.debug(f"فایل دانلود شده پاک شد: {downloaded_file_path}")
            if thumb_path and os.path.exists(thumb_path):
                os.remove(thumb_path)
                instagram_logger.debug(f"thumbnail پاک شد: {thumb_path}")
        except Exception as cleanup_error:
            instagram_logger.error(f"خطای پاکسازی فایل‌ها: {cleanup_error}")
            pass
            
    except Exception as e:
        instagram_logger.error(f"خطای پردازش رسانه تکی: {e}")
        print(f"Single media handling error: {e}")
        raise e


async def handle_multiple_media(client, message, status_msg, medias, title, user_id):
    """Handle multiple media download and upload as media group"""
    try:
        instagram_logger.debug(f"شروع پردازش چندرسانه‌ای - تعداد: {len(medias)} برای کاربر {user_id}")
        # Limit to maximum 10 media items (Telegram limit)
        medias = medias[:10]
        media_group = []
        downloaded_files = []
        
        # Update status
        await status_msg.edit_text(
            f"📥 **دانلود چندرسانه‌ای اینستاگرام**\n\n📝 **عنوان:** {title[:100]}...\n📊 **تعداد فایل:** {len(medias)}\n⏳ **وضعیت:** آماده‌سازی دانلود...",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏳ در حال پردازش...", callback_data="ignore")]])
        )
        
        # Download all media files
        for i, media in enumerate(medias):
            try:
                instagram_logger.debug(f"پردازش رسانه {i+1} از {len(medias)}")
                download_url = media.get('url')
                if not download_url:
                    instagram_logger.warning(f"URL دانلود برای رسانه {i+1} یافت نشد")
                    continue
                
                # Determine file type and extension
                media_type = media.get('type', 'image')
                ext = 'mp4' if media_type == 'video' else 'jpg'
                instagram_logger.debug(f"نوع رسانه {i+1}: {media_type}, پسوند: {ext}")
                
                # Create filename
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()[:30]
                filename = f"{safe_title}_{i+1}_{int(time.time())}.{ext}"
                file_path = os.path.join(PATH, filename)
                instagram_logger.debug(f"مسیر فایل رسانه {i+1}: {file_path}")
                
                # Update progress
                await status_msg.edit_text(
                    f"📥 **دانلود چندرسانه‌ای اینستاگرام**\n\n📝 **عنوان:** {title[:100]}...\n📊 **پیشرفت:** {i+1}/{len(medias)}\n⏳ **وضعیت:** دانلود فایل {i+1}...",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"⏳ دانلود {i+1}/{len(medias)}...", callback_data="ignore")]])
                )
                
                # Download file with proper error handling
                try:
                    instagram_logger.debug(f"شروع دانلود رسانه {i+1} از URL: {download_url}")
                    download_result = await download_file_with_progress(download_url, file_path, status_msg, f"⬇️ دانلود فایل {i+1}/{len(medias)}", "Instagram")
                    
                    # Extract file_path from tuple (file_path, total_size)
                    if isinstance(download_result, tuple):
                        file_path, total_size = download_result
                    else:
                        file_path = download_result
                        
                    if not file_path or not os.path.exists(file_path):
                        instagram_logger.error(f"دانلود رسانه {i+1} ناموفق: فایل یافت نشد")
                        print(f"Download failed for media {i+1}: file not found")
                        continue
                        
                    # Validate file existence and size
                    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                        instagram_logger.error(f"فایل دانلود شده رسانه {i+1} نامعتبر: {file_path}")
                        raise Exception(f"Downloaded file invalid for item {i+1}: {file_path}")
                
                    # Skip unsupported media types (e.g., audio-only streams)
                    if media_type not in ('video', 'image', 'photo'):
                        instagram_logger.warning(f"نوع رسانه پشتیبانی نشده '{media_type}' برای آیتم {i+1}")
                        print(f"Skipping unsupported media type '{media_type}' for item {i+1}")
                        try:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                        except Exception:
                            pass
                        continue
                
                    # For videos in media group, enforce Telegram-friendly encoding
                    if media_type == 'video':
                        # Fast path: skip re-encoding for small MP4 files under 10MB
                        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                        base_noext, ext0 = os.path.splitext(file_path)
                        ext_lower = ext0.lower()
                        
                        if ext_lower == '.mp4' and file_size <= 10 * 1024 * 1024:
                            instagram_logger.debug(f"ویدیو MP4 کم‌حجم شناسایی شد برای رسانه {i+1}؛ صرف‌نظر از re-encode")
                            # Keep the original file without processing
                        else:
                            try:
                                instagram_logger.debug(f"شروع پردازش ویدیو برای رسانه {i+1}")
                                ffmpeg_path = os.environ.get('FFMPEG_PATH')
                                try:
                                    if (not ffmpeg_path) and sys.platform.startswith('linux') and os.path.exists('/usr/bin/ffmpeg'):
                                        ffmpeg_path = '/usr/bin/ffmpeg'
                                except Exception:
                                    pass
                                if not ffmpeg_path:
                                    from config import FFMPEG_PATH
                                    candidates = [
                                        FFMPEG_PATH,
                                        "ffmpeg",
                                        "/usr/local/bin/ffmpeg"
                                    ]
                                    for p in candidates:
                                        if shutil.which(p) or os.path.exists(p):
                                            ffmpeg_path = p
                                            break
                                instagram_logger.debug(f"مسیر ffmpeg برای رسانه {i+1}: {ffmpeg_path}")
                                base_noext, _ = os.path.splitext(file_path)
                                enforced_path = f"{base_noext}_720p.mp4"
                                vf = "scale=w=1280:h=720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1"
                                cmd = [ffmpeg_path or 'ffmpeg', '-y', '-i', file_path, '-vf', vf,
                                       '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22',
                                       '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart',
                                       enforced_path]
                                instagram_logger.debug(f"شروع re-encode ویدیو رسانه {i+1} به 720p")
                                await asyncio.to_thread(lambda: subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
                                if os.path.exists(enforced_path) and os.path.getsize(enforced_path) > 0:
                                    instagram_logger.debug(f"re-encode ویدیو رسانه {i+1} موفق - فایل جدید: {enforced_path}")
                                    try:
                                        os.remove(file_path)
                                    except Exception:
                                        pass
                                    file_path = enforced_path
                            except Exception as reenc_err:
                                instagram_logger.error(f"خطای re-encode ویدیو رسانه {i+1}: {reenc_err}")
                                print(f"Media group re-encode error for item {i+1}: {reenc_err}")
                
                    # For photos, normalize format to JPEG to avoid IMAGE_PROCESS_FAILED (e.g., WEBP)
                    if media_type == 'image' or media_type == 'photo':
                        try:
                            base_noext, ext2 = os.path.splitext(file_path)
                            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                            
                            # Fast path: skip processing for JPG/JPEG files under 10MB
                            if ext2.lower() in ('.jpg', '.jpeg') and file_size <= 10 * 1024 * 1024:
                                instagram_logger.debug(f"تصویر JPG کم‌حجم شناسایی شد برای رسانه {i+1}؛ صرف‌نظر از پردازش")
                                # Keep the original file without processing
                            elif ext2.lower() not in ('.jpg', '.jpeg'):
                                instagram_logger.debug(f"شروع پردازش تصویر رسانه {i+1}")
                                instagram_logger.debug(f"تبدیل فرمت تصویر رسانه {i+1} از {ext2} به JPEG")
                                ffmpeg_path = os.environ.get('FFMPEG_PATH')
                                try:
                                    if (not ffmpeg_path) and sys.platform.startswith('linux') and os.path.exists('/usr/bin/ffmpeg'):
                                        ffmpeg_path = '/usr/bin/ffmpeg'
                                except Exception:
                                    pass
                                if not ffmpeg_path:
                                    from config import FFMPEG_PATH
                                    candidates = [
                                        FFMPEG_PATH,
                                        "ffmpeg",
                                        "/usr/local/bin/ffmpeg"
                                    ]
                                    for p in candidates:
                                        if shutil.which(p) or os.path.exists(p):
                                            ffmpeg_path = p
                                            break
                                normalized_path = f"{base_noext}_norm.jpg"
                                cmd = [ffmpeg_path or 'ffmpeg', '-y', '-i', file_path,
                                       '-vf', 'scale=1280:-2:force_original_aspect_ratio=decrease,setsar=1',
                                       '-q:v', '2',
                                       normalized_path]
                                instagram_logger.debug(f"شروع تبدیل فرمت تصویر رسانه {i+1}")
                                await asyncio.to_thread(lambda: subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
                                if os.path.exists(normalized_path) and os.path.getsize(normalized_path) > 0:
                                    instagram_logger.debug(f"تبدیل فرمت تصویر رسانه {i+1} موفق - فایل جدید: {normalized_path}")
                                    try:
                                        os.remove(file_path)
                                    except Exception:
                                        pass
                                    file_path = normalized_path
                        except Exception as norm_err:
                            instagram_logger.error(f"خطای تبدیل فرمت تصویر رسانه {i+1}: {norm_err}")
                            print(f"Photo normalization error for item {i+1}: {norm_err}")
                
                    # Track final file path for cleanup
                    downloaded_files.append(file_path)
                    instagram_logger.debug(f"فایل رسانه {i+1} آماده برای ارسال: {file_path}")
                
                    # Add to media group with error handling
                    try:
                        if media_type == 'video':
                            if i == 0:  # First item gets caption
                                instagram_logger.debug(f"اضافه کردن ویدیو رسانه {i+1} با کپشن به گروه رسانه")
                                media_group.append(InputMediaVideo(media=file_path, caption=create_safe_caption(title, len(medias))))
                            else:
                                instagram_logger.debug(f"اضافه کردن ویدیو رسانه {i+1} بدون کپشن به گروه رسانه")
                                media_group.append(InputMediaVideo(media=file_path))
                        else:
                            if i == 0:  # First item gets caption
                                instagram_logger.debug(f"اضافه کردن تصویر رسانه {i+1} با کپشن به گروه رسانه")
                                media_group.append(InputMediaPhoto(media=file_path, caption=create_safe_caption(title, len(medias))))
                            else:
                                instagram_logger.debug(f"اضافه کردن تصویر رسانه {i+1} بدون کپشن به گروه رسانه")
                                media_group.append(InputMediaPhoto(media=file_path))
                    except Exception as media_error:
                        instagram_logger.error(f"خطای ایجاد شیء رسانه برای فایل {i+1}: {media_error}")
                        print(f"Error creating media object for file {i+1}: {media_error}")
                        continue
                except Exception as dl_err:
                    instagram_logger.error(f"خطای دانلود یا آماده‌سازی فایل برای آیتم {i+1}: {dl_err}")
                    print(f"Error downloading or preparing file for item {i+1}: {dl_err}")
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    except Exception:
                        pass
                    continue
            except Exception as item_err:
                instagram_logger.error(f"خطای پردازش آیتم {i+1}: {item_err}")
                print(f"Error processing item {i+1}: {item_err}")
                continue
        
        if not media_group:
            instagram_logger.warning("هیچ رسانه‌ای برای ارسال آماده نشد")
            await status_msg.edit_text(
                "❌ **خطا در دانلود فایل‌ها**\n\n🔍 هیچ فایل قابل دانلودی یافت نشد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 تلاش مجدد", callback_data="start")]])
            )
            return
        
        # Update status for upload
        instagram_logger.debug(f"آماده‌سازی برای ارسال {len(media_group)} رسانه")
        await status_msg.edit_text(
            f"📥 **دانلود چندرسانه‌ای اینستاگرام**\n\n📝 **عنوان:** {title[:100]}...\n📊 **فایل‌های آماده:** {len(media_group)}\n📤 **وضعیت:** آماده‌سازی برای ارسال...",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 در حال ارسال...", callback_data="ignore")]])
        )
        
        # Send media group
        try:
            instagram_logger.debug("شروع ارسال گروه رسانه")
            await message.reply_media_group(media=media_group)
            instagram_logger.debug("ارسال گروه رسانه موفق")
        except Exception as group_error:
            instagram_logger.error(f"خطای ارسال گروه رسانه: {group_error}")
            print(f"Media group upload failed: {group_error}")
            # Fallback: send items one-by-one
            instagram_logger.debug("شروع ارسال تک‌تک رسانه‌ها به عنوان fallback")
            for idx, m in enumerate(media_group):
                try:
                    if isinstance(m, InputMediaVideo):
                        try:
                            instagram_logger.debug(f"ارسال ویدیو {idx+1} به صورت جداگانه")
                            await message.reply_video(video=m.media, caption=m.caption if idx == 0 else None)
                        except Exception as ve:
                            instagram_logger.error(f"خطای ارسال ویدیو {idx+1}: {ve}")
                            print(f"Fallback video send failed for item {idx+1}: {ve}")
                            await message.reply_document(document=m.media, caption=m.caption if idx == 0 else None)
                    elif isinstance(m, InputMediaPhoto):
                        try:
                            instagram_logger.debug(f"ارسال تصویر {idx+1} به صورت جداگانه")
                            await message.reply_photo(photo=m.media, caption=m.caption if idx == 0 else None)
                        except Exception as pe:
                            instagram_logger.error(f"خطای ارسال تصویر {idx+1}: {pe}")
                            print(f"Fallback photo send failed for item {idx+1}: {pe}")
                            await message.reply_document(document=m.media, caption=m.caption if idx == 0 else None)
                except Exception as item_err:
                    instagram_logger.error(f"خطای ارسال آیتم {idx+1}: {item_err}")
                    print(f"Error sending individual item {idx+1}: {item_err}")
        
        # Wait a moment to ensure upload is complete
        await asyncio.sleep(3)
        
        # Clean up files
        instagram_logger.debug(f"شروع پاکسازی {len(downloaded_files)} فایل")
        for file_path in downloaded_files:
            try:
                os.remove(file_path)
                instagram_logger.debug(f"فایل پاک شد: {file_path}")
            except Exception as cleanup_err:
                instagram_logger.error(f"خطای پاکسازی فایل {file_path}: {cleanup_err}")
                pass
                
    except Exception as e:
        instagram_logger.error(f"خطای کلی در پردازش چندرسانه‌ای: {e}")
        print(f"Multiple media handling error: {e}")
        # Clean up any downloaded files on error
        for file_path in downloaded_files:
            try:
                os.remove(file_path)
            except Exception:
                pass
        raise e


def create_safe_caption(title, media_count=1):
    """Create a safe caption that doesn't exceed Telegram's limits"""
    # Truncate title if too long
    safe_title = title[:400] + "..." if len(title) > 400 else title
    
    if media_count > 1:
        caption = f"📥 **دانلود شده از اینستاگرام**\n\n📝 **عنوان:** {safe_title}\n📊 **تعداد فایل:** {media_count}"
    else:
        caption = f"📥 **دانلود شده از اینستاگرام**\n\n📝 **عنوان:** {safe_title}"
    
    # Ensure caption doesn't exceed 800 characters
    if len(caption) > 800:
        # Further truncate title
        max_title_len = 400 - (len(caption) - len(safe_title))
        safe_title = title[:max_title_len] + "..."
        if media_count > 1:
            caption = f"📥 **دانلود شده از اینستاگرام**\n\n📝 **عنوان:** {safe_title}\n📊 **تعداد فایل:** {media_count}"
        else:
            caption = f"📥 **دانلود شده از اینستاگرام**\n\n📝 **عنوان:** {safe_title}"
    
    return caption