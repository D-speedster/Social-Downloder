#!/usr/bin/env python3
"""
تنظیم بات برای کار بدون پروکسی
Configure bot to work without proxy
"""

import os

def configure_no_proxy():
    """تنظیم متغیرهای محیطی برای غیرفعال کردن پروکسی"""
    
    print("🔧 Configuring bot to work without proxy...")
    
    # غیرفعال کردن SOCKS5
    os.environ['YOUTUBE_ENABLE_SOCKS'] = '0'
    
    # حذف پروکسی واحد
    if 'YOUTUBE_SINGLE_PROXY' in os.environ:
        del os.environ['YOUTUBE_SINGLE_PROXY']
    
    print("✅ Configuration completed:")
    print("   - SOCKS5 proxies: DISABLED")
    print("   - HTTP proxy: Will be skipped if not available")
    print("   - Bot will use direct connection")
    
    print("\n📋 To make this permanent, add this to your environment:")
    print("   YOUTUBE_ENABLE_SOCKS=0")
    
    return True

def test_no_proxy():
    """تست بدون پروکسی"""
    import asyncio
    from plugins.youtube_proxy_rotator import extract_with_rotation
    
    async def run_test():
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        base_opts = {
            'quiet': False,
            'no_warnings': False,
        }
        
        print(f"\n🧪 Testing without proxy...")
        print(f"📺 URL: {test_url}")
        
        try:
            result = await extract_with_rotation(test_url, base_opts)
            
            if result and isinstance(result, dict):
                print("✅ SUCCESS! No-proxy test completed successfully")
                print(f"📹 Title: {result.get('title', 'N/A')}")
                print(f"⏱️  Duration: {result.get('duration', 'N/A')} seconds")
                print(f"👀 Views: {result.get('view_count', 'N/A')}")
                return True
            else:
                print("❌ FAILED: No valid result returned")
                return False
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            return False
    
    return asyncio.run(run_test())

if __name__ == "__main__":
    print("🚀 YouTube Downloader - No Proxy Configuration")
    print("=" * 60)
    
    # تنظیم
    configure_no_proxy()
    
    # تست
    success = test_no_proxy()
    
    if success:
        print("\n🎉 Perfect! Bot is working correctly without proxy.")
        print("💡 You can now use the bot normally.")
        print("🔧 If you want to use proxy later, just enable it in config.")
    else:
        print("\n💥 Test failed even without proxy.")
        print("🔍 There might be another issue.")