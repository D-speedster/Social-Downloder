"""
Circuit Breaker برای مدیریت خطاهای API
"""
import time
import asyncio
from enum import Enum
from typing import Dict, Callable
import logging

logger = logging.getLogger('circuit_breaker')


class CircuitState(Enum):
    """وضعیت‌های Circuit Breaker"""
    CLOSED = "closed"      # عادی - همه درخواست‌ها اجرا می‌شوند
    OPEN = "open"          # خطا - درخواست‌ها رد می‌شوند
    HALF_OPEN = "half_open"  # تست - درخواست‌های محدود اجرا می‌شوند


class CircuitBreaker:
    """
    Circuit Breaker برای جلوگیری از فشار بیش از حد به سرویس‌های خراب
    """
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 60,
        half_open_timeout: int = 30
    ):
        """
        Args:
            name: نام circuit breaker
            failure_threshold: تعداد خطا برای باز شدن circuit
            success_threshold: تعداد موفقیت برای بسته شدن circuit
            timeout: مدت زمان باز بودن circuit (ثانیه)
            half_open_timeout: مدت زمان half-open (ثانیه)
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.half_open_timeout = half_open_timeout
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_state_change = time.time()
        
        logger.info(f"Circuit breaker '{name}' initialized")
    
    def _should_attempt(self) -> bool:
        """
        بررسی اینکه آیا باید درخواست را اجرا کرد
        """
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # بررسی اینکه آیا زمان timeout گذشته
            if time.time() - self.last_failure_time >= self.timeout:
                logger.info(f"Circuit '{self.name}' moving to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                self.last_state_change = time.time()
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            # در حالت half-open، فقط درخواست‌های محدود
            return True
        
        return False
    
    def _record_success(self):
        """ثبت موفقیت"""
        self.failure_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                logger.info(f"Circuit '{self.name}' moving to CLOSED")
                self.state = CircuitState.CLOSED
                self.success_count = 0
                self.last_state_change = time.time()
    
    def _record_failure(self):
        """ثبت خطا"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit '{self.name}' moving back to OPEN")
            self.state = CircuitState.OPEN
            self.failure_count = 0
            self.last_state_change = time.time()
        
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                logger.warning(
                    f"Circuit '{self.name}' OPEN after {self.failure_count} failures"
                )
                self.state = CircuitState.OPEN
                self.last_state_change = time.time()
    
    async def call(self, func: Callable, *args, **kwargs):
        """
        اجرای تابع با circuit breaker
        
        Args:
            func: تابع async برای اجرا
            *args, **kwargs: آرگومان‌های تابع
        
        Returns:
            نتیجه تابع
        
        Raises:
            CircuitBreakerOpenError: اگر circuit باز باشد
        """
        if not self._should_attempt():
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN"
            )
        
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise e
    
    def get_stats(self) -> Dict:
        """دریافت آمار circuit breaker"""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_state_change': self.last_state_change,
            'uptime': time.time() - self.last_state_change
        }


class CircuitBreakerOpenError(Exception):
    """خطای circuit breaker باز"""
    pass


class CircuitBreakerManager:
    """
    مدیریت چند circuit breaker
    """
    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}
        logger.info("Circuit breaker manager initialized")
    
    def get_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 60
    ) -> CircuitBreaker:
        """
        دریافت یا ایجاد circuit breaker
        """
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                success_threshold=success_threshold,
                timeout=timeout
            )
        return self.breakers[name]
    
    def get_all_stats(self) -> Dict:
        """دریافت آمار تمام circuit breakers"""
        return {
            name: breaker.get_stats()
            for name, breaker in self.breakers.items()
        }


# 🔥 Global manager
circuit_manager = CircuitBreakerManager()


# 🔥 Circuit breakers برای سرویس‌های مختلف
def get_instagram_breaker() -> CircuitBreaker:
    """Circuit breaker برای Instagram API"""
    return circuit_manager.get_breaker(
        name="instagram_api",
        failure_threshold=10,  # 10 خطا
        success_threshold=3,   # 3 موفقیت
        timeout=300            # 5 دقیقه
    )


def get_youtube_breaker() -> CircuitBreaker:
    """Circuit breaker برای YouTube"""
    return circuit_manager.get_breaker(
        name="youtube_api",
        failure_threshold=5,
        success_threshold=2,
        timeout=180
    )


def get_spotify_breaker() -> CircuitBreaker:
    """Circuit breaker برای Spotify API"""
    return circuit_manager.get_breaker(
        name="spotify_api",
        failure_threshold=10,
        success_threshold=3,
        timeout=300
    )


print("✅ Circuit breaker system ready")
print("   - Instagram: 10 failures → 5min timeout")
print("   - YouTube: 5 failures → 3min timeout")
print("   - Spotify: 10 failures → 5min timeout")
