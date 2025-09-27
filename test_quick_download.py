"""
تست سریع برای دانلود ویدیو کوتاه
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

# Short test video (available and short)
TEST_URL = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"  # Big Buck Bunny trailer (short)

async def quick_test():
    """تست سریع دانلود"""
    print("🚀 Quick download test...")
    
    try:
        # Get quality options
        print("📊 Getting quality options...")
        start_time = datetime.now()
        quality_options = await quality_selector.get_quality_options(TEST_URL)
        extraction_time = (datetime.now() - start_time).total_seconds()
        
        if not quality_options:
            print("❌ Failed to get quality options")
            return False
        
        print(f"✅ Quality extraction: {extraction_time:.2f}s")
        print(f"📹 Title: {quality_options['title']}")
        print(f"⏱ Duration: {quality_options['duration']}s")
        print(f"🎯 Available qualities: {len(quality_options['qualities'])}")
        
        # Select lowest quality for quick test
        if not quality_options['qualities']:
            print("❌ No qualities available")
            return False
        
        # Find lowest resolution quality
        selected_quality = quality_options['qualities'][-1]  # Usually lowest is last
        print(f"🎯 Testing with: {selected_quality['resolution']} ({selected_quality['type']})")
        
        # Create output path
        output_path = os.path.join(tempfile.gettempdir(), f"quick_test_{selected_quality['resolution']}.mp4")
        
        # Progress callback
        def progress_callback(d):
            if d['status'] == 'downloading':
                if 'total_bytes' in d and d['total_bytes']:
                    downloaded = d.get('downloaded_bytes', 0)
                    total = d['total_bytes']
                    progress = int((downloaded / total) * 100)
                    print(f"\r📥 Progress: {progress}%", end='', flush=True)
        
        # Download
        print("\n📥 Starting download...")
        download_start = datetime.now()
        final_path = await youtube_downloader.download_and_merge(
            TEST_URL, selected_quality, output_path, None, progress_callback
        )
        download_time = (datetime.now() - download_start).total_seconds()
        
        if final_path and os.path.exists(final_path):
            file_size = os.path.getsize(final_path)
            print(f"\n✅ Download completed: {download_time:.2f}s")
            print(f"📦 File size: {file_size / (1024*1024):.2f} MB")
            
            # Test metadata
            print("📊 Extracting metadata...")
            metadata_start = datetime.now()
            metadata = await youtube_downloader.get_file_metadata(final_path)
            metadata_time = (datetime.now() - metadata_start).total_seconds()
            
            print(f"✅ Metadata extraction: {metadata_time:.2f}s")
            if metadata:
                print(f"   Resolution: {metadata.get('width', 0)}x{metadata.get('height', 0)}")
                print(f"   Duration: {metadata.get('duration', 0):.2f}s")
                print(f"   Video codec: {metadata.get('video_codec', 'Unknown')}")
                print(f"   Audio codec: {metadata.get('audio_codec', 'Unknown')}")
                print(f"   FPS: {metadata.get('fps', 0):.2f}")
            
            # Clean up
            try:
                os.unlink(final_path)
                print("🗑 File cleaned up")
            except:
                pass
            
            total_time = extraction_time + download_time + metadata_time
            print(f"\n🎉 Total time: {total_time:.2f}s")
            print(f"   Extraction: {extraction_time:.2f}s")
            print(f"   Download: {download_time:.2f}s") 
            print(f"   Metadata: {metadata_time:.2f}s")
            
            return True
        else:
            print("\n❌ Download failed")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(quick_test())
    if result:
        print("\n✅ Quick test PASSED")
    else:
        print("\n❌ Quick test FAILED")