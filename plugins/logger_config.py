"""
مدیریت مرکزی لاگ‌گذاری برای ربات دانلودر
این ماژول تنظیمات یکپارچه برای تمام لاگرها فراهم می‌کند
"""

import logging
import logging.handlers
import os
from datetime import datetime


class BotLoggerManager:
    """مدیر مرکزی لاگ‌گذاری ربات"""
    
    def __init__(self, logs_dir='./logs'):
        self.logs_dir = logs_dir
        self.ensure_logs_directory()
        
    def ensure_logs_directory(self):
        """اطمینان از وجود دایرکتوری لاگ‌ها"""
        os.makedirs(self.logs_dir, exist_ok=True)
        
    def get_logger(self, name, log_file=None, level=logging.DEBUG, 
                   max_bytes=10*1024*1024, backup_count=5):
        """
        ایجاد یا دریافت لاگر با تنظیمات بهینه
        
        Args:
            name: نام لاگر
            log_file: نام فایل لاگ (اختیاری)
            level: سطح لاگ‌گذاری
            max_bytes: حداکثر اندازه فایل لاگ (10MB)
            backup_count: تعداد فایل‌های پشتیبان
        """
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # تعیین نام فایل لاگ
        if not log_file:
            log_file = f"{name}.log"
            
        log_path = os.path.join(self.logs_dir, log_file)
        
        # تنظیم فرمت لاگ
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # افزودن FileHandler تنها در صورت عدم وجود
        has_file = any(isinstance(h, logging.handlers.RotatingFileHandler) for h in logger.handlers)
        if not has_file:
            file_handler = logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        # افزودن StreamHandler (کنسول) تنها در صورت عدم وجود و اگر فعال باشد
        has_console = any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
        if not has_console and os.environ.get('LOG_TO_CONSOLE', '1') == '1':
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # جلوگیری از انتشار به root logger
        logger.propagate = False
        
        return logger
    
    def get_performance_logger(self, name='performance'):
        """لاگر ویژه برای نظارت بر عملکرد"""
        return self.get_logger(
            name, 
            'performance.log', 
            level=logging.INFO,
            max_bytes=5*1024*1024,  # 5MB
            backup_count=3
        )
    
    def get_error_logger(self, name='errors'):
        """لاگر ویژه برای خطاها"""
        return self.get_logger(
            name,
            'errors.log',
            level=logging.ERROR,
            max_bytes=20*1024*1024,  # 20MB
            backup_count=10
        )
    
    def cleanup_old_logs(self, days_to_keep=30):
        """پاک‌سازی لاگ‌های قدیمی"""
        try:
            current_time = datetime.now()
            for filename in os.listdir(self.logs_dir):
                file_path = os.path.join(self.logs_dir, filename)
                if os.path.isfile(file_path) and filename.endswith('.log'):
                    file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    if (current_time - file_time).days > days_to_keep:
                        os.remove(file_path)
                        print(f"Removed old log file: {filename}")
        except Exception as e:
            print(f"Error cleaning up logs: {e}")


# نمونه سراسری مدیر لاگ
log_manager = BotLoggerManager()

# تابع‌های کمکی برای دسترسی آسان
def get_logger(name, **kwargs):
    """دریافت لاگر با تنظیمات پیش‌فرض"""
    return log_manager.get_logger(name, **kwargs)

def get_performance_logger():
    """دریافت لاگر عملکرد"""
    return log_manager.get_performance_logger()

def get_error_logger():
    """دریافت لاگر خطا"""
    return log_manager.get_error_logger()