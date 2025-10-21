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


import asyncio
import time
from pyrogram import Client
from pyrogram.types import CallbackQuery
from plugins.stream_utils import direct_youtube_upload
from plugins.logger_config import get_logger, get_performance_logger

# Initialize loggers
callback_logger = get_logger('youtube_callback')
performance_logger = get_performance_logger()

async def handle_youtube_new_callback(client: Client, callback_query: CallbackQuery):
    """
    Handle YouTube download callback with comprehensive logging and timing
    """
    callback_start_time = time.time()
    
    try:
        callback_logger.info(f"🎬 YouTube callback received from user {callback_query.from_user.id}")
        performance_logger.info(f"[CALLBACK_START] User: {callback_query.from_user.id}, Data: {callback_query.data}")
        
        # Parse callback data
        data_parts = callback_query.data.split('_')
        if len(data_parts) < 3:
            callback_logger.error(f"❌ Invalid callback data format: {callback_query.data}")
            await callback_query.answer("❌ خطا در پردازش درخواست", show_alert=True)
            return
        
        action = data_parts[1]  # 'new'
        format_id = data_parts[2]
        
        callback_logger.info(f"📋 Parsed callback - Action: {action}, Format ID: {format_id}")
        
        # Get the original message and extract URL
        original_message = callback_query.message
        if not original_message or not original_message.text:
            callback_logger.error("❌ Original message not found or empty")
            await callback_query.answer("❌ پیام اصلی یافت نشد", show_alert=True)
            return
        
        # Extract URL from message text (assuming it's in the message)
        message_lines = original_message.text.split('\n')
        url = None
        title = "Unknown Video"
        
        for line in message_lines:
            if line.startswith('🔗') or 'youtube.com' in line or 'youtu.be' in line:
                # Extract URL from line
                words = line.split()
                for word in words:
                    if 'youtube.com' in word or 'youtu.be' in word:
                        url = word
                        break
            elif line.startswith('🏷️'):
                title = line.replace('🏷️ عنوان:', '').strip()
        
        if not url:
            callback_logger.error("❌ URL not found in original message")
            await callback_query.answer("❌ لینک ویدیو یافت نشد", show_alert=True)
            return
        
        callback_logger.info(f"🔗 Extracted URL: {url}")
        callback_logger.info(f"🏷️ Video title: {title[:50]}...")
        
        # Acknowledge the callback
        await callback_query.answer("⏳ در حال آماده‌سازی دانلود...")
        
        # Update message to show download started
        preparation_start = time.time()
        callback_logger.info("📝 Updating message to show download started...")
        
        try:
            await original_message.edit_text(
                f"🚀 **شروع دانلود**\n\n"
                f"🏷️ **عنوان:** {title}\n"
                f"🎛️ **کیفیت:** {format_id}\n"
                f"📥 **وضعیت:** در حال آماده‌سازی...\n\n"
                f"⏰ **زمان شروع:** {time.strftime('%H:%M:%S')}"
            )
            preparation_time = time.time() - preparation_start
            callback_logger.info(f"✅ Message updated in {preparation_time:.2f}s")
            performance_logger.info(f"[MESSAGE_UPDATE_TIME] {preparation_time:.2f}s")
            
        except Exception as e:
            callback_logger.warning(f"⚠️ Failed to update message: {e}")
        
        # Prepare quality info for direct_youtube_upload
        quality_info = {
            'format_id': format_id,
            'type': 'video' if not format_id.endswith('_audio') else 'audio_only'
        }
        
        callback_logger.info(f"🎯 Quality info prepared: {quality_info}")
        
        # Define progress callback
        last_progress_update = 0
        progress_start_time = time.time()
        
        def progress_callback(downloaded_bytes, total_bytes):
            nonlocal last_progress_update
            current_time = time.time()
            
            if total_bytes > 0:
                progress_percent = (downloaded_bytes / total_bytes) * 100
                
                # Update every 5% or every 10 seconds
                if (progress_percent - last_progress_update >= 5) or (current_time - progress_start_time >= 10):
                    last_progress_update = progress_percent
                    
                    elapsed_time = current_time - progress_start_time
                    speed_mbps = (downloaded_bytes / (1024 * 1024)) / elapsed_time if elapsed_time > 0 else 0
                    
                    callback_logger.info(f"📊 Progress: {progress_percent:.1f}% ({downloaded_bytes/(1024*1024):.1f}/{total_bytes/(1024*1024):.1f} MB) - Speed: {speed_mbps:.2f} MB/s")
                    performance_logger.info(f"[DOWNLOAD_PROGRESS] {progress_percent:.1f}% - Speed: {speed_mbps:.2f}MB/s")
                    
                    # Update message with progress
                    try:
                        asyncio.create_task(original_message.edit_text(
                            f"📥 **در حال دانلود**\n\n"
                            f"🏷️ **عنوان:** {title}\n"
                            f"🎛️ **کیفیت:** {format_id}\n"
                            f"📊 **پیشرفت:** {progress_percent:.1f}%\n"
                            f"💾 **دانلود شده:** {downloaded_bytes/(1024*1024):.1f} MB از {total_bytes/(1024*1024):.1f} MB\n"
                            f"🚀 **سرعت:** {speed_mbps:.2f} MB/s\n\n"
                            f"⏰ **زمان شروع:** {time.strftime('%H:%M:%S', time.localtime(progress_start_time))}"
                        ))
                    except Exception:
                        pass  # Ignore message update errors during progress
        
        # Start the direct upload process
        upload_start_time = time.time()
        callback_logger.info("🚀 Starting direct YouTube upload process...")
        performance_logger.info(f"[DIRECT_UPLOAD_CALL_START] URL: {url}, Format: {format_id}")
        
        try:
            # Update message to show upload starting
            await original_message.edit_text(
                f"📤 **شروع آپلود**\n\n"
                f"🏷️ **عنوان:** {title}\n"
                f"🎛️ **کیفیت:** {format_id}\n"
                f"📥 **وضعیت:** دانلود تکمیل شد، شروع آپلود...\n\n"
                f"⏰ **زمان شروع دانلود:** {time.strftime('%H:%M:%S', time.localtime(progress_start_time))}\n"
                f"⏰ **زمان شروع آپلود:** {time.strftime('%H:%M:%S')}"
            )
        except Exception as e:
            callback_logger.warning(f"⚠️ Failed to update upload start message: {e}")
        
        # Call direct_youtube_upload
        result = await direct_youtube_upload(
            client=client,
            chat_id=callback_query.message.chat.id,
            url=url,
            quality_info=quality_info,
            title=title,
            progress_callback=progress_callback
        )
        
        upload_end_time = time.time()
        total_process_time = upload_end_time - callback_start_time
        
        if result.get('success'):
            callback_logger.info(f"✅ Direct upload completed successfully in {total_process_time:.2f}s")
            performance_logger.info(f"[CALLBACK_SUCCESS] Total time: {total_process_time:.2f}s")
            
            # Log detailed timing breakdown
            if 'total_time' in result:
                internal_time = result['total_time']
                callback_logger.info(f"📊 Timing breakdown - Internal process: {internal_time:.2f}s, Total callback: {total_process_time:.2f}s")
                performance_logger.info(f"[TIMING_BREAKDOWN] Internal: {internal_time:.2f}s, Callback: {total_process_time:.2f}s")
            
            # Delete the progress message since file was sent successfully
            try:
                await original_message.delete()
                callback_logger.info("🗑️ Progress message deleted after successful upload")
            except Exception as e:
                callback_logger.warning(f"⚠️ Failed to delete progress message: {e}")
                
            # Log upload method used
            if result.get('in_memory'):
                callback_logger.info("💾 Upload method: Memory streaming")
                performance_logger.info("[UPLOAD_METHOD] Memory streaming")
            elif result.get('fallback_used'):
                callback_logger.info("🔄 Upload method: Traditional fallback")
                performance_logger.info("[UPLOAD_METHOD] Traditional fallback")
            else:
                callback_logger.info("📁 Upload method: Temporary file")
                performance_logger.info("[UPLOAD_METHOD] Temporary file")
                
        else:
            error_msg = result.get('error', 'Unknown error')
            callback_logger.error(f"❌ Direct upload failed after {total_process_time:.2f}s: {error_msg}")
            performance_logger.error(f"[CALLBACK_ERROR] Time: {total_process_time:.2f}s, Error: {error_msg}")
            
            # Update message with error
            try:
                await original_message.edit_text(
                    f"❌ **خطا در دانلود**\n\n"
                    f"🏷️ **عنوان:** {title}\n"
                    f"🎛️ **کیفیت:** {format_id}\n"
                    f"💥 **خطا:** {error_msg}\n\n"
                    f"⏰ **زمان کل:** {total_process_time:.2f} ثانیه\n\n"
                    f"لطفاً دوباره تلاش کنید یا کیفیت دیگری انتخاب کنید."
                )
            except Exception as e:
                callback_logger.warning(f"⚠️ Failed to update error message: {e}")
    
    except Exception as e:
        total_error_time = time.time() - callback_start_time
        callback_logger.error(f"❌ Callback handler failed after {total_error_time:.2f}s: {e}")
        performance_logger.error(f"[CALLBACK_HANDLER_ERROR] Time: {total_error_time:.2f}s, Error: {str(e)}")
        
        try:
            await callback_query.answer("❌ خطا در پردازش درخواست", show_alert=True)
        except Exception:
            pass  # Ignore if we can't even send the error response