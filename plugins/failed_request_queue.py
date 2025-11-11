"""
Failed Request Queue System
مدیریت صف درخواست‌های ناموفق و retry آنها
"""

import logging
from typing import Tuple
from pyrogram import Client
from plugins.db_wrapper import DB

logger = logging.getLogger('failed_request_queue')


class FailedRequestQueue:
    """
    مدیریت صف درخواست‌های ناموفق
    """
    
    def __init__(self, db: DB):
        self.db = db
    
    def get_queue_stats(self) -> dict:
        """
        دریافت آمار کلی صف درخواست‌ها
        
        Returns:
            dict: آمار شامل total, pending, processing, completed, failed
        """
        try:
            # دریافت تمام درخواست‌ها
            all_requests = self.db.get_all_failed_requests()
            
            stats = {
                'total': len(all_requests),
                'pending': 0,
                'processing': 0,
                'completed': 0,
                'failed': 0
            }
            
            # شمارش بر اساس وضعیت
            for req in all_requests:
                status = req.get('status', 'pending')
                if status in stats:
                    stats[status] += 1
            
            return stats
        
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            return {
                'total': 0,
                'pending': 0,
                'processing': 0,
                'completed': 0,
                'failed': 0
            }
    
    def get_pending_requests(self, limit: int = 10) -> list:
        """
        دریافت لیست درخواست‌های در انتظار
        
        Args:
            limit: تعداد درخواست‌ها
        
        Returns:
            list: لیست درخواست‌های pending
        """
        try:
            all_requests = self.db.get_all_failed_requests()
            pending = [r for r in all_requests if r.get('status') == 'pending']
            return pending[:limit]
        except Exception as e:
            logger.error(f"Error getting pending requests: {e}")
            return []
    
    async def retry_request(
        self,
        client: Client,
        request_id: int
    ) -> Tuple[bool, str]:
        """
        تلاش مجدد برای پردازش یک درخواست ناموفق
        
        Args:
            client: Pyrogram client instance
            request_id: شناسه درخواست در database
        
        Returns:
            Tuple[bool, str]: (موفقیت, پیام نتیجه)
        """
        try:
            # دریافت اطلاعات درخواست
            request = self.db.get_failed_request_by_id(request_id)
            
            if not request:
                return False, "درخواست یافت نشد"
            
            # بررسی وضعیت
            if request['status'] in ['completed', 'processing']:
                return False, "این درخواست قبلاً پردازش شده است"
            
            # افزایش شمارنده retry
            self.db.increment_failed_request_retry(request_id)
            
            # استخراج اطلاعات
            user_id = request['user_id']
            url = request['url']
            platform = request['platform']
            original_message_id = request['original_message_id']
            
            logger.info(f"Retrying request {request_id} for user {user_id}, platform {platform}")
            
            # ساخت یک message object ساده برای handler
            class FakeMessage:
                def __init__(self, user_id, text, message_id):
                    self.from_user = type('obj', (object,), {'id': user_id})()
                    self.text = text
                    self.id = message_id
                    self.chat = type('obj', (object,), {'id': user_id})()
                
                async def reply_text(self, text, **kwargs):
                    return await client.send_message(user_id, text, **kwargs)
            
            fake_msg = FakeMessage(user_id, url, original_message_id)
            
            # تلاش برای دانلود
            try:
                from plugins.universal_downloader import handle_universal_link
                
                # فراخوانی handler با is_retry=True
                await handle_universal_link(client, fake_msg, is_retry=True)
                
                # اگر به اینجا رسیدیم، موفق بوده
                self.db.mark_failed_request_as_processed(request_id)
                
                logger.info(f"Successfully processed request {request_id}")
                return True, "پردازش موفق - فایل به کاربر ارسال شد"
            
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to process request {request_id}: {e}")
                
                # علامت‌گذاری به عنوان failed
                self.db.mark_failed_request_as_failed(request_id, error_msg)
                
                return False, f"خطا در دانلود: {error_msg[:200]}"
        
        except Exception as e:
            logger.error(f"Error in retry_request: {e}")
            return False, f"خطای سیستمی: {str(e)[:200]}"


logger.info("FailedRequestQueue module loaded")
