#!/usr/bin/env python3
"""
تست پروکسی HTTP پورت 10808
Test HTTP proxy on port 10808
"""

import os
import asyncio
import sys
from yt_dlp import YoutubeDL

async def test_http_proxy_direct():
    """تست مستقیم با پروکسی HTTP 10808"""
    
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    # تنظیمات مستقیم با پروکسی HTTP
    opts = {
        'proxy': 'http://127.0.0.1:10808',
        'quiet': False,
        'no_warnings': False,
    }
    
    print(f"🔍 Direct test with HTTP proxy: 127.0.0.1:10808")
    print(f"📺 URL: {test_url}")
    print(f"⚙️  Options: {opts}")
    print("=" * 60)
    
    try:
        print("🚀 Starting direct YoutubeDL extraction with HTTP proxy...")
        
        def extract_info():
            with YoutubeDL(opts) as ydl:
                return ydl.extract_info(test_url, download=False)
        
        result = await asyncio.to_thread(extract_info)
        
        if result and isinstance(result, dict):
            print("✅ SUCCESS! HTTP proxy test completed successfully")
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

async def test_http_proxy_rotation():
    """تست با سیستم rotation و پروکسی HTTP"""
    
    # غیرفعال کردن SOCKS5 تا فقط HTTP استفاده شه
    os.environ['YOUTUBE_ENABLE_SOCKS'] = '0'
    
    # حذف پروکسی واحد تا سیستم عادی کار کنه
    if 'YOUTUBE_SINGLE_PROXY' in os.environ:
        del os.environ['YOUTUBE_SINGLE_PROXY']
    
    from plugins.youtube_proxy_rotator import extract_with_rotation
    
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    base_opts = {
        'quiet': False,
        'no_warnings': False,
    }
    
    print(f"\n🔄 Testing with rotation system (HTTP proxy only)...")
    print(f"📺 URL: {test_url}")
    print(f"⚙️  SOCKS5 disabled, HTTP proxy enabled")
    print("=" * 60)
    
    try:
        result = await extract_with_rotation(test_url, base_opts)
        
        if result and isinstance(result, dict):
            print("✅ SUCCESS! HTTP rotation test completed successfully")
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

async def test_single_http_proxy():
    """تست با تنظیم پروکسی HTTP به عنوان پروکسی واحد"""
    
    # تنظیم پروکسی HTTP به عنوان پروکسی واحد
    os.environ['YOUTUBE_SINGLE_PROXY'] = 'http://127.0.0.1:10808'
    
    from plugins.youtube_proxy_rotator import extract_with_rotation
    
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    base_opts = {
        'quiet': False,
        'no_warnings': False,
    }
    
    print(f"\n🎯 Testing with single HTTP proxy configuration...")
    print(f"📺 URL: {test_url}")
    print(f"⚙️  Single proxy: http://127.0.0.1:10808")
    print("=" * 60)
    
    try:
        result = await extract_with_rotation(test_url, base_opts)
        
        if result and isinstance(result, dict):
            print("✅ SUCCESS! Single HTTP proxy test completed successfully")
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
    print("🚀 HTTP Proxy Tests (Port 10808)")
    print("=" * 80)
    
    async def run_all_tests():
        results = {}
        
        # تست 1: مستقیم
        print("TEST 1: Direct HTTP proxy test")
        print("=" * 80)
        results['direct'] = await test_http_proxy_direct()
        
        # تست 2: با سیستم rotation (فقط HTTP)
        print("\n" + "=" * 80)
        print("TEST 2: Rotation system with HTTP proxy only")
        print("=" * 80)
        results['rotation'] = await test_http_proxy_rotation()
        
        # تست 3: پروکسی واحد HTTP
        print("\n" + "=" * 80)
        print("TEST 3: Single HTTP proxy configuration")
        print("=" * 80)
        results['single'] = await test_single_http_proxy()
        
        # نتایج نهایی
        print("\n" + "=" * 80)
        print("FINAL RESULTS:")
        print("=" * 80)
        print(f"🎯 Direct HTTP proxy: {'✅ PASSED' if results['direct'] else '❌ FAILED'}")
        print(f"🔄 Rotation HTTP only: {'✅ PASSED' if results['rotation'] else '❌ FAILED'}")
        print(f"🎯 Single HTTP proxy: {'✅ PASSED' if results['single'] else '❌ FAILED'}")
        
        passed_count = sum(results.values())
        total_count = len(results)
        
        print(f"\n📊 Summary: {passed_count}/{total_count} tests passed")
        
        if passed_count == total_count:
            print("🎉 All tests passed! HTTP proxy is working perfectly.")
            return True
        elif passed_count > 0:
            print("⚠️  Some tests passed. HTTP proxy works but there might be configuration issues.")
            return True
        else:
            print("💥 All tests failed. Check HTTP proxy configuration.")
            return False
    
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)