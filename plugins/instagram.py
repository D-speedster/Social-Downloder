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
        post_type = api_data.get('type', 'single')
        
        if not medias:
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
            await handle_multiple_media(_, message, status_msg, medias, title, user_id)
        else:
            # Handle single media
            await handle_single_media(_, message, status_msg, medias[0], title, user_id)
        
        # Send advertisement after content if position is 'after' and enabled
        if ad_enabled and ad_position == 'after':
            await send_advertisement(_, user_id)
        
        # Update user download count
        db.increment_request(user_id, datetime.now().isoformat())
        
        # Delete status message
        try:
            await status_msg.delete()
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


async def handle_single_media(client, message, status_msg, media, title, user_id):
    """Handle single media download and upload"""
    try:
        download_url = media.get('url')
        if not download_url:
            raise Exception("Download URL not found")
        
        # Determine file type and extension
        media_type = media.get('type', 'unknown')
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
        
        # Create safe caption
        safe_caption = create_safe_caption(title, 1)
        
        # If video, enforce resolution & generate thumbnail
        thumb_path = None
        width_arg = None
        height_arg = None
        final_path = downloaded_file_path
        try:
            if media_type == 'video':
                # Detect ffmpeg path (similar to youtube module)
                ffmpeg_path = os.environ.get('FFMPEG_PATH')
                if not ffmpeg_path:
                    candidates = [
                        "C:\\ffmpeg\\bin\\ffmpeg.exe",
                        "ffmpeg",
                        "/usr/bin/ffmpeg",
                        "/usr/local/bin/ffmpeg"
                    ]
                    for p in candidates:
                        if shutil.which(p) or os.path.exists(p):
                            ffmpeg_path = p
                            break
                # For Instagram most videos are <=720p; choose 1280x720 if source >=720 else 720x480
                # Probe height using ffprobe minimal; fallback to 720x480
                target_w, target_h = 720, 480
                try:
                    probe_cmd = [ffmpeg_path or 'ffmpeg', '-i', downloaded_file_path]
                    # Quick text probe by reading stderr output size; skip heavy parsing.
                except Exception:
                    pass
                # Prefer 1280x720 as primary
                target_w, target_h = 1280, 720
                # Re-encode
                base_noext, _ = os.path.splitext(downloaded_file_path)
                enforced_path = f"{base_noext}_{target_w}x{target_h}.mp4"
                try:
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
                except Exception as ee:
                    print(f"FFmpeg re-encode (IG) failed: {ee}")
                    final_path = downloaded_file_path
                
                # Thumbnail (<=320px, <=200KB)
                thumb_path = f"{base_noext}_thumb.jpg"
                try:
                    def make_thumb(q):
                        vf_thumb = 'scale=320:-2:force_original_aspect_ratio=decrease'
                        cmd_t = [ffmpeg_path or 'ffmpeg', '-y', '-ss', '2', '-i', final_path, '-frames:v', '1', '-vf', vf_thumb, '-q:v', str(q), thumb_path]
                        subprocess.run(cmd_t, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    for q in [5,6,7,8,9,10]:
                        try:
                            await asyncio.to_thread(make_thumb, q)
                            if os.path.exists(thumb_path) and os.path.getsize(thumb_path) <= 200*1024:
                                break
                        except Exception:
                            continue
                except Exception as te:
                    print(f"IG thumbnail error: {te}")
                    thumb_path = None
        except Exception as ie:
            print(f"IG enforce pipeline error: {ie}")
            thumb_path = None
            final_path = downloaded_file_path
        
        # Upload file
        if media_type == 'video':
            sent_msg = await message.reply_video(
                video=final_path,
                caption=safe_caption,
                thumb=thumb_path,
                width=width_arg,
                height=height_arg,
                progress=lambda current, total: None  # Simple progress without updates
            )
        else:
            sent_msg = await message.reply_photo(
                photo=downloaded_file_path,
                caption=safe_caption
            )
        
        # Wait a moment to ensure upload is complete
        await asyncio.sleep(2)
        
        # Clean up file
        try:
            if os.path.exists(final_path):
                os.remove(final_path)
            if final_path != downloaded_file_path and os.path.exists(downloaded_file_path):
                os.remove(downloaded_file_path)
            if thumb_path and os.path.exists(thumb_path):
                os.remove(thumb_path)
        except Exception:
            pass
            
    except Exception as e:
        print(f"Single media handling error: {e}")
        raise e


async def handle_multiple_media(client, message, status_msg, medias, title, user_id):
    """Handle multiple media download and upload as media group"""
    try:
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
                download_url = media.get('url')
                if not download_url:
                    continue
                
                # Determine file type and extension
                media_type = media.get('type', 'image')
                ext = 'mp4' if media_type == 'video' else 'jpg'
                
                # Create filename
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()[:30]
                filename = f"{safe_title}_{i+1}_{int(time.time())}.{ext}"
                file_path = os.path.join(PATH, filename)
                
                # Update progress
                await status_msg.edit_text(
                    f"📥 **دانلود چندرسانه‌ای اینستاگرام**\n\n📝 **عنوان:** {title[:100]}...\n📊 **پیشرفت:** {i+1}/{len(medias)}\n⏳ **وضعیت:** دانلود فایل {i+1}...",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"⏳ دانلود {i+1}/{len(medias)}...", callback_data="ignore")]])
                )
                
                # Simple download without progress for multiple files
                response = urllib.request.urlopen(download_url)
                with open(file_path, 'wb') as f:
                    f.write(response.read())
                
                if os.path.exists(file_path):
                    downloaded_files.append(file_path)
                    
                    # Add to media group
                    if media_type == 'video':
                        if i == 0:  # First item gets caption
                            media_group.append(InputMediaVideo(media=file_path, caption=create_safe_caption(title, len(medias))))
                        else:
                            media_group.append(InputMediaVideo(media=file_path))
                    else:
                        if i == 0:  # First item gets caption
                            media_group.append(InputMediaPhoto(media=file_path, caption=create_safe_caption(title, len(medias))))
                        else:
                            media_group.append(InputMediaPhoto(media=file_path))
                
            except Exception as e:
                print(f"Error downloading media {i+1}: {e}")
                continue
        
        if not media_group:
            await status_msg.edit_text(
                "❌ **خطا در دانلود فایل‌ها**\n\n🔍 هیچ فایل قابل دانلودی یافت نشد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 تلاش مجدد", callback_data="start")]])
            )
            return
        
        # Update status for upload
        await status_msg.edit_text(
            f"📥 **دانلود چندرسانه‌ای اینستاگرام**\n\n📝 **عنوان:** {title[:100]}...\n📊 **فایل‌های آماده:** {len(media_group)}\n📤 **وضعیت:** آماده‌سازی برای ارسال...",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 در حال ارسال...", callback_data="ignore")]])
        )
        
        # Send media group
        await message.reply_media_group(media=media_group)
        
        # Wait a moment to ensure upload is complete
        await asyncio.sleep(3)
        
        # Clean up files
        for file_path in downloaded_files:
            try:
                os.remove(file_path)
            except Exception:
                pass
                
    except Exception as e:
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