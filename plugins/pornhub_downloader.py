"""
Pornhub Downloader - دانلود با yt-dlp (مشابه YouTube)
"""

import os
import asyncio
import tempfile
import time
import glob
import concurrent.futures
from typing import Optional

from plugins.logger_config import get_logger
import yt_dlp

logger = get_logger('pornhub_downloader')

# ThreadPoolExecutor برای اجرای همزمان
_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=4,
    thread_name_prefix="ph_worker"
)


class PornhubDownloader:
    """کلاس دانلود از Pornhub با yt-dlp"""
    
    def __init__(self):
        self.download_dir = tempfile.gettempdir()
    
    async def extract_info(self, url: str) -> Optional[dict]:
        """استخراج اطلاعات ویدیو بدون دانلود"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True,
            }
            
            loop = asyncio.get_running_loop()
            
            def _extract():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)
            
            info = await loop.run_in_executor(_executor, _extract)
            return info
        
        except Exception as e:
            logger.error(f"Extract info error: {e}")
            return None
    
    async def download(
        self,
        url: str,
        format_string: str,
        output_filename: str
    ) -> Optional[str]:
        """
        دانلود ویدیو با yt-dlp
        
        Args:
            url: لینک Pornhub
            format_string: فرمت مورد نظر
            output_filename: نام فایل خروجی
        
        Returns:
            مسیر فایل دانلود شده یا None
        """
        try:
            output_path = os.path.join(self.download_dir, output_filename)
            
            # حذف فایل قبلی اگر وجود دارد
            if os.path.exists(output_path):
                try:
                    os.unlink(output_path)
                except:
                    pass
            
            # تنظیمات yt-dlp
            ydl_opts = {
                'format': format_string,
                'outtmpl': output_path,
                'quiet': True,
                'no_warnings': True,
                
                # بهینه‌سازی سرعت
                'concurrent_fragment_downloads': 4,
                'http_chunk_size': 5242880,  # 5MB
                'buffersize': 16384,  # 16KB
                
                # پایداری شبکه
                'retries': 10,
                'fragment_retries': 15,
                'socket_timeout': 45,
                'read_timeout': 45,
                
                # SSL
                'no_check_certificate': True,
                
                # مدیریت فایل
                'keepvideo': False,
                'ignoreerrors': False,
                'merge_output_format': 'mp4',
            }
            
            logger.info(f"Starting download: {url} with format {format_string}")
            
            loop = asyncio.get_running_loop()
            
            def _download_with_retry():
                max_attempts = 3
                
                for attempt in range(max_attempts):
                    try:
                        logger.info(f"Download attempt {attempt + 1}/{max_attempts}")
                        
                        # حذف فایل موقت
                        if os.path.exists(output_path):
                            try:
                                os.unlink(output_path)
                            except:
                                pass
                        
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([url])
                        
                        # بررسی موفقیت
                        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                            logger.info(f"Download successful on attempt {attempt + 1}")
                            return output_path
                        else:
                            raise Exception("Downloaded file is empty or missing")
                    
                    except KeyboardInterrupt:
                        logger.warning("Download interrupted by user")
                        raise
                    
                    except Exception as e:
                        error_msg = str(e).lower()
                        logger.warning(f"Download attempt {attempt + 1} failed: {e}")
                        
                        # بررسی خطاهای قابل retry
                        if 'did not get any data blocks' in error_msg:
                            logger.error("Fragment download failed")
                            
                            if attempt < max_attempts - 1:
                                wait_time = (attempt + 1) * 3
                                logger.info(f"Waiting {wait_time} seconds before retry...")
                                time.sleep(wait_time)
                                
                                # پاک‌سازی فایل‌های موقت
                                try:
                                    temp_files = glob.glob(f"{output_path}.*")
                                    for temp_file in temp_files:
                                        try:
                                            os.unlink(temp_file)
                                        except:
                                            pass
                                except:
                                    pass
                                continue
                        
                        elif any(keyword in error_msg for keyword in [
                            'connection reset', 'timeout', 'network', 'temporary failure'
                        ]):
                            if attempt < max_attempts - 1:
                                wait_time = (attempt + 1) * 2
                                logger.info(f"Retrying in {wait_time} seconds...")
                                time.sleep(wait_time)
                                continue
                        
                        # آخرین تلاش
                        if attempt == max_attempts - 1:
                            raise e
                
                raise Exception("All download attempts failed")
            
            download_start = time.time()
            result_path = await loop.run_in_executor(_executor, _download_with_retry)
            download_time = time.time() - download_start
            
            # بررسی نهایی
            if os.path.exists(result_path) and os.path.getsize(result_path) > 0:
                file_size_mb = os.path.getsize(result_path) / (1024 * 1024)
                speed_mbps = file_size_mb / download_time if download_time > 0 else 0
                logger.info(
                    f"✅ Download completed: {file_size_mb:.2f} MB "
                    f"in {download_time:.2f}s ({speed_mbps:.2f} MB/s)"
                )
                return result_path
            else:
                logger.error("Download failed: file not found or empty")
                # پاک‌سازی
                try:
                    temp_files = glob.glob(f"{output_path}.*")
                    for temp_file in temp_files:
                        try:
                            os.unlink(temp_file)
                        except:
                            pass
                except:
                    pass
                return None
        
        except KeyboardInterrupt:
            logger.warning("Download interrupted by user at top level")
            raise
        
        except Exception as e:
            logger.error(f"Download error: {e}")
            # پاک‌سازی
            try:
                if 'output_path' in locals():
                    temp_files = glob.glob(f"{output_path}.*")
                    for temp_file in temp_files:
                        try:
                            os.unlink(temp_file)
                        except:
                            pass
            except:
                pass
            return None
    
    def cleanup(self, file_path: str):
        """حذف فایل دانلود شده"""
        try:
            if file_path and os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"Cleaned up: {file_path}")
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")


# نمونه سراسری
pornhub_downloader = PornhubDownloader()
