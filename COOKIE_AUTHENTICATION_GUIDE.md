# 🍪 راهنمای احراز هویت با کوکی برای YouTube
# Cookie Authentication Guide for YouTube

## 📋 خلاصه مشکل و راه‌حل
مشکل DNS حل شده است، اما YouTube اکنون احراز هویت با کوکی می‌خواهد تا از ربات بودن مطمئن شود.

## 🚀 راه‌حل سریع (Quick Solution)

### مرحله 1: استخراج خودکار کوکی‌ها
```bash
# اجرای مدیر خودکار کوکی
python3 auto_cookie_manager.py auto

# یا فقط استخراج کوکی‌ها
python3 auto_cookie_manager.py extract
```

### مرحله 2: تست کوکی‌ها
```bash
# تست کوکی‌ها
python3 auto_cookie_manager.py test

# یا تست با دانلودر اضطراری
python3 emergency_youtube_downloader.py test
```

### مرحله 3: دانلود با احراز هویت
```bash
# دانلود ویدیو
python3 emergency_youtube_downloader.py download "https://www.youtube.com/watch?v=VIDEO_ID"
```

## 🔧 راه‌حل‌های دستی

### روش 1: استخراج کوکی از مرورگر Chrome
```bash
# استفاده از yt-dlp برای استخراج کوکی از Chrome
yt-dlp --cookies-from-browser chrome --simulate "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# ذخیره کوکی‌ها در فایل
yt-dlp --cookies-from-browser chrome --cookies youtube_cookies.txt --simulate "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### روش 2: استخراج کوکی از Firefox
```bash
yt-dlp --cookies-from-browser firefox --cookies youtube_cookies.txt --simulate "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### روش 3: استخراج کوکی از Edge
```bash
yt-dlp --cookies-from-browser edge --cookies youtube_cookies.txt --simulate "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

## 📁 ساختار فایل‌های کوکی

### فایل‌های تولید شده:
- `youtube_cookies.txt` - فرمت Netscape (برای yt-dlp)
- `youtube_cookies.json` - فرمت JSON (برای استفاده‌های دیگر)
- `cookies/` - دایرکتوری کوکی‌ها

## 🛠️ ابزارهای موجود

### 1. مدیر خودکار کوکی (`auto_cookie_manager.py`)
```bash
# مدیریت خودکار کامل
python3 auto_cookie_manager.py auto

# فقط استخراج
python3 auto_cookie_manager.py extract

# فقط تست
python3 auto_cookie_manager.py test
```

### 2. مدیر کوکی دستی (`youtube_cookie_manager.py`)
```bash
# رابط تعاملی
python3 youtube_cookie_manager.py

# استخراج از مرورگر خاص
python3 youtube_cookie_manager.py --browser chrome

# تست کوکی‌ها
python3 youtube_cookie_manager.py --test
```

### 3. دانلودر اضطراری (`emergency_youtube_downloader.py`)
```bash
# تست اتصال
python3 emergency_youtube_downloader.py test

# دانلود ویدیو
python3 emergency_youtube_downloader.py download "URL"

# دانلود با کیفیت خاص
python3 emergency_youtube_downloader.py download "URL" --quality 1080p
```

## 🔍 عیب‌یابی

### مشکل: "No cookies found"
**راه‌حل:**
1. مطمئن شوید مرورگر بسته است
2. حداقل یک بار YouTube را در مرورگر باز کرده باشید
3. وارد حساب Google خود شده باشید

### مشکل: "Sign in to confirm you're not a bot"
**راه‌حل:**
1. کوکی‌ها را دوباره استخراج کنید
2. از مرورگر دیگری امتحان کنید
3. User-Agent را تغییر دهید

### مشکل: "Cookie file not found"
**راه‌حل:**
```bash
# بررسی وجود فایل‌های کوکی
ls -la youtube_cookies.*
ls -la cookies/

# اجرای مجدد استخراج
python3 auto_cookie_manager.py extract
```

## 📊 بررسی وضعیت

### بررسی فایل‌های کوکی:
```bash
# بررسی فایل Netscape
head -10 youtube_cookies.txt

# بررسی فایل JSON
python3 -m json.tool youtube_cookies.json | head -20

# شمارش کوکی‌ها
grep -c "youtube.com" youtube_cookies.txt
```

### بررسی مرورگرها:
```bash
# Chrome
ls -la ~/.config/google-chrome/Default/Cookies

# Firefox
ls -la ~/.mozilla/firefox/*/cookies.sqlite

# Edge
ls -la ~/.config/microsoft-edge/Default/Cookies
```

## 🎯 نکات مهم

### 1. امنیت کوکی‌ها
- کوکی‌ها حاوی اطلاعات حساس هستند
- آن‌ها را در مخزن عمومی قرار ندهید
- به صورت منظم آن‌ها را به‌روزرسانی کنید

### 2. انقضای کوکی‌ها
- کوکی‌ها معمولاً پس از چند هفته منقضی می‌شوند
- در صورت خطای احراز هویت، کوکی‌ها را دوباره استخراج کنید

### 3. مرورگرهای پشتیبانی شده
- ✅ Chrome/Chromium
- ✅ Firefox
- ✅ Microsoft Edge
- ✅ Safari (macOS)

## 🔄 به‌روزرسانی خودکار

### اسکریپت به‌روزرسانی روزانه:
```bash
#!/bin/bash
# daily_cookie_update.sh

echo "🔄 به‌روزرسانی کوکی‌های YouTube..."
python3 auto_cookie_manager.py auto

if [ $? -eq 0 ]; then
    echo "✅ کوکی‌ها با موفقیت به‌روزرسانی شدند"
else
    echo "❌ خطا در به‌روزرسانی کوکی‌ها"
fi
```

### اضافه کردن به crontab:
```bash
# اجرای روزانه در ساعت 6 صبح
0 6 * * * /path/to/daily_cookie_update.sh
```

## 📞 پشتیبانی

### لاگ‌های مفید:
- `auto_cookie_manager.log` - لاگ مدیر خودکار
- `youtube_cookie_manager.log` - لاگ مدیر دستی
- `emergency_youtube_downloader.log` - لاگ دانلودر

### دستورات تشخیصی:
```bash
# بررسی وضعیت DNS
nslookup youtube.com

# بررسی اتصال
curl -I https://www.youtube.com

# تست yt-dlp
yt-dlp --version
yt-dlp --list-formats "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

## 🎉 تست نهایی

### تست کامل سیستم:
```bash
# 1. بررسی DNS
echo "🔍 تست DNS..."
nslookup youtube.com

# 2. استخراج کوکی‌ها
echo "🍪 استخراج کوکی‌ها..."
python3 auto_cookie_manager.py auto

# 3. تست دانلودر
echo "📥 تست دانلودر..."
python3 emergency_youtube_downloader.py test

# 4. دانلود تست
echo "🎬 دانلود تست..."
python3 emergency_youtube_downloader.py download "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

---

## 🚨 در صورت مشکل

اگر همچنان با مشکل مواجه هستید:

1. **مرورگر را ببندید** و دوباره کوکی‌ها را استخراج کنید
2. **VPN** استفاده کنید اگر IP شما مسدود شده
3. **User-Agent** را تغییر دهید
4. از **مرورگر دیگری** امتحان کنید
5. **حساب Google** جدید ایجاد کنید

**موفق باشید! 🎉**