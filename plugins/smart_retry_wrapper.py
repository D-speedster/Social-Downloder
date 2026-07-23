"""
Smart Retry Wrapper
سیستم retry هوشمند با پیام‌های کاربرپسند و مدیریت خطا

این ماژول wrapper function را برای handle_universal_link فراهم می‌کند
که retry logic با timing مشخص و پیام‌های کاربرپسند را اضافه می‌کند.
"""
import asyncio
import time
import logging
from typing import Callable, Tuple
from pyrogram import Client
from pyrogram.types import Message

logger = logging.getLogger('smart_retry_wrapper')

# Import metrics system
try:
    from plugins.retry_metrics import retry_metrics
    METRICS_ENABLED = True
    logger.info("Retry metrics system enabled")
except ImportError:
    METRICS_ENABLED = False
    logger.warning("Retry metrics system not available")

# پیام‌های کاربرپسند
MESSAGES = {
    'initial': "🔄 در حال پردازش لینک {platform}...",
    'busy': "سرورهای ربات مشغول است لطفا کمی صبر کنید ☺️",
    'final_error': (
        "کاربر گرامی متاسفانه سرورهای ما با مشکل روبرو شده است!\n\n"
        "در کمترین زمان ممکن فایل شما را پردازش و برای شما ارسال خواهیم کرد"
    )
}


def categorize_error(error: Exception) -> str:
    """
    دسته‌بندی خطا برای تصمیم‌گیری در مورد retry
    
    Args:
        error: Exception object
    
    Returns:
        'transient': قابل retry خودکار
        'permanent': نیاز به دخالت ادمین
        'system': خطای سیستمی داخلی
    """
    error_str = str(error).lower()
    
    # Transient errors (قابل retry)
    transient_indicators = [
        'timeout', 'timed out',
        '429', 'rate limit', 'too many requests',
        '503', 'service unavailable',
        '502', 'bad gateway',
        '504', 'gateway timeout',
        'connection', 'network',
        'temporary', 'موقت'
    ]
    
    for indicator in transient_indicators:
        if indicator in error_str:
            logger.info(f"Categorized as transient error: {indicator}")
            return 'transient'
    
    # Permanent errors (نیاز به ادمین)
    permanent_indicators = [
        '403', 'forbidden',
        '404', 'not found',
        'invalid url', 'لینک نامعتبر',
        'quota exceeded', 'محدودیت',
        'private', 'خصوصی',
        'restricted', 'محدود'
    ]
    
    for indicator in permanent_indicators:
        if indicator in error_str:
            logger.info(f"Categorized as permanent error: {indicator}")
            return 'permanent'
    
    # System errors
    system_indicators = [
        'database', 'دیتابیس',
        'file system', 'فایل سیستم',
        'memory', 'حافظه',
        'disk', 'دیسک'
    ]
    
    for indicator in system_indicators:
        if indicator in error_str:
            logger.warning(f"Categorized as system error: {indicator}")
            return 'system'
    
    # Default to transient for unknown errors
    logger.info(f"Unknown error type, defaulting to transient: {error_str[:100]}")
    return 'transient'


async def smart_retry_wrapper(
    client: Client,
    message: Message,
    url: str,
    platform: str,
    original_handler: Callable,
    max_attempts: int = 3,
    retry_schedule: list = None
) -> Tuple[bool, str]:
    """
    Wrapper function که retry logic هوشمند را به handler اضافه می‌کند
    
    این wrapper:
    - 1 ثانیه تاخیر اولیه دارد
    - با schedule مشخص (0s, 10s, 40s) retry می‌کند
    - پیام‌های کاربرپسند نمایش می‌دهد
    - موفقیت/شکست را تشخیص می‌دهد
    - در صورت شکست نهایی، به صف ادمین ارسال می‌کند
    
    Args:
        client: Pyrogram client instance
        message: User's message object
        url: Download URL
        platform: Platform name (Instagram, TikTok, etc.)
        original_handler: Original handle_universal_link function
        max_attempts: Maximum number of retry attempts (default: 3)
        retry_schedule: List of delays in seconds [0, 10, 40] (default)
    
    Returns:
        Tuple[bool, str]: (success, message)
            - success: True if download succeeded, False if failed
            - message: Status message
    """
    user_id = message.from_user.id
    
    # Default retry schedule: [0s, 10s, 40s]
    if retry_schedule is None:
        retry_schedule = [0, 10, 40]
    
    # Ensure we have enough delays for all attempts
    while len(retry_schedule) < max_attempts:
        # Add exponential backoff for additional attempts
        last_delay = retry_schedule[-1]
        retry_schedule.append(last_delay + 30)
    
    logger.info(
        f"Starting smart retry for user {user_id}, platform {platform}, "
        f"max_attempts={max_attempts}, schedule={retry_schedule[:max_attempts]}"
    )
    
    # حذف پیام اولیه - handler اصلی خودش پیام می‌فرستد
    # این از duplicate message جلوگیری می‌کند
    status_msg = None
    
    # تاخیر اولیه 1 ثانیه (طبق requirement 1.2)
    await asyncio.sleep(1.0)
    
    last_error = None
    last_error_message = ""
    
    # تلاش‌های retry
    for attempt in range(max_attempts):
        attempt_number = attempt + 1
        delay = retry_schedule[attempt]
        
        logger.info(
            f"Attempt {attempt_number}/{max_attempts} for user {user_id}, "
            f"platform {platform}, delay={delay}s"
        )
        
        # اگر این تلاش اول نیست، منتظر بمان
        if attempt > 0:
            # نمایش پیام "سرورها مشغول است" (طبق requirement 2.1)
            if status_msg:
                try:
                    await status_msg.edit_text(MESSAGES['busy'])
                except Exception as e:
                    logger.warning(f"Failed to update status message: {e}")
            
            # انتظار طبق schedule
            if delay > 0:
                logger.info(f"Waiting {delay}s before attempt {attempt_number}")
                await asyncio.sleep(delay)
        
        # تلاش برای دانلود
        try:
            start_time = time.time()
            
            # فراخوانی handler اصلی
            # توجه: handler اصلی باید به صورت async باشد
            await original_handler(client, message, is_retry=True)
            
            elapsed = time.time() - start_time
            
            # اگر به اینجا رسیدیم، یعنی موفق بوده
            logger.info(
                f"Success on attempt {attempt_number}/{max_attempts} "
                f"for user {user_id}, platform {platform}, "
                f"elapsed={elapsed:.2f}s"
            )
            
            # Log metrics
            if METRICS_ENABLED:
                retry_metrics.log_attempt(
                    attempt_number=attempt_number,
                    success=True,
                    platform=platform,
                    duration=elapsed
                )
            
            # پاک کردن پیام وضعیت
            if status_msg:
                try:
                    await status_msg.delete()
                except Exception:
                    pass
            
            return True, f"Success on attempt {attempt_number}"
        
        except Exception as e:
            last_error = e
            last_error_message = str(e)
            elapsed = time.time() - start_time
            
            logger.warning(
                f"Attempt {attempt_number}/{max_attempts} failed "
                f"for user {user_id}, platform {platform}, "
                f"elapsed={elapsed:.2f}s, error={last_error_message[:200]}"
            )
            
            # دسته‌بندی خطا
            error_category = categorize_error(e)
            
            # Log metrics
            if METRICS_ENABLED:
                retry_metrics.log_attempt(
                    attempt_number=attempt_number,
                    success=False,
                    platform=platform,
                    duration=elapsed,
                    error_category=error_category
                )
            
            # اگر خطا permanent است و این اولین تلاش نیست، دیگر retry نکن
            if error_category == 'permanent' and attempt > 0:
                logger.info(
                    f"Permanent error detected on attempt {attempt_number}, "
                    f"stopping retries"
                )
                break
            
            # اگر این آخرین تلاش نیست، ادامه بده
            if attempt < max_attempts - 1:
                continue
    
    # اگر به اینجا رسیدیم، یعنی همه تلاش‌ها ناموفق بوده
    logger.error(
        f"All {max_attempts} attempts failed for user {user_id}, "
        f"platform {platform}, last_error={last_error_message[:200]}"
    )
    
    # Log final failure metrics
    if METRICS_ENABLED:
        retry_metrics.log_final_failure(platform)
    
    # نمایش پیام خطای نهایی به کاربر (طبق requirement 5.1, 5.2, 5.3)
    # اگر status_msg وجود نداشت (چون handler اصلی خودش پیام می‌فرستد)، پیام جدید ارسال کن
    try:
        if status_msg:
            await status_msg.edit_text(MESSAGES['final_error'])
        else:
            await message.reply_text(MESSAGES['final_error'])
    except Exception as e:
        logger.warning(f"Failed to send final error message: {e}")
    
    # افزودن به صف برای پردازش توسط ادمین
    try:
        from plugins.failed_request_queue import FailedRequestQueue
        from plugins.db_wrapper import DB
        
        db = DB()
        queue = FailedRequestQueue(db)
        
        request_id = queue.add_request(
            user_id=user_id,
            url=url,
            platform=platform,
            error_message=last_error_message[:500],  # محدود کردن طول پیام
            original_message_id=message.message_id
        )
        
        if request_id > 0:
            logger.info(
                f"Added failed request to queue: request_id={request_id}, "
                f"user={user_id}, platform={platform}"
            )
            
            # Log queue addition metrics
            if METRICS_ENABLED:
                retry_metrics.log_queue_addition()
            
            # ارسال notification به ادمین
            try:
                from plugins.admin_notification import send_admin_notification
                
                await send_admin_notification(
                    client=client,
                    request_id=request_id,
                    user_id=user_id,
                    url=url,
                    platform=platform,
                    error_message=last_error_message[:500]
                )
                
                logger.info(f"Admin notification sent for request {request_id}")
            except Exception as notify_error:
                logger.error(f"Failed to send admin notification: {notify_error}")
        else:
            logger.error(f"Failed to add request to queue for user {user_id}")
    
    except Exception as queue_error:
        logger.error(f"Error adding to queue: {queue_error}")
    
    return False, f"Failed after {max_attempts} attempts: {last_error_message}"


logger.info("SmartRetryWrapper module loaded")
