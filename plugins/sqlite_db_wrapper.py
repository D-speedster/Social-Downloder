import sqlite3
import os
import threading
from datetime import datetime, date
from datetime import datetime as _dt, timedelta as _td
from .db_path_manager import db_path_manager


# 🔥 Thread-safe connection pool
_thread_local = threading.local()
_db_path = None
_lock = threading.Lock()


def _get_connection():
    """Get thread-local database connection"""
    global _db_path
    
    if not hasattr(_thread_local, 'connection') or _thread_local.connection is None:
        if _db_path is None:
            raise RuntimeError("Database not initialized. Call DB() first.")
        
        # Create new connection for this thread
        conn = sqlite3.connect(_db_path, timeout=30, check_same_thread=True)
        
        # Apply optimizations
        cursor = conn.cursor()
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.execute('PRAGMA synchronous=NORMAL')
        cursor.execute('PRAGMA busy_timeout=30000')
        cursor.execute('PRAGMA cache_size=-10000')
        cursor.execute('PRAGMA temp_store=MEMORY')
        cursor.execute('PRAGMA page_size=4096')
        cursor.execute('PRAGMA mmap_size=268435456')
        
        _thread_local.connection = conn
        _thread_local.cursor = cursor
    
    return _thread_local.connection, _thread_local.cursor


class DB:
    def __init__(self):
        global _db_path
        
        # Use external database path based on OS
        db_path_manager.ensure_database_directory()
        db_path_manager.migrate_existing_database()
        
        with _lock:
            _db_path = db_path_manager.get_sqlite_db_path()
        
        # Get thread-local connection
        self.mydb, self.cursor = _get_connection()
        
        print(f"✅ SQLite thread-safe connection ready (thread: {threading.current_thread().name})")

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
            
            # Create jobs table for download tracking
            self.cursor.execute(
                """CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    url TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    format_id TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    progress INTEGER NOT NULL DEFAULT 0,
                    size_bytes INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )"""
            )

            # Create cookies table for YouTube cookie pool
            self.cursor.execute(
                """CREATE TABLE IF NOT EXISTS cookies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    format TEXT NOT NULL DEFAULT 'netscape',
                    cookie_text TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'unknown',
                    use_count INTEGER NOT NULL DEFAULT 0,
                    fail_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    last_used_at TEXT
                )"""
            )
            
            # Create bot_state table for tracking updates and recovery
            self.cursor.execute(
                """CREATE TABLE IF NOT EXISTS bot_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    last_update_id INTEGER NOT NULL DEFAULT 0,
                    last_startup TIMESTAMP,
                    last_shutdown TIMESTAMP,
                    total_startups INTEGER NOT NULL DEFAULT 0,
                    total_recovered_messages INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            
            # Initialize bot_state if not exists
            self.cursor.execute(
                """INSERT OR IGNORE INTO bot_state (id, last_update_id, total_startups) 
                   VALUES (1, 0, 0)"""
            )
            
            # Create failed_requests table
            self.cursor.execute(
                """CREATE TABLE IF NOT EXISTS failed_requests (
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
                )"""
            )
            
            # Create indexes for failed_requests
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_failed_requests_status ON failed_requests(status)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_failed_requests_user ON failed_requests(user_id)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_failed_requests_created ON failed_requests(created_at)")
            
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
            # Store first activity time as join time for stats
            query = 'INSERT INTO users (user_id, last_download, joined_at) VALUES (?, ?, ?)'
            record = (user_id, last_download, last_download)
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

    # --- Cookie pool operations ---
    def add_cookie(self, name: str, source_type: str, cookie_text: str, fmt: str = 'netscape', status: str = 'unknown') -> bool:
        try:
            now = _dt.now().isoformat(timespec='seconds')
            q = ('INSERT INTO cookies (name, source_type, format, cookie_text, status, use_count, fail_count, created_at) '
                 'VALUES (?, ?, ?, ?, ?, 0, 0, ?)')
            self.cursor.execute(q, (name, source_type, fmt, cookie_text, status, now))
            self.mydb.commit()
            return True
        except sqlite3.Error as e:
            print(f"Failed to add cookie: {e}")
            return False

    def list_cookies(self, limit: int = 50) -> list:
        try:
            query = 'SELECT id, name, source_type, format, status, use_count, fail_count, created_at, last_used_at FROM cookies ORDER BY id DESC LIMIT ?'
            self.cursor.execute(query, (limit,))
            rows = self.cursor.fetchall()
            return [{
                'id': r[0],
                'name': r[1],
                'source_type': r[2],
                'format': r[3],
                'status': r[4],
                'use_count': r[5],
                'fail_count': r[6],
                'created_at': r[7],
                'last_used_at': r[8]
            } for r in rows]
        except sqlite3.Error as e:
            print(f"Failed to list cookies: {e}")
            return []

    def get_cookie_by_id(self, cookie_id: int) -> dict:
        try:
            query = 'SELECT id, name, source_type, format, status, use_count, fail_count, created_at, last_used_at, cookie_text FROM cookies WHERE id = ?'
            self.cursor.execute(query, (cookie_id,))
            r = self.cursor.fetchone()
            if not r:
                return {}
            return {
                'id': r[0],
                'name': r[1],
                'source_type': r[2],
                'format': r[3],
                'status': r[4],
                'use_count': r[5],
                'fail_count': r[6],
                'created_at': r[7],
                'last_used_at': r[8],
                'cookie_text': r[9],
            }
        except sqlite3.Error as e:
            print(f"Failed to get cookie: {e}")
            return {}

    def delete_cookie(self, cookie_id: int) -> bool:
        try:
            self.cursor.execute('DELETE FROM cookies WHERE id = ?', (cookie_id,))
            self.mydb.commit()
            return True
        except sqlite3.Error as e:
            print(f"Failed to delete cookie: {e}")
            return False

    def update_cookie_status(self, cookie_id: int, status: str) -> None:
        try:
            self.cursor.execute('UPDATE cookies SET status = ? WHERE id = ?', (status, cookie_id))
            self.mydb.commit()
        except sqlite3.Error as e:
            print(f"Failed to update cookie status: {e}")

    def mark_cookie_used(self, cookie_id: int, success: bool) -> None:
        try:
            now = _dt.now().isoformat(timespec='seconds')
            self.cursor.execute('UPDATE cookies SET use_count = use_count + 1, last_used_at = ? WHERE id = ?', (now, cookie_id))
            if not success:
                self.cursor.execute('UPDATE cookies SET fail_count = fail_count + 1 WHERE id = ?', (cookie_id,))
            self.mydb.commit()
        except sqlite3.Error as e:
            print(f"Failed to update cookie usage: {e}")

    def get_next_cookie(self, prev_cookie_id: int | None) -> dict | None:
        try:
            # Simple round robin based on lowest use_count and fail_count
            rows = self.cursor.execute('SELECT id, name, source_type, format, status, use_count, fail_count, created_at, last_used_at, cookie_text FROM cookies ORDER BY use_count ASC, fail_count ASC, id ASC').fetchall()
            if not rows:
                return None
            if prev_cookie_id is None:
                # return first
                r = rows[0]
                return {
                    'id': r[0],
                    'name': r[1],
                    'source_type': r[2],
                    'format': r[3],
                    'status': r[4],
                    'use_count': r[5],
                    'fail_count': r[6],
                    'created_at': r[7],
                    'last_used_at': r[8],
                    'cookie_text': r[9],
                }
            # find next after prev
            idx = None
            for i, r in enumerate(rows):
                if r[0] == prev_cookie_id:
                    idx = i
                    break
            if idx is None:
                r = rows[0]
            else:
                r = rows[(idx + 1) % len(rows)]
            return {
                'id': r[0],
                'name': r[1],
                'source_type': r[2],
                'format': r[3],
                'status': r[4],
                'use_count': r[5],
                'fail_count': r[6],
                'created_at': r[7],
                'last_used_at': r[8],
                'cookie_text': r[9],
            }
        except sqlite3.Error as e:
            print(f"Failed to get next cookie: {e}")
            return None

    def set_blocked_until(self, user_id: int, until_str: str) -> None:
        try:
            self.cursor.execute('UPDATE users SET blocked_until = ? WHERE user_id = ?', (until_str, user_id))
            self.mydb.commit()
        except sqlite3.Error as e:
            print(f"Failed to set blocked_until: {e}")

    def increment_request(self, user_id: int, now_str: str) -> None:
        try:
            # Reset daily stats if date changed
            row = self.cursor.execute('SELECT daily_date FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if not row or row[0] != now_str:
                self.cursor.execute('UPDATE users SET daily_date = ?, daily_requests = 1, total_requests = total_requests + 1 WHERE user_id = ?', (now_str, user_id))
            else:
                self.cursor.execute('UPDATE users SET daily_requests = daily_requests + 1, total_requests = total_requests + 1 WHERE user_id = ?', (user_id,))
            self.mydb.commit()
        except sqlite3.Error as e:
            print(f"Failed to increment request: {e}")

    def get_system_stats(self) -> dict:
        stats = {
            'total_users': 0,
            'total_jobs': 0,
            'pending_jobs': 0,
            'running_jobs': 0,
            'completed_jobs': 0,
            'failed_jobs': 0,
        }
        try:
            for field, q in [
                ('total_users', 'SELECT COUNT(*) FROM users'),
                ('total_jobs', 'SELECT COUNT(*) FROM jobs'),
                ('pending_jobs', "SELECT COUNT(*) FROM jobs WHERE status = 'pending'"),
                ('running_jobs', "SELECT COUNT(*) FROM jobs WHERE status IN ('downloading','uploading')"),
                ('completed_jobs', "SELECT COUNT(*) FROM jobs WHERE status = 'completed'"),
                ('failed_jobs', "SELECT COUNT(*) FROM jobs WHERE status = 'error'"),
            ]:
                row = self.cursor.fetchone()
                stats[field] = int(row[0] or 0) if row else 0

            return stats
        except Exception as e:
            print(f"Error getting system stats: {e}")
            return stats
    
    def close(self):
        """Close database connection"""
        if self.mydb:
            self.mydb.close()
    
    # Job management methods
    def create_job(self, user_id: int, url: str = '', title: str = '', format_id: str = '', status: str = 'pending') -> int:
        """Create a new download job and return its ID"""
        try:
            query = '''INSERT INTO jobs (user_id, url, title, format_id, status, created_at, updated_at) 
                       VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)'''
            self.cursor.execute(query, (user_id, url, title, format_id, status))
            self.mydb.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as error:
            print(f"Failed to create job: {error}")
            return 0
    
    def update_job_status(self, job_id: int, status: str) -> None:
        """Update job status"""
        try:
            query = 'UPDATE jobs SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?'
            self.cursor.execute(query, (status, job_id))
            self.mydb.commit()
        except sqlite3.Error as error:
            print(f"Failed to update job status: {error}")
    
    def update_job_progress(self, job_id: int, progress: int) -> None:
        """Update job progress"""
        try:
            query = 'UPDATE jobs SET progress = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?'
            self.cursor.execute(query, (progress, job_id))
            self.mydb.commit()
        except sqlite3.Error as error:
            print(f"Failed to update job progress: {error}")
    
    def get_job(self, job_id: int) -> dict:
        """Get job by ID"""
        try:
            query = 'SELECT * FROM jobs WHERE id = ?'
            self.cursor.execute(query, (job_id,))
            row = self.cursor.fetchone()
            if row:
                columns = [description[0] for description in self.cursor.description]
                return dict(zip(columns, row))
            return {}
        except sqlite3.Error as error:
            print(f"Failed to get job: {error}")
            return {}
    
    def get_user_jobs(self, user_id: int, limit: int = 10) -> list:
        """Get recent jobs for a user"""
        try:
            query = 'SELECT * FROM jobs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?'
            self.cursor.execute(query, (user_id, limit))
            rows = self.cursor.fetchall()
            columns = [description[0] for description in self.cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        except sqlite3.Error as error:
            print(f"Failed to get user jobs: {error}")
            return []
    
    # --- Message recovery operations ---
    def get_last_update_id(self) -> int:
        """Get last processed update_id"""
        try:
            query = 'SELECT last_update_id FROM bot_state WHERE id = 1'
            result = self.cursor.execute(query).fetchone()
            return result[0] if result else 0
        except sqlite3.Error as e:
            print(f"Failed to get last_update_id: {e}")
            return 0
    
    def save_last_update_id(self, update_id: int) -> None:
        """Save last processed update_id"""
        try:
            query = '''UPDATE bot_state 
                       SET last_update_id = ?, updated_at = CURRENT_TIMESTAMP 
                       WHERE id = 1'''
            self.cursor.execute(query, (update_id,))
            self.mydb.commit()
        except sqlite3.Error as e:
            print(f"Failed to save last_update_id: {e}")
    
    def record_startup(self) -> None:
        """Record bot startup"""
        try:
            query = '''UPDATE bot_state 
                       SET last_startup = CURRENT_TIMESTAMP, 
                           total_startups = total_startups + 1,
                           updated_at = CURRENT_TIMESTAMP 
                       WHERE id = 1'''
            self.cursor.execute(query)
            self.mydb.commit()
        except sqlite3.Error as e:
            print(f"Failed to record startup: {e}")
    
    def record_shutdown(self) -> None:
        """Record bot shutdown"""
        try:
            query = '''UPDATE bot_state 
                       SET last_shutdown = CURRENT_TIMESTAMP,
                           updated_at = CURRENT_TIMESTAMP 
                       WHERE id = 1'''
            self.cursor.execute(query)
            self.mydb.commit()
        except sqlite3.Error as e:
            print(f"Failed to record shutdown: {e}")
    
    def increment_recovered_messages(self, count: int) -> None:
        """Increment recovered messages counter"""
        try:
            query = '''UPDATE bot_state 
                       SET total_recovered_messages = total_recovered_messages + ?,
                           updated_at = CURRENT_TIMESTAMP 
                       WHERE id = 1'''
            self.cursor.execute(query, (count,))
            self.mydb.commit()
        except sqlite3.Error as e:
            print(f"Failed to increment recovered messages: {e}")
    
    def get_bot_state(self) -> dict:
        """Get bot state information"""
        try:
            query = 'SELECT * FROM bot_state WHERE id = 1'
            self.cursor.execute(query)
            row = self.cursor.fetchone()
            if row:
                columns = [description[0] for description in self.cursor.description]
                return dict(zip(columns, row))
            return {}
        except sqlite3.Error as e:
            print(f"Failed to get bot state: {e}")
            return {}

    # --- Failed requests queue operations ---
    def add_failed_request(self, user_id: int, url: str, platform: str, error_message: str, original_message_id: int) -> int:
        """Add a failed request to the queue"""
        try:
            now = _dt.now().isoformat(timespec='seconds')
            q = ('INSERT INTO failed_requests (user_id, url, platform, error_message, original_message_id, status, created_at, retry_count, admin_notified) '
                 'VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0)')
            self.cursor.execute(q, (user_id, url, platform, error_message, original_message_id, 'pending', now))
            self.mydb.commit()
            return self.cursor.lastrowid or 0
        except sqlite3.Error as e:
            print(f"Failed to add failed request: {e}")
            return 0

    def get_pending_failed_requests(self, limit: int = 100) -> list:
        """Get all pending failed requests"""
        try:
            q = ('SELECT id, user_id, url, platform, error_message, original_message_id, status, created_at, processed_at, retry_count, admin_notified '
                 'FROM failed_requests WHERE status = ? ORDER BY created_at ASC LIMIT ?')
            self.cursor.execute(q, ('pending', limit))
            rows = self.cursor.fetchall() or []
            result = []
            for r in rows:
                result.append({
                    'id': r[0],
                    'user_id': r[1],
                    'url': r[2],
                    'platform': r[3],
                    'error_message': r[4],
                    'original_message_id': r[5],
                    'status': r[6],
                    'created_at': r[7],
                    'processed_at': r[8],
                    'retry_count': r[9],
                    'admin_notified': r[10]
                })
            return result
        except sqlite3.Error as e:
            print(f"Failed to get pending failed requests: {e}")
            return []

    def get_failed_request_by_id(self, request_id: int) -> dict:
        """Get a specific failed request by ID"""
        try:
            q = ('SELECT id, user_id, url, platform, error_message, original_message_id, status, created_at, processed_at, retry_count, admin_notified '
                 'FROM failed_requests WHERE id = ?')
            self.cursor.execute(q, (request_id,))
            r = self.cursor.fetchone()
            if not r:
                return {}
            return {
                'id': r[0],
                'user_id': r[1],
                'url': r[2],
                'platform': r[3],
                'error_message': r[4],
                'original_message_id': r[5],
                'status': r[6],
                'created_at': r[7],
                'processed_at': r[8],
                'retry_count': r[9],
                'admin_notified': r[10]
            }
        except sqlite3.Error as e:
            print(f"Failed to get failed request by id: {e}")
            return {}

    def mark_failed_request_as_processed(self, request_id: int) -> bool:
        """Mark a failed request as successfully processed"""
        try:
            now = _dt.now().isoformat(timespec='seconds')
            q = 'UPDATE failed_requests SET status = ?, processed_at = ? WHERE id = ?'
            self.cursor.execute(q, ('completed', now, request_id))
            self.mydb.commit()
            return True
        except sqlite3.Error as e:
            print(f"Failed to mark request as processed: {e}")
            return False

    def mark_failed_request_as_failed(self, request_id: int, error: str) -> bool:
        """Mark a failed request as permanently failed"""
        try:
            now = _dt.now().isoformat(timespec='seconds')
            q = 'UPDATE failed_requests SET status = ?, processed_at = ?, error_message = ? WHERE id = ?'
            self.cursor.execute(q, ('failed', now, error, request_id))
            self.mydb.commit()
            return True
        except sqlite3.Error as e:
            print(f"Failed to mark request as failed: {e}")
            return False

    def increment_failed_request_retry(self, request_id: int) -> bool:
        """Increment retry count for a failed request"""
        try:
            q = 'UPDATE failed_requests SET retry_count = retry_count + 1 WHERE id = ?'
            self.cursor.execute(q, (request_id,))
            self.mydb.commit()
            return True
        except sqlite3.Error as e:
            print(f"Failed to increment retry count: {e}")
            return False

    def mark_failed_request_admin_notified(self, request_id: int) -> bool:
        """Mark that admin has been notified about this request"""
        try:
            q = 'UPDATE failed_requests SET admin_notified = 1 WHERE id = ?'
            self.cursor.execute(q, (request_id,))
            self.mydb.commit()
            return True
        except sqlite3.Error as e:
            print(f"Failed to mark admin notified: {e}")
            return False

    def cleanup_old_failed_requests(self, days: int = 7) -> int:
        """Delete failed requests older than specified days"""
        try:
            cutoff_date = (_dt.now() - _td(days=days)).isoformat(timespec='seconds')
            q = 'DELETE FROM failed_requests WHERE created_at < ? AND status IN (?, ?)'
            self.cursor.execute(q, (cutoff_date, 'completed', 'failed'))
            deleted_count = self.cursor.rowcount
            self.mydb.commit()
            return deleted_count
        except sqlite3.Error as e:
            print(f"Failed to cleanup old requests: {e}")
            return 0

    def get_failed_requests_stats(self) -> dict:
        """Get statistics about failed requests queue"""
        stats = {
            'total': 0,
            'pending': 0,
            'processing': 0,
            'completed': 0,
            'failed': 0
        }
        try:
            # Total count
            self.cursor.execute('SELECT COUNT(*) FROM failed_requests')
            row = self.cursor.fetchone()
            stats['total'] = int(row[0] or 0) if row else 0

            # Count by status
            for status in ['pending', 'processing', 'completed', 'failed']:
                self.cursor.execute('SELECT COUNT(*) FROM failed_requests WHERE status = ?', (status,))
                row = self.cursor.fetchone()
                stats[status] = int(row[0] or 0) if row else 0
        except sqlite3.Error as e:
            print(f"Failed to get failed requests stats: {e}")
        return stats