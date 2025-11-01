# ⚠️ نیاز به Restart ربات

## مشکل
لینک رادیو جوان هیچ واکنشی ندارد.

## علت
ربات قبل از اضافه کردن `radiojavan_handler` راه‌اندازی شده و handler جدید load نشده است.

## راه حل
ربات را restart کنید.

### روش 1: Ctrl+C و راه‌اندازی مجدد
```bash
# در ترمینالی که ربات در آن اجرا می‌شود:
Ctrl+C

# سپس دوباره راه‌اندازی کنید:
python bot.py
```

### روش 2: استفاده از start_bot_robust.py
```bash
python start_bot_robust.py
```

## بررسی بعد از Restart

### 1. بررسی لاگ startup
باید ببینید:
```
✅ RadioJavan Handler loaded
   - Pattern: radiojavan.com/song/...
   - Independent from other downloaders
```

### 2. تست لینک
```
https://play.radiojavan.com/song/sijal-baz-mirim-baham-(ft-sami-low)
```

### 3. بررسی لاگ
```bash
tail -f logs/radiojavan_handler.log
```

باید ببینید:
```
RadioJavan handler received text: https://play.radiojavan.com/song/...
RadioJavan request from user 123456: https://play.radiojavan.com/song/...
Fetching song info from: https://play.radiojavan.com/song/...
```

## اگر هنوز کار نکرد

### بررسی 1: آیا radiojavanapi نصب شده؟
```bash
pip list | grep radiojavanapi
```

اگر نصب نشده:
```bash
pip install radiojavanapi
```

### بررسی 2: آیا import موفق بوده؟
در لاگ startup دنبال خطا بگردید:
```bash
grep -i "error\|exception" startup.log
```

### بررسی 3: آیا handler ثبت شده؟
در `bot.py` باید ببینید:
```python
import plugins.radiojavan_handler  # 🎵 RadioJavan downloader
```

## خلاصه

✅ فایل‌ها اضافه شدند
✅ کد صحیح است
⚠️ **فقط نیاز به restart دارد**

بعد از restart، همه چیز باید کار کند! 🚀
