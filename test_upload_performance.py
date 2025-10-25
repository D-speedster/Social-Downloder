#!/usr/bin/env python3
"""
اسکریپت تست عملکرد آپلود
"""
import asyncio
import time
import os
import sys
from datetime import datetime

# اضافه کردن مسیر پروژه
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_upload_performance():
    """
    تست عملکرد آپلود با فایل‌های مختلف
    """
    print("🚀 شروع تست عملکرد آپلود")
    print("=" * 50)
    
    # فایل‌های تست (اگر موجود باشند)
    test_files = [
        ("test_small.mp4", "< 10MB"),
        ("test_medium.mp4", "10-50MB"), 
        ("test_large.mp4", "50-200MB"),
        ("test_huge.mp4", "> 200MB")
    ]
    
    results = []
    
    for file_name, size_category in test_files:
        if not os.path.exists(file_name):
            print(f"⚠️ فایل {file_name} یافت نشد - رد شد")
            continue
            
        file_size = os.path.getsize(file_name)
        file_size_mb = file_size / (1024 * 1024)
        
        print(f"\n📁 تست فایل: {file_name}")
        print(f"📏 حجم: {file_size_mb:.2f} MB ({size_category})")
        
        # شبیه‌سازی آپلود (بدون کلاینت واقعی)
        start_time = time.time()
        
        # شبیه‌سازی زمان آپلود بر اساس حجم
        if file_size_mb < 10:
            simulated_time = file_size_mb * 0.5  # 0.5s per MB
        elif file_size_mb < 50:
            simulated_time = file_size_mb * 0.8  # 0.8s per MB
        elif file_size_mb < 200:
            simulated_time = file_size_mb * 1.2  # 1.2s per MB
        else:
            simulated_time = file_size_mb * 1.5  # 1.5s per MB
        
        # شبیه‌سازی پیشرفت
        for i in range(0, 101, 10):
            await asyncio.sleep(simulated_time / 10)
            print(f"📊 پیشرفت: {i}%", end='\r')
        
        end_time = time.time()
        actual_time = end_time - start_time
        speed_mbps = file_size_mb / actual_time if actual_time > 0 else 0
        
        print(f"\n✅ آپلود شبیه‌سازی شده در {actual_time:.2f}s")
        print(f"⚡ سرعت: {speed_mbps:.2f} MB/s")
        
        results.append({
            'file': file_name,
            'size_mb': file_size_mb,
            'time': actual_time,
            'speed': speed_mbps,
            'category': size_category
        })
    
    # نمایش خلاصه نتایج
    print("\n" + "=" * 50)
    print("📊 خلاصه نتایج تست:")
    print("=" * 50)
    
    if results:
        for result in results:
            print(f"📁 {result['file']}: {result['size_mb']:.1f}MB در {result['time']:.1f}s ({result['speed']:.1f}MB/s)")
        
        avg_speed = sum(r['speed'] for r in results) / len(results)
        print(f"\n⚡ میانگین سرعت: {avg_speed:.2f} MB/s")
        
        # تخمین زمان برای فایل 862MB
        estimated_time_862mb = 862 / avg_speed if avg_speed > 0 else 0
        print(f"🎯 تخمین زمان آپلود فایل 862MB: {estimated_time_862mb:.1f} ثانیه ({estimated_time_862mb/60:.1f} دقیقه)")
    else:
        print("❌ هیچ فایل تستی یافت نشد")
        print("💡 برای تست واقعی، فایل‌های تست ایجاد کنید:")
        for file_name, size_category in test_files:
            print(f"   - {file_name} ({size_category})")
    
    print("\n🏁 تست تکمیل شد")

def create_test_files():
    """
    ایجاد فایل‌های تست برای آزمایش
    """
    print("📝 ایجاد فایل‌های تست...")
    
    test_sizes = [
        ("test_small.mp4", 5 * 1024 * 1024),      # 5MB
        ("test_medium.mp4", 25 * 1024 * 1024),    # 25MB
        ("test_large.mp4", 100 * 1024 * 1024),    # 100MB
    ]
    
    for file_name, size_bytes in test_sizes:
        if not os.path.exists(file_name):
            print(f"📁 ایجاد {file_name} ({size_bytes / (1024*1024):.0f}MB)...")
            with open(file_name, 'wb') as f:
                # نوشتن داده‌های تصادفی
                chunk_size = 1024 * 1024  # 1MB chunks
                written = 0
                while written < size_bytes:
                    remaining = min(chunk_size, size_bytes - written)
                    f.write(b'0' * remaining)
                    written += remaining
            print(f"✅ {file_name} ایجاد شد")
        else:
            print(f"⚠️ {file_name} از قبل موجود است")

if __name__ == "__main__":
    print("🧪 اسکریپت تست عملکرد آپلود")
    print(f"📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    choice = input("\n1. اجرای تست عملکرد\n2. ایجاد فایل‌های تست\n\nانتخاب کنید (1 یا 2): ")
    
    if choice == "2":
        create_test_files()
    else:
        try:
            asyncio.run(test_upload_performance())
        except KeyboardInterrupt:
            print("\n⏹️ تست توسط کاربر متوقف شد")
        except Exception as e:
            print(f"\n❌ خطا در تست: {e}")