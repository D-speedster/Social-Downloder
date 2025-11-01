# 🎵 قابلیت دانلود از رادیو جوان

## تاریخ: 2025-11-01
## وضعیت: ✅ پیاده‌سازی شد

---

## خلاصه
یک سیستم کامل و مستقل برای دانلود آهنگ از رادیو جوان به ربات اضافه شد.

## ویژگی‌ها

### ✅ مستقل از سایر بخش‌ها
- هیچ ارتباطی با `universal_downloader` ندارد
- هیچ ارتباطی با `youtube_handler` ندارد
- سیستم کاملاً جداگانه با handler مخصوص خودش

### ✅ قابلیت‌ها
- دانلود آهنگ با کیفیت بالا (HQ)
- نمایش اطلاعات کامل آهنگ
- آپلود به تلگرام با متادیتا (عنوان، هنرمند، مدت زمان)
- کپشن زیبا با آمار آهنگ

### ✅ پشتیبانی از لینک‌ها
```
https://play.radiojavan.com/song/sijal-baz-mirim-baham-(ft-sami-low)
https://radiojavan.com/song/...
https://www.radiojavan.com/song/...
```

## فایل‌های ایجاد شده

### 1. `plugins/radiojavan_handler.py`
Handler اصلی که:
- لینک‌های رادیو جوان را تشخیص می‌دهد
- اطلاعات آهنگ را از API دریافت می‌کند
- فایل را دانلود و آپلود می‌کند
- آمار کاربر را بروزرسانی می‌کند

### 2. تغییرات در `bot.py`
```python
import plugins.radiojavan_handler  # 🎵 RadioJavan downloader
```

### 3. تغییرات در `requirements.txt`
```
radiojavanapi  # 🎵 RadioJavan downloader
```

## نحوه استفاده

### برای کاربران:
1. لینک آهنگ از رادیو جوان را کپی کنید
2. لینک را در ربات ارسال کنید
3. ربات اطلاعات آهنگ را نمایش می‌دهد
4. فایل صوتی با کیفیت بالا ارسال می‌شود

### مثال:
```
کاربر: https://play.radiojavan.com/song/sijal-baz-mirim-baham-(ft-sami-low)

ربات: 🎵 در حال پردازش...
      ⏳ لطفاً صبر کنید...

ربات: 🎵 Sijal - Baz Mirim Baham (Ft Sami Low)
      ⬇️ در حال دانلود...

ربات: 🎵 Sijal - Baz Mirim Baham (Ft Sami Low)
      ⬆️ در حال آپلود...

ربات: [فایل صوتی]
      🎧 Sijal - "Baz Mirim Baham (Ft Sami Low)"
      📯 Plays: 13,679,804
      📥 Downloads: 13,679,804
      👍 Likes: 1,234
      
      🎵 از رادیو جوان دانلود شد
```

## جزئیات فنی

### Pattern Recognition
```python
RADIOJAVAN_REGEX = re.compile(
    r'^(?:https?://)?(?:www\.)?(?:play\.)?radiojavan\.com/(?:song|podcast|video)/[\w\-]+/?$',
    re.IGNORECASE
)
```

### API Integration
از کتابخانه `radiojavanapi` استفاده می‌شود:
```python
from radiojavanapi import Client as RJClient

client = RJClient()
song = client.get_song_by_url(url)
```

### اطلاعات استخراج شده
- نام آهنگ
- هنرمند
- آلبوم
- تاریخ انتشار
- مدت زمان
- تعداد لایک
- تعداد دانلود
- لینک دانلود (HQ, Normal, LQ)
- تصویر کاور

### Download Flow
1. دریافت اطلاعات از API
2. انتخاب لینک HQ (یا Normal به عنوان fallback)
3. دانلود فایل به صورت async
4. آپلود به تلگرام با متادیتا
5. حذف فایل محلی
6. بروزرسانی آمار کاربر

## امنیت و بهینه‌سازی

### ✅ فیلتر عضویت اسپانسری
```python
@Client.on_message(filters.private & filters.text & join, group=5)
```
کاربران باید در کانال اسپانسر عضو باشند.

### ✅ مدیریت خطا
- تمام خطاها لاگ می‌شوند
- پیام‌های خطای کاربرپسند
- Graceful degradation

### ✅ پاکسازی خودکار
فایل‌های دانلود شده بعد از آپلود حذف می‌شوند.

### ✅ Async Operations
تمام عملیات I/O به صورت async انجام می‌شوند:
- دریافت اطلاعات از API
- دانلود فایل
- ذخیره فایل

## نصب و راه‌اندازی

### 1. نصب کتابخانه
```bash
pip install radiojavanapi
```

یا:
```bash
pip install -r requirements.txt
```

### 2. راه‌اندازی ربات
```bash
python bot.py
```

### 3. تست
لینک زیر را در ربات ارسال کنید:
```
https://play.radiojavan.com/song/sijal-baz-mirim-baham-(ft-sami-low)
```

## لاگ‌ها

لاگ‌های مربوط به رادیو جوان در فایل زیر ذخیره می‌شوند:
```
logs/radiojavan_handler.log
```

### مثال لاگ:
```
2025-11-01 14:30:15 - radiojavan_handler - INFO - RadioJavan request from user 123456: https://play.radiojavan.com/song/...
2025-11-01 14:30:16 - radiojavan_handler - INFO - Fetching song info from: https://play.radiojavan.com/song/...
2025-11-01 14:30:17 - radiojavan_handler - INFO - Song info fetched: Sijal - Baz Mirim Baham (Ft Sami Low)
2025-11-01 14:30:18 - radiojavan_handler - INFO - Downloading: Sijal - Baz Mirim Baham (Ft Sami Low).mp3
2025-11-01 14:30:25 - radiojavan_handler - INFO - Download completed: downloads/Sijal - Baz Mirim Baham (Ft Sami Low).mp3
2025-11-01 14:30:35 - radiojavan_handler - INFO - Deleted local file: downloads/Sijal - Baz Mirim Baham (Ft Sami Low).mp3
2025-11-01 14:30:35 - radiojavan_handler - INFO - Stats updated for user 123456
2025-11-01 14:30:35 - radiojavan_handler - INFO - RadioJavan download completed for user 123456
```

## محدودیت‌ها

### ⚠️ نکات مهم:
1. فقط آهنگ‌های عمومی قابل دانلود هستند
2. برخی آهنگ‌ها ممکن است محدودیت جغرافیایی داشته باشند
3. کیفیت HQ ترجیح داده می‌شود (fallback به Normal)

## آینده

### قابلیت‌های پیشنهادی:
- [ ] پشتیبانی از پادکست‌ها
- [ ] پشتیبانی از ویدیوها
- [ ] انتخاب کیفیت توسط کاربر
- [ ] نمایش متن آهنگ (lyrics)
- [ ] دانلود آلبوم کامل

## خلاصه

✅ سیستم کامل و مستقل برای دانلود از رادیو جوان
✅ هیچ تداخلی با سایر بخش‌ها
✅ کپشن زیبا با آمار کامل
✅ مدیریت خطای قوی
✅ لاگ‌گذاری دقیق
✅ بهینه‌سازی شده و async

## تست نهایی

برای تست کامل:
1. ربات را راه‌اندازی کنید
2. لینک رادیو جوان ارسال کنید
3. بررسی کنید که فایل با کپشن صحیح ارسال شود
4. لاگ‌ها را بررسی کنید
