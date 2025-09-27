#!/usr/bin/env python3
"""
تست ساده دانلود یوتیوب با ویدئوی عمومی
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from plugins.youtube_advanced_downloader import YouTubeAdvancedDownloader
from plugins.youtube_quality_selector import YouTubeQualitySelector

# ویدئوی تست - Big Buck Bunny trailer (عمومی و کوتاه)
TEST_URL = "https://www.youtube.com/watch?v=YE7VzlLtp-4"  # Big Buck Bunny

async def test_simple_download():
    print("🚀 تست ساده دانلود یوتیوب")
    print("="*50)
    
    try:
        # Initialize components
        selector = YouTubeQualitySelector()
        downloader = YouTubeAdvancedDownloader()
        
        print("🔍 استخراج کیفیت‌ها...")
        start_time = time.time()
        
        qualities = await selector.get_quality_options(TEST_URL)
        extraction_time = time.time() - start_time
        
        if not qualities or 'formats' not in qualities:
            print("❌ خطا: نتوانست کیفیت‌ها را استخراج کند")
            return
        
        print(f"✅ {len(qualities['formats'])} کیفیت در {extraction_time:.2f} ثانیه یافت شد")
        print(f"📺 عنوان: {qualities.get('title', 'نامشخص')}")
        
        # نمایش کیفیت‌های موجود
        print("\n📋 کیفیت‌های موجود:")
        for i, fmt in enumerate(qualities['formats'][:5]):  # نمایش 5 کیفیت اول
            print(f"  {i+1}. {fmt['quality']} - {fmt['type']} ({fmt.get('filesize_mb', '?')} MB)")
        
        # انتخاب کیفیت پایین برای تست سریع
        selected_quality = None
        for fmt in qualities['formats']:
            if fmt['type'] != 'audio_only' and ('480' in fmt['quality'] or '360' in fmt['quality']):
                selected_quality = fmt
                break
        
        if not selected_quality:
            selected_quality = qualities['formats'][0]  # اولین کیفیت
        
        print(f"\n📥 دانلود {selected_quality['quality']} - {selected_quality['type']}")
        
        # دانلود
        download_start = time.time()
        result = await downloader.download_and_merge(
            url=TEST_URL,
            quality_info=selected_quality,
            callback=None
        )
        download_time = time.time() - download_start
        
        if result.get('success'):
            file_path = result['file_path']
            file_size = result['file_size']
            
            print(f"✅ دانلود موفق در {download_time:.2f} ثانیه")
            print(f"📁 مسیر فایل: {file_path}")
            print(f"📦 حجم فایل: {file_size/(1024*1024):.2f} MB")
            
            # بررسی metadata
            print("\n🔍 بررسی metadata...")
            metadata = await downloader.get_file_metadata(file_path)
            
            if metadata:
                width = metadata.get('width', 0)
                height = metadata.get('height', 0)
                duration = metadata.get('duration', 0)
                video_codec = metadata.get('video_codec', 'نامشخص')
                audio_codec = metadata.get('audio_codec', 'نامشخص')
                
                print(f"📊 وضوح: {width}x{height}")
                print(f"⏱ مدت زمان: {duration:.1f} ثانیه")
                print(f"🎥 کدک ویدیو: {video_codec}")
                print(f"🎵 کدک صوتی: {audio_codec}")
                
                # بررسی صحت metadata
                if width > 320 and height > 320 and duration > 0:
                    print("✅ Metadata صحیح است")
                else:
                    print("⚠️ مشکل در metadata:")
                    if width <= 320 or height <= 320:
                        print(f"  - وضوح پایین: {width}x{height}")
                    if duration <= 0:
                        print(f"  - مدت زمان صفر: {duration}")
            else:
                print("❌ نتوانست metadata را استخراج کند")
            
            # پاک کردن فایل تست
            try:
                os.unlink(file_path)
                print("🗑️ فایل تست پاک شد")
            except:
                print("⚠️ نتوانست فایل تست را پاک کند")
                
        else:
            error_msg = result.get('error', 'خطای نامشخص')
            print(f"❌ دانلود ناموفق: {error_msg}")
        
        print("\n" + "="*50)
        print("✅ تست کامل شد")
        
    except Exception as e:
        print(f"❌ خطای کلی: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_simple_download())