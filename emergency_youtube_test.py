#!/usr/bin/env python3
"""
Emergency YouTube Test Script
Tests all DNS resolution methods and YouTube connectivity
"""

import os
import sys
import socket
import time
import subprocess
import requests
import urllib3
from typing import Dict, List, Tuple
import json
import asyncio
import logging

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class EmergencyTester:
    def __init__(self):
        self.setup_logging()
        self.test_results = {}
        
    def setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def print_header(self, title: str):
        """Print formatted header"""
        print(f"\n{'='*60}")
        print(f"🔍 {title}")
        print(f"{'='*60}")
        
    def print_result(self, test_name: str, success: bool, details: str = ""):
        """Print test result"""
        status = "✓ PASS" if success else "✗ FAIL"
        color = "\033[92m" if success else "\033[91m"
        reset = "\033[0m"
        
        print(f"{color}{status}{reset} {test_name}")
        if details:
            print(f"      {details}")
            
        self.test_results[test_name] = {
            'success': success,
            'details': details,
            'timestamp': time.time()
        }
        
    def test_basic_connectivity(self) -> bool:
        """Test basic internet connectivity"""
        self.print_header("Basic Connectivity Tests")
        
        # Test ping to Google DNS
        try:
            result = subprocess.run(['ping', '-c', '2', '8.8.8.8'], 
                                  capture_output=True, text=True, timeout=10)
            success = result.returncode == 0
            self.print_result("Ping to 8.8.8.8", success, 
                            f"RTT: {self.extract_ping_time(result.stdout)}")
        except Exception as e:
            self.print_result("Ping to 8.8.8.8", False, str(e))
            
        # Test HTTP connectivity
        try:
            response = requests.get('http://httpbin.org/ip', timeout=10)
            success = response.status_code == 200
            self.print_result("HTTP connectivity", success, 
                            f"IP: {response.json().get('origin', 'Unknown')}")
        except Exception as e:
            self.print_result("HTTP connectivity", False, str(e))
            
        # Test HTTPS connectivity
        try:
            response = requests.get('https://httpbin.org/ip', timeout=10, verify=False)
            success = response.status_code == 200
            self.print_result("HTTPS connectivity", success, 
                            f"Status: {response.status_code}")
        except Exception as e:
            self.print_result("HTTPS connectivity", False, str(e))
            
        return True
        
    def extract_ping_time(self, ping_output: str) -> str:
        """Extract ping time from ping output"""
        try:
            lines = ping_output.split('\n')
            for line in lines:
                if 'time=' in line:
                    return line.split('time=')[1].split()[0]
        except:
            pass
        return "N/A"
        
    def test_dns_resolution(self) -> bool:
        """Test DNS resolution with multiple servers"""
        self.print_header("DNS Resolution Tests")
        
        test_domains = [
            'youtube.com',
            'www.youtube.com',
            'googlevideo.com',
            'googleapis.com'
        ]
        
        dns_servers = [
            ('System Default', None),
            ('Google DNS', '8.8.8.8'),
            ('Cloudflare DNS', '1.1.1.1'),
            ('OpenDNS', '208.67.222.222'),
            ('Quad9 DNS', '9.9.9.9')
        ]
        
        for domain in test_domains:
            print(f"\n🌐 Testing {domain}:")
            
            for dns_name, dns_ip in dns_servers:
                try:
                    if dns_ip:
                        # Use nslookup for specific DNS server
                        result = subprocess.run(['nslookup', domain, dns_ip], 
                                              capture_output=True, text=True, timeout=5)
                        success = result.returncode == 0 and 'NXDOMAIN' not in result.stdout
                        ip = self.extract_ip_from_nslookup(result.stdout)
                    else:
                        # Use system default
                        ip = socket.gethostbyname(domain)
                        success = bool(ip)
                        
                    self.print_result(f"  {dns_name}", success, f"IP: {ip}")
                    
                except Exception as e:
                    self.print_result(f"  {dns_name}", False, str(e))
                    
        return True
        
    def extract_ip_from_nslookup(self, output: str) -> str:
        """Extract IP from nslookup output"""
        try:
            lines = output.split('\n')
            for line in lines:
                if 'Address:' in line and '#' not in line:
                    return line.split('Address:')[1].strip()
        except:
            pass
        return "N/A"
        
    def test_youtube_specific(self) -> bool:
        """Test YouTube specific connectivity"""
        self.print_header("YouTube Connectivity Tests")
        
        youtube_endpoints = [
            ('YouTube Main', 'https://www.youtube.com'),
            ('YouTube API', 'https://www.googleapis.com/youtube/v3'),
            ('YouTube Video', 'https://www.youtube.com/watch?v=dL_r_PPlFtI'),
            ('YouTube Thumbnail', 'https://i.ytimg.com/vi/dL_r_PPlFtI/default.jpg')
        ]
        
        for name, url in youtube_endpoints:
            try:
                response = requests.get(url, timeout=15, verify=False, 
                                      allow_redirects=True)
                success = response.status_code in [200, 301, 302]
                self.print_result(name, success, 
                                f"Status: {response.status_code}, Size: {len(response.content)} bytes")
            except Exception as e:
                self.print_result(name, False, str(e))
                
        return True
        
    def test_yt_dlp_extraction(self) -> bool:
        """Test yt-dlp video extraction"""
        self.print_header("yt-dlp Extraction Tests")
        
        test_url = "https://www.youtube.com/watch?v=dL_r_PPlFtI"
        
        try:
            import yt_dlp
            
            # Test with minimal options
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 60,
                'retries': 3,
                'nocheckcertificate': True,
                'prefer_insecure': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(test_url, download=False)
                
                if info:
                    title = info.get('title', 'Unknown')
                    duration = info.get('duration', 0)
                    formats_count = len(info.get('formats', []))
                    
                    self.print_result("Video info extraction", True, 
                                    f"Title: {title[:50]}..., Duration: {duration}s, Formats: {formats_count}")
                    
                    # Test format availability
                    qualities = self.extract_qualities(info.get('formats', []))
                    self.print_result("Video formats", len(qualities) > 0, 
                                    f"Available: {', '.join(qualities)}")
                    
                    return True
                else:
                    self.print_result("Video info extraction", False, "No info returned")
                    
        except ImportError:
            self.print_result("yt-dlp import", False, "yt-dlp not installed")
        except Exception as e:
            self.print_result("Video info extraction", False, str(e))
            
        return False
        
    def extract_qualities(self, formats: List[Dict]) -> List[str]:
        """Extract available video qualities"""
        qualities = set()
        for fmt in formats:
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
                    
        return sorted(list(qualities), key=lambda x: int(x[:-1]), reverse=True)
        
    def test_emergency_downloader(self) -> bool:
        """Test emergency downloader"""
        self.print_header("Emergency Downloader Tests")
        
        try:
            # Import emergency downloader
            sys.path.append('.')
            from emergency_youtube_downloader import EmergencyYouTubeDownloader
            
            downloader = EmergencyYouTubeDownloader()
            
            # Test connection
            test_url = "https://www.youtube.com/watch?v=dL_r_PPlFtI"
            result = asyncio.run(downloader.test_connection(test_url))
            self.print_result("Emergency downloader connection", result)
            
            if result:
                # Test info extraction
                info = asyncio.run(downloader.get_video_info(test_url))
                success = info is not None
                details = f"Title: {info.get('title', 'Unknown')[:50]}..." if info else "No info"
                self.print_result("Emergency downloader info", success, details)
                
            return result
            
        except ImportError as e:
            self.print_result("Emergency downloader import", False, str(e))
        except Exception as e:
            self.print_result("Emergency downloader test", False, str(e))
            
        return False
        
    def test_system_configuration(self) -> bool:
        """Test system configuration"""
        self.print_header("System Configuration Tests")
        
        # Test resolv.conf
        try:
            with open('/etc/resolv.conf', 'r') as f:
                content = f.read()
                dns_servers = [line.split()[1] for line in content.split('\n') 
                             if line.strip().startswith('nameserver')]
                self.print_result("DNS configuration", len(dns_servers) > 0, 
                                f"Servers: {', '.join(dns_servers)}")
        except Exception as e:
            self.print_result("DNS configuration", False, str(e))
            
        # Test network parameters
        network_params = [
            ('/proc/sys/net/ipv4/tcp_keepalive_time', 'TCP keepalive time'),
            ('/proc/sys/net/core/rmem_max', 'Max receive buffer'),
            ('/proc/sys/net/core/wmem_max', 'Max send buffer')
        ]
        
        for param_file, param_name in network_params:
            try:
                with open(param_file, 'r') as f:
                    value = f.read().strip()
                    self.print_result(param_name, True, f"Value: {value}")
            except Exception as e:
                self.print_result(param_name, False, str(e))
                
        return True
        
    def generate_report(self):
        """Generate test report"""
        self.print_header("Test Summary Report")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for test_name, result in self.test_results.items():
                if not result['success']:
                    print(f"   • {test_name}: {result['details']}")
                    
        # Save detailed report
        report_file = f"emergency_test_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
            
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        return passed_tests == total_tests
        
    def run_all_tests(self) -> bool:
        """Run all tests"""
        print("🚨 Emergency YouTube Downloader Test Suite")
        print("=" * 60)
        
        tests = [
            self.test_basic_connectivity,
            self.test_dns_resolution,
            self.test_youtube_specific,
            self.test_yt_dlp_extraction,
            self.test_emergency_downloader,
            self.test_system_configuration
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                self.logger.error(f"Test failed with exception: {e}")
                
        return self.generate_report()

def main():
    """Main function"""
    tester = EmergencyTester()
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == 'connectivity':
            tester.test_basic_connectivity()
        elif test_type == 'dns':
            tester.test_dns_resolution()
        elif test_type == 'youtube':
            tester.test_youtube_specific()
        elif test_type == 'yt-dlp':
            tester.test_yt_dlp_extraction()
        elif test_type == 'emergency':
            tester.test_emergency_downloader()
        elif test_type == 'system':
            tester.test_system_configuration()
        else:
            print("Available tests: connectivity, dns, youtube, yt-dlp, emergency, system")
            sys.exit(1)
    else:
        # Run all tests
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()