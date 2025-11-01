"""
Aparat Handler - سیستم دانلود از آپارات
مشابه با YouTube Handler اما بدون نیاز به کوکی
نویسنده: Kiro AI Assistant
تاریخ: 2025-11-01
"""

import os
import time
import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from plugins.sqlite_db_wrapper import DB
from plugins.logger_config import get_logger
from plugins.start import join  # 🔒 Import فیلتر عضویت اسپانسری
import yt_dlp

# Initialize logger
logger = get_logger('aparat_handler')

# Store video info temporarily
video_cache = {}

# Aparat URL pattern
APARAT_REGEX = re.compile(
    r'^(?:https?://)?(?:www\.)?aparat\.com/v/([\w\-]+)/?$',
    re.IGNORECASE
)

# Supported qualities for Aparat
APARAT_QUALITIES = ['144', '240', '360', '480', '720', '1080']


def format_duration(seconds) -> str:
    """فرمت کردن مدت زمان"""
    if not seconds:
        return "نامشخص"
    
    # Convert to int if it's a float
    if isinstance(seconds, float):
        seconds = int(seconds)
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def format_number(num) -> str:
    """فرمت کردن اعداد با کاما"""
    if not num:
        return "0"
    # Convert to int if it's a float
    if isinstance(num, float):
        num = int(num)
    return f"{num:,}"


def format_filesize(bytes_size: int) -> str:
    """فرمت کردن حجم فایل"""
    if not bytes_size:
        return "نامشخص"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"


async def extract_aparat_info(url: str) -> dict:
    """استخراج اطلاعات ویدیو از آپارات با yt-dlp"""
    try:
        logger.info(f"Extracting info from: {url}")
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
            # NO COOKIES for Aparat!
        }
        
        loop = asyncio.get_event_loop()
        
        def _extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        
        info = await loop.run_in_executor(None, _extract)
        
        if not info:
            logger.error("Failed to extract info")
            return None
        
        # Extract available qualities
        formats = info.get('formats', [])
        available_qualities = {}
        
        logger.info(f"Found {len(formats)} formats")
        
        for quality in APARAT_QUALITIES:
            target_height = int(quality)
            
            # Find formats matching this quality
            matching_formats = [
                f for f in formats
                if f.get('height') == target_height
                and f.get('vcodec') != 'none'
                and f.get('ext') in ['mp4', 'webm']
            ]
            
            if matching_formats:
                # Sort by filesize/bitrate
                matching_formats.sort(
                    key=lambda x: (x.get('filesize', 0) or 0, x.get('tbr', 0) or 0),
                    reverse=True
                )
                best_format = matching_formats[0]
                
                available_qualities[quality] = {
                    'format_id': best_format['format_id'],
                    'filesize': best_format.get('filesize', 0) or 0,
                    'ext': best_format.get('ext', 'mp4'),
                    'height': best_format.get('height'),
                    'width': best_format.get('width'),
                }
                logger.info(f"Found quality {quality}p: format_id={best_format['format_id']}, size={format_filesize(best_format.get('filesize', 0))}")
        
        if not available_qualities:
            logger.warning("No qualities found, using best format")
            # Fallback: use best format
            available_qualities['best'] = {
                'format_id': 'best',
                'filesize': 0,
                'ext': 'mp4',
            }
        
        result = {
            'url': url,
            'title': info.get('title', 'بدون عنوان'),
            'duration': info.get('duration', 0),
            'thumbnail': info.get('thumbnail', ''),
            'uploader': info.get('uploader', 'نامشخص'),
            'view_count': info.get('view_count', 0),
            'description': info.get('description', ''),
            'qualities': available_qualities,
        }
        
        logger.info(f"Extracted info: {result['title']}, {len(available_qualities)} qualities")
        return result
        
    except Exception as e:
        logger.error(f"Error extracting Aparat info: {e}")
        return None


def create_quality_keyboard(qualities: dict) -> InlineKeyboardMarkup:
    """ایجاد کیبورد انتخاب کیفیت"""
    buttons = []
    row = []
    
    # Sort qualities by height
    sorted_qualities = sorted(
        qualities.keys(),
        key=lambda x: int(x) if x.isdigit() else 9999,
        reverse=True
    )
    
    for quality in sorted_qualities:
        quality_info = qualities[quality]
        filesize = quality_info.get('filesize', 0)
        
        # Create button text
        if filesize > 0:
            button_text = f"📹 {quality}p ({format_filesize(filesize)})"
        else:
            button_text = f"📹 {quality}p"
        
        row.append(
            InlineKeyboardButton(
                button_text,
                callback_data=f"aparat_dl_{quality}"
            )
        )
        
        # 2 buttons per row
        if len(row) == 2:
            buttons.append(row)
            row = []
    
    # Add remaining button if any
    if row:
        buttons.append(row)
    
    # Cancel button
    buttons.append([
        InlineKeyboardButton("❌ لغو", callback_data="aparat_cancel")
    ])
    
    return InlineKeyboardMarkup(buttons)


async def download_thumbnail(url: str) -> str:
    """دانلود thumbnail"""
    try:
        import aiohttp
        import tempfile
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    content = await response.read()
                    
                    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                    temp_file.write(content)
                    temp_file.close()
                    
                    logger.info(f"Thumbnail downloaded: {temp_file.name}")
                    return temp_file.name
        
        return None
    except Exception as e:
        logger.error(f"Thumbnail download error: {e}")
        return None


@Client.on_message(filters.private & filters.text & join, group=4)
async def aparat_handler(client: Client, message: Message):
    """Handler اصلی برای لینک‌های آپارات"""
    try:
        text = message.text.strip()
        
        # Check if it's an Aparat link
        match = APARAT_REGEX.match(text)
        if not match:
            return
        
        user_id = message.from_user.id
        logger.info(f"Aparat request from user {user_id}: {text}")
        
        start_time = time.time()
        
        # Send processing message
        status_msg = await message.reply_text(
            "🔄 در حال پردازش لینک آپارات...\n\n"
            "⏳ لطفاً چند لحظه صبر کنید..."
        )
        
        # Extract video info
        video_info = await extract_aparat_info(text)
        
        if not video_info or not video_info.get('qualities'):
            await status_msg.edit_text(
                "❌ **خطا در پردازش ویدیو**\n\n"
                "متأسفانه امکان دریافت اطلاعات ویدیو وجود ندارد.\n\n"
                "لطفاً موارد زیر را بررسی کنید:\n"
                "• لینک معتبر باشد\n"
                "• ویدیو در دسترس عموم باشد\n"
                "• اتصال اینترنت برقرار باشد",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Store video info in cache
        video_cache[user_id] = video_info
        
        # Create info text
        info_text = (
            f"🎬 <b>{video_info['title']}</b>\n\n"
            f"👤 <b>آپلودر:</b> {video_info['uploader']}\n"
            f"⏱ <b>مدت زمان:</b> {format_duration(video_info['duration'])}\n"
            f"👁 <b>بازدید:</b> {format_number(video_info['view_count'])}\n\n"
            f"📋 <b>لطفاً کیفیت مورد نظر را انتخاب کنید:</b>"
        )
        
        # Create keyboard
        keyboard = create_quality_keyboard(video_info['qualities'])
        
        # Download and send thumbnail
        thumbnail_path = None
        if video_info.get('thumbnail'):
            thumbnail_path = await download_thumbnail(video_info['thumbnail'])
        
        # Send quality selection message
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                await status_msg.delete()
                await message.reply_photo(
                    photo=thumbnail_path,
                    caption=info_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
                
                # Clean up thumbnail
                try:
                    os.unlink(thumbnail_path)
                except:
                    pass
            except Exception as e:
                logger.warning(f"Failed to send photo: {e}")
                await status_msg.edit_text(
                    text=info_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
        else:
            await status_msg.edit_text(
                text=info_text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        
        elapsed = time.time() - start_time
        logger.info(f"Quality selection displayed in {elapsed:.2f}s")
        
    except Exception as e:
        logger.error(f"Error handling Aparat link: {e}")
        try:
            await message.reply_text(
                f"❌ **خطا در پردازش ویدیو**\n\n"
                f"خطا: {str(e)[:100]}\n\n"
                f"لطفاً دوباره تلاش کنید.",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass


print("✅ Aparat Handler loaded")
print("   - Pattern: aparat.com/v/...")
print("   - Quality selection like YouTube")
print("   - Independent from YouTube (no cookies)")
