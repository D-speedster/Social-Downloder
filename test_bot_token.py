#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Token Test Script
This script tests if the bot token is valid and can connect to Telegram
"""

import asyncio
import logging
import sys
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_bot_token():
    """Test bot token validity"""
    try:
        # Import config
        import config
        
        logger.info("Testing bot token...")
        logger.info(f"API_ID: {config.API_ID}")
        logger.info(f"API_HASH length: {len(config.API_HASH)}")
        logger.info(f"BOT_TOKEN length: {len(config.BOT_TOKEN)}")
        
        # Import pyrogram
        from pyrogram import Client
        
        # Create client
        app = Client(
            "test_session",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN
        )
        
        logger.info("Starting client...")
        
        async with app:
            # Get bot info
            me = await app.get_me()
            logger.info(f"✓ Bot connected successfully!")
            logger.info(f"Bot username: @{me.username}")
            logger.info(f"Bot name: {me.first_name}")
            logger.info(f"Bot ID: {me.id}")
            
            # Test sending a message to self (if possible)
            try:
                await app.send_message("me", "Test message from bot")
                logger.info("✓ Bot can send messages")
            except Exception as e:
                logger.warning(f"Cannot send test message: {e}")
            
            return True
            
    except ImportError as e:
        logger.error(f"✗ Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Bot token test failed: {e}")
        return False

async def test_database_connection():
    """Test database connection"""
    try:
        import sqlite3
        
        logger.info("Testing database connection...")
        
        # Ensure plugins directory exists
        os.makedirs("plugins", exist_ok=True)
        
        # Test database connection
        db_path = "plugins/test_database.db"
        
        conn = sqlite3.connect(db_path, timeout=10)
        cursor = conn.cursor()
        
        # Create a test table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                test_data TEXT
            )
        """)
        
        # Insert test data
        cursor.execute("INSERT INTO test_table (test_data) VALUES (?)", ("test",))
        conn.commit()
        
        # Read test data
        cursor.execute("SELECT * FROM test_table")
        results = cursor.fetchall()
        
        conn.close()
        
        # Clean up test database
        os.remove(db_path)
        
        logger.info(f"✓ Database connection successful (test records: {len(results)})")
        return True
        
    except Exception as e:
        logger.error(f"✗ Database test failed: {e}")
        return False

async def main():
    """Main test function"""
    logger.info("Starting bot token and database tests...")
    logger.info("=" * 50)
    
    # Test bot token
    token_ok = await test_bot_token()
    
    # Test database
    db_ok = await test_database_connection()
    
    logger.info("=" * 50)
    
    if token_ok and db_ok:
        logger.info("✓ All tests passed! Bot should work correctly.")
        return 0
    else:
        logger.error("✗ Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)