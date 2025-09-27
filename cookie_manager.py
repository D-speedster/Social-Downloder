"""Cookie management utilities for YouTube and Instagram.

This module provides the CookieManager class used across plugins to store,
load, select, and convert cookies between JSON and Netscape formats. The
implementation maintains simple usage statistics and supports toggling
active status.
"""

import json
import os
import random
import time
from typing import List, Dict, Optional
from pathlib import Path


class CookieManager:
    """مدیریت استخر کوکی‌های یوتیوب و اینستاگرام"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.youtube_cookies_file = self.data_dir / "youtube_cookies.json"
        self.instagram_cookies_file = self.data_dir / "instagram_cookies.json"
        
        # ایجاد فایل‌های اولیه در صورت عدم وجود
        self._init_cookie_files()
    
    def _init_cookie_files(self):
        """ایجاد فایل‌های کوکی در صورت عدم وجود"""
        for file_path in [self.youtube_cookies_file, self.instagram_cookies_file]:
            if not file_path.exists():
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump([], f, indent=2, ensure_ascii=False)
    
    def _load_cookies(self, platform: str) -> List[Dict]:
        """بارگذاری کوکی‌های یک پلتفرم"""
        file_path = self.youtube_cookies_file if platform == 'youtube' else self.instagram_cookies_file
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _save_cookies(self, platform: str, cookies: List[Dict]):
        """ذخیره کوکی‌های یک پلتفرم"""
        file_path = self.youtube_cookies_file if platform == 'youtube' else self.instagram_cookies_file
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving cookies for {platform}: {e}")
            return False
    
    def add_cookie(self, platform: str, cookie_data: str, description: str = "") -> bool:
        """افزودن کوکی جدید به استخر
        
        Args:
            platform: 'youtube' یا 'instagram'
            cookie_data: محتوای کوکی (فرمت Netscape یا JSON)
            description: توضیحات اختیاری
        
        Returns:
            bool: موفقیت عملیات
        """
        if platform not in ['youtube', 'instagram']:
            return False
        
        # Validate cookie data
        cookie_data = cookie_data.strip()
        if not cookie_data or len(cookie_data) < 10:
            return False
            
        # Check for duplicate cookies
        cookies = self._load_cookies(platform)
        for existing_cookie in cookies:
            if existing_cookie.get('data') == cookie_data:
                # Cookie already exists, don't add duplicate
                return False
        
        # ایجاد شناسه یکتا برای کوکی
        cookie_id = len(cookies) + 1
        while any(c.get('id') == cookie_id for c in cookies):
            cookie_id += 1
        
        new_cookie = {
            'id': cookie_id,
            'data': cookie_data,
            'description': description or f"کوکی {platform} #{cookie_id}",
            'added_at': str(int(time.time())),
            'usage_count': 0,
            'last_used': None,
            'active': True
        }
        
        cookies.append(new_cookie)
        return self._save_cookies(platform, cookies)
    
    def get_cookies(self, platform: str, active_only: bool = True) -> List[Dict]:
        """دریافت لیست کوکی‌های یک پلتفرم
        
        Args:
            platform: 'youtube' یا 'instagram'
            active_only: فقط کوکی‌های فعال
        
        Returns:
            List[Dict]: لیست کوکی‌ها
        """
        cookies = self._load_cookies(platform)
        
        if active_only:
            cookies = [c for c in cookies if c.get('active', True)]
        
        return cookies
    
    def get_random_cookie(self, platform: str) -> Optional[Dict]:
        """انتخاب تصادفی یک کوکی فعال
        
        Args:
            platform: 'youtube' یا 'instagram'
        
        Returns:
            Optional[Dict]: کوکی انتخاب شده یا None
        """
        active_cookies = self.get_cookies(platform, active_only=True)
        
        if not active_cookies:
            return None
        
        # انتخاب تصادفی
        selected_cookie = random.choice(active_cookies)
        
        # به‌روزرسانی آمار استفاده
        self._update_cookie_usage(platform, selected_cookie['id'])
        
        return selected_cookie
    
    def get_least_used_cookie(self, platform: str) -> Optional[Dict]:
        """انتخاب کوکی با کمترین استفاده
        
        Args:
            platform: 'youtube' یا 'instagram'
        
        Returns:
            Optional[Dict]: کوکی انتخاب شده یا None
        """
        active_cookies = self.get_cookies(platform, active_only=True)
        
        if not active_cookies:
            return None
        
        # مرتب‌سازی بر اساس تعداد استفاده
        sorted_cookies = sorted(active_cookies, key=lambda x: x.get('usage_count', 0))
        selected_cookie = sorted_cookies[0]
        
        # به‌روزرسانی آمار استفاده
        self._update_cookie_usage(platform, selected_cookie['id'])
        
        return selected_cookie
    
    def get_cookie(self, platform: str) -> Optional[str]:
        """دریافت محتوای کوکی برای استفاده
        
        Args:
            platform: 'youtube' یا 'instagram'
        
        Returns:
            Optional[str]: محتوای کوکی یا None
        """
        cookie = self.get_least_used_cookie(platform)
        if cookie:
            cookie_data = cookie.get('data')
            # اگر کوکی در فرمت JSON است، آن را به فرمت Netscape تبدیل کن
            if isinstance(cookie_data, dict) or (isinstance(cookie_data, str) and cookie_data.strip().startswith('{')):
                return self._convert_to_netscape_format(cookie_data, platform)
            return cookie_data
        return None
    
    def _convert_to_netscape_format(self, cookie_data, platform: str) -> str:
        """تبدیل کوکی JSON به فرمت Netscape
        
        Args:
            cookie_data: داده کوکی در فرمت JSON
            platform: پلتفرم (youtube یا instagram)
        
        Returns:
            str: کوکی در فرمت Netscape
        """
        try:
            import json
            
            # اگر رشته است، آن را به dict تبدیل کن
            if isinstance(cookie_data, str):
                cookie_dict = json.loads(cookie_data)
            else:
                cookie_dict = cookie_data
            
            # اگر کوکی تست است، کوکی واقعی ایجاد کن
            if cookie_dict.get('test') == 'cookie':
                domain = f".{platform}.com"
                return f"# Netscape HTTP Cookie File\n{domain}\tTRUE\t/\tFALSE\t0\ttest_cookie\ttest_value\n"
            
            # تبدیل کوکی واقعی به فرمت Netscape
            netscape_lines = ["# Netscape HTTP Cookie File"]
            
            # اگر کوکی آرایه‌ای از کوکی‌ها است
            if isinstance(cookie_dict, list):
                for cookie in cookie_dict:
                    line = self._cookie_to_netscape_line(cookie)
                    if line:
                        netscape_lines.append(line)
            else:
                # کوکی تکی
                line = self._cookie_to_netscape_line(cookie_dict)
                if line:
                    netscape_lines.append(line)
            
            return '\n'.join(netscape_lines)
            
        except Exception as e:
            print(f"[ERROR] Cookie conversion error: {e}")
            # در صورت خطا، کوکی اصلی را برگردان
            return str(cookie_data)
    
    def _cookie_to_netscape_line(self, cookie: dict) -> str:
        """تبدیل یک کوکی به خط Netscape
        
        Args:
            cookie: دیکشنری کوکی
        
        Returns:
            str: خط کوکی در فرمت Netscape
        """
        try:
            domain = cookie.get('domain', '.youtube.com')
            if not domain.startswith('.'):
                domain = '.' + domain
                
            include_subdomains = 'TRUE' if domain.startswith('.') else 'FALSE'
            path = cookie.get('path', '/')
            secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
            expires = cookie.get('expires', 0)
            name = cookie.get('name', 'unknown')
            value = cookie.get('value', '')
            
            return f"{domain}\t{include_subdomains}\t{path}\t{secure}\t{expires}\t{name}\t{value}"
            
        except Exception as e:
            print(f"[ERROR] Cookie line conversion error: {e}")
            return None
    
    def _update_cookie_usage(self, platform: str, cookie_id: int):
        """به‌روزرسانی آمار استفاده کوکی"""
        cookies = self._load_cookies(platform)
        
        for cookie in cookies:
            if cookie.get('id') == cookie_id:
                cookie['usage_count'] = cookie.get('usage_count', 0) + 1
                cookie['last_used'] = str(int(time.time()))
                break
        
        self._save_cookies(platform, cookies)
    
    def remove_cookie(self, platform: str, cookie_id: int) -> bool:
        """حذف یک کوکی
        
        Args:
            platform: 'youtube' یا 'instagram'
            cookie_id: شناسه کوکی
        
        Returns:
            bool: موفقیت عملیات
        """
        cookies = self._load_cookies(platform)
        
        # حذف کوکی با شناسه مشخص
        cookies = [c for c in cookies if c.get('id') != cookie_id]
        
        return self._save_cookies(platform, cookies)
    
    def clear_cookies(self, platform: str) -> bool:
        """حذف تمام کوکی‌های یک پلتفرم
        
        Args:
            platform: 'youtube' یا 'instagram'
        
        Returns:
            bool: موفقیت عملیات
        """
        return self._save_cookies(platform, [])
    
    def toggle_cookie_status(self, platform: str, cookie_id: int) -> bool:
        """تغییر وضعیت فعال/غیرفعال کوکی
        
        Args:
            platform: 'youtube' یا 'instagram'
            cookie_id: شناسه کوکی
        
        Returns:
            bool: موفقیت عملیات
        """
        cookies = self._load_cookies(platform)
        
        for cookie in cookies:
            if cookie.get('id') == cookie_id:
                cookie['active'] = not cookie.get('active', True)
                return self._save_cookies(platform, cookies)
        
        return False
    
    def get_cookie_stats(self, platform: str) -> Dict:
        """دریافت آمار کوکی‌های یک پلتفرم
        
        Args:
            platform: 'youtube' یا 'instagram'
        
        Returns:
            Dict: آمار کوکی‌ها
        """
        cookies = self._load_cookies(platform)
        
        active_count = len([c for c in cookies if c.get('active', True)])
        inactive_count = len(cookies) - active_count
        total_usage = sum(c.get('usage_count', 0) for c in cookies)
        
        return {
            'total': len(cookies),
            'active': active_count,
            'inactive': inactive_count,
            'total_usage': total_usage
        }

    def update_usage(self, platform: str, cookie_id: int):
        """به‌روزرسانی آمار استفاده کوکی (متد عمومی)
        
        Args:
            platform: 'youtube' یا 'instagram'
            cookie_id: شناسه کوکی
        """
        self._update_cookie_usage(platform, cookie_id)
    
    def mark_invalid(self, platform: str, cookie_id: int) -> bool:
        """علامت‌گذاری کوکی به عنوان نامعتبر
        
        Args:
            platform: 'youtube' یا 'instagram'
            cookie_id: شناسه کوکی
        
        Returns:
            bool: موفقیت عملیات
        """
        cookies = self._load_cookies(platform)
        
        for cookie in cookies:
            if cookie.get('id') == cookie_id:
                cookie['active'] = False
                cookie['invalid_reason'] = 'marked_invalid'
                cookie['invalid_time'] = str(int(time.time()))
                return self._save_cookies(platform, cookies)
        
        return False

# نمونه سراسری
cookie_manager = CookieManager()