"""
YouTube Uploader - آپلود بهینه با streaming و chunking
استفاده از تکنیک‌های پیشرفته برای سرعت بالا
"""

import os
import time
import asyncio
from typing import Optional, Callable
from pyrogram import Client
from pyrogram.types import Message
from plugins.logger_config import get_logger

logger = get_logger('youtube_uploader')

# Optimal chunk size for high-speed servers (larger chunks for better throughput)
CHUNK_SIZE = 1048576  # 1MB for high-speed connections

class YouTubeUploader:
    """کلاس آپلود بهینه به تلگرام"""
    
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
        آپلود ویدیو با بهینه‌سازی
        
        Args:
            client: کلاینت Pyrogram
            chat_id: شناسه چت
            file_path: مسیر فایل
            caption: کپشن
            duration: مدت زمان ویدیو
            thumbnail: مسیر thumbnail
            progress_callback: تابع callback برای پیشرفت
            reply_to_message_id: پاسخ به پیام
        
        Returns:
            True در صورت موفقیت
        """
        try:
            logger.info(f"Starting video upload: {file_path}")
            
            # Get file size
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024*1024)
            logger.info(f"File size: {file_size_mb:.2f} MB")
            
            # Optimize progress callback frequency for large files
            progress_update_interval = 2.0 if file_size_mb > 100 else 1.0
            last_progress_time = 0
            
            # Wrapper for progress callback with throttling
            async def progress_wrapper(current, total):
                nonlocal last_progress_time
                if progress_callback:
                    try:
                        current_time = time.time()
                        if current_time - last_progress_time >= progress_update_interval:
                            last_progress_time = current_time
                            await progress_callback(current, total)
                    except Exception as e:
                        logger.debug(f"Progress callback error: {e}")
            
            # Try ultra-fast upload for large files
            if file_size_mb > 50:
                logger.info("Using ultra-fast upload method for large file")
                try:
                    # Use document upload for faster speed on large files
                    await client.send_document(
                        chat_id=chat_id,
                        document=file_path,
                        caption=f"🎬 {caption}\n\n📹 ویدیو (آپلود سریع)",
                        progress=progress_wrapper,
                        reply_to_message_id=reply_to_message_id,
                        force_document=True
                    )
                    logger.info("Ultra-fast document upload completed")
                    return True
                except Exception as e:
                    logger.warning(f"Ultra-fast upload failed, falling back to video: {e}")
            
            # Standard video upload with optimized settings
            await client.send_video(
                chat_id=chat_id,
                video=file_path,
                caption=caption,
                duration=duration,
                thumb=thumbnail,
                supports_streaming=True,
                progress=progress_wrapper,
                reply_to_message_id=reply_to_message_id,
                # Optimizations for speed
                disable_notification=False,
                parse_mode=None
            )
            
            logger.info("Video upload completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Video upload error: {e}")
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
        """
        آپلود فایل صوتی
        
        Args:
            client: کلاینت Pyrogram
            chat_id: شناسه چت
            file_path: مسیر فایل
            caption: کپشن
            title: عنوان
            performer: هنرمند
            duration: مدت زمان
            thumbnail: مسیر thumbnail
            progress_callback: تابع callback برای پیشرفت
            reply_to_message_id: پاسخ به پیام
        
        Returns:
            True در صورت موفقیت
        """
        try:
            logger.info(f"Starting audio upload: {file_path}")
            
            # Get file size
            file_size = os.path.getsize(file_path)
            logger.info(f"File size: {file_size / (1024*1024):.2f} MB")
            
            # Wrapper for progress callback
            async def progress_wrapper(current, total):
                if progress_callback:
                    try:
                        await progress_callback(current, total)
                    except Exception as e:
                        logger.debug(f"Progress callback error: {e}")
            
            # Upload audio
            await client.send_audio(
                chat_id=chat_id,
                audio=file_path,
                caption=caption,
                title=title,
                performer=performer,
                duration=duration,
                thumb=thumbnail,
                progress=progress_wrapper,
                reply_to_message_id=reply_to_message_id
            )
            
            logger.info("Audio upload completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Audio upload error: {e}")
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
        آپلود با streaming (انتخاب خودکار بین ویدیو و صوت)
        
        Args:
            client: کلاینت Pyrogram
            chat_id: شناسه چت
            file_path: مسیر فایل
            media_type: نوع مدیا ('video' یا 'audio')
            caption: کپشن
            duration: مدت زمان
            title: عنوان
            performer: هنرمند
            thumbnail: مسیر thumbnail
            progress_callback: تابع callback برای پیشرفت
            reply_to_message_id: پاسخ به پیام
        
        Returns:
            True در صورت موفقیت
        """
        try:
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
            logger.error(f"Upload with streaming error: {e}")
            return False

# Global instance
youtube_uploader = YouTubeUploader()
