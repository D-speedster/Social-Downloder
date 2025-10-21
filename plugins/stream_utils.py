"""
Stream utilities for optimized file handling and direct streaming to Telegram
"""
import asyncio
import aiohttp
import io
import os
import requests
import shutil
from typing import BinaryIO, Union, Optional
from plugins.youtube_helpers import get_direct_download_url
from plugins.logger_config import get_logger, get_performance_logger
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from config import TELEGRAM_THROTTLING


class StreamBuffer(io.BytesIO):
    """
    A BytesIO buffer that can be used for in-memory file uploads to Telegram
    """
    def __init__(self, name: str):
        super().__init__()
        self.name = name


async def download_to_memory_stream(url: str, max_size_mb: int = 50) -> Optional[StreamBuffer]:
    """
    Download file directly to memory for small files (< max_size_mb)
    Returns a StreamBuffer that can be used directly with Pyrogram send methods
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
    # Base delay for large files
    if file_size_mb > 100:
        return TELEGRAM_THROTTLING['upload_delay_large']  # delay for very large files
    elif file_size_mb > 50:
        return TELEGRAM_THROTTLING['upload_delay_large']  # delay for large files
    elif file_size_mb > 20:
        return TELEGRAM_THROTTLING['upload_delay_medium']  # delay for medium files
    else:
        return TELEGRAM_THROTTLING['upload_delay_small']  # delay for small files


async def throttled_upload_with_retry(upload_func, max_retries=None, base_delay=None):
    """
    اجرای تابع آپلود با مکانیزم تلاش مجدد exponential backoff
    """
    if max_retries is None:
        max_retries = TELEGRAM_THROTTLING['retry_attempts']
    if base_delay is None:
        base_delay = TELEGRAM_THROTTLING['base_retry_delay']
        
    for attempt in range(max_retries + 1):
        try:
            return await upload_func()
        except FloodWaitError as e:
            if attempt == max_retries:
                print(f"FloodWaitError: Maximum retries reached. Waiting {e.seconds} seconds...")
                await asyncio.sleep(e.seconds)
                raise
            
            wait_time = min(e.seconds, base_delay * (2 ** attempt))
            print(f"FloodWaitError: Waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
            await asyncio.sleep(wait_time)
            
        except SlowModeWaitError as e:
            if attempt == max_retries:
                print(f"SlowModeWaitError: Maximum retries reached. Waiting {e.seconds} seconds...")
                await asyncio.sleep(e.seconds)
                raise
            
            wait_time = min(e.seconds, base_delay * (2 ** attempt))
            print(f"SlowModeWaitError: Waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
            await asyncio.sleep(wait_time)
            
        except Exception as e:
            if attempt == max_retries:
                print(f"Upload failed after {max_retries} retries: {e}")
                raise
            
            wait_time = base_delay * (2 ** attempt)
            print(f"Upload error: {e}. Retrying in {wait_time} seconds...")
            await asyncio.sleep(wait_time)
    
    return None


async def smart_upload_strategy(client, chat_id: int, file_path: str, media_type: str, **kwargs) -> bool:
    """
    Smart upload strategy with optimized retry and timeout handling
    Returns True if upload was successful, False otherwise
    """
    file_size = os.path.getsize(file_path)
    file_size_mb = file_size / (1024 * 1024)
    
    # استخراج progress callback از kwargs
    progress_callback = kwargs.pop('progress', None)
    
    # Calculate optimal delay for throttling
    upload_delay = calculate_upload_delay(file_size_mb, 1)
    
    # Define upload function for throttled retry
    async def perform_upload():
        # For small files (< 10MB), try memory streaming first
        if file_size_mb < 10:
            try:
                with open(file_path, 'rb') as f:
                    buffer = StreamBuffer(os.path.basename(file_path))
                    buffer.write(f.read())
                    buffer.seek(0)
                    
                    # اضافه کردن progress callback اگر موجود باشد
                    upload_kwargs = kwargs.copy()
                    if progress_callback:
                        upload_kwargs['progress'] = progress_callback
                    
                    if media_type == "video":
                        result = await client.send_video(chat_id=chat_id, video=buffer, **upload_kwargs)
                    elif media_type == "photo":
                        result = await client.send_photo(chat_id=chat_id, photo=buffer, **upload_kwargs)
                    elif media_type == "audio":
                        result = await client.send_audio(chat_id=chat_id, audio=buffer, **upload_kwargs)
                    else:
                        result = await client.send_document(chat_id=chat_id, document=buffer, **upload_kwargs)
                    
                    buffer.close()
                    return result
            except Exception as e:
                print(f"Memory upload failed, falling back to file upload: {e}")
        
        # File-based upload with progress callback
        upload_kwargs = kwargs.copy()
        if progress_callback:
            upload_kwargs['progress'] = progress_callback
        
        # Add throttling delay before upload
        if upload_delay > 0:
            await asyncio.sleep(upload_delay)
        
        # تنظیمات بهینه برای آپلود فایل
        if media_type == "video":
            return await client.send_video(chat_id=chat_id, video=file_path, **upload_kwargs)
        elif media_type == "photo":
            return await client.send_photo(chat_id=chat_id, photo=file_path, **upload_kwargs)
        elif media_type == "audio":
            return await client.send_audio(chat_id=chat_id, audio=file_path, **upload_kwargs)
        else:
            return await client.send_document(chat_id=chat_id, document=file_path, **upload_kwargs)
    
    # Use throttled upload with retry
    try:
        await throttled_upload_with_retry(perform_upload, max_retries=3, base_delay=upload_delay)
        return True
    except Exception as e:
        print(f"Smart upload failed after all retries: {e}")
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
    
    try:
        stream_utils_logger.info(f"🚀 Starting direct YouTube upload process for: {title[:50]}...")
        performance_logger.info(f"[DIRECT_UPLOAD_START] URL: {url}, Quality: {quality_info.get('format_id', 'unknown')}")
        
        # Extract format_id and media_type from quality_info
        format_id = quality_info.get('format_id', '')
        media_type = 'audio' if quality_info.get('type') == 'audio_only' else 'video'
        
        stream_utils_logger.info(f"📋 Media type: {media_type}, Format ID: {format_id}")
        
        # Phase 1: Resolve direct download URL
        url_start = time.time()
        stream_utils_logger.info("🔍 Phase 1: Resolving direct download URL...")
        
        direct_url = await get_direct_download_url(url, preferred_format_id=format_id)
        url_resolution_time = time.time() - url_start
        
        if not direct_url:
            stream_utils_logger.error("❌ Failed to resolve direct download URL")
            raise Exception("No direct URL found")
        
        stream_utils_logger.info(f"✅ URL resolved in {url_resolution_time:.2f}s")
        performance_logger.info(f"[URL_RESOLUTION_TIME] {url_resolution_time:.2f}s")
        
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
                    if media_type == "video":
                        upload_kwargs['supports_streaming'] = True
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
            
            if media_type == "video":
                upload_kwargs['supports_streaming'] = True
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
            
            return {"success": True, "message": message, "total_time": total_time}
            
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

    except Exception as e:
        error_time = time.time() - start_time
        stream_utils_logger.error(f"❌ Direct YouTube upload failed after {error_time:.2f}s: {e}")
        performance_logger.error(f"[DIRECT_UPLOAD_ERROR] Time: {error_time:.2f}s, Error: {str(e)}")
        
        # Fallback to traditional download method
        try:
            fallback_start = time.time()
            stream_utils_logger.info("🔄 Falling back to traditional download method...")
            performance_logger.info("[FALLBACK_START] Traditional download method")
            
            from plugins.youtube_helpers import download_youtube_file
            
            # Download using traditional method
            downloaded_file = await download_youtube_file(url, format_id, progress_callback)
            
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
                    
                    if media_type == "video":
                        upload_kwargs['supports_streaming'] = True
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
                stream_utils_logger.error("❌ Fallback download failed - no file downloaded")
                performance_logger.error("[FALLBACK_DOWNLOAD_FAILED] No file downloaded")
                return {"success": False, "error": "Fallback download failed - no file downloaded"}
                
        except Exception as fallback_error:
            fallback_time = time.time() - start_time
            stream_utils_logger.error(f"❌ Fallback download also failed after {fallback_time:.2f}s: {fallback_error}")
            performance_logger.error(f"[FALLBACK_ERROR] Time: {fallback_time:.2f}s, Error: {str(fallback_error)}")
            return {"success": False, "error": f"Both direct upload and fallback failed. Direct: {str(e)}, Fallback: {str(fallback_error)}"}


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
            
            # محاسبه تأخیر برای throttling
            file_size_mb = os.path.getsize(temp_path) / (1024 * 1024) if os.path.exists(temp_path) else 10
            upload_delay = calculate_upload_delay(file_size_mb, 1)
            
            # تعریف تابع آپلود با throttling
            async def perform_concurrent_upload():
                if upload_delay > 0:
                    await asyncio.sleep(upload_delay)
                    
                if media_type == "video":
                    return await client.send_video(chat_id=chat_id, video=temp_path, **upload_kwargs)
                elif media_type == "audio":
                    return await client.send_audio(chat_id=chat_id, audio=temp_path, **upload_kwargs)
                else:
                    return await client.send_document(chat_id=chat_id, document=temp_path, **upload_kwargs)
            
            # استفاده از throttled upload
            upload_task = asyncio.create_task(
                throttled_upload_with_retry(perform_concurrent_upload, max_retries=2, base_delay=upload_delay)
            )
            
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