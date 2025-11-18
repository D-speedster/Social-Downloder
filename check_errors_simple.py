#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بررسی ساده خطاها - برای تست سریع"""

from plugins.db_wrapper import DB

db = DB()

print("=" * 70)
print("📊 خطاهای اخیر")
print("=" * 70)
print()

# خطاهای YouTube
print("🔴 YouTube (Top 5):")
db.cursor.execute('''
    SELECT error_message, COUNT(*) as count
    FROM requests 
    WHERE platform = "youtube" 
    AND status = "failed"
    GROUP BY error_message 
    ORDER BY count DESC 
    LIMIT 5
''')
for row in db.cursor.fetchall():
    print(f"  [{row[1]}x] {row[0][:60]}")

print()

# خطاهای Universal
print("🔴 Universal (Top 5):")
db.cursor.execute('''
    SELECT error_message, COUNT(*) as count
    FROM requests 
    WHERE platform = "universal" 
    AND status = "failed"
    GROUP BY error_message 
    ORDER BY count DESC 
    LIMIT 5
''')
for row in db.cursor.fetchall():
    print(f"  [{row[1]}x] {row[0][:60]}")

print()

# خطاهای Instagram
print("🔴 Instagram (Top 5):")
db.cursor.execute('''
    SELECT error_message, COUNT(*) as count
    FROM requests 
    WHERE platform = "instagram" 
    AND status = "failed"
    GROUP BY error_message 
    ORDER BY count DESC 
    LIMIT 5
''')
for row in db.cursor.fetchall():
    print(f"  [{row[1]}x] {row[0][:60]}")

print()

# مشکل routing: Instagram که به Universal رفته
print("⚠️ Instagram که به Universal رفته (آخرین 5):")
db.cursor.execute('''
    SELECT url, created_at
    FROM requests 
    WHERE platform = "universal" 
    AND status = "failed"
    AND url LIKE "%instagram.com%"
    ORDER BY created_at DESC 
    LIMIT 5
''')

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

db.close()
