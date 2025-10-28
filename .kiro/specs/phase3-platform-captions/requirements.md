# Requirements Document - Phase 3: Platform-Specific Captions

## Introduction

این فاز شامل پیاده‌سازی caption های اختصاصی برای هر پلتفرم است. هر شبکه اجتماعی باید اطلاعات مرتبط و مفید خود را به صورت زیبا و منظم نمایش دهد.

## Glossary

- **Caption**: متن توضیحات زیر فایل ارسالی در تلگرام
- **Platform**: شبکه اجتماعی (TikTok, Spotify, SoundCloud, Pinterest, Instagram, etc.)
- **Metadata**: اطلاعات مربوط به محتوا (عنوان، سازنده، مدت زمان، etc.)
- **Universal Downloader**: سیستم دانلود یکپارچه که تمام پلتفرم‌ها را پشتیبانی می‌کند

## Requirements

### Requirement 1: Caption اختصاصی TikTok

**User Story:** به عنوان کاربر، می‌خواهم وقتی ویدیو TikTok دانلود می‌کنم، اطلاعات مرتبط با TikTok را ببینم.

#### Acceptance Criteria

1. WHEN کاربر لینک TikTok ارسال می‌کند، THE System SHALL caption با فرمت زیر نمایش دهد:
   ```
   🎬 ویدیو از TikTok
   👤 سازنده: @username
   📄 عنوان: [title/caption]
   ⏱️ مدت زمان: X دقیقه و Y ثانیه
   ```

2. THE System SHALL فیلدهای زیر را از API response استخراج کند:
   - `author` یا `unique_id` برای نام سازنده
   - `title` برای عنوان/کپشن
   - `duration` برای مدت زمان

3. THE System SHALL اگر عنوان خیلی طولانی باشد، آن را به 100 کاراکتر محدود کند

4. THE System SHALL مدت زمان را به فرمت "X دقیقه و Y ثانیه" تبدیل کند

### Requirement 2: Caption اختصاصی Spotify

**User Story:** به عنوان کاربر، می‌خواهم وقتی آهنگ Spotify دانلود می‌کنم، اطلاعات آهنگ را ببینم.

#### Acceptance Criteria

1. WHEN کاربر لینک Spotify ارسال می‌کند، THE System SHALL caption با فرمت زیر نمایش دهد:
   ```
   🎵 آهنگ از Spotify
   🎧 نام آهنگ: [title]
   👤 هنرمند: [artist]
   ⏱️ مدت زمان: X:YZ
   ```

2. THE System SHALL فیلدهای زیر را استخراج کند:
   - `title` برای نام آهنگ
   - `artist` از URL یا metadata
   - `duration` برای مدت زمان

3. THE System SHALL مدت زمان را به فرمت "M:SS" نمایش دهد

### Requirement 3: Caption اختصاصی SoundCloud

**User Story:** به عنوان کاربر، می‌خواهم وقتی موزیک SoundCloud دانلود می‌کنم، اطلاعات کامل قطعه را ببینم.

#### Acceptance Criteria

1. WHEN کاربر لینک SoundCloud ارسال می‌کند، THE System SHALL caption با فرمت زیر نمایش دهد:
   ```
   🎶 موزیک از SoundCloud
   🎧 نام قطعه: [title]
   👤 هنرمند: [author]
   ⏱️ مدت زمان: X:YZ
   ```

2. THE System SHALL از `title` استفاده کند چون معمولاً شامل اطلاعات کامل است (Mashup, Remix, etc.)

3. THE System SHALL از `author` برای نام هنرمند استفاده کند

### Requirement 4: Caption اختصاصی Pinterest

**User Story:** به عنوان کاربر، می‌خواهم وقتی تصویر Pinterest دانلود می‌کنم، اطلاعات تصویر را ببینم.

#### Acceptance Criteria

1. WHEN کاربر لینک Pinterest ارسال می‌کند، THE System SHALL caption با فرمت زیر نمایش دهد:
   ```
   🖼 تصویر از Pinterest
   👤 منتشرکننده: [author]
   📏 ابعاد تصویر: WxH
   ```

2. THE System SHALL `title` را نمایش ندهد چون معمولاً خالی یا بی‌فایده است

3. THE System SHALL `resolution` را برای نمایش کیفیت تصویر استخراج کند

4. THE System SHALL `duration` را نمایش ندهد چون برای تصویر 0 است

### Requirement 5: Caption اختصاصی Instagram

**User Story:** به عنوان کاربر، می‌خواهم وقتی پست Instagram دانلود می‌کنم، اطلاعات کامل پست را ببینم.

#### Acceptance Criteria

1. WHEN کاربر لینک Instagram ارسال می‌کند، THE System SHALL caption با فرمت زیر نمایش دهد:
   ```
   📸 پست از Instagram
   👤 پیج: @username
   📝 توضیح: [caption]
   ❤️ لایک‌ها: [like_count]
   📍 موقعیت: [location] (اختیاری)
   🎞 کیفیت ویدیو: WxH (برای ویدیو)
   📏 کیفیت تصویر: WxH (برای عکس)
   ```

2. THE System SHALL فیلدهای زیر را استخراج کند:
   - `owner.username` برای نام پیج
   - `title` یا `caption` برای توضیحات
   - `like_count` برای تعداد لایک
   - `location.name` برای موقعیت (اگر موجود باشد)
   - `resolution` برای کیفیت

3. THE System SHALL بر اساس نوع محتوا (image/video) emoji مناسب نمایش دهد

4. THE System SHALL اگر `duration` کمتر از 60 ثانیه باشد، آن را نمایش ندهد

### Requirement 6: Caption پیش‌فرض برای سایر پلتفرم‌ها

**User Story:** به عنوان کاربر، می‌خواهم برای پلتفرم‌های دیگر هم caption مناسب ببینم.

#### Acceptance Criteria

1. WHEN کاربر لینک از پلتفرم دیگری ارسال می‌کند، THE System SHALL caption عمومی با اطلاعات موجود نمایش دهد

2. THE System SHALL حداقل `title` و `author` را نمایش دهد

3. THE System SHALL اگر اطلاعات کافی نباشد، فقط نام پلتفرم را نمایش دهد

### Requirement 7: مدیریت فیلدهای خالی

**User Story:** به عنوان کاربر، می‌خواهم اگر برخی اطلاعات موجود نباشد، caption زیبا و بدون خطا باشد.

#### Acceptance Criteria

1. THE System SHALL اگر فیلدی خالی یا None باشد، آن را نمایش ندهد

2. THE System SHALL اگر `title` خیلی طولانی باشد، آن را کوتاه کند و "..." اضافه کند

3. THE System SHALL اگر `duration` 0 باشد، آن را نمایش ندهد

4. THE System SHALL اگر `like_count` 0 باشد، آن را نمایش ندهد

### Requirement 8: فرمت زمان

**User Story:** به عنوان کاربر، می‌خواهم مدت زمان به صورت خوانا نمایش داده شود.

#### Acceptance Criteria

1. THE System SHALL برای زمان‌های کمتر از 60 ثانیه: "X ثانیه"

2. THE System SHALL برای زمان‌های 60 ثانیه تا 1 ساعت: "X دقیقه و Y ثانیه"

3. THE System SHALL برای زمان‌های بیش از 1 ساعت: "X ساعت و Y دقیقه"

4. THE System SHALL برای Spotify/SoundCloud: فرمت "M:SS" یا "H:MM:SS"

---

## Non-Functional Requirements

### Maintainability
- کد باید ماژولار و قابل توسعه باشد
- اضافه کردن پلتفرم جدید باید آسان باشد

### Performance
- ساخت caption نباید بیش از 10ms طول بکشد

### Usability
- Caption ها باید خوانا و زیبا باشند
- Emoji ها باید مناسب و معنادار باشند

---

**تاریخ ایجاد**: 28 اکتبر 2025  
**نسخه**: 1.0  
**وضعیت**: آماده برای طراحی