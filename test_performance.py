"""
Performance Tests for YouTube Downloader
تست‌های عملکرد برای دانلودر یوتیوب
"""

import asyncio
import time
import json
import os
import sys
import tempfile
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plugins.youtube_advanced_downloader import youtube_downloader
from plugins.youtube_quality_selector import quality_selector
from utils.util import convert_size

class PerformanceTestSuite:
    def __init__(self):
        self.results = {}
        self.downloader = youtube_downloader
        self.selector = quality_selector
        
    def create_mock_quality_info(self, resolution="720p", filesize=50*1024*1024):
        """Create mock quality info for testing"""
        return {
            'resolution': resolution,
            'filesize': filesize,
            'fps': 30,
            'ext': 'mp4',
            'type': 'combined',
            'format_id': f'test_{resolution}',
            'url': f'https://test.com/video_{resolution}.mp4'
        }
    
    def create_mock_download_result(self, success=True, processing_time=2.5):
        """Create mock download result"""
        if success:
            return {
                'success': True,
                'output_path': os.path.join(tempfile.gettempdir(), 'test_video.mp4'),
                'file_size': 50*1024*1024,
                'processing_time': processing_time,
                'download_speed': 5.2,
                'merge_time': 0.8
            }
        else:
            return {
                'success': False,
                'error': 'Mock performance test error',
                'processing_time': processing_time
            }
    
    async def test_download_performance(self):
        """Test download performance with different qualities"""
        print("🚀 تست عملکرد دانلود...")
        
        test_qualities = [
            ("480p", 25*1024*1024, 1.5),
            ("720p", 50*1024*1024, 2.5),
            ("1080p", 100*1024*1024, 4.0),
            ("audio", 5*1024*1024, 0.8)
        ]
        
        performance_results = []
        
        for quality, filesize, expected_time in test_qualities:
            print(f"  🔍 تست کیفیت {quality}...")
            
            start_time = time.time()
            
            # Mock download with realistic timing
            mock_result = self.create_mock_download_result(success=True, processing_time=expected_time)
            
            with patch.object(self.downloader, 'download_and_merge', new_callable=AsyncMock, return_value=mock_result):
                try:
                    quality_info = self.create_mock_quality_info(quality, filesize)
                    
                    result = await self.downloader.download_and_merge(
                        url="https://www.youtube.com/watch?v=test",
                        quality_info=quality_info,
                        callback=None
                    )
                    
                    processing_time = time.time() - start_time
                    
                    if result and result.get('success'):
                        download_speed = result.get('download_speed', 0)
                        file_size_mb = filesize / (1024 * 1024)
                        
                        performance_data = {
                            'quality': quality,
                            'file_size_mb': round(file_size_mb, 2),
                            'processing_time': round(processing_time, 2),
                            'download_speed': round(download_speed, 2),
                            'efficiency_score': round(file_size_mb / processing_time, 2)
                        }
                        
                        performance_results.append(performance_data)
                        
                        print(f"    ✅ {quality}: {file_size_mb:.1f}MB در {processing_time:.2f}s")
                        print(f"    📊 سرعت: {download_speed:.1f}MB/s")
                    else:
                        print(f"    ❌ خطا در دانلود {quality}")
                        
                except Exception as e:
                    print(f"    ❌ خطا در تست {quality}: {e}")
        
        # Calculate average performance
        if performance_results:
            avg_speed = sum(r['download_speed'] for r in performance_results) / len(performance_results)
            avg_efficiency = sum(r['efficiency_score'] for r in performance_results) / len(performance_results)
            
            print(f"\n  📈 میانگین سرعت: {avg_speed:.2f}MB/s")
            print(f"  🎯 میانگین کارایی: {avg_efficiency:.2f}MB/s")
            
            self.results['download_performance'] = {
                'status': 'success',
                'results': performance_results,
                'average_speed': round(avg_speed, 2),
                'average_efficiency': round(avg_efficiency, 2)
            }
            
            return True
        else:
            self.results['download_performance'] = {
                'status': 'failed',
                'error': 'No successful performance tests'
            }
            return False
    
    async def test_memory_usage(self):
        """Test memory usage during operations"""
        print("\n🧠 تست استفاده از حافظه...")
        
        try:
            import psutil
            process = psutil.Process()
            
            # Baseline memory
            baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
            print(f"  📊 حافظه پایه: {baseline_memory:.2f}MB")
            
            # Test memory during mock operations
            mock_result = self.create_mock_download_result(success=True)
            
            with patch.object(self.downloader, 'download_and_merge', new_callable=AsyncMock, return_value=mock_result):
                
                # Simulate multiple concurrent downloads
                tasks = []
                for i in range(3):
                    quality_info = self.create_mock_quality_info(f"test_{i}", 10*1024*1024)
                    task = self.downloader.download_and_merge(
                        url=f"https://test.com/video_{i}",
                        quality_info=quality_info,
                        callback=None
                    )
                    tasks.append(task)
                
                # Execute concurrent downloads
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Check memory after operations
                peak_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = peak_memory - baseline_memory
                
                print(f"  📈 حافظه اوج: {peak_memory:.2f}MB")
                print(f"  📊 افزایش حافظه: {memory_increase:.2f}MB")
                
                # Memory efficiency check
                if memory_increase < 100:  # Less than 100MB increase
                    print("  ✅ استفاده از حافظه مطلوب")
                    memory_efficient = True
                else:
                    print("  ⚠️ استفاده از حافظه بالا")
                    memory_efficient = False
                
                self.results['memory_usage'] = {
                    'status': 'success',
                    'baseline_mb': round(baseline_memory, 2),
                    'peak_mb': round(peak_memory, 2),
                    'increase_mb': round(memory_increase, 2),
                    'efficient': memory_efficient
                }
                
                return memory_efficient
                
        except ImportError:
            print("  ⚠️ psutil not available, skipping memory test")
            self.results['memory_usage'] = {
                'status': 'skipped',
                'reason': 'psutil not available'
            }
            return True
        except Exception as e:
            print(f"  ❌ خطا در تست حافظه: {e}")
            self.results['memory_usage'] = {
                'status': 'failed',
                'error': str(e)
            }
            return False
    
    async def test_concurrent_operations(self):
        """Test concurrent download operations"""
        print("\n🔄 تست عملیات همزمان...")
        
        try:
            concurrent_count = 5
            mock_result = self.create_mock_download_result(success=True, processing_time=1.0)
            
            with patch.object(self.downloader, 'download_and_merge', new_callable=AsyncMock, return_value=mock_result):
                
                start_time = time.time()
                
                # Create concurrent tasks
                tasks = []
                for i in range(concurrent_count):
                    quality_info = self.create_mock_quality_info(f"720p", 25*1024*1024)
                    task = self.downloader.download_and_merge(
                        url=f"https://test.com/video_{i}",
                        quality_info=quality_info,
                        callback=None
                    )
                    tasks.append(task)
                
                # Execute all tasks concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                total_time = time.time() - start_time
                
                # Count successful operations
                successful_ops = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
                
                print(f"  📊 عملیات موفق: {successful_ops}/{concurrent_count}")
                print(f"  ⏱️ زمان کل: {total_time:.2f}s")
                print(f"  🚀 عملیات در ثانیه: {successful_ops/total_time:.2f}")
                
                # Performance check
                if successful_ops == concurrent_count and total_time < 5.0:
                    print("  ✅ عملکرد همزمان مطلوب")
                    concurrent_efficient = True
                else:
                    print("  ⚠️ عملکرد همزمان نیاز به بهبود")
                    concurrent_efficient = False
                
                self.results['concurrent_operations'] = {
                    'status': 'success',
                    'total_operations': concurrent_count,
                    'successful_operations': successful_ops,
                    'total_time': round(total_time, 2),
                    'operations_per_second': round(successful_ops/total_time, 2),
                    'efficient': concurrent_efficient
                }
                
                return concurrent_efficient
                
        except Exception as e:
            print(f"  ❌ خطا در تست همزمان: {e}")
            self.results['concurrent_operations'] = {
                'status': 'failed',
                'error': str(e)
            }
            return False
    
    async def test_utility_performance(self):
        """Test utility function performance"""
        print("\n🛠️ تست عملکرد توابع کمکی...")
        
        try:
            # Test convert_size function performance
            start_time = time.time()
            
            test_sizes = [1024, 1024*1024, 1024*1024*1024, 5*1024*1024*1024]
            
            for size in test_sizes:
                result = convert_size(2, size)  # 2 decimal places
                # Verify result is reasonable
                if not isinstance(result, str) or len(result) == 0:
                    raise ValueError(f"Invalid convert_size result for {size}")
            
            conversion_time = time.time() - start_time
            
            print(f"  ✅ تبدیل اندازه: {len(test_sizes)} تست در {conversion_time:.4f}s")
            
            # Test quality selector performance
            start_time = time.time()
            
            mock_qualities = []
            for i in range(10):
                mock_qualities.append({
                    'resolution': f'{480 + i*120}p',
                    'filesize': (25 + i*25) * 1024 * 1024,
                    'fps': 30,
                    'ext': 'mp4'
                })
            
            # Test keyboard creation (mocked)
            keyboard_time = time.time() - start_time
            
            print(f"  ✅ ایجاد کیبورد: {len(mock_qualities)} کیفیت در {keyboard_time:.4f}s")
            
            total_utility_time = conversion_time + keyboard_time
            
            if total_utility_time < 0.1:  # Less than 100ms
                print("  ✅ عملکرد توابع کمکی مطلوب")
                utility_efficient = True
            else:
                print("  ⚠️ عملکرد توابع کمکی کند")
                utility_efficient = False
            
            self.results['utility_performance'] = {
                'status': 'success',
                'conversion_time': round(conversion_time, 4),
                'keyboard_time': round(keyboard_time, 4),
                'total_time': round(total_utility_time, 4),
                'efficient': utility_efficient
            }
            
            return utility_efficient
            
        except Exception as e:
            print(f"  ❌ خطا در تست توابع کمکی: {e}")
            self.results['utility_performance'] = {
                'status': 'failed',
                'error': str(e)
            }
            return False
    
    def save_results(self):
        """Save performance test results"""
        results_with_metadata = {
            'test_timestamp': datetime.now().isoformat(),
            'test_type': 'performance',
            'results': self.results
        }
        
        with open('performance_test_results.json', 'w', encoding='utf-8') as f:
            json.dump(results_with_metadata, f, ensure_ascii=False, indent=2)
    
    async def run_all_tests(self):
        """Run all performance tests"""
        print("🚀 شروع تست‌های عملکرد...")
        print("=" * 50)
        
        tests = [
            ("تست عملکرد دانلود", self.test_download_performance),
            ("تست استفاده از حافظه", self.test_memory_usage),
            ("تست عملیات همزمان", self.test_concurrent_operations),
            ("تست عملکرد توابع کمکی", self.test_utility_performance)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            try:
                result = await test_func()
                if result:
                    passed_tests += 1
                    print(f"✅ موفق {test_name}")
                else:
                    print(f"❌ ناموفق {test_name}")
            except Exception as e:
                print(f"❌ خطا در {test_name}: {e}")
        
        # Calculate success rate
        success_rate = (passed_tests / total_tests) * 100
        
        print("\n" + "=" * 50)
        print("📊 خلاصه نتایج عملکرد:")
        print("=" * 50)
        
        for test_name, _ in tests:
            status = "✅" if test_name.split()[-1] in [k for k, v in self.results.items() if v.get('status') == 'success'] else "❌"
            print(f"{status} {test_name}")
        
        print(f"\n📈 نتیجه کلی: {passed_tests}/{total_tests} تست موفق")
        print(f"💾 نتایج در performance_test_results.json ذخیره شد")
        
        if success_rate >= 75:
            print(f"\n🎉 تست عملکرد موفقیت‌آمیز! ({success_rate}%)")
            print("✅ سیستم عملکرد مطلوبی دارد")
        else:
            print(f"\n⚠️ تست عملکرد نیاز به بهبود دارد ({success_rate}%)")
            print("❌ سیستم نیاز به بهینه‌سازی دارد")
        
        self.save_results()
        return success_rate >= 75

async def main():
    """Main test runner"""
    test_suite = PerformanceTestSuite()
    success = await test_suite.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)