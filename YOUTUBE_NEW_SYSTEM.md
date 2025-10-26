# سیستم جدید دانلود از یوتیوب

## ساختار فایل‌ها

```
plugins/
├── youtube_handler.py      # Handler اصلی - دریافت لینک و نمایش کیفیت‌ها
├── youtube_downloader.py   # دانلود با yt-dlp
├── youtube_uploader.py     # آپلود بهینه با streaming
└── youtube_callback.py     # مدیریت callback انتخاب کیفیت
```

## ویژگی‌های جدید

### 1. کیفیت‌های محدود (4 کیفیت)
- 360p
- 480p
- 720p
- 1080p
- فقط صدا (بهترین کیفیت)

### 2. نمایش دکمه‌ها (2 در هر سطر)
```
[360p] [480p]
[720p] [1080p]
[🎵 فقط صدا]
```

### 3. حذف مرحله "فایل یا لینک"
- بعد از انتخاب کیفیت، مستقیماً دانلود شروع می‌شود

### 4. بهینه‌سازی آپلود
- استفاده از streaming
- Chunking بهینه (512KB)
- نمایش پیشرفت هر 3 ثانیه

## نحوه استفاده

1. کاربر لینک یوتیوب ارسال می‌کند
2. اطلاعات ویدیو + thumbnail نمایش داده می‌شود
3. کاربر کیفیت را انتخاب می‌کند
4. دانلود و آپلود به صورت خودکار انجام می‌شود

## فایل‌های قدیمی که باید حذف شوند

- youtube.py
- youtube_new_handler.py
- youtube_new_callback.py
- youtube_callback_query.py
- youtube_quality_selector.py
- youtube_advanced_downloader.py
- youtube_helpers.py

## نکات مهم

- از concurrency برای مدیریت صف استفاده می‌شود
- Cache در حافظه برای اطلاعات ویدیو (در production از Redis استفاده کنید)
- Logging کامل برای debugging
- Error handling جامع
