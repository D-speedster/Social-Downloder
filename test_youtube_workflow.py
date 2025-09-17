import os
import sys
import time
from yt_dlp import YoutubeDL

def test_youtube_workflow():
    # Test URLs - one normal video and one that requires authentication
    normal_url = "https://www.youtube.com/watch?v=Cd9jejfatdI"  # A popular video that should work without authentication
    auth_url = "https://www.youtube.com/watch?v=XBJ5qRoBSeg"    # Video that requires authentication
    
    # Path to cookies file
    cookies_path = os.path.join(os.getcwd(), 'cookies', 'youtube.txt')
    print(f"Cookies file exists: {os.path.exists(cookies_path)}")
    
    # Test 1: Extract formats from normal video
    print("\n=== Test 1: Extract formats from normal video ===\n")
    test_extract_formats(normal_url, cookies_path)
    
    # Test 2: Extract formats from video requiring authentication
    print("\n=== Test 2: Extract formats from video requiring authentication ===\n")
    test_extract_formats(auth_url, cookies_path)
    
    # Test 3: Download a small portion of video with cookies
    print("\n=== Test 3: Download a small portion of video with cookies ===\n")
    test_download_with_progress(auth_url, cookies_path)

def test_extract_formats(url, cookies_path):
    ydl_opts = {
        'quiet': True,
        'simulate': True,
        'cookiefile': cookies_path,
        'extractor_retries': 3,
        'fragment_retries': 3,
        'retry_sleep_functions': {'http': lambda n: min(4 ** n, 60)}
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print(f"Title: {info.get('title')}")
            print(f"Duration: {info.get('duration')} seconds")
            
            # Count video formats
            video_formats = [f for f in info['formats'] 
                           if f.get('vcodec', 'none') != 'none' and f.get('acodec', 'none') != 'none']
            print(f"Available video formats: {len(video_formats)}")
            
            # Print some video formats
            print("\nSample video formats:")
            for i, fmt in enumerate(sorted(video_formats, key=lambda x: (x.get('height', 0) or 0), reverse=True)):
                if i < 5:  # Show top 5 formats
                    print(f"  {fmt.get('format_id')}: {fmt.get('height')}p - {fmt.get('ext')} - {fmt.get('filesize_approx', 0) // 1024 // 1024}MB")
            
            # Count audio formats
            audio_formats = [f for f in info['formats'] 
                           if f.get('vcodec', 'none') == 'none' and f.get('acodec', 'none') != 'none']
            print(f"\nAvailable audio formats: {len(audio_formats)}")
            
            # Print some audio formats
            print("\nSample audio formats:")
            for i, fmt in enumerate(sorted(audio_formats, key=lambda x: (x.get('abr', 0) or 0), reverse=True)):
                if i < 5:  # Show top 5 formats
                    print(f"  {fmt.get('format_id')}: {fmt.get('abr')}kbps - {fmt.get('ext')} - {fmt.get('filesize_approx', 0) // 1024 // 1024}MB")
            
            print("\nFormat extraction: SUCCESS")
            return True
    except Exception as e:
        print(f"Format extraction failed: {e}")
        return False

def test_download_with_progress(url, cookies_path):
    # Create a progress hook to show download progress
    def progress_hook(d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            if total_bytes > 0:
                downloaded_bytes = d.get('downloaded_bytes', 0)
                percent = int(downloaded_bytes / total_bytes * 100)
                speed = d.get('speed', 0)
                speed_str = f"{speed / 1024 / 1024:.2f} MB/s" if speed else "N/A"
                eta = d.get('eta', 0)
                eta_str = f"{int(eta)} seconds" if eta else "N/A"
                
                sys.stdout.write(f"\rDownloading: {percent}% | Speed: {speed_str} | ETA: {eta_str}")
                sys.stdout.flush()
                
                # Download only a small portion (10%) to save time
                if percent >= 10:
                    raise KeyboardInterrupt("Stopping download at 10% for testing purposes")
        elif d['status'] == 'finished':
            print("\nDownload finished!")
    
    # Set up yt-dlp options for downloading
    filename = "test_download.mp4"
    ydl_opts = {
        'format': 'best[height<=480]',  # Choose a smaller format for testing
        'outtmpl': filename,
        'progress_hooks': [progress_hook],
        'noplaylist': True,
        'cookiefile': cookies_path,
        'extractor_retries': 3,
        'fragment_retries': 3,
        'retry_sleep_functions': {'http': lambda n: min(4 ** n, 60)},
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download([url])
            except KeyboardInterrupt as e:
                if "testing purposes" in str(e):
                    print("\nDownload test stopped at 10% as planned.")
                    print("Progress updates are working correctly.")
                    return True
                else:
                    raise
    except Exception as e:
        print(f"\nDownload test failed: {e}")
        return False
    finally:
        # Clean up the test file
        if os.path.exists(filename):
            try:
                os.remove(filename)
                print(f"Test file {filename} removed.")
            except Exception as e:
                print(f"Could not remove test file: {e}")

if __name__ == "__main__":
    test_youtube_workflow()