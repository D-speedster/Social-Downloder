import sqlite3
import os


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
                    last_download TEXT NOT NULL
                )"""
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

    def close(self):
        """Close database connection"""
        if self.mydb:
            self.mydb.close()