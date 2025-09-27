#!/usr/bin/env python3
"""
تست عملکرد database job management
"""

import os
import sys
import time
from plugins.sqlite_db_wrapper import DB

def test_database_connection():
    """تست اتصال به دیتابیس"""
    print("🔍 تست اتصال به دیتابیس...")
    
    try:
        db = DB()
        db.setup()
        print("✅ اتصال به دیتابیس موفق")
        return db
    except Exception as e:
        print(f"❌ خطا در اتصال به دیتابیس: {e}")
        return None

def test_job_creation(db):
    """تست ایجاد job"""
    print("🔍 تست ایجاد job...")
    
    try:
        job_id = db.create_job(
            user_id=12345,
            url="https://www.youtube.com/watch?v=jNQXAC9IVRw",
            title="Me at the zoo",
            format_id="best",
            status="pending"
        )
        
        if job_id > 0:
            print(f"✅ Job ایجاد شد با ID: {job_id}")
            return job_id
        else:
            print("❌ نتوانست job ایجاد کند")
            return None
    except Exception as e:
        print(f"❌ خطا در ایجاد job: {e}")
        return None

def test_job_updates(db, job_id):
    """تست به‌روزرسانی job"""
    print("🔍 تست به‌روزرسانی job...")
    
    try:
        # تست به‌روزرسانی وضعیت
        db.update_job_status(job_id, "downloading")
        print("✅ وضعیت job به downloading تغییر کرد")
        
        # تست به‌روزرسانی پیشرفت
        for progress in [25, 50, 75, 100]:
            db.update_job_progress(job_id, progress)
            print(f"✅ پیشرفت job به {progress}% تغییر کرد")
            time.sleep(0.1)  # شبیه‌سازی زمان دانلود
        
        # تست به‌روزرسانی وضعیت نهایی
        db.update_job_status(job_id, "completed")
        print("✅ وضعیت job به completed تغییر کرد")
        
        return True
    except Exception as e:
        print(f"❌ خطا در به‌روزرسانی job: {e}")
        return False

def test_job_retrieval(db, job_id):
    """تست دریافت اطلاعات job"""
    print("🔍 تست دریافت اطلاعات job...")
    
    try:
        # دریافت job خاص
        job = db.get_job(job_id)
        if job:
            print(f"✅ اطلاعات job دریافت شد:")
            print(f"   - ID: {job.get('id')}")
            print(f"   - User ID: {job.get('user_id')}")
            print(f"   - Title: {job.get('title')}")
            print(f"   - Status: {job.get('status')}")
            print(f"   - Progress: {job.get('progress')}%")
            print(f"   - Created: {job.get('created_at')}")
        else:
            print("❌ نتوانست job را دریافت کند")
            return False
        
        # دریافت job های کاربر
        user_jobs = db.get_user_jobs(12345)
        if user_jobs:
            print(f"✅ {len(user_jobs)} job برای کاربر دریافت شد")
            for job in user_jobs:
                print(f"   - Job {job.get('id')}: {job.get('title')} ({job.get('status')})")
        else:
            print("❌ نتوانست job های کاربر را دریافت کند")
            return False
        
        return True
    except Exception as e:
        print(f"❌ خطا در دریافت job: {e}")
        return False

def test_multiple_jobs(db):
    """تست ایجاد چندین job"""
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
                "user_id": 12345,
                "url": "https://www.youtube.com/watch?v=kJQP7kiw5Fk",
                "title": "Luis Fonsi - Despacito",
                "format_id": "bestaudio",
                "status": "downloading"
            },
            {
                "user_id": 67890,
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "title": "Rick Astley - Never Gonna Give You Up",
                "format_id": "best",
                "status": "completed"
            }
        ]
        
        created_jobs = []
        for job_data in test_jobs:
            job_id = db.create_job(**job_data)
            if job_id > 0:
                created_jobs.append(job_id)
                print(f"✅ Job {job_id} ایجاد شد: {job_data['title']}")
            else:
                print(f"❌ نتوانست job ایجاد کند: {job_data['title']}")
        
        print(f"✅ {len(created_jobs)} job از {len(test_jobs)} job ایجاد شد")
        return created_jobs
    except Exception as e:
        print(f"❌ خطا در ایجاد چندین job: {e}")
        return []

def test_database_jobs():
    """تست جامع database job management"""
    
    print("🚀 شروع تست database job management...")
    print("=" * 60)
    
    # تست اتصال
    db = test_database_connection()
    if not db:
        print("❌ تست متوقف شد - مشکل در اتصال به دیتابیس")
        return
    
    print("-" * 40)
    
    # تست ایجاد job
    job_id = test_job_creation(db)
    if not job_id:
        print("❌ تست متوقف شد - مشکل در ایجاد job")
        db.close()
        return
    
    print("-" * 40)
    
    # تست به‌روزرسانی job
    if not test_job_updates(db, job_id):
        print("❌ مشکل در به‌روزرسانی job")
    
    print("-" * 40)
    
    # تست دریافت job
    if not test_job_retrieval(db, job_id):
        print("❌ مشکل در دریافت job")
    
    print("-" * 40)
    
    # تست چندین job
    multiple_jobs = test_multiple_jobs(db)
    if multiple_jobs:
        print(f"✅ تست چندین job موفق - {len(multiple_jobs)} job ایجاد شد")
    
    print("-" * 40)
    
    # بستن اتصال
    db.close()
    print("✅ اتصال دیتابیس بسته شد")
    
    print("=" * 60)
    print("🏁 تست database job management تمام شد")

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 تست Database Job Management")
    print("=" * 60)
    
    test_database_jobs()