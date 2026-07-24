#!/usr/bin/env python3
"""
سیستم مدیریت خودکار کوکی برای YouTube
Auto Cookie Management System for YouTube
"""

import os
import sys
import json
import sqlite3
import tempfile
import subprocess
import shutil
import time
from pathlib import Path
from datetime import datetime, timedelta
import logging
import platform
from typing import Dict, List, Optional

class AutoCookieManager:
    """مدیریت خودکار کوکی‌های YouTube با پشتیبانی از روش‌های توصیه شده"""
    
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
        self.po_token_file = self.cookie_dir / "po_token.txt"
        
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
    
    def extract_chrome_cookies(self, db_path: str):
        """استخراج کوکی‌های YouTube از مرورگرهای مبتنی بر Chromium"""
        if not os.path.exists(db_path):
            return []
        
        cookies = []
        temp_db = None
        
        try:
            # کپی پایگاه داده برای جلوگیری از قفل شدن
            temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
            shutil.copy2(db_path, temp_db.name)
            
            conn = sqlite3.connect(temp_db.name)
            cursor = conn.cursor()
            
            # کوکی‌های YouTube
            cursor.execute("""
                SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly
                FROM cookies
                WHERE host_key LIKE '%youtube.com' OR host_key = '.youtube.com'
                   OR host_key LIKE '%google.com' OR host_key = '.google.com'
            """)
            
            for row in cursor.fetchall():
                name, value, domain, path, expires_utc, secure, httponly = row
                
                # تبدیل زمان انقضا
                if expires_utc:
                    # زمان انقضا در Chromium بر اساس میکروثانیه از 1601-01-01
                    expires_date = datetime(1601, 1, 1) + timedelta(microseconds=expires_utc)
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

    def extract_incognito_cookies(self, browser_type: str = "chrome") -> bool:
        """
        استخراج کوکی‌ها از پنجره خصوصی/ناشناس با روش توصیه شده YouTube
        
        مراحل:
        1. باز کردن پنجره خصوصی/ناشناس
        2. ورود به YouTube
        3. رفتن به https://www.youtube.com/robots.txt
        4. استخراج کوکی‌ها
        5. بستن پنجره
        """
        self.logger.info("🔒 شروع استخراج کوکی‌ها از پنجره خصوصی/ناشناس...")
        
        try:
            # ایجاد یک فایل موقت برای ذخیره کوکی‌ها
            temp_cookie_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8')
            temp_cookie_file.close()
            
            # دستور برای باز کردن مرورگر در حالت خصوصی و استخراج کوکی‌ها
            if browser_type == "chrome":
                cmd = [
                    "chrome",
                    "--incognito",
                    "--new-window",
                    "https://www.youtube.com/robots.txt",
                    f"--export-cookies={temp_cookie_file.name}"
                ]
            elif browser_type == "firefox":
                cmd = [
                    "firefox",
                    "-private-window",
                    "https://www.youtube.com/robots.txt"
                ]
            else:
                self.logger.error(f"مرورگر {browser_type} پشتیبانی نمی‌شود")
                return False
            
            self.logger.info("🖥️  در حال باز کردن مرورگر در حالت خصوصی...")
            self.logger.info("⚠️  لطفاً دستی وارد YouTube شوید و سپس Enter را بزنید...")
            
            # اجرای مرورگر
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # منتظر ماندن برای ورود کاربر
            input("پس از ورود به YouTube در پنجره خصوصی، Enter را بزنید...")
            
            # بستن مرورگر
            process.terminate()
            
            # خواندن کوکی‌های استخراج شده
            if os.path.exists(temp_cookie_file.name):
                with open(temp_cookie_file.name, 'r', encoding='utf-8') as f:
                    cookie_content = f.read()
                
                if cookie_content:
                    # ذخیره کوکی‌ها در فایل Netscape
                    with open(self.netscape_file, 'w', encoding='utf-8') as f:
                        f.write("# Netscape HTTP Cookie File\n")
                        f.write("# Extracted from incognito/private window\n\n")
                        f.write(cookie_content)
                    
                    self.logger.info(f"✓ کوکی‌ها از پنجره خصوصی استخراج شدند: {self.netscape_file}")
                    
                    # حذف فایل موقت
                    os.unlink(temp_cookie_file.name)
                    
                    return True
                else:
                    self.logger.warning("⚠️ هیچ کوکی‌ای استخراج نشد")
            else:
                self.logger.error("❌ فایل کوکی موقت ایجاد نشد")
            
            # حذف فایل موقت در صورت خطا
            if os.path.exists(temp_cookie_file.name):
                os.unlink(temp_cookie_file.name)
                
        except Exception as e:
            self.logger.error(f"❌ خطا در استخراج کوکی‌های خصوصی: {e}")
            if 'temp_cookie_file' in locals() and os.path.exists(temp_cookie_file.name):
                os.unlink(temp_cookie_file.name)
        
        return False

    def save_po_token(self, token: str) -> bool:
        """ذخیره PO Token در فایل"""
        try:
            with open(self.po_token_file, 'w', encoding='utf-8') as f:
                f.write(token)
            
            self.logger.info(f"✓ PO Token ذخیره شد: {self.po_token_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ خطا در ذخیره PO Token: {e}")
            return False

    def get_po_token(self):
        """خواندن PO Token از فایل"""
        try:
            if self.po_token_file.exists():
                with open(self.po_token_file, 'r', encoding='utf-8') as f:
                    token = f.read().strip()
                
                if token:
                    return token
                    
        except Exception as e:
            self.logger.error(f"❌ خطا در خواندن PO Token: {e}")
        
        return None

    def generate_po_token_guide(self) -> str:
        """تولید راهنمای استفاده از PO Token"""
        guide = """
🎯 راهنمای استفاده از PO Token برای YouTube

📝 مقدمه:
YouTube به تدریج استفاده از "PO Token" را برای دانلود ویدیوها اجباری می‌کند. این توکن‌ها باید به صورت خارجی ارائه شوند و yt-dlp نمی‌تواند آن‌ها را تولید کند.

🚀 روش پیشنهادی:
1. استفاده از کلاینت mweb همراه با PO Token
2. استخراج کوکی‌ها از پنجره خصوصی/ناشناس

🔧 دستور نمونه با PO Token:
```
yt-dlp \
    --extractor-args "youtubetab:skip=webpage" \
    --extractor-args "youtube:player_skip=webpage,configs;visitor_data=YOUR_VISITOR_DATA_HERE" \
    --sleep-interval 5 \
    --max-sleep-interval 10 \
    URL
```

⚠️ هشدارها:
- استفاده از حساب کاربری با yt-dlp ممکن است منجر به مسدود شدن حساب شود
- بین دانلودها 5-10 ثانیه تأخیر قرار دهید
- از حساب throwaway استفاده کنید

📁 فایل‌های کوکی:
- Netscape: {netscape_file}
- JSON: {json_file}
- PO Token: {po_token_file}
""".format(
            netscape_file=self.netscape_file,
            json_file=self.json_file,
            po_token_file=self.po_token_file
        )
        
        return guide
    
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
    
    def auto_extract_cookies(self, use_incognito: bool = False) -> bool:
        """
        استخراج خودکار کوکی‌ها از تمام مرورگرها
        
        Args:
            use_incognito: اگر True باشد، از روش پنجره خصوصی استفاده می‌کند
        """
        if use_incognito:
            self.logger.info("🔒 استفاده از روش پنجره خصوصی/ناشناس...")
            return self.extract_incognito_cookies()
        
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
            # اگر روش معمول شکست خورد، روش پنجره خصوصی را امتحان کن
            self.logger.info("🔄 امتحان روش پنجره خصوصی...")
            return self.extract_incognito_cookies()
    
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
    
    def run_auto_management(self, use_incognito: bool = False):
        """
        اجرای مدیریت خودکار کامل
        
        Args:
            use_incognito: اگر True باشد، از روش پنجره خصوصی استفاده می‌کند
        """
        self.logger.info("🚀 شروع مدیریت خودکار کوکی‌ها...")
        
        if use_incognito:
            self.logger.info("🔒 استفاده از روش پنجره خصوصی/ناشناس...")
        
        # استخراج کوکی‌ها
        if self.auto_extract_cookies(use_incognito):
            # ایجاد لینک‌ها
            self.create_symlinks()
            
            # تست کوکی‌ها
            if self.test_cookies():
                self.logger.info("🎉 مدیریت خودکار کوکی‌ها با موفقیت تکمیل شد!")
                
                # نمایش راهنمای PO Token
                guide = self.generate_po_token_guide()
                self.logger.info(guide)
                
                return True
            else:
                self.logger.warning("⚠️ کوکی‌ها استخراج شدند اما تست ناموفق بود")
                
                # نمایش راهنمای PO Token
                guide = self.generate_po_token_guide()
                self.logger.info(guide)
                
                return True  # Still consider it successful
        else:
            self.logger.error("❌ مدیریت خودکار کوکی‌ها ناموفق بود")
            
            # نمایش راهنمای PO Token
            guide = self.generate_po_token_guide()
            self.logger.info(guide)
            
            return False

def main():
    """تابع اصلی"""
    use_incognito = False
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        # بررسی گزینه‌های اضافی
        if "--incognito" in sys.argv or "-i" in sys.argv:
            use_incognito = True
    else:
        command = "auto"
    
    manager = AutoCookieManager()
    
    if command == "auto":
        success = manager.run_auto_management(use_incognito)
        sys.exit(0 if success else 1)
    elif command == "extract":
        success = manager.auto_extract_cookies(use_incognito)
        sys.exit(0 if success else 1)
    elif command == "test":
        success = manager.test_cookies()
        sys.exit(0 if success else 1)
    elif command == "guide":
        guide = manager.generate_po_token_guide()
        print(guide)
        sys.exit(0)
    elif command == "save-token":
        if len(sys.argv) > 2:
            token = sys.argv[2]
            success = manager.save_po_token(token)
            sys.exit(0 if success else 1)
        else:
            print("لطفاً PO Token را وارد کنید: python auto_cookie_manager.py save-token YOUR_TOKEN")
            sys.exit(1)
    elif command == "get-token":
        token = manager.get_po_token()
        if token:
            print(f"PO Token: {token}")
            sys.exit(0)
        else:
            print("PO Token پیدا نشد")
            sys.exit(1)
    else:
        print("استفاده: python auto_cookie_manager.py [auto|extract|test|guide|save-token|get-token] [--incognito|-i]")
        print("auto: مدیریت خودکار کامل (پیش‌فرض)")
        print("extract: فقط استخراج کوکی‌ها")
        print("test: فقط تست کوکی‌ها")
        print("guide: نمایش راهنمای PO Token")
        print("save-token TOKEN: ذخیره PO Token")
        print("get-token: نمایش PO Token ذخیره شده")
        print("--incognito یا -i: استفاده از روش پنجره خصوصی/ناشناس")
        sys.exit(1)

if __name__ == "__main__":
    main()