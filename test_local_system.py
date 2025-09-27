#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست کامل سیستم با استفاده از فایل‌های محلی
"""

import os
import sys
import asyncio
import json
import subprocess
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plugins.youtube_advanced_downloader import YouTubeAdvancedDownloader
from plugins.youtube_quality_selector import YouTubeQualitySelector

class LocalSystemTest:
    def __init__(self):
        self.downloader = YouTubeAdvancedDownloader()
        self.selector = YouTubeQualitySelector()
        self.test_files = []
        
    def create_test_files(self):
        """ایجاد فایل‌های تست مختلف"""
        print("🎬 ایجاد فایل‌های تست...")
        
        # Test video 1: HD video with audio
        video1_path = "test_video_hd.mp4"
        cmd1 = [
            "ffmpeg", "-y", "-f", "lavfi", 
            "-i", "testsrc2=duration=10:size=1920x1080:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=10",
            "-c:v", "libx264", "-c:a", "aac", "-shortest",
            video1_path
        ]
        
        # Test video 2: SD video with audio
        video2_path = "test_video_sd.mp4"
        cmd2 = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "testsrc2=duration=8:size=854x480:rate=25",
            "-f", "lavfi", "-i", "sine=frequency=500:duration=8",
            "-c:v", "libx264", "-c:a", "aac", "-shortest",
            video2_path
        ]
        
        # Test audio only
        audio_path = "test_audio.m4a"
        cmd3 = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "sine=frequency=440:duration=6",
            "-c:a", "aac",
            audio_path
        ]
        
        try:
            # Create HD video
            print("📹 ایجاد ویدئوی HD...")
            subprocess.run(cmd1, check=True, capture_output=True)
            self.test_files.append(video1_path)
            
            # Create SD video
            print("📹 ایجاد ویدئوی SD...")
            subprocess.run(cmd2, check=True, capture_output=True)
            self.test_files.append(video2_path)
            
            # Create audio
            print("🎵 ایجاد فایل صوتی...")
            subprocess.run(cmd3, check=True, capture_output=True)
            self.test_files.append(audio_path)
            
            print("✅ فایل‌های تست ایجاد شدند")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ خطا در ایجاد فایل‌های تست: {e}")
            return False
    
    async def test_metadata_extraction(self):
        """تست استخراج metadata"""
        print("\n🔍 تست استخراج metadata...")
        results = {}
        
        for file_path in self.test_files:
            if not os.path.exists(file_path):
                continue
                
            print(f"📊 بررسی {file_path}...")
            
            # Extract metadata
            metadata = await self.downloader.get_file_metadata(file_path)
            
            if metadata:
                print(f"  ✅ Metadata استخراج شد:")
                if 'width' in metadata and 'height' in metadata:
                    print(f"    📺 وضوح: {metadata['width']}x{metadata['height']}")
                if 'duration' in metadata:
                    print(f"    ⏱ مدت زمان: {metadata['duration']:.1f} ثانیه")
                if 'size' in metadata:
                    print(f"    📦 حجم: {metadata['size'] / (1024*1024):.2f} MB")
                if 'video_codec' in metadata:
                    print(f"    🎥 کدک ویدیو: {metadata['video_codec']}")
                if 'audio_codec' in metadata:
                    print(f"    🎵 کدک صوتی: {metadata['audio_codec']}")
                
                results[file_path] = {
                    'success': True,
                    'metadata': metadata
                }
            else:
                print(f"  ❌ خطا در استخراج metadata")
                results[file_path] = {
                    'success': False,
                    'metadata': {}
                }
        
        return results
    
    def test_file_integrity(self):
        """تست بررسی یکپارچگی فایل‌ها"""
        print("\n🔍 تست بررسی یکپارچگی فایل‌ها...")
        results = {}
        
        for file_path in self.test_files:
            if not os.path.exists(file_path):
                continue
                
            print(f"🔧 بررسی {file_path}...")
            
            # Test file integrity
            is_valid = self.downloader._verify_file_integrity(file_path, 'ffprobe')
            
            if is_valid:
                print(f"  ✅ فایل معتبر است")
                results[file_path] = {'valid': True}
            else:
                print(f"  ❌ فایل معتبر نیست")
                results[file_path] = {'valid': False}
        
        return results
    
    def test_stream_probing(self):
        """تست بررسی stream های فایل"""
        print("\n🔍 تست بررسی stream ها...")
        results = {}
        
        for file_path in self.test_files:
            if not os.path.exists(file_path):
                continue
                
            print(f"🎬 بررسی stream های {file_path}...")
            
            # Probe streams
            streams = self.downloader._probe_file_streams(file_path, 'ffprobe')
            
            if streams:
                print(f"  ✅ Stream ها شناسایی شدند:")
                if streams.get('has_video'):
                    print(f"    📹 ویدیو: {streams.get('width', 0)}x{streams.get('height', 0)}")
                if streams.get('has_audio'):
                    print(f"    🎵 صوت: موجود")
                
                results[file_path] = {
                    'success': True,
                    'streams': streams
                }
            else:
                print(f"  ❌ خطا در شناسایی stream ها")
                results[file_path] = {
                    'success': False,
                    'streams': {}
                }
        
        return results
    
    def cleanup(self):
        """پاک کردن فایل‌های تست"""
        print("\n🗑️ پاک کردن فایل‌های تست...")
        for file_path in self.test_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"  ✅ {file_path} پاک شد")
            except Exception as e:
                print(f"  ❌ خطا در پاک کردن {file_path}: {e}")
    
    async def run_all_tests(self):
        """اجرای تمام تست‌ها"""
        print("🚀 تست کامل سیستم محلی")
        print("=" * 50)
        
        # Create test files
        if not self.create_test_files():
            print("❌ خطا در ایجاد فایل‌های تست")
            return False
        
        try:
            # Test metadata extraction
            metadata_results = await self.test_metadata_extraction()
            
            # Test file integrity
            integrity_results = self.test_file_integrity()
            
            # Test stream probing
            stream_results = self.test_stream_probing()
            
            # Summary
            print("\n📊 خلاصه نتایج:")
            print("=" * 30)
            
            total_files = len(self.test_files)
            metadata_success = sum(1 for r in metadata_results.values() if r['success'])
            integrity_success = sum(1 for r in integrity_results.values() if r['valid'])
            stream_success = sum(1 for r in stream_results.values() if r['success'])
            
            print(f"📁 تعداد فایل‌های تست: {total_files}")
            print(f"📊 استخراج metadata: {metadata_success}/{total_files}")
            print(f"🔧 بررسی یکپارچگی: {integrity_success}/{total_files}")
            print(f"🎬 بررسی stream ها: {stream_success}/{total_files}")
            
            # Save results
            results = {
                'metadata': metadata_results,
                'integrity': integrity_results,
                'streams': stream_results,
                'summary': {
                    'total_files': total_files,
                    'metadata_success': metadata_success,
                    'integrity_success': integrity_success,
                    'stream_success': stream_success
                }
            }
            
            with open('local_test_results.json', 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 نتایج در local_test_results.json ذخیره شد")
            
            # Check if all tests passed
            all_passed = (metadata_success == total_files and 
                         integrity_success == total_files and 
                         stream_success == total_files)
            
            if all_passed:
                print("\n🎉 تمام تست‌ها موفقیت‌آمیز بودند!")
                return True
            else:
                print("\n⚠️ برخی تست‌ها ناموفق بودند")
                return False
                
        finally:
            # Cleanup
            self.cleanup()

async def main():
    """تابع اصلی"""
    tester = LocalSystemTest()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✅ تست کامل سیستم موفقیت‌آمیز بود")
    else:
        print("\n❌ تست کامل سیستم ناموفق بود")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())