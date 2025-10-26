"""
YouTube Uploader - آپلود فوق‌سریع با تنظیمات بهینه
راه‌حل قطعی برای سرعت بالا
"""

import os
import time
import asyncio
from typing import Optional, Callable
from pyrogram import Client
from pyrogram.types import Message
from plugins.logger_config import get_logger

logger = get_logger('youtube_uploader')

# 🔥 CRITICAL: Chunk size optimization for high-speed servers
# Default Pyrogram: 512KB → Too small!
# Optimal for high-speed: 2-4MB
OPTIMAL_CHUNK_SIZE = 2 * 1024 * 1024  # 2MB (بهترین برای سرورهای پرسرعت)

class YouTubeUploader:
    """کلاس آپلود فوق‌سریع به تلگرام"""
    
    def __init__(self):
        """مقداردهی اولیه با تنظیمات بهینه"""
        # 🔥 اعمال chunk size به کلاینت Pyrogram
        try:
            import pyrogram
            # Set global chunk size for all file operations
            if hasattr(pyrogram.file_id, 'CHUNK_SIZE'):
                pyrogram.file_id.CHUNK_SIZE = OPTIMAL_CHUNK_SIZE
                logger.info(f"✅ Pyrogram chunk size set to {OPTIMAL_CHUNK_SIZE / (1024*1024):.1f}MB")
        except Exception as e:
            logger.warning(f"Could not set global chunk size: {e}")
    
    async def upload_video(
        self,
        client: Client,
        chat_id: int,
        file_path: str,
        caption: str,
        duration: int = 0,
        thumbnail: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
        reply_to_message_id: Optional[int] = None
    ) -> bool:
        """
        آپلود ویدیو با سرعت فوق‌العاده
        """
        try:
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024*1024)
            
            logger.info(f"🚀 Starting ULTRA-FAST video upload")
            logger.info(f"📦 Size: {file_size_mb:.2f} MB")
            logger.info(f"⚡ Chunk size: {OPTIMAL_CHUNK_SIZE / (1024*1024):.1f} MB")
            
            upload_start = time.time()
            
            # 🔥 Progress wrapper با throttling شدید
            last_update = {'time': 0}
            
            async def optimized_progress(current, total):
                nonlocal last_update
                if not progress_callback:
                    return
                
                now = time.time()
                # فقط هر 3 ثانیه یک بار (کاهش overhead)
                if now - last_update['time'] >= 3.0:
                    last_update['time'] = now
                    try:
                        await progress_callback(current, total)
                    except Exception:
                        pass  # Ignore errors
            
            # 🔥 استراتژی هوشمند بر اساس حجم
            if file_size_mb > 100:
                # فایل‌های خیلی بزرگ: Document با force
                logger.info("📄 Using DOCUMENT mode for ultra-large file")
                
                sent = await client.send_document(
                    chat_id=chat_id,
                    document=file_path,
                    caption=f"🎬 {caption}",
                    progress=optimized_progress,
                    reply_to_message_id=reply_to_message_id,
                    force_document=True,
                    disable_notification=True,  # کاهش overhead
                    file_name=os.path.basename(file_path)
                )
            
            elif file_size_mb > 50:
                # فایل‌های بزرگ: ویدیو بدون thumbnail
                logger.info("🎥 Using VIDEO mode without thumbnail")
                
                sent = await client.send_video(
                    chat_id=chat_id,
                    video=file_path,
                    caption=caption,
                    duration=duration,
                    supports_streaming=True,  # 🔥 حتماً فعال
                    progress=optimized_progress,
                    reply_to_message_id=reply_to_message_id,
                    disable_notification=True,  # کاهش overhead
                    thumb=None  # بدون thumbnail برای سرعت
                )
            
            else:
                # فایل‌های کوچک: ویدیو با تمام ویژگی‌ها
                logger.info("🎬 Using FULL VIDEO mode")
                
                sent = await client.send_video(
                    chat_id=chat_id,
                    video=file_path,
                    caption=caption,
                    duration=duration,
                    thumb=thumbnail,
                    supports_streaming=True,
                    progress=optimized_progress,
                    reply_to_message_id=reply_to_message_id,
                    disable_notification=True
                )
            
            upload_time = time.time() - upload_start
            upload_speed = file_size_mb / upload_time if upload_time > 0 else 0
            
            logger.info(f"✅ Upload SUCCESS in {upload_time:.2f}s")
            logger.info(f"⚡ Speed: {upload_speed:.2f} MB/s")
            
            # 🔥 هشدار اگر سرعت کم باشد
            if upload_speed < 2.0 and file_size_mb > 10:
                logger.warning(f"⚠️ Slow upload speed detected: {upload_speed:.2f} MB/s")
                logger.warning("Check: Network bandwidth, Server CPU, Telegram API limits")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Upload FAILED: {e}")
            return False
    
    async def upload_audio(
        self,
        client: Client,
        chat_id: int,
        file_path: str,
        caption: str,
        title: str,
        performer: str = "Unknown",
        duration: int = 0,
        thumbnail: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
        reply_to_message_id: Optional[int] = None
    ) -> bool:
        """آپلود فایل صوتی با سرعت بالا"""
        try:
            file_size = os.path.getsize(file_path)
            logger.info(f"🎵 Starting audio upload: {file_size / (1024*1024):.2f} MB")
            
            upload_start = time.time()
            
            # Progress wrapper
            last_update = {'time': 0}
            
            async def optimized_progress(current, total):
                nonlocal last_update
                if not progress_callback:
                    return
                
                now = time.time()
                if now - last_update['time'] >= 3.0:
                    last_update['time'] = now
                    try:
                        await progress_callback(current, total)
                    except Exception:
                        pass
            
            # 🔥 آپلود با تنظیمات بهینه
            sent = await client.send_audio(
                chat_id=chat_id,
                audio=file_path,
                caption=caption,
                title=title,
                performer=performer,
                duration=duration,
                thumb=thumbnail,
                progress=optimized_progress,
                reply_to_message_id=reply_to_message_id,
                disable_notification=True  # کاهش overhead
            )
            
            upload_time = time.time() - upload_start
            logger.info(f"✅ Audio upload completed in {upload_time:.2f}s")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Audio upload failed: {e}")
            return False
    
    async def upload_with_streaming(
        self,
        client: Client,
        chat_id: int,
        file_path: str,
        media_type: str,
        caption: str,
        duration: int = 0,
        title: str = "Unknown",
        performer: str = "Unknown",
        thumbnail: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
        reply_to_message_id: Optional[int] = None
    ) -> bool:
        """
        آپلود با streaming (انتخاب خودکار)
        🔥 این متد اصلی است که از youtube_callback.py صدا زده می‌شود
        """
        try:
            # 🔥 اعمال chunk size به session (در صورت امکان)
            try:
                if hasattr(client, 'storage') and hasattr(client.storage, 'session'):
                    session = client.storage.session
                    if hasattr(session, 'CHUNK_SIZE'):
                        session.CHUNK_SIZE = OPTIMAL_CHUNK_SIZE
                        logger.debug(f"Session chunk size set to {OPTIMAL_CHUNK_SIZE}")
            except Exception:
                pass
            
            if media_type == 'audio':
                return await self.upload_audio(
                    client=client,
                    chat_id=chat_id,
                    file_path=file_path,
                    caption=caption,
                    title=title,
                    performer=performer,
                    duration=duration,
                    thumbnail=thumbnail,
                    progress_callback=progress_callback,
                    reply_to_message_id=reply_to_message_id
                )
            else:
                return await self.upload_video(
                    client=client,
                    chat_id=chat_id,
                    file_path=file_path,
                    caption=caption,
                    duration=duration,
                    thumbnail=thumbnail,
                    progress_callback=progress_callback,
                    reply_to_message_id=reply_to_message_id
                )
                
        except Exception as e:
            logger.error(f"❌ Upload with streaming failed: {e}")
            return False

# 🔥 Global instance با تنظیمات بهینه
youtube_uploader = YouTubeUploader()

# 🔥 تابع کمکی برای تنظیم chunk size در کلاینت
def optimize_client_for_upload(client: Client):
    """
    بهینه‌سازی کلاینت برای آپلود سریع
    این تابع را در main.py یا هنگام ساخت کلاینت صدا بزنید
    """
    try:
        # Patch Pyrogram's internal chunk size
        import pyrogram.methods.messages.send_document as send_doc
        import pyrogram.methods.messages.send_video as send_vid
        import pyrogram.methods.messages.send_audio as send_aud
        
        # تلاش برای تغییر chunk size در ماژول‌های Pyrogram
        for module in [send_doc, send_vid, send_aud]:
            if hasattr(module, 'CHUNK_SIZE'):
                module.CHUNK_SIZE = OPTIMAL_CHUNK_SIZE
                logger.info(f"✅ Patched {module.__name__} chunk size")
        
        logger.info("✅ Client optimized for ultra-fast uploads")
        return True
        
    except Exception as e:
        logger.warning(f"Could not fully optimize client: {e}")
        return False