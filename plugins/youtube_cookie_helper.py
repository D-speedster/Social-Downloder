"""
YouTube Cookie Helper - مدیریت استفاده از کوکی‌های دیتابیس
"""

import os
import tempfile
from typing import Optional
from plugins.db_wrapper import DB
from plugins.logger_config import get_logger

logger = get_logger('youtube_cookie_helper')

# Cache برای جلوگیری از query زیاد به دیتابیس
_cookie_cache = {
    'cookie_id': None,
    'cookie_text': None,
    'cookie_file': None,
    'last_update': 0
}

def get_cookie_file(force_refresh: bool = False) -> Optional[str]:
    """
    دریافت مسیر فایل کوکی برای استفاده در yt-dlp
    
    این تابع:
    1. کوکی را از دیتابیس می‌گیرد
    2. در یک فایل موقت می‌نویسد
    3. مسیر فایل را برمی‌گرداند
    
    Args:
        force_refresh: اگر True باشد، کوکی را از دیتابیس مجدداً می‌گیرد
    
    Returns:
        مسیر فایل کوکی یا None اگر کوکی موجود نباشد
    """
    import time
    
    # بررسی cache (10 دقیقه اعتبار)
    if not force_refresh and _cookie_cache['cookie_file']:
        if time.time() - _cookie_cache['last_update'] < 600:  # 10 minutes
            if os.path.exists(_cookie_cache['cookie_file']):
                logger.debug(f"Using cached cookie file: {_cookie_cache['cookie_file']}")
                return _cookie_cache['cookie_file']
    
    try:
        # دریافت کوکی از دیتابیس
        db = DB()
        cookie = db.get_next_cookie(prev_cookie_id=_cookie_cache.get('cookie_id'))
        
        if not cookie or not cookie.get('cookie_text'):
            logger.warning("No valid cookie found in database")
            # سعی در استفاده از فایل قدیمی
            fallback_path = 'cookie_youtube.txt'
            if os.path.exists(fallback_path):
                logger.info(f"Using fallback cookie file: {fallback_path}")
                return fallback_path
            return None
        
        cookie_id = cookie['id']
        cookie_text = cookie['cookie_text']
        cookie_name = cookie.get('name', f'cookie_{cookie_id}')
        
        # نوشتن در فایل موقت
        # استفاده از مسیر ثابت در data/cookies_tmp برای استفاده مجدد
        cookie_dir = os.path.join('data', 'cookies_tmp')
        os.makedirs(cookie_dir, exist_ok=True)
        
        cookie_file = os.path.join(cookie_dir, f'active_cookie_{cookie_id}.txt')
        
        with open(cookie_file, 'w', encoding='utf-8') as f:
            f.write(cookie_text)
        
        # به‌روزرسانی cache
        _cookie_cache['cookie_id'] = cookie_id
        _cookie_cache['cookie_text'] = cookie_text
        _cookie_cache['cookie_file'] = cookie_file
        _cookie_cache['last_update'] = time.time()
        
        logger.info(f"✅ Cookie loaded from database: {cookie_name} (ID: {cookie_id})")
        return cookie_file
        
    except Exception as e:
        logger.error(f"Error getting cookie from database: {e}")
        # سعی در استفاده از فایل قدیمی
        fallback_path = 'cookie_youtube.txt'
        if os.path.exists(fallback_path):
            logger.info(f"Using fallback cookie file after error: {fallback_path}")
            return fallback_path
        return None


def mark_cookie_success(cookie_id: Optional[int] = None):
    """
    ثبت موفقیت استفاده از کوکی
    
    Args:
        cookie_id: شناسه کوکی (اگر None باشد، از cache استفاده می‌شود)
    """
    try:
        if cookie_id is None:
            cookie_id = _cookie_cache.get('cookie_id')
        
        if cookie_id is None:
            return
        
        db = DB()
        db.mark_cookie_used(cookie_id, success=True)
        logger.debug(f"Marked cookie {cookie_id} as successfully used")
        
    except Exception as e:
        logger.error(f"Error marking cookie success: {e}")


def mark_cookie_failure(cookie_id: Optional[int] = None):
    """
    ثبت شکست استفاده از کوکی
    
    Args:
        cookie_id: شناسه کوکی (اگر None باشد، از cache استفاده می‌شود)
    """
    try:
        if cookie_id is None:
            cookie_id = _cookie_cache.get('cookie_id')
        
        if cookie_id is None:
            return
        
        db = DB()
        db.mark_cookie_used(cookie_id, success=False)
        logger.warning(f"Marked cookie {cookie_id} as failed")
        
        # پاک کردن cache برای استفاده از کوکی بعدی
        _cookie_cache['cookie_id'] = None
        _cookie_cache['cookie_text'] = None
        _cookie_cache['cookie_file'] = None
        
    except Exception as e:
        logger.error(f"Error marking cookie failure: {e}")


def cleanup_temp_cookies():
    """پاکسازی فایل‌های کوکی موقت قدیمی"""
    try:
        import time
        cookie_dir = os.path.join('data', 'cookies_tmp')
        if not os.path.exists(cookie_dir):
            return
        
        # حذف فایل‌های قدیمی‌تر از 1 ساعت
        cutoff_time = time.time() - 3600  # 1 hour
        removed = 0
        
        for filename in os.listdir(cookie_dir):
            if not filename.startswith('active_cookie_'):
                continue
            
            filepath = os.path.join(cookie_dir, filename)
            try:
                file_mtime = os.path.getmtime(filepath)
                if file_mtime < cutoff_time:
                    os.remove(filepath)
                    removed += 1
            except Exception as e:
                logger.debug(f"Could not remove old cookie file {filename}: {e}")
        
        if removed > 0:
            logger.info(f"🧹 Cleaned up {removed} old cookie file(s)")
            
    except Exception as e:
        logger.error(f"Error cleaning up temp cookies: {e}")
