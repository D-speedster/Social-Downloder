from pyrogram import Client, filters
from pyrogram.types import Message
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
            await client.send_photo(
                chat_id=user_id,
                photo=file_id,
                caption=caption
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
    """Get Instagram data using RapidAPI"""
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
        
        if res.status != 200:
            print(f"API Error: Status {res.status}")
            return None
            
        response_data = json.loads(data.decode("utf-8"))
        return response_data
        
    except Exception as e:
        print(f"Instagram API Error: {e}")
        return None

async def download_file_with_progress(url, file_path, status_msg, title, type_label):
    """Download file with progress updates"""
    try:
        import asyncio
        
        # Get file size first
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            
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
                        
                        text = _format_status_text(title, type_label, size_mb, "در حال دانلود ...")
                        kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"🚀 پیشرفت: {percent}٪", callback_data="ignore")]])
                        
                        try:
                            await status_msg.edit_text(text, reply_markup=kb)
                        except Exception:
                            pass
        
        return file_path, total_size
        
    except Exception as e:
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
    
    # Check if user is in database
    db = DB()
    if not db.check_user_register(user_id):
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
                await message.reply_text("⛔ شما به دلیل تجاوز از حد مجاز روزانه موقتاً مسدود شده‌اید.\n\n⏰ لطفاً بعداً تلاش کنید.")
                return
        except Exception:
            pass
    
    # Send initial status message
    status_msg = await message.reply_text(
        "🔍 **در حال بررسی لینک اینستاگرام...**\n\n⏳ لطفاً صبر کنید...",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏳ در حال پردازش...", callback_data="ignore")]])
    )
    
    try:
        # Get Instagram data from API
        api_data = await get_instagram_data_from_api(url)
        
        if not api_data or not api_data.get('medias'):
            await status_msg.edit_text(
                "❌ **خطا در دریافت اطلاعات**\n\n🔍 لینک اینستاگرام معتبر نیست یا در دسترس نمی‌باشد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 تلاش مجدد", callback_data="start")]])
            )
            return
        
        # Extract media information
        title = api_data.get('title', 'Instagram Media')
        medias = api_data.get('medias', [])
        
        if not medias:
            await status_msg.edit_text(
                "❌ **فایل قابل دانلود یافت نشد**\n\n🔍 این پست ممکن است حاوی محتوای قابل دانلود نباشد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 تلاش مجدد", callback_data="start")]])
            )
            return
        
        # Select best quality media (prefer video over image)
        selected_media = None
        for media in medias:
            if media.get('type') == 'video':
                selected_media = media
                break
        
        if not selected_media:
            # If no video, take first image
            selected_media = medias[0]
        
        download_url = selected_media.get('url')
        if not download_url:
            await status_msg.edit_text(
                "❌ **خطا در دریافت لینک دانلود**\n\n🔍 لینک دانلود معتبر یافت نشد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 تلاش مجدد", callback_data="start")]])
            )
            return
        
        # Determine file type and extension
        media_type = selected_media.get('type', 'unknown')
        if media_type == 'video':
            type_label = "🎥 ویدیو"
            ext = 'mp4'
        elif media_type == 'image':
            type_label = "🖼️ عکس"
            ext = 'jpg'
        else:
            type_label = "📄 فایل"
            ext = 'mp4'  # default
        
        # Create filename
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()[:50]
        filename = f"{safe_title}_{int(time.time())}.{ext}"
        file_path = os.path.join(PATH, filename)
        
        # Update status
        await status_msg.edit_text(
            _format_status_text(title, type_label, "محاسبه...", "آماده‌سازی دانلود..."),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏳ در حال آماده‌سازی...", callback_data="ignore")]])
        )
        
        # Download file
        downloaded_file_path, total_bytes = await download_file_with_progress(download_url, file_path, status_msg, title, type_label)

        if not os.path.exists(downloaded_file_path):
            raise Exception("Downloaded file not found")

        total_mb_text = f"{(total_bytes/1024/1024):.2f}" if total_bytes else "نامشخص"
        
        # Update status for upload
        await status_msg.edit_text(
            _format_status_text(title, type_label, total_mb_text, "آماده‌سازی برای ارسال..."),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 در حال ارسال...", callback_data="ignore")]])
        )
        
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
        
        # Upload file
        if media_type == 'video':
            sent_msg = await message.reply_video(
                video=downloaded_file_path,
                caption=f"📥 **دانلود شده از اینستاگرام**\n\n📝 **عنوان:** {title}\n📏 **حجم:** {total_mb_text} مگابایت",
                progress=lambda current, total: None  # Simple progress without updates
            )
        else:
            sent_msg = await message.reply_photo(
                photo=downloaded_file_path,
                caption=f"📥 **دانلود شده از اینستاگرام**\n\n📝 **عنوان:** {title}\n📏 **حجم:** {total_mb_text} مگابایت"
            )
        
        # Wait a moment to ensure upload is complete
        await asyncio.sleep(2)
        
        # Send advertisement after content if position is 'after' and enabled (only if not sent before)
        if ad_enabled and ad_position == 'after':
            await send_advertisement(_, user_id)
        
        # Update user download count
        db.increment_request(user_id, datetime.now().isoformat())
        
        # Delete status message
        try:
            await status_msg.delete()
        except Exception:
            pass
        
        # Clean up file
        try:
            os.remove(downloaded_file_path)
        except Exception:
            pass
    
    except Exception as e:
        error_msg = str(e)
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