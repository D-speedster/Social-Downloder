import os
import sqlite3
from config import db_config, USE_MYSQL
from datetime import datetime, date
from datetime import datetime as _dt, timedelta as _td

# Try to import mysql connector lazily only if enabled
if USE_MYSQL:
    try:
        import mysql.connector  # type: ignore
    except Exception:
        mysql = None
else:
    mysql = None


class DB:
    def __init__(self):
        self.mydb = None
        self.cursor = None
        self.db_type = None
        
        if USE_MYSQL and mysql is not None:
            try:
                # Validate MySQL config before connecting
                if not db_config.get('password'):
                    print("Warning: MySQL password is empty. This may be a security risk.")
                    
                # Try to connect to MySQL first
                self.mydb = mysql.connector.connect(
                    **db_config,
                    autocommit=True,  # Enable autocommit for better performance
                    connection_timeout=10,  # Add connection timeout
                    auth_plugin='mysql_native_password'  # Specify auth plugin
                )
                self.cursor = self.mydb.cursor(buffered=True)  # Use buffered cursor
                self.db_type = 'mysql'
                print("Connected to MySQL database successfully!")
                return
            except Exception as error:
                print(f"MySQL connection failed: {error}")
                print("Falling back to SQLite database...")
                
        # Fallback to SQLite with better security using external path
        from .db_path_manager import db_path_manager
        
        # Ensure database directory exists and migrate if needed
        db_path_manager.ensure_database_directory()
        db_path_manager.migrate_existing_database()
        
        db_path = db_path_manager.get_sqlite_db_path()
            
        self.mydb = sqlite3.connect(
            db_path, 
            check_same_thread=False, 
            timeout=30,
            isolation_level=None  # Enable autocommit mode
        )
        
        # Better concurrency and durability for SQLite
        try:
            self.mydb.execute('PRAGMA journal_mode=WAL;')
            self.mydb.execute('PRAGMA synchronous=NORMAL;')
            self.mydb.execute('PRAGMA temp_store=MEMORY;')
            self.mydb.execute('PRAGMA mmap_size=134217728;')  # 128MB
            self.mydb.execute('PRAGMA busy_timeout=5000;')
            self.mydb.execute('PRAGMA foreign_keys=ON;')  # Enable foreign key constraints
            self.mydb.execute('PRAGMA secure_delete=ON;')  # Secure delete for sensitive data
        except Exception as e:
            print(f"Warning: Failed to set SQLite pragmas: {e}")
            
        self.cursor = self.mydb.cursor()
        self.db_type = 'sqlite'
        print("Connected to SQLite database successfully!")

    def _has_column(self, table: str, column: str) -> bool:
        try:
            if self.db_type == 'mysql':
                self.cursor.execute(
                    "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
                    (table, column,)
                )
                return (self.cursor.fetchone() or [0])[0] > 0
            else:
                self.cursor.execute(f"PRAGMA table_info({table});")
                cols = [r[1] for r in self.cursor.fetchall()]
                return column in cols
        except Exception:
            return False

    def _ensure_user_columns(self):
        try:
            if self.db_type == 'mysql':
                # Add missing columns if not exists (MySQL 8 supports IF NOT EXISTS)
                self.cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS joined_at VARCHAR(255) NOT NULL DEFAULT '' AFTER last_download;")
                self.cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS total_requests BIGINT UNSIGNED NOT NULL DEFAULT 0;")
                self.cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS daily_requests BIGINT UNSIGNED NOT NULL DEFAULT 0;")
                self.cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS daily_date VARCHAR(32) NOT NULL DEFAULT '';")
                self.cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS blocked_until VARCHAR(255) NOT NULL DEFAULT '';")
                self.mydb.commit()
            else:
                # SQLite: add columns if absent
                if not self._has_column('users', 'joined_at'):
                    self.cursor.execute("ALTER TABLE users ADD COLUMN joined_at TEXT NOT NULL DEFAULT '';")
                if not self._has_column('users', 'total_requests'):
                    self.cursor.execute("ALTER TABLE users ADD COLUMN total_requests INTEGER NOT NULL DEFAULT 0;")
                if not self._has_column('users', 'daily_requests'):
                    self.cursor.execute("ALTER TABLE users ADD COLUMN daily_requests INTEGER NOT NULL DEFAULT 0;")
                if not self._has_column('users', 'daily_date'):
                    self.cursor.execute("ALTER TABLE users ADD COLUMN daily_date TEXT NOT NULL DEFAULT '';")
                if not self._has_column('users', 'blocked_until'):
                    self.cursor.execute("ALTER TABLE users ADD COLUMN blocked_until TEXT NOT NULL DEFAULT '';")
                self.mydb.commit()
        except Exception as e:
            print(f"Failed to ensure users columns: {e}")

    def setup(self) -> None:
        try:
            if self.db_type == 'mysql':
                self.cursor.execute(
                    "CREATE TABLE IF NOT EXISTS insta_acc (`id` INTEGER UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY, `username` VARCHAR(255) NOT NULL, `password` VARCHAR(255) NOT NULL) CHARACTER SET `utf8` COLLATE `utf8_general_ci`")
                self.cursor.execute(
                    "CREATE TABLE IF NOT EXISTS users (`id` INTEGER UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY, `user_id` BIGINT UNSIGNED NOT NULL, `last_download` VARCHAR(255) NOT NULL) CHARACTER SET `utf8` COLLATE `utf8_general_ci`")
                # Jobs table for dashboard
                self.cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS jobs (
                        id INTEGER UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        user_id BIGINT UNSIGNED NOT NULL,
                        title VARCHAR(512) NOT NULL,
                        status VARCHAR(32) NOT NULL,
                        size_bytes BIGINT UNSIGNED NULL,
                        link TEXT,
                        created_at VARCHAR(32) NOT NULL,
                        updated_at VARCHAR(32) NOT NULL
                    ) CHARACTER SET `utf8` COLLATE `utf8_general_ci`
                    """
                )
                # Cookies pool
                self.cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cookies (
                        id INTEGER UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        source_type VARCHAR(32) NOT NULL,
                        format VARCHAR(32) NOT NULL DEFAULT 'netscape',
                        cookie_text MEDIUMTEXT NOT NULL,
                        status VARCHAR(16) NOT NULL DEFAULT 'unknown',
                        use_count BIGINT UNSIGNED NOT NULL DEFAULT 0,
                        fail_count BIGINT UNSIGNED NOT NULL DEFAULT 0,
                        created_at VARCHAR(32) NOT NULL,
                        last_used_at VARCHAR(32) NULL
                    ) CHARACTER SET `utf8` COLLATE `utf8_general_ci`
                    """
                )
                # User settings (quality, language)
                self.cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_settings (
                        user_id BIGINT UNSIGNED NOT NULL PRIMARY KEY,
                        quality VARCHAR(32) NOT NULL DEFAULT 'auto',
                        language VARCHAR(8) NOT NULL DEFAULT 'fa'
                    ) CHARACTER SET `utf8` COLLATE `utf8_general_ci`
                    """
                )
                # Requests table for statistics
                self.cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS requests (
                        id INTEGER UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        user_id BIGINT UNSIGNED NOT NULL,
                        platform VARCHAR(64) NOT NULL,
                        url TEXT,
                        status VARCHAR(32) NOT NULL,
                        created_at VARCHAR(32) NOT NULL,
                        completed_at VARCHAR(32),
                        processing_time DOUBLE,
                        error_message TEXT,
                        INDEX idx_requests_platform (platform),
                        INDEX idx_requests_created_at (created_at),
                        INDEX idx_requests_status (status)
                    ) CHARACTER SET `utf8` COLLATE `utf8_general_ci`
                    """
                )
                # Failed requests queue
                self.cursor.execute(
                    """
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
                    ) CHARACTER SET `utf8` COLLATE `utf8_general_ci`
                    """
                )
            else:  # SQLite
                self.cursor.execute(
                    """CREATE TABLE IF NOT EXISTS insta_acc (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        password TEXT NOT NULL
                    )""")
                self.cursor.execute(
                    """CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        last_download TEXT NOT NULL
                    )""")
                # Jobs table for dashboard
                self.cursor.execute(
                    """CREATE TABLE IF NOT EXISTS jobs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        title TEXT NOT NULL,
                        status TEXT NOT NULL,
                        size_bytes INTEGER,
                        link TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )"""
                )
                # Requests table for statistics
                self.cursor.execute(
                    """CREATE TABLE IF NOT EXISTS requests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        platform TEXT NOT NULL,
                        url TEXT,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        completed_at TEXT,
                        processing_time REAL,
                        error_message TEXT
                    )"""
                )
                # Create index for better performance
                self.cursor.execute(
                    """CREATE INDEX IF NOT EXISTS idx_requests_platform 
                    ON requests(platform)"""
                )
                self.cursor.execute(
                    """CREATE INDEX IF NOT EXISTS idx_requests_created_at 
                    ON requests(created_at)"""
                )
                self.cursor.execute(
                    """CREATE INDEX IF NOT EXISTS idx_requests_status 
                    ON requests(status)"""
                )
                # Cookies pool
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
                # Failed requests queue
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
            self.mydb.commit()
        except Exception as e:
            print(f"Database setup failed: {e}")

    def register_user(self, user_id: int, last_download: str) -> None:
        try:
            # Ensure all extended columns exist first
            self._ensure_user_columns()
            # treat incoming last_download also as joined_at for first time registration
            joined_at = last_download
            if self.db_type == 'mysql':
                query = 'INSERT INTO users (user_id, last_download, joined_at, total_requests, daily_requests, daily_date, blocked_until) VALUES (%s, %s, %s, 0, 0, "", "")'
                record = (user_id, last_download, joined_at)
            else:
                query = 'INSERT INTO users (user_id, last_download, joined_at, total_requests, daily_requests, daily_date, blocked_until) VALUES (?, ?, ?, 0, 0, "", "")'
                record = (user_id, last_download, joined_at)
            self.cursor.execute(query, record)
            self.mydb.commit()
        except Exception as e:
            print(f"Failed to register user: {e}")

    def check_user_register(self, user_id: int) -> bool:
        try:
            if self.db_type == 'mysql':
                query = 'SELECT * FROM users WHERE user_id = %s'
            else:
                query = 'SELECT * FROM users WHERE user_id = ?'
            self.cursor.execute(query, (user_id,))
            record = self.cursor.fetchall()
            if record:
                return True
            return False
        except Exception as e:
            print(f"Failed to check user register: {e}")
            return False

    def get_users_id(self) -> any:
        try:
            if self.db_type == 'mysql':
                self.cursor.execute('SELECT user_id FROM users')
            else:
                self.cursor.execute('SELECT user_id FROM users')
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Failed to fetch users id: {e}")
            return []

    def get_insta_acc(self) -> any:
        try:
            if self.db_type == 'mysql':
                query = 'SELECT username, password FROM insta_acc WHERE id = 1'
            else:
                query = 'SELECT username, password FROM insta_acc WHERE id = 1'
            self.cursor.execute(query)
            record = self.cursor.fetchall()
            return record
        except Exception as e:
            print(f"Failed to get instagram account: {e}")
            return []

    def save_insta_acc(self, username: str, password: str) -> any:
        try:
            if self.db_type == 'mysql':
                query = 'INSERT INTO insta_acc (username, password) VALUES (%s, %s)'
            else:
                query = 'INSERT INTO insta_acc (username, password) VALUES (?, ?)'
            record = (username, password)
            self.cursor.execute(query, record)
            self.mydb.commit()
            return True
        except Exception as e:
            print(f"Failed to save instagram account: {e}")
            return False

    def get_last_download(self, user_id: int) -> str:
        try:
            if self.db_type == 'mysql':
                query = 'SELECT last_download FROM users WHERE user_id = %s'
            else:
                query = 'SELECT last_download FROM users WHERE user_id = ?'
            self.cursor.execute(query, (user_id,))
            record = self.cursor.fetchall()
            if record:
                return record[0][0]
            return ""
        except Exception as error:
            print("Failed to get last download of user: {}".format(error))
            return ""

    def update_last_download(self, user_id: int, last_download: str) -> None:
        try:
            if self.db_type == 'mysql':
                query = 'UPDATE users SET last_download = %s WHERE user_id = %s'
            else:  # SQLite
                query = 'UPDATE users SET last_download = ? WHERE user_id = ?'
            record = (last_download, user_id)
            self.cursor.execute(query, record)
            self.mydb.commit()
        except Exception as error:
            print("Failed to update last download of user: {}".format(error))

    def get_blocked_until(self, user_id: int) -> str:
        try:
            self._ensure_user_columns()
            if self.db_type == 'mysql':
                query = 'SELECT blocked_until FROM users WHERE user_id = %s'
            else:
                query = 'SELECT blocked_until FROM users WHERE user_id = ?'
            self.cursor.execute(query, (user_id,))
            row = self.cursor.fetchone()
            return row[0] if row and row[0] else ''
        except Exception as e:
            print(f"Failed to get blocked_until: {e}")
            return ''

    def set_blocked_until(self, user_id: int, until_str: str) -> None:
        try:
            self._ensure_user_columns()
            if self.db_type == 'mysql':
                query = 'UPDATE users SET blocked_until = %s WHERE user_id = %s'
            else:
                query = 'UPDATE users SET blocked_until = ? WHERE user_id = ?'
            self.cursor.execute(query, (until_str, user_id))
            self.mydb.commit()
        except Exception as e:
            print(f"Failed to set blocked_until: {e}")

    def increment_request(self, user_id: int, now_str: str) -> None:
        """Increase total and daily counters and update last_download."""
        try:
            # Ensure user exists
            if not self.check_user_register(user_id):
                self.register_user(user_id, now_str)
            self._ensure_user_columns()
            if self.db_type == 'mysql':
                # Update last_download
                self.cursor.execute('UPDATE users SET last_download = %s WHERE user_id = %s', (now_str, user_id))
                # Ensure daily_date and counters
                self.cursor.execute('SELECT daily_date, daily_requests, total_requests, blocked_until FROM users WHERE user_id = %s', (user_id,))
                row = self.cursor.fetchone()
                daily_date = row[0] if row else ''
                daily_requests = int(row[1] or 0) if row else 0
                total_requests = int(row[2] or 0) if row else 0
                blocked_until = row[3] or '' if row else ''
                today = date.today().isoformat()
                if daily_date != today:
                    daily_requests = 0
                    daily_date = today
                daily_requests += 1
                total_requests += 1
                self.cursor.execute('UPDATE users SET daily_date = %s, daily_requests = %s, total_requests = %s WHERE user_id = %s',
                                    (daily_date, daily_requests, total_requests, user_id))
                # Enforce 1-hour block after 10 daily requests
                try:
                    bu = _dt.fromisoformat(blocked_until) if blocked_until else None
                except Exception:
                    bu = None
                now_dt = _dt.now()
                if daily_requests == 10 and (bu is None or bu <= now_dt):
                    until_str = (now_dt + _td(hours=1)).isoformat(timespec='seconds')
                    self.cursor.execute('UPDATE users SET blocked_until = %s WHERE user_id = %s', (until_str, user_id))
                self.mydb.commit()
            else:
                # SQLite path
                self.cursor.execute('UPDATE users SET last_download = ? WHERE user_id = ?', (now_str, user_id))
                self.cursor.execute('SELECT daily_date, daily_requests, total_requests, blocked_until FROM users WHERE user_id = ?', (user_id,))
                row = self.cursor.fetchone()
                daily_date = row[0] if row else ''
                daily_requests = int(row[1] or 0) if row else 0
                total_requests = int(row[2] or 0) if row else 0
                blocked_until = row[3] or '' if row else ''
                today = date.today().isoformat()
                if daily_date != today:
                    daily_requests = 0
                    daily_date = today
                daily_requests += 1
                total_requests += 1
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

    def get_user_profile(self, user_id: int) -> dict:
        """Return profile information for account page."""
        try:
            self._ensure_user_columns()
            if self.db_type == 'mysql':
                self.cursor.execute('SELECT joined_at, last_download, total_requests, daily_requests, daily_date FROM users WHERE user_id = %s', (user_id,))
            else:
                self.cursor.execute('SELECT joined_at, last_download, total_requests, daily_requests, daily_date FROM users WHERE user_id = ?', (user_id,))
            row = self.cursor.fetchone()
            if not row:
                return {
                    'joined_at': '',
                    'last_download': '',
                    'total_requests': 0,
                    'daily_requests': 0,
                    'daily_date': ''
                }
            return {
                'joined_at': row[0] or '',
                'last_download': row[1] or '',
                'total_requests': int(row[2] or 0),
                'daily_requests': int(row[3] or 0),
                'daily_date': row[4] or ''
            }
        except Exception as e:
            print(f"Failed to get user profile: {e}")
            return {
                'joined_at': '',
                'last_download': '',
                'total_requests': 0,
                'daily_requests': 0,
                'daily_date': ''
            }

    def create_job(self, user_id: int, title: str, status: str = 'pending', size_bytes: int | None = None, link: str | None = None) -> int:
        try:
            from datetime import datetime as _dt
            now = _dt.now().isoformat(timespec='seconds')
            if self.db_type == 'mysql':
                self.cursor.execute(
                    'INSERT INTO jobs (user_id, title, status, size_bytes, link, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                    (user_id, title, status, size_bytes, link, now, now)
                )
                self.mydb.commit()
                return self.cursor.lastrowid or 0
            else:
                self.cursor.execute(
                    'INSERT INTO jobs (user_id, title, status, size_bytes, link, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (user_id, title, status, size_bytes, link, now, now)
                )
                self.mydb.commit()
                return self.cursor.lastrowid or 0
        except Exception as e:
            print(f"Failed to create job: {e}")
            return 0

    def update_job_status(self, job_id: int, status: str, link: str | None = None, size_bytes: int | None = None, title: str | None = None) -> None:
        try:
            from datetime import datetime as _dt
            now = _dt.now().isoformat(timespec='seconds')
            set_parts = ['status = ?' if self.db_type == 'sqlite' else 'status = %s', 'updated_at = ?' if self.db_type == 'sqlite' else 'updated_at = %s']
            params = [status, now]
            if link is not None:
                set_parts.append('link = ?' if self.db_type == 'sqlite' else 'link = %s')
                params.append(link)
            if size_bytes is not None:
                set_parts.append('size_bytes = ?' if self.db_type == 'sqlite' else 'size_bytes = %s')
                params.append(size_bytes)
            if title is not None:
                set_parts.append('title = ?' if self.db_type == 'sqlite' else 'title = %s')
                params.append(title)
            set_clause = ', '.join(set_parts)
            if self.db_type == 'mysql':
                query = f'UPDATE jobs SET {set_clause} WHERE id = %s'
                params.append(job_id)
            else:
                query = f'UPDATE jobs SET {set_clause} WHERE id = ?'
                params.append(job_id)
            self.cursor.execute(query, tuple(params))
            self.mydb.commit()
        except Exception as e:
            print(f"Failed to update job status: {e}")

    def get_recent_jobs(self, user_id: int, statuses: list[str], limit: int = 5) -> list[dict]:
        try:
            placeholders = ','.join(['?']*len(statuses)) if self.db_type == 'sqlite' else ','.join(['%s']*len(statuses))
            if self.db_type == 'mysql':
                query = f'SELECT id, title, status, size_bytes, link, created_at, updated_at FROM jobs WHERE user_id = %s AND status IN ({placeholders}) ORDER BY id DESC LIMIT %s'
                params = [user_id] + statuses + [limit]
            else:
                query = f'SELECT id, title, status, size_bytes, link, created_at, updated_at FROM jobs WHERE user_id = ? AND status IN ({placeholders}) ORDER BY id DESC LIMIT ?'
                params = [user_id] + statuses + [limit]
            self.cursor.execute(query, tuple(params))
            rows = self.cursor.fetchall() or []
            result = []
            for r in rows:
                result.append({
                    'id': r[0],
                    'title': r[1],
                    'status': r[2],
                    'size_bytes': r[3],
                    'link': r[4],
                    'created_at': r[5],
                    'updated_at': r[6],
                })
            return result
        except Exception as e:
            print(f"Failed to get recent jobs: {e}")
            return []

    def get_user_settings(self, user_id: int) -> dict:
        try:
            if self.db_type == 'mysql':
                self.cursor.execute('SELECT quality, language FROM user_settings WHERE user_id = %s', (user_id,))
            else:
                self.cursor.execute('SELECT quality, language FROM user_settings WHERE user_id = ?', (user_id,))
            row = self.cursor.fetchone()
            if not row:
                return { 'quality': 'auto', 'language': 'fa' }
            return { 'quality': row[0] or 'auto', 'language': row[1] or 'fa' }
        except Exception:
            return { 'quality': 'auto', 'language': 'fa' }

    def set_quality(self, user_id: int, quality: str) -> None:
        try:
            if self.db_type == 'mysql':
                self.cursor.execute('INSERT INTO user_settings (user_id, quality, language) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE quality = VALUES(quality)', (user_id, quality, 'fa'))
            else:
                # SQLite upsert
                self.cursor.execute('INSERT INTO user_settings (user_id, quality, language) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET quality=excluded.quality', (user_id, quality, 'fa'))
            self.mydb.commit()
        except Exception as e:
            print(f"Failed to set quality: {e}")

    def set_language(self, user_id: int, language: str) -> None:
        try:
            if self.db_type == 'mysql':
                self.cursor.execute('INSERT INTO user_settings (user_id, quality, language) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE language = VALUES(language)', (user_id, 'auto', language))
            else:
                # SQLite upsert
                self.cursor.execute('INSERT INTO user_settings (user_id, quality, language) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET language=excluded.language', (user_id, 'auto', language))
            self.mydb.commit()
        except Exception as e:
            print(f"Failed to set language: {e}")

    def clear_user_history(self, user_id: int) -> None:
        try:
            if self.db_type == 'mysql':
                self.cursor.execute('DELETE FROM jobs WHERE user_id = %s', (user_id,))
                self.cursor.execute('UPDATE users SET total_requests = 0, daily_requests = 0, last_download = %s WHERE user_id = %s', ('', user_id))
            else:
                self.cursor.execute('DELETE FROM jobs WHERE user_id = ?', (user_id,))
                self.cursor.execute('UPDATE users SET total_requests = 0, daily_requests = 0, last_download = ? WHERE user_id = ?', ('', user_id))
            self.mydb.commit()
        except Exception as e:
            print(f"Failed to clear user history: {e}")

    def get_system_stats(self) -> dict:
        """Aggregate statistics for admin panel."""
        stats = {
            'total_users': 0,
            'users_today': 0,
            'active_today': 0,
            'total_requests_sum': 0,
            'blocked_count': 0,
            'total_jobs': 0,
            'jobs_pending': 0,
            'jobs_ready': 0,
            'jobs_completed': 0,
        }
        try:
            self._ensure_user_columns()
            today = date.today().isoformat()
            # Users count
            self.cursor.execute('SELECT COUNT(*) FROM users')
            row = self.cursor.fetchone()
            stats['total_users'] = int(row[0] or 0) if row else 0

            # Users joined today (joined_at LIKE 'YYYY-MM-DD%')
            try:
                if self.db_type == 'mysql':
                    self.cursor.execute('SELECT COUNT(*) FROM users WHERE joined_at LIKE %s', (today + '%',))
                else:
                    self.cursor.execute('SELECT COUNT(*) FROM users WHERE joined_at LIKE ?', (today + '%',))
                row = self.cursor.fetchone()
                stats['users_today'] = int(row[0] or 0) if row else 0
            except Exception:
                stats['users_today'] = 0

            # Active today (daily_date == today AND daily_requests > 0)
            if self.db_type == 'mysql':
                self.cursor.execute('SELECT COUNT(*) FROM users WHERE daily_date = %s AND daily_requests > 0', (today,))
            else:
                self.cursor.execute('SELECT COUNT(*) FROM users WHERE daily_date = ? AND daily_requests > 0', (today,))
            row = self.cursor.fetchone()
            stats['active_today'] = int(row[0] or 0) if row else 0

            # Total requests sum
            self.cursor.execute('SELECT SUM(total_requests) FROM users')
            row = self.cursor.fetchone()
            stats['total_requests_sum'] = int(row[0] or 0) if row and row[0] is not None else 0

            # Blocked count (blocked_until > now)
            try:
                now_str = _dt.now().isoformat(timespec='seconds')
                if self.db_type == 'mysql':
                    self.cursor.execute('SELECT COUNT(*) FROM users WHERE blocked_until > %s', (now_str,))
                else:
                    self.cursor.execute('SELECT COUNT(*) FROM users WHERE blocked_until > ?', (now_str,))
                row = self.cursor.fetchone()
                stats['blocked_count'] = int(row[0] or 0) if row else 0
            except Exception:
                stats['blocked_count'] = 0

            # Jobs counts
            self.cursor.execute('SELECT COUNT(*) FROM jobs')
            row = self.cursor.fetchone()
            stats['total_jobs'] = int(row[0] or 0) if row else 0

            for status_key, field in [('pending', 'jobs_pending'), ('ready', 'jobs_ready'), ('completed', 'jobs_completed')]:
                if self.db_type == 'mysql':
                    self.cursor.execute('SELECT COUNT(*) FROM jobs WHERE status = %s', (status_key,))
                else:
                    self.cursor.execute('SELECT COUNT(*) FROM jobs WHERE status = ?', (status_key,))
                row = self.cursor.fetchone()
                stats[field] = int(row[0] or 0) if row else 0
        except Exception as e:
            print(f"Failed to get system stats: {e}")
        return stats

    def close(self):
        try:
            self.cursor.close()
            self.mydb.close()
        except Exception:
            pass

    # --- Cookie pool operations ---
    def add_cookie(self, name: str, source_type: str, cookie_text: str, fmt: str = 'netscape', status: str = 'unknown') -> bool:
        try:
            now = _dt.now().isoformat(timespec='seconds')
            if self.db_type == 'mysql':
                q = ('INSERT INTO cookies (name, source_type, format, cookie_text, status, use_count, fail_count, created_at) '
                     'VALUES (%s, %s, %s, %s, %s, 0, 0, %s)')
                self.cursor.execute(q, (name, source_type, fmt, cookie_text, status, now))
            else:
                q = ('INSERT INTO cookies (name, source_type, format, cookie_text, status, use_count, fail_count, created_at) '
                     'VALUES (?, ?, ?, ?, ?, 0, 0, ?)')
                self.cursor.execute(q, (name, source_type, fmt, cookie_text, status, now))
            self.mydb.commit()
            return True
        except Exception as e:
            print(f"Failed to add cookie: {e}")
            return False

    def list_cookies(self, limit: int = 50) -> list[dict]:
        try:
            if self.db_type == 'mysql':
                q = 'SELECT id, name, source_type, status, use_count, fail_count, last_used_at, created_at FROM cookies ORDER BY id DESC LIMIT %s'
                self.cursor.execute(q, (limit,))
            else:
                q = 'SELECT id, name, source_type, status, use_count, fail_count, last_used_at, created_at FROM cookies ORDER BY id DESC LIMIT ?'
                self.cursor.execute(q, (limit,))
            rows = self.cursor.fetchall() or []
            result = []
            for r in rows:
                result.append({
                    'id': r[0], 'name': r[1], 'source_type': r[2], 'status': r[3],
                    'use_count': r[4], 'fail_count': r[5], 'last_used_at': r[6], 'created_at': r[7]
                })
            return result
        except Exception as e:
            print(f"Failed to list cookies: {e}")
            return []

    def get_cookie_by_id(self, cookie_id: int) -> dict | list[dict]:
        try:
            if self.db_type == 'mysql':
                q = 'SELECT id, name, source_type, format, cookie_text, status, use_count, fail_count, last_used_at, created_at FROM cookies WHERE id = %s'
                self.cursor.execute(q, (cookie_id,))
            else:
                q = 'SELECT id, name, source_type, format, cookie_text, status, use_count, fail_count, last_used_at, created_at FROM cookies WHERE id = ?'
                self.cursor.execute(q, (cookie_id,))
            r = self.cursor.fetchone()
            if not r:
                return {}
            return {
                'id': r[0], 'name': r[1], 'source_type': r[2], 'format': r[3], 'cookie_text': r[4],
                'status': r[5], 'use_count': r[6], 'fail_count': r[7], 'last_used_at': r[8], 'created_at': r[9]
            }
        except Exception as e:
            print(f"Failed to get cookie by id: {e}")
            return {}

    def delete_cookie(self, cookie_id: int) -> bool:
        try:
            if self.db_type == 'mysql':
                q = 'DELETE FROM cookies WHERE id = %s'
                self.cursor.execute(q, (cookie_id,))
            else:
                q = 'DELETE FROM cookies WHERE id = ?'
                self.cursor.execute(q, (cookie_id,))
            self.mydb.commit()
            return True
        except Exception as e:
            print(f"Failed to delete cookie: {e}")
            return False

    def update_cookie_status(self, cookie_id: int, status: str) -> None:
        try:
            if self.db_type == 'mysql':
                q = 'UPDATE cookies SET status = %s WHERE id = %s'
                self.cursor.execute(q, (status, cookie_id))
            else:
                q = 'UPDATE cookies SET status = ? WHERE id = ?'
                self.cursor.execute(q, (status, cookie_id))
            self.mydb.commit()
        except Exception as e:
            print(f"Failed to update cookie status: {e}")

    def mark_cookie_used(self, cookie_id: int, success: bool) -> None:
        try:
            now = _dt.now().isoformat(timespec='seconds')
            # Get current counters
            if self.db_type == 'mysql':
                self.cursor.execute('SELECT use_count, fail_count FROM cookies WHERE id = %s', (cookie_id,))
            else:
                self.cursor.execute('SELECT use_count, fail_count FROM cookies WHERE id = ?', (cookie_id,))
            row = self.cursor.fetchone()
            use_count = int(row[0] or 0) if row else 0
            fail_count = int(row[1] or 0) if row else 0
            use_count += 1
            if not success:
                fail_count += 1
            # Update
            if self.db_type == 'mysql':
                self.cursor.execute('UPDATE cookies SET use_count = %s, fail_count = %s, last_used_at = %s WHERE id = %s', (use_count, fail_count, now, cookie_id))
            else:
                self.cursor.execute('UPDATE cookies SET use_count = ?, fail_count = ?, last_used_at = ? WHERE id = ?', (use_count, fail_count, now, cookie_id))
            self.mydb.commit()
        except Exception as e:
            print(f"Failed to mark cookie used: {e}")

    def get_next_cookie(self, prev_cookie_id: int | None) -> dict | None:
        """Pick the least recently used cookie, avoiding immediate reuse of prev_cookie_id."""
        try:
            # Exclude disabled/invalid
            if self.db_type == 'mysql':
                q = ('SELECT id, name, cookie_text FROM cookies WHERE status != %s '
                     'ORDER BY COALESCE(last_used_at, "1970-01-01 00:00:00") ASC, use_count ASC LIMIT 2')
                self.cursor.execute(q, ('disabled',))
            else:
                q = ('SELECT id, name, cookie_text FROM cookies WHERE status != ? '
                     'ORDER BY COALESCE(last_used_at, "1970-01-01 00:00:00") ASC, use_count ASC LIMIT 2')
                self.cursor.execute(q, ('disabled',))
            rows = self.cursor.fetchall() or []
            if not rows:
                return None
            # Choose a cookie not equal to prev if possible
            if prev_cookie_id is None:
                chosen = rows[0]
            else:
                chosen = None
                for r in rows:
                    if r[0] != prev_cookie_id:
                        chosen = r
                        break
                if chosen is None:
                    chosen = rows[0]
            return {'id': chosen[0], 'name': chosen[1], 'cookie_text': chosen[2]}
        except Exception as e:
            print(f"Failed to get next cookie: {e}")
            return None

    # --- Failed requests queue operations ---
    def add_failed_request(self, user_id: int, url: str, platform: str, error_message: str, original_message_id: int) -> int:
        """Add a failed request to the queue"""
        try:
            now = _dt.now().isoformat(timespec='seconds')
            if self.db_type == 'mysql':
                q = ('INSERT INTO failed_requests (user_id, url, platform, error_message, original_message_id, status, created_at, retry_count, admin_notified) '
                     'VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 0)')
                self.cursor.execute(q, (user_id, url, platform, error_message, original_message_id, 'pending', now))
            else:
                q = ('INSERT INTO failed_requests (user_id, url, platform, error_message, original_message_id, status, created_at, retry_count, admin_notified) '
                     'VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0)')
                self.cursor.execute(q, (user_id, url, platform, error_message, original_message_id, 'pending', now))
            self.mydb.commit()
            return self.cursor.lastrowid or 0
        except Exception as e:
            print(f"Failed to add failed request: {e}")
            return 0

    def get_pending_failed_requests(self, limit: int = 100) -> list[dict]:
        """Get all pending failed requests"""
        try:
            if self.db_type == 'mysql':
                q = ('SELECT id, user_id, url, platform, error_message, original_message_id, status, created_at, processed_at, retry_count, admin_notified '
                     'FROM failed_requests WHERE status = %s ORDER BY created_at ASC LIMIT %s')
                self.cursor.execute(q, ('pending', limit))
            else:
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
        except Exception as e:
            print(f"Failed to get pending failed requests: {e}")
            return []

    def get_failed_request_by_id(self, request_id: int) -> dict:
        """Get a specific failed request by ID"""
        try:
            if self.db_type == 'mysql':
                q = ('SELECT id, user_id, url, platform, error_message, original_message_id, status, created_at, processed_at, retry_count, admin_notified '
                     'FROM failed_requests WHERE id = %s')
                self.cursor.execute(q, (request_id,))
            else:
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
        except Exception as e:
            print(f"Failed to get failed request by id: {e}")
            return {}

    def mark_failed_request_as_processed(self, request_id: int) -> bool:
        """Mark a failed request as successfully processed"""
        try:
            now = _dt.now().isoformat(timespec='seconds')
            if self.db_type == 'mysql':
                q = 'UPDATE failed_requests SET status = %s, processed_at = %s WHERE id = %s'
                self.cursor.execute(q, ('completed', now, request_id))
            else:
                q = 'UPDATE failed_requests SET status = ?, processed_at = ? WHERE id = ?'
                self.cursor.execute(q, ('completed', now, request_id))
            self.mydb.commit()
            return True
        except Exception as e:
            print(f"Failed to mark request as processed: {e}")
            return False

    def mark_failed_request_as_failed(self, request_id: int, error: str) -> bool:
        """Mark a failed request as permanently failed"""
        try:
            now = _dt.now().isoformat(timespec='seconds')
            if self.db_type == 'mysql':
                q = 'UPDATE failed_requests SET status = %s, processed_at = %s, error_message = %s WHERE id = %s'
                self.cursor.execute(q, ('failed', now, error, request_id))
            else:
                q = 'UPDATE failed_requests SET status = ?, processed_at = ?, error_message = ? WHERE id = ?'
                self.cursor.execute(q, ('failed', now, error, request_id))
            self.mydb.commit()
            return True
        except Exception as e:
            print(f"Failed to mark request as failed: {e}")
            return False

    def increment_failed_request_retry(self, request_id: int) -> bool:
        """Increment retry count for a failed request"""
        try:
            if self.db_type == 'mysql':
                q = 'UPDATE failed_requests SET retry_count = retry_count + 1 WHERE id = %s'
                self.cursor.execute(q, (request_id,))
            else:
                q = 'UPDATE failed_requests SET retry_count = retry_count + 1 WHERE id = ?'
                self.cursor.execute(q, (request_id,))
            self.mydb.commit()
            return True
        except Exception as e:
            print(f"Failed to increment retry count: {e}")
            return False

    def mark_failed_request_admin_notified(self, request_id: int) -> bool:
        """Mark that admin has been notified about this request"""
        try:
            if self.db_type == 'mysql':
                q = 'UPDATE failed_requests SET admin_notified = 1 WHERE id = %s'
                self.cursor.execute(q, (request_id,))
            else:
                q = 'UPDATE failed_requests SET admin_notified = 1 WHERE id = ?'
                self.cursor.execute(q, (request_id,))
            self.mydb.commit()
            return True
        except Exception as e:
            print(f"Failed to mark admin notified: {e}")
            return False

    def cleanup_old_failed_requests(self, days: int = 7) -> int:
        """Delete failed requests older than specified days"""
        try:
            cutoff_date = (_dt.now() - _td(days=days)).isoformat(timespec='seconds')
            if self.db_type == 'mysql':
                q = 'DELETE FROM failed_requests WHERE created_at < %s AND status IN (%s, %s)'
                self.cursor.execute(q, (cutoff_date, 'completed', 'failed'))
            else:
                q = 'DELETE FROM failed_requests WHERE created_at < ? AND status IN (?, ?)'
                self.cursor.execute(q, (cutoff_date, 'completed', 'failed'))
            deleted_count = self.cursor.rowcount
            self.mydb.commit()
            return deleted_count
        except Exception as e:
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
                if self.db_type == 'mysql':
                    self.cursor.execute('SELECT COUNT(*) FROM failed_requests WHERE status = %s', (status,))
                else:
                    self.cursor.execute('SELECT COUNT(*) FROM failed_requests WHERE status = ?', (status,))
                row = self.cursor.fetchone()
                stats[status] = int(row[0] or 0) if row else 0
        except Exception as e:
            print(f"Failed to get failed requests stats: {e}")
        return stats

    def get_failed_requests_by_platform(self) -> dict:
        """Get statistics grouped by platform"""
        platform_stats = {}
        try:
            if self.db_type == 'mysql':
                q = 'SELECT platform, status, COUNT(*) FROM failed_requests GROUP BY platform, status'
            else:
                q = 'SELECT platform, status, COUNT(*) FROM failed_requests GROUP BY platform, status'
            self.cursor.execute(q)
            rows = self.cursor.fetchall() or []
            
            for row in rows:
                platform = row[0] or 'Unknown'
                status = row[1]
                count = int(row[2] or 0)
                
                if platform not in platform_stats:
                    platform_stats[platform] = {
                        'total': 0,
                        'pending': 0,
                        'processing': 0,
                        'completed': 0,
                        'failed': 0
                    }
                
                platform_stats[platform][status] = count
                platform_stats[platform]['total'] += count
        except Exception as e:
            print(f"Failed to get platform stats: {e}")
        return platform_stats

    def get_average_processing_time(self) -> float:
        """Get average processing time for completed requests in seconds"""
        try:
            if self.db_type == 'mysql':
                q = '''
                    SELECT AVG(TIMESTAMPDIFF(SECOND, created_at, processed_at))
                    FROM failed_requests
                    WHERE status = %s AND processed_at IS NOT NULL
                '''
                self.cursor.execute(q, ('completed',))
            else:
                q = '''
                    SELECT AVG(
                        (julianday(processed_at) - julianday(created_at)) * 86400
                    )
                    FROM failed_requests
                    WHERE status = ? AND processed_at IS NOT NULL
                '''
                self.cursor.execute(q, ('completed',))
            
            row = self.cursor.fetchone()
            if row and row[0] is not None:
                return float(row[0])
            return 0.0
        except Exception as e:
            print(f"Failed to get average processing time: {e}")
            return 0.0


    # ==================== Statistics Methods ====================
    
    def get_total_users(self) -> int:
        """دریافت تعداد کل کاربران"""
        try:
            self.cursor.execute('SELECT COUNT(*) FROM users')
            row = self.cursor.fetchone()
            return int(row[0] or 0) if row else 0
        except Exception as e:
            print(f"Error getting total users: {e}")
            return 0
    
    def get_users_since(self, since_date: _dt) -> int:
        """دریافت تعداد کاربران جدید از تاریخ مشخص"""
        try:
            date_str = since_date.isoformat()
            if self.db_type == 'mysql':
                self.cursor.execute('SELECT COUNT(*) FROM users WHERE joined_at >= %s', (date_str,))
            else:
                self.cursor.execute('SELECT COUNT(*) FROM users WHERE joined_at >= ?', (date_str,))
            row = self.cursor.fetchone()
            return int(row[0] or 0) if row else 0
        except Exception as e:
            print(f"Error getting users since {since_date}: {e}")
            return 0
    
    def get_active_users_since(self, since_date: _dt) -> int:
        """دریافت تعداد کاربران فعال از تاریخ مشخص"""
        try:
            date_str = since_date.isoformat()
            if self.db_type == 'mysql':
                self.cursor.execute('SELECT COUNT(*) FROM users WHERE last_download >= %s', (date_str,))
            else:
                self.cursor.execute('SELECT COUNT(*) FROM users WHERE last_download >= ?', (date_str,))
            row = self.cursor.fetchone()
            return int(row[0] or 0) if row else 0
        except Exception as e:
            print(f"Error getting active users since {since_date}: {e}")
            return 0
    
    def get_total_requests(self) -> int:
        """دریافت مجموع کل درخواست‌ها"""
        try:
            self.cursor.execute('SELECT SUM(total_requests) FROM users')
            row = self.cursor.fetchone()
            return int(row[0] or 0) if row and row[0] is not None else 0
        except Exception as e:
            print(f"Error getting total requests: {e}")
            return 0
    
    def get_requests_by_platform(self, platform: str) -> int:
        """
        دریافت تعداد درخواست‌ها به تفکیک پلتفرم از جدول requests
        """
        try:
            if self.db_type == 'mysql':
                self.cursor.execute('SELECT COUNT(*) FROM requests WHERE platform = %s', (platform,))
            else:
                self.cursor.execute('SELECT COUNT(*) FROM requests WHERE platform = ?', (platform,))
            row = self.cursor.fetchone()
            return int(row[0] or 0) if row else 0
        except Exception as e:
            print(f"Error getting requests by platform {platform}: {e}")
            return 0
    
    def get_successful_requests(self) -> int:
        """دریافت تعداد درخواست‌های موفق از جدول requests"""
        try:
            if self.db_type == 'mysql':
                self.cursor.execute("SELECT COUNT(*) FROM requests WHERE status = %s", ('success',))
            else:
                self.cursor.execute("SELECT COUNT(*) FROM requests WHERE status = ?", ('success',))
            row = self.cursor.fetchone()
            return int(row[0] or 0) if row else 0
        except Exception as e:
            print(f"Error getting successful requests: {e}")
            return 0
    
    def get_failed_requests(self) -> int:
        """دریافت تعداد درخواست‌های ناموفق از جدول requests"""
        try:
            if self.db_type == 'mysql':
                self.cursor.execute("SELECT COUNT(*) FROM requests WHERE status = %s", ('failed',))
            else:
                self.cursor.execute("SELECT COUNT(*) FROM requests WHERE status = ?", ('failed',))
            row = self.cursor.fetchone()
            return int(row[0] or 0) if row else 0
        except Exception as e:
            print(f"Error getting failed requests: {e}")
            return 0
    
    def get_avg_processing_time(self) -> float:
        """دریافت میانگین زمان پردازش از جدول requests"""
        try:
            query = """
                SELECT AVG(processing_time) 
                FROM requests 
                WHERE status = ? AND processing_time IS NOT NULL
            """ if self.db_type == 'sqlite' else """
                SELECT AVG(processing_time) 
                FROM requests 
                WHERE status = %s AND processing_time IS NOT NULL
            """
            
            if self.db_type == 'mysql':
                self.cursor.execute(query, ('success',))
            else:
                self.cursor.execute(query, ('success',))
            
            row = self.cursor.fetchone()
            return float(row[0] or 0) if row and row[0] is not None else 0.0
        except Exception as e:
            print(f"Error getting avg processing time: {e}")
            return 0.0


    def log_request(self, user_id: int, platform: str, url: str, status: str = 'pending'):
        """
        ثبت یک درخواست جدید در جدول requests
        
        Args:
            user_id: شناسه کاربر
            platform: نام پلتفرم (youtube, aparat, adult, universal)
            url: آدرس درخواست
            status: وضعیت (pending, success, failed)
        
        Returns:
            int: شناسه درخواست ثبت شده
        """
        try:
            created_at = _dt.now().isoformat()
            
            if self.db_type == 'mysql':
                self.cursor.execute(
                    'INSERT INTO requests (user_id, platform, url, status, created_at) VALUES (%s, %s, %s, %s, %s)',
                    (user_id, platform, url, status, created_at)
                )
                self.mydb.commit()
                return self.cursor.lastrowid
            else:
                self.cursor.execute(
                    'INSERT INTO requests (user_id, platform, url, status, created_at) VALUES (?, ?, ?, ?, ?)',
                    (user_id, platform, url, status, created_at)
                )
                self.mydb.commit()
                return self.cursor.lastrowid
        except Exception as e:
            print(f"Error logging request: {e}")
            return 0
    
    def update_request_status(self, request_id: int, status: str, processing_time: float = None, error_message: str = None):
        """
        به‌روزرسانی وضعیت یک درخواست
        
        Args:
            request_id: شناسه درخواست
            status: وضعیت جدید (success, failed)
            processing_time: زمان پردازش (ثانیه)
            error_message: پیام خطا (در صورت failed)
        """
        try:
            completed_at = _dt.now().isoformat()
            
            if self.db_type == 'mysql':
                self.cursor.execute(
                    'UPDATE requests SET status = %s, completed_at = %s, processing_time = %s, error_message = %s WHERE id = %s',
                    (status, completed_at, processing_time, error_message, request_id)
                )
            else:
                self.cursor.execute(
                    'UPDATE requests SET status = ?, completed_at = ?, processing_time = ?, error_message = ? WHERE id = ?',
                    (status, completed_at, processing_time, error_message, request_id)
                )
            self.mydb.commit()
        except Exception as e:
            print(f"Error updating request status: {e}")
