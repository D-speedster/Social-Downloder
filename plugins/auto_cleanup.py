"""
سیستم پاکسازی خودکار فایل‌های موقت
"""
import os
import time
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger('auto_cleanup')


class AutoCleanup:
    """
    کلاس پاکسازی خودکار فایل‌های موقت
    """
    def __init__(self):
        self.cleanup_interval = 3600  # هر 1 ساعت
        self.max_file_age = 7200  # فایل‌های قدیمی‌تر از 2 ساعت
        self.running = False
        
        # دایرکتوری‌های هدف
        self.target_dirs = [
            './downloads',
            './temp',
        ]
        
        # الگوهای فایل‌های موقت
        self.temp_patterns = [
            '_thumb.jpg',
            'tmp',
            'download_',
        ]
        
        logger.info("Auto-cleanup initialized")
    
    def should_delete(self, file_path: str) -> bool:
        """
        بررسی اینکه آیا فایل باید پاک شود
        """
        try:
            # بررسی سن فایل
            file_age = time.time() - os.path.getmtime(file_path)
            if file_age < self.max_file_age:
                return False
            
            # بررسی الگوی نام فایل
            filename = os.path.basename(file_path)
            for pattern in self.temp_patterns:
                if pattern in filename:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking file {file_path}: {e}")
            return False
    
    def cleanup_directory(self, directory: str) -> tuple:
        """
        پاکسازی یک دایرکتوری
        
        Returns:
            (deleted_count, freed_bytes)
        """
        if not os.path.exists(directory):
            return 0, 0
        
        deleted_count = 0
        freed_bytes = 0
        
        try:
            for entry in os.scandir(directory):
                try:
                    if entry.is_file() and self.should_delete(entry.path):
                        size = entry.stat().st_size
                        os.remove(entry.path)
                        deleted_count += 1
                        freed_bytes += size
                        logger.debug(f"Deleted: {entry.name} ({size} bytes)")
                except Exception as e:
                    logger.error(f"Error deleting {entry.name}: {e}")
        except Exception as e:
            logger.error(f"Error scanning {directory}: {e}")
        
        return deleted_count, freed_bytes
    
    def cleanup_temp_files(self) -> dict:
        """
        پاکسازی تمام فایل‌های موقت
        
        Returns:
            آمار پاکسازی
        """
        total_deleted = 0
        total_freed = 0
        
        for directory in self.target_dirs:
            deleted, freed = self.cleanup_directory(directory)
            total_deleted += deleted
            total_freed += freed
        
        # پاکسازی فایل‌های temp سیستم
        import tempfile
        temp_dir = tempfile.gettempdir()
        
        try:
            for entry in os.scandir(temp_dir):
                try:
                    if entry.is_file():
                        filename = entry.name
                        # فقط فایل‌های مربوط به ربات
                        if any(p in filename for p in ['tmp', 'download_', 'thumb_']):
                            file_age = time.time() - entry.stat().st_mtime
                            if file_age > self.max_file_age:
                                size = entry.stat().st_size
                                os.remove(entry.path)
                                total_deleted += 1
                                total_freed += size
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Error cleaning temp dir: {e}")
        
        return {
            'deleted_count': total_deleted,
            'freed_bytes': total_freed,
            'freed_mb': total_freed / 1024 / 1024
        }
    
    async def run_periodic_cleanup(self):
        """
        اجرای دوره‌ای پاکسازی
        """
        self.running = True
        logger.info(f"Starting periodic cleanup (interval: {self.cleanup_interval}s)")
        
        while self.running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                logger.info("Running scheduled cleanup...")
                stats = self.cleanup_temp_files()
                
                if stats['deleted_count'] > 0:
                    logger.info(
                        f"Cleanup complete: {stats['deleted_count']} files, "
                        f"{stats['freed_mb']:.2f} MB freed"
                    )
                    print(
                        f"🧹 Auto-cleanup: {stats['deleted_count']} files, "
                        f"{stats['freed_mb']:.2f} MB freed"
                    )
                else:
                    logger.debug("No files to clean")
                    
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    def stop(self):
        """
        توقف پاکسازی دوره‌ای
        """
        self.running = False
        logger.info("Auto-cleanup stopped")


# 🔥 Global instance
auto_cleanup = AutoCleanup()


async def start_auto_cleanup():
    """
    شروع سرویس پاکسازی خودکار
    """
    try:
        await auto_cleanup.run_periodic_cleanup()
    except Exception as e:
        logger.error(f"Auto-cleanup service error: {e}")


def stop_auto_cleanup():
    """
    توقف سرویس پاکسازی خودکار
    """
    auto_cleanup.stop()


print("✅ Auto-cleanup service ready")
print(f"   - Cleanup interval: {auto_cleanup.cleanup_interval}s (1 hour)")
print(f"   - Max file age: {auto_cleanup.max_file_age}s (2 hours)")
