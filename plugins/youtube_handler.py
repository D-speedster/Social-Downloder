"""
YouTube Handler - سیستم جدید و بهینه دانلود از یوتیوب
نسخه بازنویسی شده با ساختار ساده و کارآمد
"""

import os
import time
import asyncio
import html
import aiohttp
import tempfile
import concurrent.futures
import re
from urllib.parse import urlparse, parse_qs

from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton
)
from pyrogram.enums import ParseMode
from pyrogram.errors import MessageIdInvalid

from plugins.db_wrapper import DB
from plugins.logger_config import get_logger
from plugins.start import join  # 🔒 Import فیلتر عضویت اسپانسری
import yt_dlp

# ------------------------------------------------------------------- #
# PHASE 2 FIX: TTL Cache with background cleanup to prevent memory leaks
# کش موقت با TTL (Time To Live) و پاکسازی خودکار
import asyncio

class TTLCache:
    """
    Simple Time-To-Live cache with automatic cleanup.
    Prevents memory leaks by removing expired entries.
    """
    def __init__(self, ttl_seconds: int = 600):
        self.cache: dict[int, dict] = {}
        self.ttl = ttl_seconds
        self._cleanup_task = None
        logger.info(f"✅ TTL Cache initialized (TTL: {ttl_seconds}s)")
    
    def set(self, key: int, value: dict):
        """Set a cache entry with expiration timestamp"""
        self.cache[key] = {
            'data': value,
            'expires_at': time.time() + self.ttl
        }
    
    def get(self, key: int):
        """Get a cache entry if not expired"""
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        if time.time() > entry['expires_at']:
            # Expired - remove it
            del self.cache[key]
            return None
        
        return entry['data']
    
    def remove(self, key: int):
        """Remove a specific cache entry"""
        self.cache.pop(key, None)
    
    def cleanup_expired(self):
        """Remove all expired entries"""
        now = time.time()
        expired_keys = [
            k for k, v in self.cache.items()
            if now > v['expires_at']
        ]
        for k in expired_keys:
            del self.cache[k]
        
        if expired_keys:
            logger.info(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    async def start_cleanup_task(self, interval_seconds: int = 300):
        """Start background cleanup task"""
        async def _cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(interval_seconds)
                    count = self.cleanup_expired()
                    logger.debug(f"Background cleanup: removed {count} expired entries")
                except asyncio.CancelledError:
                    logger.info("TTL Cache cleanup task cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in cache cleanup: {e}")
        
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(_cleanup_loop())
            logger.info(f"✅ Started background cache cleanup (interval: {interval_seconds}s)")
    
    def stats(self) -> dict:
        """Get cache statistics"""
        now = time.time()
        active = sum(1 for v in self.cache.values() if now <= v['expires_at'])
        expired = len(self.cache) - active
        return {
            'total': len(self.cache),
            'active': active,
            'expired': expired
        }

# Global TTL cache instance
video_cache = TTLCache(ttl_seconds=600)  # 10 minutes TTL

# Start cleanup task when module is imported
# (will be called when bot starts)
def init_cache_cleanup():
    """Initialize cache cleanup background task"""
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(video_cache.start_cleanup_task(interval_seconds=300))
    except RuntimeError:
        # Event loop not running yet - will be started later
        pass

# Call init when module loads (if event loop exists)
try:
    init_cache_cleanup()
except Exception:
    pass

# ------------------------------------------------------------------- #
# کیفیت‌های پشتیبانی‌شده (به‌درخواست شما محدود به 4 بود)
SUPPORTED_QUALITIES = ['360', '480', '720', '1080']

# ------------------------------------------------------------------- #
# یک ThreadPoolExecutor سراسری (همانند universal_downloader)
_global_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=6,
    thread_name_prefix="yt_api_worker"
)

# ------------------------------------------------------------------- #
def normalize_youtube_url(url: str) -> str:
    """
    پاکسازی و normalize کردن URL های YouTube
    
    مثال:
    - https://www.youtube.com/watch?v=VIDEO_ID&list=...&start_radio=1
      -> https://www.youtube.com/watch?v=VIDEO_ID
    
    - https://youtu.be/VIDEO_ID?si=...
      -> https://www.youtube.com/watch?v=VIDEO_ID
    
    - https://m.youtube.com/watch?v=VIDEO_ID
      -> https://www.youtube.com/watch?v=VIDEO_ID
    """
    try:
        url = url.strip()
        
        # الگوهای مختلف YouTube
        patterns = [
            # youtu.be/VIDEO_ID
            r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
            # youtube.com/watch?v=VIDEO_ID
            r'(?:https?://)?(?:www\.)?(?:m\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
            # youtube.com/embed/VIDEO_ID
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
            # youtube.com/v/VIDEO_ID
            r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})',
        ]
        
        video_id = None
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                break
        
        if video_id:
            # URL ساده و تمیز
            clean_url = f"https://www.youtube.com/watch?v={video_id}"
            logger.info(f"Normalized URL: {url} -> {clean_url}")
            return clean_url
        
        # اگر الگو match نشد، URL اصلی رو برگردون
        logger.warning(f"Could not normalize URL: {url}")
        return url
        
    except Exception as e:
        logger.error(f"Error normalizing URL: {e}")
        return url

# ------------------------------------------------------------------- #
async def extract_video_info(url: str) -> dict | None:
    """استخراج اطلاعات ویدیو با yt‑dlp (به صورت async)"""
    try:
        cookie_file = 'cookie_youtube.txt'

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
        }

        if os.path.exists(cookie_file):
            ydl_opts['cookiefile'] = cookie_file
            logger.info(f"Using cookies from: {cookie_file}")

        # ------------------------------------------------------------------- #
        # استخراج هم‑زمان با executor سراسری
        loop = asyncio.get_running_loop()

        def _extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        info = await loop.run_in_executor(_global_executor, _extract)

        if not info:
            return None

        formats = info.get('formats', [])
        available_qualities: dict = {}

        # ------------------------------------------------------------------- #
        # بررسی کیفیت‌های درخواست‌شده
        for quality in SUPPORTED_QUALITIES:
            target_height = int(quality)

            # 1️⃣  قالب ترکیبی (video + audio در یک فایل)
            combined_formats = [
                f for f in formats
                if f.get('vcodec') != 'none'
                and f.get('acodec') != 'none'
                and f.get('height') == target_height
                and f.get('ext') in ['mp4', 'webm']
            ]

            # انعطاف‑پذیری ±10px
            if not combined_formats:
                combined_formats = [
                    f for f in formats
                    if f.get('vcodec') != 'none'
                    and f.get('acodec') != 'none'
                    and f.get('height') is not None
                    and isinstance(f.get('height'), (int, float))
                    and abs(int(f.get('height')) - target_height) <= 10
                    and f.get('ext') in ['mp4', 'webm']
                ]

            # شورت‌س (portrait) → نگاشت به landscape
            if not combined_formats:
                portrait_map = {
                    360: [640, 426, 256],
                    480: [854, 640, 426],
                    720: [1280, 854],
                    1080: [1920, 1280],
                }
                if target_height in portrait_map:
                    for ph in portrait_map[target_height]:
                        combined_formats = [
                            f for f in formats
                            if f.get('vcodec') != 'none'
                            and f.get('acodec') != 'none'
                            and f.get('height') == ph
                            and f.get('ext') in ['mp4', 'webm']
                        ]
                        if combined_formats:
                            logger.info(
                                f"Portrait format mapped: {quality}p → {ph}p"
                            )
                            break

            # ----------------------------------------------------------- #
            if combined_formats:
                combined_formats.sort(
                    key=lambda x: (x.get('fps', 0) or 0,
                                   x.get('tbr', 0) or 0),
                    reverse=True
                )
                best = combined_formats[0]
                available_qualities[quality] = {
                    'format_string': best['format_id'],
                    'filesize': best.get('filesize', 0) or 0,
                    'fps': best.get('fps', 30),
                    'ext': best.get('ext', 'mp4'),
                    'type': 'combined',
                    'actual_height': best.get('height')
                }
                logger.info(
                    f"Combined {quality}p → {best['format_id']} (h={best.get('height')})"
                )
                continue

            # 2️⃣  قالب جداگانه (video + audio)
            #   ↳ اینجا بود که در نسخهٔ قبلی متغیر `height` تعریف نشده بود
            video_formats = [
                f for f in formats
                if f.get('vcodec') != 'none'
                and f.get('acodec') == 'none'
                and f.get('height') == target_height
                and f.get('ext') in ['mp4', 'webm']
            ]

            # ±10px برای video‑only
            if not video_formats:
                video_formats = [
                    f for f in formats
                    if f.get('vcodec') != 'none'
                    and f.get('acodec') == 'none'
                    and f.get('height') is not None
                    and isinstance(f.get('height'), (int, float))
                    and abs(int(f.get('height')) - target_height) <= 10
                    and f.get('ext') in ['mp4', 'webm']
                ]

            # Portrait‑mapping برای video‑only
            if not video_formats:
                portrait_map = {
                    360: [640, 426, 256],
                    480: [854, 640, 426],
                    720: [1280, 854],
                    1080: [1920, 1280],
                }
                if target_height in portrait_map:
                    for ph in portrait_map[target_height]:
                        video_formats = [
                            f for f in formats
                            if f.get('vcodec') != 'none'
                            and f.get('acodec') == 'none'
                            and f.get('height') == ph
                            and f.get('ext') in ['mp4', 'webm']
                        ]
                        if video_formats:
                            logger.info(
                                f"Portrait video mapped: {quality}p → {ph}p"
                            )
                            break

            if not video_formats:
                # هیچ فایلی یافت نشد → به کیفیت‌های دیگر می‌رویم
                continue

            # پیدا کردن بهترین صدا برای این ویدیو
            audio_formats = [
                f for f in formats
                if f.get('acodec') != 'none'
                and f.get('vcodec') == 'none'
                and f.get('ext') in ['m4a', 'webm']
            ]

            if not audio_formats:
                # اگر صدا جداگانه نداشت، شاید در قالب ترکیبی باشد؛ پس ادامه می‌دهیم
                continue

            video_formats.sort(
                key=lambda x: (x.get('fps', 0) or 0,
                               x.get('tbr', 0) or 0),
                reverse=True
            )
            audio_formats.sort(
                key=lambda x: x.get('abr', 0) or 0,
                reverse=True
            )
            best_video = video_formats[0]
            best_audio = audio_formats[0]

            available_qualities[quality] = {
                'video_id': best_video['format_id'],
                'audio_id': best_audio['format_id'],
                'format_string': f"{best_video['format_id']}+{best_audio['format_id']}",
                'filesize': (best_video.get('filesize', 0) or 0) +
                            (best_audio.get('filesize', 0) or 0),
                'fps': best_video.get('fps', 30),
                'ext': 'mp4',
                'type': 'separate',
                'actual_height': best_video.get('height')
            }
            logger.info(
                f"Separate {quality}p → v:{best_video['format_id']} a:{best_audio['format_id']} "
                f"(h={best_video.get('height')})"
            )

        # ------------------------------------------------------------------- #
        # گزینهٔ فقط صدا
        audio_formats = [
            f for f in formats
            if f.get('acodec') != 'none' and f.get('vcodec') == 'none'
        ]

        if not audio_formats:
            audio_formats = [
                f for f in formats
                if f.get('acodec') != 'none' and f.get('ext') in ['mp4', 'webm', 'm4a']
            ]

        if audio_formats:
            audio_formats.sort(
                key=lambda x: x.get('abr', 0) or x.get('tbr', 0) or 0,
                reverse=True
            )
            best_audio = audio_formats[0]
            available_qualities['audio'] = {
                'format_string': 'bestaudio',
                'filesize': best_audio.get('filesize', 0) or 0,
                'ext': 'mp3',      # خروجی نهایی تبدیل به mp3 خواهد شد
                'type': 'audio_only'
            }
            logger.info(
                f"Audio only → {best_audio['format_id']}"
            )
        else:
            available_qualities['audio'] = {
                'format_string': 'best',
                'filesize': 0,
                'ext': 'mp3',
                'type': 'audio_only'
            }
            logger.warning("No audio formats found – falling back to 'best'")

        # ------------------------------------------------------------------- #
        logger.info(f"Total formats discovered: {len(formats)}")
        logger.info(f"Qualities available: {list(available_qualities.keys())}")

        if not any(q in available_qualities for q in SUPPORTED_QUALITIES):
            logger.warning("No video qualities matched! First 5 formats:")
            for i, fmt in enumerate(formats[:5], 1):
                logger.warning(
                    f"  {i}. id={fmt.get('format_id')} "
                    f"h={fmt.get('height')} v={fmt.get('vcodec')} a={fmt.get('acodec')} ext={fmt.get('ext')}"
                )

        return {
            'title': info.get('title', 'Unknown'),
            'duration': info.get('duration', 0),
            'thumbnail': info.get('thumbnail', ''),
            'uploader': info.get('uploader', 'Unknown'),
            'view_count': info.get('view_count', 0),
            'url': url,
            'qualities': available_qualities
        }

    except Exception as exc:
        logger.error(f"extract_video_info error: {exc}")
        return None


# ------------------------------------------------------------------- #
def format_duration(seconds: int) -> str:
    """مدت زمان را به قالب hh:mm:ss یا mm:ss تبدیل می‌کند"""
    if not seconds:
        return "نامشخص"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def format_number(num: int) -> str:
    """اعداد بزرگ (مثلاً 1 200 000) → 1.2M"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(num)


# ------------------------------------------------------------------- #
def create_quality_keyboard(qualities: dict) -> InlineKeyboardMarkup:
    """دکمه‌های کیفیت (۲ دکمه در هر ردیف)"""
    rows = []
    row = []

    for q in SUPPORTED_QUALITIES:
        if q in qualities:
            row.append(
                InlineKeyboardButton(
                    f"📹 {q}p",
                    callback_data=f"yt_dl_{q}"
                )
            )
            if len(row) == 2:
                rows.append(row)
                row = []

    if row:
        rows.append(row)

    # دکمهٔ فقط صدا
    if 'audio' in qualities:
        rows.append([
            InlineKeyboardButton(
                "🎵 فقط صدا (بهترین کیفیت)",
                callback_data="yt_dl_audio"
            )
        ])

    # دکمه لغو
    rows.append([InlineKeyboardButton("❌ لغو", callback_data="yt_cancel")])

    return InlineKeyboardMarkup(rows)


# ------------------------------------------------------------------- #
async def download_thumbnail(url: str) -> str | None:
    """بارگیری thumbnail و برگرداندن مسیر موقت"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    tmp = tempfile.NamedTemporaryFile(
                        suffix=".jpg", delete=False
                    )
                    tmp.write(data)
                    tmp.close()
                    return tmp.name
        return None
    except aiohttp.ClientError as ce:
        logger.error(f"Thumbnail download failed (client error): {ce}")
    except Exception as exc:
        logger.error(f"Thumbnail download error: {exc}")
    return None


# ------------------------------------------------------------------- #
@Client.on_message(
    filters.regex(
        r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})'
    )
    & filters.private
    & join
)
async def handle_youtube_link(client: Client, message: Message):
    """دست‌گیرهٔ اصلی برای لینک‌های YouTube"""
    start = time.time()
    user_id = message.from_user.id
    url = message.text.strip()

    logger.info(f"User {user_id} sent YouTube link: {url}")
    
    # پاکسازی و normalize کردن URL
    url = normalize_youtube_url(url)
    logger.info(f"Normalized URL: {url}")

    # ------------------------------------------------------------------- #
    # بررسی ثبت‌نام کاربر
    logger.info(f"Creating DB instance...")
    db = DB()
    logger.info(f"DB instance created, checking user registration...")
    if not db.check_user_register(user_id):
        logger.info(f"User {user_id} not registered")
        await message.reply_text(
            "⚠️ ابتدا باید ربات را استارت کنید.\n\nلطفاً دستور /start را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔄 شروع مجدد", callback_data="start")]]
            )
        )
        return

    # ------------------------------------------------------------------- #
    # ثبت درخواست در دیتابیس
    logger.info(f"Logging request to database...")
    request_id = db.log_request(user_id=user_id, platform='youtube', url=url, status='pending')
    logger.info(f"Request logged with ID: {request_id}")

    # پیام وضعیت اولیه
    logger.info(f"Sending status message to user...")
    status_msg = await message.reply_text(
        "🔄 در حال پردازش لینک یوتیوب…\n⏳ لطفاً چند لحظه صبر کنید…"
    )
    logger.info(f"Status message sent")

    try:
        # استخراج اطلاعات ویدیو
        video_info = await extract_video_info(url)

        if not video_info or not video_info.get('qualities'):
            # به‌روزرسانی وضعیت به failed
            processing_time = time.time() - start
            db.update_request_status(
                request_id=request_id,
                status='failed',
                processing_time=processing_time,
                error_message='امکان دریافت اطلاعات ویدیو وجود ندارد'
            )
            
            await status_msg.edit_text(
                "❌ **خطا در پردازش ویدیو**\n\n"
                "امکان دریافت اطلاعات ویدیو وجود ندارد.\n"
                "لطفاً موارد زیر را بررسی کنید:\n"
                "• لینک معتبر باشد\n"
                "• ویدیو عمومی باشد\n"
                "• اتصال اینترنت برقرار باشد",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # ذخیره‌سازی موقت برای مرحلهٔ انتخاب کیفیت
        video_info['request_id'] = request_id
        video_cache.set(user_id, video_info)

        # متن توصیفی
        title = video_info.get('title') or 'Unknown'
        uploader = video_info.get('uploader') or 'Unknown'
        duration = video_info.get('duration') or 0
        view_count = video_info.get('view_count') or 0
        
        info_text = (
            f"🎬 <b>{html.escape(title)}</b>\n\n"
            f"👤 <b>کانال:</b> {html.escape(uploader)}\n"
            f"⏱ <b>مدت زمان:</b> {format_duration(duration)}\n"
            f"👁 <b>بازدید:</b> {format_number(view_count)}\n\n"
            f"📋 <b>لطفاً کیفیت مورد نظر را انتخاب کنید:</b>"
        )

        # کیبورد کیفیت‌ها
        kb = create_quality_keyboard(video_info['qualities'])

        # دریافت و ارسال thumbnail (اگر موجود باشد)
        thumbnail_path = None
        if video_info.get('thumbnail'):
            thumbnail_path = await download_thumbnail(video_info['thumbnail'])

        if thumbnail_path and os.path.exists(thumbnail_path):
            # ✅ ارسال تصویر و سپس حذف پیام وضعیت
            await message.reply_photo(
                photo=thumbnail_path,
                caption=info_text,
                parse_mode=ParseMode.HTML,
                reply_markup=kb
            )
            # حذف پیام وضعیت فقط پس از موفقیت
            await status_msg.delete()
            # پاک‌سازی فایل موقت thumbnail
            try:
                os.unlink(thumbnail_path)
            except Exception:
                pass
        else:
            # اگر thumbnail موجود نیست، فقط متن را ویرایش می‌کنیم
            await status_msg.edit_text(
                text=info_text,
                parse_mode=ParseMode.HTML,
                reply_markup=kb
            )

        # به‌روزرسانی وضعیت به success (نمایش کیفیت‌ها موفق بود)
        processing_time = time.time() - start
        db.update_request_status(
            request_id=request_id,
            status='success',
            processing_time=processing_time
        )
        
        elapsed = time.time() - start
        logger.info(f"Quality selection shown in {elapsed:.2f}s برای کاربر {user_id}")

    except Exception as exc:
        # به‌روزرسانی وضعیت به failed
        processing_time = time.time() - start
        db.update_request_status(
            request_id=request_id,
            status='failed',
            processing_time=processing_time,
            error_message=str(exc)[:500]
        )
        
        logger.error(f"Error handling YouTube link (user {user_id}): {exc}")
        await status_msg.edit_text(
            f"❌ **خطا در پردازش ویدیو**\n\nخطا: {str(exc)[:150]}\n\nلطفاً دوباره تلاش کنید.",
            parse_mode=ParseMode.MARKDOWN
        )
    finally:
        # اگر به هر دلیلی پیام وضعیت باقی مانده بود، سعی می‌کنیم حذفش کنیم
        try:
            if status_msg and not status_msg.deleted:
                await status_msg.delete()
        except (MessageIdInvalid, Exception):
            pass
        # (در این handler ما هنوز دانلود نهایی را انجام نمی‌دهیم؛ این کار در
        # هندلر callbackهای quality انجام می‌شود، بنابراین در اینجا کش را
        # تمیز نمی‌کنیم؛ ولی می‌توانید با یک TTL یا پس از دانلود حذف کنید.)

# ------------------------------------------------------------------- #
# هندلر callbackهای کیفیت (اختیاری – فقط نمونه)
@Client.on_callback_query(filters.regex(r'^yt_dl_(\d+|audio)$'))
async def quality_callback(client: Client, callback_query):
    """دریافت انتخاب کیفیت و شروع دانلود (پیکره ساده)"""
    data = callback_query.data  # مثال: yt_dl_720 یا yt_dl_audio
    user_id = callback_query.from_user.id

    video_info = video_cache.get(user_id)
    if not video_info:
        await callback_query.answer(
            "⏳ اطلاعات منقضی شده. لطفاً دوباره لینک بفرستید.", show_alert=True
        )
        return

    selected = data.split('_')[-1]  # 720 یا audio

    await callback_query.answer("📥 در حال آماده‌سازی دانلود…", show_alert=False)

    # اینجا می‌توانید از `youtube_downloader` موجود در پروژه استفاده کنید:
    #   await youtube_downloader.download(url, format_string, out_name, ...)
    # برای سادگی فقط پیغام تکمیل می‌فرستیم:
    await callback_query.message.edit_caption(
        caption=f"✅ دانلود {selected}p (یا فقط صدا) شروع شد…\n\n⏳ لطفاً صبر کنید.",
        reply_markup=None
    )
    # پاک‌سازی کش (اکنون با TTL cache مدیریت می‌شود)
    video_cache.remove(user_id)


# ------------------------------------------------------------------- #
# هندلر لغو
@Client.on_callback_query(filters.regex(r'^yt_cancel$'))
async def cancel_callback(client: Client, callback_query):
    user_id = callback_query.from_user.id
    await callback_query.answer("🔴 عملیات لغو شد", show_alert=True)
    await callback_query.message.delete()
    video_cache.remove(user_id)

