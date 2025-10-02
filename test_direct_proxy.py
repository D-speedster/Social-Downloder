#!/usr/bin/env python3
"""
تست مستقیم پروکسی - شبیه‌سازی دقیق دستور دستی
Direct proxy test - exact simulation of manual command
"""

import os
import asyncio
import sys
from yt_dlp import YoutubeDL

async def test_direct_proxy():
    """تست مستقیم با پروکسی 1082 - دقیقاً مثل دستور دستی"""
    
    # URL تست
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    # تنظیمات دقیقاً مثل دستور دستی
    opts = {
        'proxy': 'socks5://127.0.0.1:10808',
        'quiet': False,
        'no_warnings': False,
    }
    
    print(f"🔍 Direct test with SOCKS5 proxy: 127.0.0.1:1082")
    print(f"📺 URL: {test_url}")
    print(f"⚙️  Options: {opts}")
    print("=" * 60)
    
    try:
        # تست مستقیم با YoutubeDL
        print("🚀 Starting direct YoutubeDL extraction...")
        
        def extract_info():
            with YoutubeDL(opts) as ydl:
                return ydl.extract_info(test_url, download=False)
        
        result = await asyncio.to_thread(extract_info)
        
        if result and isinstance(result, dict):
            print("✅ SUCCESS! Direct proxy test completed successfully")
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

async def test_with_rotation():
    """تست با سیستم rotation ما"""
    
    # تنظیم پروکسی واحد
    os.environ['YOUTUBE_SINGLE_PROXY'] = 'socks5://127.0.0.1:1082'
    
    from plugins.youtube_proxy_rotator import extract_with_rotation
    
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    # تنظیمات ساده
    base_opts = {
        'quiet': False,
        'no_warnings': False,
    }
    
    print(f"\n🔄 Testing with rotation system...")
    print(f"📺 URL: {test_url}")
    print(f"⚙️  Base options: {base_opts}")
    print("=" * 60)
    
    try:
        result = await extract_with_rotation(test_url, base_opts)
        
        if result and isinstance(result, dict):
            print("✅ SUCCESS! Rotation system test completed successfully")
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
    print("🚀 Starting comprehensive proxy tests...")
    print("📋 This will test both direct and rotation methods")
    print()
    
    async def run_tests():
        # تست 1: مستقیم
        print("=" * 80)
        print("TEST 1: Direct YoutubeDL with proxy (simulating manual command)")
        print("=" * 80)
        direct_success = await test_direct_proxy()
        
        # تست 2: با سیستم rotation
        print("\n" + "=" * 80)
        print("TEST 2: Using rotation system with single proxy")
        print("=" * 80)
        rotation_success = await test_with_rotation()
        
        # نتیجه نهایی
        print("\n" + "=" * 80)
        print("FINAL RESULTS:")
        print("=" * 80)
        print(f"✅ Direct test: {'PASSED' if direct_success else 'FAILED'}")
        print(f"🔄 Rotation test: {'PASSED' if rotation_success else 'FAILED'}")
        
        if direct_success and rotation_success:
            print("\n🎉 All tests passed! Proxy configuration is working correctly.")
            return True
        elif direct_success and not rotation_success:
            print("\n⚠️  Direct test passed but rotation failed. Issue is in our rotation code.")
            return False
        elif not direct_success and not rotation_success:
            print("\n💥 Both tests failed. Check if proxy is running on port 1082.")
            return False
        else:
            print("\n🤔 Unexpected result pattern.")
            return False
    
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)