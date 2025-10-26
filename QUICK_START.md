# راهنمای سریع - سیستم جدید یوتیوب

## 🚀 شروع سریع (3 مرحله)

### 1️⃣ بررسی فایل‌های جدید
```bash
plugins/
├── youtube_handler.py      ✅ ایجاد شد
├── youtube_downloader.py   ✅ ایجاد شد
├── youtube_uploader.py     ✅ ایجاد شد
└── youtube_callback.py     ✅ ایجاد شد
```

### 2️⃣ Import در فایل اصلی
در فایل `main.py` یا `bot.py`:
```python
import plugins.youtube_handler
import plugins.youtube_callback
```

### 3️⃣ اجرای ربات
```bash
python main.py
```

## ✅ تست سریع

1. ربات را اجرا کنید
2. یک لینک یوتیوب ارسال کنید (مثلاً: https://youtu.be/dQw4w9WgXcQ)
3. باید 4 کیفیت در 2 ستون ببینید:
   ```
   [360p] [480p]
   [720p] [1080p]
   [🎵 فقط صدا]
   ```
4. یک کیفیت را انتخاب کنید
5. دانلود خودکار شروع می‌شود (بدون مرحله "فایل یا لینک")

## ❓ مشکل دارید?

### خطا: ModuleNotFoundError
```bash
pip install yt-dlp pyrogram aiohttp
```

### فایل‌های قدیمی مزاحم هستند
```powershell
# حذف کامل فایل‌های قدیمی
Remove-Item plugins\*.old
```

### ربات پاسخ نمی‌دهد
1. بررسی کنید که imports درست باشند
2. لاگ‌ها را چک کنید: `logs/youtube_handler.log`
3. تست را اجرا کنید: `python test_youtube_new.py`

## 📚 مستندات بیشتر

- **ساختار کامل**: YOUTUBE_NEW_SYSTEM.md
- **راهنمای مهاجرت**: MIGRATION_GUIDE.md
- **مقایسه قدیم/جدید**: COMPARISON.md
- **تغییرات**: CHANGELOG.md

## 💡 نکات مهم

✅ فقط 4 کیفیت نمایش داده می‌شود
✅ دکمه‌ها در 2 ستون هستند
✅ مرحله "فایل یا لینک" حذف شده
✅ آپلود با streaming بهینه شده

## 🎉 همین!

سیستم جدید آماده استفاده است. لذت ببرید! 🚀
