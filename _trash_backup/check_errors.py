#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بررسی خطاهای دانلود در سرور"""

from plugins.db_wrapper import DB
from datetime import datetime, timedelta

def main():
    db = DB()
    
    print("=" * 80)
    print("📊 گزارش خطاهای دانلود - آخرین 24 ساعت")
    print("=" * 80)
    print()
    
    # خطاهای YouTube
    print("🔴 خطاهای YouTube:")
    print("-" * 80)
    db.cursor.execute('''
        SELECT error_message, COUNT(*) as count
        FROM requests 
        WHERE platform = "youtube" 
        AND status = "failed"
        AND created_at > datetime('now', '-24 hours')
        GROUP BY error_message 
        ORDER BY count DESC 
        LIMIT 10
    ''')
    
    youtube_errors = db.cursor.fetchall()
    if youtube_errors:
        for row in youtube_errors:
            print(f"  [{row[1]:3d}x] {row[0][:70]}")
    else:
        print("  ✅ هیچ خطایی در 24 ساعت گذشته!")
    
    print()
    
    # خطاهای Universal
    print("🔴 خطاهای Universal:")
    print("-" * 80)
    db.cursor.execute('''
        SELECT error_message, COUNT(*) as count
        FROM requests 
        WHERE platform = "universal" 
        AND status = "failed"
        AND created_at > datetime('now', '-24 hours')
        GROUP BY error_message 
        ORDER BY count DESC 
        LIMIT 10
    ''')
    
    universal_errors = db.cursor.fetchall()
    if universal_errors:
        for row in universal_errors:
            print(f"  [{row[1]:3d}x] {row[0][:70]}")
    else:
        print("  ✅ هیچ خطایی در 24 ساعت گذشته!")
    
    print()
    
    # خطاهای Instagram
    print("🔴 خطاهای Instagram:")
    print("-" * 80)
    db.cursor.execute('''
        SELECT error_message, COUNT(*) as count
        FROM requests 
        WHERE platform = "instagram" 
        AND status = "failed"
        AND created_at > datetime('now', '-24 hours')
        GROUP BY error_message 
        ORDER BY count DESC 
        LIMIT 10
    ''')
    
    instagram_errors = db.cursor.fetchall()
    if instagram_errors:
        for row in instagram_errors:
            print(f"  [{row[1]:3d}x] {row[0][:70]}")
    else:
        print("  ✅ هیچ خطایی در 24 ساعت گذشته!")
    
    print()
    print("=" * 80)
    
    # URL های ناموفق Instagram (آخرین 10)
    print("🔗 URL های ناموفق Instagram (آخرین 10):")
    print("-" * 80)
    db.cursor.execute('''
        SELECT url, error_message, created_at
        FROM requests 
        WHERE platform = "instagram" 
        AND status = "failed"
        AND created_at > datetime('now', '-24 hours')
        ORDER BY created_at DESC 
        LIMIT 10
    ''')
    
    instagram_urls = db.cursor.fetchall()
    if instagram_urls:
        for i, row in enumerate(instagram_urls, 1):
            print(f"\n{i}. URL: {row[0][:70]}")
            print(f"   خطا: {row[1][:70]}")
            print(f"   زمان: {row[2]}")
    else:
        print("  ✅ هیچ خطایی در 24 ساعت گذشته!")
    
    print()
    print("=" * 80)
    
    # URL های ناموفق Universal که Instagram هستن (مشکل routing!)
    print("⚠️ URL های Instagram که به Universal رفتن (مشکل routing!):")
    print("-" * 80)
    db.cursor.execute('''
        SELECT url, error_message, created_at
        FROM requests 
        WHERE platform = "universal" 
        AND status = "failed"
        AND url LIKE "%instagram.com%"
        AND created_at > datetime('now', '-24 hours')
        ORDER BY created_at DESC 
        LIMIT 10
    ''')
    
    routing_errors = db.cursor.fetchall()
    if routing_errors:
        print(f"  🚨 {len(routing_errors)} لینک Instagram به Universal رفته!")
        for i, row in enumerate(routing_errors, 1):
            print(f"\n{i}. URL: {row[0][:70]}")
            print(f"   خطا: {row[1][:70]}")
            print(f"   زمان: {row[2]}")
    else:
        print("  ✅ هیچ مشکل routing در 24 ساعت گذشته!")
    
    print()
    print("=" * 80)
    
    # آمار کلی
    print("📈 آمار کلی (آخرین 24 ساعت):")
    print("-" * 80)
    
    # YouTube
    db.cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = "success" THEN 1 ELSE 0 END) as success,
            SUM(CASE WHEN status = "failed" THEN 1 ELSE 0 END) as failed
        FROM requests 
        WHERE platform = "youtube"
        AND created_at > datetime('now', '-24 hours')
    ''')
    yt_stats = db.cursor.fetchone()
    if yt_stats and yt_stats[0] > 0:
        success_rate = (yt_stats[1] / yt_stats[0]) * 100
        print(f"  YouTube:   {yt_stats[0]:4d} کل | {yt_stats[1]:4d} موفق | {yt_stats[2]:4d} ناموفق | {success_rate:.1f}% موفقیت")
    else:
        print(f"  YouTube:   هیچ درخواستی")
    
    # Universal
    db.cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = "success" THEN 1 ELSE 0 END) as success,
            SUM(CASE WHEN status = "failed" THEN 1 ELSE 0 END) as failed
        FROM requests 
        WHERE platform = "universal"
        AND created_at > datetime('now', '-24 hours')
    ''')
    uni_stats = db.cursor.fetchone()
    if uni_stats and uni_stats[0] > 0:
        success_rate = (uni_stats[1] / uni_stats[0]) * 100
        print(f"  Universal: {uni_stats[0]:4d} کل | {uni_stats[1]:4d} موفق | {uni_stats[2]:4d} ناموفق | {success_rate:.1f}% موفقیت")
    else:
        print(f"  Universal: هیچ درخواستی")
    
    # Instagram
    db.cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = "success" THEN 1 ELSE 0 END) as success,
            SUM(CASE WHEN status = "failed" THEN 1 ELSE 0 END) as failed
        FROM requests 
        WHERE platform = "instagram"
        AND created_at > datetime('now', '-24 hours')
    ''')
    ig_stats = db.cursor.fetchone()
    if ig_stats and ig_stats[0] > 0:
        success_rate = (ig_stats[1] / ig_stats[0]) * 100
        print(f"  Instagram: {ig_stats[0]:4d} کل | {ig_stats[1]:4d} موفق | {ig_stats[2]:4d} ناموفق | {success_rate:.1f}% موفقیت")
    else:
        print(f"  Instagram: هیچ درخواستی")
    
    print()
    print("=" * 80)
    print("✅ گزارش تمام شد")
    print("=" * 80)
    
    db.close()

if __name__ == "__main__":
    main()
