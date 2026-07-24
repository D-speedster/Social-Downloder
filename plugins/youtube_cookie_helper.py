"""
YouTube Cookie Helper - مدیریت استفاده از کوکی‌های دیتابیس
"""

import os
import json
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

def _convert_json_to_netscape(cookie_text: str) -> str:
    """
    تبدیل کوکی از فرمت JSON به Netscape
    
    این تابع برای جلوگیری از مشکلات احتمالی در صورتی که کوکی به صورت JSON
    در دیتابیس ذخیره شده باشد، آن را به فرمت Netscape تبدیل می‌کند.
    
    Args:
        cookie_text: متن کوکی (ممکن است JSON یا Netscape باشد)
    
    Returns:
        متن کوکی در فرمت Netscape
    """
    try:
        # بررسی اینکه آیا کوکی JSON است یا خیر
        text_stripped = cookie_text.strip()
        
        # اگر با { یا [ شروع شود، احتمالاً JSON است
        if text_stripped.startswith('{') or text_stripped.startswith('['):
            logger.info("Detected JSON format cookie, converting to Netscape...")
            
            # پارس JSON
            data = json.loads(text_stripped)
            
            # تشخیص ساختار JSON
            if isinstance(data, dict) and 'cookies' in data:
                cookies = data['cookies']
            elif isinstance(data, list):
                cookies = data
            else:
                logger.warning("Unknown JSON cookie structure")
                return cookie_text
            
            # تبدیل به Netscape
            lines = [
                '# Netscape HTTP Cookie File',
                '# Auto-converted from JSON format',
            ]
            
            for c in cookies:
                try:
                    domain = c.get('domain', '.youtube.com')
                    # hostOnly: True → flag=FALSE, hostOnly: False → flag=TRUE
                    flag = 'FALSE' if c.get('hostOnly', False) else 'TRUE'
                    path = c.get('path', '/')
                    secure = 'TRUE' if c.get('secure', True) else 'FALSE'
                    expiration = str(c.get('expirationDate', c.get('expires', 0) or 0)).split('.')[0]
                    name = c.get('name', '')
                    value = c.get('value', '')
                    
                    if name:  # فقط اگر name وجود داشته باشد
                        lines.append('\t'.join([domain, flag, path, secure, expiration, name, value]))
                except Exception as e:
                    logger.debug(f"Skipping invalid cookie entry: {e}")
                    continue
            
            netscape_text = '\n'.join(lines) + '\n'
            logger.info(f"✅ Successfully converted JSON to Netscape ({len(lines)-2} cookies)")
            return netscape_text
        
        # اگر قبلاً Netscape است، همان را برگردان
        return cookie_text
        
    except json.JSONDecodeError:
        # اگر JSON نبود، احتمالاً Netscape است
        logger.debug("Cookie is not JSON, assuming Netscape format")
        return cookie_text
    except Exception as e:
        logger.error(f"Error converting cookie format: {e}")
        # در صورت خطا، متن اصلی را برگردان
        return cookie_text

def get_cookie_file(force_refresh: bool = False, allow_fallback_to_none: bool = True) -> Optional[str]:
    """
    دریافت مسیر فایل کوکی برای استفاده در yt-dlp
    
    این تابع:
    1. کوکی را از دیتابیس می‌گیرد
    2. در یک فایل موقت می‌نویسد
    3. مسیر فایل را برمی‌گرداند
    
    Args:
        force_refresh: اگر True باشد، کوکی را از دیتابیس مجدداً می‌گیرد
        allow_fallback_to_none: اگر True باشد، در صورت نبود کوکی معتبر، None برمی‌گرداند (برای download بدون کوکی)
    
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
            # اگر allow_fallback_to_none=True، None برگردان (برای download بدون کوکی)
            if allow_fallback_to_none:
                logger.info("No cookie available - will attempt download without cookies")
            return None
        
        cookie_id = cookie['id']
        cookie_text = cookie['cookie_text']
        cookie_name = cookie.get('name', f'cookie_{cookie_id}')
        
        # 🔥 تبدیل فرمت در صورت نیاز (JSON → Netscape)
        cookie_text = _convert_json_to_netscape(cookie_text)
        
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
        logger.debug(f"✅ Marked cookie {cookie_id} as successfully used")
        
    except Exception as e:
        logger.error(f"Error marking cookie success: {e}")


def mark_cookie_failure(cookie_id: Optional[int] = None):
    """
    ثبت شکست استفاده از کوکی
    
    🔥 این تابع کش را کاملاً پاک می‌کند تا درخواست بعدی بلافاصله کوکی جدید دریافت کند
    
    Args:
        cookie_id: شناسه کوکی (اگر None باشد، از cache استفاده می‌شود)
    """
    try:
        if cookie_id is None:
            cookie_id = _cookie_cache.get('cookie_id')
        
        if cookie_id is None:
            logger.warning("mark_cookie_failure called but no cookie_id in cache")
            return
        
        # ثبت شکست در دیتابیس
        db = DB()
        db.mark_cookie_used(cookie_id, success=False)
        logger.warning(f"❌ Marked cookie {cookie_id} as failed")
        
        # 🔥 حذف فایل کش قدیمی از دیسک
        old_cookie_file = _cookie_cache.get('cookie_file')
        if old_cookie_file and os.path.exists(old_cookie_file):
            try:
                os.unlink(old_cookie_file)
                logger.info(f"🗑️ Deleted failed cookie file: {old_cookie_file}")
            except Exception as e:
                logger.debug(f"Could not delete old cookie file: {e}")
        
        # 🔥 پاک کردن کامل cache برای استفاده از کوکی بعدی
        _cookie_cache['cookie_id'] = None
        _cookie_cache['cookie_text'] = None
        _cookie_cache['cookie_file'] = None
        _cookie_cache['last_update'] = 0  # 🔴 مهم: این فیلد را هم باید پاک کرد!
        
        logger.info(f"🔄 Cache cleared - next request will fetch a new cookie from database")
        
    except Exception as e:
        logger.error(f"Error marking cookie failure: {e}")
        # در صورت خطا، حتماً کش را پاک کن
        _cookie_cache['cookie_id'] = None
        _cookie_cache['cookie_text'] = None
        _cookie_cache['cookie_file'] = None
        _cookie_cache['last_update'] = 0


def cleanup_temp_cookies(force_cleanup: bool = False):
    """
    پاکسازی فایل‌های کوکی موقت قدیمی
    
    این تابع دو نوع پاکسازی انجام می‌دهد:
    1. حذف فایل‌های قدیمی‌تر از 1 ساعت (time-based)
    2. حذف فایل‌های مربوط به کوکی‌های حذف شده از دیتابیس (sync with DB)
    
    Args:
        force_cleanup: اگر True باشد، تمام فایل‌های temp حذف می‌شوند
    """
    try:
        import time
        cookie_dir = os.path.join('data', 'cookies_tmp')
        if not os.path.exists(cookie_dir):
            return
        
        removed_old = 0
        removed_orphan = 0
        
        # دریافت لیست ID های کوکی‌های معتبر از دیتابیس
        valid_cookie_ids = set()
        try:
            db = DB()
            result = db.cursor.execute('SELECT id FROM cookies').fetchall()
            valid_cookie_ids = {row[0] for row in result}
            logger.debug(f"Valid cookie IDs in DB: {valid_cookie_ids}")
        except Exception as e:
            logger.warning(f"Could not fetch cookie IDs from DB: {e}")
        
        # پاکسازی فایل‌های موقت
        cutoff_time = time.time() - 3600  # 1 hour
        
        for filename in os.listdir(cookie_dir):
            if not filename.startswith('active_cookie_'):
                continue
            
            filepath = os.path.join(cookie_dir, filename)
            
            try:
                # استخراج ID از نام فایل (مثلاً active_cookie_123.txt → 123)
                cookie_id_str = filename.replace('active_cookie_', '').replace('.txt', '')
                
                should_remove = False
                reason = ""
                
                if force_cleanup:
                    should_remove = True
                    reason = "force cleanup"
                else:
                    # بررسی 1: فایل قدیمی است؟
                    try:
                        file_mtime = os.path.getmtime(filepath)
                        if file_mtime < cutoff_time:
                            should_remove = True
                            reason = "older than 1 hour"
                            removed_old += 1
                    except Exception:
                        pass
                    
                    # بررسی 2: کوکی در دیتابیس حذف شده؟ (orphan file)
                    if not should_remove and valid_cookie_ids:
                        try:
                            cookie_id = int(cookie_id_str)
                            if cookie_id not in valid_cookie_ids:
                                should_remove = True
                                reason = "cookie deleted from DB"
                                removed_orphan += 1
                        except ValueError:
                            # اگر ID عددی نبود، فایل نامعتبر است
                            should_remove = True
                            reason = "invalid filename"
                
                if should_remove:
                    os.remove(filepath)
                    logger.debug(f"Removed {filename}: {reason}")
                    
            except Exception as e:
                logger.debug(f"Could not process/remove {filename}: {e}")
        
        total_removed = removed_old + removed_orphan
        if total_removed > 0:
            logger.info(f"🧹 Cleaned up {total_removed} cookie file(s) (old: {removed_old}, orphan: {removed_orphan})")
        
        return total_removed
            
    except Exception as e:
        logger.error(f"Error cleaning up temp cookies: {e}")
        return 0


def clear_cookie_cache():
    """
    پاکسازی کامل کش کوکی (برای استفاده در شرایط اضطراری یا تست)
    
    این تابع تمام اطلاعات cache شده را پاک می‌کند و درخواست بعدی
    مجبور می‌شود کوکی جدید از دیتابیس بگیرد.
    """
    global _cookie_cache
    
    try:
        # حذف فایل کش قدیمی
        old_file = _cookie_cache.get('cookie_file')
        if old_file and os.path.exists(old_file):
            try:
                os.unlink(old_file)
                logger.info(f"🗑️ Deleted cached cookie file: {old_file}")
            except Exception as e:
                logger.debug(f"Could not delete cache file: {e}")
        
        # پاکسازی کامل متغیر global
        _cookie_cache = {
            'cookie_id': None,
            'cookie_text': None,
            'cookie_file': None,
            'last_update': 0
        }
        
        logger.info("🔄 Cookie cache completely cleared")
        return True
        
    except Exception as e:
        logger.error(f"Error clearing cookie cache: {e}")
        return False


async def periodic_cleanup_task(interval_seconds: int = 1800):
    """
    تسک پس‌زمینه برای پاکسازی دوره‌ای فایل‌های کوکی موقت
    
    این تابع هر 30 دقیقه (یا interval تعیین شده) اجرا می‌شود و:
    1. فایل‌های قدیمی‌تر از 1 ساعت را حذف می‌کند
    2. فایل‌های مربوط به کوکی‌های حذف شده از DB را پاک می‌کند
    
    Args:
        interval_seconds: فاصله زمانی بین هر cleanup (پیش‌فرض: 1800 ثانیه = 30 دقیقه)
    """
    import asyncio
    
    logger.info(f"🔄 Started periodic cookie cleanup task (interval: {interval_seconds}s)")
    
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            
            logger.debug("Running periodic cookie cleanup...")
            removed = cleanup_temp_cookies()
            
            if removed > 0:
                logger.info(f"✅ Periodic cleanup: removed {removed} file(s)")
            
        except asyncio.CancelledError:
            logger.info("Periodic cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")
            # ادامه می‌دهد حتی در صورت خطا
