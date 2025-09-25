import asyncio
import http.client
import json
import os
import re
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from plugins.start import SPOTIFY_REGEX, TIKTOK_REGEX, SOUNDCLOUD_REGEX
from plugins.instagram import send_advertisement, download_file_with_progress
from plugins.db_wrapper import DB
from plugins import constant
from datetime import datetime as _dt

# Use the same database system as Instagram handler
txt = constant.TEXT

def get_platform_name(url):
    """Determine the platform based on URL"""
    if SPOTIFY_REGEX.search(url):
        return "Spotify"
    elif TIKTOK_REGEX.search(url):
        return "TikTok"
    elif SOUNDCLOUD_REGEX.search(url):
        return "SoundCloud"
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
        print(f"API Response: {response_data}")
        return response_data
    except Exception as e:
        print(f"API Error: {e}")
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
        
        # Send advertisement before content if enabled
        try:
            with open('plugins/database.json', 'r', encoding='utf-8') as f:
                db_data = json.load(f)
            ad_settings = db_data.get('advertisement', {})
            if ad_settings.get('enabled', False) and ad_settings.get('position') == 'before':
                await send_advertisement(client, message.chat.id)
        except Exception:
            pass
        
        # Get data from API
        await status_msg.edit_text(f"📡 در حال دریافت اطلاعات از {platform}...")
        api_data = get_universal_data_from_api(url)
        
        if not api_data or "medias" not in api_data:
            await status_msg.edit_text(f"❌ خطا در دریافت اطلاعات از {platform}. لطفاً لینک را بررسی کنید.")
            return
        
        # Check for API errors
        if api_data.get("error", False) or api_data.get("data", {}).get("error", False):
            error_message = api_data.get("message", "خطای نامشخص")
            await status_msg.edit_text(f"❌ خطا در دریافت اطلاعات از {platform}: {error_message}")
            return
        
        # Extract media information
        title = api_data.get("title", "Unknown Title")
        author = api_data.get("author", "Unknown Author")
        duration = api_data.get("duration", "Unknown")
        thumbnail = api_data.get("thumbnail", "")
        
        # Find the best quality media
        medias = api_data.get("medias", [])
        if not medias:
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
        
        if not download_url:
            await status_msg.edit_text(f"❌ لینک دانلود از {platform} یافت نشد.")
            return
        
        # Create filename
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title[:50])
        filename = f"{safe_title}.{file_extension}"
        
        # Download file
        await status_msg.edit_text(f"⬇️ در حال دانلود از {platform}...")
        file_path = await download_file_with_progress(download_url, filename, status_msg, f"⬇️ دانلود {platform}", platform)
        
        if not file_path or not os.path.exists(file_path):
            await status_msg.edit_text(f"❌ خطا در دانلود فایل از {platform}.")
            return
        
        # Prepare caption
        caption = f"🎵 **{title}**\n"
        caption += f"👤 **نویسنده:** {author}\n"
        caption += f"⏱️ **مدت زمان:** {duration}\n"
        caption += f"🔗 **پلتفرم:** {platform}\n"
        caption += f"📊 **کیفیت:** {quality}\n"
        caption += f"📁 **نوع:** {media_type.title()}"
        
        # Send advertisement before content if enabled
        try:
            with open('plugins/database.json', 'r', encoding='utf-8') as f:
                db_data = json.load(f)
            ad_settings = db_data.get('advertisement', {})
            if ad_settings.get('enabled', False) and ad_settings.get('position') == 'before':
                await send_advertisement(client, message.chat.id)
                await asyncio.sleep(1)  # Wait 1 second after advertisement
        except Exception:
            pass
        
        # Upload file based on type
        await status_msg.edit_text(f"📤 در حال ارسال فایل {platform}...")
        
        try:
            # Force video upload for TikTok and other video platforms
            if (media_type == "video" or 
                file_extension in ["mp4", "avi", "mov", "mkv", "webm"] or 
                platform.lower() == "tiktok"):
                await client.send_video(
                    chat_id=message.chat.id,
                    video=file_path,
                    caption=caption,
                    duration=int(duration) if duration.isdigit() else 0,
                    supports_streaming=True
                )
            else:
                await client.send_audio(
                    chat_id=message.chat.id,
                    audio=file_path,
                    caption=caption,
                    duration=int(duration) if duration.isdigit() else 0,
                    title=title,
                    performer=author
                )
        except Exception as upload_error:
            print(f"Upload error: {upload_error}")
            await client.send_document(
                chat_id=message.chat.id,
                document=file_path,
                caption=caption
            )
        
        # Delete status message
        await status_msg.delete()
        
        # Wait 1 second after upload (similar to Instagram timing)
        await asyncio.sleep(1)
        
        # Send advertisement after content if enabled
        try:
            with open('plugins/database.json', 'r', encoding='utf-8') as f:
                db_data = json.load(f)
            ad_settings = db_data.get('advertisement', {})
            if ad_settings.get('enabled', False) and ad_settings.get('position') == 'after':
                await send_advertisement(client, message.chat.id)
        except Exception:
            pass
        
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