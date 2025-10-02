import os
import asyncio
import tempfile
import yt_dlp
from plugins.logger_config import get_logger
from plugins.proxy_config import get_proxy_url
from plugins.cookie_manager import get_rotated_cookie_file, mark_cookie_used
from plugins.youtube_proxy_rotator import is_enabled as proxy_rotation_enabled, extract_with_rotation, download_with_rotation

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
        
        # Configure yt-dlp options (initially without proxy/cookie)
        ydl_opts = {
            'format': format_id,
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'extract_flat': False,
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

        # Optional: always use cookies from rotation if enabled by environment
        if os.getenv('YOUTUBE_ALWAYS_USE_COOKIES', '0') == '1':
            try:
                cookiefile, cid = get_rotated_cookie_file(None)
                if cookiefile:
                    ydl_opts['cookiefile'] = cookiefile
                    cookie_id_used = cid
                    youtube_helpers_logger.debug(f"کوکی از ابتدا فعال شد: id={cid}, path={cookiefile}")
            except Exception:
                pass

        # Initial attempt: use proxy rotation if enabled
        try:
            if proxy_rotation_enabled():
                await download_with_rotation(url, ydl_opts, cookiefile=None, max_attempts=3)
            else:
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
                    cookiefile, cid = get_rotated_cookie_file(None)
                    if cookiefile:
                        ydl_opts['cookiefile'] = cookiefile
                        cookie_id_used = cid
                        youtube_helpers_logger.debug(f"تلاش مجدد دانلود با کوکی: id={cid}, path={cookiefile}")
                        if proxy_rotation_enabled():
                            await download_with_rotation(url, ydl_opts, cookiefile=cookiefile, max_attempts=3)
                        else:
                            def download_sync_cookie():
                                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                                    ydl.download([url])
                            await asyncio.to_thread(download_sync_cookie)
                        if cookie_id_used:
                            try:
                                mark_cookie_used(cookie_id_used, True)
                            except Exception:
                                pass
                    else:
                        youtube_helpers_logger.debug("کوکی دردسترس نیست؛ عبور")
                except Exception as cookie_err:
                    # اگر خطا مرتبط با محدودیت/شبکه باشد و پراکسی سیستم موجود باشد، تلاش با پراکسی
                    needs_proxy = any(h in str(cookie_err).lower() for h in ['403', '429', 'proxy', 'forbidden', 'blocked'])
                    if needs_proxy:
                        ydl_opts.pop('cookiefile', None)
                        if proxy_rotation_enabled():
                            youtube_helpers_logger.debug("تلاش دانلود با چرخش پراکسی SOCKS5H")
                            await download_with_rotation(url, ydl_opts, cookiefile=None, max_attempts=3)
                        else:
                            proxy_url = get_proxy_url()
                            if proxy_url:
                                ydl_opts['proxy'] = proxy_url
                                youtube_helpers_logger.debug(f"تلاش دانلود با پراکسی سیستم: {proxy_url}")
                                def download_sync_proxy():
                                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                                        ydl.download([url])
                                await asyncio.to_thread(download_sync_proxy)
        
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
        
        # Configure yt-dlp options for URL extraction only (initially without proxy/cookie)
        ydl_opts = {
            'format': format_id,
            'quiet': True,
            'simulate': True,
            'noplaylist': True,
            'extract_flat': False,
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios']
                }
            },
        }
        
        cookie_id_used = None
        
        # Optional: always use cookies from rotation if enabled by environment
        if os.getenv('YOUTUBE_ALWAYS_USE_COOKIES', '0') == '1':
            try:
                cookiefile, cid = get_rotated_cookie_file(None)
                if cookiefile:
                    ydl_opts['cookiefile'] = cookiefile
                    cookie_id_used = cid
                    youtube_helpers_logger.debug(f"کوکی از ابتدا فعال شد: id={cid}, path={cookiefile}")
            except Exception:
                pass
        
        # Extract info in thread to avoid blocking
        def extract_sync():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        
        try:
            if proxy_rotation_enabled():
                info = await extract_with_rotation(url, ydl_opts, cookiefile=None, max_attempts=3)
            else:
                info = await asyncio.to_thread(extract_sync)
        except Exception as first_err:
            # اگر نیاز به کوکی باشد، تلاش مجدد با کوکی
            msg = str(first_err).lower()
            needs_cookie = any(h in msg for h in ['login required', 'sign in', 'age', 'restricted', 'private'])
            if needs_cookie:
                try:
                    cookiefile, cid = get_rotated_cookie_file(None)
                    if cookiefile:
                        ydl_opts['cookiefile'] = cookiefile
                        cookie_id_used = cid
                        youtube_helpers_logger.debug(f"تلاش مجدد استخراج لینک با کوکی: id={cid}, path={cookiefile}")
                        if proxy_rotation_enabled():
                            info = await extract_with_rotation(url, ydl_opts, cookiefile=cookiefile, max_attempts=3)
                        else:
                            info = await asyncio.to_thread(extract_sync)
                        if cookie_id_used:
                            try:
                                mark_cookie_used(cookie_id_used, True)
                            except Exception:
                                pass
                    else:
                        youtube_helpers_logger.debug("کوکی دردسترس نیست؛ عبور")
                except Exception as cookie_err:
                    # اگر خطا مرتبط با محدودیت/شبکه باشد و پراکسی سیستم موجود باشد، تلاش با پراکسی
                    needs_proxy = any(h in str(cookie_err).lower() for h in ['403', '429', 'proxy', 'forbidden', 'blocked'])
                    if needs_proxy:
                        ydl_opts.pop('cookiefile', None)
                        if proxy_rotation_enabled():
                            youtube_helpers_logger.debug("تلاش استخراج لینک با چرخش پراکسی SOCKS5H")
                            info = await extract_with_rotation(url, ydl_opts, cookiefile=None, max_attempts=3)
                        else:
                            proxy_url = get_proxy_url()
                            if proxy_url:
                                ydl_opts['proxy'] = proxy_url
                                youtube_helpers_logger.debug(f"تلاش استخراج لینک با پراکسی سیستم: {proxy_url}")
                                info = await asyncio.to_thread(extract_sync)
            else:
                # شاید صرفاً محدودیت/شبکه باشد؛ اگر پراکسی سیستم موجود است امتحان می‌کنیم
                needs_proxy = any(h in msg for h in ['403', '429', 'proxy', 'forbidden', 'blocked'])
                if needs_proxy:
                    if proxy_rotation_enabled():
                        youtube_helpers_logger.debug("تلاش استخراج لینک با چرخش پراکسی SOCKS5H")
                        info = await extract_with_rotation(url, ydl_opts, cookiefile=None, max_attempts=3)
                    else:
                        proxy_url = get_proxy_url()
                        if proxy_url:
                            ydl_opts['proxy'] = proxy_url
                            youtube_helpers_logger.debug(f"تلاش استخراج لینک با پراکسی سیستم: {proxy_url}")
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