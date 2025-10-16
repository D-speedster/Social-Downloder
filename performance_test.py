#!/usr/bin/env python3
"""
Performance Test Script for Universal Downloader Optimizations
Tests download and upload performance with different file sizes and types
"""

import asyncio
import time
import os
import sys
import aiohttp
import tempfile
from typing import Dict, List, Tuple
import json
from datetime import datetime

# Add plugins directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'plugins'))

from stream_utils import download_to_memory_stream, download_with_progress_callback, smart_upload_strategy
from media_utils import download_file_simple

class PerformanceTest:
    def __init__(self):
        self.results = []
        self.test_urls = {
            'small_image': 'https://picsum.photos/800/600.jpg',  # ~100KB
            'medium_image': 'https://picsum.photos/2000/1500.jpg',  # ~1MB
            'large_image': 'https://picsum.photos/4000/3000.jpg',  # ~5MB
            'small_video': 'https://sample-videos.com/zip/10/mp4/SampleVideo_360x240_1mb.mp4',  # 1MB
            'medium_video': 'https://sample-videos.com/zip/10/mp4/SampleVideo_720x480_5mb.mp4',  # 5MB
        }
        
    async def test_download_methods(self, url: str, file_type: str, size_category: str) -> Dict:
        """Test different download methods and measure performance"""
        results = {
            'url': url,
            'file_type': file_type,
            'size_category': size_category,
            'timestamp': datetime.now().isoformat(),
            'methods': {}
        }
        
        # Test 1: Memory streaming (for small files)
        if size_category in ['small', 'medium']:
            try:
                start_time = time.perf_counter()
                memory_stream = await download_to_memory_stream(url, max_size_mb=10)
                end_time = time.perf_counter()
                
                if memory_stream:
                    file_size = memory_stream.tell()
                    memory_stream.close()
                    results['methods']['memory_stream'] = {
                        'success': True,
                        'duration': end_time - start_time,
                        'file_size': file_size,
                        'speed_mbps': (file_size / (1024 * 1024)) / (end_time - start_time) if end_time > start_time else 0
                    }
                else:
                    results['methods']['memory_stream'] = {
                        'success': False,
                        'reason': 'File too large or download failed'
                    }
            except Exception as e:
                results['methods']['memory_stream'] = {
                    'success': False,
                    'error': str(e)
                }
        
        # Test 2: File download with progress
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as tmp_file:
                temp_path = tmp_file.name
            
            start_time = time.perf_counter()
            await download_with_progress_callback(url, temp_path)
            end_time = time.perf_counter()
            
            if os.path.exists(temp_path):
                file_size = os.path.getsize(temp_path)
                os.unlink(temp_path)  # Clean up
                results['methods']['file_download'] = {
                    'success': True,
                    'duration': end_time - start_time,
                    'file_size': file_size,
                    'speed_mbps': (file_size / (1024 * 1024)) / (end_time - start_time) if end_time > start_time else 0
                }
            else:
                results['methods']['file_download'] = {
                    'success': False,
                    'reason': 'File not created'
                }
        except Exception as e:
            results['methods']['file_download'] = {
                'success': False,
                'error': str(e)
            }
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
        
        # Test 3: Simple download (legacy method)
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as tmp_file:
                temp_path = tmp_file.name
            
            start_time = time.perf_counter()
            await download_file_simple(url, temp_path)
            end_time = time.perf_counter()
            
            if os.path.exists(temp_path):
                file_size = os.path.getsize(temp_path)
                os.unlink(temp_path)  # Clean up
                results['methods']['simple_download'] = {
                    'success': True,
                    'duration': end_time - start_time,
                    'file_size': file_size,
                    'speed_mbps': (file_size / (1024 * 1024)) / (end_time - start_time) if end_time > start_time else 0
                }
            else:
                results['methods']['simple_download'] = {
                    'success': False,
                    'reason': 'File not created'
                }
        except Exception as e:
            results['methods']['simple_download'] = {
                'success': False,
                'error': str(e)
            }
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
        
        return results
    
    async def test_retry_mechanisms(self, invalid_url: str) -> Dict:
        """Test retry mechanisms with invalid URLs"""
        results = {
            'test_type': 'retry_mechanism',
            'timestamp': datetime.now().isoformat(),
            'methods': {}
        }
        
        # Test memory stream retry
        try:
            start_time = time.perf_counter()
            memory_stream = await download_to_memory_stream(invalid_url, max_size_mb=1)
            end_time = time.perf_counter()
            
            results['methods']['memory_stream_retry'] = {
                'success': memory_stream is not None,
                'duration': end_time - start_time,
                'expected_failure': True
            }
        except Exception as e:
            results['methods']['memory_stream_retry'] = {
                'success': False,
                'duration': time.perf_counter() - start_time,
                'error': str(e),
                'expected_failure': True
            }
        
        return results
    
    async def run_comprehensive_test(self) -> Dict:
        """Run comprehensive performance tests"""
        print("🚀 Starting Performance Tests...")
        print("=" * 50)
        
        all_results = {
            'test_start': datetime.now().isoformat(),
            'download_tests': [],
            'retry_tests': [],
            'summary': {}
        }
        
        # Test download methods for different file types and sizes
        for test_name, url in self.test_urls.items():
            file_type = 'image' if 'image' in test_name else 'video'
            size_category = test_name.split('_')[0]  # small, medium, large
            
            print(f"\n📥 Testing {test_name} ({file_type}, {size_category})...")
            
            try:
                result = await self.test_download_methods(url, file_type, size_category)
                all_results['download_tests'].append(result)
                
                # Print immediate results
                for method, data in result['methods'].items():
                    if data.get('success'):
                        speed = data.get('speed_mbps', 0)
                        duration = data.get('duration', 0)
                        size_mb = data.get('file_size', 0) / (1024 * 1024)
                        print(f"  ✅ {method}: {duration:.2f}s, {size_mb:.2f}MB, {speed:.2f} MB/s")
                    else:
                        print(f"  ❌ {method}: {data.get('error', data.get('reason', 'Failed'))}")
                        
            except Exception as e:
                print(f"  ❌ Test failed: {e}")
        
        # Test retry mechanisms
        print(f"\n🔄 Testing retry mechanisms...")
        invalid_urls = [
            'https://invalid-domain-12345.com/file.jpg',
            'https://httpstat.us/500',  # Returns 500 error
            'https://httpstat.us/404'   # Returns 404 error
        ]
        
        for invalid_url in invalid_urls:
            try:
                retry_result = await self.test_retry_mechanisms(invalid_url)
                all_results['retry_tests'].append(retry_result)
            except Exception as e:
                print(f"  ❌ Retry test failed: {e}")
        
        # Generate summary
        all_results['summary'] = self.generate_summary(all_results)
        all_results['test_end'] = datetime.now().isoformat()
        
        return all_results
    
    def generate_summary(self, results: Dict) -> Dict:
        """Generate performance summary"""
        summary = {
            'total_tests': len(results['download_tests']),
            'successful_tests': 0,
            'average_speeds': {},
            'best_method_by_size': {},
            'recommendations': []
        }
        
        # Analyze download tests
        method_speeds = {}
        size_performance = {}
        
        for test in results['download_tests']:
            size_cat = test['size_category']
            if size_cat not in size_performance:
                size_performance[size_cat] = {}
            
            for method, data in test['methods'].items():
                if data.get('success'):
                    summary['successful_tests'] += 1
                    speed = data.get('speed_mbps', 0)
                    
                    if method not in method_speeds:
                        method_speeds[method] = []
                    method_speeds[method].append(speed)
                    
                    if method not in size_performance[size_cat]:
                        size_performance[size_cat][method] = []
                    size_performance[size_cat][method].append(speed)
        
        # Calculate average speeds
        for method, speeds in method_speeds.items():
            if speeds:
                summary['average_speeds'][method] = sum(speeds) / len(speeds)
        
        # Find best method by size category
        for size_cat, methods in size_performance.items():
            best_method = None
            best_speed = 0
            for method, speeds in methods.items():
                if speeds:
                    avg_speed = sum(speeds) / len(speeds)
                    if avg_speed > best_speed:
                        best_speed = avg_speed
                        best_method = method
            
            if best_method:
                summary['best_method_by_size'][size_cat] = {
                    'method': best_method,
                    'speed': best_speed
                }
        
        # Generate recommendations
        if 'memory_stream' in summary['average_speeds']:
            if summary['average_speeds']['memory_stream'] > summary['average_speeds'].get('file_download', 0):
                summary['recommendations'].append("Memory streaming shows better performance for small files")
        
        if summary['successful_tests'] > 0:
            success_rate = (summary['successful_tests'] / (len(results['download_tests']) * 3)) * 100
            summary['success_rate'] = success_rate
            if success_rate > 80:
                summary['recommendations'].append("High success rate indicates stable download mechanisms")
        
        return summary
    
    def save_results(self, results: Dict, filename: str = None):
        """Save test results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_test_results_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {filename}")
        return filename
    
    def print_summary(self, results: Dict):
        """Print formatted summary"""
        summary = results['summary']
        
        print("\n" + "=" * 50)
        print("📊 PERFORMANCE TEST SUMMARY")
        print("=" * 50)
        
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Successful Tests: {summary['successful_tests']}")
        if 'success_rate' in summary:
            print(f"Success Rate: {summary['success_rate']:.1f}%")
        
        print("\n📈 Average Speeds by Method:")
        for method, speed in summary['average_speeds'].items():
            print(f"  {method}: {speed:.2f} MB/s")
        
        print("\n🏆 Best Method by File Size:")
        for size_cat, data in summary['best_method_by_size'].items():
            print(f"  {size_cat}: {data['method']} ({data['speed']:.2f} MB/s)")
        
        if summary['recommendations']:
            print("\n💡 Recommendations:")
            for rec in summary['recommendations']:
                print(f"  • {rec}")

async def main():
    """Main test function"""
    test = PerformanceTest()
    
    try:
        results = await test.run_comprehensive_test()
        test.print_summary(results)
        filename = test.save_results(results)
        
        print(f"\n✅ Performance testing completed!")
        print(f"📄 Detailed results saved to: {filename}")
        
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())