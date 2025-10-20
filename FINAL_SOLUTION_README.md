# 🎬 راه‌حل کامل احراز هویت کوکی YouTube
# Complete YouTube Cookie Authentication Solution

## 🚀 راه‌حل سریع (Quick Solution)

### مرحله 1: تست سریع
```bash
python3 quick_cookie_test.py
```

### مرحله 2: اگر تست ناموفق بود، استخراج کوکی‌ها
```bash
python3 auto_cookie_manager.py auto
```

### مرحله 3: دانلود ویدیو
```bash
python3 run_complete_solution.py download "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"
```

---

## 📋 فهرست فایل‌های راه‌حل

### 🔧 ابزارهای اصلی
- **`run_complete_solution.py`** - اسکریپت اصلی برای اجرای کامل راه‌حل
- **`emergency_youtube_downloader.py`** - دانلودر اضطراری با پشتیبانی کوکی
- **`auto_cookie_manager.py`** - مدیر خودکار کوکی‌ها
- **`youtube_cookie_manager.py`** - مدیر دستی کوکی‌ها

### 🧪 ابزارهای تست
- **`quick_cookie_test.py`** - تست سریع کوکی‌ها
- **`test_complete_solution.py`** - تست کامل سیستم

### 📚 مستندات
- **`COOKIE_AUTHENTICATION_GUIDE.md`** - راهنمای کامل احراز هویت
- **`FINAL_SOLUTION_README.md`** - این فایل

---

## 🛠️ نصب و راه‌اندازی

### پیش‌نیازها
```bash
pip install yt-dlp requests sqlite3
```

### تنظیم اولیه
```bash
python3 run_complete_solution.py setup
```

---

## 📖 دستورات اصلی

### 🔧 تنظیم و تست
```bash
# تنظیم اولیه کامل
python3 run_complete_solution.py setup

# تست سریع سیستم
python3 run_complete_solution.py test

# تست کامل تمام قابلیت‌ها
python3 run_complete_solution.py fulltest
```

### 🍪 مدیریت کوکی‌ها
```bash
# استخراج خودکار کوکی‌ها از تمام مرورگرها
python3 auto_cookie_manager.py auto

# استخراج دستی کوکی‌ها
python3 auto_cookie_manager.py extract

# تست اعتبار کوکی‌ها
python3 auto_cookie_manager.py test

# تست سریع کوکی‌ها
python3 quick_cookie_test.py
```

### 📥 دانلود ویدیو
```bash
# دانلود با کیفیت پیش‌فرض (720p)
python3 run_complete_solution.py download "https://www.youtube.com/watch?v=VIDEO_ID"

# دانلود با کیفیت مشخص
python3 run_complete_solution.py download "https://www.youtube.com/watch?v=VIDEO_ID" 1080p

# دانلود مستقیم با دانلودر اضطراری
python3 emergency_youtube_downloader.py download "URL" 720p
```

---

## 🔍 تشخیص و حل مشکلات

### مشکل 1: خطای DNS
```bash
# اجرای اسکریپت تعمیر DNS (در لینوکس)
sudo ./emergency_dns_fix.sh
source /tmp/emergency_youtube_env.sh
```

### مشکل 2: خطای احراز هویت
```bash
# تست کوکی‌ها
python3 quick_cookie_test.py

# استخراج مجدد کوکی‌ها
python3 auto_cookie_manager.py extract

# تست با مرورگر مشخص
yt-dlp --cookies-from-browser chrome "URL"
```

### مشکل 3: خطای شبکه
```bash
# تست اتصال
python3 emergency_youtube_downloader.py test

# تست کامل سیستم
python3 test_complete_solution.py
```

---

## 📊 نحوه عملکرد راه‌حل

### 1. تشخیص مرورگر
- جستجوی خودکار مرورگرهای نصب شده
- پشتیبانی از Chrome, Firefox, Edge, Chromium

### 2. استخراج کوکی‌ها
- خواندن از پایگاه داده SQLite مرورگر
- رمزگشایی کوکی‌های رمزشده
- ذخیره در فرمت‌های Netscape و JSON

### 3. احراز هویت
- استفاده از کوکی‌های استخراج شده
- چرخش User-Agent برای جلوگیری از تشخیص
- مدیریت خودکار انقضای کوکی‌ها

### 4. دانلود
- استفاده از yt-dlp با کوکی‌های معتبر
- پشتیبانی از کیفیت‌های مختلف
- مدیریت خطا و تلاش مجدد

---

## 🔐 نکات امنیتی

### ⚠️ هشدارهای مهم
- کوکی‌ها حاوی اطلاعات حساس هستند
- فایل‌های کوکی را در اشتراک نگذارید
- کوکی‌ها دارای تاریخ انقضا هستند

### 🛡️ بهترین روش‌ها
- کوکی‌ها را به صورت منظم به‌روزرسانی کنید
- از مرورگر اصلی خود برای استخراج استفاده کنید
- فایل‌های کوکی را در مکان امن نگهداری کنید

---

## 📈 بهینه‌سازی عملکرد

### تنظیمات پیشرفته
```bash
# استفاده از پروکسی
export HTTP_PROXY="http://proxy:port"
export HTTPS_PROXY="http://proxy:port"

# تنظیم timeout
export YT_DLP_TIMEOUT=60

# فعال‌سازی لاگ تفصیلی
export YT_DLP_VERBOSE=1
```

### بهینه‌سازی شبکه
- استفاده از DNS سریع (8.8.8.8, 1.1.1.1)
- تنظیم timeout مناسب
- استفاده از اتصال پایدار

---

## 🆘 پشتیبانی و کمک

### فایل‌های لاگ
- `solution_runner.log` - لاگ اسکریپت اصلی
- `complete_solution_test.log` - لاگ تست کامل
- `test_report.json` - گزارش تفصیلی تست‌ها

### دستورات تشخیصی
```bash
# بررسی وضعیت سیستم
python3 test_complete_solution.py

# تست اتصال شبکه
ping youtube.com

# بررسی DNS
nslookup youtube.com

# تست yt-dlp
yt-dlp --version
```

### گزارش مشکل
1. اجرای `python3 test_complete_solution.py`
2. بررسی فایل `test_report.json`
3. ارسال لاگ‌ها و گزارش خطا

---

## 🔄 به‌روزرسانی

### به‌روزرسانی yt-dlp
```bash
pip install --upgrade yt-dlp
```

### به‌روزرسانی کوکی‌ها
```bash
python3 auto_cookie_manager.py extract
```

### بررسی نسخه
```bash
yt-dlp --version
python3 --version
```

---

## 📝 مثال‌های کاربردی

### دانلود پلی‌لیست
```bash
python3 emergency_youtube_downloader.py download "https://www.youtube.com/playlist?list=PLAYLIST_ID"
```

### دانلود با زیرنویس
```bash
yt-dlp --cookies youtube_cookies.txt --write-subs "URL"
```

### دانلود فقط صدا
```bash
yt-dlp --cookies youtube_cookies.txt -x --audio-format mp3 "URL"
```

---

## ✅ چک‌لیست نهایی

- [ ] نصب وابستگی‌ها (`pip install yt-dlp requests`)
- [ ] اجرای تنظیم اولیه (`python3 run_complete_solution.py setup`)
- [ ] تست کوکی‌ها (`python3 quick_cookie_test.py`)
- [ ] تست دانلود (`python3 run_complete_solution.py download "URL"`)
- [ ] بررسی لاگ‌ها در صورت خطا

---

## 🎉 تبریک!

اگر تمام مراحل بالا را طی کردید، سیستم شما آماده دانلود از YouTube با احراز هویت کوکی است!

برای سوالات بیشتر، فایل `COOKIE_AUTHENTICATION_GUIDE.md` را مطالعه کنید.

---

**نسخه:** 1.0  
**تاریخ:** 2024  
**سازگاری:** Windows, Linux, macOS  
**پشتیبانی:** Python 3.7+