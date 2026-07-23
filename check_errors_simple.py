#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بررسی ساده خطاها - برای تست سریع"""

from plugins.db_wrapper import DB
from datetime import datetime, timedelta

db = DB()

# محاسبه زمان 24 ساعت پیش
now = datetime.now()
yesterday = now - timedelta(hours=24)
yesterday_str = yesterday.strftime('%Y-%m-%d %H:%M:%S')

print("=" * 70)
print("📊 خطاهای اخیر (آخرین 24 ساعت)")
print("=" * 70)
print(f"🕐 از: {yesterday_str}")
print(f"🕐 تا: {now.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)
print()

# خطاهای YouTube
print("🔴 YouTube (Top 5):")
db.cursor.execute('''
    SELECT error_message, COUNT(*) as count
    FROM requests 
    WHERE platform = "youtube" 
    AND status = "failed"
    AND created_at > ?
    GROUP BY error_message 
    ORDER BY count DESC 
    LIMIT 5
''', (yesterday_str,))

youtube_errors = db.cursor.fetchall()
if youtube_errors:
    for row in youtube_errors:
        print(f"  [{row[1]}x] {row[0][:60]}")
else:
    print("  ✅ هیچ خطایی در 24 ساعت گذشته!")

print()

# خطاهای Universal
print("🔴 Universal (Top 5):")
db.cursor.execute('''
    SELECT error_message, COUNT(*) as count
    FROM requests 
    WHERE platform = "universal" 
    AND status = "failed"
    AND created_at > ?
    GROUP BY error_message 
    ORDER BY count DESC 
    LIMIT 5
''', (yesterday_str,))

universal_errors = db.cursor.fetchall()
if universal_errors:
    for row in universal_errors:
        print(f"  [{row[1]}x] {row[0][:60]}")
else:
    print("  ✅ هیچ خطایی در 24 ساعت گذشته!")

print()

# خطاهای Instagram
print("🔴 Instagram (Top 5):")
db.cursor.execute('''
    SELECT error_message, COUNT(*) as count
    FROM requests 
    WHERE platform = "instagram" 
    AND status = "failed"
    AND created_at > ?
    GROUP BY error_message 
    ORDER BY count DESC 
    LIMIT 5
''', (yesterday_str,))

instagram_errors = db.cursor.fetchall()
if instagram_errors:
    for row in instagram_errors:
        print(f"  [{row[1]}x] {row[0][:60]}")
else:
    print("  ✅ هیچ خطایی در 24 ساعت گذشته!")

print()

# مشکل routing: Instagram که به Universal رفته
print("⚠️ Instagram که به Universal رفته (آخرین 24 ساعت):")
db.cursor.execute('''
    SELECT url, created_at
    FROM requests 
    WHERE platform = "universal" 
    AND status = "failed"
    AND url LIKE "%instagram.com%"
    AND created_at > ?
    ORDER BY created_at DESC 
    LIMIT 5
''', (yesterday_str,))

routing_errors = db.cursor.fetchall()
if routing_errors:
    print(f"  🚨 {len(routing_errors)} لینک پیدا شد!")
    for i, row in enumerate(routing_errors, 1):
        print(f"  {i}. {row[0][:60]}")
        print(f"     زمان: {row[1]}")
else:
    print("  ✅ مشکلی نیست!")

print()
print("=" * 70)
print("📈 آمار کلی (آخرین 24 ساعت):")
print("=" * 70)

# آمار YouTube
db.cursor.execute('''
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN status = "success" THEN 1 ELSE 0 END) as success,
        SUM(CASE WHEN status = "failed" THEN 1 ELSE 0 END) as failed
    FROM requests 
    WHERE platform = "youtube"
    AND created_at > ?
''', (yesterday_str,))
yt_stats = db.cursor.fetchone()
if yt_stats and yt_stats[0] > 0:
    success_rate = (yt_stats[1] / yt_stats[0]) * 100
    print(f"YouTube:   {yt_stats[0]:4d} کل | {yt_stats[1]:4d} موفق | {yt_stats[2]:4d} ناموفق | {success_rate:.1f}% موفقیت")
else:
    print(f"YouTube:   هیچ درخواستی")

# آمار Universal
db.cursor.execute('''
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN status = "success" THEN 1 ELSE 0 END) as success,
        SUM(CASE WHEN status = "failed" THEN 1 ELSE 0 END) as failed
    FROM requests 
    WHERE platform = "universal"
    AND created_at > ?
''', (yesterday_str,))
uni_stats = db.cursor.fetchone()
if uni_stats and uni_stats[0] > 0:
    success_rate = (uni_stats[1] / uni_stats[0]) * 100
    print(f"Universal: {uni_stats[0]:4d} کل | {uni_stats[1]:4d} موفق | {uni_stats[2]:4d} ناموفق | {success_rate:.1f}% موفقیت")
else:
    print(f"Universal: هیچ درخواستی")

# آمار Instagram
db.cursor.execute('''
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN status = "success" THEN 1 ELSE 0 END) as success,
        SUM(CASE WHEN status = "failed" THEN 1 ELSE 0 END) as failed
    FROM requests 
    WHERE platform = "instagram"
    AND created_at > ?
''', (yesterday_str,))
ig_stats = db.cursor.fetchone()
if ig_stats and ig_stats[0] > 0:
    success_rate = (ig_stats[1] / ig_stats[0]) * 100
    print(f"Instagram: {ig_stats[0]:4d} کل | {ig_stats[1]:4d} موفق | {ig_stats[2]:4d} ناموفق | {success_rate:.1f}% موفقیت")
else:
    print(f"Instagram: هیچ درخواستی")

print()
print("=" * 70)

db.close()
