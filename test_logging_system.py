#!/usr/bin/env python3
"""
تست سیستم لاگ‌گذاری ربات
"""

import os
import sys
from plugins.logger_config import get_logger, get_performance_logger, get_error_logger

def test_logging_system():
    """تست جامع سیستم لاگ‌گذاری"""
    
    print("🚀 تست سیستم لاگ‌گذاری...")
    print("=" * 60)
    
    # تست لاگر عمومی
    print("🔍 تست لاگر عمومی...")
    try:
        main_logger = get_logger('main_test')
        main_logger.info("تست پیام اطلاعاتی")
        main_logger.warning("تست پیام هشدار")
        main_logger.error("تست پیام خطا")
        main_logger.debug("تست پیام دیباگ")
        print("✅ لاگر عمومی کار می‌کند")
    except Exception as e:
        print(f"❌ خطا در لاگر عمومی: {e}")
    
    print("-" * 40)
    
    # تست لاگر عملکرد
    print("🔍 تست لاگر عملکرد...")
    try:
        perf_logger = get_performance_logger()
        perf_logger.info("شروع عملیات دانلود")
        perf_logger.info("پیشرفت: 50%")
        perf_logger.info("اتمام عملیات دانلود")
        print("✅ لاگر عملکرد کار می‌کند")
    except Exception as e:
        print(f"❌ خطا در لاگر عملکرد: {e}")
    
    print("-" * 40)
    
    # تست لاگر خطاها
    print("🔍 تست لاگر خطاها...")
    try:
        error_logger = get_error_logger()
        error_logger.error("خطای تست شماره 1")
        error_logger.critical("خطای بحرانی تست")
        error_logger.error("خطای تست شماره 2")
        print("✅ لاگر خطاها کار می‌کند")
    except Exception as e:
        print(f"❌ خطا در لاگر خطاها: {e}")
    
    print("-" * 40)
    
    # بررسی فایل‌های لاگ ایجاد شده
    print("🔍 بررسی فایل‌های لاگ ایجاد شده...")
    logs_dir = './logs'
    
    if os.path.exists(logs_dir):
        log_files = [f for f in os.listdir(logs_dir) if f.endswith('.log')]
        if log_files:
            print(f"✅ {len(log_files)} فایل لاگ ایجاد شد:")
            for log_file in log_files:
                file_path = os.path.join(logs_dir, log_file)
                file_size = os.path.getsize(file_path)
                print(f"   - {log_file}: {file_size} بایت")
                
                # نمایش محتوای فایل
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.strip().split('\n')
                        print(f"     محتوا ({len(lines)} خط):")
                        for i, line in enumerate(lines[-3:], 1):  # آخرین 3 خط
                            print(f"       {i}: {line}")
                except Exception as e:
                    print(f"     ❌ خطا در خواندن فایل: {e}")
        else:
            print("❌ هیچ فایل لاگی ایجاد نشد")
    else:
        print("❌ پوشه logs وجود ندارد")
    
    print("-" * 40)
    
    # تست لاگرهای مختلف
    print("🔍 تست لاگرهای مختلف...")
    try:
        youtube_logger = get_logger('youtube_test')
        instagram_logger = get_logger('instagram_test')
        database_logger = get_logger('database_test')
        
        youtube_logger.info("تست دانلود یوتیوب")
        instagram_logger.info("تست دانلود اینستاگرام")
        database_logger.info("تست عملیات دیتابیس")
        
        print("✅ لاگرهای مختلف کار می‌کنند")
    except Exception as e:
        print(f"❌ خطا در لاگرهای مختلف: {e}")
    
    print("=" * 60)
    print("🏁 تست سیستم لاگ‌گذاری تمام شد")

if __name__ == "__main__":
    test_logging_system()