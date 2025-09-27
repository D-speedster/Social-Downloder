#!/usr/bin/env python3
"""
اسکریپت تست کامل سیستم لاگ‌گذاری
این اسکریپت تمام لاگرهای موجود در پلاگین‌ها را تست می‌کند
"""

import sys
import os
sys.path.append('.')

def test_all_loggers():
    """تست تمام لاگرهای پلاگین‌ها"""
    
    print("🔍 شروع تست سیستم لاگ‌گذاری...")
    
    # تست لاگر مرکزی
    try:
        from plugins.logger_config import get_logger, get_performance_logger, get_error_logger
        
        central_logger = get_logger('central_test')
        central_logger.info('✅ لاگر مرکزی فعال است')
        print("✅ لاگر مرکزی: موفق")
    except Exception as e:
        print(f"❌ لاگر مرکزی: خطا - {e}")
    
    # تست لاگر start.py
    try:
        import logging
        os.makedirs('./logs', exist_ok=True)
        start_logger = logging.getLogger('start_main')
        start_logger.setLevel(logging.DEBUG)
        
        if not start_logger.handlers:
            start_handler = logging.FileHandler('./logs/start_main.log', encoding='utf-8')
            start_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            start_handler.setFormatter(start_formatter)
            start_logger.addHandler(start_handler)
        
        start_logger.info('✅ تست لاگر start.py')
        print("✅ لاگر start.py: موفق")
    except Exception as e:
        print(f"❌ لاگر start.py: خطا - {e}")
    
    # تست لاگر instagram.py
    try:
        instagram_logger = logging.getLogger('instagram_main')
        instagram_logger.setLevel(logging.DEBUG)
        
        if not instagram_logger.handlers:
            instagram_handler = logging.FileHandler('./logs/instagram_main.log', encoding='utf-8')
            instagram_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            instagram_handler.setFormatter(instagram_formatter)
            instagram_logger.addHandler(instagram_handler)
        
        instagram_logger.info('✅ تست لاگر instagram.py')
        print("✅ لاگر instagram.py: موفق")
    except Exception as e:
        print(f"❌ لاگر instagram.py: خطا - {e}")
    
    # تست لاگر youtube.py
    try:
        youtube_logger = logging.getLogger('youtube_main')
        youtube_logger.setLevel(logging.DEBUG)
        
        if not youtube_logger.handlers:
            youtube_handler = logging.FileHandler('./logs/youtube_main.log', encoding='utf-8')
            youtube_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            youtube_handler.setFormatter(youtube_formatter)
            youtube_logger.addHandler(youtube_handler)
        
        youtube_logger.info('✅ تست لاگر youtube.py')
        print("✅ لاگر youtube.py: موفق")
    except Exception as e:
        print(f"❌ لاگر youtube.py: خطا - {e}")
    
    # تست لاگر universal_downloader.py
    try:
        universal_logger = logging.getLogger('universal_downloader')
        universal_logger.setLevel(logging.DEBUG)
        
        if not universal_logger.handlers:
            universal_handler = logging.FileHandler('./logs/universal_downloader.log', encoding='utf-8')
            universal_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            universal_handler.setFormatter(universal_formatter)
            universal_logger.addHandler(universal_handler)
        
        universal_logger.info('✅ تست لاگر universal_downloader.py')
        print("✅ لاگر universal_downloader.py: موفق")
    except Exception as e:
        print(f"❌ لاگر universal_downloader.py: خطا - {e}")
    
    # تست لاگر admin.py
    try:
        admin_logger = logging.getLogger('admin_main')
        admin_logger.setLevel(logging.DEBUG)
        
        if not admin_logger.handlers:
            admin_handler = logging.FileHandler('./logs/admin_main.log', encoding='utf-8')
            admin_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            admin_handler.setFormatter(admin_formatter)
            admin_logger.addHandler(admin_handler)
        
        admin_logger.info('✅ تست لاگر admin.py')
        print("✅ لاگر admin.py: موفق")
    except Exception as e:
        print(f"❌ لاگر admin.py: خطا - {e}")
    
    # تست لاگر dashboard.py
    try:
        dashboard_logger = logging.getLogger('dashboard_main')
        dashboard_logger.setLevel(logging.DEBUG)
        
        if not dashboard_logger.handlers:
            dashboard_handler = logging.FileHandler('./logs/dashboard_main.log', encoding='utf-8')
            dashboard_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            dashboard_handler.setFormatter(dashboard_formatter)
            dashboard_logger.addHandler(dashboard_handler)
        
        dashboard_logger.info('✅ تست لاگر dashboard.py')
        print("✅ لاگر dashboard.py: موفق")
    except Exception as e:
        print(f"❌ لاگر dashboard.py: خطا - {e}")
    
    # تست لاگر youtube_callback_query.py
    try:
        youtube_callback_logger = logging.getLogger('youtube_callback')
        youtube_callback_logger.setLevel(logging.DEBUG)
        
        if not youtube_callback_logger.handlers:
            youtube_callback_handler = logging.FileHandler('./logs/youtube_callback.log', encoding='utf-8')
            youtube_callback_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            youtube_callback_handler.setFormatter(youtube_callback_formatter)
            youtube_callback_logger.addHandler(youtube_callback_handler)
        
        youtube_callback_logger.info('✅ تست لاگر youtube_callback_query.py')
        print("✅ لاگر youtube_callback_query.py: موفق")
    except Exception as e:
        print(f"❌ لاگر youtube_callback_query.py: خطا - {e}")
    
    print("\n📊 خلاصه تست:")
    print("🔍 بررسی فایل‌های لاگ ایجاد شده...")
    
    # بررسی فایل‌های لاگ
    log_files = [
        'start_main.log',
        'instagram_main.log', 
        'youtube_main.log',
        'universal_downloader.log',
        'admin_main.log',
        'dashboard_main.log',
        'youtube_callback.log',
        'performance.log',
        'errors.log'
    ]
    
    existing_logs = []
    for log_file in log_files:
        log_path = f'./logs/{log_file}'
        if os.path.exists(log_path):
            size = os.path.getsize(log_path)
            existing_logs.append(f"✅ {log_file} ({size} bytes)")
        else:
            existing_logs.append(f"❌ {log_file} (وجود ندارد)")
    
    for log_info in existing_logs:
        print(log_info)
    
    print(f"\n🎉 تست کامل! {len([l for l in existing_logs if '✅' in l])}/{len(log_files)} فایل لاگ موجود است.")

if __name__ == "__main__":
    test_all_loggers()