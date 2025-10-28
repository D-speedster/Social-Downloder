"""
YouTube Downloader - دانلود بهینه با yt-dlp
"""

import os
import asyncio
import tempfile
from typing import Optional, Callable
from plugins.logger_config import get_logger
import yt_dlp

logger = get_logger('youtube_downloader')

class YouTubeDownloader:
    """کلاس دانلود از یوتیوب"""
    
    def __init__(self):
        self.download_dir = tempfile.gettempdir()
    
    async def download(
        self,
        url: str,
        format_string: str,
        output_filename: str,
        progress_callback: Optional[Callable] = None,
        is_audio_only: bool = False
    ) -> Optional[str]:
        """
        دانلود ویدیو با yt-dlp
        
        Args:
            url: لینک یوتیوب
            format_string: فرمت مورد نظر (مثل "137+140" یا "251")
            output_filename: نام فایل خروجی
            progress_callback: تابع callback برای نمایش پیشرفت
        
        Returns:
            مسیر فایل دانلود شده یا None در صورت خطا
        """
        try:
            output_path = os.path.join(self.download_dir, output_filename)
            
            # Remove existing file
            if os.path.exists(output_path):
                try:
                    os.unlink(output_path)
                except:
                    pass
            
            # Progress hook for yt-dlp
            def progress_hook(d):
                if progress_callback and d['status'] == 'downloading':
                    try:
                        downloaded = d.get('downloaded_bytes', 0)
                        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                        
                        if total > 0:
                            progress_callback(downloaded, total)
                    except Exception as e:
                        logger.debug(f"Progress callback error: {e}")
            
            # Check for cookie file
            cookie_file = 'cookie_youtube.txt'
            
            # yt-dlp options with maximum stability
            ydl_opts = {
                'format': format_string,
                'outtmpl': output_path,
                'quiet': True,
                'no_warnings': True,
                'progress_hooks': [progress_hook] if progress_callback else [],
                # Network stability improvements
                'retries': 10,                   # افزایش تلاش مجدد به 10 بار
                'fragment_retries': 20,          # افزایش تلاش مجدد fragment ها
                'retry_sleep_functions': {       # زمان انتظار بین تلاش‌ها
                    'http': lambda n: min(3 * (2 ** n), 30),
                    'fragment': lambda n: min(2 * (2 ** n), 20),
                },
                # Connection settings - حداکثر پایداری
                'http_chunk_size': 524288,       # کاهش بیشتر به 512KB
                'concurrent_fragment_downloads': 1,  # فقط 1 fragment همزمان
                'socket_timeout': 60,            # افزایش timeout به 60s
                'read_timeout': 60,              # افزایش timeout به 60s
                # Disable problematic features
                'no_check_certificate': True,    # نادیده گرفتن مشکلات SSL
                'prefer_insecure': False,        # استفاده از HTTPS
                # Additional stability options
                'keepvideo': False,              # حذف فایل ویدیو بعد از merge
                'ignoreerrors': False,           # توقف در صورت خطا
                'nocheckcertificate': False,     # بررسی certificate
            }
            
            # تنظیمات مخصوص فایل‌های صوتی
            if is_audio_only:
                ydl_opts.update({
                    # استفاده از format selector عمومی‌تر برای صوت
                    'format': 'bestaudio/best',  # بهترین صوت موجود
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'merge_output_format': 'mp3',
                })
            else:
                # تنظیمات مخصوص ویدیو
                ydl_opts.update({
                    'merge_output_format': 'mp4',
                    'postprocessor_args': [
                        '-c:v', 'copy',
                        '-c:a', 'aac',
                        '-b:a', '128k'
                    ],
                })
            
            # Add cookies if file exists
            if os.path.exists(cookie_file):
                ydl_opts['cookiefile'] = cookie_file
                logger.info(f"Using cookies from: {cookie_file}")
            
            logger.info(f"Starting download: {url} with format {format_string}")
            
            # Run download in executor with retry logic
            loop = asyncio.get_event_loop()
            
            def _download_with_retry():
                max_attempts = 3
                
                # لیست format های fallback برای صوت
                format_fallbacks = []
                if is_audio_only:
                    format_fallbacks = ['bestaudio/best', 'bestaudio', 'best']
                
                for attempt in range(max_attempts):
                    try:
                        logger.info(f"Download attempt {attempt + 1}/{max_attempts}")
                        
                        # Remove partial file if exists
                        if os.path.exists(output_path):
                            try:
                                os.unlink(output_path)
                            except:
                                pass
                        
                        # در تلاش آخر برای صوت، از format ساده‌تر استفاده کن
                        current_opts = ydl_opts.copy()
                        if is_audio_only and attempt == max_attempts - 1:
                            logger.info("Last attempt: using simplified format selector")
                            current_opts['format'] = 'worst'  # کیفیت پایین‌تر ولی پایدارتر
                        
                        with yt_dlp.YoutubeDL(current_opts) as ydl:
                            ydl.download([url])
                        
                        # Check if file was created successfully
                        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                            logger.info(f"Download successful on attempt {attempt + 1}")
                            return output_path
                        else:
                            raise Exception("Downloaded file is empty or missing")
                            
                    except Exception as e:
                        error_msg = str(e).lower()
                        logger.warning(f"Download attempt {attempt + 1} failed: {e}")
                        
                        # Check for "did not get any data blocks" specifically
                        if 'did not get any data blocks' in error_msg:
                            logger.error("Fragment download failed - this is a known YouTube issue")
                            
                            if attempt < max_attempts - 1:
                                wait_time = (attempt + 1) * 3  # 3, 6, 9 seconds
                                logger.info(f"Waiting {wait_time} seconds before retry...")
                                import time
                                time.sleep(wait_time)
                                
                                # پاک کردن تمام فایل‌های موقت
                                import glob
                                temp_files = glob.glob(f"{output_path}.*")
                                for temp_file in temp_files:
                                    try:
                                        os.unlink(temp_file)
                                        logger.info(f"Cleaned up temp file: {temp_file}")
                                    except:
                                        pass
                                continue
                        
                        # Check for other retryable errors
                        elif any(keyword in error_msg for keyword in [
                            'connection reset',
                            'timeout',
                            'network',
                            'temporary failure'
                        ]):
                            if attempt < max_attempts - 1:
                                wait_time = (attempt + 1) * 2  # 2, 4, 6 seconds
                                logger.info(f"Retrying in {wait_time} seconds...")
                                import time
                                time.sleep(wait_time)
                                continue
                        
                        # If it's the last attempt or non-retryable error, raise
                        if attempt == max_attempts - 1:
                            raise e
                
                raise Exception("All download attempts failed")
            
            result_path = await loop.run_in_executor(None, _download_with_retry)
            
            # Verify file exists
            if os.path.exists(result_path) and os.path.getsize(result_path) > 0:
                logger.info(f"Download completed: {result_path} ({os.path.getsize(result_path)} bytes)")
                return result_path
            else:
                logger.error(f"Download failed: file not found or empty")
                return None
                
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None
    
    def cleanup(self, file_path: str):
        """حذف فایل دانلود شده"""
        try:
            if file_path and os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"Cleaned up: {file_path}")
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")

# Global instance
youtube_downloader = YouTubeDownloader()
