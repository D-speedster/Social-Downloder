# Database Migration to External Paths

## Overview
This document describes the migration of database files from the project directory to external system-specific locations for better organization and security.

## Changes Made

### 1. Database Path Manager (`plugins/db_path_manager.py`)
- **New Component**: Created a centralized database path management system
- **Features**:
  - OS-specific path detection (Windows, macOS, Linux)
  - Automatic directory creation
  - Database migration from old to new locations
  - Centralized path configuration

### 2. Environment Configuration (`.env`)
- **Added**: `DATABASE_BASE_PATH` configuration
- **Purpose**: Allows customization of database storage location
- **Default Paths**:
  - **Windows**: `C:\Users\{username}\Documents\Database`
  - **macOS**: `~/Documents/Database`
  - **Linux**: `~/.local/share/DownloaderYT/Database`

### 3. Updated Files
The following files were updated to use the new external database paths:

#### Core Files:
- `plugins/constant.py` - Configuration constants
- `plugins/sqlite_db_wrapper.py` - SQLite database wrapper
- `plugins/media_utils.py` - Media utilities

#### Admin and Management:
- `plugins/admin.py` - Admin panel functionality (3 locations updated)

#### Downloaders:
- `plugins/instagram.py` - Instagram downloader (2 locations updated)
- `plugins/universal_downloader.py` - Universal downloader

## Migration Process

### Automatic Migration
When the application starts, it automatically:
1. **Detects** existing database files in the old location (`plugins/`)
2. **Creates** the new external database directory
3. **Migrates** existing files to the new location
4. **Preserves** all existing data and settings

### Migration Details
- **SQLite Database**: `bot_database.db` → External path
- **JSON Database**: `database.json` → External path
- **Backup Safety**: Original files are copied, not moved

## Benefits

### 1. Better Organization
- Database files are stored in standard system locations
- Separation of code and data
- Easier backup and maintenance

### 2. Security
- Database files are outside the project directory
- Reduced risk of accidental commits
- Better access control

### 3. Portability
- Project directory can be moved without losing data
- Easier deployment and updates
- Cross-platform compatibility

### 4. User Experience
- Standard system paths familiar to users
- Automatic directory creation
- Seamless migration process

## File Locations

### Before Migration
```
DownloaderYT-V1/
├── plugins/
│   ├── bot_database.db     # SQLite database
│   ├── database.json       # JSON configuration
│   └── ...
```

### After Migration
```
# Windows
C:\Users\{username}\Documents\Database\
├── bot_database.db
└── database.json

# macOS
~/Documents/Database/
├── bot_database.db
└── database.json

# Linux
~/.local/share/DownloaderYT/Database/
├── bot_database.db
└── database.json
```

## Configuration

### Custom Database Path
You can customize the database location by setting the `DATABASE_BASE_PATH` in your `.env` file:

```env
DATABASE_BASE_PATH=/custom/path/to/database
```

### Environment Variables
- `DATABASE_BASE_PATH`: Custom base path for database storage (optional)

## Testing

The migration was thoroughly tested with:
- ✅ Database Path Manager functionality
- ✅ SQLite database connection
- ✅ JSON database operations
- ✅ Constants import
- ✅ Automatic migration process

## Troubleshooting

### Common Issues

1. **Permission Errors**
   - Ensure the user has write permissions to the database directory
   - Check if antivirus software is blocking file operations

2. **Migration Failures**
   - Verify source files exist in the `plugins/` directory
   - Check available disk space in the target location

3. **Path Issues**
   - Ensure `DATABASE_BASE_PATH` (if set) is a valid directory path
   - Check for special characters in the path

### Recovery
If migration fails, the original database files remain in the `plugins/` directory and the application will continue to work with the old paths until the issue is resolved.

## Technical Implementation

### Key Components

1. **`db_path_manager.py`**: Central path management
2. **Environment Detection**: Automatic OS-specific path selection
3. **Migration Logic**: Safe file copying with error handling
4. **Integration**: Updated all database access points

### Code Changes Summary
- **Files Modified**: 7 plugin files
- **Import Statements**: Added `db_path_manager` imports
- **Path Resolution**: Replaced hardcoded paths with dynamic path resolution
- **Error Handling**: Added robust error handling for path operations

## Maintenance

### Regular Tasks
- Monitor database directory size
- Backup database files regularly
- Check for permission issues

### Updates
- The migration is a one-time process
- Future updates will automatically use the new paths
- No manual intervention required for normal operation

---

**Migration Date**: January 2024  
**Status**: ✅ Completed Successfully  
**Tested**: ✅ All functionality verified