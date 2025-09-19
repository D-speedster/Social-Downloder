#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Server Debug Script for Telegram Bot
This script helps diagnose issues on Linux servers
"""

import os
import sys
import subprocess
import time
import logging
import platform
import sqlite3
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug_server.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def check_system_info():
    """Check system information"""
    logger.info("=== SYSTEM INFORMATION ===")
    logger.info(f"Platform: {platform.platform()}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Python executable: {sys.executable}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"User: {os.getenv('USER', 'unknown')}")
    logger.info(f"Home: {os.getenv('HOME', 'unknown')}")
    
    # Check if we're in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        logger.info("Running in virtual environment")
        logger.info(f"Virtual env path: {sys.prefix}")
    else:
        logger.info("Not running in virtual environment")

def check_file_permissions():
    """Check file permissions"""
    logger.info("=== FILE PERMISSIONS ===")
    
    files_to_check = [
        'bot.py',
        'config.py',
        'plugins/',
        'plugins/bot_database.db'
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            stat_info = os.stat(file_path)
            permissions = oct(stat_info.st_mode)[-3:]
            logger.info(f"{file_path}: permissions {permissions}, owner {stat_info.st_uid}")
        else:
            logger.warning(f"{file_path}: does not exist")

def check_dependencies():
    """Check Python dependencies"""
    logger.info("=== DEPENDENCIES CHECK ===")
    
    required_packages = [
        'pyrogram',
        'sqlite3',
        'asyncio',
        'logging'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"✓ {package}: available")
        except ImportError as e:
            logger.error(f"✗ {package}: missing - {e}")
    
    # Check TgCrypto
    try:
        import TgCrypto
        logger.info(f"✓ TgCrypto: available (version: {TgCrypto.__version__})")
    except ImportError:
        logger.warning("⚠ TgCrypto: not available (performance may be reduced)")

def check_database():
    """Check database status"""
    logger.info("=== DATABASE CHECK ===")
    
    db_path = "plugins/bot_database.db"
    
    if not os.path.exists("plugins"):
        logger.error("plugins directory does not exist")
        return
    
    if os.path.exists(db_path):
        try:
            # Check if database is accessible
            conn = sqlite3.connect(db_path, timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            logger.info(f"Database exists with {len(tables)} tables: {[t[0] for t in tables]}")
            conn.close()
            
            # Check file size
            size = os.path.getsize(db_path)
            logger.info(f"Database size: {size} bytes")
            
        except sqlite3.OperationalError as e:
            logger.error(f"Database error: {e}")
        except Exception as e:
            logger.error(f"Unexpected database error: {e}")
    else:
        logger.info("Database does not exist (will be created on first run)")
    
    # Check for lock files
    lock_files = [
        "plugins/bot_database.db-shm",
        "plugins/bot_database.db-wal"
    ]
    
    for lock_file in lock_files:
        if os.path.exists(lock_file):
            logger.warning(f"Lock file exists: {lock_file}")
        else:
            logger.info(f"No lock file: {lock_file}")

def check_config():
    """Check configuration"""
    logger.info("=== CONFIGURATION CHECK ===")
    
    try:
        import config
        
        # Check API credentials (without logging sensitive data)
        if hasattr(config, 'API_ID'):
            api_id = getattr(config, 'API_ID', None)
            if api_id and str(api_id).strip() and str(api_id) != 'None':
                logger.info(f"API_ID: configured (length: {len(str(config.API_ID))})")
            else:
                logger.error("API_ID: not configured")
        else:
            logger.error("API_ID: not configured")
        
        if hasattr(config, 'API_HASH'):
            logger.info(f"API_HASH: configured (length: {len(config.API_HASH)})")
        else:
            logger.error("API_HASH: not configured")
        
        if hasattr(config, 'BOT_TOKEN'):
            logger.info(f"BOT_TOKEN: configured (length: {len(config.BOT_TOKEN)})")
        else:
            logger.error("BOT_TOKEN: not configured")
            
    except ImportError as e:
        logger.error(f"Cannot import config: {e}")
    except Exception as e:
        logger.error(f"Config error: {e}")

def test_bot_startup():
    """Test bot startup with detailed logging"""
    logger.info("=== BOT STARTUP TEST ===")
    
    try:
        # Start bot process with detailed output capture
        process = subprocess.Popen(
            [sys.executable, 'bot.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )
        
        logger.info("Bot process started, waiting for output...")
        
        # Wait for a few seconds to capture initial output
        time.sleep(5)
        
        # Check if process is still running
        if process.poll() is None:
            logger.info("Bot is still running after 5 seconds")
            
            # Try to get some output
            try:
                stdout, stderr = process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                logger.info("Bot is running normally (timeout waiting for output)")
                process.terminate()
                stdout, stderr = process.communicate()
        else:
            # Process exited
            stdout, stderr = process.communicate()
            exit_code = process.returncode
            
            logger.error(f"Bot exited with code: {exit_code}")
            
            if stdout:
                logger.info("STDOUT:")
                for line in stdout.split('\n'):
                    if line.strip():
                        logger.info(f"  {line}")
            
            if stderr:
                logger.error("STDERR:")
                for line in stderr.split('\n'):
                    if line.strip():
                        logger.error(f"  {line}")
        
    except Exception as e:
        logger.error(f"Error testing bot startup: {e}")

def check_network():
    """Check network connectivity"""
    logger.info("=== NETWORK CHECK ===")
    
    # Test DNS resolution
    try:
        import socket
        socket.gethostbyname('api.telegram.org')
        logger.info("✓ DNS resolution: working")
    except Exception as e:
        logger.error(f"✗ DNS resolution failed: {e}")
    
    # Test HTTP connectivity (if requests is available)
    try:
        import requests
        response = requests.get('https://api.telegram.org', timeout=10)
        logger.info(f"✓ HTTP connectivity: working (status: {response.status_code})")
    except ImportError:
        logger.info("requests module not available, skipping HTTP test")
    except Exception as e:
        logger.error(f"✗ HTTP connectivity failed: {e}")

def main():
    """Main diagnostic function"""
    logger.info("Starting server diagnostic...")
    logger.info("=" * 50)
    
    try:
        check_system_info()
        check_file_permissions()
        check_dependencies()
        check_config()
        check_database()
        check_network()
        test_bot_startup()
        
    except Exception as e:
        logger.error(f"Diagnostic failed: {e}")
    
    logger.info("=" * 50)
    logger.info("Diagnostic completed. Check debug_server.log for details.")

if __name__ == "__main__":
    main()