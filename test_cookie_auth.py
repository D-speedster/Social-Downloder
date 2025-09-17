import os
from yt_dlp import YoutubeDL

def test_cookie_authentication():
    # Test URL - this should be a video that requires authentication
    test_url = "https://www.youtube.com/watch?v=XBJ5qRoBSeg"
    
    # Path to cookies file
    cookies_path = os.path.join(os.getcwd(), 'cookies', 'youtube.txt')
    
    print(f"Cookies file exists: {os.path.exists(cookies_path)}")
    
    # Test with cookies
    print("\n=== Testing with cookies ===\n")
    ydl_opts_with_cookies = {
        'quiet': True,
        'simulate': True,
        'cookiefile': cookies_path,
        'extractor_retries': 3,
        'fragment_retries': 3,
        'retry_sleep_functions': {'http': lambda n: min(4 ** n, 60)}
    }
    
    try:
        with YoutubeDL(ydl_opts_with_cookies) as ydl:
            info = ydl.extract_info(test_url, download=False)
            print(f"Title: {info.get('title')}")
            print(f"Duration: {info.get('duration')} seconds")
            print(f"Available formats: {len(info.get('formats', []))}")
            print("Authentication with cookies: SUCCESS")
    except Exception as e:
        print(f"Authentication with cookies failed: {e}")
    
    # Test without cookies
    print("\n=== Testing without cookies ===\n")
    ydl_opts_without_cookies = {
        'quiet': True,
        'simulate': True,
        'extractor_retries': 3,
        'fragment_retries': 3
    }
    
    try:
        with YoutubeDL(ydl_opts_without_cookies) as ydl:
            info = ydl.extract_info(test_url, download=False)
            print(f"Title: {info.get('title')}")
            print(f"Duration: {info.get('duration')} seconds")
            print(f"Available formats: {len(info.get('formats', []))}")
            print("Authentication without cookies: SUCCESS (video might not require authentication)")
    except Exception as e:
        print(f"Authentication without cookies failed: {e}")
        print("This is expected if the video requires authentication")

if __name__ == "__main__":
    test_cookie_authentication()