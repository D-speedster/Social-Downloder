#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
تست ساده yt-dlp با تنظیمات جدید
"""

import yt_dlp
import os

def test_ytdlp_direct():
    """تست مستقیم yt-dlp با تنظیمات جدید"""
    
    url = "https://www.youtube.com/watch?v=5fNDHDIj-78"  # ویدیوی تست اصلی
    cookie_file = "cookie.json"
    
    print("🔍 تست مستقیم yt-dlp با تنظیمات جدید:")
    print(f"🔗 URL: {url}")
    print(f"🍪 کوکی: {cookie_file}")
    print(f"📁 وجود کوکی: {os.path.exists(cookie_file)}")
    
    # تنظیمات جدید (همان چیزی که روی سرور کار کرده) - ابتدا بدون کوکی تست
    ydl_opts = {
        'quiet': False,  # لاگ کامل برای دیباگ
        'no_warnings': False,
        'extract_flat': False,
        'skip_download': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['mweb', 'ios']
            }
        },
        'remote_components': ['ejs:github']
        # بدون کوکی در تست اول
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("📡 در حال استخراج اطلاعات (بدون کوکی)...")
            info = ydl.extract_info(url, download=False)
            
            if info and 'formats' in info:
                print(f"✅ موفقیت! تعداد فرمت: {len(info['formats'])}")
                print(f"📺 عنوان: {info.get('title', 'نامشخص')}")
                print(f"⏱️  مدت: {info.get('duration', 0)} ثانیه")
                
                # نمایش فرمت‌های ویدیو
                video_formats = [f for f in info['formats'] if f.get('height')]
                print(f"\n📹 فرمت‌های ویدیو ({len(video_formats)} عدد):")
                
                for fmt in sorted(video_formats, key=lambda x: x.get('height', 0), reverse=True):
                    height = fmt.get('height')
                    ext = fmt.get('ext', 'unknown')
                    vcodec = fmt.get('vcodec', 'unknown')[:15]  # محدود کردن طول
                    filesize = fmt.get('filesize')
                    
                    if filesize:
                        size_mb = round(filesize / (1024 * 1024), 1)
                        print(f"  • {height}p - {ext} ({vcodec}) - {size_mb} MB")
                    else:
                        print(f"  • {height}p - {ext} ({vcodec})")
                        
                return True
            else:
                print("❌ نتیجه خالی")
                return False
                
    except Exception as e:
        print(f"❌ خطا: {str(e)}")
        return False

def test_with_cookie():
    """تست با کوکی"""
    
    url = "https://www.youtube.com/watch?v=5fNDHDIj-78"  # ویدیوی تست اصلی
    cookie_file = "cookie.json"
    
    print("\n" + "="*50)
    print("🍪 تست با کوکی:")
    
    ydl_opts = {
        'quiet': False,
        'no_warnings': False,
        'extract_flat': False,
        'skip_download': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['mweb', 'ios']
            }
        },
        'remote_components': ['ejs:github'],
        'cookiefile': "cookie.json"
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if info and 'formats' in info:
                video_formats = [f for f in info['formats'] if f.get('height')]
                print(f"✅ موفقیت با کوکی! فرمت‌های ویدیو: {len(video_formats)}")
                return True
            else:
                print("❌ نتیجه خالی با کوکی")
                return False
                
    except Exception as e:
        print(f"❌ خطا با کوکی: {str(e)}")
        return False

if __name__ == "__main__":
    # تست بدون کوکی
    success1 = test_ytdlp_direct()
    
    # تست با کوکی
    success2 = test_with_cookie()
    
    print("\n" + "="*50)
    print("📋 نتایج:")
    print(f"🔍 بدون کوکی: {'✅' if success1 else '❌'}")
    print(f"🍪 با کوکی: {'✅' if success2 else '❌'}")