#!/usr/bin/env python3
"""
Test script for YouTube proxy rotation fallback functionality
"""

import os
import sys
import asyncio
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('./logs/test_proxy_fallback.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# Import the proxy rotation functions
from plugins.youtube_proxy_rotator import extract_with_rotation, download_with_rotation

async def test_problematic_link():
    """Test the problematic YouTube link cgzAu5NUVkw"""
    
    # Test URL - using a more common video
    test_url = "https://www.youtube.com/watch?v=cgzAu5NUVkw"  # Original problematic link
    
    logger.info(f"Testing problematic link: {test_url}")
    logger.info("=" * 60)
    
    # Define ydl_opts similar to the main code
    ydl_opts = {
        'quiet': True,
        'simulate': True,
        'extractor_retries': 0,
        'fragment_retries': 0,
        'socket_timeout': 8,
        'connect_timeout': 5,
        'no_warnings': True,
        'extract_flat': False,

        'ignoreerrors': True,
        'no_check_certificate': True,
        'prefer_insecure': True,
        'youtube_include_dash_manifest': False,
        'writesubtitles': False,
        'writeautomaticsub': False,
        'writethumbnail': False,
        'writeinfojson': False,
        'extractor_args': {
            'youtube': {
                'player_client': ['android']
            }
        },
    }
    
    try:
        # Test extraction with rotation
        logger.info("Testing extract_with_rotation...")
        result = await extract_with_rotation(test_url, ydl_opts, cookiefile=None, max_attempts=3)
        
        if result:
            logger.info("✅ Extract with rotation succeeded!")
            logger.info(f"Title: {result.get('title', 'Unknown')}")
            logger.info(f"Duration: {result.get('duration', 'Unknown')}")
            logger.info(f"Uploader: {result.get('uploader', 'Unknown')}")
            
            # Test download with rotation (need to modify ydl_opts for download)
            download_opts = ydl_opts.copy()
            download_opts['simulate'] = False
            download_opts['outtmpl'] = './downloads/%(title)s.%(ext)s'
            
            logger.info("\nTesting download_with_rotation...")
            download_result = await download_with_rotation(test_url, download_opts, cookiefile=None, max_attempts=3)
            
            if download_result:
                logger.info("✅ Download with rotation succeeded!")
                logger.info(f"Downloaded file: {download_result}")
            else:
                logger.error("❌ Download with rotation failed!")
                
        else:
            logger.error("❌ Extract with rotation failed!")
            
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        import traceback
        logger.error(traceback.format_exc())

async def main():
    """Main test function"""
    logger.info("Starting YouTube Proxy Fallback Test")
    logger.info("=" * 60)
    
    # Ensure logs directory exists
    os.makedirs('./logs', exist_ok=True)
    
    # Set proxy rotation environment variable
    os.environ['YOUTUBE_PROXY_ROTATION'] = '1'
    logger.info("✅ Proxy rotation enabled")
    
    # Run the test
    await test_problematic_link()
    
    logger.info("=" * 60)
    logger.info("Test completed!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Test stopped by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)