# Design Document - Phase 3: Platform-Specific Captions

## Overview

طراحی یک سیستم ماژولار برای ساخت caption های اختصاصی هر پلتفرم.

## Architecture

```
┌─────────────────────────────────────────┐
│     Universal Downloader                 │
├─────────────────────────────────────────┤
│                                           │
│  ┌────────────────────────────────┐     │
│  │  Caption Builder (New)         │     │
│  │  ┌──────────────────────────┐  │     │
│  │  │ Platform Formatters      │  │     │
│  │  │ - TikTok                 │  │     │
│  │  │ - Spotify                │  │     │
│  │  │ - SoundCloud             │  │     │
│  │  │ - Pinterest              │  │     │
│  │  │ - Instagram              │  │     │
│  │  │ - Default                │  │     │
│  │  └──────────────────────────┘  │     │
│  │  ┌──────────────────────────┐  │     │
│  │  │ Helper Functions         │  │     │
│  │  │ - format_duration()      │  │     │
│  │  │ - truncate_text()        │  │     │
│  │  │ - safe_get()             │  │     │
│  │  └──────────────────────────┘  │     │
│  └────────────────────────────────┘     │
│                                           │
└─────────────────────────────────────────┘
```

## Components

### 1. Caption Builder Module

**File**: `plugins/caption_builder.py` (جدید)

**Functions**:
```python
def build_caption(platform: str, data: dict) -> str:
    """ساخت caption بر اساس platform"""
    
def format_tiktok_caption(data: dict) -> str:
    """Caption TikTok"""
    
def format_spotify_caption(data: dict) -> str:
    """Caption Spotify"""
    
def format_soundcloud_caption(data: dict) -> str:
    """Caption SoundCloud"""
    
def format_pinterest_caption(data: dict) -> str:
    """Caption Pinterest"""
    
def format_instagram_caption(data: dict) -> str:
    """Caption Instagram"""
    
def format_default_caption(platform: str, data: dict) -> str:
    """Caption پیش‌فرض"""
    
# Helper functions
def format_duration(seconds: int, style: str = 'long') -> str:
    """فرمت زمان"""
    
def truncate_text(text: str, max_length: int = 100) -> str:
    """کوتاه کردن متن"""
    
def safe_get(data: dict, *keys, default='') -> str:
    """دریافت ایمن از dict"""
```

### 2. Integration با Universal Downloader

**File**: `plugins/universal_downloader.py`

**Changes**:
```python
from plugins.caption_builder import build_caption

# در handle_universal_link():
# قبل:
caption = f"🎬 {video_info['title']}"

# بعد:
caption = build_caption(platform, api_data)
```

## Implementation Details

### Caption Formats

#### TikTok:
```python
def format_tiktok_caption(data: dict) -> str:
    author = safe_get(data, 'author') or safe_get(data, 'unique_id')
    title = truncate_text(safe_get(data, 'title'), 100)
    duration = format_duration(safe_get(data, 'duration', default=0))
    
    caption = "🎬 ویدیو از TikTok\n"
    if author:
        caption += f"👤 سازنده: @{author}\n"
    if title:
        caption += f"📄 عنوان: {title}\n"
    if duration:
        caption += f"⏱️ مدت زمان: {duration}"
    
    return caption
```

#### Spotify:
```python
def format_spotify_caption(data: dict) -> str:
    title = safe_get(data, 'title')
    artist = safe_get(data, 'artist') or safe_get(data, 'author')
    duration = format_duration(safe_get(data, 'duration', default=0), style='short')
    
    caption = "🎵 آهنگ از Spotify\n"
    if title:
        caption += f"🎧 نام آهنگ: {title}\n"
    if artist:
        caption += f"👤 هنرمند: {artist}\n"
    if duration:
        caption += f"⏱️ مدت زمان: {duration}"
    
    return caption
```

#### Instagram:
```python
def format_instagram_caption(data: dict) -> str:
    username = safe_get(data, 'owner', 'username')
    title = truncate_text(safe_get(data, 'title'), 150)
    likes = safe_get(data, 'like_count', default=0)
    location = safe_get(data, 'location', 'name')
    resolution = safe_get(data, 'resolution')
    media_type = safe_get(data, 'type', default='image')
    
    caption = "📸 پست از Instagram\n"
    if username:
        caption += f"👤 پیج: @{username}\n"
    if title:
        caption += f"📝 توضیح: {title}\n"
    if likes and likes > 0:
        caption += f"❤️ لایک‌ها: {likes:,}\n"
    if location:
        caption += f"📍 موقعیت: {location}\n"
    if resolution:
        emoji = "🎞" if media_type == "video" else "📏"
        label = "کیفیت ویدیو" if media_type == "video" else "کیفیت تصویر"
        caption += f"{emoji} {label}: {resolution}"
    
    return caption
```

### Helper Functions

#### format_duration:
```python
def format_duration(seconds: int, style: str = 'long') -> str:
    """
    فرمت زمان
    
    Args:
        seconds: تعداد ثانیه
        style: 'long' یا 'short'
    
    Returns:
        str: زمان فرمت شده
    """
    if not seconds or seconds <= 0:
        return ""
    
    if style == 'short':
        # برای Spotify/SoundCloud: "3:45" یا "1:23:45"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
    
    else:
        # برای TikTok: "1 دقیقه و 28 ثانیه"
        if seconds < 60:
            return f"{seconds} ثانیه"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            if secs > 0:
                return f"{minutes} دقیقه و {secs} ثانیه"
            else:
                return f"{minutes} دقیقه"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes > 0:
                return f"{hours} ساعت و {minutes} دقیقه"
            else:
                return f"{hours} ساعت"
```

## Testing Strategy

### Unit Tests
- تست هر formatter با data نمونه
- تست helper functions
- تست با فیلدهای خالی

### Integration Tests
- تست با universal_downloader
- تست با API response واقعی

---

**تاریخ ایجاد**: 28 اکتبر 2025  
**نسخه**: 1.0  
**وضعیت**: آماده برای پیاده‌سازی