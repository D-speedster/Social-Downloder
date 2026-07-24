#!/usr/bin/env python3
"""
اسکریپت پاکسازی فضای دیسک
"""
import os
import shutil
import time
from datetime import datetime, timedelta

def get_size(path):
    """محاسبه حجم یک دایرکتوری"""
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_size(entry.path)
    except Exception:
        pass
    return total

def format_size(bytes):
    """فرمت کردن حجم"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024
    return f"{bytes:.2f} TB"

def cleanup_old_files(directory, days=7):
    """پاک کردن فایل‌های قدیمی‌تر از X روز"""
    if not os.path.exists(directory):
        return 0, 0
    
    cutoff = time.time() - (days * 86400)
    deleted_count = 0
    freed_space = 0
    
    try:
        for entry in os.scandir(directory):
            try:
                if entry.is_file() and entry.stat().st_mtime < cutoff:
                    size = entry.stat().st_size
                    os.remove(entry.path)
                    deleted_count += 1
                    freed_space += size
                    print(f"  ✓ Deleted: {entry.name} ({format_size(size)})")
            except Exception as e:
                print(f"  ✗ Error deleting {entry.name}: {e}")
    except Exception as e:
        print(f"  ✗ Error scanning {directory}: {e}")
    
    return deleted_count, freed_space

def cleanup_logs(max_size_mb=100):
    """پاک کردن لاگ‌های قدیمی"""
    logs_dir = './logs'
    if not os.path.exists(logs_dir):
        return 0, 0
    
    total_size = get_size(logs_dir)
    if total_size < max_size_mb * 1024 * 1024:
        return 0, 0
    
    print(f"\n📋 Cleaning logs (current: {format_size(total_size)})...")
    
    # پاک کردن لاگ‌های قدیمی‌تر از 7 روز
    deleted, freed = cleanup_old_files(logs_dir, days=7)
    
    return deleted, freed

def cleanup_downloads():
    """پاک کردن فایل‌های دانلود شده"""
    downloads_dir = './downloads'
    if not os.path.exists(downloads_dir):
        return 0, 0
    
    total_size = get_size(downloads_dir)
    print(f"\n📥 Cleaning downloads (current: {format_size(total_size)})...")
    
    # پاک کردن فایل‌های قدیمی‌تر از 1 روز
    deleted, freed = cleanup_old_files(downloads_dir, days=1)
    
    return deleted, freed

def cleanup_temp():
    """پاک کردن فایل‌های موقت"""
    import tempfile
    temp_dir = tempfile.gettempdir()
    
    print(f"\n🗑️ Cleaning temp files...")
    
    deleted = 0
    freed = 0
    
    # پاک کردن فایل‌های موقت ربات
    for pattern in ['tmp*', 'download_*', 'thumb_*']:
        try:
            for entry in os.scandir(temp_dir):
                if entry.is_file() and entry.name.startswith(pattern.replace('*', '')):
                    try:
                        size = entry.stat().st_size
                        os.remove(entry.path)
                        deleted += 1
                        freed += size
                    except Exception:
                        pass
        except Exception:
            pass
    
    return deleted, freed

def main():
    print("="*60)
    print("🧹 DISK CLEANUP UTILITY")
    print("="*60)
    
    total_deleted = 0
    total_freed = 0
    
    # 1. پاکسازی لاگ‌ها
    deleted, freed = cleanup_logs()
    total_deleted += deleted
    total_freed += freed
    if deleted > 0:
        print(f"  ✅ Deleted {deleted} log files, freed {format_size(freed)}")
    
    # 2. پاکسازی دانلودها
    deleted, freed = cleanup_downloads()
    total_deleted += deleted
    total_freed += freed
    if deleted > 0:
        print(f"  ✅ Deleted {deleted} download files, freed {format_size(freed)}")
    
    # 3. پاکسازی temp
    deleted, freed = cleanup_temp()
    total_deleted += deleted
    total_freed += freed
    if deleted > 0:
        print(f"  ✅ Deleted {deleted} temp files, freed {format_size(freed)}")
    
    print("\n" + "="*60)
    print(f"🎉 CLEANUP COMPLETE")
    print(f"   Total files deleted: {total_deleted}")
    print(f"   Total space freed: {format_size(total_freed)}")
    print("="*60)
    
    # نمایش فضای باقیمانده
    try:
        import psutil
        disk = psutil.disk_usage('/')
        print(f"\n💾 Disk usage after cleanup:")
        print(f"   Total: {format_size(disk.total)}")
        print(f"   Used: {format_size(disk.used)} ({disk.percent}%)")
        print(f"   Free: {format_size(disk.free)}")
    except Exception:
        pass

if __name__ == "__main__":
    main()
