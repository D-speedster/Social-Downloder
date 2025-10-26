"""
YouTube Uploader - آپلود بهینه با streaming و chunking
استفاده از تکنیک‌های پیشرفته برای سرعت بالا
"""

import os
import asyncio
from typing import Optional, Callable
from pyrogram import Client
from pyrogram.types import Message
from plugins.logger_config import get_logger

logger = get_logger('youtube_uploader')

# Optimal chunk size for Telegram (512KB - 1MB works best)
CHUNK_SIZE = 524288  # 512KB

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
            logger.info(f"File size: {file_size / (1024*1024):.2f} MB")
            
            # Wrapper for progress callback
            async def progress_wrapper(current, total):
                if progress_callback:
                    try:
                        await progress_callback(current, total)
                    except Exception as e:
                        logger.debug(f"Progress callback error: {e}")
            
            # Upload video
            await client.send_video(
                chat_id=chat_id,
                video=file_path,
                caption=caption,
                duration=duration,
                thumb=thumbnail,
                supports_streaming=True,
                progress=progress_wrapper,
                reply_to_message_id=reply_to_message_id
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
