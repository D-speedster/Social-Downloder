# TODO - کارهای باقی‌مانده پروژه

## 🔴 اولویت بالا (High Priority)

### 1. حذف کامل AdminStepCompatibility و مهاجرت به AdminUserState

**وضعیت فعلی:** ✅ Compatibility Layer فعال است  
**هدف نهایی:** ❌ حذف کامل wrapper و استفاده مستقیم از AdminUserState

**دلیل:**
- Compatibility layer فقط یک راه‌حل **موقت** است
- فقط با **یک ادمین** کار می‌کند (ADMIN[0])
- **Conflict بین چند ادمین** را حل نمی‌کند
- باعث **overhead** و **complexity** اضافی می‌شود

**کارهای لازم:**

#### مرحله 1: شناسایی تمام استفاده‌ها (145 مورد)
```bash
Select-String -Path "plugins/admin.py" -Pattern "admin_step" | Measure-Object
# خروجی فعلی: 145 مورد
```

#### مرحله 2: الگوی مهاجرت
برای هر handler که از `admin_step` استفاده می‌کند:

```python
# ❌ قبل (با compatibility layer):
admin_step['broadcast'] = 1

# ✅ بعد (مستقیم از AdminUserState):
user_id = message.from_user.id  # یا callback_query.from_user.id
state = get_admin_user_state(user_id)
state.broadcast['step'] = 1
```

#### مرحله 3: مهاجرت فیلترها
```python
# ❌ قبل:
filter = filters.create(lambda _, __, m: admin_step.get('broadcast') == 2)

# ✅ بعد:
def broadcast_filter_func(_, __, m):
    if not m.from_user:
        return False
    user_id = m.from_user.id
    state = get_admin_user_state(user_id)
    return state.broadcast['step'] == 2

filter = filters.create(broadcast_filter_func)
```

#### مرحله 4: حذف Compatibility Layer
بعد از مهاجرت کامل، این بخش را از `plugins/admin.py` حذف کنید:

```python
# خطوط ~67-160 (تقریباً)
class AdminStepCompatibility:
    ...

admin_step = AdminStepCompatibility()
```

**تخمین زمان:** 2-4 ساعت کار دستی  
**منابع:**
- `admin_step_migration_example.py` - نمونه‌های واقعی قبل/بعد
- `PHASE2_MIGRATION_GUIDE.md` - راهنمای کامل مهاجرت

---

## 🟡 اولویت متوسط (Medium Priority)

### 2. بهینه‌سازی TTL Cache

**فایل:** `plugins/youtube_handler.py`

کش فعلی با TTL 10 دقیقه کار می‌کند، اما می‌توان:
- اضافه کردن متد `extend_ttl()` برای تمدید عمر entry
- اضافه کردن `max_size` برای محدود کردن حافظه
- پشتیبانی از Redis برای production

### 3. افزایش Coverage تست‌ها

**موارد نیاز به تست:**
- Race condition در `sqlite_db_wrapper.py`
- TTL cache expiration در `youtube_handler.py`
- FFmpeg async subprocess timeout
- AdminUserState expiration (5 minutes)

### 4. مستندسازی API

**ایجاد:**
- API documentation برای handlers
- راهنمای استفاده از Cookie Manager
- توضیح معماری Admin State Management

---

## 🟢 اولویت پایین (Low Priority)

### 5. پاکسازی کدهای قدیمی

**فایل‌های موقت برای حذف:**
- `migrate_admin_step.py` (اسکریپت مهاجرت)
- `admin_step_migration_example.py` (نمونه‌های آموزشی)
- `PHASE2_INCOMPLETE_WARNING.md` (بعد از تکمیل مهاجرت)

### 6. بهبود Logging

**موارد:**
- استانداردسازی format logها
- اضافه کردن log rotation
- جداسازی logهای admin از user

### 7. Docker Optimization (Phase 3)

**موضوعات:**
- Multi-stage Dockerfile
- کاهش حجم image
- بهبود startup time

---

## 📊 پیگیری پیشرفت

### Phase 1: Security Fixes ✅ کامل
- [x] Admin IDs به environment variables
- [x] Cookie paths به isolated directory
- [x] Named volumes در Docker
- [x] RapidAPI rate limiting
- [x] instagram_cookies.txt از Git history پاک شد

### Phase 2: Critical Bugs 🔄 75% تکمیل
- [x] Race condition دیتابیس (contextvars)
- [x] FFmpeg async subprocess
- [x] TTL cache با cleanup
- [ ] **admin_step migration** (نیمه‌کاره - compatibility layer فعال)

### Phase 3: Docker & Deployment 📋 برنامه‌ریزی نشده
- [ ] Multi-stage Dockerfile
- [ ] Setup script
- [ ] Documentation

### Phase 4: Code Cleanliness 📋 برنامه‌ریزی نشده
- [ ] Cleanup temporary files
- [ ] Enhanced logging
- [ ] Error handling

---

## 🚨 هشدارهای مهم

### ⚠️ AdminStepCompatibility
```python
# این کلاس موقتی است و باید حذف شود
class AdminStepCompatibility:
    """⚠️ TEMPORARY: Remove after full migration"""
```

**چرا باید حذف شود؟**
1. فقط با یک ادمین کار می‌کند
2. باعث confusion در کد می‌شود
3. Performance overhead دارد
4. الگوی نادرست برای توسعه آینده

### ⚠️ Security Notice
بعد از پاکسازی `instagram_cookies.txt` از Git، حتماً:
- کوکی‌های Instagram را invalidate کنید (logout یا change password)
- هرگز فایل‌های cookie را commit نکنید
- از `.env` برای secrets استفاده کنید

---

## 📚 مستندات مرتبط

- `PHASE1_COMPLETE.md` - خلاصه فاز 1
- `PHASE2_SUMMARY.md` - خلاصه فاز 2
- `PHASE2_MIGRATION_GUIDE.md` - راهنمای مهاجرت admin_step
- `admin_step_migration_example.py` - نمونه‌های کد
- `SECURITY_NOTICE.md` - هشدارهای امنیتی

---

## ✅ چک‌لیست تکمیل admin_step Migration

قبل از حذف `AdminStepCompatibility`:

- [ ] تمام 145 مورد `admin_step[...]` به `state....` تبدیل شد
- [ ] تمام فیلترهای lambda به function تبدیل شدند
- [ ] هر handler شناسه `user_id` را دریافت می‌کند
- [ ] کلاس `AdminStepCompatibility` حذف شد
- [ ] `grep -c "admin_step" plugins/admin.py` خروجی `0` می‌دهد
- [ ] تست با چند ادمین همزمان انجام شد
- [ ] تست تمام عملیات admin (broadcast, sponsor, cookie, etc.)

---

**تاریخ ایجاد:** 2026-07-24  
**آخرین به‌روزرسانی:** 2026-07-24  
**وضعیت:** Phase 2 در حال انجام
