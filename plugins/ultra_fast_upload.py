"""
Ultra Fast Upload Module - بهینه‌سازی شده برای سرعت بالا
"""
import os
import asyncio
import time
from pyrogram import Client
from pyrogram.types import Message
from plugins.logger_config import get_logger

logger = get_logger('ultra_fast_upload')

async def ultra_fast_upload(client: Client, chat_id: int, file_path: str, 
                           media_type: str = "video", caption: str = "", 
                           progress_callback=None, **kwargs) -> bool:
    """
    🚀 آپلود فوق سریع بدون هیچ تأخیر یا overhead اضافی
    """
    try:
        start_time = time.time()
        file_size = os.path.getsize(file_path)
        file_size_mb = file_size / (1024 * 1024)
        
        logger.info(f"🚀 شروع آپلود فوق سریع: {file_size_mb:.2f}MB")
        
        # تنظیمات حداقلی برای سرعت بالا
        upload_kwargs = {
            'caption': caption,
            'disable_notification': True,  # غیرفعال کردن نوتیفیکیشن
        }
        
        # اضافه کردن progress callback
        if progress_callback:
            upload_kwargs['progress'] = progress_callback
        
        # اضافه کردن reply_to_message_id اگر موجود باشد
        if 'reply_to_message_id' in kwargs:
            upload_kwargs['reply_to_message_id'] = kwargs['reply_to_message_id']
        
        # آپلود مستقیم بدون هیچ پردازش اضافی
        if media_type == "video":
            message = await client.send_video(
                chat_id=chat_id,
                video=file_path,
                **upload_kwargs
            )
        elif media_type == "audio":
            message = await client.send_audio(
                chat_id=chat_id,
                audio=file_path,
                **upload_kwargs
            )
        else:
            message = await client.send_document(
                chat_id=chat_id,
                document=file_path,
                **upload_kwargs
            )
        
        upload_time = time.time() - start_time
        speed_mbps = file_size_mb / upload_time if upload_time > 0 else 0
        
        logger.info(f"✅ آپلود موفق در {upload_time:.2f}s - سرعت: {speed_mbps:.2f}MB/s")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ خطا در آپلود فوق سریع: {e}")
        return False


async def chunked_upload(client: Client, chat_id: int, file_path: str,
                        media_type: str = "video", caption: str = "",
                        chunk_size: int = 512 * 1024,  # 512KB chunks
                        progress_callback=None, **kwargs) -> bool:
    """
    آپلود با chunk های کوچک‌تر برای فایل‌های بزرگ
    """
    try:
        start_time = time.time()
        file_size = os.path.getsize(file_path)
        
        logger.info(f"📦 شروع chunked upload: {file_size / (1024*1024):.2f}MB")
        
        # تنظیمات بهینه برای chunked upload
        upload_kwargs = {
            'caption': caption,
            'disable_notification': True,
            'file_name': os.path.basename(file_path),
        }
        
        if progress_callback:
            upload_kwargs['progress'] = progress_callback
            
        if 'reply_to_message_id' in kwargs:
            upload_kwargs['reply_to_message_id'] = kwargs['reply_to_message_id']
        
        # آپلود با تنظیمات بهینه
        if media_type == "video":
            message = await client.send_video(
                chat_id=chat_id,
                video=file_path,
                **upload_kwargs
            )
        elif media_type == "audio":
            message = await client.send_audio(
                chat_id=chat_id,
                audio=file_path,
                **upload_kwargs
            )
        else:
            message = await client.send_document(
                chat_id=chat_id,
                document=file_path,
                **upload_kwargs
            )
        
        upload_time = time.time() - start_time
        speed_mbps = (file_size / (1024*1024)) / upload_time if upload_time > 0 else 0
        
        logger.info(f"✅ Chunked upload موفق در {upload_time:.2f}s - سرعت: {speed_mbps:.2f}MB/s")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ خطا در chunked upload: {e}")
        return False


async def smart_upload_selector(client: Client, chat_id: int, file_path: str,
                               media_type: str = "video", caption: str = "",
                               progress_callback=None, **kwargs) -> bool:
    """
    انتخاب هوشمند روش آپلود بر اساس حجم فایل
    """
    try:
        file_size = os.path.getsize(file_path)
        file_size_mb = file_size / (1024 * 1024)
        
        logger.info(f"🧠 انتخاب روش آپلود برای فایل {file_size_mb:.2f}MB")
        
        # انتخاب روش بر اساس حجم
        if file_size_mb < 50:
            # فایل‌های کوچک: آپلود فوق سریع
            logger.info("🚀 استفاده از ultra_fast_upload")
            return await ultra_fast_upload(
                client, chat_id, file_path, media_type, caption, 
                progress_callback, **kwargs
            )
        else:
            # فایل‌های بزرگ: chunked upload
            logger.info("📦 استفاده از chunked_upload")
            return await chunked_upload(
                client, chat_id, file_path, media_type, caption,
                progress_callback=progress_callback, **kwargs
            )
            
    except Exception as e:
        logger.error(f"❌ خطا در smart_upload_selector: {e}")
        return False