"""
Pornhub Storage Manager - مدیریت ذخیره‌سازی فایل‌ها با کد یکتا
"""

import os
import json
import uuid
import time
from typing import Optional
from plugins.logger_config import get_logger

logger = get_logger('pornhub_storage')

class PornhubStorage:
    """مدیریت ذخیره‌سازی فایل‌های دانلود شده"""
    
    def __init__(self, storage_file: str = "data/pornhub_files.json"):
        self.storage_file = storage_file
        self._ensure_storage_file()
    
    def _ensure_storage_file(self):
        """اطمینان از وجود فایل ذخیره‌سازی"""
        os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
        if not os.path.exists(self.storage_file):
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
    
    def _load_storage(self) -> dict:
        """بارگذاری داده‌های ذخیره شده"""
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading storage: {e}")
            return {}
    
    def _save_storage(self, data: dict):
        """ذخیره داده‌ها"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving storage: {e}")
    
    def generate_file_code(self) -> str:
        """تولید کد یکتا برای فایل"""
        return str(uuid.uuid4())[:8].upper()
    
    def store_file(
        self,
        file_path: str,
        user_id: int,
        title: str,
        quality: str,
        file_size: int
    ) -> str:
        """
        ذخیره اطلاعات فایل و برگرداندن کد یکتا
        
        Args:
            file_path: مسیر فایل دانلود شده
            user_id: شناسه کاربر
            title: عنوان ویدیو
            quality: کیفیت انتخاب شده
            file_size: حجم فایل (بایت)
        
        Returns:
            کد یکتا برای دریافت فایل
        """
        try:
            code = self.generate_file_code()
            storage = self._load_storage()
            
            # اطمینان از یکتا بودن کد
            while code in storage:
                code = self.generate_file_code()
            
            storage[code] = {
                'file_path': file_path,
                'user_id': user_id,
                'title': title,
                'quality': quality,
                'file_size': file_size,
                'timestamp': int(time.time()),
                'downloaded': False,  # آیا کاربر فایل را دریافت کرده؟
                'download_count': 0
            }
            
            self._save_storage(storage)
            logger.info(f"File stored with code: {code} for user {user_id}")
            return code
        
        except Exception as e:
            logger.error(f"Error storing file: {e}")
            return None
    
    def get_file_info(self, code: str) -> Optional[dict]:
        """
        دریافت اطلاعات فایل با کد
        
        Args:
            code: کد یکتا
        
        Returns:
            اطلاعات فایل یا None
        """
        try:
            storage = self._load_storage()
            return storage.get(code.upper())
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return None
    
    def mark_as_downloaded(self, code: str) -> bool:
        """
        علامت‌گذاری فایل به عنوان دریافت شده
        
        Args:
            code: کد یکتا
        
        Returns:
            موفقیت عملیات
        """
        try:
            storage = self._load_storage()
            code = code.upper()
            
            if code in storage:
                storage[code]['downloaded'] = True
                storage[code]['download_count'] += 1
                storage[code]['last_download'] = int(time.time())
                self._save_storage(storage)
                logger.info(f"File {code} marked as downloaded")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error marking file as downloaded: {e}")
            return False
    
    def delete_file(self, code: str) -> bool:
        """
        حذف فایل و اطلاعات آن
        
        Args:
            code: کد یکتا
        
        Returns:
            موفقیت عملیات
        """
        try:
            storage = self._load_storage()
            code = code.upper()
            
            if code in storage:
                file_info = storage[code]
                file_path = file_info.get('file_path')
                
                # حذف فایل فیزیکی
                if file_path and os.path.exists(file_path):
                    try:
                        os.unlink(file_path)
                        logger.info(f"Physical file deleted: {file_path}")
                    except Exception as e:
                        logger.warning(f"Could not delete physical file: {e}")
                
                # حذف از storage
                del storage[code]
                self._save_storage(storage)
                logger.info(f"File {code} deleted from storage")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """
        پاکسازی فایل‌های قدیمی
        
        Args:
            max_age_hours: حداکثر سن فایل به ساعت
        
        Returns:
            تعداد فایل‌های حذف شده
        """
        try:
            storage = self._load_storage()
            current_time = int(time.time())
            max_age_seconds = max_age_hours * 3600
            deleted_count = 0
            
            codes_to_delete = []
            for code, info in storage.items():
                age = current_time - info.get('timestamp', 0)
                if age > max_age_seconds:
                    codes_to_delete.append(code)
            
            for code in codes_to_delete:
                if self.delete_file(code):
                    deleted_count += 1
            
            logger.info(f"Cleanup: {deleted_count} old files deleted")
            return deleted_count
        
        except Exception as e:
            logger.error(f"Error cleaning up old files: {e}")
            return 0
    
    def get_user_files(self, user_id: int) -> list:
        """
        دریافت لیست فایل‌های یک کاربر
        
        Args:
            user_id: شناسه کاربر
        
        Returns:
            لیست کدهای فایل‌های کاربر
        """
        try:
            storage = self._load_storage()
            user_files = []
            
            for code, info in storage.items():
                if info.get('user_id') == user_id:
                    user_files.append({
                        'code': code,
                        'title': info.get('title'),
                        'quality': info.get('quality'),
                        'downloaded': info.get('downloaded', False)
                    })
            
            return user_files
        
        except Exception as e:
            logger.error(f"Error getting user files: {e}")
            return []


# نمونه سراسری
pornhub_storage = PornhubStorage()
