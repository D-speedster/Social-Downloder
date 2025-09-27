"""
اسکریپت تست برای سیستم جدید یوتیوب
"""

import asyncio
import os
import sys
import tempfile
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plugins.youtube_advanced_downloader import youtube_downloader
from plugins.youtube_quality_selector import quality_selector

# Test URLs with different qualities and formats
TEST_URLS = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll - Classic test
    "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # Me at the zoo - First YouTube video
    "https://www.youtube.com/watch?v=9bZkp7q19f0",  # Gangnam Style - Popular video
]

async def test_quality_extraction():
    """تست استخراج کیفیت‌ها"""
    print("🔍 Testing quality extraction...")
    
    for i, url in enumerate(TEST_URLS[:1], 1):  # Test only first URL for speed
        print(f"\n📹 Test {i}: {url}")
        
        try:
            # Get quality options
            start_time = datetime.now()
            quality_options = await quality_selector.get_quality_options(url)
            extraction_time = (datetime.now() - start_time).total_seconds()
            
            if quality_options:
                print(f"✅ Extraction successful in {extraction_time:.2f}s")
                print(f"📊 Title: {quality_options['title']}")
                print(f"⏱ Duration: {quality_options['duration']}")
                print(f"🎯 Available qualities: {len(quality_options['qualities'])}")
                
                # Show first few qualities
                for j, quality in enumerate(quality_options['qualities'][:3]):
                    print(f"   {j+1}. {quality['resolution']} - {quality['type']} - {quality.get('filesize_text', 'Unknown size')}")
                
                return quality_options
            else:
                print(f"❌ Failed to extract qualities")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    return None

async def test_download_and_merge():
    """تست دانلود و ترکیب"""
    print("\n📥 Testing download and merge...")
    
    # First get quality options
    quality_options = await test_quality_extraction()
    if not quality_options:
        print("❌ Cannot test download without quality options")
        return False
    
    # Select first available quality for testing
    if not quality_options['qualities']:
        print("❌ No qualities available for testing")
        return False
    
    selected_quality = quality_options['qualities'][0]
    print(f"🎯 Testing with quality: {selected_quality['resolution']} ({selected_quality['type']})")
    
    # Create output path
    safe_title = "test_video"
    output_path = os.path.join(tempfile.gettempdir(), f"{safe_title}_{selected_quality['resolution']}.mp4")
    
    try:
        # Progress callback for testing
        def progress_callback(d):
            if d['status'] == 'downloading':
                if 'total_bytes' in d and d['total_bytes']:
                    downloaded = d.get('downloaded_bytes', 0)
                    total = d['total_bytes']
                    progress = int((downloaded / total) * 100)
                    print(f"\r📥 Progress: {progress}%", end='', flush=True)
        
        # Download and merge
        start_time = datetime.now()
        final_path = await youtube_downloader.download_and_merge(
            TEST_URLS[0], selected_quality, output_path, None, progress_callback
        )
        download_time = (datetime.now() - start_time).total_seconds()
        
        print(f"\n✅ Download completed in {download_time:.2f}s")
        print(f"📁 Output: {final_path}")
        
        if final_path and os.path.exists(final_path):
            file_size = os.path.getsize(final_path)
            print(f"📦 File size: {file_size / (1024*1024):.2f} MB")
            
            # Test metadata extraction
            metadata = await youtube_downloader.get_file_metadata(final_path)
            if metadata:
                print(f"📊 Metadata extracted:")
                print(f"   Resolution: {metadata.get('width', 0)}x{metadata.get('height', 0)}")
                print(f"   Duration: {metadata.get('duration', 0):.2f}s")
                print(f"   Video codec: {metadata.get('video_codec', 'Unknown')}")
                print(f"   Audio codec: {metadata.get('audio_codec', 'Unknown')}")
            
            # Clean up
            try:
                os.unlink(final_path)
                print("🗑 Temporary file cleaned up")
            except:
                pass
            
            return True
        else:
            print("❌ Download failed - no output file")
            return False
            
    except Exception as e:
        print(f"❌ Download error: {e}")
        return False

async def test_ffmpeg_availability():
    """تست در دسترس بودن ffmpeg"""
    print("🔧 Testing ffmpeg availability...")
    
    ffmpeg_path = youtube_downloader._find_ffmpeg()
    if ffmpeg_path:
        print(f"✅ ffmpeg found at: {ffmpeg_path}")
        return True
    else:
        print("❌ ffmpeg not found")
        return False

async def test_audio_only_download():
    """تست دانلود فقط صدا"""
    print("\n🎵 Testing audio-only download...")
    
    try:
        # Get quality options
        quality_options = await quality_selector.get_quality_options(TEST_URLS[0])
        if not quality_options:
            print("❌ Cannot get quality options")
            return False
        
        # Get audio-only info
        audio_info = await quality_selector.get_audio_only_info(quality_options['raw_info'])
        if not audio_info:
            print("❌ No audio-only format available")
            return False
        
        print(f"🎯 Testing audio format: {audio_info.get('ext', 'unknown')} - {audio_info.get('filesize_text', 'Unknown size')}")
        
        # Create output path
        output_path = os.path.join(tempfile.gettempdir(), f"test_audio.{audio_info.get('ext', 'm4a')}")
        
        # Download audio
        start_time = datetime.now()
        final_path = await youtube_downloader.download_and_merge(
            TEST_URLS[0], audio_info, output_path, None, None
        )
        download_time = (datetime.now() - start_time).total_seconds()
        
        if final_path and os.path.exists(final_path):
            file_size = os.path.getsize(final_path)
            print(f"✅ Audio download completed in {download_time:.2f}s")
            print(f"📦 File size: {file_size / (1024*1024):.2f} MB")
            
            # Clean up
            try:
                os.unlink(final_path)
                print("🗑 Temporary file cleaned up")
            except:
                pass
            
            return True
        else:
            print("❌ Audio download failed")
            return False
            
    except Exception as e:
        print(f"❌ Audio download error: {e}")
        return False

async def run_comprehensive_test():
    """اجرای تست جامع"""
    print("🚀 Starting comprehensive YouTube system test...")
    print("=" * 60)
    
    test_results = {}
    
    # Test 1: ffmpeg availability
    test_results['ffmpeg'] = await test_ffmpeg_availability()
    
    # Test 2: Quality extraction
    test_results['quality_extraction'] = await test_quality_extraction() is not None
    
    # Test 3: Download and merge (only if ffmpeg is available)
    if test_results['ffmpeg']:
        test_results['download_merge'] = await test_download_and_merge()
        test_results['audio_download'] = await test_audio_only_download()
    else:
        test_results['download_merge'] = False
        test_results['audio_download'] = False
        print("⚠️ Skipping download tests - ffmpeg not available")
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY:")
    print("=" * 60)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    total_tests = len(test_results)
    passed_tests = sum(test_results.values())
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! System is ready for production.")
    elif passed_tests >= total_tests * 0.75:
        print("⚠️ Most tests passed. Minor issues may exist.")
    else:
        print("❌ Multiple test failures. System needs attention.")
    
    return test_results

if __name__ == "__main__":
    asyncio.run(run_comprehensive_test())