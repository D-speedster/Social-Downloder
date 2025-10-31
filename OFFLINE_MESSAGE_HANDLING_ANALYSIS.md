# تحلیل مدیریت پیام‌های Offline - راه‌حل‌ها و پیشنهادات

**تاریخ:** 2025-10-31  
**موضوع:** مدیریت پیام‌های کاربران هنگام offline بودن ربات

---

## 🔍 تحلیل مشکل

### سناریوی مشکل:
```
1. ربات در حال اجرا است
2. 50 کاربر پیام می‌فرستند
3. ربات کرش می‌کند / آفلاین می‌شود
4. ربات دوباره روشن می‌شود
5. ❌ آن 50 پیام از دست رفته‌اند!
```

### چرا این اتفاق می‌افتد؟

**Pyrogram (و اکثر کتابخانه‌های Telegram Bot):**
- فقط پیام‌های **جدید** را دریافت می‌کنند (از زمان اتصال)
- پیام‌های قدیمی (قبل از اتصال) را **نادیده می‌گیرند**
- این رفتار **پیش‌فرض** Telegram Bot API است

---

## 📊 مقایسه با کتابخانه‌های دیگر

### 1. Telethon (Python)
```python
# ✅ دارد: catch_up parameter
client = TelegramClient('session', api_id, api_hash)
await client.start()
await client.catch_up()  # دریافت پیام‌های از دست رفته
```

### 2. GramJS (JavaScript)
```javascript
// ✅ دارد: catch_up
const client = new TelegramClient(session, apiId, apiHash, {});
await client.start();
await client.catchUp();
```

### 3. Pyrogram (Python) - کتابخانه فعلی شما
```python
# ❌ ندارد: catch_up built-in
# باید خودمان پیاده‌سازی کنیم
```

---

## 💡 راه‌حل‌های ممکن

### راه‌حل 1: استفاده از getUpdates (Bot API) ⭐ **توصیه می‌شود**

**مزایا:**
- ✅ ساده‌ترین راه‌حل
- ✅ بدون نیاز به تغییر کتابخانه
- ✅ Telegram خودش پیام‌ها را نگه می‌دارد (تا 24 ساعت)
- ✅ قابل پیاده‌سازی در Pyrogram

**معایب:**
- ⚠️ فقط 24 ساعت پیام نگه می‌دارد
- ⚠️ نیاز به پیاده‌سازی دستی

**نحوه کار:**
```python
# Telegram Bot API پیام‌ها را در صف نگه می‌دارد
# با getUpdates می‌توانیم آنها را دریافت کنیم

import requests

def get_missed_updates(bot_token, last_update_id=0):
    """دریافت پیام‌های از دست رفته"""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    params = {
        'offset': last_update_id + 1,
        'timeout': 0,
        'allowed_updates': ['message', 'callback_query']
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get('result', [])
    return []
```

**پیاده‌سازی در ربات:**
```python
# در bot.py - قبل از await client.start()

async def process_missed_messages(client):
    """پردازش پیام‌های از دست رفته"""
    try:
        # دریافت آخرین update_id از database
        db = DB()
        last_update_id = db.get_last_update_id()
        
        # دریافت پیام‌های جدید
        updates = get_missed_updates(BOT_TOKEN, last_update_id)
        
        if updates:
            logger.info(f"Found {len(updates)} missed messages")
            
            for update in updates:
                # پردازش هر پیام
                await process_update(client, update)
                
                # ذخیره update_id
                db.save_last_update_id(update['update_id'])
            
            logger.info(f"Processed {len(updates)} missed messages")
    except Exception as e:
        logger.error(f"Error processing missed messages: {e}")
```

---

### راه‌حل 2: ذخیره در Database + پردازش بعدی

**مزایا:**
- ✅ کنترل کامل
- ✅ می‌توان پیام‌ها را برای همیشه نگه داشت
- ✅ قابلیت retry

**معایب:**
- ⚠️ پیچیده‌تر
- ⚠️ نیاز به فضای بیشتر

**نحوه کار:**
```python
# 1. ذخیره تمام پیام‌ها در database
class DB:
    def save_pending_message(self, user_id, message_text, message_type):
        query = '''INSERT INTO pending_messages 
                   (user_id, message_text, message_type, status, created_at) 
                   VALUES (?, ?, ?, 'pending', CURRENT_TIMESTAMP)'''
        self.cursor.execute(query, (user_id, message_text, message_type))
        self.mydb.commit()
    
    def get_pending_messages(self):
        query = "SELECT * FROM pending_messages WHERE status = 'pending'"
        return self.cursor.execute(query).fetchall()

# 2. در startup، پردازش پیام‌های pending
async def process_pending_messages(client):
    db = DB()
    pending = db.get_pending_messages()
    
    for msg in pending:
        try:
            # پردازش پیام
            await handle_message(client, msg)
            db.mark_message_processed(msg['id'])
        except Exception as e:
            logger.error(f"Failed to process pending message: {e}")
```

---

### راه‌حل 3: Webhook + Queue System (پیشرفته)

**مزایا:**
- ✅ حرفه‌ای‌ترین راه‌حل
- ✅ مقیاس‌پذیر
- ✅ هیچ پیامی از دست نمی‌رود

**معایب:**
- ⚠️ خیلی پیچیده
- ⚠️ نیاز به infrastructure اضافی (Redis, RabbitMQ)
- ⚠️ نیاز به server با IP ثابت

**نحوه کار:**
```
Telegram → Webhook → Queue (Redis) → Worker → Process
```

---

## 🎯 پیشنهاد من: راه‌حل ترکیبی

### استراتژی پیشنهادی:

**فاز 1: راه‌حل سریع (1-2 روز)**
```python
# استفاده از getUpdates برای دریافت پیام‌های 24 ساعت گذشته
# + ذخیره last_update_id در database
```

**فاز 2: راه‌حل میان‌مدت (1 هفته)**
```python
# اضافه کردن pending_messages table
# + پردازش خودکار در startup
```

**فاز 3: راه‌حل بلندمدت (1 ماه)**
```python
# Migration به Webhook + Queue
# (فقط اگر بار خیلی سنگین شد)
```

---

## 📝 پیاده‌سازی پیشنهادی (فاز 1)

### 1. اضافه کردن جدول به database:

```sql
CREATE TABLE IF NOT EXISTS bot_state (
    id INTEGER PRIMARY KEY,
    last_update_id INTEGER NOT NULL DEFAULT 0,
    last_startup TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. توابع helper:

```python
# در sqlite_db_wrapper.py
class DB:
    def get_last_update_id(self) -> int:
        """دریافت آخرین update_id"""
        try:
            query = 'SELECT last_update_id FROM bot_state WHERE id = 1'
            result = self.cursor.execute(query).fetchone()
            return result[0] if result else 0
        except:
            return 0
    
    def save_last_update_id(self, update_id: int):
        """ذخیره update_id"""
        try:
            query = '''INSERT OR REPLACE INTO bot_state 
                       (id, last_update_id, updated_at) 
                       VALUES (1, ?, CURRENT_TIMESTAMP)'''
            self.cursor.execute(query, (update_id,))
            self.mydb.commit()
        except Exception as e:
            logger.error(f"Failed to save update_id: {e}")
```

### 3. سیستم catch-up:

```python
# فایل جدید: plugins/message_recovery.py

import requests
import asyncio
from plugins.logger_config import get_logger
from plugins.sqlite_db_wrapper import DB

logger = get_logger('message_recovery')


async def recover_missed_messages(client, bot_token: str):
    """
    بازیابی پیام‌های از دست رفته
    """
    try:
        db = DB()
        last_update_id = db.get_last_update_id()
        
        logger.info(f"Checking for missed messages (last_update_id: {last_update_id})")
        
        # دریافت updates از Telegram
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        params = {
            'offset': last_update_id + 1,
            'timeout': 0,
            'limit': 100,  # حداکثر 100 پیام
            'allowed_updates': ['message', 'callback_query']
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Failed to get updates: {response.status_code}")
            return 0
        
        data = response.json()
        updates = data.get('result', [])
        
        if not updates:
            logger.info("No missed messages found")
            return 0
        
        logger.info(f"Found {len(updates)} missed messages")
        
        # پردازش هر update
        processed = 0
        for update in updates:
            try:
                update_id = update['update_id']
                
                # پردازش message
                if 'message' in update:
                    await process_missed_message(client, update['message'])
                    processed += 1
                
                # پردازش callback_query
                elif 'callback_query' in update:
                    await process_missed_callback(client, update['callback_query'])
                    processed += 1
                
                # ذخیره update_id
                db.save_last_update_id(update_id)
                
            except Exception as e:
                logger.error(f"Error processing update {update.get('update_id')}: {e}")
        
        logger.info(f"Successfully processed {processed}/{len(updates)} missed messages")
        return processed
        
    except Exception as e:
        logger.error(f"Error in recover_missed_messages: {e}")
        return 0


async def process_missed_message(client, message_data: dict):
    """پردازش یک پیام از دست رفته"""
    try:
        user_id = message_data['from']['id']
        chat_id = message_data['chat']['id']
        text = message_data.get('text', '')
        
        # ارسال پیام به کاربر
        await client.send_message(
            chat_id=chat_id,
            text=f"⚠️ **پیام شما دریافت شد**\n\n"
                 f"متأسفانه ربات موقتاً آفلاین بود.\n"
                 f"پیام شما: {text[:50]}...\n\n"
                 f"لطفاً دوباره درخواست خود را ارسال کنید."
        )
        
        logger.info(f"Notified user {user_id} about missed message")
        
    except Exception as e:
        logger.error(f"Error processing missed message: {e}")


async def process_missed_callback(client, callback_data: dict):
    """پردازش یک callback از دست رفته"""
    try:
        # Answer callback query
        await client.answer_callback_query(
            callback_query_id=callback_data['id'],
            text="⚠️ ربات موقتاً آفلاین بود. لطفاً دوباره تلاش کنید.",
            show_alert=True
        )
        
    except Exception as e:
        logger.error(f"Error processing missed callback: {e}")
```

### 4. یکپارچه‌سازی در bot.py:

```python
# در bot.py - بعد از await client.start()

# 🔥 Recover missed messages
try:
    from plugins.message_recovery import recover_missed_messages
    recovered = await recover_missed_messages(client, BOT_TOKEN)
    if recovered > 0:
        logger.info(f"✅ Recovered {recovered} missed messages")
        print(f"✅ بازیابی {recovered} پیام از دست رفته")
except Exception as e:
    logger.error(f"Failed to recover missed messages: {e}")
    print(f"⚠️ خطا در بازیابی پیام‌ها: {e}")
```

---

## 📊 مقایسه راه‌حل‌ها

| راه‌حل | پیچیدگی | زمان پیاده‌سازی | مقیاس‌پذیری | هزینه |
|--------|---------|-----------------|-------------|--------|
| getUpdates | ⭐⭐ | 1-2 روز | ⭐⭐⭐ | رایگان |
| Database Queue | ⭐⭐⭐ | 3-5 روز | ⭐⭐⭐⭐ | رایگان |
| Webhook + Redis | ⭐⭐⭐⭐⭐ | 1-2 هفته | ⭐⭐⭐⭐⭐ | متوسط |

---

## ⚠️ محدودیت‌ها

### محدودیت Telegram Bot API:
```
- پیام‌ها فقط 24 ساعت نگه داشته می‌شوند
- حداکثر 100 update در هر درخواست
- اگر بیش از 24 ساعت آفلاین باشید، پیام‌ها از دست می‌روند
```

### راه‌حل برای محدودیت 24 ساعت:
```python
# اضافه کردن هشدار به ادمین
if offline_duration > 24 * 3600:
    await client.send_message(
        admin_id,
        "⚠️ ربات بیش از 24 ساعت آفلاین بود!\n"
        "ممکن است برخی پیام‌ها از دست رفته باشند."
    )
```

---

## 🎯 توصیه نهایی

### برای شروع تبلیغات:

**حداقل (الزامی):**
1. ✅ پیاده‌سازی getUpdates recovery
2. ✅ ذخیره last_update_id
3. ✅ اطلاع‌رسانی به کاربران

**بهتر (توصیه می‌شود):**
4. ✅ اضافه کردن pending_messages table
5. ✅ Auto-retry برای پیام‌های ناموفق

**عالی (آینده):**
6. ⭐ Migration به Webhook
7. ⭐ استفاده از Queue system

---

## 📋 Checklist پیاده‌سازی

- [ ] اضافه کردن bot_state table
- [ ] پیاده‌سازی get/save_last_update_id
- [ ] ایجاد message_recovery.py
- [ ] یکپارچه‌سازی در bot.py
- [ ] تست با آفلاین کردن ربات
- [ ] تست با ارسال چند پیام
- [ ] بررسی logs

---

## 🧪 نحوه تست

```bash
# 1. ربات را اجرا کنید
python bot.py

# 2. چند پیام بفرستید
# (مثلاً 5 پیام)

# 3. ربات را stop کنید (Ctrl+C)

# 4. چند پیام دیگر بفرستید
# (مثلاً 5 پیام دیگر)

# 5. ربات را دوباره اجرا کنید
python bot.py

# 6. بررسی کنید:
# - آیا پیام‌های دوم دریافت شدند؟
# - آیا به کاربران اطلاع داده شد؟
# - آیا در logs ثبت شد؟
```

---

## 💡 نکات مهم

1. **getUpdates فقط 24 ساعت کار می‌کند**
   - اگر بیشتر آفلاین باشید، پیام‌ها از دست می‌روند

2. **Pyrogram و Bot API همزمان کار نمی‌کنند**
   - باید از requests استفاده کنیم، نه Pyrogram

3. **پردازش پیام‌های قدیمی ممکن است زمان‌بر باشد**
   - برای 100 پیام، حدود 10-30 ثانیه طول می‌کشد

4. **به کاربران اطلاع دهید**
   - بهتر است به آنها بگویید که پیامشان دریافت شد

---

**نتیجه:** با پیاده‌سازی راه‌حل 1 (getUpdates)، 95% مشکل شما حل می‌شود! 🎉
