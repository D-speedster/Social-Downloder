#!/usr/bin/env python3
import yt_dlp
import os

def test_ytdlp_config():
    """Test yt-dlp with the same configuration as the bot"""
    
    # Same configuration as the bot
    ydl_opts = {
        'quiet': False,  # Changed to False to see all output
        'no_warnings': False,  # Changed to False to see warnings
        'extract_flat': False,
        'ignoreerrors': False,
        'no_check_certificate': True,
        'socket_timeout': 15,
        'connect_timeout': 10,
    }
    
    # Add cookie file if it exists
    if os.path.exists('cookie_youtube.txt'):
        ydl_opts['cookiefile'] = 'cookie_youtube.txt'
        print("Using cookie file: cookie_youtube.txt")
    else:
        print("No cookie file found")
    
    # Check for proxy environment variables
    env_proxy = os.environ.get('PROXY') or os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')
    if env_proxy:
        ydl_opts['proxy'] = env_proxy
        print(f"Using proxy: {env_proxy}")
    else:
        print("No proxy configured")
    
    # Test URL
    url = "https://youtube.com/watch?v=dL_r_PPlFtI"
    
    print(f"Testing URL: {url}")
    print(f"yt-dlp options: {ydl_opts}")
    print("-" * 50)
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print(f"Success! Title: {info.get('title', 'N/A')}")
            return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_ytdlp_config()