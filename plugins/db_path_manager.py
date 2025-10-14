import os
import platform
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DatabasePathManager:
    """Manages database paths based on operating system"""
    
    def __init__(self):
        self.os_type = platform.system().lower()
        
    def get_database_base_path(self):
        """Get the base path for database storage based on OS"""
        if self.os_type == 'windows':
            base_path = os.environ.get('DB_BASE_PATH_WINDOWS', r'C:\Users\speedster\Documents\Database')
        elif self.os_type == 'linux':
            base_path = os.environ.get('DB_BASE_PATH_LINUX', '/var/lib/social-db/')
        else:
            # Default for other systems (macOS, etc.)
            base_path = os.environ.get('DB_BASE_PATH_DEFAULT', './data/database')
        
        return base_path
    
    def get_sqlite_db_path(self):
        """Get full path for SQLite database file"""
        base_path = self.get_database_base_path()
        return os.path.join(base_path, 'bot_database.db')
    
    def get_json_db_path(self):
        """Get full path for JSON database file"""
        base_path = self.get_database_base_path()
        return os.path.join(base_path, 'database.json')
    
    def ensure_database_directory(self):
        """Create database directory if it doesn't exist"""
        base_path = self.get_database_base_path()
        
        try:
            if not os.path.exists(base_path):
                os.makedirs(base_path, mode=0o750, exist_ok=True)
                print(f"Created database directory: {base_path}")
            
            # Ensure proper permissions
            if self.os_type != 'windows':
                os.chmod(base_path, 0o750)
                
            return True
        except Exception as e:
            print(f"Error creating database directory {base_path}: {e}")
            return False
    
    def migrate_existing_database(self):
        """Migrate existing database files to new location"""
        old_sqlite_path = os.path.join(os.path.dirname(__file__), 'bot_database.db')
        old_json_path = os.path.join(os.path.dirname(__file__), 'database.json')
        
        new_sqlite_path = self.get_sqlite_db_path()
        new_json_path = self.get_json_db_path()
        
        # Ensure new directory exists
        if not self.ensure_database_directory():
            return False
        
        try:
            # Migrate SQLite database
            if os.path.exists(old_sqlite_path) and not os.path.exists(new_sqlite_path):
                import shutil
                shutil.copy2(old_sqlite_path, new_sqlite_path)
                print(f"Migrated SQLite database from {old_sqlite_path} to {new_sqlite_path}")
            
            # Migrate JSON database
            if os.path.exists(old_json_path) and not os.path.exists(new_json_path):
                import shutil
                shutil.copy2(old_json_path, new_json_path)
                print(f"Migrated JSON database from {old_json_path} to {new_json_path}")
            
            return True
        except Exception as e:
            print(f"Error migrating database files: {e}")
            return False
    
    def get_database_info(self):
        """Get information about database configuration"""
        return {
            'os_type': self.os_type,
            'base_path': self.get_database_base_path(),
            'sqlite_path': self.get_sqlite_db_path(),
            'json_path': self.get_json_db_path(),
            'directory_exists': os.path.exists(self.get_database_base_path())
        }

# Global instance
db_path_manager = DatabasePathManager()