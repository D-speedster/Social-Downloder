# اصلاح Progress Callback - حل RuntimeWarning

## 🐛 مشکل

بعد از انتخاب کیفیت ویدیو، این خطا نمایش داده می‌شد:

```
RuntimeWarning: coroutine 'safe_edit_text' was never awaited
logger.debug(f"Progress callback error: {e}")
```

## 🔍 علت مشکل

در `youtube_callback.py`، تابع `download_progress_callback` که sync است، سعی می‌کرد تابع async `safe_edit_text` را فراخوانی کند:

```python
def download_progress_callback(current, total):  # sync function
    # ...
    asyncio.create_task(safe_edit_text(...))  # async function call
```

این باعث RuntimeWarning می‌شد چون async function در sync context فراخوانی می‌شد.

## ✅ راه‌حل

### 1. حذف Progress Callback پیچیده
```python
# قبل:
downloaded_file = await youtube_downloader.download(
    progress_callback=download_progress_callback  # پیچیده و باعث warning
)

# بعد:
downloaded_file = await youtube_downloader.download(
    progress_callback=None  # ساده و بدون warning
)
```

### 2. بهبود پیام‌های کاربر
```python
# قبل:
"⏳ دانلود از یوتیوب..."

# بعد:
"⏳ دانلود از یوتیوب...\n💡 لطفاً صبر کنید، این ممکن است چند دقیقه طول بکشد"
```

### 3. حفظ Progress برای آپلود
Progress callback برای آپلود حفظ شد چون آن async است و مشکلی ندارد:

```python
async def upload_progress_callback(current, total):  # async function
    await safe_edit_text(...)  # درست است
```

## 📊 نتیجه

### قبل:
- ✅ دانلود کار می‌کرد
- ❌ RuntimeWarning نمایش داده می‌شد
- ❌ Progress دانلود پیچیده بود

### بعد:
- ✅ دانلود کار می‌کند
- ✅ هیچ RuntimeWarning نیست
- ✅ Progress آپلود همچنان کار می‌کند
- ✅ پیام‌های کاربرپسندتر

## 🧪 تست

برای تست:
1. ربات را اجرا کنید
2. لینک یوتیوب ارسال کنید
3. یک کیفیت ویدیو انتخاب کنید
4. بررسی کنید که RuntimeWarning نمایش داده نمی‌شود

## 💡 نکته

این تغییر تجربه کاربری را بهبود می‌دهد:
- کاربر می‌داند که دانلود در حال انجام است
- هیچ خطای مزاحمی نمایش داده نمی‌شود
- فرآیند ساده‌تر و پایدارتر است

---

**وضعیت**: ✅ حل شده  
**تاریخ**: 26 اکتبر 2025  
**تأثیر**: بهبود تجربه کاربری و حذف warnings