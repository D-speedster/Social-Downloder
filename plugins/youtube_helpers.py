import os
import asyncio
import tempfile
import yt_dlp
from plugins.logger_config import get_logger
from plugins.cookie_manager import get_rotated_cookie_file, mark_cookie_used, get_cookie_file_with_fallback

# Initialize logger
youtube_helpers_logger = get_logger('youtube_helpers')

async def get_available_formats(url):
    """
    دریافت لیست فرمت‌های موجود برای ویدیو
    """
    try:
        ydl_opts = {
            'quiet': True,
            'simulate': True,
            'listformats': True,
            'proxy': 'socks5h://127.0.0.1:1084',
            'socket_timeout': 15,
            'retries': 3,
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'android', 'web'],
                    'player_skip': ['webpage'],
                    'skip': ['hls', 'dash'],
                    'innertube_host': 'studio.youtube.com',
                    'innertube_key': 'AIzaSyBUPetSUmoZL-OhlxA7wSac5XinrygCqMo'
                }
            },
        }
        
        def extract_info_sync():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        
        info = await asyncio.to_thread(extract_info_sync)
        return info.get('formats', []) if info else []
    except Exception as e:
        youtube_helpers_logger.error(f"خطا در دریافت فرمت‌ها: {e}")
        return []

async def find_best_fallback_format(url, requested_format_id):
    """
    پیدا کردن بهترین فرمت جایگزین در صورت عدم دسترسی به فرمت درخواستی
    """
    try:
        formats = await get_available_formats(url)
        if not formats:
            return None
        
        # اگر فرمت درخواستی شامل + باشد (ترکیب ویدیو + صدا)
        if '+' in requested_format_id:
            video_id, audio_id = requested_format_id.split('+')
            
            # بررسی وجود فرمت‌های درخواستی
            video_available = any(f.get('format_id') == video_id for f in formats)
            audio_available = any(f.get('format_id') == audio_id for f in formats)
            
            if video_available and audio_available:
                return requested_format_id
            
            # پیدا کردن بهترین جایگزین
            video_formats = [f for f in formats if f.get('vcodec', 'none') != 'none' and f.get('acodec', 'none') == 'none']
            audio_formats = [f for f in formats if f.get('acodec', 'none') != 'none' and f.get('vcodec', 'none') == 'none']
            
            if video_formats and audio_formats:
                # انتخاب بهترین ویدیو (بر اساس کیفیت)
                video_formats.sort(key=lambda x: (x.get('height', 0) or 0), reverse=True)
                best_video = video_formats[0]
                
                # انتخاب بهترین صدا (بر اساس bitrate)
                audio_formats.sort(key=lambda x: (x.get('abr', 0) or x.get('tbr', 0) or 0), reverse=True)
                best_audio = audio_formats[0]
                
                return f"{best_video['format_id']}+{best_audio['format_id']}"
        else:
            # بررسی وجود فرمت تکی
            if any(f.get('format_id') == requested_format_id for f in formats):
                return requested_format_id
            
            # پیدا کردن بهترین جایگزین
            # ابتدا فرمت‌های ترکیبی (ویدیو + صدا)
            combined_formats = [f for f in formats if f.get('vcodec', 'none') != 'none' and f.get('acodec', 'none') != 'none']
            if combined_formats:
                combined_formats.sort(key=lambda x: (x.get('height', 0) or 0), reverse=True)
                return combined_formats[0]['format_id']
            
            # اگر فرمت ترکیبی نبود، بهترین ویدیو + بهترین صدا
            video_formats = [f for f in formats if f.get('vcodec', 'none') != 'none' and f.get('acodec', 'none') == 'none']
            audio_formats = [f for f in formats if f.get('acodec', 'none') != 'none' and f.get('vcodec', 'none') == 'none']
            
            if video_formats and audio_formats:
                video_formats.sort(key=lambda x: (x.get('height', 0) or 0), reverse=True)
                audio_formats.sort(key=lambda x: (x.get('abr', 0) or x.get('tbr', 0) or 0), reverse=True)
                return f"{video_formats[0]['format_id']}+{audio_formats[0]['format_id']}"
        
        # اگر هیچ فرمت مناسبی پیدا نشد، بهترین فرمت موجود
        if formats:
            # اولویت با فرمت‌های ترکیبی
            combined = [f for f in formats if f.get('vcodec', 'none') != 'none' and f.get('acodec', 'none') != 'none']
            if combined:
                combined.sort(key=lambda x: (x.get('height', 0) or 0), reverse=True)
                return combined[0]['format_id']
            
            # در غیر این صورت، بهترین فرمت موجود
            formats.sort(key=lambda x: (x.get('height', 0) or x.get('abr', 0) or x.get('tbr', 0) or 0), reverse=True)
            return formats[0]['format_id']
        
        return None
    except Exception as e:
        youtube_helpers_logger.error(f"خطا در پیدا کردن فرمت جایگزین: {e}")
        return None

async def download_youtube_file(url, format_id, progress_hook=None, out_dir=None):
    """
    دانلود فایل یوتیوب با format_id مشخص
    اگر out_dir مشخص شود، فایل در آن پوشه ذخیره می‌شود؛ در غیر این‌صورت از دایرکتوری موقت استفاده می‌شود.
    """
    try:
        youtube_helpers_logger.info(f"شروع دانلود: {url} با فرمت {format_id}")
        
        # Prepare output directory
        temp_dir = None
        if out_dir:
            try:
                os.makedirs(out_dir, exist_ok=True)
            except Exception as e:
                youtube_helpers_logger.error(f"ناتوانی در ایجاد پوشه دانلود {out_dir}: {e}")
                out_dir = None
        if not out_dir:
            temp_dir = tempfile.mkdtemp()
            youtube_helpers_logger.debug(f"دایرکتوری موقت ایجاد شد: {temp_dir}")
        target_dir = out_dir or temp_dir
        
        # Configure yt-dlp options with proxy (from env if present)
        def _get_env_proxy():
            return os.environ.get('PROXY') or os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')
        env_proxy = _get_env_proxy()

        ydl_opts = {
            'format': format_id,
            'outtmpl': os.path.join(target_dir, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'extract_flat': False,
            'socket_timeout': 30,
            'retries': 3,
            'concurrent_fragments': 8,
            'force_ipv4': True,
            'http_chunk_size': '16M',
            'fragment_retries': 3,
            # Ensure resume for partial downloads on restart
            'continuedl': True,
            'nopart': False,
            'nooverwrites': True,
            # Windows-safe filenames to avoid path issues
            'windowsfilenames': True,
            # Enhanced headers to mimic real browser
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip,deflate',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                'Keep-Alive': '300',
                'Connection': 'keep-alive',
            },
            # Additional options for YouTube compatibility
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'android', 'web'],
                    'player_skip': ['webpage'],
                    'skip': ['hls', 'dash'],
                    'innertube_host': 'studio.youtube.com',
                    'innertube_key': 'AIzaSyBUPetSUmoZL-OhlxA7wSac5XinrygCqMo'
                }
            },
        }
        if env_proxy:
            ydl_opts['proxy'] = env_proxy
        
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
            format_not_available = 'requested format is not available' in msg
            
            if format_not_available:
                # Try to find a fallback format
                try:
                    fallback_format = await find_best_fallback_format(url, format_id)
                    if fallback_format and fallback_format != format_id:
                        youtube_helpers_logger.info(f"Format {format_id} not available, trying fallback format: {fallback_format}")
                        ydl_opts['format'] = fallback_format
                        def download_sync_fallback():
                            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                                ydl.download([url])
                        await asyncio.to_thread(download_sync_fallback)
                    else:
                        raise first_err
                except Exception as fallback_err:
                    youtube_helpers_logger.error(f"Fallback format search failed: {fallback_err}")
                    raise first_err
            elif needs_cookie:
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
        
        # Find downloaded file in target_dir (pick the newest)
        downloaded_files = [
            os.path.join(target_dir, f) for f in os.listdir(target_dir)
            if os.path.isfile(os.path.join(target_dir, f))
        ]
        if not downloaded_files:
            youtube_helpers_logger.error("هیچ فایل دانلود شده‌ای یافت نشد")
            return None
        
        downloaded_files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        downloaded_file = downloaded_files[0]
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
            'socket_timeout': 15,
            'retries': 3,
            # استفاده از کلاینت پیش‌فرض web که از کوکی پشتیبانی می‌کند
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
            format_not_available = 'requested format is not available' in msg
            
            if format_not_available:
                # Try to find a fallback format
                try:
                    fallback_format = await find_best_fallback_format(url, format_id)
                    if fallback_format and fallback_format != format_id:
                        youtube_helpers_logger.info(f"Format {format_id} not available, trying fallback format: {fallback_format}")
                        ydl_opts['format'] = fallback_format
                        info = await asyncio.to_thread(extract_sync)
                        format_id = fallback_format  # Update format_id for later use
                    else:
                        raise first_err
                except Exception as fallback_err:
                    youtube_helpers_logger.error(f"Fallback format search failed: {fallback_err}")
                    raise first_err
            elif needs_cookie:
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