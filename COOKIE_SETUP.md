# راهنمای تنظیم کوکی یوتیوب

## چرا به کوکی نیاز داریم؟

یوتیوب برای جلوگیری از ربات‌ها، گاهی نیاز به احراز هویت دارد. با استفاده از کوکی‌های مرورگر، می‌توانیم این محدودیت را دور بزنیم.

## فایل کوکی

فایل کوکی باید در مسیر اصلی پروژه با نام `cookie_youtube.txt` قرار گیرد.

## نحوه استخراج کوکی از مرورگر

### روش 1: استفاده از افزونه مرورگر (ساده‌ترین)

#### برای Chrome/Edge:
1. افزونه "Get cookies.txt LOCALLY" را نصب کنید
2. به youtube.com بروید و لاگین کنید
3. روی آیکون افزونه کلیک کنید
4. "Export" را انتخاب کنید
5. فایل را با نام `cookie_youtube.txt` ذخیره کنید

#### برای Firefox:
1. افزونه "cookies.txt" را نصب کنید
2. به youtube.com بروید و لاگین کنید
3. روی آیکون افزونه کلیک کنید
4. فایل را با نام `cookie_youtube.txt` ذخیره کنید

### روش 2: استفاده از yt-dlp (پیشرفته)

```bash
# استخراج از Chrome
yt-dlp --cookies-from-browser chrome --cookies cookie_youtube.txt "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# استخراج از Firefox
yt-dlp --cookies-from-browser firefox --cookies cookie_youtube.txt "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# استخراج از Edge
yt-dlp --cookies-from-browser edge --cookies cookie_youtube.txt "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

## فرمت فایل کوکی

فایل باید در فرمت Netscape HTTP Cookie File باشد:

```
# Netscape HTTP Cookie File
.youtube.com	TRUE	/	TRUE	0	CONSENT	YES+
.youtube.com	TRUE	/	FALSE	1234567890	VISITOR_INFO1_LIVE	xxxxx
...
```

## بررسی صحت کوکی

برای اطمینان از صحت کوکی، این دستور را اجرا کنید:

```bash
yt-dlp --cookies cookie_youtube.txt "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --skip-download
```

اگر خطایی نداد، کوکی صحیح است.

## نکات مهم

⚠️ **امنیت**: فایل کوکی حاوی اطلاعات حساس است. آن را به اشتراک نگذارید!

⚠️ **انقضا**: کوکی‌ها معمولاً بعد از چند ماه منقضی می‌شوند. در صورت بروز خطا، کوکی را دوباره استخراج کنید.

⚠️ **حساب یوتیوب**: بهتر است از یک حساب جداگانه برای ربات استفاده کنید.

## عیب‌یابی

### خطا: "Sign in to confirm you're not a bot"
- کوکی وجود ندارد یا منقضی شده
- کوکی را دوباره استخراج کنید

### خطا: "Unable to extract video data"
- ویدیو خصوصی یا حذف شده است
- کوکی حساب شما دسترسی به ویدیو ندارد

### خطا: "HTTP Error 403: Forbidden"
- کوکی نامعتبر است
- از مرورگر خارج شوید، دوباره وارد شوید و کوکی را استخراج کنید

## وضعیت فعلی

✅ سیستم جدید یوتیوب از کوکی پشتیبانی می‌کند
✅ فایل `cookie_youtube.txt` به صورت خودکار شناسایی می‌شود
✅ در صورت عدم وجود کوکی، ربات بدون آن کار می‌کند (برای ویدیوهای عمومی)

## مسیر فایل

```
DownloaderYT-V1/
├── cookie_youtube.txt  ← فایل کوکی اینجا قرار گیرد
├── bot.py
├── main.py
└── plugins/
    ├── youtube_handler.py
    └── youtube_downloader.py
```
