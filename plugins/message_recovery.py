"""
🔄 Message Recovery System - بازیابی پیام‌های از دست رفته
نویسنده: Kiro AI Assistant
تاریخ: 2025-10-31
"""

import requests
import asyncio
import time
from typing import List, Dict, Optional
from datetime import datetime
from plugins.logger_config import get_logger
from plugins.sqlite_db_wrapper import DB

logger = get_logger('message_recovery')


class MessageRecovery:
    """
    سیستم بازیابی پیام‌های از دست رفته
    """
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        logger.info("Message Recovery System initialized")
    
    async def recover_missed_updates(self, client) -> int:
        """
        بازیابی updates فقط برای اولین راه‌اندازی
        
        Returns:
            همیشه 0 برمی‌گرداند (دیگر به صورت خودکار پیام‌ها را بازیابی نمی‌کند)
        """
        try:
            db = DB()
            last_update_id = db.get_last_update_id()
            bot_state = db.get_bot_state()
            
            # 🔥 تشخیص اولین راه‌اندازی
            is_first_run = (last_update_id == 0 and bot_state.get('last_shutdown') is None)
            
            if is_first_run:
                logger.info("🔄 First run detected - performing silent sync")
                print(f"🔄 اولین راه‌اندازی - همگام‌سازی بی‌صدا...")
                
                # دریافت updates از Telegram
                updates = await self._fetch_updates(last_update_id)
                
                if updates:
                    # فقط update_id ها را ذخیره کن
                    for update in updates:
                        update_id = update.get('update_id')
                        if update_id:
                            db.save_last_update_id(update_id)
                    
                    logger.info(f"📝 Synced {len(updates)} updates silently (first run)")
                    print(f"📝 همگام‌سازی {len(updates)} پیام (بدون اطلاع‌رسانی)")
                
                logger.info(f"✅ Silent sync completed")
                print(f"✅ همگام‌سازی بی‌صدا تکمیل شد")
            else:
                logger.info("✅ Skipping automatic recovery (admin-controlled only)")
                print("✅ بازیابی خودکار غیرفعال شد (فقط از طریق پنل ادمین)")
            
            return 0  # هیچ پیامی به کاربران نرفت
            
        except Exception as e:
            logger.error(f"❌ Error in recover_missed_updates: {e}")
            print(f"⚠️ خطا در بازیابی پیام‌ها: {e}")
            return 0
    
    async def _fetch_updates(self, last_update_id: int) -> List[Dict]:
        """دریافت updates از Telegram Bot API"""
        try:
            url = f"{self.base_url}/getUpdates"
            params = {
                'offset': last_update_id + 1,
                'timeout': 0,
                'limit': 100,  # حداکثر 100 update
                'allowed_updates': ['message', 'callback_query']
            }
            
            # استفاده از asyncio برای non-blocking request
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(url, params=params, timeout=10)
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch updates: HTTP {response.status_code}")
                return []
            
            data = response.json()
            
            if not data.get('ok'):
                logger.error(f"Telegram API error: {data.get('description')}")
                return []
            
            return data.get('result', [])
            
        except requests.Timeout:
            logger.error("Timeout while fetching updates")
            return []
        except Exception as e:
            logger.error(f"Error fetching updates: {e}")
            return []

    async def _fetch_updates_by_time(self, start_time: int) -> List[Dict]:
        """
        دریافت updates بر اساس زمان شروع
        
        Args:
            start_time: timestamp زمانی برای شروع جستجو
            
        Returns:
            لیست updates از زمان مشخص شده
        """
        try:
            db = DB()
            last_update_id = db.get_last_update_id()
            
            url = f"{self.base_url}/getUpdates"
            params = {
                'offset': last_update_id + 1,
                'timeout': 0,
                'limit': 100,  # حداکثر 100 update
                'allowed_updates': ['message', 'callback_query']
            }
            
            # استفاده از asyncio برای non-blocking request
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(url, params=params, timeout=10)
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch updates: HTTP {response.status_code}")
                return []
            
            data = response.json()
            
            if not data.get('ok'):
                logger.error(f"Telegram API error: {data.get('description')}")
                return []
            
            updates = data.get('result', [])
            
            # فیلتر updates بر اساس زمان
            filtered_updates = []
            for update in updates:
                message_time = None
                
                if 'message' in update:
                    message_time = update['message'].get('date', 0)
                elif 'callback_query' in update:
                    message_time = update['callback_query'].get('date', 0)
                
                # اگر زمان پیام بعد از start_time باشد، اضافه کن
                if message_time and message_time >= start_time:
                    filtered_updates.append(update)
            
            logger.info(f"Found {len(filtered_updates)} updates since timestamp {start_time}")
            return filtered_updates
            
        except requests.Timeout:
            logger.error("Timeout while fetching updates by time")
            return []
        except Exception as e:
            logger.error(f"Error fetching updates by time: {e}")
            return []
    
    async def _process_updates(self, client, updates: List[Dict]) -> int:
        """پردازش لیست updates"""
        processed = 0
        db = DB()
        
        for update in updates:
            try:
                update_id = update.get('update_id')
                
                # پردازش message
                if 'message' in update:
                    success = await self._process_message(client, update['message'])
                    if success:
                        processed += 1
                
                # پردازش callback_query
                elif 'callback_query' in update:
                    success = await self._process_callback(client, update['callback_query'])
                    if success:
                        processed += 1
                
                # ذخیره update_id (حتی اگر پردازش ناموفق بود)
                if update_id:
                    db.save_last_update_id(update_id)
                
                # کمی تأخیر برای جلوگیری از FloodWait
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error processing update {update.get('update_id')}: {e}")
                continue
        
        return processed
    
    async def _process_message(self, client, message_data: Dict) -> bool:
        """پردازش یک message از دست رفته"""
        try:
            user_id = message_data.get('from', {}).get('id')
            chat_id = message_data.get('chat', {}).get('id')
            text = message_data.get('text', '')
            message_id = message_data.get('message_id')
            
            if not user_id or not chat_id:
                return False
            
            # بررسی نوع پیام
            if text.startswith('/'):
                # دستورات را نادیده بگیر (احتمالاً قدیمی هستند)
                logger.info(f"Skipping old command from user {user_id}: {text}")
                return True
            
            # اگر لینک است، اطلاع‌رسانی کن
            if any(keyword in text.lower() for keyword in ['http', 'youtu', 'insta', 'spotify', 'tiktok']):
                await client.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ **پیام شما دریافت شد**\n\n"
                         f"متأسفانه ربات موقتاً آفلاین بود و نتوانست پیام شما را پردازش کند.\n\n"
                         f"🔄 **لطفاً لینک خود را دوباره ارسال کنید:**\n"
                         f"`{text[:100]}`\n\n"
                         f"💡 ربات اکنون آنلاین است و آماده پردازش درخواست شماست.",
                    reply_to_message_id=message_id
                )
                logger.info(f"Notified user {user_id} about missed link")
                return True
            
            # برای پیام‌های عادی، فقط اطلاع‌رسانی ساده
            await client.send_message(
                chat_id=chat_id,
                text=f"⚠️ **پیام شما دریافت شد**\n\n"
                     f"ربات موقتاً آفلاین بود.\n"
                     f"اکنون آنلاین است و آماده دریافت درخواست‌های شماست. 🚀",
                reply_to_message_id=message_id
            )
            
            logger.info(f"Notified user {user_id} about missed message")
            return True
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return False
    
    async def _process_callback(self, client, callback_data: Dict) -> bool:
        """پردازش یک callback_query از دست رفته"""
        try:
            callback_id = callback_data.get('id')
            user_id = callback_data.get('from', {}).get('id')
            
            if not callback_id:
                return False
            
            # پاسخ به callback query
            try:
                await client.answer_callback_query(
                    callback_query_id=callback_id,
                    text="⚠️ ربات موقتاً آفلاین بود.\nلطفاً دوباره تلاش کنید.",
                    show_alert=True
                )
                logger.info(f"Answered missed callback from user {user_id}")
                return True
            except Exception as e:
                # اگر callback خیلی قدیمی باشد، Telegram خطا می‌دهد
                logger.warning(f"Could not answer old callback: {e}")
                return False
            
        except Exception as e:
            logger.error(f"Error processing callback: {e}")
            return False
    
    def get_recovery_stats(self) -> Dict:
        """دریافت آمار بازیابی"""
        try:
            db = DB()
            state = db.get_bot_state()
            
            return {
                'total_startups': state.get('total_startups', 0),
                'total_recovered': state.get('total_recovered_messages', 0),
                'last_startup': state.get('last_startup'),
                'last_shutdown': state.get('last_shutdown'),
                'last_update_id': state.get('last_update_id', 0)
            }
        except Exception as e:
            logger.error(f"Error getting recovery stats: {e}")
            return {}


# 🔥 Global instance
_recovery_system: Optional[MessageRecovery] = None


def get_recovery_system(bot_token: str = None) -> Optional[MessageRecovery]:
    """دریافت instance سیستم بازیابی"""
    global _recovery_system
    if _recovery_system is None and bot_token:
        _recovery_system = MessageRecovery(bot_token)
    return _recovery_system


async def recover_missed_messages(client, bot_token: str) -> int:
    """
    تابع helper برای بازیابی پیام‌های از دست رفته
    
    Args:
        client: Pyrogram client
        bot_token: Bot token
    
    Returns:
        تعداد پیام‌های بازیابی شده
    """
    recovery = get_recovery_system(bot_token)
    if recovery:
        return await recovery.recover_missed_updates(client)
    return 0


def get_recovery_stats() -> Dict:
    """دریافت آمار بازیابی"""
    if _recovery_system:
        return _recovery_system.get_recovery_stats()
    return {}


async def process_pending_updates(minutes: int) -> Dict:
    """
    پردازش انتخابی پیام‌ها بر اساس زمان مشخص شده توسط ادمین
    
    Args:
        minutes: تعداد دقیقه گذشته برای پردازش (1-1440)
        
    Returns:
        آمار پردازش شامل تعداد پیام‌های پردازش شده و کاربران اطلاع‌رسانی شده
    """
    try:
        from main import bot_token
        from pyrogram import Client
        
        # ایجاد یک client موقت برای پردازش
        client = Client(
            "pending_updates_processor",
            bot_token=bot_token,
            no_updates=True  # برای جلوگیری از دریافت updates جدید
        )
        
        await client.start()
        
        # محاسبه زمان شروع بر اساس دقیقه‌های مشخص شده
        from datetime import datetime, timedelta
        start_time = int((datetime.now() - timedelta(minutes=minutes)).timestamp())
        
        recovery = get_recovery_system(bot_token)
        if not recovery:
            return {"processed": 0, "notified": 0, "error": "Recovery system not initialized"}
        
        # دریافت updates از زمان مشخص شده
        updates = await recovery._fetch_updates_by_time(start_time)
        
        if not updates:
            await client.stop()
            return {"processed": 0, "notified": 0, "message": "No updates found in specified time range"}
        
        # پردازش updates
        processed = await recovery._process_updates(client, updates)
        
        await client.stop()
        
        return {
            "processed": len(updates),
            "notified": processed,
            "time_range": f"آخرین {minutes} دقیقه",
            "start_time": start_time
        }
        
    except Exception as e:
        print(f"[ERROR] Failed to process pending updates: {e}")
        return {"processed": 0, "notified": 0, "error": str(e)}


print("✅ Message Recovery System ready")
print("   - Auto-recovery on startup")
print("   - User notification") 
print("   - Stats tracking")
print("   - Admin-controlled pending updates")
