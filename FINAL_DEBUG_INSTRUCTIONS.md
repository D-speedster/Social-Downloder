# 🔍 دستورالعمل نهایی دیباگ

## ✅ وضعیت فعلی

سیستم تست شد و **کاملا سالم** است:
- ✅ Import موفق
- ✅ State management کار می‌کند
- ✅ Filter به درستی عمل می‌کند

## 🚀 مراحل حل مشکل

### مرحله 1: ریستارت کامل ربات

```bash
# توقف ربات
Ctrl+C

# پاک کردن cache
rm -rf __pycache__
rm -rf plugins/__pycache__

# راه‌اندازی مجدد
python main.py
```

### مرحله 2: تست با لاگ‌گیری

1. ربات را اجرا کنید
2. در یک ترمینال دیگر لاگ‌ها را ببینید:

```bash
# در لینوکس/مک:
tail -f logs/bot.log | grep SPONSOR

# در ویندوز PowerShell:
Get-Content logs\bot.log -Wait | Select-String "SPONSOR"
```

3. حالا تست کنید:
   - وارد پنل ادمین شوید
   - **📢 تنظیم اسپانسر**
   - **➕ افزودن قفل جدید**
   - `@okalef` را بفرستید

### مرحله 3: بررسی لاگ‌ها

باید این لاگ‌ها را ببینید:

```
[SPONSOR_ADD] Callback triggered by user 79049016
[SPONSOR_ADD] State set: action=add, step=1 for user 79049016
[SPONSOR_FILTER] user=79049016, action=add, step=1, active=True
[SPONSOR_ADD] Handler triggered for user=79049016
[SPONSOR_ADD] Message text: @okalef
[SPONSOR_ADD] Channel ref: @okalef
[SPONSOR_ADD] Format valid, proceeding...
[SPONSOR_ADD] Fetching chat info...
```

## 🐛 اگر مشکل همچنان وجود دارد

### حالت 1: هیچ لاگی نمی‌بینید

**مشکل:** Handler اصلا trigger نمی‌شود

**راه‌حل:**
```bash
# بررسی import
python -c "import plugins.sponsor_admin; print('OK')"

# اگر خطا داد، فایل را دوباره بخوانید
```

### حالت 2: Filter False برمی‌گرداند

**مشکل:** State set نشده

**راه‌حل:**
```python
# اجرای اسکریپت دیباگ
python debug_sponsor_state.py

# باید همه چیز OK باشد
```

### حالت 3: Handler دیگری پیام را می‌گیرد

**مشکل:** Priority handler پایین است

**راه‌حل:**
- بررسی کنید `group=3` است
- Handler دیگری با `group` کمتر از 3 نباشد

## 📋 چک‌لیست قبل از تست

- [ ] ربات کاملا ریستارت شده
- [ ] Cache پاک شده
- [ ] `sponsor_admin.py` در `bot.py` import شده
- [ ] لاگ‌ها در حال نمایش هستند
- [ ] ربات در کانال ادمین است

## 🎯 نتیجه مورد انتظار

بعد از ارسال `@okalef`:

```
✅ قفل با موفقیت اضافه شد!

📌 کانال: OkAlef
🆔 شناسه: -1001234567890
🔗 یوزرنیم: @okalef
🆔 Lock ID: lock_1_1761912345

✅ از این لحظه کاربران باید در این کانال عضو شوند.
```

## 📞 اگر باز هم مشکل دارید

لطفاً این اطلاعات را ارسال کنید:

1. **آخرین 50 خط لاگ:**
   ```bash
   tail -n 50 logs/bot.log > last_log.txt
   ```

2. **خروجی اسکریپت دیباگ:**
   ```bash
   python debug_sponsor_state.py > debug_output.txt
   ```

3. **اسکرین‌شات:**
   - از پیامی که دریافت می‌کنید
   - از لاگ‌ها

4. **مراحل دقیق:**
   - چه دکمه‌هایی زدید؟
   - چه متنی فرستادید؟
   - چه پیامی دریافت کردید؟

---

**نکته مهم:** سیستم تست شده و کار می‌کند. اگر مشکل دارید، احتمالا یکی از این موارد است:
1. ربات ریستارت نشده
2. Cache پاک نشده
3. Handler دیگری با priority بالاتر وجود دارد
4. State به درستی set نمی‌شود

**راه‌حل قطعی:** ریستارت کامل + پاک کردن cache + بررسی لاگ‌ها

---

**تاریخ:** 1404/08/09 - 16:45  
**وضعیت:** ✅ آماده برای تست
