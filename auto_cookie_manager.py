#!/usr/bin/env python3
"""
سیستم مدیریت خودکار کوکی برای YouTube
Auto Cookie Management System for YouTube
"""

import os
import sys
import json
import sqlite3
import shutil
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import platform
import tempfile

class AutoCookieManager:
    def __init__(self):
        self.setup_logging()
        self.system = platform.system().lower()
        self.cookie_dir = Path.cwd() / "cookies"
        self.cookie_dir.mkdir(exist_ok=True)
        
        # مسیرهای مرورگرها
        self.browser_paths = self.get_browser_paths()
        
        # فایل‌های کوکی خروجی
        self.netscape_file = self.cookie_dir / "youtube_cookies.txt"
        self.json_file = self.cookie_dir / "youtube_cookies.json"
        
    def setup_logging(self):
        """تنظیم سیستم لاگ"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('auto_cookie_manager.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def get_browser_paths(self):
        """دریافت مسیرهای مرورگرها بر اساس سیستم عامل"""
        paths = {}
        
        if self.system == "windows":
            user_data = os.path.expanduser("~")
            paths = {
                'chrome': f"{user_data}\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Cookies",
                'edge': f"{user_data}\\AppData\\Local\\Microsoft\\Edge\\User Data\\Default\\Cookies",
                'firefox': self.find_firefox_profile_windows(),
                'chromium': f"{user_data}\\AppData\\Local\\Chromium\\User Data\\Default\\Cookies"
            }
        elif self.system == "linux":
            home = os.path.expanduser("~")
            paths = {
                'chrome': f"{home}/.config/google-chrome/Default/Cookies",
                'chromium': f"{home}/.config/chromium/Default/Cookies",
                'firefox': self.find_firefox_profile_linux(),
                'edge': f"{home}/.config/microsoft-edge/Default/Cookies"
            }
        elif self.system == "darwin":  # macOS
            home = os.path.expanduser("~")
            paths = {
                'chrome': f"{home}/Library/Application Support/Google/Chrome/Default/Cookies",
                'edge': f"{home}/Library/Application Support/Microsoft Edge/Default/Cookies",
                'firefox': self.find_firefox_profile_mac(),
                'safari': f"{home}/Library/Cookies/Cookies.binarycookies"
            }
        
        return paths
    
    def find_firefox_profile_windows(self):
        """پیدا کردن پروفایل Firefox در ویندوز"""
        try:
            profiles_path = os.path.expanduser("~\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles")
            if os.path.exists(profiles_path):
                for profile in os.listdir(profiles_path):
                    if profile.endswith('.default-release') or 'default' in profile:
                        return f"{profiles_path}\\{profile}\\cookies.sqlite"
        except:
            pass
        return None
    
    def find_firefox_profile_linux(self):
        """پیدا کردن پروفایل Firefox در لینوکس"""
        try:
            profiles_path = os.path.expanduser("~/.mozilla/firefox")
            if os.path.exists(profiles_path):
                for profile in os.listdir(profiles_path):
                    if profile.endswith('.default-release') or 'default' in profile:
                        return f"{profiles_path}/{profile}/cookies.sqlite"
        except:
            pass
        return None
    
    def find_firefox_profile_mac(self):
        """پیدا کردن پروفایل Firefox در macOS"""
        try:
            profiles_path = os.path.expanduser("~/Library/Application Support/Firefox/Profiles")
            if os.path.exists(profiles_path):
                for profile in os.listdir(profiles_path):
                    if profile.endswith('.default-release') or 'default' in profile:
                        return f"{profiles_path}/{profile}/cookies.sqlite"
        except:
            pass
        return None
    
    def extract_chrome_cookies(self, cookie_db_path):
        """استخراج کوکی‌های YouTube از Chrome/Chromium/Edge"""
        if not os.path.exists(cookie_db_path):
            return []
        
        cookies = []
        temp_db = None
        
        try:
            # کپی موقت از پایگاه داده
            temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
            shutil.copy2(cookie_db_path, temp_db.name)
            temp_db.close()
            
            conn = sqlite3.connect(temp_db.name)
            cursor = conn.cursor()
            
            # استعلام کوکی‌های YouTube
            query = """
            SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly
            FROM cookies 
            WHERE host_key LIKE '%youtube.com%' OR host_key LIKE '%google.com%'
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            for row in rows:
                name, value, domain, path, expires, secure, httponly = row
                
                # تبدیل زمان انقضا
                if expires:
                    # Chrome uses microseconds since Windows epoch (1601-01-01)
                    # Convert to Unix timestamp
                    expires_timestamp = (expires / 1000000) - 11644473600
                    expires_date = datetime.fromtimestamp(expires_timestamp)
                else:
                    expires_date = datetime.now() + timedelta(days=365)
                
                cookie = {
                    'name': name,
                    'value': value,
                    'domain': domain,
                    'path': path,
                    'expires': expires_date,
                    'secure': bool(secure),
                    'httponly': bool(httponly)
                }
                cookies.append(cookie)
            
            conn.close()
            
        except Exception as e:
            self.logger.error(f"خطا در استخراج کوکی‌های Chrome: {e}")
        finally:
            if temp_db and os.path.exists(temp_db.name):
                os.unlink(temp_db.name)
        
        return cookies
    
    def extract_firefox_cookies(self, cookie_db_path):
        """استخراج کوکی‌های YouTube از Firefox"""
        if not os.path.exists(cookie_db_path):
            return []
        
        cookies = []
        temp_db = None
        
        try:
            # کپی موقت از پایگاه داده
            temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
            shutil.copy2(cookie_db_path, temp_db.name)
            temp_db.close()
            
            conn = sqlite3.connect(temp_db.name)
            cursor = conn.cursor()
            
            # استعلام کوکی‌های YouTube
            query = """
            SELECT name, value, host, path, expiry, isSecure, isHttpOnly
            FROM moz_cookies 
            WHERE host LIKE '%youtube.com%' OR host LIKE '%google.com%'
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            for row in rows:
                name, value, domain, path, expires, secure, httponly = row
                
                # تبدیل زمان انقضا
                if expires:
                    expires_date = datetime.fromtimestamp(expires)
                else:
                    expires_date = datetime.now() + timedelta(days=365)
                
                cookie = {
                    'name': name,
                    'value': value,
                    'domain': domain,
                    'path': path,
                    'expires': expires_date,
                    'secure': bool(secure),
                    'httponly': bool(httponly)
                }
                cookies.append(cookie)
            
            conn.close()
            
        except Exception as e:
            self.logger.error(f"خطا در استخراج کوکی‌های Firefox: {e}")
        finally:
            if temp_db and os.path.exists(temp_db.name):
                os.unlink(temp_db.name)
        
        return cookies
    
    def save_cookies_netscape(self, cookies):
        """ذخیره کوکی‌ها در فرمت Netscape"""
        try:
            with open(self.netscape_file, 'w', encoding='utf-8') as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write("# This is a generated file! Do not edit.\n\n")
                
                for cookie in cookies:
                    domain = cookie['domain']
                    if domain.startswith('.'):
                        domain_flag = 'TRUE'
                    else:
                        domain_flag = 'FALSE'
                        domain = '.' + domain if not domain.startswith('.') else domain
                    
                    path = cookie['path']
                    secure = 'TRUE' if cookie['secure'] else 'FALSE'
                    expires = int(cookie['expires'].timestamp()) if cookie['expires'] else 0
                    name = cookie['name']
                    value = cookie['value']
                    
                    line = f"{domain}\t{domain_flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}\n"
                    f.write(line)
            
            self.logger.info(f"✓ کوکی‌ها در فرمت Netscape ذخیره شدند: {self.netscape_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"خطا در ذخیره کوکی‌های Netscape: {e}")
            return False
    
    def save_cookies_json(self, cookies):
        """ذخیره کوکی‌ها در فرمت JSON"""
        try:
            json_cookies = []
            for cookie in cookies:
                json_cookie = {
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': cookie['domain'],
                    'path': cookie['path'],
                    'expires': cookie['expires'].isoformat() if cookie['expires'] else None,
                    'secure': cookie['secure'],
                    'httpOnly': cookie['httponly']
                }
                json_cookies.append(json_cookie)
            
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(json_cookies, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"✓ کوکی‌ها در فرمت JSON ذخیره شدند: {self.json_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"خطا در ذخیره کوکی‌های JSON: {e}")
            return False
    
    def auto_extract_cookies(self):
        """استخراج خودکار کوکی‌ها از تمام مرورگرها"""
        all_cookies = []
        successful_browsers = []
        
        self.logger.info("🔍 شروع استخراج خودکار کوکی‌ها...")
        
        for browser, path in self.browser_paths.items():
            if not path or not os.path.exists(path):
                self.logger.warning(f"⚠️ مسیر {browser} پیدا نشد: {path}")
                continue
            
            self.logger.info(f"📂 استخراج کوکی‌ها از {browser}...")
            
            try:
                if browser == 'firefox':
                    cookies = self.extract_firefox_cookies(path)
                else:
                    cookies = self.extract_chrome_cookies(path)
                
                if cookies:
                    all_cookies.extend(cookies)
                    successful_browsers.append(browser)
                    self.logger.info(f"✓ {len(cookies)} کوکی از {browser} استخراج شد")
                else:
                    self.logger.warning(f"⚠️ هیچ کوکی YouTube در {browser} پیدا نشد")
                    
            except Exception as e:
                self.logger.error(f"❌ خطا در استخراج کوکی‌های {browser}: {e}")
        
        if all_cookies:
            # حذف کوکی‌های تکراری
            unique_cookies = []
            seen = set()
            
            for cookie in all_cookies:
                key = (cookie['name'], cookie['domain'])
                if key not in seen:
                    seen.add(key)
                    unique_cookies.append(cookie)
            
            self.logger.info(f"🎯 مجموع {len(unique_cookies)} کوکی منحصر به فرد پیدا شد")
            
            # ذخیره کوکی‌ها
            netscape_success = self.save_cookies_netscape(unique_cookies)
            json_success = self.save_cookies_json(unique_cookies)
            
            if netscape_success or json_success:
                self.logger.info(f"🎉 کوکی‌ها با موفقیت از {', '.join(successful_browsers)} استخراج شدند")
                return True
            else:
                self.logger.error("❌ خطا در ذخیره کوکی‌ها")
                return False
        else:
            self.logger.error("❌ هیچ کوکی YouTube پیدا نشد")
            return False
    
    def test_cookies(self):
        """تست کوکی‌ها با yt-dlp"""
        self.logger.info("🧪 تست کوکی‌ها با yt-dlp...")
        
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll for testing
        
        # تست با فایل Netscape
        if self.netscape_file.exists():
            try:
                cmd = [
                    'yt-dlp',
                    '--cookies', str(self.netscape_file),
                    '--simulate',
                    '--quiet',
                    test_url
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=30)
                
                if result.returncode == 0:
                    self.logger.info("✅ تست کوکی‌های Netscape موفق بود")
                    return True
                else:
                    self.logger.warning(f"⚠️ تست کوکی‌های Netscape ناموفق: {result.stderr}")
                    
            except Exception as e:
                self.logger.error(f"❌ خطا در تست کوکی‌ها: {e}")
        
        return False
    
    def create_symlinks(self):
        """ایجاد لینک‌های نمادین برای دسترسی آسان"""
        try:
            # لینک در دایرکتوری اصلی
            main_cookie_file = Path.cwd() / "youtube_cookies.txt"
            main_json_file = Path.cwd() / "youtube_cookies.json"
            
            # حذف لینک‌های قدیمی
            if main_cookie_file.exists():
                main_cookie_file.unlink()
            if main_json_file.exists():
                main_json_file.unlink()
            
            # ایجاد لینک‌های جدید
            if self.netscape_file.exists():
                if self.system == "windows":
                    shutil.copy2(self.netscape_file, main_cookie_file)
                else:
                    main_cookie_file.symlink_to(self.netscape_file)
                self.logger.info(f"✓ لینک ایجاد شد: {main_cookie_file}")
            
            if self.json_file.exists():
                if self.system == "windows":
                    shutil.copy2(self.json_file, main_json_file)
                else:
                    main_json_file.symlink_to(self.json_file)
                self.logger.info(f"✓ لینک ایجاد شد: {main_json_file}")
                
        except Exception as e:
            self.logger.error(f"خطا در ایجاد لینک‌ها: {e}")
    
    def run_auto_management(self):
        """اجرای مدیریت خودکار کامل"""
        self.logger.info("🚀 شروع مدیریت خودکار کوکی‌ها...")
        
        # استخراج کوکی‌ها
        if self.auto_extract_cookies():
            # ایجاد لینک‌ها
            self.create_symlinks()
            
            # تست کوکی‌ها
            if self.test_cookies():
                self.logger.info("🎉 مدیریت خودکار کوکی‌ها با موفقیت تکمیل شد!")
                return True
            else:
                self.logger.warning("⚠️ کوکی‌ها استخراج شدند اما تست ناموفق بود")
                return True  # Still consider it successful
        else:
            self.logger.error("❌ مدیریت خودکار کوکی‌ها ناموفق بود")
            return False

def main():
    """تابع اصلی"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
    else:
        command = "auto"
    
    manager = AutoCookieManager()
    
    if command == "auto":
        success = manager.run_auto_management()
        sys.exit(0 if success else 1)
    elif command == "extract":
        success = manager.auto_extract_cookies()
        sys.exit(0 if success else 1)
    elif command == "test":
        success = manager.test_cookies()
        sys.exit(0 if success else 1)
    else:
        print("استفاده: python auto_cookie_manager.py [auto|extract|test]")
        print("auto: مدیریت خودکار کامل (پیش‌فرض)")
        print("extract: فقط استخراج کوکی‌ها")
        print("test: فقط تست کوکی‌ها")
        sys.exit(1)

if __name__ == "__main__":
    main()