#!/usr/bin/env python3
"""
Emergency YouTube Downloader
Bypasses DNS resolution issues by using direct IP addresses
"""

import os
import sys
import socket
import ssl
import urllib3
import requests
import yt_dlp
from typing import Dict, Optional, List
import json
import time
import asyncio
from urllib.parse import urlparse, urlunparse
import logging

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class EmergencyYouTubeDownloader:
    def __init__(self):
        self.setup_environment()
        self.setup_logging()
        self.ip_mappings = self.get_youtube_ip_mappings()
        self.setup_dns_bypass()
        
    def setup_environment(self):
        """Setup emergency environment variables"""
        os.environ['PYTHONHTTPSVERIFY'] = '0'
        os.environ['CURL_CA_BUNDLE'] = ''
        os.environ['REQUESTS_CA_BUNDLE'] = ''
        os.environ['SSL_VERIFY'] = 'false'
        os.environ['SOCKET_TIMEOUT'] = '300'
        os.environ['CONNECT_TIMEOUT'] = '120'
        os.environ['READ_TIMEOUT'] = '600'
        os.environ['PYTHONUNBUFFERED'] = '1'
        os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
        os.environ['RES_OPTIONS'] = 'timeout:2 attempts:5 rotate single-request-reopen'
        os.environ['FORCE_IPV4'] = '1'
        
        # Set socket timeout
        socket.setdefaulttimeout(300)
        
    def setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def get_youtube_ip_mappings(self) -> Dict[str, str]:
        """Get known YouTube IP addresses"""
        return {
            'youtube.com': '142.250.191.14',
            'www.youtube.com': '142.250.191.14',
            'm.youtube.com': '142.250.191.14',
            'youtubei.googleapis.com': '172.217.16.110',
            'www.googleapis.com': '172.217.16.110',
            'googlevideo.com': '216.58.194.174',
            'r1---sn-4g5e6nls.googlevideo.com': '216.58.194.174',
            'r2---sn-4g5e6nls.googlevideo.com': '216.58.194.174',
            'r3---sn-4g5e6nls.googlevideo.com': '216.58.194.174',
            'r4---sn-4g5e6nls.googlevideo.com': '216.58.194.174',
            'r5---sn-4g5e6nls.googlevideo.com': '216.58.194.174',
            'r6---sn-4g5e6nls.googlevideo.com': '216.58.194.174',
        }
        
    def setup_dns_bypass(self):
        """Setup DNS bypass using direct IP mapping"""
        original_getaddrinfo = socket.getaddrinfo
        
        def custom_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
            # Check if we have a direct IP mapping
            if host in self.ip_mappings:
                ip = self.ip_mappings[host]
                self.logger.info(f"DNS Bypass: {host} -> {ip}")
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, port))]
            
            # Try multiple DNS servers
            dns_servers = ['8.8.8.8', '1.1.1.1', '208.67.222.222', '9.9.9.9']
            
            for dns_server in dns_servers:
                try:
                    # Use custom DNS resolution
                    result = self.resolve_with_dns(host, dns_server)
                    if result:
                        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (result, port))]
                except Exception as e:
                    self.logger.warning(f"DNS resolution failed for {host} via {dns_server}: {e}")
                    continue
            
            # Fallback to original
            try:
                return original_getaddrinfo(host, port, family, type, proto, flags)
            except Exception as e:
                self.logger.error(f"All DNS resolution methods failed for {host}: {e}")
                raise
        
        socket.getaddrinfo = custom_getaddrinfo
        
    def resolve_with_dns(self, hostname: str, dns_server: str) -> Optional[str]:
        """Resolve hostname using specific DNS server"""
        try:
            import dns.resolver
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [dns_server]
            resolver.timeout = 5
            resolver.lifetime = 10
            
            answers = resolver.resolve(hostname, 'A')
            return str(answers[0])
        except:
            # Fallback to system resolution
            try:
                return socket.gethostbyname(hostname)
            except:
                return None
                
    def get_emergency_ydl_opts(self) -> Dict:
        """Get emergency yt-dlp options with maximum resilience"""
        return {
            'format': 'best[height<=720]/best',
            'outtmpl': 'Downloads/%(title)s.%(ext)s',
            'socket_timeout': 300,
            'retries': 20,
            'fragment_retries': 20,
            'extractor_retries': 10,
            'file_access_retries': 5,
            'sleep_interval': 1,
            'max_sleep_interval': 5,
            'ignoreerrors': False,
            'no_warnings': False,
            'extractaudio': False,
            'audioformat': 'mp3',
            'embed_subs': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en', 'fa'],
            'concurrent_fragment_downloads': 1,  # Reduced for stability
            'http_chunk_size': 1048576,  # 1MB chunks
            'buffersize': 1024,
            'noresizebuffer': True,
            'continuedl': True,
            'nopart': False,
            'updatetime': True,
            'keepvideo': True,
            'prefer_insecure': True,
            'nocheckcertificate': True,
            'no_check_certificate': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            },
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_client': ['android', 'web'],
                    'player_skip': ['configs'],
                    'comment_sort': ['top'],
                    'max_comments': ['100'],
                }
            }
        }
        
    async def test_connection(self, url: str) -> bool:
        """Test connection to YouTube"""
        try:
            self.logger.info("Testing connection to YouTube...")
            
            # Test DNS resolution
            test_hosts = ['youtube.com', 'www.youtube.com', 'googlevideo.com']
            for host in test_hosts:
                try:
                    ip = socket.gethostbyname(host)
                    self.logger.info(f"✓ {host} resolves to {ip}")
                except Exception as e:
                    self.logger.warning(f"✗ {host} resolution failed: {e}")
            
            # Test yt-dlp extraction
            ydl_opts = self.get_emergency_ydl_opts()
            ydl_opts['quiet'] = True
            ydl_opts['no_warnings'] = True
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    self.logger.info(f"✓ Successfully extracted info for: {info.get('title', 'Unknown')}")
                    return True
                    
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
            
        return False
        
    async def get_video_info(self, url: str) -> Optional[Dict]:
        """Get video information with emergency settings"""
        try:
            self.logger.info(f"Extracting video info from: {url}")
            
            ydl_opts = self.get_emergency_ydl_opts()
            ydl_opts['quiet'] = True
            ydl_opts['no_warnings'] = True
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if info:
                    return {
                        'title': info.get('title', 'Unknown'),
                        'duration': info.get('duration', 0),
                        'view_count': info.get('view_count', 0),
                        'uploader': info.get('uploader', 'Unknown'),
                        'upload_date': info.get('upload_date', 'Unknown'),
                        'formats': info.get('formats', []),
                        'url': url
                    }
                    
        except Exception as e:
            self.logger.error(f"Failed to extract video info: {e}")
            return None
            
    def get_available_qualities(self, video_info: Dict) -> List[str]:
        """Get available video qualities"""
        if not video_info or 'formats' not in video_info:
            return ['720p']  # Default fallback
            
        qualities = set()
        for fmt in video_info['formats']:
            height = fmt.get('height')
            if height:
                if height >= 1080:
                    qualities.add('1080p')
                elif height >= 720:
                    qualities.add('720p')
                elif height >= 480:
                    qualities.add('480p')
                elif height >= 360:
                    qualities.add('360p')
                else:
                    qualities.add('240p')
                    
        return sorted(list(qualities), key=lambda x: int(x[:-1]), reverse=True)
        
    async def download_video(self, url: str, quality: str = '720p') -> bool:
        """Download video with emergency settings"""
        try:
            self.logger.info(f"Starting download: {url} at {quality}")
            
            # Create downloads directory
            os.makedirs('Downloads', exist_ok=True)
            
            ydl_opts = self.get_emergency_ydl_opts()
            
            # Set quality format
            if quality == '1080p':
                ydl_opts['format'] = 'best[height<=1080]/best'
            elif quality == '720p':
                ydl_opts['format'] = 'best[height<=720]/best'
            elif quality == '480p':
                ydl_opts['format'] = 'best[height<=480]/best'
            elif quality == '360p':
                ydl_opts['format'] = 'best[height<=360]/best'
            else:
                ydl_opts['format'] = 'best'
                
            # Progress hook
            def progress_hook(d):
                if d['status'] == 'downloading':
                    percent = d.get('_percent_str', 'N/A')
                    speed = d.get('_speed_str', 'N/A')
                    print(f"\rDownloading... {percent} at {speed}", end='', flush=True)
                elif d['status'] == 'finished':
                    print(f"\n✓ Download completed: {d['filename']}")
                    
            ydl_opts['progress_hooks'] = [progress_hook]
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
            self.logger.info("Download completed successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            return False
            
    def run_interactive_mode(self):
        """Run interactive mode"""
        print("🚨 Emergency YouTube Downloader")
        print("================================")
        print("This downloader bypasses DNS issues using direct IP addresses")
        print()
        
        while True:
            print("\nOptions:")
            print("1. Test connection")
            print("2. Download video")
            print("3. Exit")
            
            choice = input("\nEnter your choice (1-3): ").strip()
            
            if choice == '1':
                url = input("Enter YouTube URL to test: ").strip()
                if url:
                    result = asyncio.run(self.test_connection(url))
                    if result:
                        print("✓ Connection test passed!")
                    else:
                        print("✗ Connection test failed!")
                        
            elif choice == '2':
                url = input("Enter YouTube URL: ").strip()
                if url:
                    # Get video info first
                    info = asyncio.run(self.get_video_info(url))
                    if info:
                        print(f"\nVideo: {info['title']}")
                        print(f"Uploader: {info['uploader']}")
                        
                        qualities = self.get_available_qualities(info)
                        print(f"Available qualities: {', '.join(qualities)}")
                        
                        quality = input(f"Enter quality (default: 720p): ").strip() or '720p'
                        
                        success = asyncio.run(self.download_video(url, quality))
                        if success:
                            print("✓ Download completed!")
                        else:
                            print("✗ Download failed!")
                    else:
                        print("✗ Failed to get video information!")
                        
            elif choice == '3':
                print("Goodbye!")
                break
            else:
                print("Invalid choice!")

def main():
    """Main function"""
    downloader = EmergencyYouTubeDownloader()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'test':
            url = sys.argv[2] if len(sys.argv) > 2 else "https://www.youtube.com/watch?v=dL_r_PPlFtI"
            result = asyncio.run(downloader.test_connection(url))
            sys.exit(0 if result else 1)
            
        elif command == 'download':
            if len(sys.argv) < 3:
                print("Usage: python emergency_youtube_downloader.py download <URL> [quality]")
                sys.exit(1)
                
            url = sys.argv[2]
            quality = sys.argv[3] if len(sys.argv) > 3 else '720p'
            
            success = asyncio.run(downloader.download_video(url, quality))
            sys.exit(0 if success else 1)
            
        elif command == 'info':
            if len(sys.argv) < 3:
                print("Usage: python emergency_youtube_downloader.py info <URL>")
                sys.exit(1)
                
            url = sys.argv[2]
            info = asyncio.run(downloader.get_video_info(url))
            
            if info:
                print(json.dumps(info, indent=2, ensure_ascii=False))
            else:
                print("Failed to get video information")
                sys.exit(1)
        else:
            print("Unknown command. Use: test, download, info, or run without arguments for interactive mode")
            sys.exit(1)
    else:
        # Interactive mode
        downloader.run_interactive_mode()

if __name__ == "__main__":
    main()