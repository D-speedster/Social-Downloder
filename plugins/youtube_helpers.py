import os
import asyncio
import tempfile
import yt_dlp
from plugins.logger_config import get_logger
from plugins.cookie_manager import get_rotated_cookie_file, mark_cookie_used

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
            'extractor_args': {
                'youtube': {
                    'player_client': ['android']
                }
            },
        }
        
        # Add progress hook if provided
        if progress_hook:
            ydl_opts['progress_hooks'] = [progress_hook]
        
        # تلاش برای استفاده از کوکی چرخشی در دانلود
        cookie_id_used = None
        try:
            cookiefile, cid = get_rotated_cookie_file(None)
            if cookiefile:
                ydl_opts['cookiefile'] = cookiefile
                cookie_id_used = cid
                youtube_helpers_logger.debug(f"استفاده از کوکی چرخشی برای دانلود: id={cid}, path={cookiefile}")
            else:
                youtube_helpers_logger.debug("کوکی چرخشی دردسترس نیست؛ دانلود بدون کوکی")
        except Exception as e:
            youtube_helpers_logger.debug(f"دسترسی به کوکی چرخشی با خطا مواجه شد: {e}")

        # Download in thread to avoid blocking
        def download_sync():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        
        await asyncio.to_thread(download_sync)
        
        # ثبت موفقیت استفاده از کوکی
        if cookie_id_used:
            try:
                mark_cookie_used(cookie_id_used, True)
            except Exception:
                pass
        
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
        # ثبت شکست استفاده از کوکی
        try:
            if 'cookie_id_used' in locals() and cookie_id_used:
                mark_cookie_used(cookie_id_used, False)
        except Exception:
            pass
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
            'extractor_args': {
                'youtube': {
                    'player_client': ['android']
                }
            },
        }
        
        # تلاش برای استفاده از کوکی چرخشی در استخراج لینک
        cookie_id_used = None
        try:
            cookiefile, cid = get_rotated_cookie_file(None)
            if cookiefile:
                ydl_opts['cookiefile'] = cookiefile
                cookie_id_used = cid
                youtube_helpers_logger.debug(f"استفاده از کوکی چرخشی برای استخراج لینک: id={cid}, path={cookiefile}")
            else:
                youtube_helpers_logger.debug("کوکی چرخشی دردسترس نیست؛ استخراج لینک بدون کوکی")
        except Exception as e:
            youtube_helpers_logger.debug(f"دسترسی به کوکی چرخشی با خطا مواجه شد: {e}")
        
        # Extract info in thread to avoid blocking
        def extract_sync():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        
        info = await asyncio.to_thread(extract_sync)
        # ثبت موفقیت استفاده از کوکی
        if cookie_id_used:
            try:
                mark_cookie_used(cookie_id_used, True)
            except Exception:
                pass
        return info
    except Exception as e:
        youtube_helpers_logger.error(f"خطا در دریافت لینک مستقیم: {e}")
        try:
            if 'cookie_id_used' in locals() and cookie_id_used:
                mark_cookie_used(cookie_id_used, False)
        except Exception:
            pass
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