# راهنمای استقرار در سرور

## 🚀 دستورات سریع

### 1. آپلود کد به سرور
```bash
# در کامپیوتر محلی:
git add .
git commit -m "Fix: YouTube bot detection bypass with fallback strategy"
git push origin main

# در سرور:
cd /path/to/Social-Downloder-main
git pull origin main
```

---

### 2. نصب وابستگی‌ها (در صورت نیاز)
```bash
pip install -r requirements.txt
```

---

### 3. بررسی تغییرات
```bash
# اجرای تست خودکار
python test_bot_detection_bypass.py
```

**نتیجه مورد انتظار:**
```
🎉 All tests passed! Bot detection bypass is ready.
```

---

### 4. راه‌اندازی مجدد ربات
```bash
# متوقف کردن ربات فعلی
pkill -f bot.py

# یا اگر از screen/tmux استفاده می‌کنید:
# screen -r bot_session
# Ctrl+C

# راه‌اندازی مجدد
python bot.py

# یا در background:
nohup python bot.py > bot.log 2>&1 &
```

---

## 🔍 بررسی وضعیت

### چک کردن لاگ‌ها
```bash
# لاگ اصلی ربات
tail -f logs/bot.log

# لاگ یوتیوب
tail -f logs/youtube_handler.log

# لاگ دانلود
tail -f logs/youtube_downloader.log
```

---

## 🧪 تست عملکرد

### ارسال لینک تست به ربات
```
https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

**رفتار مورد انتظار:**

#### با کوکی معتبر:
```
🎬 Rick Astley - Never Gonna Give You Up
👤 کانال: Rick Astley
⏱ مدت زمان: 03:33
👁 بازدید: 1.5B

📋 لطفاً کیفیت مورد نظر را انتخاب کنید:
[360p] [480p]
[720p] [1080p]
[🎵 فقط صدا]
```

#### بدون کوکی معتبر (fallback mode):
```
⚠️ Bot detection with default settings, trying fallback...
✅ Success with fallback settings (limited qualities)

🎬 Rick Astley - Never Gonna Give You Up
👤 کانال: Rick Astley
⏱ مدت زمان: 03:33
👁 بازدید: 1.5B

📋 لطفاً کیفیت مورد نظر را انتخاب کنید:
[360p]  ← فقط این کیفیت
[🎵 فقط صدا]
```

---

## 📋 Checklist قبل از استقرار

- [ ] کد را از Git Pull کرده‌اید
- [ ] وابستگی‌ها نصب شده‌اند
- [ ] تست‌های خودکار موفق شده‌اند
- [ ] فایل `.env` موجود است
- [ ] دیتابیس `bot_database.db` موجود است
- [ ] FFmpeg نصب شده است (`ffmpeg -version`)
- [ ] دسترسی به پورت‌های مورد نیاز وجود دارد

---

## 🔧 عیب‌یابی

### مشکل 1: همچنان خطای "Sign in to confirm" می‌آید

**راه‌حل:**
```bash
# بررسی لاگ برای مشاهده fallback
tail -f logs/youtube_downloader.log

# باید این خطوط را ببینید:
# "🤖 Bot detection error detected!"
# "Will use bot detection bypass (player_client) in next attempt"
# "✅ Success with fallback settings"
```

اگر این خطوط را نمی‌بینید:
1. مطمئن شوید که کد جدید pull شده است
2. ربات را restart کنید
3. تست‌ها را مجدداً اجرا کنید

---

### مشکل 2: فقط کیفیت 360p نمایش داده می‌شود

**دلیل:**  
کوکی معتبر در دیتابیس موجود نیست یا منقضی شده است.

**راه‌حل:**
1. کوکی جدید از YouTube دریافت کنید:
   - از افزونه [Get cookies.txt](https://chrome.google.com/webstore/detail/get-cookiestxt/bgaddhkoddajcdgocldbbfleckgcbcid)
   - Export کوکی‌ها در فرمت Netscape

2. کوکی را به دیتابیس اضافه کنید:
   ```python
   from plugins.db_wrapper import DB
   db = DB()
   
   with open('youtube_cookie.txt', 'r') as f:
       cookie_text = f.read()
   
   db.add_cookie(name="YouTube Cookie 1", cookie_text=cookie_text)
   ```

3. ربات را restart کنید

---

### مشکل 3: دانلود بسیار کند است

**راه‌حل:**
```python
# در youtube_downloader.py، تنظیمات زیر را بررسی کنید:
'concurrent_fragment_downloads': 4,  # افزایش به 8
'http_chunk_size': 5242880,          # افزایش به 10485760 (10MB)
```

---

### مشکل 4: SQLite database is locked

**راه‌حل:**  
این مشکل با افزایش timeout حل شده است. اگر همچنان وجود دارد:

```bash
# بررسی تعداد فرآیندهای همزمان
ps aux | grep bot.py | wc -l

# باید فقط 1 فرآیند باشد
# اگر بیشتر است، موارد اضافی را kill کنید
pkill -f bot.py
python bot.py
```

---

## 📊 مانیتورینگ

### بررسی وضعیت سلامت سیستم

```bash
# چک کردن استفاده از CPU/RAM
top -p $(pgrep -f bot.py)

# چک کردن فضای دیسک
df -h

# چک کردن تعداد کوکی‌های فعال
sqlite3 data/database/bot_database.db "SELECT COUNT(*) FROM cookies;"

# چک کردن فایل‌های temp
ls -lh data/cookies_tmp/ | wc -l
```

---

## 🔄 به‌روزرسانی‌های آینده

برای دریافت آخرین به‌روزرسانی‌ها:

```bash
cd /path/to/Social-Downloder-main
git pull origin main
pip install -r requirements.txt --upgrade
python test_bot_detection_bypass.py
pkill -f bot.py
python bot.py
```

---

## 🆘 در صورت مشکل

اگر با مشکلی مواجه شدید:

1. **لاگ‌ها را بررسی کنید:**
   ```bash
   tail -100 logs/bot.log
   tail -100 logs/youtube_downloader.log
   ```

2. **تست‌ها را اجرا کنید:**
   ```bash
   python test_bot_detection_bypass.py
   ```

3. **دیتابیس را بررسی کنید:**
   ```bash
   sqlite3 data/database/bot_database.db
   SELECT * FROM cookies LIMIT 5;
   .quit
   ```

4. **ربات را restart کنید:**
   ```bash
   pkill -f bot.py
   python bot.py
   ```

---

## ✅ علائم موفقیت

زمانی که همه‌چیز درست کار می‌کند، باید موارد زیر را ببینید:

### در لاگ‌ها:
```
✅ Cookie loaded from database: YouTube Cookie 1
Trying default settings (all qualities)...
✅ Success with default settings!
✅ Download completed: 15.3 MB in 8.2s (1.87 MB/s)
```

### در پاسخ به کاربر:
```
🎬 عنوان ویدیو
📋 لطفاً کیفیت مورد نظر را انتخاب کنید:
[360p] [480p] [720p] [1080p]
[🎵 فقط صدا]

✅ دانلود موفق!
```

---

**🎉 ربات شما آماده استفاده است!**

برای سوالات بیشتر، به مستندات زیر مراجعه کنید:
- `YOUTUBE_BOT_DETECTION_FIX.md` - جزئیات فنی راه‌حل
- `COOKIE_SYSTEM.md` - سیستم مدیریت کوکی
- `PROJECT_STRUCTURE.md` - ساختار کلی پروژه
