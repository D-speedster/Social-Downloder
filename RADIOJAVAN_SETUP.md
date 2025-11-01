# 🚀 راهنمای نصب و راه‌اندازی قابلیت رادیو جوان

## مراحل نصب

### 1️⃣ نصب کتابخانه
```bash
pip install radiojavanapi
```

یا نصب تمام وابستگی‌ها:
```bash
pip install -r requirements.txt
```

### 2️⃣ راه‌اندازی ربات
```bash
python bot.py
```

### 3️⃣ تست
لینک زیر را در ربات ارسال کنید:
```
https://play.radiojavan.com/song/sijal-baz-mirim-baham-(ft-sami-low)
```

## نتیجه مورد انتظار

### مرحله 1: پیام پردازش
```
🎵 در حال پردازش...

⏳ لطفاً صبر کنید، در حال دریافت اطلاعات آهنگ از رادیو جوان...
```

### مرحله 2: دانلود
```
🎵 Sijal - Baz Mirim Baham (Ft Sami Low)

⬇️ در حال دانلود...
⏳ لطفاً صبر کنید...
```

### مرحله 3: آپلود
```
🎵 Sijal - Baz Mirim Baham (Ft Sami Low)

⬆️ در حال آپلود...
⏳ لطفاً صبر کنید...
```

### مرحله 4: فایل نهایی
```
[فایل صوتی MP3]

🎧 Sijal - "Baz Mirim Baham (Ft Sami Low)"
📯 Plays: 13,679,804
📥 Downloads: 13,679,804
👍 Likes: 1,234

🎵 از رادیو جوان دانلود شد
```

## فایل‌های اضافه شده

✅ `plugins/radiojavan_handler.py` - Handler اصلی
✅ `bot.py` - اضافه شدن import
✅ `requirements.txt` - اضافه شدن radiojavanapi

## بررسی لاگ‌ها

```bash
tail -f logs/radiojavan_handler.log
```

باید ببینید:
```
RadioJavan request from user 123456: https://play.radiojavan.com/song/...
Fetching song info from: https://play.radiojavan.com/song/...
Song info fetched: Sijal - Baz Mirim Baham (Ft Sami Low)
Downloading: Sijal - Baz Mirim Baham (Ft Sami Low).mp3
Download completed: downloads/Sijal - Baz Mirim Baham (Ft Sami Low).mp3
Deleted local file: downloads/Sijal - Baz Mirim Baham (Ft Sami Low).mp3
Stats updated for user 123456
RadioJavan download completed for user 123456
```

## عیب‌یابی

### خطا: ModuleNotFoundError: No module named 'radiojavanapi'
**راه حل:**
```bash
pip install radiojavanapi
```

### خطا: Failed to fetch song info
**علل احتمالی:**
- لینک نامعتبر است
- آهنگ حذف شده یا در دسترس نیست
- مشکل در اتصال به اینترنت

**راه حل:**
- لینک را بررسی کنید
- اتصال اینترنت را چک کنید
- لاگ‌ها را بررسی کنید

### خطا: لینک دانلود یافت نشد
**علل احتمالی:**
- آهنگ محدودیت جغرافیایی دارد
- لینک دانلود منقضی شده

**راه حل:**
- آهنگ دیگری امتحان کنید
- با VPN تست کنید

## ویژگی‌های کلیدی

✅ **مستقل**: هیچ تداخلی با youtube یا universal downloader
✅ **سریع**: دانلود و آپلود async
✅ **زیبا**: کپشن با آمار کامل
✅ **امن**: فیلتر عضویت اسپانسری
✅ **پاکیزه**: حذف خودکار فایل‌های موقت

## لینک‌های پشتیبانی شده

✅ `https://play.radiojavan.com/song/...`
✅ `https://radiojavan.com/song/...`
✅ `https://www.radiojavan.com/song/...`
✅ `http://radiojavan.com/song/...`

## آماده است! 🎉

سیستم رادیو جوان کاملاً آماده و مستقل است. فقط ربات را راه‌اندازی کنید و لینک ارسال کنید!
