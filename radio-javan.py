from radiojavanapi import Client
import requests
import os
import re
from urllib.parse import urlparse

def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    return re.sub(r'[<>:"/\\|?*]', '', filename)

def download_song(song_url, filename, download_dir="downloads"):
    """Download song from URL and save to specified directory"""
    try:
        # Create downloads directory if it doesn't exist
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        
        # Get the file extension from URL
        parsed_url = urlparse(song_url)
        file_extension = os.path.splitext(parsed_url.path)[1] or '.mp3'
        
        # Create full file path
        full_filename = f"{filename}{file_extension}"
        file_path = os.path.join(download_dir, full_filename)
        
        print(f"در حال دانلود: {full_filename}")
        
        # Download the file
        response = requests.get(song_url, stream=True)
        response.raise_for_status()
        
        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        
        print(f"دانلود کامل شد: {file_path}")
        return file_path
        
    except Exception as e:
        print(f"خطا در دانلود: {e}")
        return None

# Create a Client instance and get a song info. 
client = Client()
song = client.get_song_by_url(
            'https://play.radiojavan.com/song/sijal-baz-mirim-baham-(ft-sami-low)')

print("=" * 60)
print("🎵 مشخصات کامل آهنگ 🎵")
print("=" * 60)

# اطلاعات اصلی آهنگ
print(f"📀 نام آهنگ: {song.name}")
print(f"🎤 هنرمند: {song.artist}")
print(f"💿 آلبوم: {song.album if song.album else 'نامشخص'}")
print(f"📅 تاریخ انتشار: {song.date}")
print(f"⏱️ مدت زمان: {song.duration:.2f} ثانیه ({song.duration/60:.1f} دقیقه)")
print(f"🆔 شناسه: {song.id}")

print("\n" + "=" * 30)
print("📊 آمار و محبوبیت")
print("=" * 30)
print(f"👍 لایک: {song.likes:,}")
print(f"👎 دیسلایک: {song.dislikes}")
print(f"⬇️ تعداد دانلود: {song.downloads:,}")

print("\n" + "=" * 30)
print("🔗 لینک‌های دانلود")
print("=" * 30)
print(f"🎧 کیفیت بالا (HQ): {song.hq_link}")
print(f"🎵 کیفیت متوسط: {song.link}")
print(f"📱 کیفیت پایین (LQ): {song.lq_link}")
print(f"📺 HLS استریم: {song.hls_link}")
print(f"📺 HQ HLS: {song.hq_hls}")
print(f"📱 LQ HLS: {song.lq_hls}")

print("\n" + "=" * 30)
print("👥 اعضای تیم سازنده")
print("=" * 30)
print(f"🏷️ تگ‌های هنرمند: {', '.join(song.artist_tags)}")
print(f"🏷️ تگ‌های اعتبار: {', '.join(song.credit_tags)}")
if song.credits:
    print(f"📝 اعتبارات:\n{song.credits}")

print("\n" + "=" * 30)
print("🖼️ تصاویر")
print("=" * 30)
print(f"🖼️ تصویر اصلی: {song.photo}")
print(f"🖼️ تصویر کوچک: {song.thumbnail}")

if song.lyric:
    print("\n" + "=" * 30)
    print("📝 متن آهنگ")
    print("=" * 30)
    # نمایش فقط 200 کاراکتر اول از متن
    lyric_preview = song.lyric[:200] + "..." if len(song.lyric) > 200 else song.lyric
    print(lyric_preview)

if hasattr(song, 'stories') and song.stories:
    print(f"\n📱 تعداد استوری‌ها: {len(song.stories)}")

print("\n" + "=" * 60)

# Download the song
if song.hq_link:
    # Create filename from song name and artist
    filename = sanitize_filename(f"{song.artist} - {song.name}")
    # Convert HttpUrl object to string
    download_url = str(song.hq_link)
    download_song(download_url, filename)
else:
    print("لینک دانلود یافت نشد!")