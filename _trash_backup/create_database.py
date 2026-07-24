#!/usr/bin/env python3
"""
ایجاد دیتابیس و تست job management
"""

from plugins.sqlite_db_wrapper import DB
import time

def create_and_test_database():
    """ایجاد دیتابیس و تست عملکرد job management"""
    
    print("🚀 ایجاد دیتابیس و تست job management...")
    print("=" * 60)
    
    # ایجاد دیتابیس
    print("🔍 ایجاد دیتابیس...")
    try:
        db = DB()
        db.setup()
        print("✅ دیتابیس ایجاد شد")
    except Exception as e:
        print(f"❌ خطا در ایجاد دیتابیس: {e}")
        return
    
    print("-" * 40)
    
    # تست ایجاد job
    print("🔍 تست ایجاد job...")
    try:
        job_id = db.create_job(
            user_id=12345,
            url="https://www.youtube.com/watch?v=jNQXAC9IVRw",
            title="Me at the zoo",
            format_id="best",
            status="pending"
        )
        
        if job_id and job_id > 0:
            print(f"✅ Job ایجاد شد با ID: {job_id}")
        else:
            print("❌ نتوانست job ایجاد کند")
            db.close()
            return
    except Exception as e:
        print(f"❌ خطا در ایجاد job: {e}")
        db.close()
        return
    
    print("-" * 40)
    
    # تست به‌روزرسانی job
    print("🔍 تست به‌روزرسانی job...")
    try:
        # تغییر وضعیت به downloading
        db.update_job_status(job_id, "downloading")
        print("✅ وضعیت job به downloading تغییر کرد")
        
        # شبیه‌سازی پیشرفت دانلود
        for progress in [10, 25, 50, 75, 90, 100]:
            db.update_job_progress(job_id, progress)
            print(f"✅ پیشرفت job: {progress}%")
            time.sleep(0.2)
        
        # تغییر وضعیت به completed
        db.update_job_status(job_id, "completed")
        print("✅ وضعیت job به completed تغییر کرد")
        
    except Exception as e:
        print(f"❌ خطا در به‌روزرسانی job: {e}")
    
    print("-" * 40)
    
    # تست دریافت job
    print("🔍 تست دریافت job...")
    try:
        job = db.get_job(job_id)
        if job:
            print("✅ اطلاعات job دریافت شد:")
            print(f"   - ID: {job.get('id')}")
            print(f"   - User ID: {job.get('user_id')}")
            print(f"   - URL: {job.get('url')}")
            print(f"   - Title: {job.get('title')}")
            print(f"   - Format: {job.get('format_id')}")
            print(f"   - Status: {job.get('status')}")
            print(f"   - Progress: {job.get('progress')}%")
            print(f"   - Created: {job.get('created_at')}")
        else:
            print("❌ نتوانست job را دریافت کند")
    except Exception as e:
        print(f"❌ خطا در دریافت job: {e}")
    
    print("-" * 40)
    
    # تست job های کاربر
    print("🔍 تست دریافت job های کاربر...")
    try:
        user_jobs = db.get_user_jobs(12345)
        if user_jobs:
            print(f"✅ {len(user_jobs)} job برای کاربر دریافت شد:")
            for job in user_jobs:
                print(f"   - Job {job.get('id')}: {job.get('title')} ({job.get('status')})")
        else:
            print("❌ هیچ job برای کاربر یافت نشد")
    except Exception as e:
        print(f"❌ خطا در دریافت job های کاربر: {e}")
    
    print("-" * 40)
    
    # تست ایجاد چندین job
    print("🔍 تست ایجاد چندین job...")
    try:
        test_jobs = [
            {
                "user_id": 12345,
                "url": "https://www.youtube.com/watch?v=9bZkp7q19f0",
                "title": "PSY - Gangnam Style",
                "format_id": "best",
                "status": "pending"
            },
            {
                "user_id": 67890,
                "url": "https://www.youtube.com/watch?v=kJQP7kiw5Fk",
                "title": "Luis Fonsi - Despacito",
                "format_id": "bestaudio",
                "status": "downloading"
            }
        ]
        
        created_jobs = []
        for job_data in test_jobs:
            job_id = db.create_job(**job_data)
            if job_id and job_id > 0:
                created_jobs.append(job_id)
                print(f"✅ Job {job_id} ایجاد شد: {job_data['title']}")
            else:
                print(f"❌ نتوانست job ایجاد کند: {job_data['title']}")
        
        print(f"✅ {len(created_jobs)} job اضافی ایجاد شد")
        
    except Exception as e:
        print(f"❌ خطا در ایجاد چندین job: {e}")
    
    print("-" * 40)
    
    # بستن اتصال
    db.close()
    print("✅ اتصال دیتابیس بسته شد")
    
    print("=" * 60)
    print("🏁 تست job management تمام شد")

if __name__ == "__main__":
    create_and_test_database()