# youtube_helpers.py - نسخه بهینه شده برای سرعت بالا

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
    دانلود فایل از یوتیوب با فرمت مشخص شده - نسخه بهینه شده
    """
    try:
        # بهینه‌سازی مسیر temp برای سرعت بالا
        if out_dir:
            temp_dir = out_dir
            os.makedirs(temp_dir, exist_ok=True)
        else:
            # تلاش برای استفاده از سریع‌ترین مسیر temp موجود
            fast_temp_paths = []
            
            if os.name == 'nt':  # Windows
                for drive in ['R:', 'Z:', 'T:']:
                    if os.path.exists(drive + '\\'):
                        fast_temp_paths.append(drive + '\\temp')
                windows_temp = os.environ.get('TEMP', '')
                if windows_temp:
                    fast_temp_paths.append(windows_temp)
            else:
                # در لینوکس، تلاش برای استفاده از /dev/shm (RAM)
                if os.path.exists('/dev/shm') and os.access('/dev/shm', os.W_OK):
                    fast_temp_paths.append('/dev/shm')
                fast_temp_paths.append('/tmp')
            
            temp_dir = None
            for path in fast_temp_paths:
                try:
                    os.makedirs(path, exist_ok=True)
                    test_file = os.path.join(path, 'test_write.tmp')
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                    temp_dir = tempfile.mkdtemp(dir=path, prefix='ytdl_')
                    break
                except (OSError, PermissionError):
                    continue
            
            if not temp_dir:
                temp_dir = tempfile.mkdtemp(prefix='ytdl_')
        
        youtube_helpers_logger.info(f"استفاده از temp directory: {temp_dir}")
        youtube_helpers_logger.info(f"🚀 شروع دانلود: {url}")
        youtube_helpers_logger.info(f"📋 Format ID: '{format_id}'")
        
        is_combined_format = '+' in str(format_id)
        youtube_helpers_logger.info(f"🔀 Combined format: {is_combined_format}")
        
        # 🔥 پیدا کردن ffmpeg
        ffmpeg_path = os.environ.get('FFMPEG_PATH')
        
        if ffmpeg_path and (shutil.which(ffmpeg_path) or os.path.exists(ffmpeg_path)):
            youtube_helpers_logger.debug(f"استفاده از FFMPEG_PATH: {ffmpeg_path}")
        else:
            candidates = ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg', 'ffmpeg']
            for candidate in candidates:
                found_path = shutil.which(candidate)
                if found_path:
                    ffmpeg_path = found_path
                    youtube_helpers_logger.debug(f"Found ffmpeg: {ffmpeg_path}")
                    break

        if not ffmpeg_path:
            try:
                from config import FFMPEG_PATH
                if FFMPEG_PATH and (shutil.which(FFMPEG_PATH) or os.path.exists(FFMPEG_PATH)):
                    ffmpeg_path = FFMPEG_PATH
            except (ImportError, AttributeError):
                pass

        youtube_helpers_logger.debug(f"Final ffmpeg path: {ffmpeg_path}")
        
        # Configure yt-dlp options
        env_proxy = os.environ.get('PROXY') or os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')

        ydl_opts = {
            'format': format_id or 'bestvideo+bestaudio/best',
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'extract_flat': False,
            'ignoreerrors': False,
            'quiet': False,
            'no_warnings': False,
            'socket_timeout': 60,
            'retries': 5,
            'fragment_retries': 5,
            'concurrent_fragments': 8,  # دانلود همزمان چند قطعه
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Connection': 'keep-alive',
            },
            'extractor_retries': 5,
            'file_access_retries': 3,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'writethumbnail': False,  # 🔥 غیرفعال کردن دانلود thumbnail
            'writeinfojson': False,   # 🔥 غیرفعال کردن نوشتن info.json
        }
        
        if env_proxy:
            ydl_opts['proxy'] = env_proxy
        
        # 🔥 تنظیمات بهینه FFmpeg - فقط merge بدون re-encode
        if ffmpeg_path and (shutil.which(ffmpeg_path) or os.path.exists(ffmpeg_path)):
            ydl_opts['ffmpeg_location'] = ffmpeg_path
            
            # ✅ فقط MP4 برای merge
            ydl_opts['merge_output_format'] = 'mp4'
            
            # ✅ فقط یک postprocessor: FFmpegVideoRemuxer (بدون re-encode)
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegVideoRemuxer',  # 🔥 تغییر از VideoConvertor به VideoRemuxer
                'preferedformat': 'mp4',
            }]
            
            # ✅ آرگومان‌های FFmpeg: copy بدون re-encode + faststart
            ydl_opts['postprocessor_args'] = {
                'ffmpeg': [
                    '-c:v', 'copy',      # کپی ویدیو بدون re-encode
                    '-c:a', 'copy',      # کپی صدا بدون re-encode
                    '-movflags', '+faststart',  # بهینه‌سازی برای streaming
                ]
            }
            
            youtube_helpers_logger.debug("✅ FFmpeg: remux only (NO re-encode) + faststart")
        
        # Add progress hook با throttling
        if progress_hook:
            # 🔥 Throttle progress updates (هر 500ms یک بار)
            last_call = {'time': 0}
            def throttled_progress_hook(d):
                import time
                now = time.time()
                if now - last_call['time'] >= 0.5:  # حداکثر 2 بار در ثانیه
                    last_call['time'] = now
                    progress_hook(d)
            
            ydl_opts['progress_hooks'] = [throttled_progress_hook]
        
        cookie_id_used = None

        # کوکی
        try:
            cookiefile, cid = get_cookie_file_with_fallback(None)
            if cookiefile:
                ydl_opts['cookiefile'] = cookiefile
                cookie_id_used = cid
                if cid == -1:
                    youtube_helpers_logger.info("استفاده از کوکی اصلی")
                else:
                    youtube_helpers_logger.debug(f"استفاده از کوکی استخر: id={cid}")
        except Exception:
            pass

        # دانلود
        try:
            def download_sync():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            await asyncio.to_thread(download_sync)
        except Exception as e:
            youtube_helpers_logger.debug(f"خطا در دانلود اولیه: {e}")
            # Retry بدون postprocessors
            try:
                ydl_opts.pop('postprocessors', None)
                ydl_opts.pop('postprocessor_args', None)
                def download_sync_retry():
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                await asyncio.to_thread(download_sync_retry)
            except Exception:
                # Cookie rotation
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
                except Exception as cookie_err:
                    youtube_helpers_logger.debug(f"خطا در دانلود با کوکی: {cookie_err}")
                    ydl_opts.pop('cookiefile', None)
                    def download_sync_retry2():
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([url])
                    await asyncio.to_thread(download_sync_retry2)
        
        # ثبت موفقیت کوکی
        if cookie_id_used:
            try:
                mark_cookie_used(cookie_id_used, True)
            except Exception:
                pass
        
        # پیدا کردن فایل دانلود شده
        downloaded_files = [f for f in os.listdir(temp_dir) 
                          if os.path.isfile(os.path.join(temp_dir, f)) 
                          and not f.endswith('.part')
                          and not f.endswith('.ytdl')
                          and not f.endswith('.json')  # 🔥 حذف فایل‌های json
                          and not f.endswith('.webp')  # 🔥 حذف thumbnail
                          and not f.endswith('.jpg')]
        
        if not downloaded_files:
            youtube_helpers_logger.error("هیچ فایل دانلود شده‌ای یافت نشد")
            return None
        
        # ترجیح MP4 بعد بزرگترین
        downloaded_files.sort(key=lambda fn: (
            0 if fn.lower().endswith('.mp4') else 1, 
            -os.path.getsize(os.path.join(temp_dir, fn))
        ))
        downloaded_file = os.path.join(temp_dir, downloaded_files[0])
        file_size = os.path.getsize(downloaded_file)
        
        youtube_helpers_logger.info(f"✅ دانلود موفق: {os.path.basename(downloaded_file)}")
        youtube_helpers_logger.info(f"📦 حجم: {file_size / (1024*1024):.2f} MB ({file_size} bytes)")
        
        # 🔥 حذف بررسی metadata برای صرفه‌جویی در زمان
        # فقط در صورت debug mode فعال می‌شود
        if os.environ.get('DEBUG_MODE') == '1' and ffmpeg_path:
            try:
                ffprobe_path = ffmpeg_path.replace('ffmpeg', 'ffprobe')
                if os.path.exists(ffprobe_path) or shutil.which('ffprobe'):
                    if not os.path.exists(ffprobe_path):
                        ffprobe_path = shutil.which('ffprobe')
                    
                    cmd = [
                        ffprobe_path, '-v', 'error',
                        '-show_entries', 'stream=codec_type',
                        '-of', 'json',
                        downloaded_file
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    
                    if result.returncode == 0:
                        metadata = json.loads(result.stdout)
                        streams = metadata.get('streams', [])
                        video_count = sum(1 for s in streams if s.get('codec_type') == 'video')
                        audio_count = sum(1 for s in streams if s.get('codec_type') == 'audio')
                        youtube_helpers_logger.debug(f"Streams: {video_count}V + {audio_count}A")
            except Exception as e:
                youtube_helpers_logger.debug(f"خطا در بررسی سریع metadata: {e}")
        
        return downloaded_file
        
    except Exception as e:
        youtube_helpers_logger.error(f"❌ خطا در دانلود: {e}")
        try:
            if 'cookie_id_used' in locals() and cookie_id_used:
                mark_cookie_used(cookie_id_used, False)
        except Exception:
            pass
        return None


async def get_direct_download_url(url, format_id):
    """دریافت لینک مستقیم دانلود - بهینه شده"""
    try:
        youtube_helpers_logger.info(f"دریافت لینک مستقیم: {url} با فرمت {format_id}")
        
        ydl_opts = {
            'format': format_id,
            'quiet': True,
            'simulate': True,
            'noplaylist': True,
            'extract_flat': False,
            'socket_timeout': 10,  # 🔥 کاهش timeout
        }
        
        env_proxy = os.environ.get('PROXY') or os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')
        if env_proxy:
            ydl_opts['proxy'] = env_proxy
        
        cookie_id_used = None
        
        try:
            cookiefile, cid = get_cookie_file_with_fallback(None)
            if cookiefile:
                ydl_opts['cookiefile'] = cookiefile
                cookie_id_used = cid
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
                        info = await asyncio.to_thread(extract_sync)
                        if cookie_id_used and cookie_id_used != -1:
                            try:
                                mark_cookie_used(cookie_id_used, True)
                            except Exception:
                                pass
                except Exception:
                    ydl_opts.pop('cookiefile', None)
                    info = await asyncio.to_thread(extract_sync)
            else:
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
    """ویرایش ایمن متن پیام"""
    try:
        await message.edit_text(text=text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception as e:
        youtube_helpers_logger.debug(f"خطا در ویرایش پیام: {e}")