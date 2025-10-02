#!/usr/bin/env python3
"""
تست ساده برای یک پروکسی واحد
Test script for single proxy configuration
"""

import asyncio
import sys
from plugins.youtube_proxy_rotator import extract_with_rotation

async def test_single_proxy():
    """تست با یک پروکسی واحد"""
    
    # URL تست (همان لینکی که کاربر استفاده کرد)
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    # تنظیمات پایه
    base_opts = {
        'quiet': False,
        'no_warnings': False,
        'extract_flat': False,
    }
    
    print(f"🔍 Testing single proxy with URL: {test_url}")
    print("=" * 60)
    
    try:
        # تست استخراج اطلاعات
        result = await extract_with_rotation(test_url, base_opts)
        
        if result and isinstance(result, dict):
            print("✅ SUCCESS! Proxy test completed successfully")
            print(f"📹 Title: {result.get('title', 'N/A')}")
            print(f"⏱️  Duration: {result.get('duration', 'N/A')} seconds")
            print(f"👀 Views: {result.get('view_count', 'N/A')}")
            print(f"📺 Channel: {result.get('uploader', 'N/A')}")
            return True
        else:
            print("❌ FAILED: No valid result returned")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Starting single proxy test...")
    print("📋 This will test the proxy configuration with a single video")
    print()
    
    # اجرای تست
    success = asyncio.run(test_single_proxy())
    
    if success:
        print("\n🎉 Test completed successfully!")
        print("✅ Your proxy configuration is working correctly")
        sys.exit(0)
    else:
        print("\n💥 Test failed!")
        print("❌ Please check your proxy configuration")
        sys.exit(1)