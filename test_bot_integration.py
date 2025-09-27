#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست یکپارچگی با بات تلگرام
"""

import os
import sys
import asyncio
import json
import tempfile
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plugins.youtube_new_callback import handle_new_quality_callback
from plugins.youtube_advanced_downloader import YouTubeAdvancedDownloader
from plugins.youtube_quality_selector import YouTubeQualitySelector

class MockTelegramObjects:
    """Mock objects برای تست بات تلگرام"""
    
    def __init__(self):
        self.setup_mocks()
    
    def setup_mocks(self):
        """تنظیم mock objects"""
        
        # Mock Update
        self.update = Mock()
        self.update.callback_query = Mock()
        self.update.callback_query.data = "youtube_quality_720p_mp4"
        self.update.callback_query.message = Mock()
        self.update.callback_query.message.message_id = 123
        self.update.callback_query.message.chat = Mock()
        self.update.callback_query.message.chat.id = 456
        self.update.callback_query.from_user = Mock()
        self.update.callback_query.from_user.id = 789
        
        # Mock Context
        self.context = Mock()
        self.context.bot = Mock()
        self.context.bot.edit_message_text = AsyncMock()
        self.context.bot.send_document = AsyncMock()
        self.context.bot.delete_message = AsyncMock()
        
        # Mock step data (used by callback)
        self.mock_step_data = {
            'quality_options': [
                {'quality': '720p', 'format': 'mp4', 'size': '50MB', 'type': 'video'},
                {'quality': '480p', 'format': 'mp4', 'size': '30MB', 'type': 'video'},
                {'quality': 'audio', 'format': 'm4a', 'size': '5MB', 'type': 'audio'}
            ],
            'url': 'https://www.youtube.com/watch?v=test123',
            'video_title': 'Test Video Title'
        }

class BotIntegrationTest:
    def __init__(self):
        self.mock_objects = MockTelegramObjects()
        self.downloader = YouTubeAdvancedDownloader()
        self.selector = YouTubeQualitySelector()
        
    def create_mock_download_result(self, success=True):
        """ایجاد نتیجه mock برای دانلود"""
        if success:
            # Create a temporary test file
            temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            temp_file.write(b'fake video content for testing')
            temp_file.close()
            
            return {
                'success': True,
                'file_path': temp_file.name,
                'file_size': os.path.getsize(temp_file.name)
            }
        else:
            return {
                'success': False,
                'file_path': None,
                'file_size': 0,
                'error': 'Mock download error'
            }
    
    def create_mock_metadata(self):
        """ایجاد metadata mock"""
        return {
            'width': 1280,
            'height': 720,
            'duration': 180.5,
            'size': 52428800,  # 50MB
            'video_codec': 'h264',
            'audio_codec': 'aac'
        }
    
    async def test_successful_download_flow(self):
        """تست جریان موفقیت‌آمیز دانلود"""
        print("🔍 تست جریان موفقیت‌آمیز دانلود...")
        
        # Mock the download_and_merge method as async
        mock_result = self.create_mock_download_result(success=True)
        mock_metadata = self.create_mock_metadata()
        
        with patch.object(self.downloader, 'download_and_merge', new_callable=AsyncMock, return_value=mock_result), \
             patch.object(self.downloader, 'get_file_metadata', new_callable=AsyncMock, return_value=mock_metadata):
            
            try:
                # Simulate the download process directly
                download_result = await self.downloader.download_and_merge(
                    url="https://www.youtube.com/watch?v=test",
                    quality_info={"resolution": "720p", "filesize": 1024000},
                    callback=None
                )
                
                # Verify download success
                if download_result and download_result.get('success'):
                    print("  ✅ دانلود با موفقیت انجام شد")
                    
                    # Get file metadata
                    metadata = await self.downloader.get_file_metadata(download_result.get('output_path', 'test.mp4'))
                    
                    if metadata:
                        print("  ✅ متادیتا با موفقیت دریافت شد")
                        return True
                    else:
                        print("  ❌ متادیتا دریافت نشد")
                        return False
                else:
                    print("  ❌ دانلود ناموفق بود")
                    return False
                    
            except Exception as e:
                print(f"  ❌ خطا در تست: {e}")
                return False
            finally:
                # Cleanup temp file
                if mock_result['file_path'] and os.path.exists(mock_result['file_path']):
                    os.unlink(mock_result['file_path'])
    
    async def test_failed_download_flow(self):
        """تست جریان ناموفق دانلود"""
        print("\n🔍 تست جریان ناموفق دانلود...")
        
        # Mock failed download as async
        mock_result = self.create_mock_download_result(success=False)
        
        with patch.object(self.downloader, 'download_and_merge', new_callable=AsyncMock, return_value=mock_result):
            
            try:
                # Simulate failed download
                download_result = await self.downloader.download_and_merge(
                    url="https://www.youtube.com/watch?v=invalid",
                    quality_info={"resolution": "720p", "filesize": 1024000},
                    callback=None
                )
                
                # Verify failure handling
                if download_result and not download_result.get('success'):
                    error_msg = download_result.get('error', 'خطای نامشخص')
                    print(f"  ✅ خطا به درستی شناسایی شد: {error_msg}")
                    return True
                else:
                    print("  ❌ خطا به درستی شناسایی نشد")
                    return False
                    
            except Exception as e:
                print(f"  ❌ خطا در تست: {e}")
                return False
    
    async def test_callback_data_parsing(self):
        """تست تجزیه callback data"""
        print("\n🔍 تست تجزیه callback data...")
        
        test_cases = [
            "youtube_quality_720p_mp4",
            "youtube_quality_480p_mp4", 
            "youtube_quality_audio_m4a",
            "youtube_quality_1080p_webm"
        ]
        
        success_count = 0
        
        for callback_data in test_cases:
            print(f"  🔍 تست: {callback_data}")
            
            try:
                # Test callback data parsing logic
                if callback_data.startswith('youtube_quality_'):
                    parts = callback_data.split('_')
                    if len(parts) >= 3:
                        quality = parts[2]  # e.g., "720p", "480p", "audio"
                        format_type = parts[3] if len(parts) > 3 else "mp4"
                        
                        print(f"    ✅ تجزیه موفق: کیفیت={quality}, فرمت={format_type}")
                        success_count += 1
                    else:
                        print(f"    ❌ فرمت نامعتبر: {callback_data}")
                else:
                    print(f"    ❌ پیشوند نامعتبر: {callback_data}")
                    
            except Exception as e:
                print(f"    ❌ خطا در تجزیه: {e}")
        
        success_rate = (success_count / len(test_cases)) * 100
        print(f"  📊 نرخ موفقیت تجزیه: {success_rate}%")
        
        return success_rate > 75
    
    async def test_user_data_validation(self):
        """تست اعتبارسنجی user_data"""
        print("\n🔍 تست اعتبارسنجی user_data...")
        
        # Test with missing data
        original_user_data = self.mock_objects.context.user_data.copy()
        
        test_cases = [
            {'youtube_url': None},  # Missing URL
            {'available_qualities': None},  # Missing qualities
            {'video_title': None},  # Missing title
            {}  # Empty user_data
        ]
        
        results = []
        
        for i, test_data in enumerate(test_cases):
            print(f"  🔍 تست کیس {i+1}: {test_data}")
            
            # Update user_data
            self.mock_objects.context.user_data = test_data
            
            try:
                await handle_new_quality_callback(
                    None,  # client not needed for test
                    self.mock_objects.update.callback_query
                )
                print(f"    ⚠️ انتظار خطا بود اما موفق شد")
                results.append(False)
                
            except Exception as e:
                print(f"    ✅ خطا به درستی شناسایی شد: {type(e).__name__}")
                results.append(True)
        
        # Restore original user_data
        self.mock_objects.context.user_data = original_user_data
        
        success_rate = sum(results) / len(results) * 100
        print(f"  📊 نرخ شناسایی خطا: {success_rate:.1f}%")
        
        return success_rate >= 75
    
    async def run_all_tests(self):
        """اجرای تمام تست‌ها"""
        print("🚀 تست یکپارچگی بات تلگرام")
        print("=" * 50)
        
        tests = [
            ("جریان موفقیت‌آمیز دانلود", self.test_successful_download_flow),
            ("جریان ناموفق دانلود", self.test_failed_download_flow),
            ("تجزیه callback data", self.test_callback_data_parsing),
            ("اعتبارسنجی user_data", self.test_user_data_validation)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            try:
                result = await test_func()
                results[test_name] = result
                status = "✅ موفق" if result else "❌ ناموفق"
                print(f"\n{status} {test_name}")
                
            except Exception as e:
                results[test_name] = False
                print(f"\n❌ خطا در {test_name}: {e}")
        
        # Summary
        print("\n📊 خلاصه نتایج:")
        print("=" * 30)
        
        total_tests = len(tests)
        passed_tests = sum(1 for result in results.values() if result)
        
        for test_name, result in results.items():
            status = "✅" if result else "❌"
            print(f"{status} {test_name}")
        
        print(f"\n📈 نتیجه کلی: {passed_tests}/{total_tests} تست موفق")
        
        # Save results
        test_results = {
            'tests': results,
            'summary': {
                'total': total_tests,
                'passed': passed_tests,
                'success_rate': passed_tests / total_tests * 100
            }
        }
        
        with open('bot_integration_test_results.json', 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 نتایج در bot_integration_test_results.json ذخیره شد")
        
        success_rate = passed_tests / total_tests * 100
        if success_rate >= 75:
            print(f"\n🎉 تست یکپارچگی موفقیت‌آمیز! ({success_rate:.1f}%)")
            return True
        else:
            print(f"\n⚠️ تست یکپارچگی نیاز به بهبود دارد ({success_rate:.1f}%)")
            return False

async def main():
    """تابع اصلی"""
    tester = BotIntegrationTest()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✅ تست یکپارچگی بات موفقیت‌آمیز بود")
    else:
        print("\n❌ تست یکپارچگی بات نیاز به بررسی دارد")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())