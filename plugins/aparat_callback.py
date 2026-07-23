"""
Aparat Callback Handler - مدیریت دانلود از آپارات
مشابه با YouTube Callback اما ساده‌تر
نویسنده: Kiro AI Assistant
تاریخ: 2025-11-01
"""

import os
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from pyrogram.enums import ParseMode
from plugins.logger_config import get_logger
from plugins.aparat_handler import video_cache
from plugins.sqlite_db_wrapper import DB
import yt_dlp

logger = get_logger('aparat_callback')


def format_size(bytes_size: int) -> str:
    """فرمت کردن حجم فایل"""
    if bytes_size >= 1024 * 1024 * 1024:
        return f"{bytes_size / (1024*1024*1024):.2f} GB"
    elif bytes_size >= 1024 * 1024:
        return f"{bytes_size / (1024*1024):.2f} MB"
    elif bytes_size >= 1024:
        return f"{bytes_size / 1024:.2f} KB"
    return f"{bytes_size} B"


async def download_aparat_video(url: str, quality: str) -> dict:
    """دانلود ویدیو از آپارات با کیفیت مشخص"""
    try:
        logger.info(f"Downloading Aparat video: quality={quality}")
        
        # Get video info from cache to get format_id
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'outtmpl': 'downloads/aparat_%(id)s.%(ext)s',
        }
        
        # Set format based on quality
        if quality == 'best':
            ydl_opts['format'] = 'best'
        else:
            # Try to get specific quality
            ydl_opts['format'] = f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]'
        
        loop = asyncio.get_event_loop()
        
        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
                return {
                    'file_path': file_path,
                    'title': info.get('title', 'بدون عنوان'),
                    'duration': info.get('duration', 0),
                    'filesize': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                }
        
        result = await loop.run_in_executor(None, _download)
        logger.info(f"Download completed: {result['file_path']}")
        return result
        
    except Exception as e:
        logger.error(f"Error downloading Aparat video: {e}")
        raise


@Client.on_callback_query(filters.regex(r'^aparat_(dl_\w+|cancel)$'))
async def handle_aparat_quality_selection(client: Client, call: CallbackQuery):
    """Handler انتخاب کیفیت آپارات"""
    start_time = time.time()
    user_id = call.from_user.id
    data = call.data
    
    logger.info(f"Aparat quality selection from user {user_id}: {data}")
    
    try:
        # Get video info from cache
        video_info = video_cache.get(user_id)
        
        if not video_info:
            await call.answer(
                "❌ اطلاعات ویدیو یافت نشد. لطفاً دوباره لینک را ارسال کنید.",
                show_alert=True
            )
            return
        
        # Handle cancel
        if data == 'aparat_cancel':
            await call.edit_message_text("❌ دانلود لغو شد.")
            if user_id in video_cache:
                del video_cache[user_id]
            return
        
        # Parse quality selection
        selected_quality = data.replace('aparat_dl_', '')
        
        # Get quality info
        quality_info = video_info['qualities'].get(selected_quality)
        
        if not quality_info:
            await call.answer(
                "❌ کیفیت انتخابی در دسترس نیست.",
                show_alert=True
            )
            return
        
        await call.answer()
        
        # Update message to show download started
        await call.edit_message_text(
            f"⬇️ **در حال دانلود...**\n\n"
            f"🎬 {video_info['title']}\n"
            f"📹 کیفیت: {selected_quality}p\n\n"
            f"⏳ لطفاً صبر کنید...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Download video
        try:
            download_result = await download_aparat_video(
                video_info['url'],
                selected_quality
            )
        except Exception as e:
            await call.edit_message_text(
                f"❌ **خطا در دانلود**\n\n"
                f"متأسفانه خطایی رخ داد: {str(e)[:100]}\n\n"
                f"لطفاً دوباره تلاش کنید.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        file_path = download_result['file_path']
        
        if not os.path.exists(file_path):
            await call.edit_message_text(
                "❌ **خطا در دانلود**\n\n"
                "فایل دانلود نشد. لطفاً دوباره تلاش کنید.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Update message to show upload started
        await call.edit_message_text(
            f"⬆️ **در حال آپلود...**\n\n"
            f"🎬 {video_info['title']}\n"
            f"📹 کیفیت: {selected_quality}p\n"
            f"📦 حجم: {format_size(download_result['filesize'])}\n\n"
            f"⏳ لطفاً صبر کنید...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Upload to Telegram
        try:
            caption = (
                f"🎬 <b>{video_info['title']}</b>\n\n"
                f"📹 کیفیت: {selected_quality}p\n"
                f"📦 حجم: {format_size(download_result['filesize'])}\n"
                f"👁 بازدید: {video_info.get('view_count', 0):,}\n\n"
                f"🎥 از آپارات دانلود شد"
            )
            
            # Convert duration to int
            duration = download_result.get('duration', 0)
            if isinstance(duration, float):
                duration = int(duration)
            
            await client.send_video(
                chat_id=call.message.chat.id,
                video=file_path,
                caption=caption,
                parse_mode=ParseMode.HTML,
                duration=duration,
                supports_streaming=True,
                reply_to_message_id=call.message.reply_to_message.id if call.message.reply_to_message else None
            )
            
            # Delete status message
            await call.message.delete()
            
        except Exception as e:
            logger.error(f"Error uploading video: {e}")
            await call.edit_message_text(
                f"❌ **خطا در آپلود**\n\n"
                f"متأسفانه خطایی رخ داد: {str(e)[:100]}\n\n"
                f"لطفاً دوباره تلاش کنید.",
                parse_mode=ParseMode.MARKDOWN
            )
        finally:
            # Clean up
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Cleaned up file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up file: {e}")
        
        # Update stats
        try:
            from datetime import datetime
            db = DB()
            now_str = datetime.now().isoformat()
            db.increment_request(user_id, now_str)
            logger.info(f"Stats updated for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to update stats: {e}")
        
        # Remove from cache
        if user_id in video_cache:
            del video_cache[user_id]
        
        elapsed = time.time() - start_time
        logger.info(f"Aparat download completed in {elapsed:.2f}s")
        
    except Exception as e:
        logger.error(f"Error in Aparat callback: {e}")
        try:
            await call.edit_message_text(
                f"❌ **خطا**\n\n"
                f"متأسفانه خطایی رخ داد: {str(e)[:100]}",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass


print("✅ Aparat Callback Handler loaded")
print("   - Quality selection callback")
print("   - Download and upload")
