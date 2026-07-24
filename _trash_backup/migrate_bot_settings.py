#!/usr/bin/env python3
"""
Migration script to add bot_settings table
"""

from plugins.db_wrapper import DB

print("=" * 60)
print("Migration: Adding bot_settings table")
print("=" * 60)

db = DB()

try:
    if db.db_type == 'mysql':
        print("\n📊 Creating bot_settings table for MySQL...")
        db.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_settings (
                `key` VARCHAR(255) PRIMARY KEY,
                value TEXT,
                updated_at VARCHAR(32) NOT NULL
            ) CHARACTER SET `utf8` COLLATE `utf8_general_ci`
            """
        )
    else:
        print("\n📊 Creating bot_settings table for SQLite...")
        db.cursor.execute(
            """CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT NOT NULL
            )"""
        )
    
    db.mydb.commit()
    print("✅ Table created successfully!")
    
    # Test the table
    print("\n🧪 Testing table...")
    db.cursor.execute("SELECT COUNT(*) FROM bot_settings")
    count = db.cursor.fetchone()[0]
    print(f"✅ Table is working! Current rows: {count}")
    
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("Migration completed!")
print("=" * 60)
