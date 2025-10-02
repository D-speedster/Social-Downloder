"""
Handler جدید یوتیوب با سیستم پیشرفته دانلود و merge
"""

import os
import sys
import json
import time
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from plugins.start import step
from plugins.sqlite_db_wrapper import DB
from plugins.logger_config import get_logger, get_performance_logger
from plugins.youtube_quality_selector import quality_selector
# Import callback handler to register it
import plugins.youtube_new_callback
from plugins.youtube_advanced_downloader import youtube_downloader
from typing import Optional

# Initialize loggers
youtube_new_logger = get_logger('youtube_new')
performance_logger = get_performance_logger()

async def handle_youtube_url_new(client: Client, message: Message, url: str):
    """Handler جدید برای لینک‌های یوتیوب"""
    start_time = time.time()
    user_id = message.from_user.id
    
    performance_logger.info(f"[USER:{user_id}] NEW YouTube handler started for: {url}")
    youtube_new_logger.info(f"شروع پردازش جدید لینک یوتیوب برای کاربر {user_id}")
    
    # Get custom waiting message from database
    db = DB()
    custom_message_data = db.get_waiting_message_full('youtube')
    
    # Send initial processing message
    if custom_message_data and custom_message_data.get('type') == 'gif':
        processing_message = await message.reply_animation(
            animation=custom_message_data['content'],
            caption="🔄 در حال تحلیل ویدیو و استخراج کیفیت‌های موجود..."
        )
    elif custom_message_data and custom_message_data.get('type') == 'sticker':
        await message.reply_sticker(sticker=custom_message_data['content'])
        processing_message = await message.reply_text("🔄 در حال تحلیل ویدیو و استخراج کیفیت‌های موجود...")
    else:
        waiting_text = custom_message_data.get('content', "🔄 در حال تحلیل ویدیو و استخراج کیفیت‌های موجود...") if custom_message_data else "🔄 در حال تحلیل ویدیو و استخراج کیفیت‌های موجود..."
        processing_message = await message.reply_text(waiting_text)
    
    message_sent_time = time.time()
    performance_logger.info(f"[USER:{user_id}] Processing message sent after: {message_sent_time - start_time:.2f} seconds")
    
    try:
        # Get quality options
        extraction_start = time.time()
        quality_options = await quality_selector.get_quality_options(url)
        extraction_time = time.time() - extraction_start
        
        performance_logger.info(f"[USER:{user_id}] Quality extraction completed in: {extraction_time:.2f} seconds")
        
        if not quality_options:
            youtube_new_logger.error("Failed to get quality options")
            await processing_message.edit_text(
                "❌ **خطا در پردازش ویدیو**\n\n"
                "متأسفانه امکان دریافت اطلاعات ویدیو وجود ندارد.\n"
                "لطفاً موارد زیر را بررسی کنید:\n\n"
                "🔗 لینک معتبر باشد\n"
                "🌐 اتصال اینترنت برقرار باشد\n"
                "🔒 ویدیو در دسترس عموم باشد\n\n"
                "در صورت تکرار مشکل، لطفاً دوباره تلاش کنید.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Store info in step for callback handlers
        step['link'] = quality_options['raw_info']
        step['title'] = quality_options['title']
        step['duration'] = quality_options['duration']
        step['thumbnail'] = quality_options['thumbnail']
        step['quality_options'] = quality_options
        step['url'] = url
        # دانلود با کوکی انجام می‌شود
        
        # Create quality selection interface
        info_text = quality_selector.format_video_info_text(quality_options)
        keyboard = quality_selector.create_quality_keyboard(quality_options['qualities'])
        
        # Download and display thumbnail if available
        thumbnail_path = None
        if quality_options.get('thumbnail'):
            try:
                thumbnail_path = await download_thumbnail(quality_options['thumbnail'])
            except Exception as e:
                youtube_new_logger.warning(f"Failed to download thumbnail: {e}")
        
        # Send quality selection message
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                await processing_message.delete()
                await message.reply_photo(
                    photo=thumbnail_path,
                    caption=info_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
                # Clean up thumbnail
                try:
                    os.unlink(thumbnail_path)
                except:
                    pass
            except Exception as e:
                youtube_new_logger.warning(f"Failed to send photo message: {e}")
                await processing_message.edit_text(
                    text=info_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
        else:
            await processing_message.edit_text(
                text=info_text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        
        # Log total time
        end_time = time.time()
        total_time = end_time - start_time
        performance_logger.info(f"[USER:{user_id}] NEW HANDLER TOTAL TIME: {total_time:.2f} seconds")
        performance_logger.info(f"[USER:{user_id}] Breakdown - Message: {message_sent_time - start_time:.2f}s, Extraction: {extraction_time:.2f}s")
        
        if total_time > 10.0:
            performance_logger.warning(f"[USER:{user_id}] ⚠️ SLOW PROCESSING: {total_time:.2f}s (Target: <10s)")
        else:
            performance_logger.info(f"[USER:{user_id}] ✅ GOOD PROCESSING: {total_time:.2f}s (Target: <10s)")
        
        youtube_new_logger.info(f"Quality selection interface sent successfully in {total_time:.2f}s")
        
    except Exception as e:
        youtube_new_logger.error(f"Error in new YouTube handler: {e}")
        performance_logger.error(f"[USER:{user_id}] NEW HANDLER ERROR: {str(e)}")
        
        try:
            await processing_message.edit_text(
                "❌ **خطا در پردازش ویدیو**\n\n"
                "متأسفانه خطایی در پردازش ویدیو رخ داده است.\n"
                "لطفاً دوباره تلاش کنید.\n\n"
                f"جزئیات خطا: {str(e)[:100]}...",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            await processing_message.edit_text("خطا در پردازش ویدیو. لطفاً دوباره تلاش کنید.")

async def download_thumbnail(thumbnail_url: str) -> Optional[str]:
    """دانلود thumbnail ویدیو"""
    try:
        import aiohttp
        import tempfile
        
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail_url, timeout=10) as response:
                if response.status == 200:
                    content = await response.read()
                    
                    # Create temporary file
                    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                    temp_file.write(content)
                    temp_file.close()
                    
                    return temp_file.name
        
        return None
        
    except Exception as e:
        youtube_new_logger.error(f"Thumbnail download error: {e}")
        return None

# Register the new handler
@Client.on_message(filters.regex(r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})') & filters.private)
async def youtube_new_message_handler(client: Client, message: Message):
    """Handler پیام‌های یوتیوب جدید"""
    url = message.text.strip()
    await handle_youtube_url_new(client, message, url)