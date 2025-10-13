import asyncio
import http.client
import json
import os
import re
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from plugins.start import (
    SPOTIFY_REGEX, TIKTOK_REGEX, SOUNDCLOUD_REGEX,
    PINTEREST_REGEX, TWITTER_REGEX, THREADS_REGEX, FACEBOOK_REGEX,
    REDDIT_REGEX, IMGUR_REGEX, SNAPCHAT_REGEX, TUMBLR_REGEX,
    RUMBLE_REGEX, IFUNNY_REGEX, DEEZER_REGEX, RADIOJAVAN_REGEX,
    INSTA_REGEX,
)
from plugins.media_utils import send_advertisement, download_file_simple
from plugins.db_wrapper import DB
from plugins import constant
from datetime import datetime as _dt
import logging
import requests

# Configure Universal Downloader logger
os.makedirs('./logs', exist_ok=True)
universal_logger = logging.getLogger('universal_downloader')
universal_logger.setLevel(logging.DEBUG)

universal_handler = logging.FileHandler('./logs/universal_downloader.log', encoding='utf-8')
universal_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
universal_handler.setFormatter(universal_formatter)
universal_logger.addHandler(universal_handler)

# Use the same database system as Instagram handler
txt = constant.TEXT

# Ensure captions stay within Telegram limits
def _safe_caption(text: str, max_len: int = 950):
    try:
        t = str(text) if text else ""
        if len(t) <= max_len:
            return t
        return t[:max_len-1] + "…"
    except Exception:
        return (str(text) or "")[:max_len-1] + "…"

def get_platform_name(url):
    """Determine the platform based on URL (expanded)"""
    if INSTA_REGEX.search(url):
        return "Instagram"
    if SPOTIFY_REGEX.search(url):
        return "Spotify"
    if TIKTOK_REGEX.search(url):
        return "TikTok"
    if SOUNDCLOUD_REGEX.search(url):
        return "SoundCloud"
    if PINTEREST_REGEX.search(url):
        return "Pinterest"
    if TWITTER_REGEX.search(url):
        return "Twitter"
    if THREADS_REGEX.search(url):
        return "Threads"
    if FACEBOOK_REGEX.search(url):
        return "Facebook"
    if REDDIT_REGEX.search(url):
        return "Reddit"
    if IMGUR_REGEX.search(url):
        return "Imgur"
    if SNAPCHAT_REGEX.search(url):
        return "Snapchat"
    if TUMBLR_REGEX.search(url):
        return "Tumblr"
    if RUMBLE_REGEX.search(url):
        return "Rumble"
    if IFUNNY_REGEX.search(url):
        return "iFunny"
    if DEEZER_REGEX.search(url):
        return "Deezer"
    if RADIOJAVAN_REGEX.search(url):
        return "Radio Javan"
    return "Unknown"

def get_universal_data_from_api(url):
    """Get media data from the universal API for Spotify, TikTok, and SoundCloud"""
    try:
        conn = http.client.HTTPSConnection("social-download-all-in-one.p.rapidapi.com")
        
        payload = json.dumps({"url": url})
        
        headers = {
            'x-rapidapi-key': "d51a95d960mshb5f65a8e122bb7fp11b675jsn63ff66cbc6cf",
            'x-rapidapi-host': "social-download-all-in-one.p.rapidapi.com",
            'Content-Type': "application/json"
        }
        
        conn.request("POST", "/v1/social/autolink", payload, headers)
        res = conn.getresponse()
        data = res.read()
        
        conn.close()
        
        response_data = json.loads(data.decode("utf-8"))
        universal_logger.info(f"API Response received for URL: {url}")
        universal_logger.debug(f"API Response data: {response_data}")
        return response_data
    except Exception as e:
        universal_logger.error(f"API Error for URL {url}: {e}")
        return None

def _fetch_og_media(url: str):
    """Fallback: fetch media via OpenGraph tags for image/video-centric sites (Pinterest/Imgur/Tumblr)."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=12)
        html = resp.text
        # Try og:video first
        import re as _re
        vid = _re.search(r'<meta[^>]*property=["\"]og:video["\"][^>]*content=["\"]([^"\"]+)["\"]', html, flags=_re.IGNORECASE)
        if vid:
            vurl = vid.group(1)
            ext = 'mp4' if '.mp4' in vurl else 'mp4'
            return { 'url': vurl, 'extension': ext, 'type': 'video', 'quality': 'unknown', 'title': None, 'author': None, 'duration': 'Unknown' }
        img = _re.search(r'<meta[^>]*property=["\"]og:image["\"][^>]*content=["\"]([^"\"]+)["\"]', html, flags=_re.IGNORECASE)
        if img:
            iurl = img.group(1)
            # Prefer original image if Pinterest provides srcset
            ext = 'jpg'
            if '.png' in iurl:
                ext = 'png'
            elif '.webp' in iurl:
                ext = 'webp'
            return { 'url': iurl, 'extension': ext, 'type': 'image', 'quality': 'unknown', 'title': None, 'author': None, 'duration': 'Unknown' }
        return None
    except Exception as e:
        universal_logger.warning(f"OG fetch fallback failed for {url}: {e}")
        return None

async def handle_universal_link(client: Client, message: Message):
    """Handle downloads for Spotify, TikTok, and SoundCloud links"""
    try:
        user_id = message.from_user.id
        
        # Check if user is in database
        db = DB()
        if not db.check_user_register(user_id):
            await message.reply_text(txt['first_message'].format(message.from_user.first_name), reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 شروع مجدد", callback_data="start")]
            ]))
            return
        
        # Check if user is blocked (banned/daily limit)
        blocked_until_str = db.get_blocked_until(user_id)
        if blocked_until_str:
            try:
                blocked_until = _dt.fromisoformat(blocked_until_str)
                if blocked_until > _dt.now():
                    await message.reply_text("⛔ شما به دلیل تجاوز از حد مجاز روزانه موقتاً مسدود شده‌اید.\n\n⏰ لطفاً بعداً تلاش کنید.")
                    return
            except Exception:
                pass
        
        url = message.text.strip()
        platform = get_platform_name(url)
        
        # Send initial status message
        status_msg = await message.reply_text(f"🔄 در حال پردازش لینک {platform}...")
        
        # Advertisement will be handled later in the process
        
        # Get data from API
        await status_msg.edit_text(f"📡 در حال دریافت اطلاعات از {platform}...")
        api_data = get_universal_data_from_api(url)

        # Fallback holder
        fallback_media = None

        # If API errors, try OG fallback for Instagram before failing
        if api_data and (api_data.get("error", False) or api_data.get("data", {}).get("error", False)):
            error_message = api_data.get("message", "خطای نامشخص")
            if platform == "Instagram":
                await status_msg.edit_text("📡 API خطا داد؛ تلاش برای استخراج مستقیم Instagram...")
                og = _fetch_og_media(url)
                if og:
                    fallback_media = og
                else:
                    await status_msg.edit_text(f"❌ خطا در دریافت اطلاعات از {platform}: {error_message}")
                    return
            else:
                await status_msg.edit_text(f"❌ خطا در دریافت اطلاعات از {platform}: {error_message}")
                return

        # If API returned nothing, expand fallback to include Instagram
        if (not api_data or "medias" not in api_data or not api_data.get("medias")) and platform in ("Pinterest", "Imgur", "Tumblr", "Instagram"):
            await status_msg.edit_text(f"📡 API چیزی برنگرداند؛ تلاش برای استخراج مستقیم {platform}...")
            og = _fetch_og_media(url)
            if og:
                fallback_media = og
            else:
                await status_msg.edit_text(f"❌ خطا در دریافت اطلاعات از {platform}. لطفاً لینک را بررسی کنید.")
                return
        
        # Extract media information
        title = api_data.get("title", "Unknown Title") if api_data else "Unknown Title"
        author = api_data.get("author", "Unknown Author") if api_data else "Unknown Author"
        duration_api = api_data.get("duration", 0) if api_data else 0
        thumbnail = api_data.get("thumbnail", "") if api_data else ""
        
        # Find the best quality media
        medias = api_data.get("medias", []) if api_data else []
        if not medias:
            if fallback_media:
                medias = [fallback_media]
            else:
                await status_msg.edit_text(f"❌ هیچ فایل قابل دانلودی از {platform} یافت نشد.")
                return
        
        # Prefer video over audio, and highest quality
        selected_media = None
        for media in medias:
            if media.get("type") == "video":
                selected_media = media
                break
        
        if not selected_media:
            # If no video found, take the first available media
            selected_media = medias[0]
        
        download_url = selected_media.get("url")
        file_extension = selected_media.get("extension", "mp4")
        media_type = selected_media.get("type", "video")
        quality = selected_media.get("quality", "Unknown")
        # Robust duration int
        duration_value = selected_media.get("duration", duration_api)
        try:
            duration_sec = int(duration_value) if duration_value not in (None, "", "Unknown") else 0
        except Exception:
            duration_sec = 0
        
        if not download_url:
            await status_msg.edit_text(f"❌ لینک دانلود از {platform} یافت نشد.")
            return
        
        # Create filename
        safe_title_src = title or selected_media.get('title') or platform
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', str(safe_title_src)[:50])
        filename = f"{safe_title}.{file_extension}"
        
        # Download file
        await status_msg.edit_text(f"⬇️ در حال دانلود از {platform}...")
        download_result = await download_file_simple(download_url, filename)
        
        # Extract file_path from tuple (file_path, total_size)
        if isinstance(download_result, tuple):
            file_path, total_size = download_result
        else:
            file_path = download_result
        
        if not file_path or not os.path.exists(file_path):
            await status_msg.edit_text(f"❌ خطا در دانلود فایل از {platform}.")
            return
        
        # Prepare caption (trim to safe length)
        caption = f"🎵 **{title}**\n"
        caption += f"👤 **نویسنده:** {author}\n"
        caption += f"⏱️ **مدت زمان:** {duration_sec} ثانیه\n"
        caption += f"🔗 **پلتفرم:** {platform}\n"
        caption += f"📊 **کیفیت:** {quality}\n"
        caption += f"📁 **نوع:** {media_type.title()}"
        caption = _safe_caption(caption, max_len=950)
        
        # Check advertisement settings once
        ad_enabled = False
        ad_position = 'after'  # default
        try:
            with open('plugins/database.json', 'r', encoding='utf-8') as f:
                db_data = json.load(f)
            ad_settings = db_data.get('advertisement', {})
            ad_enabled = ad_settings.get('enabled', False)
            ad_position = ad_settings.get('position', 'after')
        except Exception:
            pass
        
        # Send advertisement before content if enabled and position is 'before'
        if ad_enabled and ad_position == 'before':
            await send_advertisement(client, message.chat.id)
            await asyncio.sleep(1)  # Wait 1 second after advertisement
        
        # Upload file based on type
        await status_msg.edit_text(f"📤 در حال ارسال فایل {platform}...")
        
        try:
            # Decide upload method based on media type and extension
            image_exts = ["jpg", "jpeg", "png", "webp"]
            video_exts = ["mp4", "avi", "mov", "mkv", "webm"]

            if media_type in ("image", "photo") or file_extension.lower() in image_exts or platform.lower() in ("pinterest", "imgur"):
                await client.send_photo(
                    chat_id=message.chat.id,
                    photo=file_path,
                    caption=caption,
                )
            elif (media_type == "video" or file_extension.lower() in video_exts or platform.lower() == "tiktok"):
                await client.send_video(
                    chat_id=message.chat.id,
                    video=file_path,
                    caption=caption,
                    duration=duration_sec,
                    supports_streaming=True
                )
            else:
                await client.send_audio(
                    chat_id=message.chat.id,
                    audio=file_path,
                    caption=caption,
                    duration=duration_sec,
                    title=title,
                    performer=author
                )
        except Exception as upload_error:
            print(f"Upload error: {upload_error}")
            await client.send_document(
                chat_id=message.chat.id,
                document=file_path,
                caption=_safe_caption(caption, max_len=950)
            )
        
        # Delete status message
        await status_msg.delete()
        
        # Send advertisement after content if enabled and position is 'after'
        if ad_enabled and ad_position == 'after':
            await asyncio.sleep(1)  # Wait 1 second after upload
            await send_advertisement(client, message.chat.id)
        
        # Increment download count
        now_str = _dt.now().isoformat(timespec='seconds')
        db.increment_request(user_id, now_str)
        
        # Clean up downloaded file
        try:
            os.remove(file_path)
        except:
            pass
            
    except Exception as e:
        error_msg = str(e)
        print(f"Universal download error: {error_msg}")
        try:
            if "API Error" in error_msg:
                await message.reply_text(f"❌ خطا در ارتباط با سرور {platform}. لطفاً بعداً تلاش کنید.")
            elif "medias" in error_msg:
                await message.reply_text(f"❌ فایل قابل دانلود از {platform} یافت نشد.")
            else:
                await message.reply_text(f"❌ خطا در پردازش لینک {platform}: {error_msg}")
        except:
            pass