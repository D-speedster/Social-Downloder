"""
Cookie Validator Service - سرویس خودکار بررسی سلامت کوکی یوتیوب

این سرویس هر 3 ساعت یک بار کوکی یوتیوب را با یک تست دانلود بررسی می‌کند
و نتیجه را به ادمین‌ها اطلاع می‌دهد.
"""

import asyncio
import os
import time
import logging
from datetime import datetime
from typing import Optional, Tuple
from pyrogram import Client
import yt_dlp

# Configure logger
os.makedirs('./logs', exist_ok=True)
cookie_logger = logging.getLogger('cookie_validator')
cookie_logger.setLevel(logging.INFO)

cookie_handler = logging.FileHandler('./logs/cookie_validator.log', encoding='utf-8')
cookie_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
cookie_handler.setFormatter(cookie_formatter)
cookie_logger.addHandler(cookie_handler)

# Constants
COOKIE_CHECK_INTERVAL = 3 * 60 * 60  # 3 ساعت به ثانیه
TEST_VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # ویدیو تست
COOKIE_FILE_PATH = "cookie_youtube.txt"
VALIDATION_TIMEOUT = 30  # ثانیه


class CookieValidator:
    """
    سرویس بررسی خودکار سلامت کوکی یوتیوب
    """
    
    def __init__(self, client: Client, admin_ids: list):
        """
        Args:
            client: Pyrogram client
            admin_ids: لیست ID ادمین‌ها
        """
        self.client = client
        self.admin_ids = admin_ids
        self.check_interval = COOKIE_CHECK_INTERVAL
        self.test_video_url = TEST_VIDEO_URL
        self.cookie_file = COOKIE_FILE_PATH
        self.is_running = False
        self._task = None
        
        cookie_logger.info("Cookie Validator initialized")
        cookie_logger.info(f"Check interval: {self.check_interval}s ({self.check_interval/3600:.1f} hours)")
        cookie_logger.info(f"Test video: {self.test_video_url}")
        cookie_logger.info(f"Cookie file: {self.cookie_file}")
        cookie_logger.info(f"Admin IDs: {self.admin_ids}")
    
    async def start(self):
        """شروع سرویس بررسی خودکار"""
        if self.is_running:
            cookie_logger.warning("Cookie validator is already running")
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._validation_loop())
        cookie_logger.info("Cookie validator service started")
    
    async def stop(self):
        """توقف سرویس"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        cookie_logger.info("Cookie validator service stopped")
    
    async def validate_cookie(self) -> Tuple[bool, Optional[str]]:
        """
        بررسی سلامت کوکی با تست دانلود
        
        Returns:
            tuple: (is_valid, error_message)
        """
        start_time = time.time()
        cookie_logger.info("Starting cookie validation")
        
        # بررسی وجود فایل کوکی
        if not os.path.exists(self.cookie_file):
            error_msg = f"Cookie file not found: {self.cookie_file}"
            cookie_logger.error(error_msg)
            return (False, "⚠️ فایل کوکی یافت نشد!")
        
        try:
            # تست دانلود با timeout
            is_valid, error = await asyncio.wait_for(
                self._test_cookie_download(),
                timeout=VALIDATION_TIMEOUT
            )
            
            duration = time.time() - start_time
            
            if is_valid:
                cookie_logger.info(f"Cookie validation successful - Duration: {duration:.2f}s")
                return (True, None)
            else:
                cookie_logger.error(f"Cookie validation failed - Error: {error} - Duration: {duration:.2f}s")
                return (False, error)
                
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            error_msg = f"Cookie validation timeout after {duration:.2f}s"
            cookie_logger.error(error_msg)
            return (False, "⏱ زمان تست به پایان رسید")
        
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Cookie validation exception: {e} - Duration: {duration:.2f}s"
            cookie_logger.error(error_msg, exc_info=True)
            return (False, f"خطا در تست: {str(e)[:100]}")
    
    async def _test_cookie_download(self) -> Tuple[bool, Optional[str]]:
        """
        تست دانلود با کوکی برای بررسی سلامت
        
        Returns:
            tuple: (success, error_message)
        """
        try:
            cookie_logger.debug(f"Testing cookie with URL: {self.test_video_url}")
            
            # تنظیمات yt-dlp برای تست سریع
            ydl_opts = {
                'format': 'worst',  # کیفیت پایین برای سرعت
                'quiet': True,
                'no_warnings': True,
                'cookiefile': self.cookie_file,
                'extract_flat': False,  # استخراج کامل اطلاعات
                'skip_download': True,  # فقط اطلاعات، بدون دانلود فایل
                'no_check_certificate': True,
            }
            
            # تست استخراج اطلاعات
            loop = asyncio.get_event_loop()
            
            def _extract():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(self.test_video_url, download=False)
                return info
            
            info = await loop.run_in_executor(None, _extract)
            
            if info and info.get('id'):
                cookie_logger.debug(f"Successfully extracted video info: {info.get('title', 'Unknown')}")
                return (True, None)
            else:
                return (False, "Failed to extract video info")
                
        except Exception as e:
            error_str = str(e)
            cookie_logger.debug(f"Cookie test failed: {error_str}")
            
            # تشخیص نوع خطا
            if "Sign in to confirm" in error_str or "login" in error_str.lower():
                return (False, "کوکی منقضی شده - نیاز به ورود مجدد")
            elif "Private video" in error_str:
                return (False, "ویدیو خصوصی است")
            elif "Video unavailable" in error_str:
                return (False, "ویدیو در دسترس نیست")
            else:
                return (False, error_str[:100])
    
    async def notify_admins(self, is_valid: bool, error_msg: Optional[str] = None):
        """
        اطلاع‌رسانی به ادمین‌ها
        
        Args:
            is_valid: آیا کوکی معتبر است
            error_msg: پیام خطا (در صورت نامعتبر بودن)
        """
        if is_valid:
            message = "🌟 گزارش کوکی : ✅ معتبر است"
        else:
            message = (
                "🌟 گزارش کوکی : ❌ نامعتبر است\n\n"
                f"⚠️ جزئیات: {error_msg or 'خطای نامشخص'}\n\n"
                "💡 لطفاً کوکی یوتیوب را بروزرسانی کنید."
            )
        
        cookie_logger.info(f"Notifying {len(self.admin_ids)} admins about cookie status: {'valid' if is_valid else 'invalid'}")
        
        # ارسال به تمام ادمین‌ها
        for admin_id in self.admin_ids:
            try:
                await self.client.send_message(
                    chat_id=admin_id,
                    text=message
                )
                cookie_logger.debug(f"Notification sent to admin {admin_id}")
            except Exception as e:
                cookie_logger.error(f"Failed to send notification to admin {admin_id}: {e}")
    
    async def _validation_loop(self):
        """حلقه اصلی بررسی (هر 3 ساعت)"""
        cookie_logger.info("Validation loop started")
        
        try:
            while self.is_running:
                # انتظار برای interval
                cookie_logger.info(f"Waiting {self.check_interval}s ({self.check_interval/3600:.1f} hours) until next check")
                await asyncio.sleep(self.check_interval)
                
                if not self.is_running:
                    break
                
                # بررسی کوکی
                cookie_logger.info("=" * 50)
                cookie_logger.info("Starting scheduled cookie validation")
                
                is_valid, error_msg = await self.validate_cookie()
                
                # اطلاع‌رسانی به ادمین‌ها
                await self.notify_admins(is_valid, error_msg)
                
                cookie_logger.info(f"Validation completed - Result: {'VALID' if is_valid else 'INVALID'}")
                cookie_logger.info("=" * 50)
                
        except asyncio.CancelledError:
            cookie_logger.info("Validation loop cancelled")
            raise
        except Exception as e:
            cookie_logger.error(f"Validation loop error: {e}", exc_info=True)
            self.is_running = False


# Global instance (will be initialized in main bot)
cookie_validator_instance: Optional[CookieValidator] = None


async def start_cookie_validator(client: Client, admin_ids: list):
    """
    شروع سرویس Cookie Validator
    
    Args:
        client: Pyrogram client
        admin_ids: لیست ID ادمین‌ها
    """
    global cookie_validator_instance
    
    if cookie_validator_instance is not None:
        cookie_logger.warning("Cookie validator already initialized")
        return
    
    cookie_validator_instance = CookieValidator(client, admin_ids)
    await cookie_validator_instance.start()
    cookie_logger.info("Cookie validator service initialized and started")


async def stop_cookie_validator():
    """توقف سرویس Cookie Validator"""
    global cookie_validator_instance
    
    if cookie_validator_instance is None:
        return
    
    await cookie_validator_instance.stop()
    cookie_validator_instance = None
    cookie_logger.info("Cookie validator service stopped and cleaned up")
