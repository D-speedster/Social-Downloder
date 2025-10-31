# 🔍 راهنمای دیباگ مشکل افزودن قفل

## 🐛 مشکل گزارش شده

وقتی ادمین `@okalef` یا شناسه عددی را برای افزودن قفل می‌فرستد، پیام "لینک پشتیبانی شده ارسال کنید" نمایش داده می‌شود.

## 🔧 تغییرات اعمال شده

### 1. لاگ‌گیری کامل اضافه شد

تمام مراحل handler حالا لاگ می‌شوند:

```python
# Filter check
[SPONSOR_FILTER] user=xxx, action=add, step=1, active=True/False

# Handler triggered
[SPONSOR_ADD] Handler triggered for user=xxx
[SPONSOR_ADD] Message text: @okalef
[SPONSOR_ADD] State: action=add, step=1

# Processing
[SPONSOR_ADD] Channel ref: @okalef
[SPONSOR_ADD] Format valid, proceeding...
[SPONSOR_ADD] Fetching chat info...
[SPONSOR_ADD] Getting chat by username: okalef
[SPONSOR_ADD] Chat info: id=-100xxx, name=xxx, username=@okalef
[SPONSOR_ADD] Checking bot admin status...
[SPONSOR_ADD] Bot status: administrator
[SPONSOR_ADD] Adding lock to system...
[SPONSOR_ADD] Lock added successfully: lock_xxx
[SPONSOR_ADD] Resetting state for user xxx
```

### 2. مکان لاگ‌ها

تمام لاگ‌ها در این فایل‌ها ذخیره می‌شوند:

```
logs/
├── bot.log              # لاگ اصلی
├── admin_main.log       # لاگ پنل ادمین
└── sponsor_system.log   # لاگ سیستم اسپانسر (اگر وجود داشته باشد)
```

## 📋 مراحل دیباگ

### مرحله 1: بررسی لاگ‌ها

```bash
# مشاهده لاگ‌های زنده
tail -f logs/bot.log | grep SPONSOR

# یا در ویندوز:
Get-Content logs/bot.log -Wait | Select-String "SPONSOR"
```

### مرحله 2: تست افزودن قفل

1. ربات را ریستارت کنید
2. وارد پنل ادمین شوید
3. **📢 تنظیم اسپانسر** → **➕ افزودن قفل جدید**
4. `@okalef` را ارسال کنید
5. لاگ‌ها را بررسی کنید

### مرحله 3: بررسی State

اگر handler فعال نشد، بررسی کنید:

```python
# در لاگ باید این خط باشد:
[SPONSOR_FILTER] user=xxx, action=add, step=1, active=True

# اگر active=False است، یعنی state درست set نشده
```

### مرحله 4: بررسی Handler Priority

```python
# Handler sponsor_add باید group=3 باشد
@Client.on_message(..., group=3)

# Handler universal باید group=10 باشد
@Client.on_message(..., group=10)
```

## 🔍 سناریوهای احتمالی

### سناریو 1: Filter فعال نمی‌شود

**علامت:**
```
[SPONSOR_FILTER] user=xxx, action=None, step=0, active=False
```

**راه‌حل:**
- بررسی کنید callback `sponsor_add` اجرا شده است
- بررسی کنید state set شده است

### سناریو 2: Handler اصلا trigger نمی‌شود

**علامت:**
- هیچ لاگی با `[SPONSOR_ADD]` وجود ندارد

**راه‌حل:**
- بررسی کنید `sponsor_admin.py` import شده است
- بررسی کنید handler ثبت شده است

### سناریو 3: Handler دیگری پیام را می‌گیرد

**علامت:**
- پیام "لینک پشتیبانی شده" نمایش داده می‌شود
- لاگ handler دیگری وجود دارد

**راه‌حل:**
- بررسی کنید group=3 است (اولویت بالا)
- بررسی کنید filter `sponsor_add_active` کار می‌کند

## 🧪 تست دستی

### تست 1: بررسی State

```python
# در کنسول Python:
from plugins.sponsor_admin import get_admin_state

user_id = 79049016  # شناسه شما
state = get_admin_state(user_id)
print(state)

# باید چیزی شبیه این باشد:
# {'action': 'add', 'step': 1, 'data': {}}
```

### تست 2: بررسی Filter

```python
# در کنسول Python:
from plugins.sponsor_admin import sponsor_add_filter, get_admin_state

# Set state
user_id = 79049016
state = get_admin_state(user_id)
state['action'] = 'add'
state['step'] = 1

# Test filter (نیاز به mock message)
# باید True برگرداند
```

### تست 3: بررسی Handler Registration

```python
# در کنسول Python:
from pyrogram import Client

# بررسی handlers
client = Client("test")
print(client.dispatcher.groups)

# باید handler sponsor_add در group 3 باشد
```

## 📊 خروجی مورد انتظار

### خروجی موفق:

```
[SPONSOR_FILTER] user=79049016, action=add, step=1, active=True
[SPONSOR_ADD] Handler triggered for user=79049016
[SPONSOR_ADD] Message text: @okalef
[SPONSOR_ADD] State: action=add, step=1
[SPONSOR_ADD] Channel ref: @okalef
[SPONSOR_ADD] Format valid, proceeding...
[SPONSOR_ADD] Fetching chat info...
[SPONSOR_ADD] Getting chat by username: okalef
[SPONSOR_ADD] Chat info: id=-1001234567890, name=OkAlef, username=@okalef
[SPONSOR_ADD] Checking bot admin status...
[SPONSOR_ADD] Bot status: administrator
[SPONSOR_ADD] Adding lock to system...
[SPONSOR_ADD] Lock added successfully: lock_1_1761912345
[SPONSOR_ADD] Resetting state for user 79049016
```

### خروجی ناموفق (مثال):

```
[SPONSOR_FILTER] user=79049016, action=None, step=0, active=False
# Handler اصلا trigger نمی‌شود
# Handler دیگری پیام را می‌گیرد
```

## 🔧 اقدامات فوری

### اگر مشکل همچنان وجود دارد:

1. **ریستارت کامل:**
   ```bash
   # توقف ربات
   Ctrl+C
   
   # پاک کردن cache Python
   rm -rf __pycache__
   rm -rf plugins/__pycache__
   
   # راه‌اندازی مجدد
   python main.py
   ```

2. **بررسی import:**
   ```python
   # در bot.py باید این خط باشد:
   import plugins.sponsor_admin
   ```

3. **بررسی فایل:**
   ```bash
   # مطمئن شوید فایل وجود دارد
   ls -la plugins/sponsor_admin.py
   ```

4. **تست مستقل:**
   ```bash
   # تست import
   python -c "from plugins.sponsor_admin import handle_sponsor_add_input; print('OK')"
   ```

## 📝 گزارش مشکل

اگر مشکل حل نشد، لطفاً این اطلاعات را ارسال کنید:

1. **لاگ کامل:**
   ```bash
   # آخرین 100 خط لاگ
   tail -n 100 logs/bot.log > debug_log.txt
   ```

2. **State فعلی:**
   ```python
   from plugins.sponsor_admin import admin_sponsor_state
   print(admin_sponsor_state)
   ```

3. **مراحل انجام شده:**
   - چه دکمه‌هایی را زدید؟
   - چه متنی را فرستادید؟
   - چه پیامی دریافت کردید؟

4. **اسکرین‌شات:**
   - از پیام خطا
   - از لاگ‌ها

## ✅ چک‌لیست نهایی

قبل از گزارش مشکل، این موارد را بررسی کنید:

- [ ] ربات ریستارت شده است
- [ ] `sponsor_admin.py` در `bot.py` import شده است
- [ ] لاگ‌ها بررسی شده‌اند
- [ ] State بعد از کلیک روی "افزودن قفل" set می‌شود
- [ ] Filter `sponsor_add_active` True برمی‌گرداند
- [ ] Handler در group=3 ثبت شده است
- [ ] هیچ handler دیگری با priority بالاتر وجود ندارد

---

**تاریخ:** 1404/08/09 - 16:30  
**نسخه:** 1.0  
**وضعیت:** آماده برای دیباگ
