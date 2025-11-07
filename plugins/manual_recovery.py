"""
📨 Manual Message Recovery - بازیابی دستی پیام‌های از دست رفته
کنترل کامل توسط ادمین
نویسنده: Kiro AI Assistant
تاریخ: 2025-10-31
"""

import requests
import asyncio
import time
import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
from plugins.logger_config import get_logger
from plugins.sqlite_db_wrapper import DB

logger = get_logger('manual_recovery')


class ManualRecovery:
    """
    سیستم بازیابی دستی پیام‌ها
    ادمین کنترل کامل دارد
    """
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.is_processing = False
        self._lock = asyncio.Lock()  # Fix #1: Thread-safe state management
        logger.info("Manual Recovery System initialized")
    
    async def recover_by_minutes(self, client, minutes: int, admin_id: int) -> Dict:
        """
        بازیابی پیام‌های X دقیقه اخیر
        
        Args:
            client: Pyrogram client
            minutes: تعداد دقیقه (1-1440)
            admin_id: شناسه ادمین برای گزارش
        
        Returns:
            Dict با آمار بازیابی
        """
        # Fix #1: Use async lock for thread-safe state management
        async with self._lock:
            if self.is_processing:
                return {
                    'success': False,
                    'message': 'یک فرآیند بازیابی در حال اجرا است',
                    'total': 0,
                    'processed': 0,
                    'notified': 0
                }
            
            self.is_processing = True
        
        try:
            # اعتبارسنجی - Fix: Return complete dict structure
            if minutes < 1 or minutes > 1440:
                return {
                    'success': False,
                    'message': 'تعداد دقیقه باید بین 1 تا 1440 باشد',
                    'total': 0,
                    'processed': 0,
                    'notified': 0,
                    'in_timeframe': 0
                }
            
            logger.info(f"🔄 Starting manual recovery for last {minutes} minutes")
            
            # ارسال پیام شروع به ادمین
            await client.send_message(
                admin_id,
                f"🔄 **شروع بازیابی**\n\n"
                f"⏱ بازه زمانی: {minutes} دقیقه اخیر\n"
                f"⏳ لطفاً صبر کنید..."
            )
            
            # دریافت updates
            db = DB()
            last_update_id = db.get_last_update_id()
            
            # Fix #2 & #3: Use last_update_id and implement pagination
            updates = await self._fetch_all_updates(last_update_id)
            
            if not updates:
                await client.send_message(
                    admin_id,
                    "✅ **بازیابی تکمیل شد**\n\n"
                    "📭 هیچ پیامی یافت نشد"
                )
                return {
                    'success': True,
                    'total': 0,
                    'processed': 0,
                    'notified': 0,
                    'in_timeframe': 0
                }
            
            # فیلتر بر اساس زمان (با timezone UTC)
            # Fix #17: Use datetime.now(timezone.utc) instead of pytz
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            filtered_updates = self._filter_by_time(updates, cutoff_time)
            
            # Fix #5 & #20: Reduce excessive logging
            logger.debug(f"Total updates: {len(updates)}")
            logger.debug(f"Cutoff time: {cutoff_time}")
            logger.info(f"Filtered updates: {len(filtered_updates)}")
            
            if not filtered_updates:
                # 🔥 Debug: نمایش اطلاعات بیشتر
                debug_info = ""
                if updates:
                    # نمایش زمان اولین و آخرین update
                    try:
                        first_time = None
                        last_time = None
                        for update in updates:
                            timestamp = None
                            if 'message' in update:
                                timestamp = update['message'].get('date')
                            elif 'callback_query' in update:
                                timestamp = update['callback_query']['message'].get('date')
                            
                            if timestamp:
                                # Fix #1: Use timezone.utc instead of pytz.UTC
                                update_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                                if first_time is None:
                                    first_time = update_time
                                last_time = update_time
                        
                        if first_time and last_time:
                            debug_info = f"\n\n🕐 اولین update: {first_time.strftime('%Y-%m-%d %H:%M:%S')}\n🕐 آخرین update: {last_time.strftime('%Y-%m-%d %H:%M:%S')}\n🕐 Cutoff: {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}"
                    except:
                        pass
                
                await client.send_message(
                    admin_id,
                    f"✅ **بازیابی تکمیل شد**\n\n"
                    f"📭 در {minutes} دقیقه اخیر پیامی یافت نشد\n"
                    f"📊 کل updates: {len(updates)}{debug_info}"
                )
                
                # ذخیره update_id ها
                for update in updates:
                    if update.get('update_id'):
                        db.save_last_update_id(update['update_id'])
                
                return {
                    'success': True,
                    'total': len(updates),
                    'processed': 0,
                    'notified': 0,
                    'in_timeframe': 0
                }
            
            # پردازش updates
            result = await self._process_updates(
                client, 
                filtered_updates, 
                admin_id
            )
            
            # ذخیره تمام update_id ها (حتی فیلتر نشده‌ها)
            for update in updates:
                if update.get('update_id'):
                    db.save_last_update_id(update['update_id'])
            
            # ذخیره آمار
            db.increment_recovered_messages(result['notified'])
            
            # گزارش نهایی
            await client.send_message(
                admin_id,
                f"✅ **بازیابی تکمیل شد**\n\n"
                f"📊 **آمار:**\n"
                f"⏱ بازه زمانی: {minutes} دقیقه\n"
                f"📨 کل updates: {len(updates)}\n"
                f"🎯 در بازه زمانی: {len(filtered_updates)}\n"
                f"✉️ پیام‌های ارسال شده: {result['notified']}\n"
                f"⏰ زمان: {datetime.now().strftime('%H:%M:%S')}"
            )
            
            logger.info(
                f"✅ Manual recovery completed: "
                f"{result['notified']}/{len(filtered_updates)} notified"
            )
            
            return {
                'success': True,
                'total': len(updates),
                'in_timeframe': len(filtered_updates),
                'processed': result['processed'],
                'notified': result['notified']
            }
            
        except Exception as e:
            logger.error(f"Error in manual recovery: {e}")
            try:
                await client.send_message(
                    admin_id,
                    f"❌ **خطا در بازیابی**\n\n"
                    f"پیام خطا: {str(e)[:200]}"
                )
            except:
                pass
            
            # Fix #12: Return complete dict structure on error
            return {
                'success': False,
                'message': str(e),
                'total': 0,
                'processed': 0,
                'notified': 0,
                'in_timeframe': 0
            }
        
        finally:
            self.is_processing = False
    
    async def _fetch_all_updates(self, last_update_id: int) -> List[Dict]:
        """
        دریافت تمام updates موجود با pagination
        Fix #2: Implement proper pagination to avoid missing messages
        """
        all_updates = []
        # Fix #2: Handle None value for last_update_id
        offset = (last_update_id or 0) + 1
        max_iterations = 50  # Safety limit to prevent infinite loops
        
        try:
            for _ in range(max_iterations):
                url = f"{self.base_url}/getUpdates"
                params = {
                    'offset': offset,
                    'timeout': 0,
                    'limit': 100,
                    'allowed_updates': ['message', 'callback_query']
                }
                
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: requests.get(url, params=params, timeout=10)
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to fetch updates: HTTP {response.status_code}")
                    break
                
                data = response.json()
                
                if not data.get('ok'):
                    logger.error(f"Telegram API error: {data.get('description')}")
                    break
                
                result = data.get('result', [])
                
                if not result:
                    break
                
                all_updates.extend(result)
                
                # If we got less than limit, we've reached the end
                if len(result) < 100:
                    break
                
                # Update offset for next iteration
                offset = result[-1]['update_id'] + 1
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.1)
            
            logger.info(f"Fetched {len(all_updates)} total updates with pagination")
            return all_updates
            
        except Exception as e:
            logger.error(f"Error fetching updates: {e}")
            return all_updates  # Return what we have so far
    
    def _filter_by_time(self, updates: List[Dict], cutoff_time: datetime) -> List[Dict]:
        """
        فیلتر updates بر اساس زمان - با استفاده از Unix timestamp
        Fix #4: Correct timestamp extraction for callback_query
        Fix #5: Reduce excessive logging
        """
        filtered = []
        
        # تبدیل cutoff_time به Unix timestamp
        cutoff_timestamp = int(cutoff_time.timestamp())
        
        for update in updates:
            try:
                # دریافت timestamp از message یا callback_query
                timestamp = None
                user_id = None
                
                if 'message' in update:
                    timestamp = update['message'].get('date')
                    user_id = update['message'].get('from', {}).get('id')
                elif 'callback_query' in update:
                    # Fix #4: Use callback_query date first, fallback to message date
                    timestamp = update['callback_query'].get('date')
                    if not timestamp:
                        timestamp = update['callback_query'].get('message', {}).get('date')
                    user_id = update['callback_query'].get('from', {}).get('id')
                
                if timestamp:
                    # Fix #5: Use debug level for per-update logging
                    logger.debug(f"Update from user {user_id}: timestamp={timestamp}, cutoff={cutoff_timestamp}, diff={(timestamp - cutoff_timestamp)/60:.1f} min, included={timestamp >= cutoff_timestamp}")
                    
                    if timestamp >= cutoff_timestamp:
                        filtered.append(update)
            except Exception as e:
                logger.warning(f"Error filtering update: {e}")
                continue
        
        return filtered
    
    async def _process_updates(self, client, updates: List[Dict], admin_id: int) -> Dict:
        """
        پردازش updates و اطلاع‌رسانی به کاربران
        Fix #6: Edit single progress message instead of sending multiple
        Fix #7: Handle FloodWait properly
        """
        from pyrogram.errors import FloodWait
        
        processed = 0
        notified = 0
        total = len(updates)
        
        # Fix #6: Send initial progress message and edit it
        progress_msg = None
        try:
            progress_msg = await client.send_message(
                admin_id,
                f"⏳ در حال پردازش... 0/{total}"
            )
        except:
            pass
        
        last_update_time = time.time()
        
        for idx, update in enumerate(updates):
            try:
                # Fix #6: Update progress message every 10 updates or every 10 seconds
                if progress_msg and ((idx + 1) % 10 == 0 or time.time() - last_update_time > 10):
                    try:
                        await progress_msg.edit_text(
                            f"⏳ در حال پردازش... {idx + 1}/{total}\n"
                            f"✅ اطلاع‌رسانی شده: {notified}"
                        )
                        last_update_time = time.time()
                    except:
                        pass
                
                # پردازش message
                if 'message' in update:
                    success = await self._process_message(client, update['message'])
                    if success:
                        notified += 1
                    processed += 1
                
                # پردازش callback_query
                elif 'callback_query' in update:
                    success = await self._process_callback(client, update['callback_query'])
                    if success:
                        notified += 1
                    processed += 1
                
                # Fix #7 & #9: Normal delay (will be skipped if FloodWait occurs)
                await asyncio.sleep(0.3)
                
            except FloodWait as e:
                # Fix #7 & #9: Handle FloodWait properly without double delay
                logger.warning(f"FloodWait: sleeping for {e.value} seconds")
                await asyncio.sleep(e.value)
                # Continue to next iteration without the normal 0.3s delay
                continue
            except Exception as e:
                logger.error(f"Error processing update: {e}")
                continue
        
        # Final progress update
        if progress_msg:
            try:
                await progress_msg.edit_text(
                    f"✅ پردازش کامل شد!\n"
                    f"📊 کل: {total}\n"
                    f"✉️ اطلاع‌رسانی شده: {notified}"
                )
            except:
                pass
        
        return {
            'processed': processed,
            'notified': notified
        }
    
    async def _process_message(self, client, message_data: Dict) -> bool:
        """
        پردازش یک message
        Fix #8: Use regex for URL detection
        Fix #9: Handle reply errors gracefully
        """
        import re
        from pyrogram.errors import MessageIdInvalid, BadRequest
        
        try:
            user_id = message_data.get('from', {}).get('id')
            chat_id = message_data.get('chat', {}).get('id')
            text = message_data.get('text', '')
            message_id = message_data.get('message_id')
            
            if not user_id or not chat_id:
                return False
            
            # Fix #5: Reduce logging
            logger.debug(f"Processing message from user {user_id}: {text[:50] if text else 'no text'}")
            
            # ✅ بررسی دستور /start
            if text.strip() == '/start':
                logger.info(f"Processing /start command from user {user_id}")
                # ارسال پیام استارت اصلی
                welcome_text = (
                    "🔴 به ربات YouTube | Instagram Save خوش آمدید\n\n"
                    "⛱ شما می‌توانید لینک‌های یوتیوب و اینستاگرام خود را برای ربات ارسال کرده و فایل آن‌ها را در سریع‌ترین زمان ممکن با کیفیت دلخواه دریافت کنید\n\n"
                    "💡 **ربات اکنون آنلاین است و آماده دریافت درخواست‌های شماست!**"
                )
                await client.send_message(
                    chat_id=chat_id,
                    text=welcome_text,
                    reply_to_message_id=message_id
                )
                return True
            
            # نادیده گرفتن سایر دستورات قدیمی
            if text.startswith('/'):
                logger.debug(f"Skipping old command from user {user_id}")
                return False
            
            # Fix #8: Use regex for proper URL detection
            has_url = bool(re.search(r'https?://\S+', text))
            
            # اطلاع‌رسانی به کاربر
            try:
                if has_url:
                    # لینک است
                    await client.send_message(
                        chat_id=chat_id,
                        text=f"⚠️ **پیام شما دریافت شد**\n\n"
                             f"متأسفانه ربات موقتاً آفلاین بود.\n\n"
                             f"🔄 **لطفاً لینک خود را دوباره ارسال کنید:**\n"
                             f"`{text[:100]}`\n\n"
                             f"💡 ربات اکنون آنلاین است.",
                        reply_to_message_id=message_id
                    )
                else:
                    # پیام عادی
                    await client.send_message(
                        chat_id=chat_id,
                        text=f"⚠️ **پیام شما دریافت شد**\n\n"
                             f"ربات موقتاً آفلاین بود.\n"
                             f"اکنون آنلاین است و آماده دریافت درخواست‌های شماست. 🚀",
                        reply_to_message_id=message_id
                    )
            except (MessageIdInvalid, BadRequest) as e:
                # Fix #9: If reply fails, send without reply_to
                logger.warning(f"Reply failed for message {message_id}, sending without reply: {e}")
                if has_url:
                    await client.send_message(
                        chat_id=chat_id,
                        text=f"⚠️ **پیام شما دریافت شد**\n\n"
                             f"متأسفانه ربات موقتاً آفلاین بود.\n\n"
                             f"🔄 **لطفاً لینک خود را دوباره ارسال کنید:**\n"
                             f"`{text[:100]}`\n\n"
                             f"💡 ربات اکنون آنلاین است."
                    )
                else:
                    await client.send_message(
                        chat_id=chat_id,
                        text=f"⚠️ **پیام شما دریافت شد**\n\n"
                             f"ربات موقتاً آفلاین بود.\n"
                             f"اکنون آنلاین است و آماده دریافت درخواست‌های شماست. 🚀"
                    )
            
            logger.debug(f"Notified user {user_id} about missed message")
            return True
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return False
    
    async def _process_callback(self, client, callback_data: Dict) -> bool:
        """پردازش یک callback_query"""
        try:
            callback_id = callback_data.get('id')
            
            if not callback_id:
                return False
            
            try:
                await client.answer_callback_query(
                    callback_query_id=callback_id,
                    text="⚠️ ربات موقتاً آفلاین بود.\nلطفاً دوباره تلاش کنید.",
                    show_alert=True
                )
                return True
            except:
                # Callback خیلی قدیمی است
                return False
            
        except Exception as e:
            logger.error(f"Error processing callback: {e}")
            return False


# Global instance
_manual_recovery: Optional[ManualRecovery] = None
_instance_lock = asyncio.Lock()


async def get_manual_recovery(bot_token: str = None) -> Optional[ManualRecovery]:
    """
    دریافت instance سیستم بازیابی دستی
    Fix #16: Thread-safe singleton creation
    """
    global _manual_recovery
    async with _instance_lock:
        if _manual_recovery is None and bot_token:
            _manual_recovery = ManualRecovery(bot_token)
    return _manual_recovery


async def manual_recover_messages(client, bot_token: str, minutes: int, admin_id: int) -> Dict:
    """
    تابع helper برای بازیابی دستی
    
    Args:
        client: Pyrogram client
        bot_token: Bot token
        minutes: تعداد دقیقه (1-1440)
        admin_id: شناسه ادمین
    
    Returns:
        Dict با نتیجه
    """
    recovery = await get_manual_recovery(bot_token)
    if recovery:
        return await recovery.recover_by_minutes(client, minutes, admin_id)
    return {
        'success': False, 
        'message': 'Recovery system not initialized',
        'total': 0,
        'processed': 0,
        'notified': 0
    }


# Fix #15: Remove duplicate print statements
logger.info("✅ Manual Recovery System ready - Admin controlled, Time-based filtering (1-1440 minutes)")
