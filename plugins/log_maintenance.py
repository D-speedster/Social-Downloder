"""
ماژول نگهداری و پاک‌سازی لاگ‌ها
این ماژول وظایف نگهداری خودکار لاگ‌ها را انجام می‌دهد
"""

import os
import time
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import logging


class LogMaintenance:
    """کلاس مدیریت و نگهداری لاگ‌ها"""
    
    def __init__(self, logs_dir='./logs'):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)
        
    def compress_old_logs(self, days_old=7):
        """فشرده‌سازی لاگ‌های قدیمی‌تر از تعداد روزهای مشخص"""
        compressed_count = 0
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        for log_file in self.logs_dir.glob('*.log'):
            if log_file.stat().st_mtime < cutoff_date.timestamp():
                compressed_file = log_file.with_suffix('.log.gz')
                
                # فشرده‌سازی فایل
                with open(log_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # حذف فایل اصلی
                log_file.unlink()
                compressed_count += 1
                print(f"فشرده شد: {log_file.name} -> {compressed_file.name}")
        
        return compressed_count
    
    def delete_old_compressed_logs(self, days_old=30):
        """حذف لاگ‌های فشرده قدیمی‌تر از تعداد روزهای مشخص"""
        deleted_count = 0
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        for compressed_file in self.logs_dir.glob('*.log.gz'):
            if compressed_file.stat().st_mtime < cutoff_date.timestamp():
                compressed_file.unlink()
                deleted_count += 1
                print(f"حذف شد: {compressed_file.name}")
        
        return deleted_count
    
    def get_logs_size_info(self):
        """دریافت اطلاعات اندازه لاگ‌ها"""
        total_size = 0
        file_count = 0
        
        info = {
            'active_logs': [],
            'compressed_logs': [],
            'total_size': 0,
            'total_files': 0
        }
        
        # بررسی لاگ‌های فعال
        for log_file in self.logs_dir.glob('*.log'):
            size = log_file.stat().st_size
            modified = datetime.fromtimestamp(log_file.stat().st_mtime)
            
            info['active_logs'].append({
                'name': log_file.name,
                'size': size,
                'size_mb': round(size / (1024 * 1024), 2),
                'modified': modified.strftime('%Y-%m-%d %H:%M:%S')
            })
            
            total_size += size
            file_count += 1
        
        # بررسی لاگ‌های فشرده
        for compressed_file in self.logs_dir.glob('*.log.gz'):
            size = compressed_file.stat().st_size
            modified = datetime.fromtimestamp(compressed_file.stat().st_mtime)
            
            info['compressed_logs'].append({
                'name': compressed_file.name,
                'size': size,
                'size_mb': round(size / (1024 * 1024), 2),
                'modified': modified.strftime('%Y-%m-%d %H:%M:%S')
            })
            
            total_size += size
            file_count += 1
        
        info['total_size'] = total_size
        info['total_size_mb'] = round(total_size / (1024 * 1024), 2)
        info['total_files'] = file_count
        
        return info
    
    def rotate_large_logs(self, max_size_mb=10):
        """چرخش لاگ‌های بزرگ"""
        rotated_count = 0
        max_size_bytes = max_size_mb * 1024 * 1024
        
        for log_file in self.logs_dir.glob('*.log'):
            if log_file.stat().st_size > max_size_bytes:
                # ایجاد نام فایل جدید با timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                rotated_name = f"{log_file.stem}_{timestamp}.log"
                rotated_path = log_file.parent / rotated_name
                
                # تغییر نام فایل قدیمی
                log_file.rename(rotated_path)
                
                # ایجاد فایل جدید خالی
                log_file.touch()
                
                rotated_count += 1
                print(f"چرخش انجام شد: {log_file.name} -> {rotated_name}")
        
        return rotated_count
    
    def cleanup_logs(self, compress_days=7, delete_days=30, max_size_mb=10):
        """پاک‌سازی کامل لاگ‌ها"""
        print("🧹 شروع پاک‌سازی لاگ‌ها...")
        
        # چرخش لاگ‌های بزرگ
        rotated = self.rotate_large_logs(max_size_mb)
        if rotated > 0:
            print(f"✅ {rotated} فایل لاگ چرخش داده شد")
        
        # فشرده‌سازی لاگ‌های قدیمی
        compressed = self.compress_old_logs(compress_days)
        if compressed > 0:
            print(f"✅ {compressed} فایل لاگ فشرده شد")
        
        # حذف لاگ‌های فشرده قدیمی
        deleted = self.delete_old_compressed_logs(delete_days)
        if deleted > 0:
            print(f"✅ {deleted} فایل لاگ فشرده حذف شد")
        
        # نمایش اطلاعات نهایی
        info = self.get_logs_size_info()
        print(f"\n📊 وضعیت نهایی لاگ‌ها:")
        print(f"   📁 تعداد کل فایل‌ها: {info['total_files']}")
        print(f"   💾 اندازه کل: {info['total_size_mb']} MB")
        print(f"   📄 لاگ‌های فعال: {len(info['active_logs'])}")
        print(f"   🗜️ لاگ‌های فشرده: {len(info['compressed_logs'])}")
        
        return {
            'rotated': rotated,
            'compressed': compressed,
            'deleted': deleted,
            'info': info
        }


def main():
    """تابع اصلی برای اجرای نگهداری لاگ‌ها"""
    maintenance = LogMaintenance()
    
    print("🔧 ابزار نگهداری لاگ‌ها")
    print("=" * 40)
    
    # نمایش وضعیت فعلی
    info = maintenance.get_logs_size_info()
    print(f"📊 وضعیت فعلی:")
    print(f"   📁 تعداد کل فایل‌ها: {info['total_files']}")
    print(f"   💾 اندازه کل: {info['total_size_mb']} MB")
    print(f"   📄 لاگ‌های فعال: {len(info['active_logs'])}")
    print(f"   🗜️ لاگ‌های فشرده: {len(info['compressed_logs'])}")
    
    print("\n" + "=" * 40)
    
    # انجام پاک‌سازی
    result = maintenance.cleanup_logs()
    
    print("\n✅ پاک‌سازی کامل شد!")


if __name__ == "__main__":
    main()