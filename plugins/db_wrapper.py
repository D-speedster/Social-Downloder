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
