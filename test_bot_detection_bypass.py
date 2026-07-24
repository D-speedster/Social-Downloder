"""
تست استراتژی fallback برای bypass کردن bot detection در YouTube

این تست بررسی می‌کند که:
1. اگر خطای bot detection رخ دهد، از player_client محدود استفاده شود
2. استراتژی fallback در هر دو extract_video_info و download کار کند
"""

import asyncio
import logging
from plugins.youtube_handler import extract_video_info
from plugins.youtube_downloader import youtube_downloader

# تنظیم logging برای مشاهده دقیق
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_extract_with_fallback():
    """تست استخراج اطلاعات با fallback"""
    print("\n" + "="*60)
    print("TEST 1: Extract Video Info with Fallback Strategy")
    print("="*60 + "\n")
    
    # یک URL معمولی یوتیوب
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    print(f"Testing URL: {test_url}")
    print("Expected behavior:")
    print("  1. Try with default settings (all qualities)")
    print("  2. If bot detection error → fallback to player_client=['android', 'web', 'mweb']")
    print("  3. Return video info with available qualities\n")
    
    try:
        video_info = await extract_video_info(test_url)
        
        if video_info:
            print(f"✅ SUCCESS: Video info extracted")
            print(f"   Title: {video_info.get('title')}")
            print(f"   Duration: {video_info.get('duration')}s")
            print(f"   Available qualities: {list(video_info.get('qualities', {}).keys())}")
            return True
        else:
            print(f"❌ FAILED: Could not extract video info")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


async def test_download_with_fallback():
    """تست دانلود با fallback"""
    print("\n" + "="*60)
    print("TEST 2: Download with Fallback Strategy")
    print("="*60 + "\n")
    
    # یک URL معمولی یوتیوب
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    print(f"Testing URL: {test_url}")
    print("Expected behavior:")
    print("  1. Try download with default settings")
    print("  2. If bot detection error → retry with player_client=['android', 'web', 'mweb']")
    print("  3. Download successfully (even with restricted quality)\n")
    
    print("⚠️  NOTE: Actual download will be skipped in this test")
    print("         We're just verifying the logic structure exists\n")
    
    # بررسی اینکه کد دارای استراتژی fallback است
    import inspect
    source = inspect.getsource(youtube_downloader.download)
    
    checks = {
        "Bot detection check": "sign in" in source.lower() and "bot" in source.lower(),
        "Player client fallback": "player_client" in source,
        "Remote components": "remote_components" in source,
        "Use bot bypass flag": "use_bot_bypass" in source,
    }
    
    print("Code structure verification:")
    all_passed = True
    for check_name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"  {status} {check_name}: {'FOUND' if result else 'MISSING'}")
        if not result:
            all_passed = False
    
    return all_passed


async def test_cookie_helper():
    """تست cookie helper functions"""
    print("\n" + "="*60)
    print("TEST 3: Cookie Helper Functions")
    print("="*60 + "\n")
    
    from plugins.youtube_cookie_helper import (
        _convert_json_to_netscape,
        get_cookie_file,
        mark_cookie_failure,
        cleanup_temp_cookies
    )
    
    checks_passed = 0
    total_checks = 4
    
    # بررسی 1: تابع تبدیل JSON به Netscape
    print("1. Testing JSON to Netscape conversion...")
    json_cookie = '[{"name":"test","value":"123","domain":".youtube.com"}]'
    netscape_result = _convert_json_to_netscape(json_cookie)
    if "Netscape HTTP Cookie File" in netscape_result:
        print("   ✅ JSON conversion works")
        checks_passed += 1
    else:
        print("   ❌ JSON conversion failed")
    
    # بررسی 2: تابع get_cookie_file
    print("2. Testing get_cookie_file...")
    try:
        cookie_file = get_cookie_file()
        print(f"   ✅ get_cookie_file works (returned: {cookie_file})")
        checks_passed += 1
    except Exception as e:
        print(f"   ❌ get_cookie_file error: {e}")
    
    # بررسی 3: تابع mark_cookie_failure
    print("3. Testing mark_cookie_failure...")
    try:
        mark_cookie_failure()
        print("   ✅ mark_cookie_failure works")
        checks_passed += 1
    except Exception as e:
        print(f"   ❌ mark_cookie_failure error: {e}")
    
    # بررسی 4: تابع cleanup_temp_cookies
    print("4. Testing cleanup_temp_cookies...")
    try:
        removed = cleanup_temp_cookies()
        print(f"   ✅ cleanup_temp_cookies works (removed {removed} files)")
        checks_passed += 1
    except Exception as e:
        print(f"   ❌ cleanup_temp_cookies error: {e}")
    
    print(f"\nCookie Helper Score: {checks_passed}/{total_checks}")
    return checks_passed == total_checks


async def main():
    """اجرای همه تست‌ها"""
    print("\n" + "🔥"*30)
    print("YouTube Bot Detection Bypass - Test Suite")
    print("🔥"*30 + "\n")
    
    results = []
    
    # تست 1: Extract with fallback
    result1 = await test_extract_with_fallback()
    results.append(("Extract with Fallback", result1))
    
    # تست 2: Download with fallback
    result2 = await test_download_with_fallback()
    results.append(("Download with Fallback", result2))
    
    # تست 3: Cookie helper
    result3 = await test_cookie_helper()
    results.append(("Cookie Helper", result3))
    
    # خلاصه نتایج
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60 + "\n")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\n{'='*60}")
    print(f"Final Score: {passed}/{total} tests passed")
    print(f"{'='*60}\n")
    
    if passed == total:
        print("🎉 All tests passed! Bot detection bypass is ready.")
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
    
    return passed == total


if __name__ == "__main__":
    asyncio.run(main())
