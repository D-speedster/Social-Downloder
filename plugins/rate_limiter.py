"""
Rate Limiter برای جلوگیری از FloodWait و مدیریت بار
"""
import time
import asyncio
from collections import deque
from typing import Dict


class SimpleRateLimiter:
    """
    Rate limiter ساده برای محدود کردن تعداد درخواست‌ها در بازه زمانی
    """
    def __init__(self, max_requests: int = 20, time_window: int = 60):
        """
        Args:
            max_requests: حداکثر تعداد درخواست در time_window
            time_window: بازه زمانی به ثانیه
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """
        منتظر می‌ماند تا بتواند یک درخواست را اجرا کند
        """
        async with self._lock:
            now = time.time()
            
            # حذف درخواست‌های قدیمی
            while self.requests and self.requests[0] < now - self.time_window:
                self.requests.popleft()
            
            # بررسی محدودیت
            if len(self.requests) >= self.max_requests:
                # محاسبه زمان انتظار
                wait_time = self.requests[0] + self.time_window - now + 0.1
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    # بعد از انتظار، دوباره پاک‌سازی
                    while self.requests and self.requests[0] < time.time() - self.time_window:
                        self.requests.popleft()
            
            # ثبت درخواست جدید
            self.requests.append(time.time())
    
    def get_stats(self) -> Dict:
        """
        آمار فعلی rate limiter
        """
        now = time.time()
        # حذف قدیمی‌ها
        while self.requests and self.requests[0] < now - self.time_window:
            self.requests.popleft()
        
        return {
            'current_requests': len(self.requests),
            'max_requests': self.max_requests,
            'time_window': self.time_window,
            'available': self.max_requests - len(self.requests)
        }


class PerUserRateLimiter:
    """
    Rate limiter جداگانه برای هر کاربر
    """
    def __init__(self, max_per_user: int = 5, time_window: int = 60):
        """
        Args:
            max_per_user: حداکثر درخواست هر کاربر در time_window
            time_window: بازه زمانی به ثانیه
        """
        self.max_per_user = max_per_user
        self.time_window = time_window
        self.user_requests: Dict[int, deque] = {}
        self._lock = asyncio.Lock()
    
    async def check_user(self, user_id: int) -> bool:
        """
        بررسی اینکه آیا کاربر می‌تواند درخواست بدهد
        
        Returns:
            True: کاربر می‌تواند درخواست بدهد
            False: کاربر باید صبر کند
        """
        async with self._lock:
            now = time.time()
            
            if user_id not in self.user_requests:
                self.user_requests[user_id] = deque()
            
            requests = self.user_requests[user_id]
            
            # حذف درخواست‌های قدیمی
            while requests and requests[0] < now - self.time_window:
                requests.popleft()
            
            # بررسی محدودیت
            if len(requests) >= self.max_per_user:
                return False  # Reject
            
            # ثبت درخواست جدید
            requests.append(now)
            return True  # Accept
    
    def get_user_stats(self, user_id: int) -> Dict:
        """
        آمار درخواست‌های یک کاربر
        """
        now = time.time()
        
        if user_id not in self.user_requests:
            return {
                'current_requests': 0,
                'max_requests': self.max_per_user,
                'available': self.max_per_user
            }
        
        requests = self.user_requests[user_id]
        
        # حذف قدیمی‌ها
        while requests and requests[0] < now - self.time_window:
            requests.popleft()
        
        return {
            'current_requests': len(requests),
            'max_requests': self.max_per_user,
            'available': self.max_per_user - len(requests)
        }
    
    def cleanup_old_users(self):
        """
        پاک‌سازی کاربرانی که مدتی درخواست نداده‌اند
        """
        now = time.time()
        users_to_remove = []
        
        for user_id, requests in self.user_requests.items():
            # حذف قدیمی‌ها
            while requests and requests[0] < now - self.time_window:
                requests.popleft()
            
            # اگر کاربر درخواستی نداشت، حذفش کن
            if not requests:
                users_to_remove.append(user_id)
        
        for user_id in users_to_remove:
            del self.user_requests[user_id]


# 🔥 Global rate limiters
# برای پیام‌های عمومی (جلوگیری از FloodWait)
message_rate_limiter = SimpleRateLimiter(max_requests=25, time_window=60)

# برای هر کاربر (جلوگیری از spam)
user_rate_limiter = PerUserRateLimiter(max_per_user=10, time_window=60)

print("🚀 Rate limiters initialized")
print(f"   - Global: 25 messages/minute")
print(f"   - Per user: 10 requests/minute")


async def send_message_safe(client, chat_id, text, **kwargs):
    """
    ارسال پیام با rate limiting
    """
    await message_rate_limiter.acquire()
    return await client.send_message(chat_id, text, **kwargs)


async def check_user_rate_limit(user_id: int) -> bool:
    """
    بررسی rate limit کاربر
    
    Returns:
        True: کاربر می‌تواند درخواست بدهد
        False: کاربر باید صبر کند
    """
    return await user_rate_limiter.check_user(user_id)
