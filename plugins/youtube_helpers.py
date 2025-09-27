import os
import asyncio
import tempfile
import yt_dlp
from plugins.logger_config import get_logger

# Initialize logger
youtube_helpers_logger = get_logger('youtube_helpers')

async def download_youtube_file(url, format_id, progress_hook=None):
    """
    دانلود فایل یوتیوب با format_id مشخص
    """
    try:
        youtube_helpers_logger.info(f"شروع دانلود: {url} با فرمت {format_id}")
        
        # Create temporary directory for download
        temp_dir = tempfile.mkdtemp()
        youtube_helpers_logger.debug(f"دایرکتوری موقت ایجاد شد: {temp_dir}")
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': format_id,
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'extract_flat': False,
        }
        
        # Add progress hook if provided
        if progress_hook:
            ydl_opts['progress_hooks'] = [progress_hook]
        
        # Add cookies if available
        cookie_path = os.path.join(os.getcwd(), 'cookies', 'youtube.txt')
        if os.path.exists(cookie_path):
            ydl_opts['cookiefile'] = cookie_path
            youtube_helpers_logger.debug(f"استفاده از کوکی: {cookie_path}")
        
        # Download in thread to avoid blocking
        def download_sync():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        
        await asyncio.to_thread(download_sync)
        
        # Find downloaded file
        downloaded_files = [f for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
        if not downloaded_files:
            youtube_helpers_logger.error("هیچ فایل دانلود شده‌ای یافت نشد")
            return None
        
        downloaded_file = os.path.join(temp_dir, downloaded_files[0])
        youtube_helpers_logger.info(f"دانلود موفق: {downloaded_file}")
        
        return downloaded_file
        
    except Exception as e:
        youtube_helpers_logger.error(f"خطا در دانلود: {e}")
        return None

async def get_direct_download_url(url, format_id):
    """
    دریافت لینک مستقیم دانلود بدون دانلود فایل
    """
    try:
        youtube_helpers_logger.info(f"دریافت لینک مستقیم: {url} با فرمت {format_id}")
        
        # Configure yt-dlp options for URL extraction only
        ydl_opts = {
            'format': format_id,
            'quiet': True,
            'simulate': True,
            'noplaylist': True,
            'extract_flat': False,
        }
        
        # Add cookies if available
        cookie_path = os.path.join(os.getcwd(), 'cookies', 'youtube.txt')
        if os.path.exists(cookie_path):
            ydl_opts['cookiefile'] = cookie_path
            youtube_helpers_logger.debug(f"استفاده از کوکی: {cookie_path}")
        
        # Extract info in thread to avoid blocking
        def extract_sync():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        
        info = await asyncio.to_thread(extract_sync)
        
        # Find the format with matching format_id
        if 'formats' in info:
            for fmt in info['formats']:
                if fmt.get('format_id') == format_id:
                    direct_url = fmt.get('url')
                    if direct_url:
                        youtube_helpers_logger.info("لینک مستقیم با موفقیت دریافت شد")
                        return direct_url
        
        youtube_helpers_logger.warning("لینک مستقیم یافت نشد")
        return None
        
    except Exception as e:
        youtube_helpers_logger.error(f"خطا در دریافت لینک مستقیم: {e}")
        return None

async def safe_edit_text(message, text, parse_mode=None, reply_markup=None):
    """
    ویرایش ایمن متن پیام
    """
    try:
        await message.edit_text(
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )
    except Exception as e:
        youtube_helpers_logger.error(f"خطا در ویرایش پیام: {e}")