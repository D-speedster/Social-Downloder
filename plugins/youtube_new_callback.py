"""
Callback handler جدید برای سیستم پیشرفته یوتیوب
"""

import os
import sys
import time
import asyncio
import tempfile
import shutil
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from pyrogram.enums import ParseMode
from plugins.start import step
from plugins.sqlite_db_wrapper import DB
from plugins.logger_config import get_logger, get_performance_logger
from plugins.youtube_quality_selector import quality_selector
from plugins.youtube_advanced_downloader import youtube_downloader
from plugins.concurrency import acquire_slot, release_slot, get_queue_stats, reserve_user, release_user
from utils.util import convert_size
from plugins.stream_utils import smart_upload_strategy, direct_youtube_upload

# Initialize loggers
callback_new_logger = get_logger('youtube_callback_new')
performance_logger = get_performance_logger()

# Progress tracking
previous_progress = {}
previous_progress_ts = {}

def progress_hook(d, user_id: int, call: CallbackQuery):
    """Hook برای نمایش پیشرفت دانلود"""
    global previous_progress
    
    try:
        if d['status'] == 'downloading':
            # Calculate progress percentage
            if 'total_bytes' in d and d['total_bytes']:
                downloaded = d.get('downloaded_bytes', 0)
                total = d['total_bytes']
                progress = int((downloaded / total) * 100)
            elif 'total_bytes_estimate' in d and d['total_bytes_estimate']:
                downloaded = d.get('downloaded_bytes', 0)
                total = d['total_bytes_estimate']
                progress = int((downloaded / total) * 100)
            else:
                return
            
            # Only update if progress changed significantly or time gate passed
            last_ts = previous_progress_ts.get(user_id, 0.0)
            if (user_id not in previous_progress) or abs(progress - previous_progress[user_id]) >= 5 or (time.time() - last_ts) >= 1.5:
                previous_progress[user_id] = progress
                previous_progress_ts[user_id] = time.time()
                
                # Create progress bar
                filled = int(progress / 5)
                empty = 20 - filled
                progress_bar = "█" * filled + "░" * empty
                
                # Format speed and ETA
                speed = d.get('speed', 0)
                eta = d.get('eta', 0)
                
                speed_text = f"{convert_size(2, speed)}/s" if speed else "نامشخص"
                eta_text = f"{eta}s" if eta else "نامشخص"
                
                progress_text = (
                    f"🚀 **آپلود مستقیم در حال انجام...**\n\n"
                    f"🔄 پیشرفت: {progress}%\n"
                    f"[{progress_bar}]\n\n"
                    f"⚡ سرعت: {speed_text}\n"
                    f"⏱ زمان باقی‌مانده: {eta_text}\n\n"
                    f"💡 فایل مستقیماً به تلگرام ارسال می‌شود"
                )
                
                # Update message asynchronously
                asyncio.create_task(safe_edit_message(call, progress_text))
                
    except Exception as e:
        callback_new_logger.error(f"Progress hook error: {e}")

async def safe_edit_message(call: CallbackQuery, text: str, reply_markup=None):
    """ویرایش ایمن پیام"""
    try:
        await call.edit_message_text(
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    except Exception as e:
        callback_new_logger.debug(f"Message edit failed (normal): {e}")

@Client.on_callback_query(filters.regex(r'^(dl_quality_\d+|dl_audio_best|quality_page_\d+|cancel_download)$'))
async def handle_new_quality_callback(client: Client, call: CallbackQuery):
    """Handler جدید برای callback های انتخاب کیفیت"""
    start_time = time.time()
    user_id = call.from_user.id
    data = call.data
    
    callback_new_logger.info(f"New quality callback from user {user_id}: {data}")
    performance_logger.info(f"[USER:{user_id}] NEW CALLBACK started: {data}")
    
    try:
        # Get stored info
        quality_options = step.get('quality_options')
        url = step.get('url')
        
        if not quality_options or not url:
            await call.answer("❌ اطلاعات ویدیو یافت نشد. لطفاً دوباره تلاش کنید.", show_alert=True)
            return
        
        if data == 'cancel_download':
            await call.edit_message_text("❌ دانلود لغو شد.")
            return
        
        elif data.startswith('quality_page_'):
            # Handle pagination
            page = int(data.split('_')[-1])
            keyboard = quality_selector.create_quality_keyboard(quality_options['qualities'], page)
            info_text = quality_selector.format_video_info_text(quality_options)
            
            await call.edit_message_text(
                text=info_text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
            await call.answer()
            return
        
        elif data == 'dl_audio_best':
            # Handle audio-only download
            audio_info = await quality_selector.get_audio_only_info(quality_options['raw_info'])
            if not audio_info:
                await call.answer("❌ فرمت صوتی یافت نشد.", show_alert=True)
                return
            
            selected_quality = audio_info
            
        elif data.startswith('dl_quality_'):
            # Handle quality selection
            quality_index = int(data.split('_')[-1])
            selected_quality = quality_selector.get_quality_by_index(quality_options['qualities'], quality_index)
            
            if not selected_quality:
                await call.answer("❌ کیفیت انتخابی نامعتبر است.", show_alert=True)
                return
        
        else:
            await call.answer("❌ درخواست نامعتبر.", show_alert=True)
            return
        
        # Start download process
        await start_download_process(client, call, url, selected_quality, quality_options)
        
        # Log callback time
        callback_time = time.time() - start_time
        performance_logger.info(f"[USER:{user_id}] NEW CALLBACK completed in: {callback_time:.2f} seconds")
        
    except Exception as e:
        callback_new_logger.error(f"Callback error: {e}")
        performance_logger.error(f"[USER:{user_id}] NEW CALLBACK ERROR: {str(e)}")
        
        try:
            await call.edit_message_text(
                f"❌ **خطا در پردازش درخواست**\n\n"
                f"متأسفانه خطایی رخ داده است.\n"
                f"لطفاً دوباره تلاش کنید.\n\n"
                f"جزئیات: {str(e)[:100]}...",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            await call.answer("❌ خطا در پردازش درخواست.", show_alert=True)

async def start_download_process(client: Client, call: CallbackQuery, url: str, 
                               selected_quality: dict, quality_options: dict):
    """شروع فرآیند دانلود"""
    user_id = call.from_user.id
    download_start = time.time()
    
    # Per-user concurrency guard
    user_reserved = reserve_user(user_id)
    if not user_reserved:
        await call.answer("⚠️ محدودیت دانلود همزمان شما پر شده است. لطفاً صبر کنید.", show_alert=True)
        return
    
    callback_new_logger.info(f"Starting download process for user {user_id}")
    performance_logger.info(f"[USER:{user_id}] DOWNLOAD started - Quality: {selected_quality['resolution']}")
    
    # Update message to show download started
    quality_text = selected_quality['resolution']
    if selected_quality.get('fps', 0) > 0:
        quality_text += f"@{selected_quality['fps']}fps"
    
    size_text = convert_size(2, selected_quality['filesize']) if selected_quality.get('filesize') else "نامشخص"
    
    download_info = (
        f"🚀 **شروع آپلود مستقیم**\n\n"
        f"🎬 **{quality_options['title']}**\n\n"
        f"📊 کیفیت: {quality_text}\n"
        f"📦 حجم تقریبی: {size_text}\n"
        f"🔧 نوع: {'ترکیبی' if selected_quality['type'] == 'combined' else 'نیاز به ترکیب' if selected_quality['type'] == 'mergeable' else 'فقط صدا'}\n\n"
        f"⏳ لطفاً صبر کنید..."
    )
    
    await call.edit_message_text(download_info, parse_mode=ParseMode.MARKDOWN)
    slot_acquired = False
    
    try:
        stats = get_queue_stats()
        if stats['active'] >= stats['capacity']:
            queue_position = stats['waiting'] + 1
            await call.edit_message_text(
                download_info + f"\n\n🕒 ظرفیت دانلود مشغول است (نفر {queue_position} در صف)\n⏳ دانلود به‌زودی شروع می‌شود...", 
                parse_mode=ParseMode.MARKDOWN
            )
        await acquire_slot()
        slot_acquired = True
        # Create output filename
        safe_title = "".join(c for c in quality_options['title'] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title[:50]  # Limit length
        
        if selected_quality['type'] == 'audio_only':
            filename = f"{safe_title}.{selected_quality.get('ext', 'm4a')}"
        else:
            filename = f"{safe_title}_{selected_quality['resolution']}.mp4"
        
        output_path = os.path.join(tempfile.gettempdir(), filename)
        
        # Setup progress callback for direct upload
        def progress_callback(d):
            progress_hook(d, user_id, call)
        
        # آپلود مستقیم بدون ذخیره در سرور
        upload_result = await direct_youtube_upload(
            client=client,
            chat_id=call.message.chat.id,
            url=url,
            quality_info=selected_quality,
            title=quality_options['title'],
            thumbnail_url=quality_options.get('thumbnail'),
            progress_callback=progress_callback,
            reply_to_message_id=call.message.reply_to_message.message_id if call.message.reply_to_message else None
        )
        
        if upload_result.get("success"):
            # موفقیت آپلود
            total_time = time.time() - download_start
            performance_logger.info(f"[USER:{user_id}] DIRECT UPLOAD completed in: {total_time:.2f} seconds")
            
            # حذف پیام callback
            try:
                await call.message.delete()
            except Exception as e:
                callback_new_logger.warning(f"Failed to delete callback message: {e}")
                
            callback_new_logger.info(f"Download process completed successfully in {total_time:.2f}s")
        else:
            # خطا در آپلود
            error_msg = upload_result.get("error", "نامشخص")
            await call.edit_message_text(f"❌ خطا در آپلود فایل: {error_msg}")
            callback_new_logger.error(f"Direct upload failed for user {user_id}: {error_msg}")
        
        try:
            if slot_acquired:
                release_slot()
        except Exception:
            pass
        try:
            if 'user_reserved' in locals() and user_reserved:
                release_user(user_id)
        except Exception:
            pass
        
    except Exception as e:
        callback_new_logger.error(f"Download process error: {e}")
        performance_logger.error(f"[USER:{user_id}] DOWNLOAD ERROR: {str(e)}")
        
        error_info = (
            f"❌ **خطا در دانلود**\n\n"
            f"متأسفانه دانلود با خطا مواجه شد.\n"
            f"لطفاً دوباره تلاش کنید.\n\n"
            f"جزئیات خطا: {str(e)[:100]}..."
        )
        
        try:
            await call.edit_message_text(error_info, parse_mode=ParseMode.MARKDOWN)
        except:
            await call.answer("❌ خطا در دانلود.", show_alert=True)
        finally:
            if slot_acquired:
                release_slot()
            if user_reserved:
                release_user(user_id)