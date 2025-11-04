#!/usr/bin/env python3
"""
Migration script to add failed_requests table to the database
This script supports both MySQL and SQLite databases
"""

import sys
import os

# Add parent directory to path to import plugins
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins.db_wrapper import DB
from datetime import datetime


def migrate_failed_requests_table():
    """Add failed_requests table with indexes"""
    
    print("🚀 Starting failed_requests table migration...")
    print("=" * 60)
    
    try:
        # Initialize database connection
        db = DB()
        print(f"✅ Connected to {db.db_type} database")
        
        # Create failed_requests table
        print("\n📋 Creating failed_requests table...")
        
        if db.db_type == 'mysql':
            # MySQL version
            create_table_query = """
            CREATE TABLE IF NOT EXISTS failed_requests (
                id INTEGER UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT UNSIGNED NOT NULL,
                url TEXT NOT NULL,
                platform VARCHAR(64) NOT NULL,
                error_message TEXT,
                original_message_id BIGINT UNSIGNED,
                status VARCHAR(32) NOT NULL DEFAULT 'pending',
                created_at VARCHAR(32) NOT NULL,
                processed_at VARCHAR(32),
                retry_count INTEGER UNSIGNED NOT NULL DEFAULT 0,
                admin_notified TINYINT(1) NOT NULL DEFAULT 0,
                INDEX idx_failed_requests_status (status),
                INDEX idx_failed_requests_user (user_id),
                INDEX idx_failed_requests_created (created_at)
            ) CHARACTER SET utf8 COLLATE utf8_general_ci
            """
        else:
            # SQLite version
            create_table_query = """
            CREATE TABLE IF NOT EXISTS failed_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                platform TEXT NOT NULL,
                error_message TEXT,
                original_message_id INTEGER,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                processed_at TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0,
                admin_notified INTEGER NOT NULL DEFAULT 0
            )
            """
        
        db.cursor.execute(create_table_query)
        db.mydb.commit()
        print("✅ failed_requests table created successfully")
        
        # Create indexes for SQLite (MySQL indexes are created with table)
        if db.db_type == 'sqlite':
            print("\n📊 Creating indexes...")
            
            indexes = [
                ("idx_failed_requests_status", "CREATE INDEX IF NOT EXISTS idx_failed_requests_status ON failed_requests(status)"),
                ("idx_failed_requests_user", "CREATE INDEX IF NOT EXISTS idx_failed_requests_user ON failed_requests(user_id)"),
                ("idx_failed_requests_created", "CREATE INDEX IF NOT EXISTS idx_failed_requests_created ON failed_requests(created_at)")
            ]
            
            for idx_name, idx_query in indexes:
                try:
                    db.cursor.execute(idx_query)
                    print(f"  ✅ Created index: {idx_name}")
                except Exception as e:
                    print(f"  ⚠️  Index {idx_name} might already exist: {e}")
            
            db.mydb.commit()
            print("✅ All indexes created successfully")
        
        # Verify table creation
        print("\n🔍 Verifying table structure...")
        
        if db.db_type == 'mysql':
            db.cursor.execute("SHOW TABLES LIKE 'failed_requests'")
            if db.cursor.fetchone():
                print("✅ Table verified in MySQL")
                
                # Show table structure
                db.cursor.execute("DESCRIBE failed_requests")
                columns = db.cursor.fetchall()
                print("\n📋 Table structure:")
                for col in columns:
                    print(f"  - {col[0]}: {col[1]}")
        else:
            db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='failed_requests'")
            if db.cursor.fetchone():
                print("✅ Table verified in SQLite")
                
                # Show table structure
                db.cursor.execute("PRAGMA table_info(failed_requests)")
                columns = db.cursor.fetchall()
                print("\n📋 Table structure:")
                for col in columns:
                    print(f"  - {col[1]}: {col[2]}")
        
        # Close connection
        db.close()
        
        print("\n" + "=" * 60)
        print("🎉 Migration completed successfully!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = migrate_failed_requests_table()
    sys.exit(0 if success else 1)
