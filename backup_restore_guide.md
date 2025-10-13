# راهنمای Backup و Restore داده‌های کاربران

## مقدمه
این راهنما برای محافظت از داده‌های کاربران و جلوگیری از از دست رفتن اطلاعات هنگام به‌روزرسانی کد طراحی شده است.

## ⚠️ مشکل اصلی: از دست رفتن داده‌های کاربران
هنگامی که تغییرات کد را از GitHub pull می‌کنید، داده‌های کاربران جدید سرور با داده‌های قدیمی محلی جایگزین می‌شود. این راهنما راه‌حل ساده و عملی برای این مشکل ارائه می‌دهد.

## 🎯 راه‌حل پیشنهادی: کپی مستقیم دیتابیس

### روش ساده و عملی (پیشنهادی)
کپی مستقیم فایل دیتابیس قبل و بعد از به‌روزرسانی سورس.

## فایل اصلی که باید محافظت شود

### دیتابیس اصلی
- `plugins/bot_database.db` - دیتابیس اصلی SQLite حاوی تمام داده‌های کاربران

**محتویات دیتابیس:**
- جدول `users` - اطلاعات کاربران (7 کاربر)
- جدول `insta_acc` - اکانت‌های اینستاگرام (1 اکانت)
- جدول `jobs` - کارهای در حال انجام (0 کار)
- جدول `user_settings` - تنظیمات کاربران (7 تنظیم)
- جدول `waiting_messages` - پیام‌های در انتظار (0 پیام)
- جدول `cookies` - کوکی‌های ذخیره شده (1 کوکی)

## 🚀 روش کپی مستقیم (ساده و عملی)

### مرحله 1: کپی فایل دیتابیس از سرور
```bash
# کپی فایل دیتابیس از سرور به کامپیوتر محلی
scp user@server:/path/to/project/plugins/bot_database.db ./bot_database_backup.db
```

### مرحله 2: به‌روزرسانی سورس
```bash
git pull origin main
```

### مرحله 3: جایگزینی فایل دیتابیس
```bash
# جایگزینی فایل دیتابیس جدید با فایل backup شده
cp ./bot_database_backup.db plugins/bot_database.db
```

### مزایای این روش:
- ✅ بسیار ساده و سریع
- ✅ بدون نیاز به اسکریپت‌های پیچیده
- ✅ کمترین احتمال خطا
- ✅ قابل اجرا در تمام سیستم‌عامل‌ها
- ✅ حفظ کامل تمام داده‌های کاربران

## 📥 مراحل Deploy ایمن (روش ساده):

### 1. متوقف کردن ربات
```bash
# متوقف کردن process ربات
pkill -f "python.*bot"
# یا اگر از screen استفاده می‌کنید
screen -S bot -X quit
```

### 2. کپی فایل دیتابیس
```bash
# کپی فایل دیتابیس از سرور
cp plugins/bot_database.db ./bot_database_backup.db
```

### 3. Pull تغییرات جدید
```bash
git pull origin main
```

### 4. جایگزینی فایل دیتابیس
```bash
# جایگزینی فایل دیتابیس
cp ./bot_database_backup.db plugins/bot_database.db
```

### 5. نصب dependencies جدید (در صورت نیاز)
```bash
pip install -r requirements.txt
```

### 6. راه‌اندازی مجدد ربات
```bash
# راه‌اندازی ربات
python bot.py
# یا با screen
screen -S bot -dm python bot.py
```

## 💡 نکات عملی:

### برای Windows:
```cmd
# کپی فایل دیتابیس
copy plugins\bot_database.db bot_database_backup.db

# جایگزینی بعد از git pull
copy bot_database_backup.db plugins\bot_database.db
```

### برای Linux/Mac:
```bash
# کپی فایل دیتابیس
cp plugins/bot_database.db bot_database_backup.db

# جایگزینی بعد از git pull
cp bot_database_backup.db plugins/bot_database.db
```

### استفاده از SCP برای کپی از سرور:
```bash
# دانلود فایل از سرور
scp username@server_ip:/path/to/project/plugins/bot_database.db ./bot_database_backup.db

# آپلود فایل به سرور (بعد از git pull)
scp ./bot_database_backup.db username@server_ip:/path/to/project/plugins/bot_database.db
```

## ⚠️ نکات مهم:

1. **همیشه قبل از git pull، فایل دیتابیس را کپی کنید**
2. **فایل .gitignore به‌روزرسانی شده تا از commit شدن داده‌های کاربران جلوگیری کند**
3. **فایل backup را در مکان امنی نگهداری کنید**
4. **قبل از جایگزینی، از سلامت فایل backup اطمینان حاصل کنید**

## 🔍 بررسی سلامت دیتابیس:

```bash
# بررسی تعداد کاربران
sqlite3 plugins/bot_database.db "SELECT COUNT(*) FROM users;"

# بررسی آخرین کاربر ثبت شده
sqlite3 plugins/bot_database.db "SELECT * FROM users ORDER BY id DESC LIMIT 5;"

# بررسی تمام جداول
sqlite3 plugins/bot_database.db ".tables"
```

## 📞 در صورت مشکل:

اگر داده‌های کاربران از دست رفت:
1. فوراً ربات را متوقف کنید
2. فایل backup شده را جایگزین کنید
3. سلامت دیتابیس را بررسی کنید
4. ربات را مجدداً راه‌اندازی کنید

## ✅ خلاصه روش ساده:

1. **کپی:** `cp plugins/bot_database.db backup.db`
2. **آپدیت:** `git pull origin main`
3. **جایگزینی:** `cp backup.db plugins/bot_database.db`
4. **تست:** بررسی سلامت دیتابیس
5. **راه‌اندازی:** اجرای مجدد ربات