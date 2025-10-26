"""
تنظیمات سیستم یوتیوب
این فایل را در config.py خود اضافه کنید
"""

# کیفیت‌های پشتیبانی شده (فقط این 4 کیفیت)
YOUTUBE_SUPPORTED_QUALITIES = ['360', '480', '720', '1080']

# حداکثر حجم فایل برای دانلود (بایت)
# 2GB = 2 * 1024 * 1024 * 1024
YOUTUBE_MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024

# تایم‌اوت برای دانلود (ثانیه)
YOUTUBE_DOWNLOAD_TIMEOUT = 1800  # 30 دقیقه

# تایم‌اوت برای آپلود (ثانیه)
YOUTUBE_UPLOAD_TIMEOUT = 1800  # 30 دقیقه

# اندازه chunk برای آپلود (بایت)
YOUTUBE_CHUNK_SIZE = 524288  # 512KB

# فاصله زمانی نمایش پیشرفت (ثانیه)
YOUTUBE_PROGRESS_INTERVAL = 3.0

# تعداد تلاش مجدد در صورت خطا
YOUTUBE_MAX_RETRIES = 3

# استفاده از cache برای اطلاعات ویدیو
YOUTUBE_USE_CACHE = True

# مدت زمان نگهداری cache (ثانیه)
YOUTUBE_CACHE_TTL = 3600  # 1 ساعت

# استفاده از Redis برای cache (توصیه می‌شود)
YOUTUBE_USE_REDIS = False
YOUTUBE_REDIS_HOST = 'localhost'
YOUTUBE_REDIS_PORT = 6379
YOUTUBE_REDIS_DB = 0

# مسیر ذخیره موقت فایل‌ها
YOUTUBE_TEMP_DIR = './downloads/youtube'

# حذف خودکار فایل‌ها بعد از آپلود
YOUTUBE_AUTO_CLEANUP = True

# نمایش thumbnail در پیام‌ها
YOUTUBE_SHOW_THUMBNAIL = True

# فرمت خروجی ویدیو (mp4 توصیه می‌شود)
YOUTUBE_OUTPUT_FORMAT = 'mp4'

# کیفیت صدا برای merge (kbps)
YOUTUBE_AUDIO_QUALITY = 128

# استفاده از ffmpeg برای merge
YOUTUBE_USE_FFMPEG = True

# تنظیمات yt-dlp
YOUTUBE_YDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'concurrent_fragment_downloads': 4,
    'http_chunk_size': 10485760,  # 10MB
}

# پیام‌های سفارشی
YOUTUBE_MESSAGES = {
    'processing': '🔄 در حال پردازش لینک یوتیوب...',
    'downloading': '📥 در حال دانلود از یوتیوب...',
    'uploading': '📤 در حال آپلود به تلگرام...',
    'completed': '✅ دانلود و ارسال با موفقیت انجام شد!',
    'error': '❌ خطا در پردازش ویدیو',
    'queue': '🕒 در صف (نفر {position})',
}

# محدودیت‌های کاربر
YOUTUBE_USER_LIMITS = {
    'max_concurrent_downloads': 1,  # تعداد دانلود همزمان
    'max_daily_downloads': 50,      # تعداد دانلود روزانه
    'max_file_size': 2 * 1024 * 1024 * 1024,  # 2GB
}

# محدودیت‌های VIP (اختیاری)
YOUTUBE_VIP_LIMITS = {
    'max_concurrent_downloads': 3,
    'max_daily_downloads': 200,
    'max_file_size': 4 * 1024 * 1024 * 1024,  # 4GB
}
