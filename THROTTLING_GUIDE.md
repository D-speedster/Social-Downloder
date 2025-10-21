# راهنمای تنظیمات Throttling تلگرام

این راهنما توضیح می‌دهد که چگونه تنظیمات throttling در این بات برای جلوگیری از محدودیت‌های نرخ تلگرام بهینه‌سازی شده است.

## تغییرات اعمال شده

### 1. تنظیمات کلاینت تلگرام (`bot.py`)
- **sleep_threshold**: از 60 به 300 ثانیه افزایش یافت
- **flood_sleep_threshold**: 120 ثانیه اضافه شد
- **max_workers**: به حداکثر 4 محدود شد
- **max_concurrent_transmissions**: به 2 محدود شد

### 2. توابع جدید در `stream_utils.py`

#### `calculate_upload_delay(file_size_mb, concurrent_uploads)`
محاسبه تأخیر بهینه بر اساس اندازه فایل:
- فایل‌های کوچک (< 10MB): 100ms تأخیر
- فایل‌های متوسط (10-50MB): 200ms تأخیر  
- فایل‌های بزرگ (> 50MB): 500ms تأخیر

#### `throttled_upload_with_retry(upload_func, max_retries, base_delay)`
مکانیزم تلاش مجدد با exponential backoff:
- مدیریت خطاهای FloodWaitError و SlowModeWaitError
- تلاش مجدد خودکار با تأخیر افزایشی
- حداکثر 3 تلاش مجدد

### 3. بهینه‌سازی توابع موجود
- **smart_upload_strategy**: استفاده از throttling جدید
- **concurrent_download_upload**: اضافه شدن کنترل‌های throttling

## تنظیمات قابل سفارشی‌سازی

تمام تنظیمات throttling از طریق متغیرهای محیطی قابل تنظیم هستند:

```env
# تنظیمات اصلی throttling
TELEGRAM_SLEEP_THRESHOLD=300
TELEGRAM_FLOOD_SLEEP_THRESHOLD=120
TELEGRAM_MAX_CONCURRENT=2
TELEGRAM_MAX_WORKERS=4

# تأخیرهای آپلود
TELEGRAM_UPLOAD_DELAY_SMALL=0.1
TELEGRAM_UPLOAD_DELAY_MEDIUM=0.2
TELEGRAM_UPLOAD_DELAY_LARGE=0.5

# تنظیمات تلاش مجدد
TELEGRAM_RETRY_ATTEMPTS=3
TELEGRAM_BASE_RETRY_DELAY=1.0
```

## توصیه‌های بهینه‌سازی

### برای سرورهای پرترافیک:
```env
TELEGRAM_SLEEP_THRESHOLD=600
TELEGRAM_MAX_CONCURRENT=1
TELEGRAM_UPLOAD_DELAY_LARGE=1.0
```

### برای استفاده شخصی:
```env
TELEGRAM_SLEEP_THRESHOLD=180
TELEGRAM_MAX_CONCURRENT=3
TELEGRAM_UPLOAD_DELAY_SMALL=0.05
```

### برای فایل‌های بزرگ:
```env
TELEGRAM_UPLOAD_DELAY_LARGE=2.0
TELEGRAM_RETRY_ATTEMPTS=5
TELEGRAM_BASE_RETRY_DELAY=2.0
```

## نکات مهم

1. **تعادل بین سرعت و پایداری**: تنظیمات محافظه‌کارانه‌تر باعث آپلود آهسته‌تر اما پایدارتر می‌شود

2. **نظارت بر لاگ‌ها**: در صورت مشاهده خطاهای مکرر FloodWait، تنظیمات را محافظه‌کارانه‌تر کنید

3. **تست تدریجی**: تنظیمات را به تدریج تغییر دهید و عملکرد را نظارت کنید

4. **محیط تولید**: در محیط تولید حتماً از تنظیمات محافظه‌کارانه‌تر استفاده کنید

## عیب‌یابی

### اگر همچنان FloodWait دریافت می‌کنید:
1. `TELEGRAM_SLEEP_THRESHOLD` را افزایش دهید
2. `TELEGRAM_MAX_CONCURRENT` را کاهش دهید
3. تأخیرهای آپلود را افزایش دهید

### اگر آپلود خیلی آهسته است:
1. `TELEGRAM_UPLOAD_DELAY_*` را کاهش دهید
2. `TELEGRAM_MAX_CONCURRENT` را افزایش دهید (با احتیاط)
3. `TELEGRAM_MAX_WORKERS` را افزایش دهید

## مانیتورینگ

برای نظارت بر عملکرد throttling:
- لاگ‌های "FloodWaitError" و "SlowModeWaitError" را بررسی کنید
- زمان آپلود فایل‌ها را اندازه‌گیری کنید
- تعداد تلاش‌های مجدد را نظارت کنید