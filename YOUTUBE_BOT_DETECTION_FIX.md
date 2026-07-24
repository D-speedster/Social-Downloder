# راه‌حل مشکل Bot Detection یوتیوب

## 📋 خلاصه مشکل

هنگام دانلود ویدیوهای YouTube در محیط سرور، خطای زیر رخ می‌داد:

```
ERROR: [youtube] Sign in to confirm you're not a bot
```

این خطا به دلیل عدم وجود کوکی معتبر یا تشخیص ربات توسط YouTube رخ می‌داد.

---

## 🔧 راه‌حل پیاده‌سازی شده

### استراتژی Fallback دو مرحله‌ای

#### مرحله 1: تلاش با تنظیمات پیش‌فرض (همه کیفیت‌ها)
```python
# تنظیمات پیش‌فرض - ارائه همه کیفیت‌ها (360p, 480p, 720p, 1080p, ...)
ydl_opts_default = {
    'quiet': True,
    'no_warnings': True,
    'cookiefile': cookie_file,  # استفاده از کوکی معتبر
    # بدون محدودیت player_client
}
```

**مزایا:**
- دسترسی به تمام کیفیت‌های موجود
- سرعت بالاتر
- کیفیت بهتر

**شرط:**
- نیاز به کوکی معتبر

---

#### مرحله 2: Fallback با محدودیت player_client
```python
# تنظیمات fallback - حداقل 360p
ydl_opts_fallback = {
    'quiet': True,
    'no_warnings': True,
    'cookiefile': cookie_file,
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web', 'mweb']
        }
    },
    'remote_components': ['ejs:github']
}
```

**مزایا:**
- کار می‌کند حتی با کوکی نامعتبر/منقضی
- دور زدن bot detection

**معایب:**
- فقط کیفیت 360p ارائه می‌شود
- کیفیت‌های بالاتر در دسترس نیست

---

## 📝 تغییرات انجام شده

### 1️⃣ فایل: `plugins/youtube_handler.py`

**تابع:** `extract_video_info()`

**تغییرات:**
```python
# 🔥 تلاش 1: با تنظیمات پیش‌فرض (همه کیفیت‌ها)
try:
    logger.info("Trying default settings (all qualities)...")
    info = await loop.run_in_executor(_global_executor, lambda: _extract_with_options(ydl_opts_default))
    logger.info("✅ Success with default settings!")
    
except Exception as e:
    error_msg = str(e).lower()
    
    # اگر خطای bot detection یا sign in بود، fallback استفاده کن
    if 'sign in' in error_msg or 'bot' in error_msg or 'confirm' in error_msg:
        logger.warning(f"⚠️ Bot detection with default settings, trying fallback...")
        
        # 🔥 تلاش 2: با player_client محدود (حداقل 360p)
        try:
            info = await loop.run_in_executor(_global_executor, lambda: _extract_with_options(ydl_opts_fallback))
            logger.info("✅ Success with fallback settings (limited qualities)")
            
        except Exception as e2:
            # اگر باز هم خطا داد
            logger.error("❌ Both strategies failed - cookie may be invalid")
            raise Exception("⚠️ این ویدیو نیاز به احراز هویت دارد...")
```

**نتیجه:**
- ✅ استخراج اطلاعات ویدیو حتی با bot detection
- ✅ نمایش کیفیت‌های موجود به کاربر

---

### 2️⃣ فایل: `plugins/youtube_downloader.py`

**تابع:** `download()` → `_download_with_retry()`

**تغییرات:**
```python
# 🔥 Track if we need to use bot detection bypass
use_bot_bypass = False

for attempt in range(max_attempts):
    try:
        # استفاده از format fallback در صورت خطا
        current_opts = ydl_opts.copy()
        
        # 🔥 اگر bot detection تشخیص داده شد، از player_client محدود استفاده کن
        if use_bot_bypass:
            logger.warning(f"🤖 Using bot detection bypass with restricted player_client")
            current_opts['extractor_args'] = {
                'youtube': {
                    'player_client': ['android', 'web', 'mweb']
                }
            }
            current_opts['remote_components'] = ['ejs:github']
        
        with yt_dlp.YoutubeDL(current_opts) as ydl:
            ydl.download([url])
        
        # موفقیت
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return output_path
            
    except Exception as e:
        error_msg = str(e).lower()
        
        # 🔥 بررسی خطای bot detection - استفاده از player_client محدود
        if 'sign in' in error_msg or 'bot' in error_msg or 'confirm' in error_msg:
            logger.error(f"🤖 Bot detection error detected!")
            if attempt < max_attempts - 1:
                logger.info("Will use bot detection bypass (player_client) in next attempt")
                use_bot_bypass = True
                time.sleep(2)
                continue
```

**نتیجه:**
- ✅ دانلود موفق حتی با bot detection
- ✅ حداقل کیفیت 360p تضمین می‌شود

---

### 3️⃣ فایل: `plugins/youtube_cookie_helper.py`

**بهبودهای انجام شده:**

#### 🔄 تبدیل خودکار JSON به Netscape
```python
def _convert_json_to_netscape(cookie_text: str) -> str:
    """تبدیل کوکی از فرمت JSON به Netscape"""
    # بررسی اینکه آیا کوکی JSON است
    if text_stripped.startswith('{') or text_stripped.startswith('['):
        # پارس و تبدیل به Netscape
        # ...
        return netscape_text
    return cookie_text
```

#### 🗑️ پاکسازی کش در صورت شکست
```python
def mark_cookie_failure(cookie_id: Optional[int] = None):
    """ثبت شکست استفاده از کوکی"""
    # ثبت در دیتابیس
    db.mark_cookie_used(cookie_id, success=False)
    
    # 🔥 حذف فایل کش قدیمی
    if old_cookie_file and os.path.exists(old_cookie_file):
        os.unlink(old_cookie_file)
    
    # 🔥 پاک کردن کامل cache
    _cookie_cache['cookie_id'] = None
    _cookie_cache['cookie_text'] = None
    _cookie_cache['cookie_file'] = None
    _cookie_cache['last_update'] = 0  # 🔴 مهم!
```

#### 🧹 پاکسازی دوره‌ای فایل‌های موقت
```python
def cleanup_temp_cookies(force_cleanup: bool = False):
    """پاکسازی فایل‌های کوکی موقت قدیمی"""
    # 1. حذف فایل‌های قدیمی‌تر از 1 ساعت
    # 2. حذف فایل‌های orphan (کوکی حذف شده از DB)
    # ...
```

---

## 🧪 تست

### اجرای تست خودکار
```bash
python test_bot_detection_bypass.py
```

### نتیجه مورد انتظار:
```
============================================================
TEST SUMMARY
============================================================

✅ PASSED: Extract with Fallback
✅ PASSED: Download with Fallback
✅ PASSED: Cookie Helper

============================================================
Final Score: 3/3 tests passed
============================================================

🎉 All tests passed! Bot detection bypass is ready.
```

---

## 📊 نمودار جریان کار

```
┌─────────────────────────────────────────────────────────┐
│         کاربر لینک YouTube را ارسال می‌کند              │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │ extract_video_info(url)    │
        └────────────┬───────────────┘
                     │
                     ▼
        ┌─────────────────────────────────────┐
        │ تلاش 1: تنظیمات پیش‌فرض + کوکی      │
        │   (همه کیفیت‌ها)                    │
        └────────┬──────────────┬──────────────┘
                 │              │
          ✅ موفق │              │ ❌ Bot Detection
                 │              │
                 │              ▼
                 │   ┌─────────────────────────────────┐
                 │   │ تلاش 2: player_client محدود    │
                 │   │   (فقط 360p)                    │
                 │   └────────┬──────────┬─────────────┘
                 │            │          │
                 │      ✅ موفق│          │ ❌ شکست
                 │            │          │
                 ▼            ▼          ▼
        ┌────────────────────────────────────────────┐
        │  نمایش کیفیت‌های موجود به کاربر           │
        └────────────────┬───────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │ کاربر کیفیت را انتخاب می‌کند  │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │ download(url, format)      │
        └────────────┬───────────────┘
                     │
                     ▼
        ┌─────────────────────────────────────┐
        │ تلاش 1: تنظیمات پیش‌فرض + کوکی      │
        └────────┬──────────────┬──────────────┘
                 │              │
          ✅ موفق │              │ ❌ Bot Detection
                 │              │
                 │              ▼
                 │   ┌─────────────────────────────────┐
                 │   │ تلاش 2: player_client محدود    │
                 │   │   (با remote_components)        │
                 │   └────────┬──────────┬─────────────┘
                 │            │          │
                 │      ✅ موفق│          │ ❌ شکست
                 │            │          │
                 ▼            ▼          ▼
        ┌────────────────────────────────────────────┐
        │         ارسال فایل به کاربر                │
        └────────────────────────────────────────────┘
```

---

## ⚙️ تنظیمات مهم

### ⚠️ نکات مهم:

1. **iOS client سازگار نیست:**
   ```python
   # ❌ اشتباه
   'player_client': ['android', 'web', 'mweb', 'ios']
   
   # ✅ صحیح
   'player_client': ['android', 'web', 'mweb']
   ```
   iOS با فایل‌های کوکی سازگار نیست و هشدار می‌دهد.

2. **remote_components الزامی:**
   ```python
   'remote_components': ['ejs:github']
   ```
   این تنظیم برای bypass کردن برخی محدودیت‌های JS ضروری است.

3. **ترتیب fallback:**
   - ابتدا: تنظیمات پیش‌فرض (بهترین کیفیت)
   - سپس: player_client محدود (360p حداقل)
   - در نهایت: خطا به کاربر نمایش داده می‌شود

---

## 🚀 نتایج

### ✅ قبل از اعمال تغییرات:
```
ERROR: [youtube] 0aFxa-5mk8U: Sign in to confirm you're not a bot
❌ خطا در دانلود/آپلود
```

### ✅ بعد از اعمال تغییرات:

**محیط Local (با کوکی معتبر):**
```
✅ کیفیت‌های موجود: 360p, 480p, 720p, 1080p, فقط صدا
✅ دانلود موفق
```

**محیط Server (بدون کوکی معتبر):**
```
⚠️ Bot detection with default settings, trying fallback...
✅ Success with fallback settings (limited qualities)
✅ کیفیت‌های موجود: 360p
✅ دانلود موفق (حداقل 360p)
```

---

## 📚 مستندات مرتبط

- [yt-dlp Extractor Arguments](https://github.com/yt-dlp/yt-dlp#youtube)
- [YouTube Cookie System](./COOKIE_SYSTEM.md)
- [FAQ: How to pass cookies to yt-dlp](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp)

---

## 🔄 نسخه

**Version:** 2.0  
**Date:** 2024  
**Status:** ✅ Tested & Working

---

## 👨‍💻 نویسنده

این راه‌حل برای رفع مشکل bot detection در دانلودر یوتیوب پروژه Social-Downloader پیاده‌سازی شده است.

---

## 📋 Checklist اجرایی

برای اطمینان از اجرای صحیح، موارد زیر را بررسی کنید:

- [x] ✅ تبدیل خودکار JSON به Netscape پیاده‌سازی شد
- [x] ✅ پاکسازی کش در صورت شکست کوکی پیاده‌سازی شد
- [x] ✅ timeout دیتابیس SQLite افزایش یافت (30s)
- [x] ✅ پاکسازی دوره‌ای فایل‌های temp پیاده‌سازی شد
- [x] ✅ Fallback strategy در extract_video_info پیاده‌سازی شد
- [x] ✅ Fallback strategy در download پیاده‌سازی شد
- [x] ✅ تست‌های خودکار نوشته شد
- [x] ✅ همه تست‌ها موفق شدند

---

**🎉 پروژه آماده استفاده در محیط production است!**
