"""
YouTube Callback Handler - مدیریت انتخاب کیفیت و شروع دانلود
"""

import os
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from pyrogram.enums import ParseMode
from plugins.logger_config import get_logger
from plugins.youtube_handler import video_cache
from plugins.youtube_downloader import youtube_downloader
from plugins.youtube_uploader import youtube_uploader
from plugins.concurrency import acquire_slot, release_slot, get_queue_stats, reserve_user, release_user
from plugins.sqlite_db_wrapper import DB

logger = get_logger('youtube_callback')

def format_size(bytes_size: int) -> str:
    """فرمت کردن حجم فایل"""
    if bytes_size >= 1024 * 1024 * 1024:
        return f"{bytes_size / (1024*1024*1024):.2f} GB"
    elif bytes_size >= 1024 * 1024:
        return f"{bytes_size / (1024*1024):.2f} MB"
    elif bytes_size >= 1024:
        return f"{bytes_size / 1024:.2f} KB"
    return f"{bytes_size} B"

async def safe_edit_text(call: CallbackQuery, text: str, reply_markup=None):
    """ویرایش ایمن پیام"""
    try:
        await call.edit_message_text(
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.debug(f"Message edit failed: {e}")

@Client.on_callback_query(filters.regex(r'^yt_(dl_\d+|dl_audio|cancel)$'))
async def handle_quality_selection(client: Client, call: CallbackQuery):
    """Handler انتخاب کیفیت"""
    start_time = time.time()
    user_id = call.from_user.id
    data = call.data
    
    logger.info(f"Quality selection from user {user_id}: {data}")
    
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
        if data == 'yt_cancel':
            await call.edit_message_text("❌ دانلود لغو شد.")
            # Clean up cache
            if user_id in video_cache:
                del video_cache[user_id]
            return
        
        # Parse quality selection
        if data == 'yt_dl_audio':
            selected_quality = 'audio'
        else:
            # Extract quality (e.g., "yt_dl_360" -> "360")
            selected_quality = data.replace('yt_dl_', '')
        
        # Get quality info
        quality_info = video_info['qualities'].get(selected_quality)
        
        if not quality_info:
            await call.answer(
                "❌ کیفیت انتخابی در دسترس نیست.",
                show_alert=True
            )
            return
        
        # Check per-user concurrency
        if not reserve_user(user_id):
            await call.answer(
                "⚠️ شما در حال حاضر یک دانلود فعال دارید.\n"
                "لطفاً منتظر تکمیل آن بمانید.",
                show_alert=True
            )
            return
        
        user_reserved = True
        
        # Start download process
        await start_download(
            client=client,
            call=call,
            video_info=video_info,
            quality=selected_quality,
            quality_info=quality_info,
            user_id=user_id
        )
        
        elapsed = time.time() - start_time
        logger.info(f"Callback handled in {elapsed:.2f}s")
        
    except Exception as e:
        logger.error(f"Callback error: {e}")
        
        try:
            await call.edit_message_text(
                f"❌ **خطا در پردازش**\n\n"
                f"خطا: {str(e)[:100]}\n\n"
                f"لطفاً دوباره تلاش کنید.",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            await call.answer("❌ خطا در پردازش.", show_alert=True)
        
        # Release user reservation
        try:
            if 'user_reserved' in locals() and user_reserved:
                release_user(user_id)
        except:
            pass

async def start_download(
    client: Client,
    call: CallbackQuery,
    video_info: dict,
    quality: str,
    quality_info: dict,
    user_id: int
):
    """شروع فرآیند دانلود و آپلود"""
    slot_acquired = False
    downloaded_file = None
    
    try:
        # Display initial message
        quality_text = f"{quality}p" if quality != 'audio' else "فقط صدا"
        
        initial_msg = (
            f"🚀 **شروع دانلود**\n\n"
            f"🎬 {video_info['title'][:50]}...\n"
            f"📊 کیفیت: {quality_text}\n\n"
            f"⏳ در حال آماده‌سازی..."
        )
        
        await safe_edit_text(call, initial_msg)
        
        # Check queue status
        stats = get_queue_stats()
        if stats['active'] >= stats['capacity']:
            queue_position = stats['waiting'] + 1
            await safe_edit_text(
                call,
                initial_msg + f"\n\n🕒 در صف (نفر {queue_position})\n⏳ لطفاً صبر کنید..."
            )
        
        # Acquire download slot
        await acquire_slot()
        slot_acquired = True
        
        # Update message
        await safe_edit_text(
            call,
            f"📥 **در حال دانلود**\n\n"
            f"🎬 {video_info['title'][:50]}...\n"
            f"📊 کیفیت: {quality_text}\n\n"
            f"⏳ دانلود از یوتیوب..."
        )
        
        # Prepare filename
        safe_title = "".join(
            c for c in video_info['title'] 
            if c.isalnum() or c in (' ', '-', '_')
        ).strip()[:50]
        
        if quality == 'audio':
            filename = f"{safe_title}.{quality_info['ext']}"
            media_type = 'audio'
        else:
            filename = f"{safe_title}_{quality}p.mp4"
            media_type = 'video'
        
        # Progress tracking
        download_progress = {'current': 0, 'total': 0, 'last_update': 0}
        
        def download_progress_callback(current, total):
            """Callback برای نمایش پیشرفت دانلود"""
            download_progress['current'] = current
            download_progress['total'] = total
            
            now = time.time()
            if now - download_progress['last_update'] >= 3.0:  # Update every 3 seconds
                download_progress['last_update'] = now
                
                if total > 0:
                    percent = (current / total) * 100
                    progress_bar = "█" * int(percent / 5) + "░" * (20 - int(percent / 5))
                    
                    asyncio.create_task(safe_edit_text(
                        call,
                        f"📥 **در حال دانلود** {percent:.0f}%\n\n"
                        f"🎬 {video_info['title'][:50]}...\n"
                        f"📊 کیفیت: {quality_text}\n\n"
                        f"[{progress_bar}]\n"
                        f"📦 {format_size(current)} / {format_size(total)}"
                    ))
        
        # Download file
        download_start = time.time()
        downloaded_file = await youtube_downloader.download(
            url=video_info['url'],
            format_string=quality_info['format_string'],
            output_filename=filename,
            progress_callback=download_progress_callback
        )
        download_time = time.time() - download_start
        
        if not downloaded_file or not os.path.exists(downloaded_file):
            raise Exception("دانلود ناموفق بود")
        
        file_size = os.path.getsize(downloaded_file)
        logger.info(f"Download completed in {download_time:.2f}s - Size: {format_size(file_size)}")
        
        # Update message for upload
        await safe_edit_text(
            call,
            f"📤 **در حال آپلود**\n\n"
            f"🎬 {video_info['title'][:50]}...\n"
            f"📊 کیفیت: {quality_text}\n"
            f"💾 حجم: {format_size(file_size)}\n\n"
            f"⏳ آپلود به تلگرام..."
        )
        
        # Progress tracking for upload
        upload_progress = {'current': 0, 'total': 0, 'last_update': 0}
        
        async def upload_progress_callback(current, total):
            """Callback برای نمایش پیشرفت آپلود"""
            upload_progress['current'] = current
            upload_progress['total'] = total
            
            now = time.time()
            if now - upload_progress['last_update'] >= 3.0:  # Update every 3 seconds
                upload_progress['last_update'] = now
                
                if total > 0:
                    percent = (current / total) * 100
                    progress_bar = "█" * int(percent / 5) + "░" * (20 - int(percent / 5))
                    
                    await safe_edit_text(
                        call,
                        f"📤 **در حال آپلود** {percent:.0f}%\n\n"
                        f"🎬 {video_info['title'][:50]}...\n"
                        f"📊 کیفیت: {quality_text}\n"
                        f"💾 حجم: {format_size(file_size)}\n\n"
                        f"[{progress_bar}]\n"
                        f"📦 {format_size(current)} / {format_size(total)}"
                    )
        
        # Prepare caption
        caption = f"🎬 {video_info['title']}"
        
        # Upload file
        upload_start = time.time()
        success = await youtube_uploader.upload_with_streaming(
            client=client,
            chat_id=call.message.chat.id,
            file_path=downloaded_file,
            media_type=media_type,
            caption=caption,
            duration=video_info['duration'],
            title=video_info['title'],
            performer=video_info['uploader'],
            progress_callback=upload_progress_callback,
            reply_to_message_id=call.message.reply_to_message.message_id if call.message.reply_to_message else None
        )
        upload_time = time.time() - upload_start
        
        if not success:
            raise Exception("آپلود ناموفق بود")
        
        logger.info(f"Upload completed in {upload_time:.2f}s")
        
        # Delete progress message
        try:
            await call.message.delete()
        except:
            pass
        
        # Update database
        try:
            db = DB()
            db.increment_request(user_id, time.strftime('%Y-%m-%d %H:%M:%S'))
        except Exception as e:
            logger.warning(f"Database update error: {e}")
        
        # Clean up cache
        if user_id in video_cache:
            del video_cache[user_id]
        
        total_time = time.time() - download_start
        logger.info(f"Total process time: {total_time:.2f}s (Download: {download_time:.2f}s, Upload: {upload_time:.2f}s)")
        
    except Exception as e:
        logger.error(f"Download/Upload error: {e}")
        
        await safe_edit_text(
            call,
            f"❌ **خطا در دانلود/آپلود**\n\n"
            f"خطا: {str(e)}\n\n"
            f"لطفاً دوباره تلاش کنید."
        )
    
    finally:
        # Release slot
        if slot_acquired:
            try:
                release_slot()
            except:
                pass
        
        # Release user reservation
        try:
            release_user(user_id)
        except:
            pass
        
        # Clean up downloaded file
        if downloaded_file:
            try:
                youtube_downloader.cleanup(downloaded_file)
            except:
                pass
