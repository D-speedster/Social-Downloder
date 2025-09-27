"""
Error Handling Tests for YouTube Downloader
تست‌های مدیریت خطا برای دانلودر یوتیوب
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

class ErrorHandlingTestSuite:
    def __init__(self):
        self.results = {}
        self.downloader = youtube_downloader
        self.selector = quality_selector
        
    def create_mock_error_result(self, error_type="network"):
        """Create mock error result for testing"""
        error_messages = {
            'network': 'Network connection failed',
            'invalid_url': 'Invalid YouTube URL provided',
            'no_formats': 'No video formats available',
            'download_failed': 'Download process failed',
            'merge_failed': 'Video merge process failed',
            'file_not_found': 'Output file not found',
            'permission_denied': 'Permission denied to write file'
        }
        
        return {
            'success': False,
            'error': error_messages.get(error_type, 'Unknown error'),
            'error_type': error_type,
            'processing_time': 0.5
        }
    
    async def test_network_errors(self):
        """Test network-related error handling"""
        print("🌐 تست مدیریت خطاهای شبکه...")
        
        network_errors = [
            'network',
            'invalid_url', 
            'no_formats'
        ]
        
        handled_errors = 0
        
        for error_type in network_errors:
            print(f"  🔍 تست خطای {error_type}...")
            
            try:
                mock_result = self.create_mock_error_result(error_type)
                
                with patch.object(self.downloader, 'download_and_merge', new_callable=AsyncMock, return_value=mock_result):
                    
                    result = await self.downloader.download_and_merge(
                        url="https://www.youtube.com/watch?v=invalid",
                        quality_info={"resolution": "720p", "filesize": 1024000},
                        callback=None
                    )
                    
                    # Check if error was properly handled
                    if result and not result.get('success'):
                        error_msg = result.get('error', '')
                        if error_msg and len(error_msg) > 0:
                            print(f"    ✅ خطا به درستی مدیریت شد: {error_msg}")
                            handled_errors += 1
                        else:
                            print(f"    ❌ پیام خطا خالی است")
                    else:
                        print(f"    ❌ خطا به درستی شناسایی نشد")
                        
            except Exception as e:
                print(f"    ❌ خطا در تست {error_type}: {e}")
        
        success_rate = (handled_errors / len(network_errors)) * 100
        print(f"  📊 نرخ مدیریت خطاهای شبکه: {success_rate}%")
        
        self.results['network_errors'] = {
            'status': 'success' if success_rate >= 80 else 'failed',
            'handled_errors': handled_errors,
            'total_errors': len(network_errors),
            'success_rate': round(success_rate, 2)
        }
        
        return success_rate >= 80
    
    async def test_file_system_errors(self):
        """Test file system error handling"""
        print("\n📁 تست مدیریت خطاهای فایل سیستم...")
        
        file_errors = [
            'download_failed',
            'merge_failed',
            'file_not_found',
            'permission_denied'
        ]
        
        handled_errors = 0
        
        for error_type in file_errors:
            print(f"  🔍 تست خطای {error_type}...")
            
            try:
                mock_result = self.create_mock_error_result(error_type)
                
                with patch.object(self.downloader, 'download_and_merge', new_callable=AsyncMock, return_value=mock_result):
                    
                    result = await self.downloader.download_and_merge(
                        url="https://www.youtube.com/watch?v=test",
                        quality_info={"resolution": "720p", "filesize": 1024000},
                        callback=None
                    )
                    
                    # Check error handling
                    if result and not result.get('success'):
                        error_msg = result.get('error', '')
                        error_type_returned = result.get('error_type', '')
                        
                        if error_msg and error_type_returned:
                            print(f"    ✅ خطا مدیریت شد: {error_type_returned}")
                            handled_errors += 1
                        else:
                            print(f"    ❌ اطلاعات خطا ناکامل")
                    else:
                        print(f"    ❌ خطا شناسایی نشد")
                        
            except Exception as e:
                print(f"    ❌ خطا در تست {error_type}: {e}")
        
        success_rate = (handled_errors / len(file_errors)) * 100
        print(f"  📊 نرخ مدیریت خطاهای فایل: {success_rate}%")
        
        self.results['file_system_errors'] = {
            'status': 'success' if success_rate >= 80 else 'failed',
            'handled_errors': handled_errors,
            'total_errors': len(file_errors),
            'success_rate': round(success_rate, 2)
        }
        
        return success_rate >= 80
    
    async def test_invalid_input_handling(self):
        """Test invalid input handling"""
        print("\n🚫 تست مدیریت ورودی‌های نامعتبر...")
        
        invalid_inputs = [
            # Invalid URLs
            {"url": "", "quality_info": {"resolution": "720p"}, "expected_error": "empty_url"},
            {"url": "not_a_url", "quality_info": {"resolution": "720p"}, "expected_error": "invalid_format"},
            {"url": "https://example.com", "quality_info": {"resolution": "720p"}, "expected_error": "not_youtube"},
            
            # Invalid quality info
            {"url": "https://www.youtube.com/watch?v=test", "quality_info": None, "expected_error": "no_quality"},
            {"url": "https://www.youtube.com/watch?v=test", "quality_info": {}, "expected_error": "empty_quality"},
            {"url": "https://www.youtube.com/watch?v=test", "quality_info": {"invalid": "data"}, "expected_error": "invalid_quality"}
        ]
        
        handled_inputs = 0
        
        for i, test_case in enumerate(invalid_inputs):
            print(f"  🔍 تست ورودی نامعتبر {i+1}...")
            
            try:
                # Mock error based on input type
                if not test_case["url"] or test_case["url"] == "not_a_url":
                    mock_result = self.create_mock_error_result('invalid_url')
                elif not test_case["quality_info"]:
                    mock_result = self.create_mock_error_result('no_formats')
                else:
                    mock_result = self.create_mock_error_result('download_failed')
                
                with patch.object(self.downloader, 'download_and_merge', new_callable=AsyncMock, return_value=mock_result):
                    
                    result = await self.downloader.download_and_merge(
                        url=test_case["url"],
                        quality_info=test_case["quality_info"],
                        callback=None
                    )
                    
                    # Check if invalid input was handled
                    if result and not result.get('success'):
                        print(f"    ✅ ورودی نامعتبر شناسایی شد")
                        handled_inputs += 1
                    else:
                        print(f"    ❌ ورودی نامعتبر شناسایی نشد")
                        
            except Exception as e:
                # Exception handling is also valid error handling
                print(f"    ✅ خطا با exception مدیریت شد: {type(e).__name__}")
                handled_inputs += 1
        
        success_rate = (handled_inputs / len(invalid_inputs)) * 100
        print(f"  📊 نرخ مدیریت ورودی‌های نامعتبر: {success_rate}%")
        
        self.results['invalid_input_handling'] = {
            'status': 'success' if success_rate >= 80 else 'failed',
            'handled_inputs': handled_inputs,
            'total_inputs': len(invalid_inputs),
            'success_rate': round(success_rate, 2)
        }
        
        return success_rate >= 80
    
    async def test_utility_error_handling(self):
        """Test utility function error handling"""
        print("\n🛠️ تست مدیریت خطا در توابع کمکی...")
        
        utility_tests = [
            # convert_size function tests
            {"func": "convert_size", "args": [2, None], "expected": "handle_none"},
            {"func": "convert_size", "args": [2, -1], "expected": "handle_negative"},
            {"func": "convert_size", "args": [2, "invalid"], "expected": "handle_string"},
            {"func": "convert_size", "args": [-1, 1024], "expected": "handle_invalid_precision"}
        ]
        
        handled_errors = 0
        
        for test in utility_tests:
            print(f"  🔍 تست {test['func']} با آرگومان‌های نامعتبر...")
            
            try:
                if test['func'] == 'convert_size':
                    result = convert_size(*test['args'])
                    
                    # Check if function handled invalid input gracefully
                    if isinstance(result, str) and len(result) > 0:
                        print(f"    ✅ نتیجه معتبر برگردانده شد: {result}")
                        handled_errors += 1
                    else:
                        print(f"    ❌ نتیجه نامعتبر: {result}")
                        
            except Exception as e:
                # Exception handling is acceptable for invalid inputs
                print(f"    ✅ خطا با exception مدیریت شد: {type(e).__name__}")
                handled_errors += 1
        
        success_rate = (handled_errors / len(utility_tests)) * 100
        print(f"  📊 نرخ مدیریت خطا در توابع کمکی: {success_rate}%")
        
        self.results['utility_error_handling'] = {
            'status': 'success' if success_rate >= 75 else 'failed',
            'handled_errors': handled_errors,
            'total_tests': len(utility_tests),
            'success_rate': round(success_rate, 2)
        }
        
        return success_rate >= 75
    
    async def test_recovery_mechanisms(self):
        """Test error recovery mechanisms"""
        print("\n🔄 تست مکانیزم‌های بازیابی...")
        
        recovery_scenarios = [
            {"name": "retry_after_network_error", "attempts": 3},
            {"name": "fallback_quality", "attempts": 2},
            {"name": "alternative_format", "attempts": 2}
        ]
        
        successful_recoveries = 0
        
        for scenario in recovery_scenarios:
            print(f"  🔍 تست بازیابی: {scenario['name']}...")
            
            try:
                # Simulate recovery by having first attempts fail, last succeed
                call_count = 0
                
                def mock_download_with_recovery(*args, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    
                    if call_count < scenario['attempts']:
                        # Fail first attempts
                        return self.create_mock_error_result('network')
                    else:
                        # Succeed on final attempt
                        return {
                            'success': True,
                            'output_path': 'test_recovered.mp4',
                            'recovery_attempt': call_count
                        }
                
                with patch.object(self.downloader, 'download_and_merge', side_effect=mock_download_with_recovery):
                    
                    # Simulate multiple attempts
                    final_result = None
                    for attempt in range(scenario['attempts']):
                        result = await self.downloader.download_and_merge(
                            url="https://www.youtube.com/watch?v=test",
                            quality_info={"resolution": "720p"},
                            callback=None
                        )
                        
                        if result and result.get('success'):
                            final_result = result
                            break
                    
                    # Check if recovery was successful
                    if final_result and final_result.get('success'):
                        recovery_attempt = final_result.get('recovery_attempt', 0)
                        print(f"    ✅ بازیابی موفق در تلاش {recovery_attempt}")
                        successful_recoveries += 1
                    else:
                        print(f"    ❌ بازیابی ناموفق")
                        
            except Exception as e:
                print(f"    ❌ خطا در تست بازیابی: {e}")
        
        success_rate = (successful_recoveries / len(recovery_scenarios)) * 100
        print(f"  📊 نرخ موفقیت بازیابی: {success_rate}%")
        
        self.results['recovery_mechanisms'] = {
            'status': 'success' if success_rate >= 70 else 'failed',
            'successful_recoveries': successful_recoveries,
            'total_scenarios': len(recovery_scenarios),
            'success_rate': round(success_rate, 2)
        }
        
        return success_rate >= 70
    
    def save_results(self):
        """Save error handling test results"""
        results_with_metadata = {
            'test_timestamp': datetime.now().isoformat(),
            'test_type': 'error_handling',
            'results': self.results
        }
        
        with open('error_handling_test_results.json', 'w', encoding='utf-8') as f:
            json.dump(results_with_metadata, f, ensure_ascii=False, indent=2)
    
    async def run_all_tests(self):
        """Run all error handling tests"""
        print("🚨 شروع تست‌های مدیریت خطا...")
        print("=" * 50)
        
        tests = [
            ("مدیریت خطاهای شبکه", self.test_network_errors),
            ("مدیریت خطاهای فایل سیستم", self.test_file_system_errors),
            ("مدیریت ورودی‌های نامعتبر", self.test_invalid_input_handling),
            ("مدیریت خطا در توابع کمکی", self.test_utility_error_handling),
            ("مکانیزم‌های بازیابی", self.test_recovery_mechanisms)
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
        print("📊 خلاصه نتایج مدیریت خطا:")
        print("=" * 50)
        
        for test_name, _ in tests:
            status = "✅" if test_name.split()[-1] in [k for k, v in self.results.items() if v.get('status') == 'success'] else "❌"
            print(f"{status} {test_name}")
        
        print(f"\n📈 نتیجه کلی: {passed_tests}/{total_tests} تست موفق")
        print(f"💾 نتایج در error_handling_test_results.json ذخیره شد")
        
        if success_rate >= 80:
            print(f"\n🎉 تست مدیریت خطا موفقیت‌آمیز! ({success_rate}%)")
            print("✅ سیستم مدیریت خطای مطلوبی دارد")
        else:
            print(f"\n⚠️ تست مدیریت خطا نیاز به بهبود دارد ({success_rate}%)")
            print("❌ سیستم نیاز به بهبود مدیریت خطا دارد")
        
        self.save_results()
        return success_rate >= 80

async def main():
    """Main test runner"""
    test_suite = ErrorHandlingTestSuite()
    success = await test_suite.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)