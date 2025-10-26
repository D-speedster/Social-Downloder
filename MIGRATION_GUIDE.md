# راهنمای مهاجرت به سیستم جدید یوتیوب

## مراحل مهاجرت

### 1. فایل‌های جدید ایجاد شده
✅ `plugins/youtube_handler.py` - Handler اصلی
✅ `plugins/youtube_downloader.py` - دانلودر
✅ `plugins/youtube_uploader.py` - آپلودر
✅ `plugins/youtube_callback.py` - Callback handler

### 2. فایل‌های قدیمی غیرفعال شده (با پسوند .old)
- `youtube.py.old`
- `youtube_new_handler.py.old`
- `youtube_new_callback.py.old`
- `youtube_callback_query.py.old`
- `youtube_quality_selector.py.old`
- `youtube_advanced_downloader.py.old`
- `youtube_helpers.py.old`

### 3. تغییرات در فایل اصلی ربات

اگر در فایل `main.py` یا `bot.py` import هایی از فایل‌های قدیمی دارید، آنها را حذف کنید:

```python
# حذف کنید:
# import plugins.youtube
# import plugins.youtube_new_handler
# import plugins.youtube_new_callback
# import plugins.youtube_callback_query

# اضافه کنید:
import plugins.youtube_handler
import plugins.youtube_callback
```

### 4. تست سیستم جدید

1. ربات را راه‌اندازی کنید
2. یک لینک یوتیوب ارسال کنید
3. بررسی کنید که 4 کیفیت نمایش داده می‌شود (2 در هر سطر)
4. یک کیفیت را انتخاب کنید
5. بررسی کنید که مستقیماً دانلود شروع می‌شود (بدون مرحله "فایل یا لینک")

### 5. بازگشت به سیستم قدیمی (در صورت نیاز)

اگر مشکلی پیش آمد، می‌توانید به سیستم قدیمی برگردید:

```powershell
# حذف فایل‌های جدید
Remove-Item plugins\youtube_handler.py
Remove-Item plugins\youtube_downloader.py
Remove-Item plugins\youtube_uploader.py
Remove-Item plugins\youtube_callback.py

# بازگردانی فایل‌های قدیمی
Rename-Item plugins\youtube.py.old youtube.py
Rename-Item plugins\youtube_new_handler.py.old youtube_new_handler.py
# و غیره...
```

## مزایای سیستم جدید

✅ کد ساده‌تر و خواناتر
✅ فقط 4 فایل به جای 7+ فایل
✅ بهینه‌سازی آپلود با streaming
✅ نمایش پیشرفت بهتر
✅ مدیریت خطا بهتر
✅ Logging کامل‌تر
✅ حذف مرحله اضافی "فایل یا لینک"
✅ نمایش کیفیت‌ها در 2 ستون
