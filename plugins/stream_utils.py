"""
Stream utilities for optimized file handling and direct streaming to Telegram
"""
import asyncio
import aiohttp
import io
import os
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
        # Dynamic timeout based on expected file size
        timeout_seconds = min(60, max(15, max_size_mb * 2))
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout_seconds)) as session:
            async with session.get(url) as response:
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


async def download_with_progress_callback(url: str, file_path: str, progress_callback=None) -> str:
    """
    Download file with progress callback support for Pyrogram
    """
    try:
        # Start with a reasonable timeout, will be adjusted based on actual file size
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
            async with session.get(url) as response:
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
                                await progress_callback(downloaded, total_size)
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