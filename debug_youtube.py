"""
Debug script برای تست استخراج اطلاعات یوتیوب
"""

import asyncio
import yt_dlp
import os

async def test_extract():
    """تست استخراج اطلاعات"""
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    try:
        # Check for cookie file
        cookie_file = 'cookie_youtube.txt'
        
        ydl_opts = {
            'quiet': False,  # Enable output for debugging
            'no_warnings': False,  # Show warnings
            'extract_flat': False,
            'skip_download': True,
        }
        
        # Add cookies if file exists
        if os.path.exists(cookie_file):
            ydl_opts['cookiefile'] = cookie_file
            print(f"✅ Using cookies from: {cookie_file}")
        else:
            print(f"⚠️ Cookie file not found: {cookie_file}")
        
        print(f"🔍 Extracting info from: {url}")
        
        def _extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _extract)
        
        if not info:
            print("❌ No info extracted")
            return
        
        print(f"✅ Title: {info.get('title', 'Unknown')}")
        print(f"✅ Duration: {info.get('duration', 0)} seconds")
        print(f"✅ Uploader: {info.get('uploader', 'Unknown')}")
        
        # Check formats
        formats = info.get('formats', [])
        print(f"✅ Total formats found: {len(formats)}")
        
        # Check for specific qualities
        SUPPORTED_QUALITIES = ['360', '480', '720', '1080']
        available_qualities = {}
        
        for quality in SUPPORTED_QUALITIES:
            height = int(quality)
            
            # First, try to find combined formats (video + audio in one file)
            combined_formats = [
                f for f in formats
                if f.get('vcodec') != 'none' 
                and f.get('acodec') != 'none'
                and f.get('height') == height
                and f.get('ext') in ['mp4', 'webm']
            ]
            
            print(f"📹 {quality}p combined formats found: {len(combined_formats)}")
            
            if combined_formats:
                available_qualities[quality] = True
                print(f"✅ {quality}p is available (combined)")
                # Show format details
                best = combined_formats[0]
                print(f"   Format ID: {best.get('format_id')}, VCodec: {best.get('vcodec')}, ACodec: {best.get('acodec')}")
            else:
                # Fallback: try separate video + audio formats
                video_formats = [
                    f for f in formats
                    if f.get('vcodec') != 'none' 
                    and f.get('acodec') == 'none'
                    and f.get('height') == height
                    and f.get('ext') in ['mp4', 'webm']
                ]
                
                audio_formats = [
                    f for f in formats
                    if f.get('acodec') != 'none'
                    and f.get('vcodec') == 'none'
                    and f.get('ext') in ['m4a', 'webm']
                ]
                
                print(f"📹 {quality}p separate video formats: {len(video_formats)}")
                print(f"🔊 Separate audio formats: {len(audio_formats)}")
                
                if video_formats and audio_formats:
                    available_qualities[quality] = True
                    print(f"✅ {quality}p is available (separate)")
                else:
                    print(f"❌ {quality}p: Not available")
        
        # Check audio-only
        audio_only_formats = [
            f for f in formats
            if f.get('acodec') != 'none'
            and f.get('vcodec') == 'none'
        ]
        
        print(f"🎵 Audio-only formats found: {len(audio_only_formats)}")
        
        if not audio_only_formats:
            # If no separate audio formats, try to find combined formats with audio
            audio_combined_formats = [
                f for f in formats
                if f.get('acodec') != 'none'
                and f.get('ext') in ['mp4', 'webm', 'm4a']
            ]
            print(f"🎵 Audio from combined formats: {len(audio_combined_formats)}")
            if audio_combined_formats:
                available_qualities['audio'] = True
                print("✅ Audio-only is available (from combined)")
        else:
            available_qualities['audio'] = True
            print("✅ Audio-only is available (separate)")
        
        print(f"\n📊 Final available qualities: {list(available_qualities.keys())}")
        
        if not available_qualities:
            print("❌ No qualities available!")
            
            # Debug: Show some format examples
            print("\n🔍 Sample formats:")
            for i, fmt in enumerate(formats[:10]):  # Show first 10 formats
                print(f"  {i+1}. ID: {fmt.get('format_id')}, "
                      f"Height: {fmt.get('height')}, "
                      f"VCodec: {fmt.get('vcodec')}, "
                      f"ACodec: {fmt.get('acodec')}, "
                      f"Ext: {fmt.get('ext')}")
        
        return available_qualities
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(test_extract())
    print(f"\n🎯 Result: {result}")