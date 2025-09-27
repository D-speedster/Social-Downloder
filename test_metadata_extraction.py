#!/usr/bin/env python3
"""
تست استخراج metadata بدون دانلود
"""

import asyncio
import os
import sys
import time
import subprocess
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from plugins.youtube_advanced_downloader import YouTubeAdvancedDownloader

async def test_metadata_functions():
    print("🚀 تست توابع metadata")
    print("="*50)
    
    downloader = YouTubeAdvancedDownloader()
    
    # تست 1: بررسی وجود ffprobe
    print("🔍 بررسی ffprobe...")
    
    ffprobe_paths = [
        'ffprobe',
        'ffprobe.exe',
        r'C:\ffmpeg\bin\ffprobe.exe',
        r'C:\Program Files\ffmpeg\bin\ffprobe.exe'
    ]
    
    ffprobe_found = None
    for path in ffprobe_paths:
        try:
            result = subprocess.run([path, '-version'], capture_output=True, check=True)
            ffprobe_found = path
            print(f"✅ ffprobe یافت شد: {path}")
            break
        except:
            continue
    
    if not ffprobe_found:
        print("❌ ffprobe یافت نشد")
        return
    
    # تست 2: بررسی ffmpeg
    print("\n🔍 بررسی ffmpeg...")
    
    ffmpeg_paths = [
        'ffmpeg',
        'ffmpeg.exe',
        r'C:\ffmpeg\bin\ffmpeg.exe',
        r'C:\Program Files\ffmpeg\bin\ffmpeg.exe'
    ]
    
    ffmpeg_found = None
    for path in ffmpeg_paths:
        try:
            result = subprocess.run([path, '-version'], capture_output=True, check=True)
            ffmpeg_found = path
            print(f"✅ ffmpeg یافت شد: {path}")
            break
        except:
            continue
    
    if not ffmpeg_found:
        print("❌ ffmpeg یافت نشد")
        return
    
    # تست 3: ایجاد فایل تست
    print("\n🎬 ایجاد فایل ویدئوی تست...")
    
    test_video_path = "test_video.mp4"
    
    # ایجاد یک ویدئوی کوتاه تست با ffmpeg
    cmd = [
        ffmpeg_found,
        '-f', 'lavfi',
        '-i', 'testsrc=duration=5:size=1280x720:rate=30',
        '-f', 'lavfi', 
        '-i', 'sine=frequency=1000:duration=5',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-t', '5',
        '-y',  # overwrite
        test_video_path
    ]
    
    try:
        print("📹 در حال ایجاد ویدئوی تست...")
        result = subprocess.run(cmd, capture_output=True, check=True)
        print("✅ ویدئوی تست ایجاد شد")
    except subprocess.CalledProcessError as e:
        print(f"❌ خطا در ایجاد ویدئو: {e}")
        return
    
    # تست 4: استخراج metadata
    print("\n🔍 تست استخراج metadata...")
    
    try:
        metadata = await downloader.get_file_metadata(test_video_path)
        
        if metadata:
            print("✅ Metadata استخراج شد:")
            print(f"  📊 وضوح: {metadata.get('width', 0)}x{metadata.get('height', 0)}")
            print(f"  ⏱ مدت زمان: {metadata.get('duration', 0):.1f} ثانیه")
            print(f"  📦 حجم: {metadata.get('size', 0)/(1024*1024):.2f} MB")
            print(f"  🎥 کدک ویدیو: {metadata.get('video_codec', 'نامشخص')}")
            print(f"  🎵 کدک صوتی: {metadata.get('audio_codec', 'نامشخص')}")
            print(f"  📈 بیت ریت: {metadata.get('bitrate', 0)} kbps")
            
            # بررسی صحت
            width = metadata.get('width', 0)
            height = metadata.get('height', 0)
            duration = metadata.get('duration', 0)
            
            if width == 1280 and height == 720 and duration > 4:
                print("✅ Metadata صحیح است")
            else:
                print("⚠️ مشکل در metadata:")
                if width != 1280 or height != 720:
                    print(f"  - وضوح اشتباه: انتظار 1280x720، دریافت {width}x{height}")
                if duration < 4:
                    print(f"  - مدت زمان اشتباه: انتظار ~5 ثانیه، دریافت {duration:.1f}")
        else:
            print("❌ نتوانست metadata را استخراج کند")
            
    except Exception as e:
        print(f"❌ خطا در استخراج metadata: {e}")
    
    # تست 5: بررسی integrity
    print("\n🔍 تست بررسی integrity...")
    
    try:
        # استفاده از تابع _verify_file_integrity
        is_valid = await downloader._verify_file_integrity(test_video_path, 'video')
        
        if is_valid:
            print("✅ فایل معتبر است")
        else:
            print("❌ فایل نامعتبر است")
            
    except Exception as e:
        print(f"❌ خطا در بررسی integrity: {e}")
    
    # پاک کردن فایل تست
    try:
        os.unlink(test_video_path)
        print("\n🗑️ فایل تست پاک شد")
    except:
        print("\n⚠️ نتوانست فایل تست را پاک کند")
    
    print("\n" + "="*50)
    print("✅ تست metadata کامل شد")

if __name__ == "__main__":
    asyncio.run(test_metadata_functions())