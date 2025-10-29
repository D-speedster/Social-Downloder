"""
Caption Builder - ساخت caption های اختصاصی برای هر پلتفرم

این ماژول caption های زیبا و مناسب برای هر شبکه اجتماعی می‌سازد.
"""

from typing import Dict, Any, Optional


def safe_get(data: dict, *keys, default: Any = '') -> Any:
    """
    دریافت ایمن مقدار از dictionary تو در تو
    
    Args:
        data: dictionary اصلی
        *keys: کلیدهای تو در تو
        default: مقدار پیش‌فرض
    
    Returns:
        مقدار یافت شده یا default
    
    Example:
        safe_get(data, 'owner', 'username', default='Unknown')
    """
    try:
        result = data
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key)
            else:
                return default
            
            if result is None:
                return default
        
        return result if result else default
    except Exception:
        return default


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    کوتاه کردن متن با اضافه کردن ...
    
    Args:
        text: متن اصلی
        max_length: حداکثر طول
    
    Returns:
        متن کوتاه شده
    """
    if not text:
        return ""
    
    text = str(text).strip()
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."


def format_duration(seconds: int, style: str = 'long') -> str:
    """
    فرمت کردن مدت زمان
    
    Args:
        seconds: تعداد ثانیه
        style: 'long' (فارسی) یا 'short' (M:SS)
    
    Returns:
        زمان فرمت شده
    
    Examples:
        format_duration(88, 'long') -> "1 دقیقه و 28 ثانیه"
        format_duration(212, 'short') -> "3:32"
    """
    try:
        seconds = int(seconds) if seconds else 0
    except (ValueError, TypeError):
        return ""
    
    if seconds <= 0:
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


def format_tiktok_caption(data: dict) -> str:
    """
    ساخت caption برای TikTok
    
    Format:
        🎬 ویدیو از TikTok
        👤 سازنده: username
        📄 عنوان: title
        ⏱️ مدت زمان: X دقیقه و Y ثانیه
    """
    author = safe_get(data, 'author') or safe_get(data, 'unique_id')
    title = truncate_text(safe_get(data, 'title'), 100)
    
    # TikTok duration معمولاً به میلی‌ثانیه است، تبدیل به ثانیه
    duration_raw = safe_get(data, 'duration', default=0)
    try:
        duration_raw = int(duration_raw) if duration_raw else 0
        # اگر بیش از 10000 بود، احتمالاً میلی‌ثانیه است
        if duration_raw > 10000:
            duration_sec = duration_raw // 1000
        else:
            duration_sec = duration_raw
    except (ValueError, TypeError):
        duration_sec = 0
    
    duration = format_duration(duration_sec, style='long')
    
    caption = "🎬 ویدیو از TikTok\n"
    
    if author:
        caption += f"👤 سازنده: {author}\n"
    
    if title:
        caption += f"📄 عنوان: {title}\n"
    
    if duration:
        caption += f"⏱️ مدت زمان: {duration}"
    
    return caption.strip()


def format_spotify_caption(data: dict) -> str:
    """
    ساخت caption برای Spotify
    
    Format:
        🎵 آهنگ از Spotify
        🎧 نام آهنگ: title
        👤 هنرمند: artist
        ⏱️ مدت زمان: M:SS
    """
    title = safe_get(data, 'title')
    
    # استخراج artist از URL
    artist = safe_get(data, 'artist')
    
    # اگر artist نبود، از medias URL استخراج کن
    if not artist and data.get('medias'):
        try:
            media_url = data['medias'][0].get('url', '')
            if 'artist=' in media_url:
                import urllib.parse
                artist_encoded = media_url.split('artist=')[1].split('&')[0]
                artist = urllib.parse.unquote(artist_encoded)
        except Exception:
            pass
    
    # اگر هنوز نبود، از author استفاده کن
    if not artist:
        artist = safe_get(data, 'author')
    
    # duration در Spotify به فرمت "M:SS" است
    duration_str = safe_get(data, 'duration')
    
    # اگر duration به فرمت string بود، استفاده کن
    # اگر number بود، تبدیل کن
    if duration_str:
        if isinstance(duration_str, str) and ':' in duration_str:
            duration = duration_str
        else:
            try:
                duration_sec = int(duration_str) if duration_str else 0
                duration = format_duration(duration_sec, style='short')
            except (ValueError, TypeError):
                duration = ""
    else:
        duration = ""
    
    caption = "🎵 آهنگ از Spotify\n"
    
    if title:
        caption += f"🎧 نام آهنگ: {title}\n"
    
    if artist:
        caption += f"👤 هنرمند: {artist}\n"
    
    if duration:
        caption += f"⏱️ مدت زمان: {duration}"
    
    return caption.strip()


def format_soundcloud_caption(data: dict) -> str:
    """
    ساخت caption برای SoundCloud
    
    Format:
        🎧 SoundCloud
        🎵 نام قطعه: title
        🎤 هنرمند: author
        ⏱ مدت: M:SS
    """
    title = safe_get(data, 'title')
    author = safe_get(data, 'author')
    duration_sec = safe_get(data, 'duration', default=0)
    duration = format_duration(duration_sec, style='short')
    
    caption = "🎧 SoundCloud\n\n"
    
    if title:
        caption += f"🎵 {title}\n"
    
    if author:
        caption += f"🎤 {author}\n"
    
    if duration:
        caption += f"⏱ {duration}"
    
    return caption.strip()


def format_pinterest_caption(data: dict) -> str:
    """
    ساخت caption برای Pinterest
    
    Format:
        🖼 تصویر از Pinterest
        👤 منتشرکننده: author
        📏 ابعاد تصویر: WxH
    """
    author = safe_get(data, 'author')
    resolution = safe_get(data, 'resolution')
    
    caption = "🖼 تصویر از Pinterest\n"
    
    if author:
        caption += f"👤 منتشرکننده: {author}\n"
    
    if resolution:
        caption += f"📏 ابعاد تصویر: {resolution}"
    
    return caption.strip()


def format_instagram_caption(data: dict) -> str:
    """
    ساخت caption برای Instagram
    
    Format:
        📸 پست از Instagram
        👤 پیج: @username
        📝 توضیح: caption
        ❤️ لایک‌ها: count
        📍 موقعیت: location
        🎞 کیفیت ویدیو: WxH (برای ویدیو)
        📏 کیفیت تصویر: WxH (برای عکس)
    """
    username = safe_get(data, 'owner', 'username')
    title = truncate_text(safe_get(data, 'title'), 150)
    likes = safe_get(data, 'like_count', default=0)
    resolution = safe_get(data, 'resolution')
    media_type = safe_get(data, 'type', default='image')
    
    caption = "📸 پست از Instagram\n"
    
    if username:
        caption += f"👤 پیج: {username}\n"
    
    if title:
        caption += f"📝 توضیح: {title}\n"
    
    # فقط اگر لایک بیش از 0 بود
    try:
        likes_int = int(likes) if likes else 0
        if likes_int > 0:
            caption += f"❤️ لایک‌ها: {likes_int:,}\n"
    except (ValueError, TypeError):
        pass
    
    if resolution:
        # تشخیص نوع محتوا
        if media_type == "video":
            caption += f"🎞 کیفیت ویدیو: {resolution}"
        else:
            caption += f"📏 کیفیت تصویر: {resolution}"
    
    return caption.strip()


def format_default_caption(platform: str, data: dict) -> str:
    """
    ساخت caption پیش‌فرض برای سایر پلتفرم‌ها
    
    Format:
        🔗 محتوا از [Platform]
        📄 عنوان: title
        👤 سازنده: author
    """
    title = truncate_text(safe_get(data, 'title'), 100)
    author = safe_get(data, 'author')
    
    caption = f"🔗 محتوا از {platform}\n"
    
    if title:
        caption += f"📄 عنوان: {title}\n"
    
    if author:
        caption += f"👤 سازنده: {author}"
    
    return caption.strip()


def build_caption(platform: str, data: dict) -> str:
    """
    ساخت caption بر اساس platform
    
    Args:
        platform: نام پلتفرم (TikTok, Spotify, Instagram, etc.)
        data: اطلاعات دریافتی از API
    
    Returns:
        caption فرمت شده
    
    Example:
        caption = build_caption("TikTok", api_response)
    """
    if not data:
        return f"📥 محتوا از {platform}"
    
    platform_lower = platform.lower()
    
    # انتخاب formatter مناسب
    if platform_lower == "tiktok":
        return format_tiktok_caption(data)
    
    elif platform_lower == "spotify":
        return format_spotify_caption(data)
    
    elif platform_lower == "soundcloud":
        return format_soundcloud_caption(data)
    
    elif platform_lower == "pinterest":
        return format_pinterest_caption(data)
    
    elif platform_lower == "instagram":
        return format_instagram_caption(data)
    
    else:
        # پلتفرم‌های دیگر: Twitter, Facebook, Reddit, etc.
        return format_default_caption(platform, data)
