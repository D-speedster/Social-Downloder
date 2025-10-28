# Design Document - Phase 2: Admin Panel Improvements

## Overview

این سند طراحی جزئیات پیاده‌سازی بهبودهای پنل ادمین و سیستم مانیتورینگ خودکار کوکی یوتیوب را شرح می‌دهد.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Telegram Bot                          │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐         ┌──────────────────────┐     │
│  │ Admin Panel  │────────▶│  Cookie Validator    │     │
│  │  (Updated)   │         │  (New Background     │     │
│  │              │         │   Service)           │     │
│  └──────────────┘         └──────────────────────┘     │
│         │                           │                    │
│         │                           │                    │
│         ▼                           ▼                    │
│  ┌──────────────┐         ┌──────────────────────┐     │
│  │ Admin        │         │  YouTube Downloader  │     │
│  │ Handlers     │         │  (Test Download)     │     │
│  └──────────────┘         └──────────────────────┘     │
│                                     │                    │
│                                     ▼                    │
│                           ┌──────────────────────┐     │
│                           │  Cookie File         │     │
│                           │  (cookie_youtube.txt)│     │
│                           └──────────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Admin Panel Keyboard (Updated)

**File**: `plugins/admin.py`

**Changes**:
- حذف دکمه "🔌 بررسی پروکسی"
- بازآرایی دکمه‌ها به صورت 2 ستونی

**Interface**:
```python
def admin_reply_kb() -> ReplyKeyboardMarkup:
    """
    ایجاد کیبورد پنل ادمین با 10 دکمه در 5 سطر (2 ستونی)
    
    Returns:
        ReplyKeyboardMarkup: کیبورد با layout جدید
    """
    buttons = [
        ["🛠 مدیریت", "📊 آمار کاربران"],
        ["🖥 وضعیت سرور", "📢 ارسال همگانی"],
        ["📢 تنظیم اسپانسر", "🔌 خاموش/روشن"],
        ["🔐 خاموش/روشن اسپانسری", "📺 خاموش/روشن تبلیغات"],
        ["🍪 مدیریت کوکی", "📺 تنظیم تبلیغات"]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)
```

### 2. User Statistics Handler (Updated)

**File**: `plugins/admin.py` یا فایل مربوطه

**Changes**:
- حذف بخش Task Statistics

**Interface**:
```python
async def show_user_statistics(client: Client, message: Message):
    """
    نمایش آمار کاربران بدون Task Statistics
    
    Args:
        client: Pyrogram client
        message: پیام دریافتی
    """
    db = DB()
    
    # آمار کاربران
    total_users = db.get_total_users()
    active_today = db.get_active_users_today()
    total_requests = db.get_total_requests()
    
    # ساخت پیام بدون Task Stats
    stats_text = (
        "📊 **آمار کاربران**\n\n"
        f"👥 کل کاربران: {total_users}\n"
        f"🟢 فعال امروز: {active_today}\n"
        f"📥 کل درخواست‌ها: {total_requests}\n"
    )
    
    await message.reply_text(stats_text)
```

### 3. Cookie Validator Service (New)

**File**: `plugins/cookie_validator.py` (جدید)

**Purpose**: سرویس background برای بررسی خودکار سلامت کوکی

**Interface**:
```python
class CookieValidator:
    """
    سرویس بررسی خودکار سلامت کوکی یوتیوب
    """
    
    def __init__(self, client: Client, admin_ids: list):
        """
        Args:
            client: Pyrogram client
            admin_ids: لیست ID ادمین‌ها
        """
        self.client = client
        self.admin_ids = admin_ids
        self.check_interval = 3 * 60 * 60  # 3 ساعت به ثانیه
        self.test_video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.cookie_file = "cookie_youtube.txt"
        self.logger = get_logger('cookie_validator')
        self.is_running = False
    
    async def start(self):
        """شروع سرویس بررسی خودکار"""
        pass
    
    async def stop(self):
        """توقف سرویس"""
        pass
    
    async def validate_cookie(self) -> tuple[bool, str]:
        """
        بررسی سلامت کوکی با تست دانلود
        
        Returns:
            tuple: (is_valid, error_message)
        """
        pass
    
    async def notify_admins(self, is_valid: bool, error_msg: str = None):
        """
        اطلاع‌رسانی به ادمین‌ها
        
        Args:
            is_valid: آیا کوکی معتبر است
            error_msg: پیام خطا (در صورت نامعتبر بودن)
        """
        pass
    
    async def _validation_loop(self):
        """حلقه اصلی بررسی (هر 3 ساعت)"""
        pass
```

### 4. Cookie Test Downloader

**Integration**: استفاده از `youtube_downloader.py` موجود

**Method**:
```python
async def test_cookie_download(url: str, cookie_file: str) -> tuple[bool, str]:
    """
    تست دانلود با کوکی برای بررسی سلامت
    
    Args:
        url: URL ویدیو تست
        cookie_file: مسیر فایل کوکی
    
    Returns:
        tuple: (success, error_message)
    """
    try:
        # استفاده از youtube_downloader برای تست
        from plugins.youtube_downloader import youtube_downloader
        
        # تنظیمات ساده برای تست
        ydl_opts = {
            'format': 'worst',  # کیفیت پایین برای سرعت
            'quiet': True,
            'no_warnings': True,
            'cookiefile': cookie_file,
            'extract_flat': True,  # فقط اطلاعات، بدون دانلود
            'skip_download': True
        }
        
        # تست استخراج اطلاعات
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
        if info:
            return (True, None)
        else:
            return (False, "Failed to extract video info")
            
    except Exception as e:
        return (False, str(e))
```

## Data Models

### Cookie Validation Result

```python
@dataclass
class CookieValidationResult:
    """نتیجه بررسی کوکی"""
    is_valid: bool
    timestamp: datetime
    error_message: Optional[str] = None
    test_url: str = ""
    duration_ms: int = 0
```

### Validation Log Entry

```python
@dataclass
class ValidationLogEntry:
    """ورودی لاگ بررسی"""
    timestamp: datetime
    is_valid: bool
    error_message: Optional[str]
    notified_admins: list[int]
```

## Error Handling

### Cookie File Not Found

```python
if not os.path.exists(cookie_file):
    error_msg = "⚠️ فایل کوکی یافت نشد!"
    logger.error(f"Cookie file not found: {cookie_file}")
    await notify_admins(False, error_msg)
    return
```

### YouTube API Error

```python
try:
    result = await test_cookie_download(url, cookie_file)
except Exception as e:
    error_msg = f"خطا در تست دانلود: {str(e)}"
    logger.error(f"Cookie validation error: {e}", exc_info=True)
    await notify_admins(False, error_msg)
```

### Network Timeout

```python
try:
    result = await asyncio.wait_for(
        test_cookie_download(url, cookie_file),
        timeout=30.0
    )
except asyncio.TimeoutError:
    error_msg = "⏱ زمان تست به پایان رسید"
    logger.warning("Cookie validation timeout")
    await notify_admins(False, error_msg)
```

## Testing Strategy

### Unit Tests

1. **Test Admin Keyboard Layout**
   - بررسی تعداد دکمه‌ها (10)
   - بررسی تعداد سطرها (5)
   - بررسی عدم وجود دکمه پروکسی

2. **Test Cookie Validator**
   - تست با کوکی معتبر
   - تست با کوکی نامعتبر
   - تست با فایل کوکی ناموجود
   - تست timeout

3. **Test Notification System**
   - تست ارسال به ادمین‌ها
   - تست عدم ارسال به کاربران عادی

### Integration Tests

1. **Test Full Validation Flow**
   - شروع سرویس
   - انتظار 3 ساعت (mock)
   - بررسی کوکی
   - اطلاع‌رسانی به ادمین

2. **Test Admin Panel**
   - بررسی layout جدید
   - تست عدم وجود handler پروکسی
   - تست آمار کاربران بدون Task Stats

## Configuration

### Constants

```python
# در plugins/cookie_validator.py
COOKIE_CHECK_INTERVAL = 3 * 60 * 60  # 3 ساعت
TEST_VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
COOKIE_FILE_PATH = "cookie_youtube.txt"
VALIDATION_TIMEOUT = 30  # ثانیه
```

### Admin IDs

```python
# در config.py یا plugins/admin.py
ADMIN = [123456789, 987654321]  # لیست ID ادمین‌ها
```

## Logging

### Log Format

```python
# Cookie Validator Logger
cookie_logger = logging.getLogger('cookie_validator')
cookie_logger.setLevel(logging.INFO)

handler = logging.FileHandler('./logs/cookie_validator.log', encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
cookie_logger.addHandler(handler)
```

### Log Messages

```python
# شروع بررسی
logger.info("Starting cookie validation check")

# نتیجه موفق
logger.info(f"Cookie validation successful - Duration: {duration}ms")

# نتیجه ناموفق
logger.error(f"Cookie validation failed - Error: {error_msg}")

# اطلاع‌رسانی به ادمین
logger.info(f"Notified {len(admin_ids)} admins about cookie status")
```

## Performance Considerations

### Background Task

- استفاده از `asyncio.create_task()` برای اجرای background
- عدم block کردن main event loop
- استفاده از `asyncio.sleep()` برای interval

### Resource Usage

- تست دانلود با کیفیت پایین (`worst`)
- استفاده از `extract_flat=True` برای سرعت
- timeout 30 ثانیه برای جلوگیری از hang

### Memory Management

- پاکسازی فایل‌های موقت بعد از تست
- عدم ذخیره‌سازی نتایج قدیمی در memory
- استفاده از generator برای لاگ‌ها

## Security Considerations

### Admin-Only Access

```python
# بررسی ادمین بودن
if message.from_user.id not in ADMIN:
    return
```

### Cookie File Protection

- عدم نمایش محتوای کوکی در پیام‌ها
- عدم لاگ کردن محتوای کوکی
- فقط لاگ کردن وضعیت (valid/invalid)

### Error Message Sanitization

```python
# حذف اطلاعات حساس از پیام خطا
safe_error = str(error).replace(cookie_file, "[COOKIE_FILE]")
```

## Deployment

### Startup Sequence

1. راه‌اندازی ربات
2. شروع Cookie Validator Service
3. اولین بررسی بعد از 3 ساعت
4. ادامه بررسی‌های دوره‌ای

### Shutdown Sequence

1. دریافت سیگنال shutdown
2. توقف Cookie Validator Service
3. اتمام بررسی جاری (اگر در حال اجرا است)
4. بستن ربات

---

**تاریخ ایجاد**: 28 اکتبر 2025  
**نسخه**: 1.0  
**وضعیت**: آماده برای پیاده‌سازی