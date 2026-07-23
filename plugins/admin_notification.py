"""
Admin Notification System
سیستم ارسال گزارش به ادمین و مدیریت callback

این ماژول مسئول ارسال گزارش درخواست‌های ناموفق به ادمین
و مدیریت دکمه "پردازش مجدد" است.
"""
import logging
import time
from datetime import datetime
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from plugins.admin import ADMIN

logger = logging.getLogger('admin_notification')

# Import metrics system
try:
    from plugins.retry_metrics import retry_metrics
    METRICS_ENABLED = True
    logger.info("Retry metrics system enabled for admin notifications")
except ImportError:
    METRICS_ENABLED = False
    logger.warning("Retry metrics system not available for admin notifications")

# Track notification timestamps for response time calculation
notification_timestamps = {}


async def send_admin_notification(
    client: Client,
    request_id: int,
    user_id: int,
    url: str,
    platform: str,
    error_message: str
) -> bool:
    """
    ارسال گزارش درخواست ناموفق به ادمین‌ها
    
    Args:
        client: Pyrogram client instance
        request_id: شناسه درخواست در database
        user_id: شناسه کاربر
        url: لینک دانلود
        platform: نام پلتفرم
        error_message: پیام خطا
    
    Returns:
        bool: True if notification sent successfully to at least one admin
    """
    try:
        # محدود کردن طول پیام خطا به 500 کاراکتر (طبق requirement 4.5)
        error_display = error_message[:500]
        if len(error_message) > 500:
            error_display += "..."
        
        # محدود کردن طول URL برای نمایش
        url_display = url
        if len(url) > 100:
            url_display = url[:97] + "..."
        
        # ساخت timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # ساخت متن گزارش (طبق requirement 4.2)
        report_text = (
            "🚨 **درخواست ناموفق**\n\n"
            f"👤 **کاربر:** `{user_id}`\n"
            f"🌐 **پلتفرم:** {platform}\n"
            f"🔗 **لینک:** `{url_display}`\n\n"
            f"❌ **خطا:**\n"
            f"```\n{error_display}\n```\n\n"
            f"⏰ **زمان:** {timestamp}\n"
            f"🔢 **شناسه:** #{request_id}"
        )
        
        # ساخت دکمه inline "پردازش مجدد" (طبق requirement 4.3)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "✅ پردازش مجدد",
                callback_data=f"retry_failed_{request_id}"
            )]
        ])
        
        # ارسال به تمام ادمین‌ها
        success_count = 0
        for admin_id in ADMIN:
            try:
                await client.send_message(
                    chat_id=admin_id,
                    text=report_text,
                    reply_markup=keyboard
                )
                success_count += 1
                logger.info(f"Notification sent to admin {admin_id} for request {request_id}")
            except Exception as e:
                logger.error(f"Failed to send notification to admin {admin_id}: {e}")
        
        if success_count > 0:
            logger.info(
                f"Admin notification sent successfully to {success_count}/{len(ADMIN)} admins "
                f"for request {request_id}"
            )
            
            # Track notification timestamp for response time calculation
            notification_timestamps[request_id] = time.time()
            
            return True
        else:
            logger.error(f"Failed to send notification to any admin for request {request_id}")
            return False
    
    except Exception as e:
        logger.error(f"Error in send_admin_notification: {e}")
        return False


async def handle_retry_callback(
    client: Client,
    callback_query,
    request_id: int
) -> None:
    """
    مدیریت callback دکمه "پردازش مجدد" ادمین
    
    Args:
        client: Pyrogram client instance
        callback_query: Callback query object
        request_id: شناسه درخواست در database
    """
    try:
        admin_id = callback_query.from_user.id
        
        # بررسی اینکه کاربر ادمین است
        if admin_id not in ADMIN:
            await callback_query.answer(
                "⛔ شما دسترسی ادمین ندارید",
                show_alert=True
            )
            return
        
        logger.info(f"Admin {admin_id} requested retry for request {request_id}")
        
        # Calculate and log admin response time
        if request_id in notification_timestamps and METRICS_ENABLED:
            response_time = time.time() - notification_timestamps[request_id]
            retry_metrics.log_admin_response(response_time)
            logger.info(f"Admin response time for request {request_id}: {response_time:.2f}s")
            # Clean up timestamp
            del notification_timestamps[request_id]
        
        # نمایش پیام "در حال پردازش..."
        await callback_query.answer("🔄 در حال پردازش مجدد...")
        
        # بروزرسانی پیام
        try:
            await callback_query.message.edit_text(
                f"{callback_query.message.text}\n\n"
                f"⏳ **در حال پردازش توسط ادمین {admin_id}...**"
            )
        except Exception:
            pass
        
        # فراخوانی retry_request از صف
        try:
            from plugins.failed_request_queue import FailedRequestQueue
            from plugins.db_wrapper import DB
            
            db = DB()
            queue = FailedRequestQueue(db)
            
            # تلاش مجدد برای پردازش درخواست
            success, result_message = await queue.retry_request(client, request_id)
            
            if success:
                # موفقیت
                logger.info(f"Retry successful for request {request_id} by admin {admin_id}")
                
                # بروزرسانی پیام ادمین
                try:
                    await callback_query.message.edit_text(
                        f"{callback_query.message.text}\n\n"
                        f"✅ **پردازش موفق!**\n"
                        f"فایل به کاربر ارسال شد."
                    )
                except Exception:
                    pass
                
                # ارسال پیام به ادمین
                await client.send_message(
                    chat_id=admin_id,
                    text=f"✅ **پردازش موفق**\n\n"
                         f"درخواست #{request_id} با موفقیت پردازش شد.\n"
                         f"فایل به کاربر ارسال شد."
                )
            else:
                # شکست
                logger.warning(
                    f"Retry failed for request {request_id} by admin {admin_id}: "
                    f"{result_message}"
                )
                
                # بروزرسانی پیام ادمین
                try:
                    await callback_query.message.edit_text(
                        f"{callback_query.message.text}\n\n"
                        f"❌ **پردازش ناموفق**\n"
                        f"خطا: {result_message[:200]}"
                    )
                except Exception:
                    pass
                
                # ارسال پیام به ادمین
                await client.send_message(
                    chat_id=admin_id,
                    text=f"❌ **پردازش ناموفق**\n\n"
                         f"درخواست #{request_id} با خطا مواجه شد:\n\n"
                         f"```\n{result_message[:300]}\n```"
                )
        
        except Exception as retry_error:
            logger.error(f"Error during retry: {retry_error}")
            
            # ارسال پیام خطا به ادمین
            await client.send_message(
                chat_id=admin_id,
                text=f"❌ **خطا در پردازش**\n\n"
                     f"درخواست #{request_id}\n"
                     f"خطا: {str(retry_error)[:300]}"
            )
    
    except Exception as e:
        logger.error(f"Error in handle_retry_callback: {e}")
        try:
            await callback_query.answer(
                f"❌ خطا: {str(e)[:100]}",
                show_alert=True
            )
        except Exception:
            pass


logger.info("AdminNotification module loaded")
