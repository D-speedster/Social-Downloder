"""
Admin Retry Callback Handler
مدیریت callback دکمه "پردازش مجدد" در notification های ادمین

این ماژول callback handler را برای دکمه‌های retry در گزارش‌های ادمین ثبت می‌کند.
"""
import logging
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from plugins.admin_notification import handle_retry_callback

logger = logging.getLogger('admin_retry_callback')


@Client.on_callback_query(filters.regex(r"^retry_failed_(\d+)$"))
async def admin_retry_callback_handler(client: Client, callback_query: CallbackQuery):
    """
    Handler برای callback دکمه "پردازش مجدد" در گزارش‌های ادمین
    
    این handler:
    - Pattern "retry_failed_{request_id}" را تشخیص می‌دهد
    - request_id را از callback_data استخراج می‌کند
    - handle_retry_callback را از admin_notification فراخوانی می‌کند
    
    Args:
        client: Pyrogram client instance
        callback_query: Callback query object from button press
    """
    try:
        # استخراج request_id از callback_data
        callback_data = callback_query.data
        request_id_str = callback_data.replace("retry_failed_", "")
        
        try:
            request_id = int(request_id_str)
        except ValueError:
            logger.error(f"Invalid request_id in callback: {request_id_str}")
            await callback_query.answer(
                "❌ خطا: شناسه درخواست نامعتبر است",
                show_alert=True
            )
            return
        
        logger.info(
            f"Callback received: request_id={request_id}, "
            f"admin={callback_query.from_user.id}"
        )
        
        # فراخوانی handler اصلی از admin_notification
        await handle_retry_callback(client, callback_query, request_id)
        
    except Exception as e:
        logger.error(f"Error in admin_retry_callback_handler: {e}")
        try:
            await callback_query.answer(
                f"❌ خطا در پردازش: {str(e)[:100]}",
                show_alert=True
            )
        except Exception:
            pass


logger.info("AdminRetryCallback handler registered")
