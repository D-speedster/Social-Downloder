"""
Stream utilities for optimized file handling and direct streaming to Telegram
"""
import asyncio
import aiohttp
import io
import os
import requests
from typing import BinaryIO, Union, Optional


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


async def smart_upload_strategy(client, chat_id: int, file_path: str, media_type: str, **kwargs) -> bool:
    """
    Smart upload strategy with optimized retry and timeout handling
    Returns True if upload was successful, False otherwise
    """
    file_size = os.path.getsize(file_path)
    file_size_mb = file_size / (1024 * 1024)
    
    # Determine retry strategy based on file size
    max_attempts = 2 if file_size_mb > 50 else 3
    base_delay = 0.5 if file_size_mb > 20 else 0.8
    
    for attempt in range(max_attempts):
        try:
            # For small files (< 10MB), try memory streaming first
            if file_size_mb < 10 and attempt == 0:
                try:
                    with open(file_path, 'rb') as f:
                        buffer = StreamBuffer(os.path.basename(file_path))
                        buffer.write(f.read())
                        buffer.seek(0)
                        
                        if media_type == "video":
                            await client.send_video(chat_id=chat_id, video=buffer, **kwargs)
                        elif media_type == "photo":
                            await client.send_photo(chat_id=chat_id, photo=buffer, **kwargs)
                        elif media_type == "audio":
                            await client.send_audio(chat_id=chat_id, audio=buffer, **kwargs)
                        else:
                            await client.send_document(chat_id=chat_id, document=buffer, **kwargs)
                        
                        buffer.close()
                        return True
                except Exception as e:
                    print(f"Memory upload failed, falling back to file upload: {e}")
                    # Continue to file upload fallback
            
            # Regular file upload with optimized settings
            def _sanitize_upload_kwargs(src: dict) -> dict:
                """Remove None/invalid values and normalize types for Telegram API."""
                dst = {}
                for k, v in src.items():
                    if v is None:
                        continue
                    if k in ("width", "height", "duration"):
                        try:
                            iv = int(v)
                        except (TypeError, ValueError):
                            continue
                        if iv <= 0:
                            continue
                        dst[k] = iv
                    elif k == "supports_streaming":
                        dst[k] = bool(v)
                    else:
                        dst[k] = v
                return dst

            upload_kwargs = _sanitize_upload_kwargs(kwargs.copy())
            
            # Enable streaming for videos
            if media_type == "video":
                upload_kwargs['supports_streaming'] = True
                await client.send_video(chat_id=chat_id, video=file_path, **upload_kwargs)
            elif media_type == "photo":
                await client.send_photo(chat_id=chat_id, photo=file_path, **upload_kwargs)
            elif media_type == "audio":
                await client.send_audio(chat_id=chat_id, audio=file_path, **upload_kwargs)
            else:
                await client.send_document(chat_id=chat_id, document=file_path, **upload_kwargs)
            
            return True
            
        except Exception as e:
            print(f"Smart upload attempt {attempt+1}/{max_attempts} failed: {e}")
            
            # Don't retry on the last attempt
            if attempt < max_attempts - 1:
                # Exponential backoff with jitter
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
    
    return False


async def direct_youtube_upload(client, chat_id: int, url: str, quality_info: dict, title: str = "", thumbnail_url: str = None, progress_callback=None, **kwargs) -> dict:
    """
    Direct YouTube upload without saving to server storage
    Downloads and uploads simultaneously for maximum efficiency
    """
    import yt_dlp
    import tempfile
    from plugins.cookie_manager import get_cookie_file_with_fallback, get_rotated_cookie_file, mark_cookie_used
    
    try:
        # Extract format_id and media_type from quality_info
        format_id = quality_info.get('format_id', '')
        media_type = 'audio' if quality_info.get('type') == 'audio_only' else 'video'
        
        # Configure yt-dlp options for direct streaming
        def _get_env_proxy():
            return os.environ.get('PROXY') or os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')
        env_proxy = _get_env_proxy()

        # Get direct download URL from yt-dlp without downloading
        ydl_opts = {
            'format': format_id,
            'noplaylist': True,
            'extract_flat': False,
            'socket_timeout': 30,
            'retries': 3,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'prefer_insecure': True,
            'force_ipv4': True,
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

        cookie_id_used = None
        
        # Try to get cookie file
        try:
            cookiefile, cid = get_cookie_file_with_fallback(None)
            if cookiefile:
                ydl_opts['cookiefile'] = cookiefile
                cookie_id_used = cid
        except Exception:
            pass

        # Extract info and get direct URL
        def extract_info_sync():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        
        try:
            info = await asyncio.to_thread(extract_info_sync)
        except Exception as first_err:
            # Try with different cookie if needed
            msg = str(first_err).lower()
            needs_cookie = any(h in msg for h in ['login required', 'sign in', 'age', 'restricted', 'private'])
            format_not_available = 'requested format is not available' in msg
            
            if needs_cookie and not cookie_id_used:
                try:
                    cookiefile, cid = get_rotated_cookie_file(cookie_id_used)
                    if cookiefile:
                        ydl_opts['cookiefile'] = cookiefile
                        cookie_id_used = cid
                        info = await asyncio.to_thread(extract_info_sync)
                    else:
                        raise first_err
                except Exception:
                    raise first_err
            elif format_not_available:
                # Try to find a fallback format
                try:
                    from plugins.youtube_helpers import find_best_fallback_format
                    fallback_format = await find_best_fallback_format(url, format_id)
                    if fallback_format and fallback_format != format_id:
                        print(f"Format {format_id} not available, trying fallback format: {fallback_format}")
                        ydl_opts['format'] = fallback_format
                        info = await asyncio.to_thread(extract_info_sync)
                        format_id = fallback_format  # Update format_id for later use
                    else:
                        raise first_err
                except ImportError:
                    raise first_err
                except Exception as fallback_err:
                    print(f"Fallback format search failed: {fallback_err}")
                    raise first_err
            else:
                raise first_err

        # Find the requested format
        if 'formats' in info:
            selected_format = None
            for fmt in info['formats']:
                if fmt.get('format_id') == format_id:
                    selected_format = fmt
                    break
            
            if not selected_format or not selected_format.get('url'):
                raise Exception(f"Format {format_id} not found or has no direct URL")
            
            direct_url = selected_format['url']
            file_size = selected_format.get('filesize') or selected_format.get('filesize_approx', 0)
            file_size_mb = file_size / (1024 * 1024) if file_size else 0
            
        elif info.get('url'):
            # Single format
            direct_url = info['url']
            file_size = info.get('filesize') or info.get('filesize_approx', 0)
            file_size_mb = file_size / (1024 * 1024) if file_size else 0
        else:
            raise Exception("No direct URL found")

        # Mark cookie as successful if used
        if cookie_id_used:
            try:
                mark_cookie_used(cookie_id_used, True)
            except Exception:
                pass

        # Try in-memory streaming first (no disk usage)
        memory_threshold_mb = int(kwargs.pop('memory_threshold_mb', 50))
        try:
            memory_buffer = await download_to_memory_stream(direct_url, max_size_mb=memory_threshold_mb)
        except Exception:
            memory_buffer = None
        
        if memory_buffer:
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
                
                memory_buffer.close()
                return {"success": True, "message": message, "in_memory": True}
            except Exception as mem_upload_err:
                print(f"In-memory upload failed, will try requests fallback: {mem_upload_err}")
                try:
                    memory_buffer.close()
                except Exception:
                    pass
        
        # Fallback: memory streaming via requests
        try:
            memory_buffer = await download_to_memory_stream_requests(direct_url, max_size_mb=memory_threshold_mb)
        except Exception:
            memory_buffer = None
        
        if memory_buffer:
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
                
                memory_buffer.close()
                return {"success": True, "message": message, "in_memory": True}
            except Exception as req_upload_err:
                print(f"Requests in-memory upload failed, will fallback to temp file: {req_upload_err}")
                try:
                    memory_buffer.close()
                except Exception:
                    pass

        # Use temp file approach as a last resort (ephemeral, deleted immediately)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as temp_file:
            temp_path = temp_file.name
        
        try:
            # Download to temp file with progress callback
            await download_with_progress_callback(direct_url, temp_path, progress_callback)
            
            # Upload from temp file
            upload_kwargs = kwargs.copy()
            upload_kwargs['caption'] = f"🎬 {title}" if title else "🎬 Video"
            
            if media_type == "video":
                upload_kwargs['supports_streaming'] = True
                message = await client.send_video(chat_id=chat_id, video=temp_path, **upload_kwargs)
            elif media_type == "audio":
                message = await client.send_audio(chat_id=chat_id, audio=temp_path, **upload_kwargs)
            else:
                message = await client.send_document(chat_id=chat_id, document=temp_path, **upload_kwargs)
            
            return {"success": True, "message": message}
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except Exception:
                pass

    except Exception as e:
        print(f"Direct YouTube upload failed: {e}")
        # Mark cookie as failed if used
        if 'cookie_id_used' in locals() and cookie_id_used:
            try:
                mark_cookie_used(cookie_id_used, False)
            except Exception:
                pass
        
        # Fallback to traditional download method
        try:
            print("Falling back to traditional download method...")
            from plugins.youtube_helpers import download_youtube_file
            
            # Download using traditional method
            downloaded_file = await download_youtube_file(url, format_id, progress_callback)
            
            if downloaded_file and os.path.exists(downloaded_file):
                try:
                    # Upload the downloaded file
                    upload_kwargs = kwargs.copy()
                    upload_kwargs['caption'] = f"🎬 {title}" if title else "🎬 Video"
                    
                    if media_type == "video":
                        upload_kwargs['supports_streaming'] = True
                        message = await client.send_video(chat_id=chat_id, video=downloaded_file, **upload_kwargs)
                    elif media_type == "audio":
                        message = await client.send_audio(chat_id=chat_id, audio=downloaded_file, **upload_kwargs)
                    else:
                        message = await client.send_document(chat_id=chat_id, document=downloaded_file, **upload_kwargs)
                    
                    return {"success": True, "message": message, "fallback_used": True}
                    
                finally:
                    # Clean up downloaded file
                    try:
                        os.unlink(downloaded_file)
                        # Also clean up the temp directory if it exists
                        temp_dir = os.path.dirname(downloaded_file)
                        if os.path.exists(temp_dir) and os.path.basename(temp_dir).startswith('tmp'):
                            import shutil
                            shutil.rmtree(temp_dir, ignore_errors=True)
                    except Exception:
                        pass
            else:
                return {"success": False, "error": "Fallback download failed - no file downloaded"}
                
        except Exception as fallback_error:
            print(f"Fallback download also failed: {fallback_error}")
            return {"success": False, "error": f"Both direct upload and fallback failed. Direct: {str(e)}, Fallback: {str(fallback_error)}"}