# YouTube Downloader Bot

ربات دانلود از یوتیوب و شبکه‌های اجتماعی با قابلیت‌های پیشرفته

## ویژگی‌ها

### یوتیوب
- ✅ دانلود با 4 کیفیت: 360p, 480p, 720p, 1080p
- ✅ دانلود فقط صدا (بهترین کیفیت)
- ✅ نمایش کیفیت‌ها در 2 ستون
- ✅ دانلود مستقیم بدون مرحله اضافی
- ✅ آپلود بهینه با streaming
- ✅ پشتیبانی از کوکی برای دسترسی بهتر
- ✅ نمایش thumbnail روی ویدیوها

### شبکه‌های اجتماعی
- ✅ Instagram
- ✅ TikTok
- ✅ Twitter/X
- ✅ Facebook
- ✅ و بیش از 15 پلتفرم دیگر

## نصب و راه‌اندازی

### 1. نصب وابستگی‌ها
```bash
pip install -r requirements.txt
```

### 2. تنظیم فایل محیطی
```bash
cp .env.example .env
# ویرایش .env و اضافه کردن توکن ربات و API keys
```

### 3. تنظیم کوکی یوتیوب (اختیاری)
فایل `cookie_youtube.txt` را در مسیر اصلی پروژه قرار دهید.

### 4. اجرای ربات
```bash
python bot.py
```

## ساختار پروژه

```
├── bot.py                 # فایل اصلی ربات
├── main.py               # launcher
├── config.py             # تنظیمات
├── plugins/              # ماژول‌های ربات
│   ├── youtube_handler.py    # handler یوتیوب
│   ├── youtube_callback.py   # callback handler
│   ├── youtube_downloader.py # دانلودر
│   ├── youtube_uploader.py   # آپلودر
│   └── universal_downloader.py # سایر پلتفرم‌ها
├── docs/                 # مستندات (local only)
├── logs/                 # فایل‌های لاگ
└── cookie_youtube.txt    # کوکی یوتیوب
```

## تنظیمات

### متغیرهای محیطی (.env)
```
BOT_TOKEN=your_bot_token
API_ID=your_api_id
API_HASH=your_api_hash
RAPIDAPI_KEY=your_rapidapi_key
```

### کوکی یوتیوب
برای دسترسی بهتر به ویدیوهای یوتیوب، فایل کوکی را از مرورگر استخراج کنید.

## استفاده

1. ربات را استارت کنید: `/start`
2. لینک یوتیوب یا شبکه اجتماعی ارسال کنید
3. کیفیت مورد نظر را انتخاب کنید
4. فایل به صورت خودکار دانلود و ارسال می‌شود

## پشتیبانی

برای گزارش مشکل یا درخواست ویژگی جدید، issue ایجاد کنید.

## مجوز

این پروژه تحت مجوز MIT منتشر شده است.