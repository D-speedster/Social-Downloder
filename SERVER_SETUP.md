# 🚀 راهنمای نصب ربات در سرور

## ❌ مشکل فعلی:
```
Bot failed: No module named 'PIL'
```

## ✅ راه حل:

### 1. **نصب وابستگی‌ها:**
```bash
# نصب تمام پکیج‌های مورد نیاز
pip install -r requirements.txt

# یا نصب دستی Pillow
pip install Pillow>=9.0.0
```

### 2. **بررسی نصب:**
```bash
python -c "from PIL import Image; print('✅ PIL/Pillow نصب شد')"
```

### 3. **نصب سایر وابستگی‌های مهم:**
```bash
# برای Ubuntu/Debian
sudo apt update
sudo apt install python3-pip python3-dev
sudo apt install ffmpeg  # برای پردازش ویدئو

# برای CentOS/RHEL
sudo yum install python3-pip python3-devel
sudo yum install ffmpeg
```

### 4. **راه‌اندازی ربات:**
```bash
python main.py
```

## 📋 **لیست کامل وابستگی‌ها:**
- `mysql-connector-python` - اتصال به دیتابیس
- `Pyrogram==2.0.106` - کتابخانه تلگرام
- `instaloader` - دانلود از اینستاگرام
- `python-dateutil` - مدیریت تاریخ
- `yt-dlp` - دانلود از یوتیوب
- `psutil` - مدیریت سیستم
- `python-dotenv` - مدیریت متغیرهای محیطی
- `requests>=2.28.2` - درخواست‌های HTTP
- `Pillow>=9.0.0` - پردازش تصاویر ⭐ **جدید اضافه شد**

## 🔧 **عیب‌یابی:**

### اگر Pillow نصب نمی‌شود:
```bash
# Ubuntu/Debian
sudo apt install libjpeg-dev zlib1g-dev

# CentOS/RHEL  
sudo yum install libjpeg-devel zlib-devel

# سپس مجدداً نصب کنید
pip install Pillow
```

### بررسی نسخه Python:
```bash
python --version  # باید 3.7+ باشد
```

## ✨ **نکات مهم:**
1. حتماً `requirements.txt` به‌روزرسانی شده را استفاده کنید
2. اگر از virtual environment استفاده می‌کنید، آن را فعال کنید
3. در صورت مشکل، لاگ‌های کامل را بررسی کنید

---
**📅 آخرین به‌روزرسانی:** اضافه شدن Pillow به requirements.txt