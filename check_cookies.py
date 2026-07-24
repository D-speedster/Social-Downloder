#!/usr/bin/env python3
"""بررسی کوکی‌های موجود در دیتابیس"""

import os
import sys

# اضافه کردن پوشه plugins به path
sys.path.insert(0, os.path.dirname(__file__))

# Mock config برای جلوگیری از خطای import
class MockConfig:
    USE_MYSQL = False
    db_config = {}

sys.modules['config'] = MockConfig()

from plugins.db_wrapper import DB

def main():
    db = DB()
    cookies = db.list_cookies(limit=10)
    
    print("\n" + "="*60)
    print("🍪 لیست کوکی‌های موجود:")
    print("="*60)
    
    if not cookies:
        print("❌ هیچ کوکی‌ای در دیتابیس وجود ندارد!")
        return
    
    for cookie in cookies:
        print(f"\n📋 کوکی #{cookie['id']}")
        print(f"   نام: {cookie['name']}")
        print(f"   نوع: {cookie['source_type']}")
        print(f"   وضعیت: {cookie['status']}")
        print(f"   استفاده: {cookie['use_count']} بار")
        print(f"   شکست: {cookie.get('fail_count', 0)} بار")
        print(f"   تاریخ ایجاد: {cookie['created_at']}")
        
        # بررسی محتوای کوکی
        cookie_text = db.get_cookie_by_id(cookie['id']).get('cookie_text', '')
        lines = [l for l in cookie_text.splitlines() if l.strip() and not l.startswith('#')]
        print(f"   تعداد خطوط معتبر: {len(lines)}")
        
        # بررسی وجود کوکی‌های مهم
        important_cookies = ['SAPISID', 'APISID', 'HSID', 'SSID', 'SID']
        found_cookies = []
        for line in lines:
            parts = line.split('\t')
            if len(parts) >= 6:
                cookie_name = parts[5] if len(parts) > 5 else parts[-2]
                if cookie_name in important_cookies:
                    found_cookies.append(cookie_name)
        
        if found_cookies:
            print(f"   کوکی‌های مهم یافت شده: {', '.join(found_cookies)}")
        else:
            print(f"   ⚠️ هیچ کوکی مهم یوتیوب یافت نشد!")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
