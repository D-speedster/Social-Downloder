import os
import asyncio
import tempfile
import yt_dlp
from plugins.logger_config import get_logger
from plugins.cookie_manager import get_rotated_cookie_file, mark_cookie_used, get_cookie_file_with_fallback

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
        
        # Configure yt-dlp options with proxy
        ydl_opts = {
            'format': format_id,
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'extract_flat': False,
            'proxy': 'socks5h://127.0.0.1:1084',
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios']
                }
            },
        }
        
        # Add progress hook if provided
        if progress_hook:
            ydl_opts['progress_hooks'] = [progress_hook]
        
        cookie_id_used = None

        # همیشه ابتدا سعی کن از فایل کوکی اصلی استفاده کنی
        try:
            cookiefile, cid = get_cookie_file_with_fallback(None)
            if cookiefile:
                ydl_opts['cookiefile'] = cookiefile
                cookie_id_used = cid
                if cid == -1:
                    youtube_helpers_logger.info("استفاده از کوکی اصلی cookie_youtube.txt")
                else:
                    youtube_helpers_logger.debug(f"استفاده از کوکی استخر: id={cid}, path={cookiefile}")
        except Exception:
            pass

        # Initial attempt: direct download
        try:
            def download_sync():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            await asyncio.to_thread(download_sync)
        except Exception as first_err:
            # اگر نیاز به کوکی باشد، تلاش مجدد با کوکی
            msg = str(first_err).lower()
            needs_cookie = any(h in msg for h in ['login required', 'sign in', 'age', 'restricted', 'private'])
            if needs_cookie:
                try:
                    # اگر قبلاً کوکی استفاده نشده، سعی کن از فایل اصلی یا استخر استفاده کنی
                    if not cookie_id_used:
                        cookiefile, cid = get_cookie_file_with_fallback(None)
                    else:
                        # اگر قبلاً کوکی استفاده شده، از استخر کوکی دیگری بگیر
                        cookiefile, cid = get_rotated_cookie_file(cookie_id_used)
                    
                    if cookiefile:
                        ydl_opts['cookiefile'] = cookiefile
                        cookie_id_used = cid
                        if cid == -1:
                            youtube_helpers_logger.info("تلاش مجدد با کوکی اصلی cookie_youtube.txt")
                        else:
                            youtube_helpers_logger.debug(f"تلاش مجدد دانلود با کوکی: id={cid}, path={cookiefile}")
                        def download_sync_cookie():
                            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                                ydl.download([url])
                        await asyncio.to_thread(download_sync_cookie)
                        if cookie_id_used and cookie_id_used != -1:
                            try:
                                mark_cookie_used(cookie_id_used, True)
                            except Exception:
                                pass
                    else:
                        youtube_helpers_logger.debug("کوکی دردسترس نیست؛ عبور")
                except Exception as cookie_err:
                    # اگر خطا رخ داد، تلاش مجدد بدون کوکی
                    youtube_helpers_logger.debug(f"خطا در دانلود با کوکی: {cookie_err}")
                    ydl_opts.pop('cookiefile', None)
                    def download_sync_retry():
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([url])
                    await asyncio.to_thread(download_sync_retry)
        
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
        
        # Configure yt-dlp options for URL extraction with proxy
        ydl_opts = {
            'format': format_id,
            'quiet': True,
            'simulate': True,
            'noplaylist': True,
            'extract_flat': False,
            'proxy': 'socks5h://127.0.0.1:1084',
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios']
                }
            },
        }
        
        cookie_id_used = None
        
        # همیشه ابتدا سعی کن از فایل کوکی اصلی استفاده کنی
        try:
            cookiefile, cid = get_cookie_file_with_fallback(None)
            if cookiefile:
                ydl_opts['cookiefile'] = cookiefile
                cookie_id_used = cid
                if cid == -1:
                    youtube_helpers_logger.info("استفاده از کوکی اصلی cookie_youtube.txt برای استخراج لینک")
                else:
                    youtube_helpers_logger.debug(f"استفاده از کوکی استخر برای استخراج لینک: id={cid}, path={cookiefile}")
        except Exception:
            pass
        
        # Extract info in thread to avoid blocking
        def extract_sync():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        
        try:
            info = await asyncio.to_thread(extract_sync)
        except Exception as first_err:
            # اگر نیاز به کوکی باشد، تلاش مجدد با کوکی
            msg = str(first_err).lower()
            needs_cookie = any(h in msg for h in ['login required', 'sign in', 'age', 'restricted', 'private'])
            if needs_cookie:
                try:
                    # اگر قبلاً کوکی استفاده نشده، سعی کن از فایل اصلی یا استخر استفاده کنی
                    if not cookie_id_used:
                        cookiefile, cid = get_cookie_file_with_fallback(None)
                    else:
                        # اگر قبلاً کوکی استفاده شده، از استخر کوکی دیگری بگیر
                        cookiefile, cid = get_rotated_cookie_file(cookie_id_used)
                    
                    if cookiefile:
                        ydl_opts['cookiefile'] = cookiefile
                        cookie_id_used = cid
                        if cid == -1:
                            youtube_helpers_logger.info("تلاش مجدد استخراج لینک با کوکی اصلی cookie_youtube.txt")
                        else:
                            youtube_helpers_logger.debug(f"تلاش مجدد استخراج لینک با کوکی: id={cid}, path={cookiefile}")
                        info = await asyncio.to_thread(extract_sync)
                        if cookie_id_used and cookie_id_used != -1:
                            try:
                                mark_cookie_used(cookie_id_used, True)
                            except Exception:
                                pass
                    else:
                        youtube_helpers_logger.debug("کوکی دردسترس نیست؛ عبور")
                except Exception as cookie_err:
                    # اگر خطا مرتبط با محدودیت/شبکه باشد، تلاش مجدد
                    youtube_helpers_logger.debug(f"خطا در استخراج لینک با کوکی: {cookie_err}")
                    ydl_opts.pop('cookiefile', None)
                    info = await asyncio.to_thread(extract_sync)
            else:
                # شاید صرفاً محدودیت/شبکه باشد، تلاش مجدد
                youtube_helpers_logger.debug("تلاش مجدد استخراج لینک")
                info = await asyncio.to_thread(extract_sync)
        # تبدیل info به URL مستقیم
        direct_url = None
        try:
            if isinstance(info, dict):
                # اولویت: url مستقیم در سطح info
                direct_url = info.get('url')
                # در صورت وجود requested_formats یا formats، تلاش برای یافتن فرمت مطابق
                if not direct_url:
                    rf = info.get('requested_formats') or []
                    fmts = info.get('formats') or []
                    # جستجو بر اساس format_id
                    for entry in (rf if rf else fmts):
                        if str(entry.get('format_id')) == str(format_id) and entry.get('url'):
                            direct_url = entry['url']
                            break
                    # اگر هنوز چیزی پیدا نشد، اولین URL موجود را برمی‌داریم
                    if not direct_url:
                        for entry in (rf if rf else fmts):
                            if entry.get('url'):
                                direct_url = entry['url']
                                break
        except Exception:
            direct_url = None
        return direct_url
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