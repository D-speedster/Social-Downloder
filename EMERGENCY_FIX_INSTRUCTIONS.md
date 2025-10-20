# 🚨 راه‌حل اضطراری - حل فوری مشکل DNS

## مشکل شما
خطای `Failed to resolve 's'` نشان‌دهنده مشکل جدی DNS resolution در سرور لینوکس شماست.

## راه‌حل فوری (انجام دهید همین الان!) ⚡

### مرحله 1: اجرای اسکریپت اضطراری
```bash
# دانلود مجوز اجرا
sudo chmod +x emergency_dns_fix.sh

# اجرای اسکریپت اضطراری
sudo ./emergency_dns_fix.sh
```

### مرحله 2: بارگذاری متغیرهای محیط
```bash
# اعمال تنظیمات اضطراری
source /tmp/emergency_youtube_env.sh
```

### مرحله 3: تست سریع
```bash
# تست کامل سیستم
python3 emergency_youtube_test.py

# یا تست سریع
python3 emergency_youtube_downloader.py test
```

### مرحله 4: دانلود با دانلودر اضطراری
```bash
# حالت تعاملی
python3 emergency_youtube_downloader.py

# یا دانلود مستقیم
python3 emergency_youtube_downloader.py download "https://www.youtube.com/watch?v=dL_r_PPlFtI"
```

## اگر همچنان کار نکرد 🔧

### راه‌حل شماره 2: تنظیم دستی DNS
```bash
# توقف سرویس‌های DNS
sudo systemctl stop systemd-resolved
sudo systemctl stop dnsmasq

# تنظیم DNS دستی
sudo chattr -i /etc/resolv.conf
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
echo "nameserver 1.1.1.1" | sudo tee -a /etc/resolv.conf
echo "options timeout:2 attempts:5" | sudo tee -a /etc/resolv.conf
sudo chattr +i /etc/resolv.conf

# تست
nslookup youtube.com 8.8.8.8
```

### راه‌حل شماره 3: استفاده از IP مستقیم
```bash
# اضافه کردن IP های YouTube به hosts
sudo cp /etc/hosts /etc/hosts.backup
echo "142.250.191.14 youtube.com" | sudo tee -a /etc/hosts
echo "142.250.191.14 www.youtube.com" | sudo tee -a /etc/hosts
echo "172.217.16.110 youtubei.googleapis.com" | sudo tee -a /etc/hosts
echo "216.58.194.174 googlevideo.com" | sudo tee -a /etc/hosts

# تست
ping youtube.com
```

### راه‌حل شماره 4: تغییر DNS سرور
```bash
# استفاده از Cloudflare DNS
echo "nameserver 1.1.1.1" | sudo tee /etc/resolv.conf
echo "nameserver 1.0.0.1" | sudo tee -a /etc/resolv.conf

# یا استفاده از OpenDNS
echo "nameserver 208.67.222.222" | sudo tee /etc/resolv.conf
echo "nameserver 208.67.220.220" | sudo tee -a /etc/resolv.conf
```

## تست نهایی 🧪

### تست DNS
```bash
# تست DNS با سرورهای مختلف
nslookup youtube.com 8.8.8.8
nslookup youtube.com 1.1.1.1
nslookup youtube.com 208.67.222.222

# تست اتصال
ping -c 4 youtube.com
curl -I https://www.youtube.com
```

### تست دانلودر
```bash
# تست کامل
python3 emergency_youtube_test.py

# تست دانلودر اضطراری
python3 emergency_youtube_downloader.py test "https://www.youtube.com/watch?v=dL_r_PPlFtI"

# دانلود واقعی
python3 emergency_youtube_downloader.py download "https://www.youtube.com/watch?v=dL_r_PPlFtI" "720p"
```

## ویژگی‌های دانلودر اضطراری 🛡️

### مزایا:
- ✅ **DNS Bypass**: استفاده از IP مستقیم
- ✅ **Multiple DNS Fallback**: چندین سرور DNS پشتیبان
- ✅ **Enhanced Timeouts**: timeout های بالا برای اتصالات ضعیف
- ✅ **SSL Bypass**: عدم تایید گواهی SSL
- ✅ **Retry Logic**: تلاش مجدد خودکار
- ✅ **Direct IP Mapping**: نقشه‌برداری مستقیم IP

### استفاده:
```bash
# حالت تعاملی
python3 emergency_youtube_downloader.py

# دانلود مستقیم
python3 emergency_youtube_downloader.py download "URL" "QUALITY"

# دریافت اطلاعات
python3 emergency_youtube_downloader.py info "URL"

# تست اتصال
python3 emergency_youtube_downloader.py test "URL"
```

## عیب‌یابی سریع 🔍

### اگر همچنان خطا می‌دهد:

#### 1. بررسی اتصال اینترنت
```bash
ping 8.8.8.8
curl http://httpbin.org/ip
```

#### 2. بررسی فایروال
```bash
sudo ufw status
sudo iptables -L
```

#### 3. بررسی متغیرهای محیط
```bash
echo $PYTHONHTTPSVERIFY
echo $SOCKET_TIMEOUT
env | grep -E "(DNS|SOCKET|TIMEOUT)"
```

#### 4. اجرای تست کامل
```bash
python3 emergency_youtube_test.py connectivity
python3 emergency_youtube_test.py dns
python3 emergency_youtube_test.py youtube
```

## بازگردانی در صورت مشکل 🔄

### بازگردانی سریع
```bash
# اجرای اسکریپت بازیابی
sudo /tmp/emergency_recovery.sh

# یا بازگردانی دستی
sudo chattr -i /etc/resolv.conf
sudo cp /etc/resolv.conf.emergency_backup_* /etc/resolv.conf
sudo cp /etc/hosts.emergency_backup_* /etc/hosts
sudo systemctl restart systemd-resolved
```

## دستورات خلاصه برای کپی-پیست 📋

```bash
# حل فوری مشکل (کپی کنید و اجرا کنید)
sudo chmod +x emergency_dns_fix.sh && sudo ./emergency_dns_fix.sh
source /tmp/emergency_youtube_env.sh
python3 emergency_youtube_downloader.py test
python3 emergency_youtube_downloader.py download "https://www.youtube.com/watch?v=dL_r_PPlFtI"
```

## نکات مهم ⚠️

1. **این راه‌حل اضطراری است** - برای استفاده موقت
2. **بک‌آپ خودکار** - همه تنظیمات قبلی بک‌آپ می‌شود
3. **قابل بازگشت** - می‌توانید به تنظیمات قبلی برگردید
4. **مناسب سرور** - طراحی شده برای محیط سرور لینوکس

## پشتیبانی 📞

اگر همچنان مشکل دارید:
1. خروجی `python3 emergency_youtube_test.py` را بررسی کنید
2. فایل لاگ تولید شده را بررسی کنید
3. با مدیر سیستم در مورد تنظیمات شبکه صحبت کنید

**موفق باشید! 🎉**