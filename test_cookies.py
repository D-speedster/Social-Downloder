#!/usr/bin/env python3
"""
Test script to verify YouTube cookie authentication with yt-dlp
"""

import os
from yt_dlp import YoutubeDL

def test_youtube_cookies():
    """Test YouTube video extraction with cookies"""
    
    # Test URL that typically requires authentication
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll - should work without cookies
    
    cookies_path = os.path.join(os.getcwd(), 'cookies', 'youtube.txt')
    
    print(f"Testing YouTube cookie authentication...")
    print(f"Cookies file path: {cookies_path}")
    print(f"Cookies file exists: {os.path.exists(cookies_path)}")
    
    # Test with cookies
    ydl_opts_with_cookies = {
        'quiet': True,
        'simulate': True,
        'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
        'extractor_retries': 3,
        'fragment_retries': 3,
    }
    
    try:
        print("\n=== Testing with cookies ===")
        with YoutubeDL(ydl_opts_with_cookies) as ydl:
            info = ydl.extract_info(test_url, download=False)
            print(f"✅ Success with cookies!")
            print(f"Title: {info.get('title', 'N/A')}")
            print(f"Duration: {info.get('duration', 'N/A')} seconds")
            print(f"Available formats: {len(info.get('formats', []))}")
            
    except Exception as e:
        print(f"❌ Failed with cookies: {e}")
        
        # Test without cookies as fallback
        try:
            print("\n=== Testing without cookies (fallback) ===")
            ydl_opts_no_cookies = {
                'quiet': True,
                'simulate': True,
                'extractor_retries': 2,
            }
            
            with YoutubeDL(ydl_opts_no_cookies) as ydl:
                info = ydl.extract_info(test_url, download=False)
                print(f"✅ Success without cookies!")
                print(f"Title: {info.get('title', 'N/A')}")
                print(f"Duration: {info.get('duration', 'N/A')} seconds")
                
        except Exception as fallback_error:
            print(f"❌ Also failed without cookies: {fallback_error}")

if __name__ == "__main__":
    test_youtube_cookies()