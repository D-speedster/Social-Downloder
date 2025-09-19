import sqlite3
import os
from datetime import datetime, date
from datetime import datetime as _dt, timedelta as _td


class DB:
    def __init__(self):
        # Create database file in the plugins directory
        db_path = os.path.join(os.path.dirname(__file__), 'bot_database.db')
        self.mydb = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.mydb.cursor()

    def setup(self) -> None:
        try:
            # Create insta_acc table
            self.cursor.execute(
                """CREATE TABLE IF NOT EXISTS insta_acc (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL
                )"""
            )
            
            # Create users table
            self.cursor.execute(
                """CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    last_download TEXT NOT NULL,
                    joined_at TEXT NOT NULL DEFAULT '',
                    total_requests INTEGER NOT NULL DEFAULT 0,
                    daily_requests INTEGER NOT NULL DEFAULT 0,
                    daily_date TEXT NOT NULL DEFAULT '',
                    blocked_until TEXT NOT NULL DEFAULT ''
                )"""
            )
            
            # Create waiting_messages table for custom admin messages
            self.cursor.execute(
                """CREATE TABLE IF NOT EXISTS waiting_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL UNIQUE,
                    message_type TEXT NOT NULL DEFAULT 'text',
                    message_content TEXT NOT NULL,
                    file_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            
            # Insert default waiting messages if they don't exist
            self.cursor.execute(
                """INSERT OR IGNORE INTO waiting_messages (platform, message_type, message_content) 
                   VALUES ('youtube', 'text', 'در حال پردازش لینک یوتیوب...')"""
            )
            self.cursor.execute(
                """INSERT OR IGNORE INTO waiting_messages (platform, message_type, message_content) 
                   VALUES ('instagram', 'text', 'در حال پردازش لینک اینستاگرام...')"""
            )
            
            self.mydb.commit()
            print("Database tables created successfully!")
        except sqlite3.Error as error:
            print(f"Failed to create tables: {error}")

    def register_user(self, user_id: int, last_download: str) -> None:
        try:
            query = 'INSERT INTO users (user_id, last_download) VALUES (?, ?)'
            record = (user_id, last_download)
            self.cursor.execute(query, record)
            self.mydb.commit()
        except sqlite3.Error as error:
            print(f"Failed to insert user: {error}")

    def check_user_register(self, user_id: int) -> bool:
        try:
            query = 'SELECT user_id FROM users WHERE user_id = ?'
            self.cursor.execute(query, (user_id,))
            records = self.cursor.fetchall()
            return len(records) > 0
        except sqlite3.Error as error:
            print(f"Failed to check user: {error}")
            return False

    def get_users_id(self) -> any:
        try:
            query = 'SELECT user_id FROM users'
            self.cursor.execute(query)
            records = self.cursor.fetchall()
            return records
        except sqlite3.Error as error:
            print(f"Failed to get all users id: {error}")
            return []

    def get_insta_acc(self) -> any:
        try:
            query = 'SELECT username, password FROM insta_acc'
            self.cursor.execute(query)
            records = self.cursor.fetchall()
            return records
        except sqlite3.Error as error:
            print(f"Failed to get instagram account: {error}")
            return []

    def save_insta_acc(self, username: str, password: str) -> any:
        try:
            query = 'INSERT INTO insta_acc (username, password) VALUES (?, ?)'
            record = (username, password)
            self.cursor.execute(query, record)
            self.mydb.commit()
        except sqlite3.Error as error:
            print(f"Failed to insert instagram account: {error}")

    def get_last_download(self, user_id: int) -> str:
        try:
            query = 'SELECT last_download FROM users WHERE user_id = ?'
            self.cursor.execute(query, (user_id,))
            record = self.cursor.fetchall()
            if record:
                return record[0][0]
            return ""
        except sqlite3.Error as error:
            print(f"Failed to get last download of user: {error}")
            return ""

    def update_last_download(self, user_id: int, last_download: str) -> None:
        try:
            query = 'UPDATE users SET last_download = ? WHERE user_id = ?'
            record = (last_download, user_id)
            self.cursor.execute(query, record)
            self.mydb.commit()
        except sqlite3.Error as error:
            print(f"Failed to update last download of user: {error}")

    def get_waiting_message(self, platform: str) -> str:
        """Get custom waiting message for a platform"""
        try:
            query = 'SELECT message_content FROM waiting_messages WHERE platform = ?'
            self.cursor.execute(query, (platform,))
            record = self.cursor.fetchone()
            if record:
                return record[0]
            return None
        except sqlite3.Error as error:
            print(f"Failed to get waiting message: {error}")
            return None
    
    def get_waiting_message_full(self, platform: str) -> dict:
        """Get full waiting message info for a platform"""
        try:
            query = 'SELECT message_type, message_content, file_id FROM waiting_messages WHERE platform = ?'
            self.cursor.execute(query, (platform,))
            record = self.cursor.fetchone()
            if record:
                return {
                    'type': record[0],
                    'content': record[1],
                    'file_id': record[2]
                }
            return None
        except sqlite3.Error as error:
            print(f"Failed to get waiting message full: {error}")
            return None
    
    def set_waiting_message(self, platform: str, message_type: str, message_content: str, file_id: str = None) -> bool:
        """Set custom waiting message for a platform"""
        try:
            query = '''INSERT OR REPLACE INTO waiting_messages 
                      (platform, message_type, message_content, file_id, updated_at) 
                      VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)'''
            record = (platform, message_type, message_content, file_id)
            self.cursor.execute(query, record)
            self.mydb.commit()
            return True
        except sqlite3.Error as error:
            print(f"Failed to set waiting message: {error}")
            return False
    
    def get_all_waiting_messages(self) -> list:
        """Get all waiting messages for admin panel"""
        try:
            query = 'SELECT platform, message_type, message_content, file_id FROM waiting_messages'
            self.cursor.execute(query)
            records = self.cursor.fetchall()
            return [{
                'platform': record[0],
                'type': record[1],
                'content': record[2],
                'file_id': record[3]
            } for record in records]
        except sqlite3.Error as error:
            print(f"Failed to get all waiting messages: {error}")
            return []

    def get_blocked_until(self, user_id: int) -> str:
        """Get blocked_until timestamp for a user"""
        try:
            query = 'SELECT blocked_until FROM users WHERE user_id = ?'
            self.cursor.execute(query, (user_id,))
            record = self.cursor.fetchone()
            return record[0] if record and record[0] else ''
        except sqlite3.Error as error:
            print(f"Failed to get blocked_until: {error}")
            return ''
    
    def set_blocked_until(self, user_id: int, until_str: str) -> None:
        """Set blocked_until timestamp for a user"""
        try:
            query = 'UPDATE users SET blocked_until = ? WHERE user_id = ?'
            self.cursor.execute(query, (until_str, user_id))
            self.mydb.commit()
        except sqlite3.Error as error:
            print(f"Failed to set blocked_until: {error}")

    def increment_request(self, user_id: int, now_str: str) -> None:
        """Increase total and daily counters and update last_download."""
        try:
            # Ensure user exists
            if not self.check_user_register(user_id):
                self.register_user(user_id, now_str)
            
            # Update last_download
            self.cursor.execute('UPDATE users SET last_download = ? WHERE user_id = ?', (now_str, user_id))
            
            # Get current counters
            self.cursor.execute('SELECT daily_date, daily_requests, total_requests, blocked_until FROM users WHERE user_id = ?', (user_id,))
            row = self.cursor.fetchone()
            daily_date = row[0] if row else ''
            daily_requests = int(row[1] or 0) if row else 0
            total_requests = int(row[2] or 0) if row else 0
            blocked_until = row[3] or '' if row else ''
            
            # Reset daily counter if new day
            today = date.today().isoformat()
            if daily_date != today:
                daily_requests = 0
                daily_date = today
            
            # Increment counters
            daily_requests += 1
            total_requests += 1
            
            # Update counters
            self.cursor.execute('UPDATE users SET daily_date = ?, daily_requests = ?, total_requests = ? WHERE user_id = ?',
                                (daily_date, daily_requests, total_requests, user_id))
            
            # Enforce 1-hour block after 10 daily requests
            try:
                bu = _dt.fromisoformat(blocked_until) if blocked_until else None
            except Exception:
                bu = None
            
            now_dt = _dt.now()
            if daily_requests == 10 and (bu is None or bu <= now_dt):
                until_str = (now_dt + _td(hours=1)).isoformat(timespec='seconds')
                self.cursor.execute('UPDATE users SET blocked_until = ? WHERE user_id = ?', (until_str, user_id))
            
            self.mydb.commit()
        except Exception as e:
            print(f"Failed to increment request: {e}")

    def close(self):
        """Close database connection"""
        if self.mydb:
            self.mydb.close()