"""
Stream utilities for optimized file handling and direct streaming to Telegram
"""
import asyncio
import aiohttp
import io
import os
import requests
import shutil
import subprocess
import json
from typing import BinaryIO, Union, Optional
# youtube_helpers removed - using new system
from plugins.logger_config import get_logger, get_performance_logger
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from config import TELEGRAM_THROTTLING
from plugins.media_utils import send_advertisement


class StreamBuffer(io.BytesIO):
    """
    A BytesIO buffer that can be used for in-memory file uploads to Telegram
    """
    def __init__(self, name: str):
        super().__init__()
        self.name = name


async def download_to_memory_stream(url: str, max_size_mb: int = 50, headers=None) -> Optional[StreamBuffer]:
    """
    Download file directly to memory for small files (< max_size_mb)
    Returns a StreamBuffer that can be used directly with Pyrogram send methods
    """
    try:
        # Use custom headers if provided, otherwise use default
        if headers is None:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        
        # Dynamic timeout based on expected file size
        timeout_seconds = min(60, max(15, max_size_mb * 2))
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout_seconds)) as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                
                # Check content length
                content_length = response.headers.get('content-length')
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    if size_mb > max_size_mb:
                        return None  # File too large for memory streaming
                
                # Extract filename from URL or use default
                filename = url.split('/')[-1].split('?')[0] or 'media_file'
                
                # Create memory buffer
                buffer = StreamBuffer(filename)
                
                # Stream content to memory
                async for chunk in response.content.iter_chunked(64 * 1024):
                    buffer.write(chunk)
                    # Safety check for memory usage
                    if buffer.tell() > max_size_mb * 1024 * 1024:
                        buffer.close()
                        return None
                
                buffer.seek(0)  # Reset position for reading
                return buffer
                
    except Exception as e:
        print(f"Memory streaming error: {e}")
        return None


async def download_to_memory_stream_requests(url: str, max_size_mb: int = 50) -> Optional[StreamBuffer]:
    """
    Fallback: Download file to memory using requests (sync) with stream=True.
    Runs in a thread to avoid blocking the event loop.
    """
    def _sync() -> Optional[StreamBuffer]:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            with requests.Session() as session:
                # timeout=(connect, read)
                with session.get(url, headers=headers, stream=True, timeout=(10, max(30, max_size_mb))) as resp:
                    resp.raise_for_status()
                    content_length = resp.headers.get('content-length')
                    if content_length:
                        size_mb = int(content_length) / (1024 * 1024)
                        if size_mb > max_size_mb:
                            return None
                    filename = url.split('/')[-1].split('?')[0] or 'media_file'
                    buffer = StreamBuffer(filename)
                    for chunk in resp.iter_content(chunk_size=64 * 1024):
                        if not chunk:
                            continue
                        buffer.write(chunk)
                        if buffer.tell() > max_size_mb * 1024 * 1024:
                            buffer.close()
                            return None
                    buffer.seek(0)
                    return buffer
        except Exception as e:
            print(f"Requests memory streaming error: {e}")
            return None
    return await asyncio.to_thread(_sync)


async def download_with_progress_callback(url: str, file_path: str, progress_callback=None) -> str:
    """
    Download file with progress callback support for Pyrogram
    """
    try:
        # Headers to mimic a real browser and avoid 403 errors
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Start with a reasonable timeout, will be adjusted based on actual file size
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                total_size_mb = total_size / (1024 * 1024) if total_size > 0 else 0
                downloaded = 0
                
                # Optimize chunk size based on file size
                chunk_size = optimize_chunk_size(total_size_mb)
                
                with open(file_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Call progress callback if provided
                        if progress_callback and total_size > 0:
                            try:
                                # Format progress data for YouTube callback
                                progress_data = {
                                    'status': 'downloading',
                                    'downloaded_bytes': downloaded,
                                    'total_bytes': total_size,
                                    'speed': 0,
                                    'eta': 0
                                }
                                progress_callback(progress_data)
                            except Exception:
                                pass  # Don't let progress callback errors stop download
                
                return file_path
                
    except Exception as e:
        print(f"Download with progress error: {e}")
        raise


def optimize_chunk_size(file_size_mb: float) -> int:
    """
    Optimize chunk size based on file size for better performance
    """
    if file_size_mb < 1:
        return 32 * 1024  # 32KB for small files
    elif file_size_mb < 10:
        return 64 * 1024  # 64KB for medium files
    elif file_size_mb < 50:
        return 128 * 1024  # 128KB for large files
    else:
        return 256 * 1024  # 256KB for very large files


def calculate_upload_delay(file_size_mb: float, chunk_count: int) -> float:
    """
    Calculate optimal delay between chunks to avoid Telegram throttling
    """
    # 🔥 حذف کامل تأخیرها برای سرعت حداکثری
    return 0.0  # بدون تأخیر برای تمام فایل‌ها


async def throttled_upload_with_retry(upload_func, max_retries=None, base_delay=None):
    """
    اجرای تابع آپلود با مکانیزم تلاش مجدد - فوق سریع
    """
    if max_retries is None:
        max_retries = 1  # کاهش بیشتر تعداد تلاش‌ها
    if base_delay is None:
        base_delay = 0.2  # کاهش بیشتر تأخیر پایه
        
    for attempt in range(max_retries + 1):
        try:
            return await upload_func()
        except Exception as e:
            # فقط برای FloodWait retry کن، بقیه خطاها فوراً raise شوند
            error_str = str(e).lower()
            
            if 'flood' in error_str and hasattr(e, 'seconds'):
                print(f"FloodWait: Waiting {e.seconds} seconds...")
                await asyncio.sleep(e.seconds)
                continue
            
            # برای سایر خطاها، فقط یک بار retry کن
            if attempt < max_retries and any(keyword in error_str for keyword in ['timeout', 'connection']):
                wait_time = base_delay
                print(f"Upload error: {e}. Quick retry in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                continue
            
            # در غیر این صورت، فوراً خطا را raise کن
            raise
    
    return None


# 🔥 تابع جدید برای استخراج metadata
def extract_video_metadata(file_path: str) -> dict:
    """
    استخراج metadata کامل از ویدیو با ffprobe و لاگ‌گیری کامل
    """
    logger = get_logger('stream_utils')
    
    try:
        logger.info(f"📊 Starting metadata extraction for: {os.path.basename(file_path)}")
        
        # بررسی وجود فایل
        if not os.path.exists(file_path):
            logger.error(f"❌ File not found: {file_path}")
            return {}
        
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        logger.info(f"📁 File size: {file_size_mb:.2f} MB")
        
        # پیدا کردن ffprobe
        ffprobe_path = os.environ.get('FFMPEG_PATH', 'ffmpeg').replace('ffmpeg', 'ffprobe')
        logger.info(f"🔍 Initial ffprobe path: {ffprobe_path}")
        
        if not os.path.exists(ffprobe_path):
            ffprobe_path = shutil.which('ffprobe') or 'ffprobe'
            logger.info(f"🔍 ffprobe from PATH: {ffprobe_path}")
        
        if not ffprobe_path or not os.path.exists(ffprobe_path):
            logger.error("❌ ffprobe not found")
            return {}
        
        cmd = [
            ffprobe_path, '-v', 'error',
            '-show_entries', 'format=duration:stream=width,height,codec_type,duration',
            '-of', 'json',
            file_path
        ]
        
        logger.info(f"🔧 ffprobe command: {' '.join(cmd)}")
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=10)
        end_time = time.time()
        
        logger.info(f"⏱️ ffprobe execution time: {end_time - start_time:.2f}s")
        logger.info(f"🔍 ffprobe return code: {result.returncode}")
        
        if result.stderr:
            logger.warning(f"⚠️ ffprobe stderr: {result.stderr}")
        
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                logger.info(f"📋 Raw ffprobe data: {data}")
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON decode error: {e}")
                return {}
            
            metadata = {
                'duration': 0,
                'width': 0,
                'height': 0,
                'has_video': False,
                'has_audio': False
            }
            
            format_data = data.get('format', {})
            logger.info(f"📊 Format data: {format_data}")
            
            if 'duration' in format_data:
                try:
                    metadata['duration'] = int(float(format_data['duration']))
                    logger.info(f"⏱️ Duration from format: {metadata['duration']}s")
                except Exception as e:
                    logger.warning(f"⚠️ Duration parsing error: {e}")
            
            streams = data.get('streams', [])
            logger.info(f"🎬 Found {len(streams)} streams")
            
            for i, stream in enumerate(streams):
                codec_type = stream.get('codec_type', '')
                logger.info(f"🔍 Stream {i}: type={codec_type}, data={stream}")
                
                if codec_type == 'video':
                    metadata['has_video'] = True
                    if 'width' in stream and not metadata['width']:
                        metadata['width'] = int(stream['width'])
                        logger.info(f"📐 Width: {metadata['width']}")
                    if 'height' in stream and not metadata['height']:
                        metadata['height'] = int(stream['height'])
                        logger.info(f"📐 Height: {metadata['height']}")
                    if not metadata['duration'] and 'duration' in stream:
                        try:
                            metadata['duration'] = int(float(stream['duration']))
                            logger.info(f"⏱️ Duration from video stream: {metadata['duration']}s")
                        except Exception as e:
                            logger.warning(f"⚠️ Stream duration parsing error: {e}")
                
                elif codec_type == 'audio':
                    metadata['has_audio'] = True
                    logger.info("🔊 Audio stream detected")
            
            logger.info(f"✅ Final metadata: {metadata}")
            print(f"📊 Metadata extracted: {metadata}")
            return metadata
        else:
            logger.error(f"❌ ffprobe failed with return code {result.returncode}")
            logger.error(f"❌ ffprobe stderr: {result.stderr}")
            print(f"❌ ffprobe failed: {result.stderr}")
            return {}
            
    except subprocess.TimeoutExpired:
        logger.error("❌ ffprobe timeout after 10 seconds")
        print("❌ Metadata extraction timeout")
        return {}
    except Exception as e:
        logger.error(f"❌ Metadata extraction error: {e}")
        print(f"❌ Metadata extraction error: {e}")
        return {}


# 🔥 تابع جدید برای ساخت thumbnail
def generate_thumbnail(file_path: str) -> str:
    """
    ساخت سریع thumbnail از ویدیو با لاگ‌گیری کامل
    """
    logger = get_logger('stream_utils')
    
    try:
        logger.info(f"🎬 Starting thumbnail generation for: {os.path.basename(file_path)}")
        
        # بررسی اینکه آیا thumbnail قبلاً وجود دارد
        thumb_path = file_path.rsplit('.', 1)[0] + '_thumb.jpg'
        if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0:
            logger.info(f"✅ Existing thumbnail found: {thumb_path}")
            return thumb_path
        
        # پیدا کردن FFmpeg
        ffmpeg_path = os.environ.get('FFMPEG_PATH')
        logger.info(f"🔍 FFMPEG_PATH from env: {ffmpeg_path}")
        
        if not ffmpeg_path:
            try:
                from config import FFMPEG_PATH as CFG_FFMPEG
                ffmpeg_path = CFG_FFMPEG
                logger.info(f"🔍 FFMPEG_PATH from config: {ffmpeg_path}")
            except Exception as e:
                logger.warning(f"⚠️ Could not load FFMPEG_PATH from config: {e}")
                ffmpeg_path = None
        
        if not ffmpeg_path or not os.path.exists(ffmpeg_path):
            ffmpeg_path = shutil.which('ffmpeg')
            logger.info(f"🔍 FFmpeg from PATH: {ffmpeg_path}")
        
        if not ffmpeg_path:
            logger.error("❌ FFmpeg not found in any location")
            print("❌ FFmpeg not found, skipping thumbnail")
            return None
        
        # بررسی دسترسی به فایل ورودی
        if not os.path.exists(file_path):
            logger.error(f"❌ Input file not found: {file_path}")
            return None
        
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        logger.info(f"📊 Input file size: {file_size_mb:.2f} MB")
        
        # دستور بهینه‌سازی شده برای سرعت بالا
        cmd = [
            ffmpeg_path, '-y',
            '-ss', '1',  # کاهش زمان seek
            '-i', file_path,
            '-vframes', '1',
            '-vf', 'scale=320:-2',  # سایز کوچک‌تر برای سرعت
            '-q:v', '5',  # کیفیت متوسط برای سرعت
            '-f', 'image2',
            thumb_path
        ]
        
        logger.info(f"🔧 FFmpeg command: {' '.join(cmd)}")
        
        # timeout کوتاه‌تر برای جلوگیری از کندی
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, timeout=8, 
                              encoding='utf-8', errors='ignore')
        end_time = time.time()
        
        logger.info(f"⏱️ FFmpeg execution time: {end_time - start_time:.2f}s")
        logger.info(f"🔍 FFmpeg return code: {result.returncode}")
        
        if result.stdout:
            logger.info(f"📝 FFmpeg stdout: {result.stdout}")
        if result.stderr:
            logger.warning(f"⚠️ FFmpeg stderr: {result.stderr}")
        
        if result.returncode == 0 and os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0:
            thumb_size = os.path.getsize(thumb_path)
            logger.info(f"✅ Thumbnail created successfully: {thumb_path} ({thumb_size} bytes)")
            print(f"✅ Thumbnail created: {thumb_path}")
            return thumb_path
        else:
            logger.error(f"❌ Thumbnail generation failed - return code: {result.returncode}")
            if os.path.exists(thumb_path):
                thumb_size = os.path.getsize(thumb_path)
                logger.error(f"❌ Thumbnail file exists but size is: {thumb_size} bytes")
            print(f"❌ Thumbnail generation failed")
            return None
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Thumbnail generation timeout after 8 seconds")
        print("❌ Thumbnail generation timeout")
        return None
    except Exception as e:
        logger.error(f"❌ Thumbnail generation error: {e}")
        print(f"❌ Thumbnail error: {e}")
        return None


# 🔥 تابع smart_upload_strategy اصلاح شده
async def smart_upload_strategy(client, chat_id: int, file_path: str, media_type: str, **kwargs) -> bool:
    """
    بهینه‌سازی شده برای سرعت بالا با حفظ metadata ضروری و لاگ‌گیری کامل
    """
    logger = get_logger('stream_utils')
    
    file_size = os.path.getsize(file_path)
    file_size_mb = file_size / (1024 * 1024)
    
    logger.info(f"🚀 Starting smart upload: {os.path.basename(file_path)} ({file_size_mb:.2f} MB, type: {media_type})")
    
    progress_callback = kwargs.pop('progress', None)
    
    # برای ویدیوهای یوتیوب، metadata و thumbnail ضروری است
    if media_type == "video" and file_size_mb > 1:  # فقط برای ویدیوهای بزرگتر از 1MB
        logger.info("🎬 Video detected, extracting metadata and thumbnail...")
        
        try:
            # استخراج سریع metadata
            metadata_start = time.time()
            metadata = extract_video_metadata(file_path)
            metadata_time = time.time() - metadata_start
            
            logger.info(f"⏱️ Metadata extraction took: {metadata_time:.2f}s")
            
            if metadata:
                if 'duration' not in kwargs and metadata.get('duration'):
                    kwargs['duration'] = metadata['duration']
                    logger.info(f"⏱️ Added duration: {metadata['duration']}s")
                if 'width' not in kwargs and metadata.get('width'):
                    kwargs['width'] = metadata['width']
                    logger.info(f"📐 Added width: {metadata['width']}px")
                if 'height' not in kwargs and metadata.get('height'):
                    kwargs['height'] = metadata['height']
                    logger.info(f"📐 Added height: {metadata['height']}px")
            else:
                logger.warning("⚠️ No metadata extracted")
            
            # ساخت thumbnail سریع اگر وجود ندارد
            if 'thumb' not in kwargs:
                logger.info("🖼️ Generating thumbnail...")
                thumb_start = time.time()
                thumb_path = generate_thumbnail(file_path)
                thumb_time = time.time() - thumb_start
                
                logger.info(f"⏱️ Thumbnail generation took: {thumb_time:.2f}s")
                
                if thumb_path:
                    kwargs['thumb'] = thumb_path
                    logger.info(f"✅ Thumbnail added: {thumb_path}")
                else:
                    logger.warning("⚠️ Thumbnail generation failed")
            else:
                logger.info("🖼️ Thumbnail already provided")
                
        except Exception as e:
            logger.error(f"❌ Metadata/thumbnail extraction failed: {e}")
            print(f"Metadata extraction failed, continuing without: {e}")
    else:
        logger.info(f"📄 Non-video or small file, skipping metadata extraction")
    
    # لاگ کردن تنظیمات نهایی آپلود
    upload_settings = {k: v for k, v in kwargs.items() if k not in ['thumb']}  # حذف thumb از لاگ برای خوانایی
    if 'thumb' in kwargs:
        upload_settings['thumb'] = f"<thumbnail: {os.path.basename(kwargs['thumb'])}>"
    logger.info(f"📋 Upload settings: {upload_settings}")
    
    async def perform_upload():
        upload_kwargs = kwargs.copy()
        if progress_callback:
            upload_kwargs['progress'] = progress_callback
        
        logger.info(f"📤 Starting {media_type} upload...")
        upload_start = time.time()
        
        # آپلود مستقیم بدون تأخیر اضافی
        if media_type == "video":
            # اضافه کردن supports_streaming برای بهبود پخش
            upload_kwargs['supports_streaming'] = True
            result = await client.send_video(chat_id=chat_id, video=file_path, **upload_kwargs)
        elif media_type == "photo":
            result = await client.send_photo(chat_id=chat_id, photo=file_path, **upload_kwargs)
        elif media_type == "audio":
            result = await client.send_audio(chat_id=chat_id, audio=file_path, **upload_kwargs)
        else:
            result = await client.send_document(chat_id=chat_id, document=file_path, **upload_kwargs)
        
        upload_time = time.time() - upload_start
        logger.info(f"✅ Upload completed in {upload_time:.2f}s")
        
        return result
    
    try:
        # آپلود مستقیم بدون retry اضافی برای سرعت بالا
        total_start = time.time()
        await perform_upload()
        total_time = time.time() - total_start
        
        logger.info(f"🎉 Smart upload successful! Total time: {total_time:.2f}s")
        return True
        
    except Exception as e:
        logger.error(f"❌ Smart upload failed: {e}")
        print(f"Smart upload failed: {e}")
        
        # فقط یک بار retry در صورت خطا
        try:
            logger.info("🔄 Retrying upload after 0.5s...")
            await asyncio.sleep(0.5)
            await perform_upload()
            
            total_time = time.time() - total_start
            logger.info(f"✅ Smart upload retry successful! Total time: {total_time:.2f}s")
            return True
            
        except Exception as e2:
            logger.error(f"❌ Smart upload retry failed: {e2}")
            print(f"Smart upload retry failed: {e2}")
            return False


async def direct_youtube_upload(client, chat_id: int, url: str, quality_info: dict, title: str = "", thumbnail_url: str = None, progress_callback=None, **kwargs) -> dict:
    """
    Direct YouTube upload without saving to server storage
    Downloads and uploads simultaneously for maximum efficiency
    """
    import tempfile
    
    # Initialize loggers
    stream_utils_logger = get_logger('stream_utils')
    performance_logger = get_performance_logger()
    
    # Initialize timing variables
    start_time = time.time()
    url_resolution_time = None
    download_time = None
    upload_time = None
    ad_enabled = False
    ad_position = 'after'
    try:
        try:
            from plugins.db_path_manager import db_path_manager
        except Exception:
            from .db_path_manager import db_path_manager
        json_db_path = db_path_manager.get_json_db_path()
        with open(json_db_path, 'r', encoding='utf-8') as f:
            db_data = json.load(f)
        ad = db_data.get('advertisement', {})
        ad_enabled = ad.get('enabled', False)
        ad_position = ad.get('position', 'after')
    except Exception:
        stream_utils_logger.warning("⚠️ Failed to load advertisement settings; skipping ads.")
        pass
    
    # Extract format_id and media_type from quality_info
    format_id = quality_info.get('format_id', '')
    media_type = 'audio' if quality_info.get('type') == 'audio_only' else 'video'
    
    stream_utils_logger.info(f"📋 Media type: {media_type}, Format ID: {format_id}")
    
    # Phase 1: Resolve direct download URL
    url_start = time.time()
    stream_utils_logger.info("🔍 Phase 1: Resolving direct download URL...")
    
    direct_url = await get_direct_download_url(url, format_id)
    url_resolution_time = time.time() - url_start
    
    if not direct_url:
        stream_utils_logger.error("❌ Failed to resolve direct download URL")
        raise Exception("No direct URL found")
    
    stream_utils_logger.info(f"✅ URL resolved in {url_resolution_time:.2f}s")
    performance_logger.info(f"[URL_RESOLUTION_TIME] {url_resolution_time:.2f}s")
    
    # If video, skip direct streaming and use yt-dlp traditional path
    if media_type == "video":
        stream_utils_logger.info("🎬 Video detected; using yt-dlp traditional path for proper metadata.")
        performance_logger.info("[DIRECT_UPLOAD_SKIP] Using traditional yt-dlp path for video")
        
        from plugins.youtube_downloader import youtube_downloader
        safe_title = "".join(c for c in (title or "video") if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
        filename = f"{safe_title}.mp4"
        downloaded_file = await youtube_downloader.download(url, format_id, filename, None)
        
        if not downloaded_file or not os.path.exists(downloaded_file):
            return {"success": False, "error": "Download failed in traditional path"}
        
        # Extract robust metadata and thumbnail for better Telegram display
        from plugins.universal_downloader import _extract_video_metadata as _extract_video_metadata_local
        video_meta = _extract_video_metadata_local(downloaded_file)
        duration = video_meta.get('duration', 0) or None
        width = video_meta.get('width', 0) or None
        height = video_meta.get('height', 0) or None
        thumb_to_cleanup = video_meta.get('thumbnail')
        
        upload_kwargs = kwargs.copy()
        upload_kwargs['caption'] = f"🎬 {title}" if title else "🎬 Video"
        # 🔥 حذف supports_streaming برای سرعت بالا
        if duration:
            upload_kwargs['duration'] = int(duration)
        if width:
            upload_kwargs['width'] = width
        if height:
            upload_kwargs['height'] = height
        if thumb_to_cleanup and os.path.exists(thumb_to_cleanup):
            upload_kwargs['thumb'] = thumb_to_cleanup

        if ad_enabled and ad_position == 'before':
            send_advertisement(client, chat_id)
            # حذف تأخیر غیرضروری
        
        # آپلود مستقیم بدون تأخیر
        message = await client.send_video(chat_id=chat_id, video=downloaded_file, **upload_kwargs)

        if ad_enabled and ad_position == 'after':
            # کاهش تأخیر به حداقل
            await asyncio.sleep(0.2)
            send_advertisement(client, chat_id)
        
        total_time = time.time() - start_time
        performance_logger.info(f"[TOTAL_TRADITIONAL_VIDEO_TIME] {total_time:.2f}s")
        
        # Cleanup
        try:
            os.unlink(downloaded_file)
            temp_dir = os.path.dirname(downloaded_file)
            # Remove generated thumbnail if present
            if 'thumb_to_cleanup' in locals() and thumb_to_cleanup and os.path.exists(thumb_to_cleanup):
                try:
                    os.unlink(thumb_to_cleanup)
                except Exception:
                    pass
            if os.path.exists(temp_dir) and os.path.basename(temp_dir).startswith('tmp'):
                import shutil as _sh
                _sh.rmtree(temp_dir, ignore_errors=True)
        except Exception as cleanup_err:
            stream_utils_logger.warning(f"⚠️ Cleanup failed: {cleanup_err}")
        
        return {"success": True, "message": message, "fallback_used": True, "total_time": total_time}
    
    # Early decision: force traditional path for large/unsupported videos
    direct_fallback_threshold_mb = int(kwargs.pop('direct_fallback_threshold_mb', 100))
    force_traditional = bool(kwargs.pop('force_traditional', False))
    if media_type == 'video':
        # برای حفظ متادیتا و پیش‌نمایش، از مسیر سنتی استفاده شود
        force_traditional = True
    content_length = 0
    content_type = ''
    
    # Phase 2: Check content headers
    stream_utils_logger.info("📊 Phase 2: Checking content headers...")
    header_check_start = time.time()
    
    try:
        timeout = aiohttp.ClientTimeout(total=8)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request('HEAD', direct_url, headers={'User-Agent': 'Mozilla/5.0'}) as resp:
                content_length = int(resp.headers.get('Content-Length') or 0)
                content_type = resp.headers.get('Content-Type', '')
                
        header_check_time = time.time() - header_check_start
        file_size_mb = content_length / (1024 * 1024) if content_length > 0 else 0
        
        stream_utils_logger.info(f"📏 File size: {file_size_mb:.2f} MB, Content-Type: {content_type}")
        stream_utils_logger.info(f"⏱️ Header check completed in {header_check_time:.2f}s")
        performance_logger.info(f"[HEADER_CHECK_TIME] {header_check_time:.2f}s, Size: {file_size_mb:.2f}MB")
        
    except Exception as e:
        stream_utils_logger.warning(f"⚠️ Header check failed: {e}")
    
    # Determine strategy based on file size
    memory_threshold_mb = 50
    if file_size_mb > direct_fallback_threshold_mb or force_traditional:
        stream_utils_logger.info(f"📁 File too large ({file_size_mb:.2f}MB > {direct_fallback_threshold_mb}MB), using temp file strategy")
    else:
        stream_utils_logger.info(f"💾 File size acceptable ({file_size_mb:.2f}MB), attempting memory streaming")
    
    # Phase 3: Attempt memory streaming first (for smaller files)
    if file_size_mb <= memory_threshold_mb and not force_traditional:
        stream_utils_logger.info("🧠 Phase 3a: Attempting memory streaming...")
        memory_start = time.time()
        
        try:
            memory_buffer = await download_to_memory_stream(direct_url, max_size_mb=memory_threshold_mb)
        except Exception as e:
            stream_utils_logger.warning(f"⚠️ aiohttp memory streaming failed: {e}")
            memory_buffer = None
        
        if not memory_buffer:
            try:
                memory_buffer = await download_to_memory_stream_requests(direct_url, max_size_mb=memory_threshold_mb)
            except Exception as e:
                stream_utils_logger.warning(f"⚠️ requests memory streaming failed: {e}")
                memory_buffer = None
        
        if memory_buffer:
            memory_download_time = time.time() - memory_start
            stream_utils_logger.info(f"✅ Memory download completed in {memory_download_time:.2f}s")
            performance_logger.info(f"[MEMORY_DOWNLOAD_TIME] {memory_download_time:.2f}s")
            
            # Phase 4a: Memory upload
            upload_start = time.time()
            stream_utils_logger.info("📤 Phase 4a: Starting memory upload...")
            
            upload_kwargs = kwargs.copy()
            upload_kwargs['caption'] = f"🎬 {title}" if title else "🎬 Video"
            
            try:
                if ad_enabled and ad_position == 'before':
                    await send_advertisement(client, chat_id)
                    await asyncio.sleep(0.5)  # کاهش تأخیر
                if media_type == "video":
                    # 🔥 حذف supports_streaming برای سرعت بالا
                    message = await client.send_video(chat_id=chat_id, video=memory_buffer, **upload_kwargs)
                elif media_type == "audio":
                    message = await client.send_audio(chat_id=chat_id, audio=memory_buffer, **upload_kwargs)
                else:
                    message = await client.send_document(chat_id=chat_id, document=memory_buffer, **upload_kwargs)
                    
                upload_time = time.time() - upload_start
                total_time = time.time() - start_time
                
                stream_utils_logger.info(f"✅ Memory upload completed in {upload_time:.2f}s")
                stream_utils_logger.info(f"🎉 Total process completed in {total_time:.2f}s (Memory strategy)")
                performance_logger.info(f"[MEMORY_UPLOAD_TIME] {upload_time:.2f}s")
                performance_logger.info(f"[TOTAL_MEMORY_PROCESS_TIME] {total_time:.2f}s")
                
                if ad_enabled and ad_position == 'after':
                    await asyncio.sleep(1)
                    send_advertisement(client, chat_id)
                memory_buffer.close()
                return {"success": True, "message": message, "in_memory": True, "total_time": total_time}
                
            except Exception as req_upload_err:
                stream_utils_logger.error(f"❌ Memory upload failed: {req_upload_err}")
                performance_logger.error(f"[MEMORY_UPLOAD_ERROR] {str(req_upload_err)}")
                try:
                    memory_buffer.close()
                except Exception:
                    pass

    # Phase 3b: Use temp file approach
    stream_utils_logger.info("📁 Phase 3b: Using temporary file strategy...")
    temp_file_start = time.time()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as temp_file:
        temp_path = temp_file.name
        
        stream_utils_logger.info(f"📂 Created temp file: {temp_path}")
        
        try:
            # Download to temp file with progress callback
            download_start = time.time()
            stream_utils_logger.info("⬇️ Starting download to temp file...")
            
            await download_with_progress_callback(direct_url, temp_path, progress_callback)
            
            download_time = time.time() - download_start
            file_size = os.path.getsize(temp_path) / (1024 * 1024)
            
            stream_utils_logger.info(f"✅ Download completed in {download_time:.2f}s, File size: {file_size:.2f}MB")
            performance_logger.info(f"[TEMP_DOWNLOAD_TIME] {download_time:.2f}s, Size: {file_size:.2f}MB")
            
            # Phase 4b: Upload from temp file
            upload_start = time.time()
            stream_utils_logger.info("📤 Phase 4b: Starting upload from temp file...")
            
            upload_kwargs = kwargs.copy()
            upload_kwargs['caption'] = f"🎬 {title}" if title else "🎬 Video"
            
            # Optional remux to MP4 with faststart to preserve metadata
            upload_source_path = temp_path
            if media_type == "video":
                try:
                    content_is_mp4 = ('mp4' in (content_type or '').lower()) or (str(quality_info.get('ext','')).lower() == 'mp4')
                    ffmpeg_path = os.environ.get('FFMPEG_PATH') or shutil.which('ffmpeg')
                    if ffmpeg_path and content_is_mp4:
                        remuxed_path = temp_path + ".mp4"
                        remux_start = time.time()
                        import subprocess
                        result = subprocess.run(
                            [ffmpeg_path, '-y', '-i', temp_path, '-c', 'copy', '-movflags', '+faststart', remuxed_path],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE
                        )
                        if result.returncode == 0 and os.path.exists(remuxed_path) and os.path.getsize(remuxed_path) > 0:
                            remux_time = time.time() - remux_start
                            stream_utils_logger.info(f"🎞️ Remuxed to faststart in {remux_time:.2f}s")
                            upload_source_path = remuxed_path
                        else:
                            stream_utils_logger.warning("⚠️ Remux failed, using original file")
                    else:
                        if not ffmpeg_path:
                            stream_utils_logger.info("ℹ️ FFmpeg not found; uploading original file")
                except Exception as remux_err:
                    stream_utils_logger.warning(f"⚠️ Remux error, uploading original file: {remux_err}")
            
            if ad_enabled and ad_position == 'before':
                send_advertisement(client, chat_id)
                await asyncio.sleep(0.5)  # کاهش تأخیر
            if media_type == "video":
                # 🔥 حذف supports_streaming برای سرعت بالا
                message = await client.send_video(chat_id=chat_id, video=upload_source_path, **upload_kwargs)
            elif media_type == "audio":
                message = await client.send_audio(chat_id=chat_id, audio=upload_source_path, **upload_kwargs)
            else:
                message = await client.send_document(chat_id=chat_id, document=upload_source_path, **upload_kwargs)
            
            upload_time = time.time() - upload_start
            total_time = time.time() - start_time
            
            stream_utils_logger.info(f"✅ Upload completed in {upload_time:.2f}s")
            stream_utils_logger.info(f"🎉 Total process completed in {total_time:.2f}s (Temp file strategy)")
            performance_logger.info(f"[TEMP_UPLOAD_TIME] {upload_time:.2f}s")
            performance_logger.info(f"[TOTAL_TEMP_PROCESS_TIME] {total_time:.2f}s")
            
            if ad_enabled and ad_position == 'after':
                await asyncio.sleep(1)
                send_advertisement(client, chat_id)
            
            return {"success": True, "message": message, "total_time": total_time}
            
        except Exception as e:
            error_time = time.time() - start_time
            stream_utils_logger.error(f"❌ Direct YouTube upload failed after {error_time:.2f}s: {e}")
            
            # Fallback to traditional download method
            try:
                fallback_start = time.time()
                stream_utils_logger.info("🔄 Falling back to traditional download method...")
                performance_logger.info("[FALLBACK_START] Traditional download method")
                
                from plugins.youtube_downloader import youtube_downloader
                
                # Download using traditional method
                safe_title = "".join(c for c in (title or "video") if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
                filename = f"{safe_title}.mp4"
                downloaded_file = await youtube_downloader.download(url, format_id, filename, None)
                
                if downloaded_file and os.path.exists(downloaded_file):
                    fallback_download_time = time.time() - fallback_start
                    file_size = os.path.getsize(downloaded_file) / (1024 * 1024)
                    
                    stream_utils_logger.info(f"✅ Fallback download completed in {fallback_download_time:.2f}s, Size: {file_size:.2f}MB")
                    performance_logger.info(f"[FALLBACK_DOWNLOAD_TIME] {fallback_download_time:.2f}s, Size: {file_size:.2f}MB")
                    
                    try:
                        # Upload the downloaded file
                        upload_start = time.time()
                        stream_utils_logger.info("📤 Starting fallback upload...")
                        
                        upload_kwargs = kwargs.copy()
                        upload_kwargs['caption'] = f"🎬 {title}" if title else "🎬 Video"
                        
                        if ad_enabled and ad_position == 'before':
                            send_advertisement(client, chat_id)
                            await asyncio.sleep(0.5)  # کاهش تأخیر
                        if media_type == "video":
                            # 🔥 حذف supports_streaming برای سرعت بالا
                            message = await client.send_video(chat_id=chat_id, video=downloaded_file, **upload_kwargs)
                        elif media_type == "audio":
                            message = await client.send_audio(chat_id=chat_id, audio=downloaded_file, **upload_kwargs)
                        else:
                            message = await client.send_document(chat_id=chat_id, document=downloaded_file, **upload_kwargs)
                        
                        upload_time = time.time() - upload_start
                        total_time = time.time() - start_time
                        
                        stream_utils_logger.info(f"✅ Fallback upload completed in {upload_time:.2f}s")
                        stream_utils_logger.info(f"🎉 Total fallback process completed in {total_time:.2f}s")
                        performance_logger.info(f"[FALLBACK_UPLOAD_TIME] {upload_time:.2f}s")
                        performance_logger.info(f"[TOTAL_FALLBACK_PROCESS_TIME] {total_time:.2f}s")
                        
                        if ad_enabled and ad_position == 'after':
                            await asyncio.sleep(1)
                            send_advertisement(client, chat_id)
                        
                        return {"success": True, "message": message, "fallback_used": True, "total_time": total_time}
                        
                    finally:
                        # Clean up downloaded file
                        cleanup_start = time.time()
                        try:
                            os.unlink(downloaded_file)
                            # Also clean up the temp directory if it exists
                            temp_dir = os.path.dirname(downloaded_file)
                            if os.path.exists(temp_dir) and os.path.basename(temp_dir).startswith('tmp'):
                                import shutil
                                shutil.rmtree(temp_dir, ignore_errors=True)
                            cleanup_time = time.time() - cleanup_start
                            stream_utils_logger.info(f"🧹 Fallback cleanup completed in {cleanup_time:.3f}s")
                        except Exception as cleanup_err:
                            stream_utils_logger.warning(f"⚠️ Fallback cleanup failed: {cleanup_err}")
                else:
                    return {"success": False, "error": "Fallback download failed"}
            except Exception as fb_err:
                stream_utils_logger.error(f"❌ Fallback method failed: {fb_err}")
                return {"success": False, "error": str(fb_err)}
        
        finally:
            # Clean up temp file
            cleanup_start = time.time()
            try:
                os.unlink(temp_path)
                if 'upload_source_path' in locals() and upload_source_path != temp_path:
                    try:
                        os.unlink(upload_source_path)
                    except Exception as e2:
                        stream_utils_logger.warning(f"⚠️ Remuxed file cleanup failed: {e2}")
                cleanup_time = time.time() - cleanup_start
                stream_utils_logger.info(f"🧹 Temp file cleanup completed in {cleanup_time:.3f}s")
            except Exception as e:
                stream_utils_logger.warning(f"⚠️ Temp file cleanup failed: {e}")


async def concurrent_download_upload(client, chat_id: int, download_url: str, file_name: str, 
                                   media_type: str = "document", progress_callback=None, 
                                   chunk_size: int = 1024*1024, **kwargs) -> dict:
    """
    دانلود و آپلود همزمان برای حداکثر کارایی
    Downloads and uploads simultaneously using streaming
    """
    logger = get_logger('stream_utils')
    performance_logger = get_performance_logger()
    
    start_time = time.time()
    
    try:
        # ایجاد یک فایل موقت برای streaming
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_name)[1]) as temp_file:
            temp_path = temp_file.name
            
            # شروع دانلود در background
            download_task = asyncio.create_task(
                _stream_download_to_file(download_url, temp_path, progress_callback, chunk_size)
            )
            
            # صبر کردن تا حداقل 5MB دانلود شود قبل شروع آپلود
            await asyncio.sleep(2)  # 2 ثانیه صبر برای شروع دانلود
            
            # بررسی اینکه آیا فایل شروع به دانلود شده
            while not os.path.exists(temp_path) or os.path.getsize(temp_path) < 1024*1024:  # 1MB
                if download_task.done():
                    break
                await asyncio.sleep(0.5)
            
            # شروع آپلود همزمان با دانلود با throttling
            upload_kwargs = kwargs.copy()
            if progress_callback:
                upload_kwargs['progress'] = progress_callback
            
            # 🔥 حذف throttling برای سرعت بالا
            
            # تعریف تابع آپلود بدون تأخیر
            async def perform_concurrent_upload():
                if media_type == "video":
                    return await client.send_video(chat_id=chat_id, video=temp_path, **upload_kwargs)
                elif media_type == "audio":
                    return await client.send_audio(chat_id=chat_id, audio=temp_path, **upload_kwargs)
                else:
                    return await client.send_document(chat_id=chat_id, document=temp_path, **upload_kwargs)
            
            # آپلود مستقیم بدون retry اضافی
            upload_task = asyncio.create_task(perform_concurrent_upload())
            
            # انتظار برای تکمیل هر دو عملیات
            download_result, upload_result = await asyncio.gather(
                download_task, upload_task, return_exceptions=True
            )
            
            # بررسی نتایج
            if isinstance(download_result, Exception):
                raise download_result
            if isinstance(upload_result, Exception):
                raise upload_result
                
            total_time = time.time() - start_time
            performance_logger.info(f"Concurrent download/upload completed in {total_time:.2f}s")
            
            # حذف فایل موقت
            try:
                os.unlink(temp_path)
            except:
                pass
                
            return {
                "success": True,
                "message": upload_result,
                "download_time": download_result.get("time", 0),
                "total_time": total_time
            }
            
    except Exception as e:
        logger.error(f"Concurrent download/upload failed: {e}")
        return {"success": False, "error": str(e)}


async def fast_upload_video(client, chat_id: int, file_path: str, caption: str = "", **kwargs) -> bool:
    """
    🚀 آپلود فوق سریع ویدیو بدون metadata اضافی
    """
    try:
        # حذف تمام تنظیمات اضافی که باعث کندی می‌شوند
        upload_kwargs = {
            'caption': caption,
            'file_name': os.path.basename(file_path)
        }
        
        # اضافه کردن progress callback اگر موجود باشد
        if 'progress' in kwargs:
            upload_kwargs['progress'] = kwargs['progress']
        
        # آپلود مستقیم بدون هیچ تأخیری
        message = await client.send_video(
            chat_id=chat_id, 
            video=file_path, 
            **upload_kwargs
        )
        
        return True
    except Exception as e:
        print(f"Fast upload failed: {e}")
        return False


async def _stream_download_to_file(url: str, file_path: str, progress_callback=None, chunk_size: int = 1024*1024) -> dict:
    """
    دانلود streaming به فایل با progress callback
    """
    start_time = time.time()
    downloaded_size = 0
    
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=3600, connect=30),
            connector=aiohttp.TCPConnector(limit=10, limit_per_host=5)
        ) as session:
            async with session.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }) as response:
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                
                with open(file_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # فراخوانی progress callback
                        if progress_callback and total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            try:
                                await progress_callback(downloaded_size, total_size)
                            except:
                                pass  # ignore callback errors
                
                download_time = time.time() - start_time
                return {
                    "success": True,
                    "size": downloaded_size,
                    "time": download_time,
                    "speed_mbps": (downloaded_size / (1024*1024)) / download_time if download_time > 0 else 0
                }
                
    except Exception as e:
        return {"success": False, "error": str(e)}