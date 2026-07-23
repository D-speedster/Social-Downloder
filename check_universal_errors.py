#!/usr/bin/env python3
"""بررسی خطاهای Universal Downloader"""
from plugins.db_wrapper import DB

db = DB()

# خطاهای Universal
cursor = db.mydb.execute('''
    SELECT error_message, COUNT(*) as count 
    FROM requests 
    WHERE platform="universal" AND status="failed" 
    GROUP BY error_message 
    ORDER BY count DESC 
    LIMIT 15
''')

print("=" * 70)
print("🔴 خطاهای Universal Downloader")
print("=" * 70)
print()

errors = cursor.fetchall()
total_errors = sum(row[1] for row in errors)

for row in errors:
    error_msg = row[0] if row[0] else "Unknown"
    count = row[1]
    percentage = (count / total_errors * 100) if total_errors > 0 else 0
    print(f"[{count:3d}x] ({percentage:5.1f}%) {error_msg[:80]}")

print()
print("=" * 70)
print(f"📊 مجموع خطاها: {total_errors}")
print("=" * 70)
print()

# بررسی پلتفرم‌های مختلف در Universal
cursor2 = db.mydb.execute('''
    SELECT url, error_message 
    FROM requests 
    WHERE platform="universal" AND status="failed" 
    LIMIT 20
''')

print("🔍 نمونه URL های failed:")
print("=" * 70)
for idx, row in enumerate(cursor2.fetchall(), 1):
    url = row[0][:60] if row[0] else "N/A"
    error = row[1][:40] if row[1] else "Unknown"
    
    # تشخیص پلتفرم
    platform = "Unknown"
    if "spotify" in url.lower():
        platform = "Spotify"
    elif "tiktok" in url.lower():
        platform = "TikTok"
    elif "soundcloud" in url.lower():
        platform = "SoundCloud"
    elif "instagram" in url.lower():
        platform = "Instagram"
    elif "pinterest" in url.lower():
        platform = "Pinterest"
    elif "twitter" in url.lower() or "x.com" in url.lower():
        platform = "Twitter"
    
    print(f"{idx:2d}. [{platform:10s}] {url}")
    print(f"    ❌ {error}")
    print()

print("=" * 70)
