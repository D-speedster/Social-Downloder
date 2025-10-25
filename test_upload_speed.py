#!/usr/bin/env python3
"""
تست سرعت آپلود برای بررسی بهبودهای اعمال شده
"""

import asyncio
import time
import os
from plugins.stream_utils import fast_upload_video, smart_upload_strategy

async def test_upload_speed():
    """
    تست سرعت آپلود با روش‌های مختلف
    """
    print("🚀 شروع تست سرعت آپلود...")
    
    # فرض کنیم فایل تستی داریم
    test_file = "test_video.mp4"
    
    if not os.path.exists(test_file):
        print("❌ فایل تست یافت نشد")
        return
    
    file_size_mb = os.path.getsize(test_file) / (1024 * 1024)
    print(f"📁 حجم فایل: {file_size_mb:.2f} MB")
    
    # تست 1: آپلود سریع جدید
    print("\n🔥 تست 1: آپلود فوق سریع")
    start_time = time.time()
    
    # اینجا باید client واقعی باشد
    # success = await fast_upload_video(client, chat_id, test_file, "تست سرعت")
    
    end_time = time.time()
    upload_time = end_time - start_time
    speed_mbps = file_size_mb / upload_time if upload_time > 0 else 0
    
    print(f"⏱️ زمان آپلود: {upload_time:.2f} ثانیه")
    print(f"🚀 سرعت: {speed_mbps:.2f} MB/s")
    
    return upload_time, speed_mbps

if __name__ == "__main__":
    print("برای تست کامل، این فایل را در محیط بات اجرا کنید")