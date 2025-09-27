#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست جامع نهایی سیستم دانلود یوتیوب
Final Integration Test for YouTube Downloader System
"""

import os
import sys
import json
import asyncio
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plugins.youtube_advanced_downloader import YouTubeAdvancedDownloader
from plugins.youtube_quality_selector import YouTubeQualitySelector
from plugins.logger_config import get_logger

# Initialize logger
advanced_logger = get_logger('final_integration_test')

class FinalIntegrationTest:
    def __init__(self):
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'test_name': 'Final Integration Test',
            'version': '1.0',
            'tests': {},
            'summary': {
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'success_rate': 0.0
            }
        }
        self.temp_dir = None
        self.downloader = None
        self.selector = None
        
    def log_test(self, test_name: str, status: str, details: dict = None):
        """ثبت نتیجه تست"""
        self.test_results['tests'][test_name] = {
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        
        if status == 'PASS':
            self.test_results['summary']['passed'] += 1
            print(f"  ✅ {test_name}")
        else:
            self.test_results['summary']['failed'] += 1
            print(f"  ❌ {test_name}")
            if details:
                print(f"     Error: {details.get('error', 'Unknown error')}")
        
        self.test_results['summary']['total_tests'] += 1
    
    async def setup_test_environment(self):
        """راه‌اندازی محیط تست"""
        print("🔧 راه‌اندازی محیط تست...")
        
        try:
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp(prefix='youtube_test_')
            print(f"  📁 دایرکتوری موقت: {self.temp_dir}")
            
            # Initialize components
            self.downloader = YouTubeAdvancedDownloader()
            self.selector = YouTubeQualitySelector()
            
            # Verify tools availability
            tools_available = True
            for tool in ['ffmpeg', 'ffprobe', 'yt-dlp']:
                if not shutil.which(tool):
                    tools_available = False
                    break
            
            if not tools_available:
                raise Exception("Required tools not available")
            
            self.log_test("Environment Setup", "PASS", {
                'temp_dir': self.temp_dir,
                'tools_available': True
            })
            
        except Exception as e:
            self.log_test("Environment Setup", "FAIL", {'error': str(e)})
            raise
    
    async def test_component_initialization(self):
        """تست مقداردهی اجزای سیستم"""
        print("\n🔍 تست مقداردهی اجزای سیستم...")
        
        try:
            # Test downloader initialization
            assert hasattr(self.downloader, 'ffmpeg_path'), "ffmpeg_path not set"
            assert hasattr(self.downloader, 'cookies_file'), "cookies_file not set"
            assert hasattr(self.downloader, 'get_file_metadata'), "get_file_metadata method missing"
            assert hasattr(self.downloader, 'download_and_merge'), "download_and_merge method missing"
            
            self.log_test("Downloader Initialization", "PASS", {
                'ffmpeg_path': getattr(self.downloader, 'ffmpeg_path', None),
                'cookies_file': getattr(self.downloader, 'cookies_file', None)
            })
            
        except Exception as e:
            self.log_test("Downloader Initialization", "FAIL", {'error': str(e)})
        
        try:
            # Test selector initialization
            assert hasattr(self.selector, 'get_available_qualities'), "get_available_qualities method missing"
            assert hasattr(self.selector, 'format_quality_info'), "format_quality_info method missing"
            
            self.log_test("Selector Initialization", "PASS")
            
        except Exception as e:
            self.log_test("Selector Initialization", "FAIL", {'error': str(e)})
    
    async def test_file_operations(self):
        """تست عملیات فایل"""
        print("\n📁 تست عملیات فایل...")
        
        try:
            # Create test video file
            test_file = os.path.join(self.temp_dir, 'test_video.mp4')
            
            # Create a simple test video using ffmpeg
            cmd = [
                'ffmpeg', '-f', 'lavfi', '-i', 'testsrc=duration=5:size=640x480:rate=1',
                '-f', 'lavfi', '-i', 'sine=frequency=1000:duration=5',
                '-c:v', 'libx264', '-c:a', 'aac', '-t', '5',
                '-y', test_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if not os.path.exists(test_file):
                raise Exception("Test file creation failed")
            
            # Test metadata extraction
            metadata = await self.downloader.get_file_metadata(test_file)
            if not metadata:
                raise Exception("Metadata extraction failed")
            
            # Test file integrity
            integrity_ok = self.downloader._verify_file_integrity(test_file)
            if not integrity_ok:
                raise Exception("File integrity check failed")
            
            # Test stream probing
            ffprobe_path = shutil.which('ffprobe') or 'ffprobe'
            streams = self.downloader._probe_file_streams(test_file, ffprobe_path)
            if not streams:
                raise Exception("Stream probing failed")
            
            self.log_test("File Operations", "PASS", {
                'file_size': os.path.getsize(test_file),
                'metadata_keys': list(metadata.keys()) if metadata else [],
                'has_video': streams.get('has_video', False) if streams else False,
                'has_audio': streams.get('has_audio', False) if streams else False
            })
            
        except Exception as e:
            self.log_test("File Operations", "FAIL", {'error': str(e)})
    
    async def test_quality_selection(self):
        """تست انتخاب کیفیت"""
        print("\n🎥 تست انتخاب کیفیت...")
        
        try:
            # Test with a sample URL (we'll mock this for testing)
            test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll for testing
            
            # Test quality options retrieval (this might fail due to network/API limits)
            try:
                quality_options = await self.selector.get_quality_options(test_url)
                if quality_options:
                    self.log_test("Quality Selection - Real URL", "PASS", {
                        'options_count': len(quality_options),
                        'sample_option': quality_options[0] if quality_options else None
                    })
                else:
                    # This is expected in testing environment
                    self.log_test("Quality Selection - Real URL", "SKIP", {
                        'reason': 'No network access or API limits'
                    })
            except Exception as e:
                self.log_test("Quality Selection - Real URL", "SKIP", {
                    'reason': f'Network/API error: {str(e)}'
                })
            
            # Test quality formatting
            mock_quality = {
                'format_id': '137',
                'ext': 'mp4',
                'height': 1080,
                'fps': 30,
                'vcodec': 'avc1',
                'acodec': 'none',
                'filesize': 50000000
            }
            
            formatted = self.selector.format_quality_info(mock_quality)
            if not formatted:
                raise Exception("Quality formatting failed")
            
            self.log_test("Quality Formatting", "PASS", {
                'formatted_text': formatted[:100] + "..." if len(formatted) > 100 else formatted
            })
            
        except Exception as e:
            self.log_test("Quality Selection", "FAIL", {'error': str(e)})
    
    async def test_error_handling(self):
        """تست مدیریت خطاها"""
        print("\n⚠️ تست مدیریت خطاها...")
        
        try:
            # Test with non-existent file
            fake_file = os.path.join(self.temp_dir, 'non_existent.mp4')
            
            # These should handle errors gracefully
            metadata = await self.downloader.get_file_metadata(fake_file)
            integrity = self.downloader._verify_file_integrity(fake_file)
            ffprobe_path = shutil.which('ffprobe') or 'ffprobe'
            streams = self.downloader._probe_file_streams(fake_file, ffprobe_path)
            
            # All should return None/False for non-existent file
            if (metadata == {} or metadata is None) and not integrity and streams == {}:
                self.log_test("Error Handling - Non-existent File", "PASS")
            else:
                raise Exception(f"Error handling failed for non-existent file: metadata={metadata}, integrity={integrity}, streams={streams}")
            
            # Test with invalid URL
            try:
                invalid_url = "not_a_valid_url"
                quality_options = await self.selector.get_quality_options(invalid_url)
                # Should return empty list or None
                if not quality_options:
                    self.log_test("Error Handling - Invalid URL", "PASS")
                else:
                    self.log_test("Error Handling - Invalid URL", "FAIL", {
                        'error': 'Should return empty for invalid URL'
                    })
            except Exception:
                # Exception is also acceptable for invalid URL
                self.log_test("Error Handling - Invalid URL", "PASS")
            
            # Test utility functions
            from utils.util import convert_size
            size_check = convert_size(1, 1024*1024*100)  # 100MB
            size_format = convert_size(2, 1024*1024*100)  # 100MB
            
        except Exception as e:
            self.log_test("Error Handling", "FAIL", {'error': str(e)})
    
    async def test_performance_metrics(self):
        """تست معیارهای عملکرد"""
        print("\n⚡ تست معیارهای عملکرد...")
        
        try:
            import time
            
            # Create test file
            test_file = os.path.join(self.temp_dir, 'perf_test.mp4')
            cmd = [
                'ffmpeg', '-f', 'lavfi', '-i', 'testsrc=duration=3:size=320x240:rate=1',
                '-f', 'lavfi', '-i', 'sine=frequency=500:duration=3',
                '-c:v', 'libx264', '-c:a', 'aac', '-t', '3',
                '-y', test_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if not os.path.exists(test_file):
                raise Exception("Performance test file creation failed")
            
            # Measure metadata extraction time
            start_time = time.time()
            metadata = await self.downloader.get_file_metadata(test_file)
            metadata_time = time.time() - start_time
            
            # Measure integrity check time
            start_time = time.time()
            integrity = self.downloader._verify_file_integrity(test_file)
            integrity_time = time.time() - start_time
            
            # Measure stream probing time
            start_time = time.time()
            ffprobe_path = shutil.which('ffprobe') or 'ffprobe'
            streams = self.downloader._probe_file_streams(test_file, ffprobe_path)
            streams_time = time.time() - start_time
            
            self.log_test("Performance Metrics", "PASS", {
                'metadata_extraction_time': round(metadata_time, 3),
                'integrity_check_time': round(integrity_time, 3),
                'stream_probing_time': round(streams_time, 3),
                'file_size': os.path.getsize(test_file)
            })
            
        except Exception as e:
            self.log_test("Performance Metrics", "FAIL", {'error': str(e)})
    
    async def cleanup_test_environment(self):
        """پاک‌سازی محیط تست"""
        print("\n🗑️ پاک‌سازی محیط تست...")
        
        try:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                print(f"  ✅ دایرکتوری موقت پاک شد: {self.temp_dir}")
            
            self.log_test("Cleanup", "PASS")
            
        except Exception as e:
            self.log_test("Cleanup", "FAIL", {'error': str(e)})
    
    async def run_all_tests(self):
        """اجرای تمام تست‌ها"""
        print("🚀 شروع تست جامع نهایی سیستم...")
        print("=" * 50)
        
        try:
            await self.setup_test_environment()
            await self.test_component_initialization()
            await self.test_file_operations()
            await self.test_quality_selection()
            await self.test_error_handling()
            await self.test_performance_metrics()
            
        finally:
            await self.cleanup_test_environment()
        
        # Calculate success rate
        total = self.test_results['summary']['total_tests']
        passed = self.test_results['summary']['passed']
        if total > 0:
            self.test_results['summary']['success_rate'] = (passed / total) * 100
        
        # Save results
        results_file = 'final_integration_test_results.json'
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 خلاصه نتایج تست جامع:")
        print("=" * 50)
        print(f"📈 تعداد کل تست‌ها: {total}")
        print(f"✅ تست‌های موفق: {passed}")
        print(f"❌ تست‌های ناموفق: {self.test_results['summary']['failed']}")
        print(f"📊 نرخ موفقیت: {self.test_results['summary']['success_rate']:.1f}%")
        print(f"💾 نتایج در {results_file} ذخیره شد")
        
        if self.test_results['summary']['success_rate'] >= 80:
            print("\n🎉 تست جامع نهایی موفقیت‌آمیز!")
            return True
        else:
            print("\n⚠️ تست جامع نهایی نیاز به بهبود دارد")
            return False

async def main():
    """تابع اصلی"""
    test_runner = FinalIntegrationTest()
    success = await test_runner.run_all_tests()
    
    if success:
        print("\n✅ سیستم آماده استفاده است")
        sys.exit(0)
    else:
        print("\n❌ سیستم نیاز به اصلاح دارد")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())