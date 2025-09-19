#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to validate bot token and basic connectivity
"""

import asyncio
import sys
import os
from dotenv import load_dotenv
from pyrogram import Client
from pyrogram.errors import AuthKeyUnregistered, UserDeactivated, AuthKeyInvalid

# Load environment variables
load_dotenv()

def test_token():
    """Test if bot token is valid"""
    print("🔍 Testing bot token...")
    
    # Get credentials
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    API_ID = os.environ.get("API_ID")
    API_HASH = os.environ.get("API_HASH")
    
    # Validate environment variables
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not found in environment")
        return False
        
    if not API_ID:
        print("❌ API_ID not found in environment")
        return False
        
    if not API_HASH:
        print("❌ API_HASH not found in environment")
        return False
    
    try:
        API_ID = int(API_ID)
    except ValueError:
        print("❌ API_ID must be a valid integer")
        return False
    
    print(f"✅ Environment variables loaded")
    print(f"📋 API_ID: {API_ID}")
    print(f"📋 API_HASH: {API_HASH[:8]}...")
    print(f"📋 BOT_TOKEN: {BOT_TOKEN[:10]}...")
    
    return BOT_TOKEN, API_ID, API_HASH

async def test_connection(bot_token, api_id, api_hash):
    """Test bot connection to Telegram"""
    print("\n🔗 Testing connection to Telegram...")
    
    try:
        # Create client with minimal configuration
        client = Client(
            "test_session",
            bot_token=bot_token,
            api_id=api_id,
            api_hash=api_hash,
            in_memory=True  # Don't create session files
        )
        
        print("🔸 Starting client...")
        await client.start()
        
        print("🔸 Getting bot info...")
        me = await client.get_me()
        
        print(f"✅ Bot connected successfully!")
        print(f"📋 Bot Name: {me.first_name}")
        print(f"📋 Bot Username: @{me.username}")
        print(f"📋 Bot ID: {me.id}")
        
        await client.stop()
        return True
        
    except AuthKeyUnregistered:
        print("❌ Bot token is invalid or expired")
        return False
    except AuthKeyInvalid:
        print("❌ Invalid authentication key")
        return False
    except UserDeactivated:
        print("❌ Bot has been deactivated")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🤖 Bot Token Validation Test")
    print("=" * 40)
    
    # Test token
    result = test_token()
    if not result:
        print("\n❌ Token validation failed")
        return False
    
    bot_token, api_id, api_hash = result
    
    # Test connection
    success = await test_connection(bot_token, api_id, api_hash)
    
    if success:
        print("\n✅ All tests passed! Bot token is valid and working.")
        return True
    else:
        print("\n❌ Connection test failed. Please check your bot token.")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)