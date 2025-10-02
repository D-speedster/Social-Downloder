#!/usr/bin/env python3
import yt_dlp
from plugins.cookie_manager import get_cookie_file_with_fallback

def test_youtube_download():
    try:
        # Get cookie file
        cookiefile, cid = get_cookie_file_with_fallback()
        print(f"Using cookie: {cookiefile}")
        print(f"Cookie ID: {cid}")
        
        # Configure yt-dlp
        ydl_opts = {
            'quiet': True,
            # 'proxy': 'socks5h://127.0.0.1:1084',  # Disabled for testing
            'cookiefile': cookiefile,
            # Use default web client which supports cookies
        }
        
        # Test extraction
        ydl = yt_dlp.YoutubeDL(ydl_opts)
        info = ydl.extract_info('https://youtube.com/shorts/oQ3Gz651vVY', download=False)
        
        print(f"Title: {info.get('title', 'Unknown')}")
        print(f"Duration: {info.get('duration', 'Unknown')}")
        print("✅ Success! YouTube extraction works with cookies!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_youtube_download()