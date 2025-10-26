# بهینه‌سازی سرعت آپلود

## 🐌 مشکل قبلی

- **زمان آپلود**: 14 دقیقه برای 131MB
- **سرعت محاسبه شده**: ~0.16 MB/s
- **سرعت سرور**: 300 Mbps (~37.5 MB/s)
- **کارایی**: فقط 0.4% از ظرفیت سرور!

## ⚡ بهینه‌سازی‌های اعمال شده

### 1. افزایش اندازه Chunk
```python
# قبل:
CHUNK_SIZE = 524288  # 512KB

# بعد:
CHUNK_SIZE = 1048576  # 1MB (برای سرورهای پرسرعت)
```

### 2. بهینه‌سازی Progress Callback
```python
# قبل: هر بار فراخوانی می‌شد (overhead زیاد)
async def progress_wrapper(current, total):
    await progress_callback(current, total)

# بعد: throttling برای فایل‌های بزرگ
progress_update_interval = 2.0 if file_size_mb > 100 else 1.0
if current_time - last_progress_time >= progress_update_interval:
    await progress_callback(current, total)
```

### 3. تنظیمات بهینه Pyrogram
```python
await client.send_video(
    supports_streaming=True,  # فعال‌سازی streaming
    disable_notification=False,
    parse_mode=None  # حذف پردازش اضافی
)
```

### 4. اضافه کردن Thumbnail
```python
# دانلود thumbnail قبل از آپلود
thumbnail_path = await download_thumbnail(video_info['thumbnail'])
await client.send_video(thumb=thumbnail_path)
```

## 📊 انتظار بهبود

### محاسبات تئوری:
- **سرعت سرور**: 300 Mbps = 37.5 MB/s
- **سرعت واقعی تلگرام**: معمولاً 20-30% از حداکثر
- **سرعت انتظاری**: 7.5-11.25 MB/s
- **زمان انتظاری برای 131MB**: 12-17 ثانیه

### مقایسه:
| معیار | قبل | بعد (انتظار) | بهبود |
|-------|-----|-------------|-------|
| زمان آپلود | 14 دقیقه | 15-20 ثانیه | 40-50x سریع‌تر |
| سرعت | 0.16 MB/s | 7-11 MB/s | 40-70x سریع‌تر |
| کارایی | 0.4% | 20-30% | 50-75x بهتر |

## 🔧 تنظیمات اضافی (اختیاری)

### در bot.py:
```python
client_config = {
    "workers": 32,  # افزایش workers
    "max_concurrent_transmissions": 16,  # افزایش همزمانی
    "sleep_threshold": 30,  # کاهش sleep
}
```

## 🧪 تست

برای تست بهبود سرعت:

1. **قبل از تست**: یادداشت زمان شروع
2. **ارسال ویدیو**: لینک یوتیوب با حجم متوسط (50-200MB)
3. **اندازه‌گیری**: زمان از شروع دانلود تا ارسال نهایی
4. **مقایسه**: با زمان قبلی

### مثال تست:
```
ویدیو: 131MB
زمان قبل: 14 دقیقه (840 ثانیه)
زمان بعد: ؟ ثانیه
بهبود: ؟x سریع‌تر
```

## 🎯 نتیجه انتظاری

با این بهینه‌سازی‌ها، انتظار می‌رود:
- ✅ سرعت آپلود 40-50 برابر بهبود یابد
- ✅ Thumbnail روی ویدیوها نمایش داده شود
- ✅ تجربه کاربری بسیار بهتر شود
- ✅ از ظرفیت سرور بهتر استفاده شود

---

**وضعیت**: ✅ اعمال شده  
**تاریخ**: 26 اکتبر 2025  
**هدف**: کاهش زمان آپلود از 14 دقیقه به 15-20 ثانیه