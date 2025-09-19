#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick test script to verify API_ID configuration fix
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("🔍 Quick Configuration Test")
print("=" * 40)

try:
    # Test environment variables
    print("📋 Environment Variables:")
    api_id_env = os.getenv('API_ID')
    api_hash_env = os.getenv('API_HASH')
    bot_token_env = os.getenv('BOT_TOKEN')
    
    print(f"   API_ID from .env: {'✓' if api_id_env else '✗'} ({api_id_env if api_id_env else 'Not found'})")
    print(f"   API_HASH from .env: {'✓' if api_hash_env else '✗'} ({'*' * len(api_hash_env) if api_hash_env else 'Not found'})")
    print(f"   BOT_TOKEN from .env: {'✓' if bot_token_env else '✗'} ({'*' * 10 if bot_token_env else 'Not found'})")
    print()
    
    # Test config import
    print("📋 Config Module Test:")
    try:
        import config
        print(f"   config.API_ID: {'✓' if hasattr(config, 'API_ID') else '✗'} ({getattr(config, 'API_ID', 'Not found')})")
        print(f"   config.API_HASH: {'✓' if hasattr(config, 'API_HASH') else '✗'} ({'*' * 10 if hasattr(config, 'API_HASH') else 'Not found'})")
        print(f"   config.BOT_TOKEN: {'✓' if hasattr(config, 'BOT_TOKEN') else '✗'} ({'*' * 10 if hasattr(config, 'BOT_TOKEN') else 'Not found'})")
        
        # Check if all required values are present and valid
        if hasattr(config, 'API_ID') and hasattr(config, 'API_HASH') and hasattr(config, 'BOT_TOKEN'):
            api_id = getattr(config, 'API_ID')
            api_hash = getattr(config, 'API_HASH')
            bot_token = getattr(config, 'BOT_TOKEN')
            
            if api_id and str(api_id).strip() and str(api_id) != 'None':
                if api_hash and str(api_hash).strip():
                    if bot_token and str(bot_token).strip():
                        print("\n✅ All configuration values are present and valid!")
                        print("🚀 Bot should start successfully now.")
                    else:
                        print("\n❌ BOT_TOKEN is empty or invalid")
                else:
                    print("\n❌ API_HASH is empty or invalid")
            else:
                print("\n❌ API_ID is empty or invalid")
        else:
            print("\n❌ Missing configuration attributes")
            
    except ImportError as e:
        print(f"   ❌ Failed to import config: {e}")
    except Exception as e:
        print(f"   ❌ Config error: {e}")
    
    print()
    print("📋 Quick Bot Test:")
    try:
        # Try to create a Pyrogram client (without starting it)
        from pyrogram import Client
        import config
        
        # Just test client creation
        client = Client(
            "test_session",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN,
            in_memory=True
        )
        print("   ✅ Pyrogram client created successfully")
        print("   🔧 Configuration is valid for bot startup")
        
    except Exception as e:
        print(f"   ❌ Client creation failed: {e}")
        
except Exception as e:
    print(f"❌ Test failed: {e}")

print("\n" + "=" * 40)
print("Test completed. If all checks pass, run: python bot.py")