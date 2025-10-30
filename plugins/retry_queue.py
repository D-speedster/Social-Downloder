"""
سیستم صف تلاش مجدد خودکار برای دانلودهای ناموفق
"""
import asyncio
import time
import json
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger('retry_queue')


@dataclass
class RetryRequest:
    """درخواست برای تلاش مجدد"""
    user_id: int
    chat_id: int
    url: str
    platform: str
    message_id: int  # پیام اصلی کاربر
    status_message_id: int  # پیام وضعیت
    attempt: int = 0
    max_attempts: int = 3
    created_at: float = None
    last_attempt: float = None
    error_message: str = ""
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.last_attempt is None:
            self.last_attempt = time.time()


class RetryQueue:
    """
    صف تلاش مجدد خودکار
    """
    def __init__(self):
        self.queue: List[RetryRequest] = []
        self.processing = False
        self.retry_delays = [120, 300, 600]  # 2min, 5min, 10min
        
        logger.info("Retry queue initialized")
    
    def add(self, request: RetryRequest):
        """
        اضافه کردن درخواست به صف
        """
        self.queue.append(request)
        logger.info(f"Added to retry queue: user={request.user_id}, platform={request.platform}, url={request.url[:50]}")
        print(f"📋 Added to retry queue: {request.platform} for user {request.user_id}")
    
    def get_pending(self) -> List[RetryRequest]:
        """
        دریافت درخواست‌های آماده برای تلاش مجدد
        """
        now = time.time()
        pending = []
        
        for req in self.queue:
            if req.attempt >= req.max_attempts:
                continue  # حداکثر تلاش انجام شده
            
            # محاسبه زمان انتظار
            delay = self.retry_delays[min(req.attempt, len(self.retry_delays) - 1)]
            if now - req.last_attempt >= delay:
                pending.append(req)
        
        return pending
    
    def get_failed(self) -> List[RetryRequest]:
        """
        دریافت درخواست‌هایی که تمام تلاش‌ها ناموفق بوده
        """
        return [req for req in self.queue if req.attempt >= req.max_attempts]
    
    def remove(self, request: RetryRequest):
        """
        حذف درخواست از صف
        """
        try:
            self.queue.remove(request)
            logger.info(f"Removed from queue: user={request.user_id}")
        except ValueError:
            pass
    
    def get_stats(self) -> Dict:
        """
        آمار صف
        """
        total = len(self.queue)
        pending = len(self.get_pending())
        failed = len(self.get_failed())
        
        return {
            'total': total,
            'pending': pending,
            'failed': failed,
            'in_progress': total - pending - failed
        }
    
    async def process_queue(self, client):
        """
        پردازش صف - اجرا در background
        """
        self.processing = True
        logger.info("Retry queue processor started")
        
        while self.processing:
            try:
                await asyncio.sleep(60)  # هر 1 دقیقه چک کن
                
                pending = self.get_pending()
                
                if pending:
                    logger.info(f"Processing {len(pending)} pending retry requests")
                    print(f"🔄 Processing {len(pending)} retry requests...")
                
                for req in pending:
                    try:
                        await self._retry_download(client, req)
                    except Exception as e:
                        logger.error(f"Error processing retry: {e}")
                
                # بررسی درخواست‌های ناموفق
                failed = self.get_failed()
                if failed:
                    await self._report_failed_to_admin(client, failed)
                    # حذف از صف
                    for req in failed:
                        self.remove(req)
                
            except Exception as e:
                logger.error(f"Error in queue processor: {e}")
    
    async def _retry_download(self, client, req: RetryRequest):
        """
        تلاش مجدد برای دانلود
        """
        req.attempt += 1
        req.last_attempt = time.time()
        
        logger.info(f"Retry attempt {req.attempt}/{req.max_attempts} for user {req.user_id}")
        
        try:
            # به‌روزرسانی پیام وضعیت
            await client.edit_message_text(
                chat_id=req.chat_id,
                message_id=req.status_message_id,
                text=f"🔄 **تلاش مجدد {req.attempt}/{req.max_attempts}**\n\n"
                     f"⏳ در حال دریافت فایل از {req.platform}...\n"
                     f"💡 لطفاً صبور باشید"
            )
        except Exception:
            pass
        
        # تلاش مجدد برای دانلود
        try:
            from plugins.universal_downloader import handle_universal_link
            
            # ساخت یک message object ساده
            class FakeMessage:
                def __init__(self, text, user_id, chat_id, message_id):
                    self.text = text
                    self.from_user = type('obj', (object,), {'id': user_id})()
                    self.chat = type('obj', (object,), {'id': chat_id})()
                    self.message_id = message_id
                    self.reply_to_message = None
                
                async def reply_text(self, text, **kwargs):
                    return await client.send_message(self.chat.id, text, **kwargs)
            
            fake_msg = FakeMessage(req.url, req.user_id, req.chat_id, req.message_id)
            
            # تلاش مجدد (با flag is_retry=True تا از infinite loop جلوگیری کنیم)
            await handle_universal_link(client, fake_msg, is_retry=True)
            
            # اگر موفق بود، حذف از صف
            self.remove(req)
            logger.info(f"Retry successful for user {req.user_id}")
            
            # پیام موفقیت
            try:
                await client.send_message(
                    chat_id=req.chat_id,
                    text="✅ **موفق شد!**\n\n"
                         "فایل شما با موفقیت دریافت شد 🎉"
                )
            except Exception:
                pass
            
        except Exception as e:
            logger.warning(f"Retry attempt {req.attempt} failed: {e}")
            req.error_message = str(e)
            
            # اگر هنوز تلاش باقی مانده
            if req.attempt < req.max_attempts:
                next_delay = self.retry_delays[min(req.attempt, len(self.retry_delays) - 1)]
                try:
                    await client.edit_message_text(
                        chat_id=req.chat_id,
                        message_id=req.status_message_id,
                        text=f"⏳ **در حال تلاش...**\n\n"
                             f"تلاش {req.attempt}/{req.max_attempts} ناموفق بود\n"
                             f"🔄 تلاش بعدی در {next_delay // 60} دقیقه\n\n"
                             f"💡 لطفاً صبور باشید، ما تلاش می‌کنیم!"
                    )
                except Exception:
                    pass
    
    async def _report_failed_to_admin(self, client, failed_requests: List[RetryRequest]):
        """
        گزارش درخواست‌های ناموفق به ادمین
        """
        if not failed_requests:
            return
        
        logger.info(f"Reporting {len(failed_requests)} failed requests to admin")
        
        for req in failed_requests:
            try:
                text = f"⚠️ **درخواست ناموفق**\n\n"
                text += f"👤 کاربر: `{req.user_id}`\n"
                text += f"📱 Platform: {req.platform}\n"
                text += f"🔗 لینک: {req.url}\n"
                text += f"🔄 تلاش‌ها: {req.attempt}/{req.max_attempts}\n"
                text += f"❌ خطا: {req.error_message[:200]}\n"
                text += f"⏰ زمان: {datetime.fromtimestamp(req.created_at).strftime('%H:%M:%S')}\n\n"
                text += f"💡 لطفاً دستی فایل را برای کاربر ارسال کنید."
                
                # دکمه برای ارسال به کاربر
                from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 ارسال به کاربر", callback_data=f"retry_send_{req.user_id}_{req.chat_id}")]
                ])
                
                await client.send_message(
                    chat_id=79049016,
                    text=text,
                    reply_markup=keyboard
                )
                
                # پیام به کاربر
                try:
                    await client.send_message(
                        chat_id=req.chat_id,
                        text="😔 **متأسفیم!**\n\n"
                             f"متأسفانه نتوانستیم فایل {req.platform} شما را دریافت کنیم.\n\n"
                             "💡 **لطفاً:**\n"
                             "• چند دقیقه صبر کنید\n"
                             "• دوباره لینک را ارسال کنید\n"
                             "• یا از پلتفرم دیگری استفاده کنید\n\n"
                             "🙏 از صبر و شکیبایی شما متشکریم!"
                    )
                except Exception:
                    pass
                
            except Exception as e:
                logger.error(f"Error reporting to admin: {e}")
    
    def stop(self):
        """توقف پردازش صف"""
        self.processing = False
        logger.info("Retry queue processor stopped")


# 🔥 Global retry queue
retry_queue = RetryQueue()


async def start_retry_queue_processor(client):
    """
    شروع پردازش‌گر صف
    """
    try:
        await retry_queue.process_queue(client)
    except Exception as e:
        logger.error(f"Retry queue processor error: {e}")


def stop_retry_queue_processor():
    """
    توقف پردازش‌گر صف
    """
    retry_queue.stop()


print("✅ Retry queue system ready")
print("   - Auto-retry: 2min, 5min, 10min")
print("   - Max attempts: 3")
print("   - Admin notification: after all attempts failed")
