"""
YouTube Callback Handler - نسخه فوق بهینه شده
تغییرات:
- کاهش update های پیام (overhead کمتر)
- حذف progress callback برای دانلود (سرعت بیشتر)
- بهینه‌سازی memory
"""

import os
import time
import asyncio
import json
import html
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from pyrogram.enums import ParseMode
from pyrogram.errors import MessageNotModified, MessageDeleteForbidden, FloodWait
from plugins.logger_config import get_logger
from plugins.youtube_handler import video_cache
from plugins.youtube_downloader import youtube_downloader
from plugins.youtube_uploader import youtube_uploader
from plugins.concurrency import acquire_slot, release_slot, get_queue_stats, reserve_user, release_user
from plugins.sqlite_db_wrapper import DB
from plugins.media_utils import send_advertisement

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
    """ویرایش ایمن پیام - با مدیریت FloodWait"""
    max_retries = 2
    for attempt in range(max_retries):
        try:
            await call.edit_message_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return
        except FloodWait as fw:
            # ✅ مدیریت rate limit
            if attempt < max_retries - 1:
                logger.warning(f"FloodWait: sleeping {fw.value}s")
                await asyncio.sleep(fw.value)
            else:
                logger.error(f"FloodWait exceeded max retries")
        except (MessageNotModified, MessageDeleteForbidden) as e:
            # ✅ مدیریت خطاهای خاص پیام
            logger.debug(f"Message edit skipped: {e}")
            return
        except Exception as e:
            logger.debug(f"Message edit failed: {e}")
            return

@Client.on_callback_query(filters.regex(r'^yt_(dl_\d+|dl_audio|cancel)$'))
async def handle_quality_selection(client: Client, call: CallbackQuery):
    """Handler انتخاب کیفیت"""
    start_time = time.time()
    user_id = call.from_user.id
    data = call.data
    
    # ✅ مقداردهی اولیه متغیرها برای جلوگیری از UnboundLocalError
    user_reserved = False
    
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
            if user_id in video_cache:
                del video_cache[user_id]
            return
        
        # Parse quality selection
        if data == 'yt_dl_audio':
            selected_quality = 'audio'
        else:
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
    
    finally:
        # ✅ آزادسازی user در finally برای اطمینان از آزادسازی در هر شرایطی
        if user_reserved:
            try:
                release_user(user_id)
            except Exception as release_error:
                logger.warning(f"Failed to release user {user_id}: {release_error}")

async def start_download(
    client: Client,
    call: CallbackQuery,
    video_info: dict,
    quality: str,
    quality_info: dict,
    user_id: int
):
    """شروع فرآیند دانلود و آپلود - نسخه بهینه شده"""
    # ✅ مقداردهی اولیه متغیرها
    slot_acquired = False
    downloaded_file = None
    thumbnail_path = None
    overall_start = time.time()  # ✅ زمان شروع کلی
    
    try:
        quality_text = f"{quality}p" if quality != 'audio' else "فقط صدا"
        
        # ✅ Escape کردن عنوان برای Markdown
        safe_title = html.escape(video_info['title'][:50])
        
        # پیام اولیه
        initial_msg = (
            f"🚀 **شروع دانلود**\n\n"
            f"🎬 {safe_title}...\n"
            f"📊 کیفیت: {quality_text}\n\n"
            f"⏳ در حال آماده‌سازی..."
        )
        
        await safe_edit_text(call, initial_msg)
        
        # Check queue
        stats = get_queue_stats()
        if stats['active'] >= stats['capacity']:
            queue_position = stats['waiting'] + 1
            await safe_edit_text(
                call,
                initial_msg + f"\n\n🕐 در صف (نفر {queue_position})\n⏳ لطفاً صبر کنید..."
            )
        
        # ✅ Acquire slot با try/except
        try:
            await acquire_slot()
            slot_acquired = True
        except Exception as e:
            logger.error(f"Slot acquire failed: {e}")
            raise
        
        # 🔥 پیام ساده بدون progress برای دانلود
        await safe_edit_text(
            call,
            f"📥 **در حال دانلود**\n\n"
            f"🎬 {safe_title}...\n"
            f"📊 کیفیت: {quality_text}\n\n"
            f"⏳ دانلود از یوتیوب در حال انجام است...\n"
            f"💡 این مرحله ممکن است 1-2 دقیقه طول بکشد ⌛"
        )
        
        # Prepare filename (کوتاه و ساده برای جلوگیری از ارسال به عنوان document)
        safe_title = "".join(
            c for c in video_info['title'] 
            if c.isalnum() or c in (' ', '-', '_')
        ).strip()
        
        # محدود کردن طول نام فایل برای جلوگیری از مشکل Telegram
        max_title_length = 30  # کاهش از 50 به 30
        if len(safe_title) > max_title_length:
            safe_title = safe_title[:max_title_length].strip()
        
        # اگر نام خیلی کوتاه شد، از نام پیش‌فرض استفاده کن
        if len(safe_title) < 5:
            safe_title = "YouTube_Video"
        
        if quality == 'audio':
            # ✅ پیش‌فرض برای ext در صورت نبود
            ext = quality_info.get('ext', 'mp3')
            filename = f"{safe_title}.{ext}"
            media_type = 'audio'
        else:
            filename = f"{safe_title}_{quality}p.mp4"
            media_type = 'video'
        
        # ✅ لاگ کامل‌تر برای دیباگ
        logger.info(f"📁 Generated filename: {filename} (temp dir: {youtube_downloader.download_dir})")
        
        # 🔥 دانلود بدون progress callback (سرعت بیشتر)
        download_start = time.time()
        downloaded_file = await youtube_downloader.download(
            url=video_info['url'],
            format_string=quality_info['format_string'],
            output_filename=filename,
            progress_callback=None,  # بدون callback برای سرعت بیشتر
            is_audio_only=(quality == 'audio')  # مشخص کردن نوع فایل
        )
        download_time = time.time() - download_start
        
        if not downloaded_file or not os.path.exists(downloaded_file):
            raise Exception("دانلود ناموفق بود")
        
        file_size = os.path.getsize(downloaded_file)
        logger.info(f"✅ Download: {download_time:.2f}s - {format_size(file_size)}")
        
        # پیام آپلود
        await safe_edit_text(
            call,
            f"📤 **در حال آپلود**\n\n"
            f"🎬 {safe_title}...\n"
            f"📊 کیفیت: {quality_text}\n"
            f"💾 حجم: {format_size(file_size)}\n\n"
            f"⏳ آپلود به تلگرام..."
        )
        
        # 🔥 Progress callback بهینه شده - فقط برای فایل‌های بزرگ
        upload_progress = {'last_update': 0}
        
        async def optimized_upload_progress(current, total):
            """Progress با حداقل overhead"""
            now = time.time()
            
            # فقط هر 5 ثانیه یک بار و فقط برای فایل‌های > 20MB
            if file_size > 20 * 1024 * 1024 and now - upload_progress['last_update'] >= 5.0:
                upload_progress['last_update'] = now
                percent = (current / total) * 100
                
                # پیام خیلی ساده
                await safe_edit_text(
                    call,
                    f"📤 **آپلود** {percent:.0f}%\n\n"
                    f"💾 {format_size(current)} / {format_size(total)}"
                )
        
        # Download thumbnail (برای همه ویدیوها)
        if media_type == 'video' and video_info.get('thumbnail'):
            try:
                from plugins.youtube_handler import download_thumbnail
                thumbnail_path = await download_thumbnail(video_info['thumbnail'])
                if thumbnail_path and os.path.exists(thumbnail_path):
                    logger.info(f"✅ Thumbnail downloaded: {thumbnail_path}")
                else:
                    logger.warning("❌ Thumbnail download failed: file not found")
                    thumbnail_path = None
            except Exception as e:
                logger.warning(f"❌ Thumbnail download failed: {e}")
                thumbnail_path = None
        
        # ✅ Caption با escape کردن عنوان
        caption = f"🎬 {html.escape(video_info['title'])}"
        
        # Check advertisement settings
        ad_enabled = False
        ad_position = 'after'  # default
        try:
            from plugins.db_path_manager import db_path_manager
            json_db_path = db_path_manager.get_json_db_path()
            
            with open(json_db_path, 'r', encoding='utf-8') as f:
                db_data = json.load(f)
            ad_settings = db_data.get('advertisement', {})
            ad_enabled = ad_settings.get('enabled', False)
            ad_position = ad_settings.get('position', 'after')
            logger.info(f"Advertisement settings: enabled={ad_enabled}, position={ad_position}")
        except Exception as e:
            logger.warning(f"Failed to load advertisement settings: {e}")
        
        # ✅ Send advertisement before content با try/except
        if ad_enabled and ad_position == 'before':
            try:
                logger.info("Sending advertisement before YouTube content")
                send_advertisement(client, call.message.chat.id)
            except Exception as e:
                logger.warning(f"Advertisement send failed (before): {e}")
        
        # 🔥 آپلود با تنظیمات بهینه
        # ✅ بررسی امن reply_to_message
        reply_to_id = None
        if call.message and call.message.reply_to_message:
            reply_to_id = call.message.reply_to_message.message_id
        
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
            thumbnail=thumbnail_path,
            progress_callback=optimized_upload_progress,  # Progress بهینه شده
            reply_to_message_id=reply_to_id  # ✅ استفاده از متغیر امن
        )
        upload_time = time.time() - upload_start
        
        if not success:
            raise Exception("آپلود ناموفق بود")
        
        logger.info(f"✅ Upload: {upload_time:.2f}s")
        
        # ✅ حذف ایمن پیام progress با FloodWait
        logger.debug("Deleting progress message...")
        try:
            if call.message:
                await call.message.delete()
                logger.debug("Progress message deleted")
        except FloodWait as fw:
            logger.warning(f"FloodWait on delete: {fw.value}s - skipping")
        except (MessageNotModified, MessageDeleteForbidden) as e:
            logger.debug(f"Message delete skipped: {e}")
        except Exception as e:
            logger.warning(f"Failed to delete progress message: {e}")
        
        # ✅ Send advertisement after content با try/except
        if ad_enabled and ad_position == 'after':
            try:
                logger.info("Sending advertisement after YouTube content")
                send_advertisement(client, call.message.chat.id)
                logger.debug("Advertisement sent")
            except Exception as e:
                logger.warning(f"Advertisement send failed (after): {e}")
        
        # Update database
        logger.debug("Updating database...")
        try:
            db = DB()
            db.increment_request(user_id, time.strftime('%Y-%m-%d %H:%M:%S'))
            logger.debug("Database updated")
        except Exception as e:
            logger.warning(f"Database update error: {e}")
        
        # Clean up cache
        if user_id in video_cache:
            del video_cache[user_id]
        
        # ✅ محاسبه زمان کلی از overall_start
        total_time = time.time() - overall_start
        logger.info(f"🎯 Total: {total_time:.2f}s (DL: {download_time:.2f}s, UL: {upload_time:.2f}s)")
        
    except Exception as e:
        logger.error(f"Download/Upload error: {e}")
        
        await safe_edit_text(
            call,
            f"❌ **خطا در دانلود/آپلود**\n\n"
            f"خطا: {str(e)}\n\n"
            f"لطفاً دوباره تلاش کنید."
        )
    
    finally:
        # ✅ Release slot با بررسی
        if slot_acquired:
            try:
                release_slot()
                logger.debug("Slot released")
            except Exception as e:
                logger.warning(f"Failed to release slot: {e}")
        
        # ✅ Release user (این کار در handler اصلی انجام می‌شود)
        # توجه: release_user در finally بلوک handle_quality_selection فراخوانی می‌شود
        
        # ✅ Clean up files با بررسی امن و وجود فایل
        if downloaded_file and os.path.exists(downloaded_file):
            try:
                youtube_downloader.cleanup(downloaded_file)
                logger.debug(f"Cleaned up downloaded file: {downloaded_file}")
            except Exception as e:
                logger.warning(f"Failed to cleanup downloaded file: {e}")
        
        # ✅ پاک‌سازی thumbnail با try/except
        if thumbnail_path:
            try:
                if os.path.exists(thumbnail_path):
                    os.unlink(thumbnail_path)
                    logger.debug(f"Cleaned up thumbnail: {thumbnail_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup thumbnail: {e}")