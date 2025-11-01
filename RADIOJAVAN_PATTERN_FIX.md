# 🔧 رفع مشکل Pattern رادیو جوان

## تاریخ: 2025-11-01
## وضعیت: ✅ رفع شد

---

## مشکل اصلی
لینک `https://play.radiojavan.com/song/sijal-baz-mirim-baham-(ft-sami-low)` match نمی‌شد!

## علت
Pattern فقط `[\w\-]+` را می‌پذیرفت که شامل پرانتز `()` نمی‌شود.

## تست
```python
URL: https://play.radiojavan.com/song/sijal-baz-mirim-baham-(ft-sami-low)
Match: False  ❌
```

## تصحیح

### قبل:
```python
RADIOJAVAN_REGEX = re.compile(
    r'^(?:https?://)?(?:www\.)?(?:play\.)?radiojavan\.com/(?:song|podcast|video)/[\w\-]+/?$',
    re.IGNORECASE
)
```

### بعد:
```python
RADIOJAVAN_REGEX = re.compile(
    r'^(?:https?://)?(?:www\.)?(?:play\.)?radiojavan\.com/(?:song|podcast|video)/[\w\-\(\)]+/?$',
    re.IGNORECASE
)
```

**تغییر**: اضافه شدن `\(\)` به pattern برای پشتیبانی از پرانتز

## نتیجه تست

```python
URL: https://play.radiojavan.com/song/sijal-baz-mirim-baham-(ft-sami-low)
Match: True  ✅
Matched: https://play.radiojavan.com/song/sijal-baz-mirim-baham-(ft-sami-low)
```

## فایل‌های تغییر یافته
- `plugins/radiojavan_handler.py` - Pattern تصحیح شد
- `plugins/start.py` - Pattern تصحیح شد

## ⚠️ نیاز به Restart

**حتماً ربات را restart کنید:**

```bash
Ctrl+C
python bot.py
```

## تست نهایی

بعد از restart، لینک زیر را ارسال کنید:
```
https://play.radiojavan.com/song/sijal-baz-mirim-baham-(ft-sami-low)
```

باید ببینید:
```
🎵 در حال پردازش...
⏳ لطفاً صبر کنید، در حال دریافت اطلاعات آهنگ از رادیو جوان...
```

## خلاصه
✅ Pattern تصحیح شد
✅ پرانتز پشتیبانی می‌شود
⚠️ **نیاز به restart دارد**

بعد از restart، همه چیز باید کار کند! 🎵
