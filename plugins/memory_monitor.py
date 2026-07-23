"""
🧠 Memory Monitor - نظارت و مدیریت خودکار حافظه
"""
import asyncio
import psutil
import os
import gc
import logging
from datetime import datetime

logger = logging.getLogger('memory_monitor')


class MemoryMonitor:
    """نظارت بر استفاده حافظه و cleanup خودکار"""
    
    def __init__(self, threshold_percent=85, check_interval=300):
        """
        Args:
            threshold_percent: آستانه هشدار (درصد)
            check_interval: فاصله چک کردن (ثانیه)
        """
        self.threshold = threshold_percent
        self.check_interval = check_interval
        self.is_running = False
        self.cleanup_count = 0
        
    async def start(self, client=None, admin_id=None):
        """شروع نظارت"""
        self.is_running = True
        logger.info(f"Memory monitor started (threshold: {self.threshold}%)")
        
        while self.is_running:
            try:
                await asyncio.sleep(self.check_interval)
                
                # بررسی حافظه
                memory = psutil.virtual_memory()
                mem_percent = memory.percent
                
                if mem_percent >= self.threshold:
                    logger.warning(f"High memory usage: {mem_percent}%")
                    
                    # Cleanup خودکار
                    await self._auto_cleanup()
                    
                    # اطلاع به ادمین
                    if client and admin_id:
                        try:
                            await client.send_message(
                                admin_id,
                                f"⚠️ **هشدار حافظه**\n\n"
                                f"استفاده: {mem_percent}%\n"
                                f"Cleanup خودکار انجام شد\n"
                                f"تعداد: {self.cleanup_count}"
                            )
                        except:
                            pass
                
            except Exception as e:
                logger.error(f"Memory monitor error: {e}")
    
    async def _auto_cleanup(self):
        """Cleanup خودکار"""
        try:
            self.cleanup_count += 1
            logger.info(f"Starting auto cleanup #{self.cleanup_count}")
            
            # 1. Python garbage collection
            collected = gc.collect()
            logger.info(f"GC collected {collected} objects")
            
            # 2. پاک کردن فایل‌های موقت
            await self._cleanup_temp_files()
            
            # 3. بررسی حافظه بعد از cleanup
            memory = psutil.virtual_memory()
            logger.info(f"Memory after cleanup: {memory.percent}%")
            
        except Exception as e:
            logger.error(f"Auto cleanup error: {e}")
    
    async def _cleanup_temp_files(self):
        """پاک کردن فایل‌های موقت"""
        try:
            downloads_dir = "Downloads"
            if os.path.exists(downloads_dir):
                # حذف فایل‌های قدیمی‌تر از 1 ساعت
                import time
                now = time.time()
                removed = 0
                
                for filename in os.listdir(downloads_dir):
                    filepath = os.path.join(downloads_dir, filename)
                    try:
                        if os.path.isfile(filepath):
                            # فایل‌های قدیمی‌تر از 1 ساعت
                            if now - os.path.getmtime(filepath) > 3600:
                                os.remove(filepath)
                                removed += 1
                    except:
                        pass
                
                if removed > 0:
                    logger.info(f"Removed {removed} old temp files")
        
        except Exception as e:
            logger.error(f"Temp cleanup error: {e}")
    
    def stop(self):
        """توقف نظارت"""
        self.is_running = False
        logger.info("Memory monitor stopped")


# Global instance
_memory_monitor = None


def get_memory_monitor():
    """دریافت instance"""
    global _memory_monitor
    if _memory_monitor is None:
        _memory_monitor = MemoryMonitor(threshold_percent=85, check_interval=300)
    return _memory_monitor


async def start_memory_monitor(client, admin_id):
    """شروع نظارت حافظه"""
    monitor = get_memory_monitor()
    await monitor.start(client, admin_id)


print("✅ Memory Monitor ready")
print("   - Threshold: 85%")
print("   - Check interval: 5 minutes")
print("   - Auto cleanup enabled")
