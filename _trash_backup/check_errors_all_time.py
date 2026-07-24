#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بررسی خطاها - همه زمان‌ها"""

from plugins.db_wrapper import DB

db = DB()

print("=" * 70)
print("📊 خطاهای کل (همه زمان‌ها)")
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
print("⚠️ Instagram که به Universal رفته (کل):")
db.cursor.execute('''
    SELECT COUNT(*) as count
    FROM requests 
    WHERE platform = "universal" 
    AND url LIKE "%instagram.com%"
''')

count = db.cursor.fetchone()[0]
if count > 0:
    print(f"  🚨 {count} لینک پیدا شد!")
else:
    print("  ✅ مشکلی نیست!")

print()
print("=" * 70)

db.close()
