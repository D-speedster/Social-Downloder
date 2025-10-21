# youtube_helpers.py - نسخه فیکس شده نهایی

import os
import asyncio
import tempfile
import yt_dlp
import shutil
import sys
import subprocess
import json
from plugins.logger_config import get_logger, get_performance_logger
from plugins.cookie_manager import get_rotated_cookie_file, mark_cookie_used, get_cookie_file_with_fallback

# Initialize logger
youtube_helpers_logger = get_logger('youtube_helpers')
performance_logger = get_performance_logger()

async def download_youtube_file(url, format_id, progress_hook=None, out_dir=None):
    """
    دانلود فایل از یوتیوب با فرمت مشخص شده
    """
    try:
        # بهینه‌سازی مسیر temp برای سرعت بالا
        if out_dir:
            temp_dir = out_dir
            os.makedirs(temp_dir, exist_ok=True)
        else:
            # تلاش برای استفاده از سریع‌ترین مسیر temp موجود
            fast_temp_paths = []
            
            # در ویندوز، تلاش برای استفاده از RAM disk یا SSD
            if os.name == 'nt':  # Windows
                # بررسی وجود RAM disk (معمولاً R:\ یا Z:\)
                for drive in ['R:', 'Z:', 'T:']:
                    if os.path.exists(drive + '\\'):
                        fast_temp_paths.append(drive + '\\temp')
                
                # استفاده از %TEMP% اگر روی SSD باشد
                windows_temp = os.environ.get('TEMP', '')
                if windows_temp:
                    fast_temp_paths.append(windows_temp)
            else:
                # در لینوکس، تلاش برای استفاده از /dev/shm (RAM)
                if os.path.exists('/dev/shm') and os.access('/dev/shm', os.W_OK):
                    fast_temp_paths.append('/dev/shm')
                # یا /tmp اگر روی tmpfs باشد
                fast_temp_paths.append('/tmp')
            
            # انتخاب اولین مسیر قابل دسترس
            temp_dir = None
            for path in fast_temp_paths:
                try:
                    os.makedirs(path, exist_ok=True)
                    # تست نوشتن برای اطمینان از دسترسی
                    test_file = os.path.join(path, 'test_write.tmp')
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                    temp_dir = tempfile.mkdtemp(dir=path, prefix='ytdl_')
                    break
                except (OSError, PermissionError):
                    continue
            
            # اگر هیچ مسیر سریع در دسترس نبود، از مسیر پیش‌فرض استفاده کن
            if not temp_dir:
                temp_dir = tempfile.mkdtemp(prefix='ytdl_')
        
        youtube_helpers_logger.info(f"استفاده از temp directory: {temp_dir}")
        youtube_helpers_logger.info(f"شروع دانلود: {url} با فرمت {format_id}")
        youtube_helpers_logger.info(f"📋 Format ID دقیق: '{format_id}'")
        youtube_helpers_logger.info(f"📋 Type: {type(format_id)}")
        
        ffmpeg_path = os.environ.get('FFMPEG_PATH')
        
        # اگر FFMPEG_PATH تنظیم شده و معتبر است، از آن استفاده کن
        if ffmpeg_path and (shutil.which(ffmpeg_path) or os.path.exists(ffmpeg_path)):
            youtube_helpers_logger.debug(f"استفاده از FFMPEG_PATH از متغیر محیطی: {ffmpeg_path}")
        else:
            # جستجو در مسیرهای معمول
            youtube_helpers_logger.debug("FFMPEG_PATH env not set or invalid, searching common paths...")
            candidates = ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg', 'ffmpeg', 'C\\Program Files\\ffmpeg\\bin\\ffmpeg.exe', 'C\\ffmpeg\\bin\\ffmpeg.exe']
            for candidate in candidates:
                found_path = shutil.which(candidate)
                if found_path:
                    ffmpeg_path = found_path
                    youtube_helpers_logger.debug(f"Found ffmpeg at: {ffmpeg_path}")
                    break

        if not ffmpeg_path:
            youtube_helpers_logger.debug("ffmpeg not found in common paths, checking config.py")
            try:
                from config import FFMPEG_PATH
                if FFMPEG_PATH and (shutil.which(FFMPEG_PATH) or os.path.exists(FFMPEG_PATH)):
                    ffmpeg_path = FFMPEG_PATH
            except (ImportError, AttributeError):
                youtube_helpers_logger.warning("Could not import FFMPEG_PATH from config or it is invalid.")

        youtube_helpers_logger.debug(f"Final ffmpeg path: {ffmpeg_path}")
        
        # Configure yt-dlp options with proxy (from env if present)
        def _get_env_proxy():
            return os.environ.get('PROXY') or os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')
        env_proxy = _get_env_proxy()

        ydl_opts = {
            'format': format_id or 'bestvideo+bestaudio/best',
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'extract_flat': False,
            'ignoreerrors': False,
            'quiet': False,  # فعال‌سازی لاگ‌ها
            'no_warnings': False,
            'socket_timeout': 60,
            'retries': 5,
            'fragment_retries': 5,
            'concurrent_fragments': 8,  # افزایش از 4 به 8
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip,deflate',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            },
            'extractor_retries': 5,
            'file_access_retries': 3,
            'writesubtitles': False,
            'writeautomaticsub': False
        }
        
        if env_proxy:
            ydl_opts['proxy'] = env_proxy
        
        # 🔥 فیکس اصلی: تنظیمات صحیح ffmpeg
        if ffmpeg_path and (shutil.which(ffmpeg_path) or os.path.exists(ffmpeg_path)):
            ydl_opts['ffmpeg_location'] = ffmpeg_path
            ydl_opts['merge_output_format'] = 'mp4'
            
            # ✅ استفاده از FFmpegVideoRemuxer بجای Convertor
            ydl_opts['postprocessors'] = [
                {
                    'key': 'FFmpegVideoRemuxer',
                    'preferedformat': 'mp4',
                },
                {
                    'key': 'FFmpegMetadata',
                    'add_metadata': True,
                },
            ]
            
            # ✅ فیکس کلید postprocessor_args
            # باید 'video' باشه، نه 'remuxvideo'
            ydl_opts['postprocessor_args'] = {
                'video': ['-c:v', 'copy', '-c:a', 'copy', '-movflags', '+faststart']
            }
            
            youtube_helpers_logger.debug("تنظیمات FFmpeg برای merge و faststart اعمال شد")
        
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

        # Initial attempt: download with merging
        try:
            def download_sync():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            await asyncio.to_thread(download_sync)
        except Exception as e:
            youtube_helpers_logger.debug(f"خطا در دانلود اولیه: {e}")
            # Retry with reduced options (no postprocessors)
            try:
                ydl_opts.pop('postprocessors', None)
                ydl_opts.pop('postprocessor_args', None)
                def download_sync_retry():
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                await asyncio.to_thread(download_sync_retry)
            except Exception:
                # Try cookie rotation
                try:
                    cookiefile, cid = get_cookie_file_with_fallback(cookie_id_used)
                    if cookiefile:
                        ydl_opts['cookiefile'] = cookiefile
                        cookie_id_used = cid
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
                    def download_sync_retry2():
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([url])
                    await asyncio.to_thread(download_sync_retry2)
        
        # ثبت موفقیت استفاده از کوکی
        if cookie_id_used:
            try:
                mark_cookie_used(cookie_id_used, True)
            except Exception:
                pass
        
        # Find downloaded/merged file (prefer MP4)
        downloaded_files = [f for f in os.listdir(temp_dir) 
                          if os.path.isfile(os.path.join(temp_dir, f)) 
                          and not f.endswith('.part')
                          and not f.endswith('.ytdl')]
        
        if not downloaded_files:
            youtube_helpers_logger.error("هیچ فایل دانلود شده‌ای یافت نشد")
            return None
        
        # Prefer .mp4 then by size
        downloaded_files.sort(key=lambda fn: (
            0 if fn.lower().endswith('.mp4') else 1, 
            -os.path.getsize(os.path.join(temp_dir, fn))
        ))
        downloaded_file = os.path.join(temp_dir, downloaded_files[0])
        file_size = os.path.getsize(downloaded_file)
        
        youtube_helpers_logger.info(f"✅ دانلود موفق: {downloaded_file}")
        youtube_helpers_logger.info(f"📋 Format ID دقیق: '{format_id}'")
        youtube_helpers_logger.info(f"📋 Type: {type(format_id)}")
        youtube_helpers_logger.info(f"📦 حجم فایل: {file_size / (1024*1024):.2f} MB")
        
        # 🔍 بررسی metadata با ffprobe
        if ffmpeg_path:
            try:
                ffprobe_path = ffmpeg_path.replace('ffmpeg', 'ffprobe')
                if not os.path.exists(ffprobe_path):
                    ffprobe_path = shutil.which('ffprobe')
                
                if ffprobe_path:
                    cmd = [
                        ffprobe_path, '-v', 'error',
                        '-show_entries', 'format=duration,size,bit_rate',
                        '-show_entries', 'stream=codec_type,codec_name,width,height',
                        '-of', 'json',
                        downloaded_file
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        metadata = json.loads(result.stdout)
                        streams = metadata.get('streams', [])
                        fmt = metadata.get('format', {})
                        has_video = any(s.get('codec_type') == 'video' for s in streams)
                        has_audio = any(s.get('codec_type') == 'audio' for s in streams)
                        duration = float(fmt.get('duration', 0) or 0)
                        bitrate = int(fmt.get('bit_rate', 0) or 0) // 1000  # kbps
                        size_bytes_meta = int(fmt.get('size', 0) or 0)
                        
                        youtube_helpers_logger.info(
                            f"📊 Metadata: Video={'✅' if has_video else '❌'}, "
                            f"Audio={'✅' if has_audio else '❌'}, "
                            f"⏱️ Duration={duration:.1f}s, 📊 Bitrate={bitrate} kbps, "
                            f"📦 SizeMeta={size_bytes_meta / (1024*1024):.2f} MB"
                        )
                        
                        # جزئیات هر stream
                        for s in streams:
                            codec_type = s.get('codec_type')
                            codec_name = s.get('codec_name')
                            w = s.get('width')
                            h = s.get('height')
                            if codec_type == 'video':
                                youtube_helpers_logger.info(f"🔧 VideoCodec: {codec_name}, 📐 {w}x{h}")
                            elif codec_type == 'audio':
                                youtube_helpers_logger.info(f"🔧 AudioCodec: {codec_name}")
                        
                        if not has_audio and has_video:
                            youtube_helpers_logger.warning("⚠️ فایل صوت ندارد!")
                        if duration == 0:
                            youtube_helpers_logger.warning("⚠️ مدت زمان صفر است!")
                    else:
                        youtube_helpers_logger.warning(f"⚠️ خطا در ffprobe: {result.stderr}")
                        
            except Exception as e:
                youtube_helpers_logger.debug(f"نتوانستیم metadata را بررسی کنیم: {e}")
        
        return downloaded_file
        
    except Exception as e:
        youtube_helpers_logger.error(f"❌ خطا در دانلود: {e}")
        # ثبت شکست استفاده از کوکی
        try:
            if 'cookie_id_used' in locals() and cookie_id_used:
                mark_cookie_used(cookie_id_used, False)
        except Exception:
            pass
        return None


# بقیه توابع بدون تغییر...
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
        }
        
        cookie_id_used = None
        
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
        
        def extract_sync():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        
        try:
            info = await asyncio.to_thread(extract_sync)
        except Exception as first_err:
            msg = str(first_err).lower()
            needs_cookie = any(h in msg for h in ['login required', 'sign in', 'age', 'restricted', 'private'])
            if needs_cookie:
                try:
                    if not cookie_id_used:
                        cookiefile, cid = get_cookie_file_with_fallback(None)
                    else:
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
                    youtube_helpers_logger.debug(f"خطا در استخراج لینک با کوکی: {cookie_err}")
                    ydl_opts.pop('cookiefile', None)
                    info = await asyncio.to_thread(extract_sync)
            else:
                youtube_helpers_logger.debug("تلاش مجدد استخراج لینک")
                info = await asyncio.to_thread(extract_sync)
        
        direct_url = None
        try:
            if isinstance(info, dict):
                direct_url = info.get('url')
                if not direct_url:
                    rf = info.get('requested_formats') or []
                    fmts = info.get('formats') or []
                    for entry in (rf if rf else fmts):
                        if str(entry.get('format_id')) == str(format_id) and entry.get('url'):
                            direct_url = entry['url']
                            break
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