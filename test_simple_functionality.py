#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست ساده عملکردهای اصلی سیستم
"""

import os
import sys
import asyncio
import json
import tempfile
import subprocess

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plugins.youtube_advanced_downloader import YouTubeAdvancedDownloader
from plugins.youtube_quality_selector import YouTubeQualitySelector

class SimpleFunctionalityTest:
    def __init__(self):
        self.downloader = YouTubeAdvancedDownloader()
        self.selector = YouTubeQualitySelector()
        
    def test_ffmpeg_availability(self):
        """تست در دسترس بودن ffmpeg و ffprobe"""
        print("🔍 تست در دسترس بودن ابزارها...")
        
        results = {}
        
        # Test ffmpeg
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("  ✅ ffmpeg در دسترس است")
                results['ffmpeg'] = True
            else:
                print("  ❌ ffmpeg در دسترس نیست")
                results['ffmpeg'] = False
        except Exception as e:
            print(f"  ❌ خطا در تست ffmpeg: {e}")
            results['ffmpeg'] = False
        
        # Test ffprobe
        try:
            result = subprocess.run(['ffprobe', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("  ✅ ffprobe در دسترس است")
                results['ffprobe'] = True
            else:
                print("  ❌ ffprobe در دسترس نیست")
                results['ffprobe'] = False
        except Exception as e:
            print(f"  ❌ خطا در تست ffprobe: {e}")
            results['ffprobe'] = False
        
        # Test yt-dlp
        try:
            result = subprocess.run(['yt-dlp', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("  ✅ yt-dlp در دسترس است")
                results['yt-dlp'] = True
            else:
                print("  ❌ yt-dlp در دسترس نیست")
                results['yt-dlp'] = False
        except Exception as e:
            print(f"  ❌ خطا در تست yt-dlp: {e}")
            results['yt-dlp'] = False
        
        return results
    
    def test_downloader_initialization(self):
        """تست مقداردهی اولیه downloader"""
        print("\n🔍 تست مقداردهی اولیه downloader...")
        
        try:
            # Check if downloader is properly initialized
            if hasattr(self.downloader, 'ffmpeg_path'):
                print("  ✅ ffmpeg_path تنظیم شده")
            else:
                print("  ❌ ffmpeg_path تنظیم نشده")
                return False
            
            if hasattr(self.downloader, 'cookies_file'):
                print("  ✅ cookies_file تنظیم شده")
            else:
                print("  ❌ cookies_file تنظیم نشده")
                return False
            
            if hasattr(self.downloader, 'download_and_merge'):
                print("  ✅ متد download_and_merge موجود است")
            else:
                print("  ❌ متد download_and_merge موجود نیست")
                return False
            
            if hasattr(self.downloader, 'get_file_metadata'):
                print("  ✅ متد get_file_metadata موجود است")
            else:
                print("  ❌ متد get_file_metadata موجود نیست")
                return False
            
            print("  ✅ downloader به درستی مقداردهی شده")
            return True
            
        except Exception as e:
            print(f"  ❌ خطا در تست مقداردهی: {e}")
            return False
    
    def test_selector_initialization(self):
        """تست مقداردهی اولیه selector"""
        print("\n🔍 تست مقداردهی اولیه selector...")
        
        try:
            # Check if selector is properly initialized
            if hasattr(self.selector, 'get_available_qualities'):
                print("  ✅ متد get_available_qualities موجود است")
            else:
                print("  ❌ متد get_available_qualities موجود نیست")
                return False
            
            if hasattr(self.selector, 'format_quality_info'):
                print("  ✅ متد format_quality_info موجود است")
            else:
                print("  ❌ متد format_quality_info موجود نیست")
                return False
            
            print("  ✅ selector به درستی مقداردهی شده")
            return True
            
        except Exception as e:
            print(f"  ❌ خطا در تست مقداردهی: {e}")
            return False
    
    async def test_metadata_functions(self):
        """تست توابع metadata"""
        print("\n🔍 تست توابع metadata...")
        
        # Create a test file
        test_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        try:
            # Create a simple test video
            cmd = [
                'ffmpeg', '-y', '-f', 'lavfi',
                '-i', 'testsrc2=duration=3:size=640x480:rate=15',
                '-f', 'lavfi', '-i', 'sine=frequency=440:duration=3',
                '-c:v', 'libx264', '-c:a', 'aac', '-shortest',
                test_file.name
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            if result.returncode != 0:
                print("  ❌ نتوانست فایل تست ایجاد کند")
                return False
            
            # Test metadata extraction
            metadata = await self.downloader.get_file_metadata(test_file.name)
            
            if metadata:
                print("  ✅ metadata استخراج شد:")
                if 'width' in metadata:
                    print(f"    📺 عرض: {metadata['width']}")
                if 'height' in metadata:
                    print(f"    📺 ارتفاع: {metadata['height']}")
                if 'duration' in metadata:
                    print(f"    ⏱ مدت زمان: {metadata['duration']}")
                if 'size' in metadata:
                    print(f"    📦 حجم: {metadata['size']} بایت")
                return True
            else:
                print("  ❌ نتوانست metadata استخراج کند")
                return False
                
        except Exception as e:
            print(f"  ❌ خطا در تست metadata: {e}")
            return False
        finally:
            # Cleanup
            try:
                os.unlink(test_file.name)
            except:
                pass
    
    def test_file_integrity_check(self):
        """تست بررسی یکپارچگی فایل"""
        print("\n🔍 تست بررسی یکپارچگی فایل...")
        
        # Create a test file
        test_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        try:
            # Create a simple test video
            cmd = [
                'ffmpeg', '-y', '-f', 'lavfi',
                '-i', 'testsrc2=duration=2:size=320x240:rate=10',
                '-c:v', 'libx264', '-t', '2',
                test_file.name
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=20)
            if result.returncode != 0:
                print("  ❌ نتوانست فایل تست ایجاد کند")
                return False
            
            # Test file integrity
            is_valid = self.downloader._verify_file_integrity(test_file.name, 'ffprobe')
            
            if is_valid:
                print("  ✅ فایل معتبر تشخیص داده شد")
                return True
            else:
                print("  ❌ فایل نامعتبر تشخیص داده شد")
                return False
                
        except Exception as e:
            print(f"  ❌ خطا در تست یکپارچگی: {e}")
            return False
        finally:
            # Cleanup
            try:
                os.unlink(test_file.name)
            except:
                pass
    
    def test_stream_probing(self):
        """تست بررسی stream ها"""
        print("\n🔍 تست بررسی stream ها...")
        
        # Create test files
        video_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        audio_file = tempfile.NamedTemporaryFile(suffix='.m4a', delete=False)
        
        try:
            # Create video file
            cmd_video = [
                'ffmpeg', '-y', '-f', 'lavfi',
                '-i', 'testsrc2=duration=2:size=320x240:rate=10',
                '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2',
                '-c:v', 'libx264', '-c:a', 'aac', '-shortest',
                video_file.name
            ]
            
            # Create audio file
            cmd_audio = [
                'ffmpeg', '-y', '-f', 'lavfi',
                '-i', 'sine=frequency=440:duration=2',
                '-c:a', 'aac',
                audio_file.name
            ]
            
            # Create video
            result = subprocess.run(cmd_video, capture_output=True, timeout=20)
            if result.returncode != 0:
                print("  ❌ نتوانست فایل ویدیو ایجاد کند")
                return False
            
            # Create audio
            result = subprocess.run(cmd_audio, capture_output=True, timeout=20)
            if result.returncode != 0:
                print("  ❌ نتوانست فایل صوتی ایجاد کند")
                return False
            
            # Test video streams
            video_streams = self.downloader._probe_file_streams(video_file.name, 'ffprobe')
            if video_streams and video_streams.get('has_video') and video_streams.get('has_audio'):
                print("  ✅ stream های ویدیو شناسایی شدند")
            else:
                print("  ❌ stream های ویدیو شناسایی نشدند")
                return False
            
            # Test audio streams
            audio_streams = self.downloader._probe_file_streams(audio_file.name, 'ffprobe')
            if audio_streams and audio_streams.get('has_audio') and not audio_streams.get('has_video'):
                print("  ✅ stream های صوتی شناسایی شدند")
            else:
                print("  ❌ stream های صوتی شناسایی نشدند")
                return False
            
            return True
            
        except Exception as e:
            print(f"  ❌ خطا در تست stream ها: {e}")
            return False
        finally:
            # Cleanup
            try:
                os.unlink(video_file.name)
                os.unlink(audio_file.name)
            except:
                pass
    
    async def run_all_tests(self):
        """اجرای تمام تست‌ها"""
        print("🚀 تست ساده عملکردهای اصلی")
        print("=" * 50)
        
        tests = [
            ("در دسترس بودن ابزارها", self.test_ffmpeg_availability),
            ("مقداردهی downloader", self.test_downloader_initialization),
            ("مقداردهی selector", self.test_selector_initialization),
            ("توابع metadata", self.test_metadata_functions),
            ("بررسی یکپارچگی فایل", self.test_file_integrity_check),
            ("بررسی stream ها", self.test_stream_probing)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            print(f"\n🔍 {test_name}...")
            try:
                if asyncio.iscoroutinefunction(test_func):
                    result = await test_func()
                else:
                    result = test_func()
                
                results[test_name] = result
                status = "✅ موفق" if result else "❌ ناموفق"
                print(f"  {status}")
                
            except Exception as e:
                results[test_name] = False
                print(f"  ❌ خطا: {e}")
        
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
        
        with open('simple_functionality_test_results.json', 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 نتایج در simple_functionality_test_results.json ذخیره شد")
        
        success_rate = passed_tests / total_tests * 100
        if success_rate >= 80:
            print(f"\n🎉 تست عملکردهای اصلی موفقیت‌آمیز! ({success_rate:.1f}%)")
            return True
        else:
            print(f"\n⚠️ تست عملکردهای اصلی نیاز به بهبود دارد ({success_rate:.1f}%)")
            return False

async def main():
    """تابع اصلی"""
    tester = SimpleFunctionalityTest()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✅ تست عملکردهای اصلی موفقیت‌آمیز بود")
    else:
        print("\n❌ تست عملکردهای اصلی نیاز به بررسی دارد")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())