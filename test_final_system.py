#!/usr/bin/env python3
"""
تست نهایی سیستم دانلود یوتیوب
بررسی merge واقعی، metadata صحیح و thumbnail
"""

import asyncio
import os
import sys
import time
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from plugins.youtube_advanced_downloader import YouTubeAdvancedDownloader
from plugins.youtube_quality_selector import YouTubeQualitySelector

# Test URLs - مجموعه‌ای از ویدئوهای مختلف
TEST_VIDEOS = [
    {
        'name': 'Short Video (1080p)',
        'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',  # Rick Roll - کوتاه و معروف
        'expected_qualities': ['1080p', '720p', '480p']
    },
    {
        'name': 'Music Video',
        'url': 'https://www.youtube.com/watch?v=kJQP7kiw5Fk',  # Despacito - ویدئو موزیک
        'expected_qualities': ['1080p', '720p']
    },
    {
        'name': 'Educational Video',
        'url': 'https://www.youtube.com/watch?v=9bZkp7q19f0',  # PSY - Gangnam Style
        'expected_qualities': ['1080p', '720p', '480p']
    }
]

class TestResults:
    def __init__(self):
        self.results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
    
    def add_result(self, test_name, success, details):
        self.total_tests += 1
        if success:
            self.passed_tests += 1
            status = "✅ PASS"
        else:
            self.failed_tests += 1
            status = "❌ FAIL"
        
        result = {
            'test': test_name,
            'status': status,
            'success': success,
            'details': details,
            'timestamp': time.strftime('%H:%M:%S')
        }
        self.results.append(result)
        print(f"{status} - {test_name}: {details}")
    
    def print_summary(self):
        print("\n" + "="*60)
        print("📊 خلاصه نتایج تست")
        print("="*60)
        print(f"🔢 تعداد کل تست‌ها: {self.total_tests}")
        print(f"✅ موفق: {self.passed_tests}")
        print(f"❌ ناموفق: {self.failed_tests}")
        print(f"📈 درصد موفقیت: {(self.passed_tests/self.total_tests)*100:.1f}%")
        print("="*60)

async def test_quality_extraction(test_results):
    """تست استخراج کیفیت‌ها"""
    print("\n🔍 تست استخراج کیفیت‌ها...")
    
    selector = YouTubeQualitySelector()
    
    for video in TEST_VIDEOS:
        try:
            start_time = time.time()
            qualities = await selector.get_quality_options(video['url'])
            extraction_time = time.time() - start_time
            
            if qualities and 'formats' in qualities:
                available_qualities = [f['quality'] for f in qualities['formats'] if f['type'] != 'audio_only']
                test_results.add_result(
                    f"Quality Extraction - {video['name']}", 
                    True,
                    f"Found {len(available_qualities)} qualities in {extraction_time:.2f}s: {', '.join(available_qualities[:3])}"
                )
            else:
                test_results.add_result(
                    f"Quality Extraction - {video['name']}", 
                    False,
                    "No qualities found"
                )
        except Exception as e:
            test_results.add_result(
                f"Quality Extraction - {video['name']}", 
                False,
                f"Error: {str(e)[:50]}"
            )

async def test_download_and_merge(test_results):
    """تست دانلود و merge"""
    print("\n⬇️ تست دانلود و merge...")
    
    downloader = YouTubeAdvancedDownloader()
    selector = YouTubeQualitySelector()
    
    # تست با یک ویدئو
    test_video = TEST_VIDEOS[0]
    
    try:
        # Get qualities
        qualities = await selector.get_quality_options(test_video['url'])
        if not qualities or 'formats' not in qualities:
            test_results.add_result("Download Test", False, "Could not get qualities")
            return
        
        # انتخاب کیفیت 720p یا اولین کیفیت موجود
        selected_quality = None
        for fmt in qualities['formats']:
            if fmt['type'] != 'audio_only' and '720' in fmt['quality']:
                selected_quality = fmt
                break
        
        if not selected_quality:
            selected_quality = qualities['formats'][0]  # اولین کیفیت
        
        print(f"📥 دانلود {selected_quality['quality']} - {selected_quality['type']}")
        
        # Download
        start_time = time.time()
        result = await downloader.download_and_merge(
            url=test_video['url'],
            quality_info=selected_quality,
            callback=None
        )
        download_time = time.time() - start_time
        
        if result.get('success'):
            file_path = result['file_path']
            file_size = result['file_size']
            
            # بررسی وجود فایل
            if os.path.exists(file_path):
                # Get metadata
                metadata = await downloader.get_file_metadata(file_path)
                
                # بررسی metadata
                width = metadata.get('width', 0)
                height = metadata.get('height', 0)
                duration = metadata.get('duration', 0)
                
                # بررسی صحت metadata
                metadata_ok = True
                issues = []
                
                if width <= 320 and height <= 320:
                    metadata_ok = False
                    issues.append(f"Low resolution: {width}x{height}")
                
                if duration <= 0:
                    metadata_ok = False
                    issues.append("Zero duration")
                
                if metadata_ok:
                    test_results.add_result(
                        "Download & Merge", 
                        True,
                        f"Success! {width}x{height}, {duration:.1f}s, {file_size/(1024*1024):.1f}MB in {download_time:.2f}s"
                    )
                else:
                    test_results.add_result(
                        "Download & Merge", 
                        False,
                        f"Metadata issues: {', '.join(issues)}"
                    )
                
                # پاک کردن فایل تست
                try:
                    os.unlink(file_path)
                except:
                    pass
                    
            else:
                test_results.add_result("Download & Merge", False, "File not found after download")
        else:
            error_msg = result.get('error', 'Unknown error')
            test_results.add_result("Download & Merge", False, f"Download failed: {error_msg}")
            
    except Exception as e:
        test_results.add_result("Download & Merge", False, f"Exception: {str(e)[:50]}")

async def test_thumbnail_embedding(test_results):
    """تست thumbnail embedding"""
    print("\n🖼️ تست thumbnail embedding...")
    
    downloader = YouTubeAdvancedDownloader()
    selector = YouTubeQualitySelector()
    
    test_video = TEST_VIDEOS[0]
    
    try:
        qualities = await selector.get_quality_options(test_video['url'])
        if not qualities or 'formats' not in qualities:
            test_results.add_result("Thumbnail Test", False, "Could not get qualities")
            return
        
        # انتخاب کیفیت پایین برای تست سریع
        selected_quality = None
        for fmt in qualities['formats']:
            if fmt['type'] != 'audio_only' and '480' in fmt['quality']:
                selected_quality = fmt
                break
        
        if not selected_quality:
            selected_quality = qualities['formats'][0]
        
        # Download
        result = await downloader.download_and_merge(
            url=test_video['url'],
            quality_info=selected_quality,
            callback=None
        )
        
        if result.get('success'):
            file_path = result['file_path']
            
            # بررسی وجود thumbnail در فایل با ffprobe
            try:
                import subprocess
                
                # جستجو برای ffprobe
                ffprobe_path = None
                possible_paths = [
                    'ffprobe',
                    'ffprobe.exe',
                    r'C:\ffmpeg\bin\ffprobe.exe',
                    r'C:\Program Files\ffmpeg\bin\ffprobe.exe'
                ]
                
                for path in possible_paths:
                    try:
                        subprocess.run([path, '-version'], capture_output=True, check=True)
                        ffprobe_path = path
                        break
                    except:
                        continue
                
                if ffprobe_path:
                    # بررسی streams برای thumbnail
                    cmd = [
                        ffprobe_path,
                        '-v', 'quiet',
                        '-print_format', 'json',
                        '-show_streams',
                        file_path
                    ]
                    
                    result_probe = subprocess.run(cmd, capture_output=True, text=True)
                    if result_probe.returncode == 0:
                        streams_data = json.loads(result_probe.stdout)
                        
                        # جستجو برای stream تصویری که ممکن است thumbnail باشد
                        has_thumbnail = False
                        for stream in streams_data.get('streams', []):
                            if stream.get('codec_name') in ['mjpeg', 'png'] or stream.get('disposition', {}).get('attached_pic'):
                                has_thumbnail = True
                                break
                        
                        test_results.add_result(
                            "Thumbnail Embedding", 
                            has_thumbnail,
                            "Thumbnail found in video" if has_thumbnail else "No thumbnail detected"
                        )
                    else:
                        test_results.add_result("Thumbnail Embedding", False, "Could not probe file")
                else:
                    test_results.add_result("Thumbnail Embedding", False, "ffprobe not available")
                
            except Exception as e:
                test_results.add_result("Thumbnail Embedding", False, f"Probe error: {str(e)[:30]}")
            
            # پاک کردن فایل
            try:
                os.unlink(file_path)
            except:
                pass
        else:
            test_results.add_result("Thumbnail Embedding", False, "Download failed")
            
    except Exception as e:
        test_results.add_result("Thumbnail Embedding", False, f"Exception: {str(e)[:50]}")

async def main():
    print("🚀 شروع تست نهایی سیستم دانلود یوتیوب")
    print("="*60)
    
    test_results = TestResults()
    
    # اجرای تست‌ها
    await test_quality_extraction(test_results)
    await test_download_and_merge(test_results)
    await test_thumbnail_embedding(test_results)
    
    # نمایش خلاصه
    test_results.print_summary()
    
    # ذخیره نتایج
    results_file = "test_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'summary': {
                'total': test_results.total_tests,
                'passed': test_results.passed_tests,
                'failed': test_results.failed_tests,
                'success_rate': f"{(test_results.passed_tests/test_results.total_tests)*100:.1f}%"
            },
            'results': test_results.results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 نتایج در فایل {results_file} ذخیره شد")
    
    if test_results.failed_tests == 0:
        print("\n🎉 تمام تست‌ها موفق! سیستم آماده استفاده است.")
    else:
        print(f"\n⚠️ {test_results.failed_tests} تست ناموفق. نیاز به بررسی بیشتر.")

if __name__ == "__main__":
    asyncio.run(main())