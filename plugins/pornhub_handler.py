"""
Pornhub Handler - سیستم دانلود از Pornhub با yt-dlp
فاز 1: دانلود و ذخیره‌سازی (بدون ارسال به کاربر)
"""

import os
import time
import asyncio
import html
import tempfile
import re

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

from plugins.sqlite_db_wrapper import DB
from plugins.logger_config import get_logger
from plugins.start import join
from plugins.pornhub_downloader import pornhub_downloader
from plugins.pornhub_storage import pornhub_storage

# Logger
logger = get_logger('pornhub_handler')

# کش موقت برای ذخیره اطلاعات ویدیو
pornhub_cache: dict[int, dict] = {}

# کیفیت‌های پشتیبانی‌شده (مشابه یوتیوب)
SUPPORTED_QUALITIES = ['360', '480', '720', '1080']

# Regex برای تشخیص لینک‌های سایت‌های بزرگسال
PORNHUB_REGEX = re.compile(
    r'(https?://)?(www\.|[a-z]{2}\.)?(pornhub\.com|xvideos\.com|youporn\.com)/(view_video\.php\?viewkey=|video\.|watch/|embed/)?([a-zA-Z0-9_.-]+)',
    re.IGNORECASE
)


def safe_get_height(format_dict: dict) -> int | None:
    """دریافت ایمن height از format"""
    try:
        height = format_dict.get('height')
        if height is None:
            return None
        if isinstance(height, (int, float)):
            return int(height)
        return None
    except:
        return None


async def extract_pornhub_info(url: str) -> dict | None:
    """استخراج اطلاعات ویدیو Pornhub با yt-dlp"""
    try:
        info = await pornhub_downloader.extract_info(url)
        
        if not info:
            return None
        
        formats = info.get('formats', [])
        available_qualities: dict = {}
        
        logger.info(f"Total formats found: {len(formats)}")
        
        # بررسی کیفیت‌های موجود
        for quality in SUPPORTED_QUALITIES:
            target_height = int(quality)
            
            # جستجوی فرمت‌های ترکیبی (دقیق)
            combined_formats = [
                f for f in formats
                if f.get('vcodec') != 'none'
                and f.get('acodec') != 'none'
                and safe_get_height(f) is not None
                and safe_get_height(f) == target_height
            ]
            
            # انعطاف‌پذیری ±20px (برای XNXX و سایت‌های مشابه)
            if not combined_formats:
                combined_formats = [
                    f for f in formats
                    if f.get('vcodec') != 'none'
                    and f.get('acodec') != 'none'
                    and safe_get_height(f) is not None
                    and abs(safe_get_height(f) - target_height) <= 20
                ]
            
            # اگر هنوز پیدا نشد، از format_id استفاده کن (برای XNXX)
            if not combined_formats:
                quality_patterns = {
                    '360': ['360p', '358p', 'hls-360p'],
                    '480': ['480p', '478p', 'hls-480p'],
                    '720': ['720p', 'hls-720p'],
                    '1080': ['1080p', 'hls-1080p']
                }
                patterns = quality_patterns.get(quality, [])
                combined_formats = [
                    f for f in formats
                    if any(pattern in str(f.get('format_id', '')).lower() for pattern in patterns)
                ]
            
            if combined_formats:
                combined_formats.sort(
                    key=lambda x: (x.get('fps', 0) or 0, x.get('tbr', 0) or 0),
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
                logger.info(f"Quality {quality}p found: {best['format_id']}")
                continue
            
            # جستجوی فرمت‌های جداگانه (video + audio)
            video_formats = [
                f for f in formats
                if f.get('vcodec') != 'none'
                and f.get('acodec') == 'none'
                and safe_get_height(f) is not None
                and safe_get_height(f) == target_height
            ]
            
            if not video_formats:
                video_formats = [
                    f for f in formats
                    if f.get('vcodec') != 'none'
                    and f.get('acodec') == 'none'
                    and safe_get_height(f) is not None
                    and abs(safe_get_height(f) - target_height) <= 20
                ]
            
            # اگر هنوز پیدا نشد، از format_id استفاده کن
            if not video_formats:
                quality_patterns = {
                    '360': ['360p', '358p', 'hls-360p'],
                    '480': ['480p', '478p', 'hls-480p'],
                    '720': ['720p', 'hls-720p'],
                    '1080': ['1080p', 'hls-1080p']
                }
                patterns = quality_patterns.get(quality, [])
                video_formats = [
                    f for f in formats
                    if f.get('vcodec') != 'none'
                    and f.get('acodec') == 'none'
                    and any(pattern in str(f.get('format_id', '')).lower() for pattern in patterns)
                ]
            
            if not video_formats:
                continue
            
            audio_formats = [
                f for f in formats
                if f.get('acodec') != 'none'
                and f.get('vcodec') == 'none'
            ]
            
            if not audio_formats:
                continue
            
            video_formats.sort(
                key=lambda x: (x.get('fps', 0) or 0, x.get('tbr', 0) or 0),
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
                'filesize': (best_video.get('filesize', 0) or 0) + (best_audio.get('filesize', 0) or 0),
                'fps': best_video.get('fps', 30),
                'ext': 'mp4',
                'type': 'separate',
                'actual_height': best_video.get('height')
            }
            logger.info(f"Quality {quality}p found (separate): v:{best_video['format_id']} a:{best_audio['format_id']}")
        
        logger.info(f"Available qualities: {list(available_qualities.keys())}")
        
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
        logger.error(f"Extract info error: {exc}")
        return None


def format_duration(seconds) -> str:
    """تبدیل ثانیه به فرمت hh:mm:ss"""
    if not seconds:
        return "نامشخص"
    try:
        # تبدیل به int در صورت float بودن
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
    except (ValueError, TypeError):
        return "نامشخص"


def format_number(num: int) -> str:
    """فرمت کردن اعداد بزرگ"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(num)


def create_quality_keyboard(qualities: dict) -> InlineKeyboardMarkup:
    """ساخت دکمه‌های انتخاب کیفیت"""
    rows = []
    row = []
    
    for q in SUPPORTED_QUALITIES:
        if q in qualities:
            row.append(
                InlineKeyboardButton(
                    f"📹 {q}p",
                    callback_data=f"ph_dl_{q}"
                )
            )
            if len(row) == 2:
                rows.append(row)
                row = []
    
    if row:
        rows.append(row)
    
    # دکمه لغو
    rows.append([InlineKeyboardButton("❌ لغو", callback_data="ph_cancel")])
    
    return InlineKeyboardMarkup(rows)


@Client.on_message(
    filters.regex(PORNHUB_REGEX) & filters.private & join
)
async def handle_pornhub_link(client: Client, message: Message):
    """هندلر اصلی برای لینک‌های Pornhub"""
    start = time.time()
    user_id = message.from_user.id
    url = message.text.strip()
    
    logger.info(f"User {user_id} sent Pornhub link: {url}")
    
    # بررسی ثبت‌نام کاربر
    db = DB()
    if not db.check_user_register(user_id):
        await message.reply_text(
            "⚠️ ابتدا باید ربات را استارت کنید.\n\nلطفاً دستور /start را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔄 شروع مجدد", callback_data="start")]]
            )
        )
        return
    
    # پیام وضعیت
    status_msg = await message.reply_text(
        "🔄 در حال پردازش لینک از سایت بزرگسال…\n⏳ لطفاً چند لحظه صبر کنید…"
    )
    
    try:
        # استخراج اطلاعات ویدیو
        video_info = await extract_pornhub_info(url)
        
        if not video_info or not video_info.get('qualities'):
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
        
        # ذخیره در کش
        pornhub_cache[user_id] = video_info
        
        # متن توصیفی
        info_text = (
            f"🎬 <b>{html.escape(video_info['title'])}</b>\n\n"
            f"👤 <b>آپلودر:</b> {html.escape(video_info['uploader'])}\n"
            f"⏱ <b>مدت زمان:</b> {format_duration(video_info['duration'])}\n"
            f"👁 <b>بازدید:</b> {format_number(video_info['view_count'])}\n\n"
            f"📋 <b>لطفاً کیفیت مورد نظر را انتخاب کنید:</b>"
        )
        
        # کیبورد کیفیت‌ها
        kb = create_quality_keyboard(video_info['qualities'])
        
        # ویرایش پیام
        await status_msg.edit_text(
            text=info_text,
            parse_mode=ParseMode.HTML,
            reply_markup=kb
        )
        
        elapsed = time.time() - start
        logger.info(f"Quality selection shown in {elapsed:.2f}s for user {user_id}")
    
    except Exception as exc:
        logger.error(f"Error handling Pornhub link (user {user_id}): {exc}")
        await status_msg.edit_text(
            f"❌ **خطا در پردازش ویدیو**\n\nخطا: {str(exc)[:150]}\n\nلطفاً دوباره تلاش کنید.",
            parse_mode=ParseMode.MARKDOWN
        )


@Client.on_callback_query(filters.regex(r'^ph_dl_(\d+)$'))
async def quality_callback(client: Client, callback_query):
    """دریافت انتخاب کیفیت و شروع دانلود"""
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    if user_id not in pornhub_cache:
        await callback_query.answer(
            "⏳ اطلاعات منقضی شده. لطفاً دوباره لینک بفرستید.",
            show_alert=True
        )
        return
    
    video_info = pornhub_cache[user_id]
    selected = data.split('_')[-1]  # مثلاً 720 یا best
    
    if selected not in video_info['qualities']:
        await callback_query.answer(
            "❌ کیفیت انتخابی موجود نیست.",
            show_alert=True
        )
        return
    
    await callback_query.answer("📥 شروع دانلود…", show_alert=False)
    
    quality_info = video_info['qualities'][selected]
    
    # شروع دانلود - پیام بدون تایتل (برای جلوگیری از فیلتر)
    await callback_query.message.edit_text(
        " **دانلود محتوای بزرگسال**\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **کیفیت:** {selected}p\n"
        f"⏱️ **وضعیت:** در حال دانلود...\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "⏳ لطفاً صبر کنید، این فرآیند ممکن است چند دقیقه طول بکشد.\n\n"
        ,
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        # ساخت نام فایل
        safe_title = "".join(
            c for c in video_info['title']
            if c.isalnum() or c in (' ', '-', '_')
        ).strip()[:30]
        
        if len(safe_title) < 5:
            safe_title = "Pornhub_Video"
        
        filename = f"{safe_title}_{selected}p.mp4"
        
        # دانلود فایل
        download_start = time.time()
        downloaded_file = await pornhub_downloader.download(
            url=video_info['url'],
            format_string=quality_info['format_string'],
            output_filename=filename
        )
        download_time = time.time() - download_start
        
        if not downloaded_file or not os.path.exists(downloaded_file):
            raise Exception("دانلود ناموفق بود")
        
        file_size = os.path.getsize(downloaded_file)
        file_size_mb = file_size / (1024 * 1024)
        
        logger.info(f"Download completed: {file_size_mb:.2f}MB in {download_time:.2f}s")
        
        # ذخیره فایل با کد یکتا
        file_code = pornhub_storage.store_file(
            file_path=downloaded_file,
            user_id=user_id,
            title=video_info['title'],
            quality=selected,
            file_size=file_size
        )
        
        if not file_code:
            raise Exception("خطا در ذخیره‌سازی فایل")
        
        # پیام موفقیت - ساده و کوتاه
        success_message = (
            "✅ **فایل آماده است!**\n\n"
            "📥 **برای دریافت:**\n"
            "1️⃣ وارد ربات شوید: @wwwiranbot\n"
            "2️⃣ این پیام را فوروارد کنید\n\n"
            f"🔑 کد فایل: `FILE_{file_code}`"
        )
        
        await callback_query.message.edit_text(
            success_message,
            parse_mode=ParseMode.HTML
        )
        
        # پاک‌سازی کش
        pornhub_cache.pop(user_id, None)
    
    except Exception as e:
        logger.error(f"Download error: {e}")
        error_msg = str(e)[:100]  # محدود کردن طول خطا
        await callback_query.message.edit_text(
            "❌ **خطا در دانلود**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🔴 **علت:** {error_msg}\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 **راهنمایی:**\n"
            "• لینک را دوباره بررسی کنید\n"
            "• چند دقیقه دیگر تلاش کنید\n"
            "• در صورت تکرار، با پشتیبانی تماس بگیرید\n\n"
            "🔄 برای تلاش مجدد، لینک را دوباره ارسال کنید.",
            parse_mode=ParseMode.MARKDOWN
        )


@Client.on_callback_query(filters.regex(r'^ph_cancel$'))
async def cancel_callback(client: Client, callback_query):
    """لغو عملیات"""
    user_id = callback_query.from_user.id
    await callback_query.answer("🔴 عملیات لغو شد", show_alert=True)
    await callback_query.message.delete()
    pornhub_cache.pop(user_id, None)
