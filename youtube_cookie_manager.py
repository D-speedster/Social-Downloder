#!/usr/bin/env python3
"""
YouTube Cookie Manager - حل مشکل احراز هویت YouTube
این اسکریپت کوکی‌های YouTube را از مرورگرهای مختلف استخراج می‌کند
"""

import os
import sys
import json
import sqlite3
import shutil
import tempfile
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests
from datetime import datetime

# تنظیم لاگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class YouTubeCookieManager:
    """مدیریت کوکی‌های YouTube برای حل مشکل احراز هویت"""
    
    def __init__(self):
        self.cookie_file = "youtube_cookies.txt"
        self.cookie_json = "youtube_cookies.json"
        self.browsers = {
            'chrome': self._get_chrome_cookies,
            'firefox': self._get_firefox_cookies,
            'edge': self._get_edge_cookies,
            'chromium': self._get_chromium_cookies
        }
        
    def extract_cookies_from_browser(self, browser: str = 'auto') -> bool:
        """استخراج کوکی‌ها از مرورگر"""
        try:
            if browser == 'auto':
                # تلاش برای تمام مرورگرها
                for browser_name in self.browsers:
                    logger.info(f"تلاش برای استخراج کوکی از {browser_name}...")
                    if self._extract_from_browser(browser_name):
                        logger.info(f"✓ کوکی‌ها با موفقیت از {browser_name} استخراج شد")
                        return True
                return False
            else:
                return self._extract_from_browser(browser)
                
        except Exception as e:
            logger.error(f"خطا در استخراج کوکی: {e}")
            return False
    
    def _extract_from_browser(self, browser: str) -> bool:
        """استخراج کوکی از مرورگر خاص"""
        try:
            if browser in self.browsers:
                cookies = self.browsers[browser]()
                if cookies:
                    self._save_cookies(cookies)
                    return True
            return False
        except Exception as e:
            logger.error(f"خطا در استخراج از {browser}: {e}")
            return False
    
    def _get_chrome_cookies(self) -> List[Dict]:
        """استخراج کوکی‌های Chrome"""
        try:
            # مسیرهای مختلف Chrome در لینوکس
            chrome_paths = [
                os.path.expanduser("~/.config/google-chrome/Default/Cookies"),
                os.path.expanduser("~/.config/google-chrome/Profile 1/Cookies"),
                os.path.expanduser("~/.config/chromium/Default/Cookies"),
                "/root/.config/google-chrome/Default/Cookies",
                "/home/*/.config/google-chrome/Default/Cookies"
            ]
            
            for path in chrome_paths:
                if os.path.exists(path):
                    return self._extract_from_sqlite(path, 'chrome')
            
            logger.warning("فایل کوکی Chrome پیدا نشد")
            return []
            
        except Exception as e:
            logger.error(f"خطا در استخراج کوکی Chrome: {e}")
            return []
    
    def _get_firefox_cookies(self) -> List[Dict]:
        """استخراج کوکی‌های Firefox"""
        try:
            firefox_paths = [
                os.path.expanduser("~/.mozilla/firefox/"),
                "/root/.mozilla/firefox/"
            ]
            
            for base_path in firefox_paths:
                if os.path.exists(base_path):
                    # پیدا کردن پروفایل پیش‌فرض
                    for item in os.listdir(base_path):
                        if item.endswith('.default-release') or item.endswith('.default'):
                            cookie_path = os.path.join(base_path, item, 'cookies.sqlite')
                            if os.path.exists(cookie_path):
                                return self._extract_from_sqlite(cookie_path, 'firefox')
            
            logger.warning("فایل کوکی Firefox پیدا نشد")
            return []
            
        except Exception as e:
            logger.error(f"خطا در استخراج کوکی Firefox: {e}")
            return []
    
    def _get_edge_cookies(self) -> List[Dict]:
        """استخراج کوکی‌های Edge"""
        try:
            edge_paths = [
                os.path.expanduser("~/.config/microsoft-edge/Default/Cookies"),
                "/root/.config/microsoft-edge/Default/Cookies"
            ]
            
            for path in edge_paths:
                if os.path.exists(path):
                    return self._extract_from_sqlite(path, 'edge')
            
            logger.warning("فایل کوکی Edge پیدا نشد")
            return []
            
        except Exception as e:
            logger.error(f"خطا در استخراج کوکی Edge: {e}")
            return []
    
    def _get_chromium_cookies(self) -> List[Dict]:
        """استخراج کوکی‌های Chromium"""
        try:
            chromium_paths = [
                os.path.expanduser("~/.config/chromium/Default/Cookies"),
                "/root/.config/chromium/Default/Cookies"
            ]
            
            for path in chromium_paths:
                if os.path.exists(path):
                    return self._extract_from_sqlite(path, 'chromium')
            
            logger.warning("فایل کوکی Chromium پیدا نشد")
            return []
            
        except Exception as e:
            logger.error(f"خطا در استخراج کوکی Chromium: {e}")
            return []
    
    def _extract_from_sqlite(self, db_path: str, browser: str) -> List[Dict]:
        """استخراج کوکی‌ها از پایگاه داده SQLite"""
        try:
            # کپی موقت از فایل کوکی
            temp_db = tempfile.mktemp(suffix='.db')
            shutil.copy2(db_path, temp_db)
            
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            # کوئری برای استخراج کوکی‌های YouTube
            if browser == 'firefox':
                query = """
                SELECT name, value, host, path, expiry, isSecure, isHttpOnly
                FROM moz_cookies 
                WHERE host LIKE '%youtube.com%' OR host LIKE '%google.com%'
                """
            else:
                query = """
                SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly
                FROM cookies 
                WHERE host_key LIKE '%youtube.com%' OR host_key LIKE '%google.com%'
                """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            cookies = []
            for row in rows:
                cookie = {
                    'name': row[0],
                    'value': row[1],
                    'domain': row[2],
                    'path': row[3],
                    'expires': row[4] if row[4] else 0,
                    'secure': bool(row[5]),
                    'httponly': bool(row[6]) if len(row) > 6 else False
                }
                cookies.append(cookie)
            
            conn.close()
            os.unlink(temp_db)
            
            logger.info(f"✓ {len(cookies)} کوکی از {browser} استخراج شد")
            return cookies
            
        except Exception as e:
            logger.error(f"خطا در استخراج از SQLite: {e}")
            return []
    
    def _save_cookies(self, cookies: List[Dict]):
        """ذخیره کوکی‌ها در فرمت‌های مختلف"""
        try:
            # ذخیره در فرمت Netscape (برای yt-dlp)
            with open(self.cookie_file, 'w') as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write("# This is a generated file! Do not edit.\n\n")
                
                for cookie in cookies:
                    domain = cookie['domain']
                    if domain.startswith('.'):
                        domain_flag = 'TRUE'
                    else:
                        domain_flag = 'FALSE'
                    
                    secure = 'TRUE' if cookie['secure'] else 'FALSE'
                    expires = str(cookie['expires']) if cookie['expires'] else '0'
                    
                    line = f"{domain}\t{domain_flag}\t{cookie['path']}\t{secure}\t{expires}\t{cookie['name']}\t{cookie['value']}\n"
                    f.write(line)
            
            # ذخیره در فرمت JSON
            with open(self.cookie_json, 'w') as f:
                json.dump(cookies, f, indent=2)
            
            logger.info(f"✓ کوکی‌ها در {self.cookie_file} و {self.cookie_json} ذخیره شد")
            
        except Exception as e:
            logger.error(f"خطا در ذخیره کوکی‌ها: {e}")
    
    def create_manual_cookies(self) -> bool:
        """ایجاد کوکی‌های دستی برای تست"""
        try:
            logger.info("ایجاد کوکی‌های دستی...")
            
            # کوکی‌های پایه برای YouTube
            manual_cookies = [
                {
                    'name': 'CONSENT',
                    'value': 'YES+cb.20210328-17-p0.en+FX+667',
                    'domain': '.youtube.com',
                    'path': '/',
                    'expires': 0,
                    'secure': True,
                    'httponly': False
                },
                {
                    'name': 'VISITOR_INFO1_LIVE',
                    'value': 'dGVzdF92aXNpdG9y',
                    'domain': '.youtube.com',
                    'path': '/',
                    'expires': 0,
                    'secure': True,
                    'httponly': False
                }
            ]
            
            self._save_cookies(manual_cookies)
            return True
            
        except Exception as e:
            logger.error(f"خطا در ایجاد کوکی‌های دستی: {e}")
            return False
    
    def test_cookies(self) -> bool:
        """تست کوکی‌ها با YouTube"""
        try:
            if not os.path.exists(self.cookie_file):
                logger.error("فایل کوکی وجود ندارد")
                return False
            
            # تست با yt-dlp
            test_url = "https://www.youtube.com/watch?v=dL_r_PPlFtI"
            cmd = [
                'yt-dlp',
                '--cookies', self.cookie_file,
                '--no-download',
                '--get-title',
                test_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info("✓ تست کوکی‌ها موفق بود")
                return True
            else:
                logger.error(f"تست کوکی‌ها ناموفق: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"خطا در تست کوکی‌ها: {e}")
            return False
    
    def get_session_cookies(self) -> Dict:
        """دریافت کوکی‌های session برای استفاده در requests"""
        try:
            if not os.path.exists(self.cookie_json):
                return {}
            
            with open(self.cookie_json, 'r') as f:
                cookies = json.load(f)
            
            session_cookies = {}
            for cookie in cookies:
                session_cookies[cookie['name']] = cookie['value']
            
            return session_cookies
            
        except Exception as e:
            logger.error(f"خطا در دریافت session cookies: {e}")
            return {}

def main():
    """تابع اصلی"""
    print("🍪 YouTube Cookie Manager")
    print("=" * 40)
    
    manager = YouTubeCookieManager()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'extract':
            browser = sys.argv[2] if len(sys.argv) > 2 else 'auto'
            success = manager.extract_cookies_from_browser(browser)
            if success:
                print("✅ کوکی‌ها با موفقیت استخراج شد")
                manager.test_cookies()
            else:
                print("❌ استخراج کوکی‌ها ناموفق بود")
                print("💡 تلاش برای ایجاد کوکی‌های دستی...")
                manager.create_manual_cookies()
        
        elif command == 'test':
            success = manager.test_cookies()
            if success:
                print("✅ کوکی‌ها معتبر هستند")
            else:
                print("❌ کوکی‌ها معتبر نیستند")
        
        elif command == 'manual':
            success = manager.create_manual_cookies()
            if success:
                print("✅ کوکی‌های دستی ایجاد شد")
            else:
                print("❌ ایجاد کوکی‌های دستی ناموفق بود")
        
        else:
            print("❌ دستور نامعتبر")
            print("استفاده: python3 youtube_cookie_manager.py [extract|test|manual] [browser]")
    
    else:
        # حالت تعاملی
        print("1. استخراج کوکی‌ها از مرورگر")
        print("2. تست کوکی‌های موجود")
        print("3. ایجاد کوکی‌های دستی")
        
        try:
            choice = input("\nانتخاب کنید (1-3): ").strip()
            
            if choice == '1':
                print("\nمرورگرهای موجود:")
                print("- auto (همه مرورگرها)")
                print("- chrome")
                print("- firefox")
                print("- edge")
                print("- chromium")
                
                browser = input("مرورگر را انتخاب کنید (پیش‌فرض: auto): ").strip() or 'auto'
                
                success = manager.extract_cookies_from_browser(browser)
                if success:
                    print("✅ کوکی‌ها با موفقیت استخراج شد")
                    manager.test_cookies()
                else:
                    print("❌ استخراج کوکی‌ها ناموفق بود")
            
            elif choice == '2':
                success = manager.test_cookies()
                if success:
                    print("✅ کوکی‌ها معتبر هستند")
                else:
                    print("❌ کوکی‌ها معتبر نیستند")
            
            elif choice == '3':
                success = manager.create_manual_cookies()
                if success:
                    print("✅ کوکی‌های دستی ایجاد شد")
                else:
                    print("❌ ایجاد کوکی‌های دستی ناموفق بود")
            
            else:
                print("❌ انتخاب نامعتبر")
                
        except KeyboardInterrupt:
            print("\n\n👋 خروج...")
            sys.exit(0)

if __name__ == "__main__":
    main()