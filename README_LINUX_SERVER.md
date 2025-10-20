# راهنمای نصب و راه‌اندازی در محیط سرور لینوکس

## مشکل DNS Resolution در سرور لینوکس

اگر با خطای زیر مواجه شده‌اید:
```
Failed to resolve 's' ([Errno -3] Temporary failure in name resolution)
```

این راهنما به شما کمک می‌کند تا مشکل را حل کنید.

## راه‌حل‌های سریع

### 1. راه‌اندازی خودکار (توصیه شده)

```bash
# اجرای اسکریپت راه‌اندازی
sudo python3 setup_linux_server.py

# تنظیم محیط
source youtube_env.sh

# تست عملکرد
python3 test_linux_server.py
```

### 2. راه‌حل دستی

#### تنظیم DNS

```bash
# بک‌آپ فایل فعلی
sudo cp /etc/resolv.conf /etc/resolv.conf.backup

# ویرایش فایل DNS
sudo nano /etc/resolv.conf
```

محتوای فایل را با این جایگزین کنید:
```
# Google DNS
nameserver 8.8.8.8
nameserver 8.8.4.4

# Cloudflare DNS
nameserver 1.1.1.1
nameserver 1.0.0.1

# تنظیمات بهینه‌سازی
options timeout:5
options attempts:3
options rotate
options single-request-reopen
```

#### تنظیم پارامترهای شبکه

```bash
# تنظیم پارامترهای TCP
sudo sysctl -w net.ipv4.tcp_keepalive_time=600
sudo sysctl -w net.ipv4.tcp_keepalive_intvl=60
sudo sysctl -w net.ipv4.tcp_keepalive_probes=3

# تنظیم بافرهای شبکه
sudo sysctl -w net.core.rmem_default=262144
sudo sysctl -w net.core.rmem_max=16777216
sudo sysctl -w net.core.wmem_default=262144
sudo sysctl -w net.core.wmem_max=16777216
```

#### نصب وابستگی‌ها

```bash
# به‌روزرسانی سیستم
sudo apt update && sudo apt upgrade -y

# نصب پکیج‌های مورد نیاز
sudo apt install -y python3-pip python3-dev build-essential \
    libssl-dev libffi-dev curl wget dnsutils

# نصب پکیج‌های پایتون
pip3 install --upgrade pip
pip3 install yt-dlp>=2023.12.30 aiohttp>=3.9.0 aiofiles>=23.0.0 \
    urllib3>=2.0.0 certifi>=2023.0.0 requests>=2.31.0
```

## تست عملکرد

### تست DNS

```bash
# تست DNS با nslookup
nslookup youtube.com 8.8.8.8

# تست DNS با dig
dig @8.8.8.8 youtube.com

# تست اتصال
ping -c 4 youtube.com
```

### تست دانلودر

```bash
# اجرای تست کامل
python3 test_linux_server.py

# تست دستی
python3 -c "
import asyncio
from plugins.youtube_advanced_downloader import youtube_downloader

async def test():
    info = await youtube_downloader.get_video_info('https://www.youtube.com/watch?v=dL_r_PPlFtI')
    print('موفق!' if info else 'ناموفق!')

asyncio.run(test())
"
```

## عیب‌یابی

### مشکلات رایج

#### 1. خطای DNS Resolution
```bash
# بررسی وضعیت DNS
systemctl status systemd-resolved

# راه‌اندازی مجدد DNS
sudo systemctl restart systemd-resolved

# پاک کردن کش DNS
sudo systemd-resolve --flush-caches
```

#### 2. مشکل اتصال HTTPS
```bash
# تنظیم متغیرهای محیط
export PYTHONHTTPSVERIFY=0
export CURL_CA_BUNDLE=""
export REQUESTS_CA_BUNDLE=""
```

#### 3. مشکل Timeout
```bash
# افزایش timeout
export SOCKET_TIMEOUT=120
export CONNECT_TIMEOUT=60
export READ_TIMEOUT=180
```

### لاگ‌های مفید

```bash
# مشاهده لاگ‌های شبکه
sudo journalctl -u systemd-networkd -f

# مشاهده لاگ‌های DNS
sudo journalctl -u systemd-resolved -f

# تست اتصال با curl
curl -v -I https://www.youtube.com
```

## تنظیمات پیشرفته

### فایروال

```bash
# اجازه اتصال خروجی HTTPS
sudo ufw allow out 443
sudo ufw allow out 80

# اجازه DNS
sudo ufw allow out 53
```

### پروکسی (در صورت نیاز)

```bash
# تنظیم پروکسی HTTP
export http_proxy=http://proxy-server:port
export https_proxy=http://proxy-server:port

# تنظیم پروکسی برای pip
pip3 install --proxy http://proxy-server:port package-name
```

### بهینه‌سازی عملکرد

```bash
# افزایش حد فایل‌های باز
ulimit -n 65536

# تنظیم اولویت پردازش
nice -n -10 python3 main.py
```

## اسکریپت‌های کمکی

### اسکریپت مانیتورینگ

```bash
#!/bin/bash
# monitor_youtube_downloader.sh

while true; do
    echo "=== $(date) ==="
    
    # بررسی DNS
    nslookup youtube.com | grep -q "Address" && echo "✅ DNS OK" || echo "❌ DNS Failed"
    
    # بررسی اتصال
    curl -s -I https://www.youtube.com | grep -q "200 OK" && echo "✅ Connection OK" || echo "❌ Connection Failed"
    
    sleep 60
done
```

### اسکریپت بازیابی

```bash
#!/bin/bash
# recovery_youtube_downloader.sh

echo "شروع بازیابی..."

# بازگردانی DNS
sudo cp /etc/resolv.conf.backup /etc/resolv.conf

# راه‌اندازی مجدد سرویس‌ها
sudo systemctl restart systemd-resolved
sudo systemctl restart networking

# پاک کردن کش
sudo systemd-resolve --flush-caches

echo "بازیابی کامل شد!"
```

## پشتیبانی

اگر همچنان با مشکل مواجه هستید:

1. لاگ‌های خطا را بررسی کنید
2. اسکریپت تست را اجرا کنید
3. تنظیمات شبکه سرور را بررسی کنید
4. با مدیر سیستم تماس بگیرید

## نکات مهم

- همیشه قبل از تغییر، بک‌آپ بگیرید
- تنظیمات را مرحله به مرحله اعمال کنید
- پس از هر تغییر، تست کنید
- در محیط production احتیاط کنید