#!/usr/bin/env python3
"""
Test script to check database access and resolve lock issues
"""

import os
import sys
import sqlite3
import time
from pathlib import Path

# Add plugins directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'plugins'))

try:
    from db_path_manager import db_path_manager
    print("✓ Successfully imported db_path_manager")
except ImportError as e:
    print(f"✗ Failed to import db_path_manager: {e}")
    sys.exit(1)

def test_database_access():
    """Test database access and resolve any lock issues"""
    
    print("=== Database Access Test ===")
    
    # Get database info
    db_info = db_path_manager.get_database_info()
    print(f"OS Type: {db_info['os_type']}")
    print(f"Base Path: {db_info['base_path']}")
    print(f"SQLite Path: {db_info['sqlite_path']}")
    print(f"Directory Exists: {db_info['directory_exists']}")
    
    # Ensure database directory exists
    print("\n--- Creating database directory ---")
    if db_path_manager.ensure_database_directory():
        print("✓ Database directory created/verified")
    else:
        print("✗ Failed to create database directory")
        return False
    
    # Check if database file exists
    sqlite_path = db_path_manager.get_sqlite_db_path()
    print(f"\n--- Checking database file: {sqlite_path} ---")
    
    if os.path.exists(sqlite_path):
        print("✓ Database file exists")
        file_size = os.path.getsize(sqlite_path)
        print(f"File size: {file_size} bytes")
        
        # Check file permissions
        if os.access(sqlite_path, os.R_OK):
            print("✓ Database file is readable")
        else:
            print("✗ Database file is not readable")
            
        if os.access(sqlite_path, os.W_OK):
            print("✓ Database file is writable")
        else:
            print("✗ Database file is not writable")
    else:
        print("✗ Database file does not exist")
        print("Creating new database file...")
        
        try:
            # Create empty database file
            conn = sqlite3.connect(sqlite_path)
            conn.execute("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY)")
            conn.commit()
            conn.close()
            print("✓ Created new database file")
        except Exception as e:
            print(f"✗ Failed to create database file: {e}")
            return False
    
    # Test database connection
    print("\n--- Testing database connection ---")
    try:
        conn = sqlite3.connect(sqlite_path, timeout=10.0)
        cursor = conn.cursor()
        
        # Test write operation
        cursor.execute("CREATE TABLE IF NOT EXISTS connection_test (timestamp TEXT)")
        cursor.execute("INSERT INTO connection_test (timestamp) VALUES (?)", (str(time.time()),))
        conn.commit()
        
        # Test read operation
        cursor.execute("SELECT COUNT(*) FROM connection_test")
        count = cursor.fetchone()[0]
        print(f"✓ Database connection successful, test records: {count}")
        
        # Clean up test table
        cursor.execute("DROP TABLE IF EXISTS connection_test")
        conn.commit()
        conn.close()
        
        return True
        
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e).lower():
            print(f"✗ Database is locked: {e}")
            print("Attempting to resolve lock...")
            
            # Try to find and kill any processes using the database
            try:
                # Force close any existing connections
                if 'conn' in locals():
                    conn.close()
                
                # Wait a moment
                time.sleep(2)
                
                # Try again with a shorter timeout
                conn = sqlite3.connect(sqlite_path, timeout=1.0)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.close()
                print("✓ Database lock resolved")
                return True
                
            except Exception as e2:
                print(f"✗ Could not resolve database lock: {e2}")
                return False
        else:
            print(f"✗ Database error: {e}")
            return False
            
    except Exception as e:
        print(f"✗ Unexpected database error: {e}")
        return False

def check_for_running_bots():
    """Check for any running bot processes"""
    print("\n=== Checking for Running Bot Processes ===")
    
    import psutil
    
    bot_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                cmdline = proc.info['cmdline']
                if cmdline and any('main.py' in arg or 'bot.py' in arg for arg in cmdline):
                    bot_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if bot_processes:
        print(f"Found {len(bot_processes)} bot processes:")
        for proc in bot_processes:
            print(f"  PID: {proc.pid}, Command: {' '.join(proc.cmdline())}")
        return bot_processes
    else:
        print("✓ No bot processes found running")
        return []

if __name__ == "__main__":
    print("Starting database access test...\n")
    
    # Check for running bots first
    running_bots = check_for_running_bots()
    
    if running_bots:
        print("\n⚠️  Warning: Found running bot processes!")
        print("These may be causing database lock issues.")
        response = input("Do you want to terminate them? (y/n): ")
        if response.lower() == 'y':
            for proc in running_bots:
                try:
                    proc.terminate()
                    print(f"Terminated process {proc.pid}")
                except Exception as e:
                    print(f"Failed to terminate process {proc.pid}: {e}")
            time.sleep(2)
    
    # Test database access
    if test_database_access():
        print("\n🎉 Database access test PASSED!")
        print("You can now safely run the bot.")
    else:
        print("\n❌ Database access test FAILED!")
        print("Please check the errors above and resolve them before running the bot.")