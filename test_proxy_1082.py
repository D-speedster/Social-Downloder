#!/usr/bin/env python3
"""
تست با پروکسی واحد 1082
Test with single proxy 1082 (the one that worked manually)
"""

import os
import asyncio
import sys

# تنظیم پروکسی واحد برای تست
os.environ['YOUTUBE_SINGLE_PROXY'] = 'socks5://127.0.0.1:1082'

from plugins.youtube_proxy_rotator import extract_with_rotation

async def test_proxy_1082():
    """تست با پروکسی 1082 که دستی کار کرد"""
    
    # URL تست (همان لینکی که کاربر استفاده کرد)
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    # تنظیمات پایه
    base_opts = {
        'quiet': False,
        'no_warnings': False,
        'extract_flat': False,
    }
    
    print(f"🔍 Testing with SOCKS5 proxy: 127.0.0.1:1082")
    print(f"📺 URL: {test_url}")
    print("=" * 60)
    
    try:
        # تست استخراج اطلاعات
        result = await extract_with_rotation(test_url, base_opts)
        
        if result and isinstance(result, dict):
            print("✅ SUCCESS! Single proxy test completed successfully")
            print(f"📹 Title: {result.get('title', 'N/A')}")
            print(f"⏱️  Duration: {result.get('duration', 'N/A')} seconds")
            print(f"👀 Views: {result.get('view_count', 'N/A')}")
            print(f"📺 Channel: {result.get('uploader', 'N/A')}")
            print(f"🔗 URL: {result.get('webpage_url', 'N/A')}")
            return True
        else:
            print("❌ FAILED: No valid result returned")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Starting single proxy test with port 1082...")
    print("📋 This will test only the proxy that worked manually")
    print()
    
    # اجرای تست
    success = asyncio.run(test_proxy_1082())
    
    if success:
        print("\n🎉 Test completed successfully!")
        print("✅ Proxy 1082 is working correctly with the bot")
        print("💡 You can now use this configuration for all downloads")
        sys.exit(0)
    else:
        print("\n💥 Test failed!")
        print("❌ There might be an issue with the proxy configuration")
        print("🔧 Check if the proxy is running on port 1082")
        sys.exit(1)