#!/usr/bin/env python3
"""
پیکربندی نهایی پروکسی HTTP 10808 برای بات
Final HTTP proxy 10808 configuration for the bot
"""

import os
import asyncio
import sys

def configure_environment():
    """تنظیم متغیرهای محیطی برای پروکسی HTTP"""
    
    print("🔧 Configuring HTTP Proxy 10808 Environment")
    print("=" * 50)
    
    # تنظیم متغیرهای محیطی
    os.environ['YOUTUBE_SINGLE_PROXY'] = 'http://127.0.0.1:10808'
    os.environ['YOUTUBE_ENABLE_SOCKS'] = '0'  # غیرفعال کردن SOCKS5
    
    print("✅ Environment variables configured:")
    print(f"   YOUTUBE_SINGLE_PROXY = {os.environ.get('YOUTUBE_SINGLE_PROXY')}")
    print(f"   YOUTUBE_ENABLE_SOCKS = {os.environ.get('YOUTUBE_ENABLE_SOCKS')}")
    
    return True

def create_env_file():
    """ایجاد فایل .env برای ذخیره تنظیمات"""
    
    env_content = """# YouTube Bot Proxy Configuration
# پیکربندی پروکسی بات یوتیوب

# HTTP Proxy Configuration
YOUTUBE_SINGLE_PROXY=http://127.0.0.1:10808

# Disable SOCKS5 Proxy
YOUTUBE_ENABLE_SOCKS=0

# Additional Settings
YOUTUBE_PROXY_TIMEOUT=10
YOUTUBE_MAX_RETRIES=3
"""
    
    try:
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print("✅ .env file created successfully")
        print("📁 Location: .env")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create .env file: {str(e)}")
        return False

def update_config_py():
    """بروزرسانی فایل config.py در صورت وجود"""
    
    config_file = 'config.py'
    
    if not os.path.exists(config_file):
        print("ℹ️  config.py not found, skipping update")
        return True
    
    try:
        # خواندن فایل موجود
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # اضافه کردن تنظیمات پروکسی
        proxy_config = """
# HTTP Proxy Configuration - Added by configure_http_proxy_10808.py
YOUTUBE_SINGLE_PROXY = "http://127.0.0.1:10808"
YOUTUBE_ENABLE_SOCKS = False
"""
        
        # بررسی اینکه آیا تنظیمات قبلاً اضافه شده یا نه
        if 'YOUTUBE_SINGLE_PROXY' not in content:
            content += proxy_config
            
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ config.py updated with proxy settings")
        else:
            print("ℹ️  config.py already contains proxy settings")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to update config.py: {str(e)}")
        return False

async def test_configuration():
    """تست تنظیمات نهایی"""
    
    print("\n🧪 Testing Final Configuration")
    print("=" * 40)
    
    try:
        from plugins.youtube_proxy_rotator import extract_with_rotation
        
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        result = await extract_with_rotation(test_url, {
            'quiet': True,
            'no_warnings': True,
        })
        
        if result and isinstance(result, dict):
            print("✅ Configuration test PASSED")
            print(f"📹 Successfully extracted: {result.get('title', 'N/A')}")
            return True
        else:
            print("❌ Configuration test FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Configuration test ERROR: {str(e)}")
        return False

def print_usage_instructions():
    """چاپ دستورالعمل استفاده"""
    
    print("\n" + "=" * 60)
    print("📋 USAGE INSTRUCTIONS")
    print("=" * 60)
    print("🚀 Your bot is now configured to use HTTP proxy 10808!")
    print()
    print("📝 To start the bot:")
    print("   python bot.py")
    print("   # or")
    print("   python main.py")
    print()
    print("🔧 Configuration Details:")
    print("   - HTTP Proxy: 127.0.0.1:10808 ✅")
    print("   - SOCKS5 Proxy: Disabled ❌")
    print("   - Single Proxy Mode: Enabled ✅")
    print()
    print("📁 Configuration Files:")
    print("   - .env (environment variables)")
    print("   - config.py (updated if exists)")
    print()
    print("⚠️  Important Notes:")
    print("   - Make sure your HTTP proxy on port 10808 is running")
    print("   - The bot will use this proxy for all YouTube downloads")
    print("   - If proxy fails, the bot will fallback to direct connection")
    print()
    print("🔄 To change proxy settings later:")
    print("   - Edit the .env file")
    print("   - Or run this script again with different settings")
    print("=" * 60)

if __name__ == "__main__":
    print("🚀 HTTP Proxy 10808 Configuration Script")
    print("=" * 80)
    
    async def main():
        success_count = 0
        total_steps = 4
        
        # مرحله 1: تنظیم متغیرهای محیطی
        print("STEP 1/4: Environment Configuration")
        if configure_environment():
            success_count += 1
        
        # مرحله 2: ایجاد فایل .env
        print("\nSTEP 2/4: Creating .env file")
        if create_env_file():
            success_count += 1
        
        # مرحله 3: بروزرسانی config.py
        print("\nSTEP 3/4: Updating config.py")
        if update_config_py():
            success_count += 1
        
        # مرحله 4: تست تنظیمات
        print("\nSTEP 4/4: Testing configuration")
        if await test_configuration():
            success_count += 1
        
        # نتیجه نهایی
        print("\n" + "=" * 80)
        print("CONFIGURATION RESULTS:")
        print("=" * 80)
        print(f"📊 Completed: {success_count}/{total_steps} steps")
        
        if success_count == total_steps:
            print("🎉 SUCCESS! HTTP proxy 10808 configured successfully!")
            print_usage_instructions()
            return True
        elif success_count >= 2:
            print("⚠️  PARTIAL SUCCESS! Some steps completed.")
            print("The bot should work, but please check any failed steps.")
            print_usage_instructions()
            return True
        else:
            print("❌ FAILED! Configuration unsuccessful.")
            print("Please check the errors above and try again.")
            return False
    
    success = asyncio.run(main())
    sys.exit(0 if success else 1)