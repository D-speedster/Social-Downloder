"""
Phase 1: Simple Rate Limiter for RapidAPI
Prevents quota exhaustion by limiting requests per time window.
"""

import asyncio
import time
import logging
from collections import deque
from typing import Optional

logger = logging.getLogger(__name__)


class SimpleRateLimiter:
    """
    Thread-safe rate limiter using sliding window algorithm.
    
    Example:
        limiter = SimpleRateLimiter(max_requests=30, window_seconds=60)
        
        # Non-blocking check
        if await limiter.acquire():
            # Make API call
            pass
        
        # Blocking wait (automatically waits until allowed)
        await limiter.wait_if_needed()
        # Make API call
    """
    
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed in the time window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()  # (timestamp, metadata)
        self._lock = asyncio.Lock()
        
        logger.info(
            f"✅ Rate Limiter initialized: "
            f"{max_requests} requests per {window_seconds}s"
        )
    
    async def acquire(self) -> bool:
        """
        Try to acquire permission to make a request.
        
        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        async with self._lock:
            now = time.time()
            
            # Remove old requests outside the window
            while self.requests and self.requests[0][0] < now - self.window_seconds:
                self.requests.popleft()
            
            # Check if we're at the limit
            if len(self.requests) >= self.max_requests:
                oldest = self.requests[0][0]
                wait_time = self.window_seconds - (now - oldest)
                logger.warning(
                    f"⏱ Rate limit reached: {len(self.requests)}/{self.max_requests}. "
                    f"Wait {wait_time:.1f}s"
                )
                return False
            
            # Add this request
            self.requests.append((now, {}))
            logger.debug(
                f"✅ Request allowed: {len(self.requests)}/{self.max_requests}"
            )
            return True
    
    async def wait_if_needed(self, max_wait: Optional[float] = None):
        """
        Wait until we can make a request (blocking).
        
        Args:
            max_wait: Maximum time to wait in seconds (None = unlimited)
        
        Raises:
            asyncio.TimeoutError: If max_wait is exceeded
        """
        start_time = time.time()
        
        while not await self.acquire():
            now = time.time()
            
            # Check max wait time
            if max_wait and (now - start_time) >= max_wait:
                raise asyncio.TimeoutError(
                    f"Rate limiter wait exceeded {max_wait}s"
                )
            
            # Calculate wait time
            async with self._lock:
                if self.requests:
                    oldest = self.requests[0][0]
                    wait_time = max(0.5, self.window_seconds - (now - oldest))
                else:
                    wait_time = 0.5
            
            logger.info(f"⏱ Rate limit: waiting {wait_time:.1f}s...")
            await asyncio.sleep(min(wait_time, 5))  # Cap at 5 seconds per iteration
    
    def get_stats(self) -> dict:
        """
        Get current rate limiter statistics.
        
        Returns:
            Dictionary with current usage stats
        """
        now = time.time()
        
        # Count recent requests
        recent = [r for r in self.requests if r[0] > now - self.window_seconds]
        
        return {
            'current': len(recent),
            'limit': self.max_requests,
            'window': self.window_seconds,
            'available': self.max_requests - len(recent),
            'usage_percent': (len(recent) / self.max_requests * 100) if self.max_requests > 0 else 0
        }
    
    def reset(self):
        """Reset the rate limiter (clear all tracked requests)."""
        self.requests.clear()
        logger.info("🔄 Rate limiter reset")
    
    async def get_wait_time(self) -> float:
        """
        Get estimated wait time before next request can be made.
        
        Returns:
            Wait time in seconds (0 if request can be made now)
        """
        async with self._lock:
            now = time.time()
            
            # Remove old requests
            while self.requests and self.requests[0][0] < now - self.window_seconds:
                self.requests.popleft()
            
            # Check if we're at the limit
            if len(self.requests) < self.max_requests:
                return 0.0
            
            # Calculate wait time
            oldest = self.requests[0][0]
            return max(0, self.window_seconds - (now - oldest))


# ============================================================
# Global rate limiter instances for common use cases
# ============================================================
_rapidapi_limiter = None


def get_rapidapi_limiter() -> SimpleRateLimiter:
    """
    Get global RapidAPI rate limiter instance.
    
    Returns:
        Singleton rate limiter for RapidAPI
    """
    global _rapidapi_limiter
    
    if _rapidapi_limiter is None:
        # Load from config
        try:
            from config import RAPIDAPI_RATE_LIMIT, RAPIDAPI_RATE_WINDOW
            _rapidapi_limiter = SimpleRateLimiter(
                max_requests=RAPIDAPI_RATE_LIMIT,
                window_seconds=RAPIDAPI_RATE_WINDOW
            )
        except ImportError:
            # Fallback defaults
            logger.warning("Could not import rate limit config, using defaults")
            _rapidapi_limiter = SimpleRateLimiter(
                max_requests=30,
                window_seconds=60
            )
    
    return _rapidapi_limiter


# ============================================================
# Convenience functions
# ============================================================
async def check_rapidapi_limit() -> bool:
    """Check if RapidAPI request can be made now."""
    limiter = get_rapidapi_limiter()
    return await limiter.acquire()


async def wait_for_rapidapi() -> None:
    """Wait until RapidAPI request can be made."""
    limiter = get_rapidapi_limiter()
    await limiter.wait_if_needed()


def get_rapidapi_stats() -> dict:
    """Get RapidAPI rate limiter statistics."""
    limiter = get_rapidapi_limiter()
    return limiter.get_stats()
