# دستورالعمل نهایی - اجرا در سرور لینوکس

## مشکل شما
خطای `Failed to resolve 's' ([Errno -3] Temporary failure in name resolution)` نشان‌دهنده مشکل DNS resolution در سرور لینوکس شماست.

## راه‌حل سریع (توصیه شده) ⚡

### مرحله 1: حل فوری مشکل DNS
```bash
# دانلود و اجرای اسکریپت حل سریع
sudo chmod +x quick_dns_fix.sh
sudo ./quick_dns_fix.sh
```

### مرحله 2: تنظیم محیط
```bash
# اعمال متغیرهای محیط
source /tmp/youtube_env_fix.sh
```

### مرحله 3: تست عملکرد
```bash
# تست سریع
python3 run_on_linux_server.py test

# یا تست کامل
python3 test_linux_server.py
```

### مرحله 4: اجرای دانلودر
```bash
# حالت تعاملی
python3 run_on_linux_server.py

# یا دانلود مستقیم
python3 run_on_linux_server.py download "https://www.youtube.com/watch?v=dL_r_PPlFtI"
```

## راه‌حل کامل (در صورت نیاز) 🔧

### 1. راه‌اندازی کامل سیستم
```bash
# اجرای اسکریپت راه‌اندازی کامل
sudo python3 setup_linux_server.py
```

### 2. تنظیم دستی DNS (اختیاری)
```bash
# بک‌آپ فایل فعلی
sudo cp /etc/resolv.conf /etc/resolv.conf.backup

# ویرایش DNS
sudo nano /etc/resolv.conf
```

محتوای فایل:
```
nameserver 8.8.8.8
nameserver 8.8.4.4
nameserver 1.1.1.1
nameserver 1.0.0.1
options timeout:5
options attempts:3
options rotate
options single-request-reopen
```

### 3. راه‌اندازی مجدد سرویس‌ها
```bash
sudo systemctl restart systemd-resolved
sudo systemctl restart networking
sudo systemd-resolve --flush-caches
```

## استفاده از دانلودر 🚀

### حالت تعاملی
```bash
python3 run_on_linux_server.py
```

### دانلود مستقیم
```bash
# دانلود با کیفیت پیش‌فرض (720p)
python3 run_on_linux_server.py download "URL_VIDEO"

# دانلود با کیفیت مشخص
python3 run_on_linux_server.py download "URL_VIDEO" "480p"
```

### دانلود دسته‌ای
```bash
# ایجاد فایل لیست URL ها
echo "https://www.youtube.com/watch?v=VIDEO1" > urls.txt
echo "https://www.youtube.com/watch?v=VIDEO2" >> urls.txt

# دانلود دسته‌ای
python3 run_on_linux_server.py batch urls.txt "720p"
```

## عیب‌یابی 🔍

### بررسی DNS
```bash
# تست DNS
nslookup youtube.com 8.8.8.8
dig @1.1.1.1 youtube.com

# تست اتصال
ping -c 4 youtube.com
curl -I https://www.youtube.com
```

### بررسی لاگ‌ها
```bash
# لاگ‌های DNS
sudo journalctl -u systemd-resolved -f

# لاگ‌های شبکه
sudo journalctl -u systemd-networkd -f
```

### مشکلات رایج و راه‌حل

#### 1. همچنان DNS Error
```bash
# تغییر DNS به Cloudflare
echo "nameserver 1.1.1.1" | sudo tee /etc/resolv.conf
echo "nameserver 1.0.0.1" | sudo tee -a /etc/resolv.conf
```

#### 2. مشکل SSL/TLS
```bash
# غیرفعال کردن تایید SSL
export PYTHONHTTPSVERIFY=0
export CURL_CA_BUNDLE=""
export REQUESTS_CA_BUNDLE=""
```

#### 3. Timeout خیلی کم
```bash
# افزایش timeout
export SOCKET_TIMEOUT=120
export CONNECT_TIMEOUT=60
export READ_TIMEOUT=180
```

#### 4. مشکل فایروال
```bash
# اجازه اتصالات خروجی
sudo ufw allow out 443
sudo ufw allow out 80
sudo ufw allow out 53
```

## بازگردانی در صورت مشکل 🔄

### بازگردانی DNS
```bash
# بازگردانی از بک‌آپ
sudo cp /etc/resolv.conf.backup /etc/resolv.conf
sudo systemctl restart systemd-resolved
```

### بازگردانی کامل
```bash
# اجرای اسکریپت بازیابی
sudo bash recovery_youtube_downloader.sh
```

## نکات مهم ⚠️

1. **همیشه بک‌آپ بگیرید** قبل از تغییر تنظیمات سیستم
2. **مرحله به مرحله تست کنید** پس از هر تغییر
3. **در محیط production احتیاط کنید** و ابتدا در محیط تست امتحان کنید
4. **لاگ‌ها را بررسی کنید** در صورت بروز مشکل

## پشتیبانی 📞

اگر همچنان مشکل دارید:

1. لاگ کامل خطا را ذخیره کنید
2. خروجی `python3 test_linux_server.py` را بررسی کنید
3. تنظیمات شبکه سرور را با مدیر سیستم بررسی کنید

## خلاصه دستورات سریع 📝

```bash
# حل سریع مشکل
sudo ./quick_dns_fix.sh
source /tmp/youtube_env_fix.sh

# تست
python3 run_on_linux_server.py test

# دانلود
python3 run_on_linux_server.py download "YOUR_URL"
```

**موفق باشید! 🎉**