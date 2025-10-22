# youtube_helpers.py - نسخه فیکس شده نهایی با حل مشکل merge

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
            
            # انتخاب اولین مسیر قابل دسترس
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
        youtube_helpers_logger.info(f"📋 Format ID: '{format_id}' (Type: {type(format_id).__name__})")
        
        # 🔍 چک کردن اینکه format_id شامل + هست یا نه
        is_combined_format = '+' in str(format_id)
        youtube_helpers_logger.info(f"🔀 Combined format (video+audio): {is_combined_format}")
        
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
            'concurrent_fragments': 8,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Connection': 'keep-alive',
            },
            'extractor_retries': 5,
            'file_access_retries': 3,
            'writesubtitles': False,
            'writeautomaticsub': False
        }
        
        if env_proxy:
            ydl_opts['proxy'] = env_proxy
        
        # 🔥 فیکس اصلی: تنظیمات صحیح برای merge
        if ffmpeg_path and (shutil.which(ffmpeg_path) or os.path.exists(ffmpeg_path)):
            ydl_opts['ffmpeg_location'] = ffmpeg_path
            
            # ✅ حتماً merge_output_format تنظیم کن
            ydl_opts['merge_output_format'] = 'mp4'
            
            # ✅ postprocessors صحیح با ترتیب درست
            ydl_opts['postprocessors'] = [
                # اول: Merge کردن video+audio (اگه جدا باشن)
                {
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                },
                # دوم: اضافه کردن metadata
                {
                    'key': 'FFmpegMetadata',
                    'add_metadata': True,
                },
            ]
            
            # ✅ postprocessor_args برای جلوگیری از re-encode
            ydl_opts['postprocessor_args'] = {
                'ffmpeg': ['-c:v', 'copy', '-c:a', 'copy', '-movflags', '+faststart']
            }
            
            youtube_helpers_logger.debug("✅ تنظیمات FFmpeg: merge + metadata + faststart (بدون re-encode)")
        
        # Add progress hook
        if progress_hook:
            ydl_opts['progress_hooks'] = [progress_hook]
        
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
                          and not f.endswith('.ytdl')]
        
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
        youtube_helpers_logger.info(f"📦 حجم فایل دانلود شده: {file_size / (1024*1024):.2f} MB")
        youtube_helpers_logger.info(f"💾 حجم دقیق به بایت: {file_size} bytes")
        
        # 🔍 بررسی دقیق metadata
        if ffmpeg_path:
            try:
                ffprobe_path = ffmpeg_path.replace('ffmpeg', 'ffprobe')
                if not os.path.exists(ffprobe_path):
                    ffprobe_path = shutil.which('ffprobe')
                
                if ffprobe_path:
                    youtube_helpers_logger.info("="*60)
                    youtube_helpers_logger.info("🔍 بررسی دقیق فایل با ffprobe")
                    youtube_helpers_logger.info("="*60)
                    
                    cmd = [
                        ffprobe_path, '-v', 'error',
                        '-show_entries', 'format=size,duration,bit_rate,format_name',
                        '-show_entries', 'stream=index,codec_type,codec_name,width,height,bit_rate',
                        '-of', 'json',
                        downloaded_file
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                    
                    if result.returncode == 0:
                        metadata = json.loads(result.stdout)
                        fmt = metadata.get('format', {})
                        streams = metadata.get('streams', [])
                        
                        # اطلاعات format
                        youtube_helpers_logger.info(f"🎞️  Format: {fmt.get('format_name', 'N/A')}")
                        duration = float(fmt.get('duration', 0) or 0)
                        youtube_helpers_logger.info(f"⏱️  Duration: {duration:.1f}s ({duration/60:.1f} min)")
                        
                        total_bitrate = int(fmt.get('bit_rate', 0) or 0) // 1000
                        youtube_helpers_logger.info(f"📊 Total Bitrate: {total_bitrate} kbps")
                        
                        size_meta = int(fmt.get('size', 0) or 0)
                        youtube_helpers_logger.info(f"📦 Size (metadata): {size_meta / (1024*1024):.2f} MB")
                        
                        # تعداد streams
                        youtube_helpers_logger.info(f"🎬 تعداد streams: {len(streams)}")
                        
                        video_count = 0
                        audio_count = 0
                        
                        # جزئیات هر stream
                        for i, s in enumerate(streams):
                            stype = s.get('codec_type', 'unknown')
                            codec = s.get('codec_name', 'unknown')
                            
                            if stype == 'video':
                                video_count += 1
                                w = s.get('width', 0)
                                h = s.get('height', 0)
                                vbr = int(s.get('bit_rate', 0) or 0) // 1000
                                youtube_helpers_logger.info(
                                    f"  📺 Video Stream #{video_count}: "
                                    f"codec={codec}, resolution={w}x{h}, bitrate={vbr}kbps"
                                )
                            elif stype == 'audio':
                                audio_count += 1
                                abr = int(s.get('bit_rate', 0) or 0) // 1000
                                youtube_helpers_logger.info(
                                    f"  🔊 Audio Stream #{audio_count}: "
                                    f"codec={codec}, bitrate={abr}kbps"
                                )
                        
                        # نتیجه نهایی
                        youtube_helpers_logger.info("")
                        youtube_helpers_logger.info(f"✅ خلاصه: {video_count} video + {audio_count} audio streams")
                        
                        # هشدارها
                        if video_count == 0:
                            youtube_helpers_logger.error("❌ هیچ stream ویدیویی یافت نشد!")
                        if audio_count == 0:
                            youtube_helpers_logger.warning("⚠️ هیچ stream صوتی یافت نشد!")
                        
                        # مقایسه حجم
                        if size_meta > 0:
                            diff_mb = abs(file_size - size_meta) / (1024*1024)
                            if diff_mb > 1:
                                youtube_helpers_logger.warning(
                                    f"⚠️ اختلاف حجم: {diff_mb:.2f} MB "
                                    f"(file={file_size/(1024*1024):.2f}MB vs meta={size_meta/(1024*1024):.2f}MB)"
                                )
                        
                        youtube_helpers_logger.info("="*60)
                        
                    else:
                        youtube_helpers_logger.warning(f"⚠️ ffprobe failed: {result.stderr}")
                        
            except Exception as e:
                youtube_helpers_logger.debug(f"خطا در بررسی metadata: {e}")
        
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
    """دریافت لینک مستقیم دانلود"""
    try:
        youtube_helpers_logger.info(f"دریافت لینک مستقیم: {url} با فرمت {format_id}")
        
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
        youtube_helpers_logger.error(f"خطا در ویرایش پیام: {e}")