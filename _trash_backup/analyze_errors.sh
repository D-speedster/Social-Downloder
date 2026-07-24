#!/bin/bash
# تحلیل دقیق خطاهای Universal و YouTube

echo "========================================================================"
echo "🔍 تحلیل دقیق خطاها"
echo "========================================================================"
echo ""

python3 << 'EOF'
from plugins.db_wrapper import DB
db = DB()

print("📊 خطاهای Universal (آخرین 20):")
print("=" * 70)
db.cursor.execute('''
    SELECT url, error_message, created_at 
    FROM requests 
    WHERE platform = "universal" AND status = "failed"
    ORDER BY id DESC 
    LIMIT 20
''')

for i, row in enumerate(db.cursor.fetchall(), 1):
    url = row[0][:40] if row[0] else 'No URL'
    error = row[1][:60] if row[1] else 'No error'
    print(f"{i}. {url}")
    print(f"   Error: {error}")
    print()

print("\n" + "=" * 70)
print("📊 خطاهای YouTube (آخرین 18):")
print("=" * 70)
db.cursor.execute('''
    SELECT url, error_message, created_at 
    FROM requests 
    WHERE platform = "youtube" AND status = "failed"
    ORDER BY id DESC 
    LIMIT 18
''')

for i, row in enumerate(db.cursor.fetchall(), 1):
    url = row[0][:40] if row[0] else 'No URL'
    error = row[1][:60] if row[1] else 'No error'
    print(f"{i}. {url}")
    print(f"   Error: {error}")
    print()

print("\n" + "=" * 70)
print("📊 آمار نوع خطاها:")
print("=" * 70)

# خطاهای رایج Universal
print("\nUniversal:")
db.cursor.execute('''
    SELECT error_message, COUNT(*) as count
    FROM requests 
    WHERE platform = "universal" AND status = "failed"
    GROUP BY error_message 
    ORDER BY count DESC 
    LIMIT 5
''')
for row in db.cursor.fetchall():
    error = row[0][:50] if row[0] else 'Unknown'
    print(f"  [{row[1]}x] {error}")

# خطاهای رایج YouTube
print("\nYouTube:")
db.cursor.execute('''
    SELECT error_message, COUNT(*) as count
    FROM requests 
    WHERE platform = "youtube" AND status = "failed"
    GROUP BY error_message 
    ORDER BY count DESC 
    LIMIT 5
''')
for row in db.cursor.fetchall():
    error = row[0][:50] if row[0] else 'Unknown'
    print(f"  [{row[1]}x] {error}")

EOF
