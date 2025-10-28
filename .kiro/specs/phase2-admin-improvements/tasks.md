# Implementation Plan - Phase 2: Admin Panel Improvements

## Task List

- [x] 1. بررسی و شناسایی فایل‌های مربوط به پنل ادمین


  - شناسایی فایل admin.py و handler های مربوطه
  - بررسی ساختار کیبورد فعلی
  - شناسایی handler های proxy check
  - _Requirements: 1.1, 2.1_





- [ ] 2. حذف بخش بررسی پروکسی
- [x] 2.1 حذف دکمه "🔌 بررسی پروکسی" از کیبورد ادمین


  - پیدا کردن تابع ایجاد کیبورد ادمین
  - حذف دکمه پروکسی از لیست دکمه‌ها
  - _Requirements: 1.1_



- [ ] 2.2 حذف handler های مربوط به proxy check
  - شناسایی تمام callback handler های proxy
  - حذف توابع مربوط به proxy check
  - حذف import های غیرضروری

  - _Requirements: 1.2, 1.3, 1.4_

- [x] 3. بازآرایی دکمه‌های پنل ادمین



- [ ] 3.1 تغییر layout کیبورد به 2 ستونی
  - تغییر ساختار buttons به 5 سطر × 2 ستون
  - تست نمایش صحیح در تلگرام
  - _Requirements: 2.2, 2.3_



- [ ] 3.2 بهینه‌سازی ترتیب دکمه‌ها
  - مرتب کردن دکمه‌ها به صورت منطقی




  - گروه‌بندی دکمه‌های مرتبط
  - _Requirements: 2.3_

- [x] 4. حذف آمار وظایف از بخش آمار کاربران

- [ ] 4.1 شناسایی handler آمار کاربران
  - پیدا کردن تابع نمایش آمار
  - بررسی کدهای مربوط به Task Stats
  - _Requirements: 3.1_


- [ ] 4.2 حذف بخش Task Statistics
  - حذف کدهای محاسبه Task Stats
  - حذف نمایش Task Stats از پیام
  - تست عملکرد سایر بخش‌های آمار
  - _Requirements: 3.2, 3.3, 3.4_


- [ ] 5. ایجاد سرویس Cookie Validator
- [ ] 5.1 ایجاد فایل cookie_validator.py
  - ایجاد ساختار اولیه کلاس CookieValidator
  - تعریف constants (interval, test URL, etc.)

  - راه‌اندازی logger مخصوص
  - _Requirements: 4.1, 5.1, 5.2_

- [ ] 5.2 پیاده‌سازی تابع test_cookie_download
  - استفاده از yt-dlp برای تست
  - تنظیمات بهینه برای تست سریع

  - مدیریت خطاها و timeout
  - _Requirements: 4.2, 4.3_

- [x] 5.3 پیاده‌سازی تابع validate_cookie



  - بررسی وجود فایل کوکی
  - فراخوانی test_cookie_download
  - برگرداندن نتیجه (valid/invalid + error)
  - _Requirements: 4.2, 4.3, 4.6_


- [ ] 5.4 پیاده‌سازی تابع notify_admins
  - ساخت پیام مناسب (✅ معتبر / ❌ نامعتبر)
  - ارسال به تمام ادمین‌ها

  - مدیریت خطای ارسال پیام

  - _Requirements: 4.4, 4.5, 4.9_

- [ ] 5.5 پیاده‌سازی حلقه اصلی بررسی (_validation_loop)
  - ایجاد infinite loop با interval 3 ساعت

  - فراخوانی validate_cookie
  - فراخوانی notify_admins
  - مدیریت خطاها و retry
  - _Requirements: 4.1, 4.7, 4.8_



- [ ] 5.6 پیاده‌سازی توابع start و stop
  - start: شروع background task
  - stop: توقف graceful سرویس
  - مدیریت state (is_running)
  - _Requirements: 4.7, 4.8_


- [ ] 6. یکپارچه‌سازی Cookie Validator با ربات اصلی
- [ ] 6.1 اضافه کردن Cookie Validator به main bot
  - import کردن CookieValidator



  - ایجاد instance با admin IDs
  - شروع سرویس در startup
  - _Requirements: 4.7_

- [x] 6.2 مدیریت shutdown

  - توقف سرویس در shutdown
  - cleanup منابع
  - _Requirements: 4.8_

- [ ] 7. لاگ‌گذاری و مانیتورینگ
- [x] 7.1 راه‌اندازی logger مخصوص

  - ایجاد فایل لاگ cookie_validator.log
  - تنظیم format و level
  - _Requirements: 5.1_


- [ ] 7.2 اضافه کردن log statements
  - لاگ شروع/پایان هر بررسی
  - لاگ نتیجه (موفق/ناموفق)
  - لاگ خطاها با stack trace
  - _Requirements: 5.2, 5.3, 5.4, 5.5_

- [ ] 8. تنظیمات و Configuration
- [ ] 8.1 تعریف constants قابل تغییر
  - COOKIE_CHECK_INTERVAL
  - TEST_VIDEO_URL
  - COOKIE_FILE_PATH
  - VALIDATION_TIMEOUT
  - _Requirements: 6.1, 6.2_

- [ ] 8.2 خواندن admin IDs از config
  - استفاده از ADMIN list موجود
  - مدیریت خطای عدم تعریف ادمین
  - _Requirements: 6.3_

- [ ] 9. تست و عیب‌یابی
- [ ] 9.1 تست دستی پنل ادمین
  - بررسی layout جدید (2 ستونی)
  - تست عدم وجود دکمه پروکسی
  - تست آمار کاربران بدون Task Stats
  - _Requirements: 1.1, 2.2, 3.2_

- [ ] 9.2 تست Cookie Validator
  - تست با کوکی معتبر
  - تست با کوکی نامعتبر
  - تست با فایل ناموجود
  - تست timeout
  - _Requirements: 4.2, 4.3, 4.4, 4.5, 4.10_

- [ ] 9.3 تست اطلاع‌رسانی
  - بررسی ارسال پیام به ادمین‌ها
  - بررسی عدم ارسال به کاربران عادی
  - بررسی فرمت پیام‌ها
  - _Requirements: 4.4, 4.5, 4.9_

- [x] 10. مستندسازی


- [x] 10.1 ایجاد README برای Cookie Validator

  - توضیح نحوه کار
  - تنظیمات قابل تغییر
  - troubleshooting
  - _Requirements: 6.4_

- [x] 10.2 به‌روزرسانی مستندات پنل ادمین

  - توضیح تغییرات layout
  - لیست دکمه‌های جدید
  - _Requirements: 2.1, 2.2_

---

**نکات مهم**:
- هر task باید به صورت مستقل قابل تست باشد
- بعد از هر task، کد را تست کنید
- لاگ‌ها را بررسی کنید
- از git commit برای هر task استفاده کنید

**ترتیب اجرا**:
1. ابتدا tasks 1-4 (پنل ادمین)
2. سپس tasks 5-6 (Cookie Validator)
3. در نهایت tasks 7-10 (لاگ، تست، مستندات)

---

**تاریخ ایجاد**: 28 اکتبر 2025  
**نسخه**: 1.0  
**وضعیت**: آماده برای اجرا