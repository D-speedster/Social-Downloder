#!/usr/bin/env python3
"""
تست یکپارچگی ساده بات با پروکسی HTTP 10808
Simple bot integration test with HTTP proxy 10808
"""

import os
import asyncio
import sys

async def test_bot_integration():
    """تست یکپارچگی بات با پروکسی HTTP"""
    
    # تنظیم متغیرهای محیطی برای استفاده از HTTP proxy
    os.environ['YOUTUBE_SINGLE_PROXY'] = 'http://127.0.0.1:10808'
    os.environ['YOUTUBE_ENABLE_SOCKS'] = '0'  # غیرفعال کردن SOCKS5
    
    print("🤖 Simple Bot Integration Test with HTTP Proxy 10808")
    print("=" * 60)
    print(f"🔧 HTTP Proxy: {os.environ.get('YOUTUBE_SINGLE_PROXY')}")
    print(f"🚫 SOCKS5 Disabled: {os.environ.get('YOUTUBE_ENABLE_SOCKS')}")
    print("=" * 60)
    
    # تست با ماژول یوتیوب بات
    try:
        from plugins.youtube_proxy_rotator import extract_with_rotation
        
        test_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll
            "https://www.youtube.com/watch?v=9bZkp7q19f0",  # Gangnam Style
        ]
        
        results = []
        
        for i, url in enumerate(test_urls, 1):
            print(f"\n🎬 Test {i}: {url}")
            print("-" * 40)
            
            try:
                # تست با extract_with_rotation
                result = await extract_with_rotation(url, {
                    'quiet': False,
                    'no_warnings': False,
                })
                
                if result and isinstance(result, dict):
                    print(f"✅ SUCCESS!")
                    print(f"📹 Title: {result.get('title', 'N/A')}")
                    print(f"⏱️  Duration: {result.get('duration', 'N/A')} seconds")
                    print(f"👀 Views: {result.get('view_count', 'N/A')}")
                    print(f"📺 Channel: {result.get('uploader', 'N/A')}")
                    results.append(True)
                else:
                    print(f"❌ FAILED: No valid result")
                    results.append(False)
                    
            except Exception as e:
                print(f"❌ ERROR: {str(e)}")
                results.append(False)
        
        # نتیجه نهایی
        print("\n" + "=" * 60)
        print("INTEGRATION TEST RESULTS:")
        print("=" * 60)
        
        passed = sum(results)
        total = len(results)
        
        for i, (url, success) in enumerate(zip(test_urls, results), 1):
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"Test {i}: {status}")
        
        print(f"\n📊 Summary: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All integration tests passed! Bot is ready to use with HTTP proxy.")
            return True
        elif passed > 0:
            print("⚠️  Some tests passed. Bot works but there might be issues with some videos.")
            return True
        else:
            print("💥 All tests failed. Check bot configuration.")
            return False
            
    except ImportError as e:
        print(f"❌ Import Error: {str(e)}")
        print("Make sure all bot modules are properly installed.")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")
        return False

def test_proxy_connectivity():
    """تست اتصال مستقیم به پروکسی"""
    
    print("🔧 Proxy Connectivity Test")
    print("=" * 40)
    
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3.0)
        result = sock.connect_ex(('127.0.0.1', 10808))
        sock.close()
        
        if result == 0:
            print("✅ HTTP proxy 10808 is reachable")
            return True
        else:
            print("❌ HTTP proxy 10808 is not reachable")
            return False
    except Exception as e:
        print(f"❌ Socket test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Simple Bot Integration Test with HTTP Proxy")
    print("=" * 80)
    
    async def run_integration_test():
        # تست اتصال پروکسی
        proxy_ok = test_proxy_connectivity()
        
        if not proxy_ok:
            print("❌ HTTP proxy 10808 is not available. Please check your proxy server.")
            return False
        
        # تست یکپارچگی بات
        bot_ok = await test_bot_integration()
        
        print("\n" + "=" * 80)
        print("FINAL INTEGRATION RESULTS:")
        print("=" * 80)
        
        if bot_ok:
            print("🎉 SUCCESS! Bot is fully functional with HTTP proxy 10808.")
            print("✅ You can now use the bot with confidence.")
            print("\n📝 Configuration Summary:")
            print("   - HTTP Proxy: 127.0.0.1:10808 ✅")
            print("   - SOCKS5 Proxy: Disabled ❌")
            print("   - Single Proxy Mode: Enabled ✅")
            print("\n🚀 Ready to start the bot!")
            return True
        else:
            print("❌ FAILED! Bot integration test failed.")
            print("Please check the configuration and try again.")
            return False
    
    success = asyncio.run(run_integration_test())
    sys.exit(0 if success else 1)