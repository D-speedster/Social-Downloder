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
        progress_callback: Optional[Callable] = None
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
            
            # yt-dlp options
            ydl_opts = {
                'format': format_string,
                'outtmpl': output_path,
                'quiet': True,
                'no_warnings': True,
                'progress_hooks': [progress_hook] if progress_callback else [],
                # Merge video+audio if needed
                'merge_output_format': 'mp4',
                # Use ffmpeg for merging
                'postprocessor_args': [
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    '-b:a', '128k'
                ],
                # Optimize for speed
                'concurrent_fragment_downloads': 4,
                'http_chunk_size': 10485760,  # 10MB chunks
            }
            
            # Add cookies if file exists
            if os.path.exists(cookie_file):
                ydl_opts['cookiefile'] = cookie_file
                logger.info(f"Using cookies from: {cookie_file}")
            
            logger.info(f"Starting download: {url} with format {format_string}")
            
            # Run download in executor to avoid blocking
            loop = asyncio.get_event_loop()
            
            def _download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                return output_path
            
            result_path = await loop.run_in_executor(None, _download)
            
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
