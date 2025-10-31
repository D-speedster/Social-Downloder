"""
🔐 سیستم مولتی قفل اسپانسری با آمار کامل
نویسنده: Kiro AI Assistant
تاریخ: 1404/08/09
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus
import logging

logger = logging.getLogger('sponsor_system')

@dataclass
class SponsorLock:
    """یک قفل اسپانسری"""
    id: str  # Unique ID for this lock
    channel_id: str  # @username or -100xxx
    channel_name: Optional[str] = None
    channel_username: Optional[str] = None
    created_at: str = ""
    
    # آمار
    total_bot_starts: int = 0  # تعداد کل استارت‌های ربات
    joined_through_lock: int = 0  # تعداد جوین از طریق این قفل
    already_members: int = 0  # تعداد کسانی که قبلا عضو بودند
    not_joined: int = 0  # تعداد کسانی که جوین نکردند/لفت دادند
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def get_join_url(self) -> str:
        """لینک جوین کانال"""
        if self.channel_username:
            return f"https://t.me/{self.channel_username.lstrip('@')}"
        elif self.channel_id.startswith('@'):
            return f"https://t.me/{self.channel_id.lstrip('@')}"
        return ""
    
    def get_stats_text(self) -> str:
        """متن آمار به فارسی زیبا"""
        # تبدیل تاریخ میلادی به شمسی (ساده)
        try:
            dt = datetime.strptime(self.created_at, "%Y-%m-%d %H:%M:%S")
            jalali_date = f"{dt.year - 621}/{dt.month:02d}/{dt.day:02d}"
            jalali_time = dt.strftime("%H:%M")
        except:
            jalali_date = "1404/08/09"
            jalali_time = "15:12"
        
        display_name = self.channel_name or self.channel_username or self.channel_id
        join_url = self.get_join_url()
        
        text = f"""🔐 وضعیت این قفل

╔
║ ‏╣ ‏ 🔗 {join_url}
╣  ‏🌐 {display_name}
║ ‏╣ از لحظه تنظیم قفل در 🗓 {jalali_date} ⏰ {jalali_time}
║ ‏╣ ‏👥 {self.total_bot_starts:,} نفر ربات را استارت کرده اند؛
║ ‏╣ ‏ 👨‍👩‍👦 {self.joined_through_lock:,} نفر از طریق این قفل، عضو لینک شده اند؛
╣ 🚶‍♂️ {self.already_members:,} نفر از قبل عضو آن بودند؛
║ ‏╣  ‏🫣 {self.not_joined:,} نفر عضو لینک نشده اند / لفت داده اند.
║ ‏🗓 {datetime.now().strftime('%Y/%m/%d')} ⏰ {datetime.now().strftime('%H:%M')}"""
        
        return text


class SponsorSystem:
    """سیستم مدیریت قفل‌های اسپانسری"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), 'sponsor_locks.json')
        self.db_path = db_path
        self.locks: List[SponsorLock] = []
        self.load()
    
    def load(self):
        """بارگذاری از فایل"""
        try:
            if os.path.exists(self.db_path):
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.locks = [SponsorLock(**lock) for lock in data.get('locks', [])]
                logger.info(f"Loaded {len(self.locks)} sponsor locks")
            else:
                self.locks = []
                self.save()
        except Exception as e:
            logger.error(f"Error loading sponsor locks: {e}")
            self.locks = []
    
    def save(self):
        """ذخیره در فایل"""
        try:
            data = {
                'locks': [asdict(lock) for lock in self.locks],
                'updated_at': datetime.now().isoformat()
            }
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(self.locks)} sponsor locks")
        except Exception as e:
            logger.error(f"Error saving sponsor locks: {e}")
    
    def add_lock(self, channel_id: str, channel_name: str = None, channel_username: str = None) -> SponsorLock:
        """افزودن قفل جدید"""
        # بررسی تکراری
        for lock in self.locks:
            if lock.channel_id == channel_id:
                logger.warning(f"Lock already exists for {channel_id}")
                return lock
        
        lock = SponsorLock(
            id=f"lock_{len(self.locks) + 1}_{int(datetime.now().timestamp())}",
            channel_id=channel_id,
            channel_name=channel_name,
            channel_username=channel_username
        )
        self.locks.append(lock)
        self.save()
        logger.info(f"Added new lock: {lock.id} for {channel_id}")
        return lock
    
    def remove_lock(self, lock_id: str) -> bool:
        """حذف قفل"""
        for i, lock in enumerate(self.locks):
            if lock.id == lock_id:
                self.locks.pop(i)
                self.save()
                logger.info(f"Removed lock: {lock_id}")
                return True
        return False
    
    def get_lock(self, lock_id: str) -> Optional[SponsorLock]:
        """دریافت یک قفل"""
        for lock in self.locks:
            if lock.id == lock_id:
                return lock
        return None
    
    def get_all_locks(self) -> List[SponsorLock]:
        """دریافت تمام قفل‌ها"""
        return self.locks.copy()
    
    async def check_user_membership(self, client: Client, user_id: int) -> Tuple[bool, List[SponsorLock]]:
        """
        بررسی عضویت کاربر در تمام قفل‌ها
        
        Returns:
            (is_member_of_all, list_of_not_joined_locks)
        """
        if not self.locks:
            return True, []
        
        not_joined = []
        
        for lock in self.locks:
            try:
                # Resolve channel ID
                chat_id = await self._resolve_channel_id(client, lock.channel_id)
                if not chat_id:
                    logger.warning(f"Could not resolve channel: {lock.channel_id}")
                    continue
                
                # Check membership
                try:
                    member = await client.get_chat_member(chat_id, user_id)
                    status = member.status
                    
                    if status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, 
                                  ChatMemberStatus.OWNER, ChatMemberStatus.RESTRICTED]:
                        # عضو است
                        continue
                    else:
                        # عضو نیست
                        not_joined.append(lock)
                except Exception as e:
                    logger.warning(f"Error checking membership for {user_id} in {chat_id}: {e}")
                    not_joined.append(lock)
                    
            except Exception as e:
                logger.error(f"Error processing lock {lock.id}: {e}")
                not_joined.append(lock)
        
        is_member_of_all = len(not_joined) == 0
        return is_member_of_all, not_joined
    
    async def _resolve_channel_id(self, client: Client, channel_ref: str):
        """تبدیل @username یا -100xxx به chat_id"""
        try:
            if channel_ref.startswith('-100') or channel_ref.lstrip('-').isdigit():
                return int(channel_ref)
            
            # Username
            username = channel_ref.lstrip('@')
            chat = await client.get_chat(username)
            return chat.id
        except Exception as e:
            logger.error(f"Error resolving channel {channel_ref}: {e}")
            return None
    
    def build_join_markup(self, not_joined_locks: List[SponsorLock]) -> InlineKeyboardMarkup:
        """ساخت دکمه‌های جوین"""
        buttons = []
        
        for lock in not_joined_locks:
            url = lock.get_join_url()
            if url:
                name = lock.channel_name or lock.channel_username or "کانال اسپانسر"
                buttons.append([InlineKeyboardButton(f"🔗 {name}", url=url)])
        
        # دکمه تایید
        buttons.append([InlineKeyboardButton("✅ جوین شدم", callback_data="verify_multi_join")])
        
        return InlineKeyboardMarkup(buttons)
    
    async def track_bot_start(self, client: Client, user_id: int):
        """ثبت استارت ربات و بررسی وضعیت عضویت"""
        for lock in self.locks:
            lock.total_bot_starts += 1
            
            try:
                chat_id = await self._resolve_channel_id(client, lock.channel_id)
                if not chat_id:
                    continue
                
                member = await client.get_chat_member(chat_id, user_id)
                status = member.status
                
                if status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, 
                              ChatMemberStatus.OWNER, ChatMemberStatus.RESTRICTED]:
                    lock.already_members += 1
                else:
                    lock.not_joined += 1
            except Exception:
                lock.not_joined += 1
        
        self.save()
    
    async def track_successful_join(self, client: Client, user_id: int, lock_id: str):
        """ثبت جوین موفق"""
        lock = self.get_lock(lock_id)
        if lock:
            lock.joined_through_lock += 1
            # کاهش از not_joined
            if lock.not_joined > 0:
                lock.not_joined -= 1
            self.save()
    
    def get_total_stats(self) -> Dict:
        """آمار کلی تمام قفل‌ها"""
        total_starts = sum(lock.total_bot_starts for lock in self.locks)
        total_joined = sum(lock.joined_through_lock for lock in self.locks)
        total_already = sum(lock.already_members for lock in self.locks)
        total_not_joined = sum(lock.not_joined for lock in self.locks)
        
        return {
            'total_locks': len(self.locks),
            'total_bot_starts': total_starts,
            'total_joined': total_joined,
            'total_already_members': total_already,
            'total_not_joined': total_not_joined,
            'conversion_rate': (total_joined / total_starts * 100) if total_starts > 0 else 0
        }


# Singleton instance
_sponsor_system = None

def get_sponsor_system() -> SponsorSystem:
    """دریافت instance سیستم اسپانسر"""
    global _sponsor_system
    if _sponsor_system is None:
        _sponsor_system = SponsorSystem()
    return _sponsor_system
