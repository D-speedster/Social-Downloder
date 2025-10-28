"""
YouTube Handler - سیستم جدید و بهینه دانلود از یوتیوب
نسخه بازنویسی شده با ساختار ساده و کارآمد
"""

import os
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from plugins.sqlite_db_wrapper import DB
from plugins.logger_config import get_logger
import yt_dlp

# Initialize logger
logger = get_logger('youtube_handler')

# Store video info temporarily (in production, use Redis or database)
video_cache = {}

# Supported qualities (only 4 qualities as requested)
SUPPORTED_QUALITIES = ['360', '480', '720', '1080']

async def extract_video_info(url: str) -> dict:
    """استخراج اطلاعات ویدیو با yt-dlp"""
    try:
        # Check for cookie file
        cookie_file = 'cookie_youtube.txt'
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
        }
        
        # Add cookies if file exists
        if os.path.exists(cookie_file):
            ydl_opts['cookiefile'] = cookie_file
            logger.info(f"Using cookies from: {cookie_file}")
        
        loop = asyncio.get_event_loop()
        
        def _extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        
        info = await loop.run_in_executor(None, _extract)
        
        if not info:
            return None
        
        # Extract available qualities
        formats = info.get('formats', [])
        available_qualities = {}
        
        for quality in SUPPORTED_QUALITIES:
            target_height = int(quality)
            
            # First, try to find combined formats (video + audio in one file)
            combined_formats = [
                f for f in formats
                if f.get('vcodec') != 'none' 
                and f.get('acodec') != 'none'
                and f.get('height') == target_height
                and f.get('ext') in ['mp4', 'webm']
            ]
            
            # For Shorts and some videos, try more flexible matching
            if not combined_formats:
                # Try with height tolerance (±10 pixels)
                combined_formats = [
                    f for f in formats
                    if f.get('vcodec') != 'none' 
                    and f.get('acodec') != 'none'
                    and f.get('height') is not None
                    and abs(f.get('height') - target_height) <= 10
                    and f.get('ext') in ['mp4', 'webm']
                ]
            
            # Special handling for Shorts (Portrait videos)
            if not combined_formats:
                # For Shorts, map portrait heights to landscape equivalents
                portrait_height_map = {
                    360: [640, 426, 256],    # 360p equivalents in portrait
                    480: [854, 640, 426],    # 480p equivalents in portrait  
                    720: [1280, 854],        # 720p equivalents in portrait
                    1080: [1920, 1280]       # 1080p equivalents in portrait
                }
                
                if target_height in portrait_height_map:
                    for portrait_height in portrait_height_map[target_height]:
                        combined_formats = [
                            f for f in formats
                            if f.get('vcodec') != 'none' 
                            and f.get('acodec') != 'none'
                            and f.get('height') == portrait_height
                            and f.get('ext') in ['mp4', 'webm']
                        ]
                        if combined_formats:
                            logger.info(f"Found portrait format for {quality}p: {portrait_height}p (Shorts)")
                            break
            
            if combined_formats:
                # Sort by quality (fps, bitrate)
                combined_formats.sort(
                    key=lambda x: (
                        x.get('fps', 0) or 0,
                        x.get('tbr', 0) or 0
                    ),
                    reverse=True
                )
                best_format = combined_formats[0]
                
                # Store combined format
                available_qualities[quality] = {
                    'format_string': best_format['format_id'],
                    'filesize': best_format.get('filesize', 0) or 0,
                    'fps': best_format.get('fps', 30),
                    'ext': best_format.get('ext', 'mp4'),
                    'type': 'combined',
                    'actual_height': best_format.get('height')
                }
                logger.info(f"Found combined format for {quality}p: {best_format['format_id']} (actual: {best_format.get('height')}p)")
            else:
                # Fallback: try separate video + audio formats
                video_formats = [
                    f for f in formats
                    if f.get('vcodec') != 'none' 
                    and f.get('acodec') == 'none'
                    and f.get('height') == height
                    and f.get('ext') in ['mp4', 'webm']
                ]
                
                # Try flexible height matching for video formats too
                if not video_formats:
                    video_formats = [
                        f for f in formats
                        if f.get('vcodec') != 'none' 
                        and f.get('acodec') == 'none'
                        and f.get('height') is not None
                        and abs(f.get('height') - target_height) <= 10
                        and f.get('ext') in ['mp4', 'webm']
                    ]
                
                # Special handling for Shorts (Portrait videos) - separate formats
                if not video_formats:
                    portrait_height_map = {
                        360: [640, 426, 256],
                        480: [854, 640, 426],  
                        720: [1280, 854],
                        1080: [1920, 1280]
                    }
                    
                    if target_height in portrait_height_map:
                        for portrait_height in portrait_height_map[target_height]:
                            video_formats = [
                                f for f in formats
                                if f.get('vcodec') != 'none' 
                                and f.get('acodec') == 'none'
                                and f.get('height') == portrait_height
                                and f.get('ext') in ['mp4', 'webm']
                            ]
                            if video_formats:
                                logger.info(f"Found portrait video format for {quality}p: {portrait_height}p (Shorts)")
                                break
                
                if video_formats:
                    # Find best audio format
                    audio_formats = [
                        f for f in formats
                        if f.get('acodec') != 'none'
                        and f.get('vcodec') == 'none'
                        and f.get('ext') in ['m4a', 'webm']
                    ]
                    
                    if audio_formats:
                        video_formats.sort(
                            key=lambda x: (
                                x.get('fps', 0) or 0,
                                x.get('tbr', 0) or 0
                            ),
                            reverse=True
                        )
                        audio_formats.sort(
                            key=lambda x: x.get('abr', 0) or 0,
                            reverse=True
                        )
                        
                        best_video = video_formats[0]
                        best_audio = audio_formats[0]
                        
                        # Store separate format combination
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
                        logger.info(f"Found separate formats for {quality}p: video={best_video['format_id']}, audio={best_audio['format_id']} (actual: {best_video.get('height')}p)")
        
        # Also add audio-only option
        audio_formats = [
            f for f in formats
            if f.get('acodec') != 'none'
            and f.get('vcodec') == 'none'
        ]
        
        if not audio_formats:
            # If no separate audio formats, try to find combined formats with audio
            audio_formats = [
                f for f in formats
                if f.get('acodec') != 'none'
                and f.get('ext') in ['mp4', 'webm', 'm4a']
            ]
        
        if audio_formats:
            audio_formats.sort(key=lambda x: x.get('abr', 0) or x.get('tbr', 0) or 0, reverse=True)
            best_audio = audio_formats[0]
            available_qualities['audio'] = {
                'format_string': 'bestaudio',  # استفاده از selector عمومی
                'filesize': best_audio.get('filesize', 0) or 0,
                'ext': 'mp3',  # همیشه mp3 برای فایل‌های صوتی
                'type': 'audio_only'
            }
            logger.info(f"Found audio format: bestaudio (best available: {best_audio['format_id']})")
        else:
            # اگر هیچ فرمت صوتی پیدا نشد، از best استفاده کن
            available_qualities['audio'] = {
                'format_string': 'best',  # fallback به بهترین فرمت موجود
                'filesize': 0,
                'ext': 'mp3',
                'type': 'audio_only'
            }
            logger.warning("No audio formats found, using 'best' as fallback")
        
        # Debug logging for troubleshooting
        logger.info(f"Total formats found: {len(formats)}")
        logger.info(f"Available qualities: {list(available_qualities.keys())}")
        
        # If no video qualities found, log format details for debugging
        if not any(q in available_qualities for q in SUPPORTED_QUALITIES):
            logger.warning("No video qualities found! Format details:")
            for i, fmt in enumerate(formats[:5]):  # Log first 5 formats
                logger.warning(f"  Format {i+1}: ID={fmt.get('format_id')}, "
                             f"Height={fmt.get('height')}, "
                             f"VCodec={fmt.get('vcodec')}, "
                             f"ACodec={fmt.get('acodec')}, "
                             f"Ext={fmt.get('ext')}")
        
        return {
            'title': info.get('title', 'Unknown'),
            'duration': info.get('duration', 0),
            'thumbnail': info.get('thumbnail', ''),
            'uploader': info.get('uploader', 'Unknown'),
            'view_count': info.get('view_count', 0),
            'url': url,
            'qualities': available_qualities
        }
        
    except Exception as e:
        logger.error(f"Error extracting video info: {e}")
        return None

def format_duration(seconds: int) -> str:
    """فرمت کردن مدت زمان"""
    if not seconds:
        return "نامشخص"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def format_number(num: int) -> str:
    """فرمت کردن اعداد بزرگ"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(num)

def create_quality_keyboard(qualities: dict) -> InlineKeyboardMarkup:
    """ایجاد کیبورد انتخاب کیفیت (2 دکمه در هر سطر)"""
    buttons = []
    
    # Video qualities in 2 columns
    row = []
    for quality in SUPPORTED_QUALITIES:
        if quality in qualities:
            row.append(
                InlineKeyboardButton(
                    f"📹 {quality}p",
                    callback_data=f"yt_dl_{quality}"
                )
            )
            
            if len(row) == 2:
                buttons.append(row)
                row = []
    
    # Add remaining button if any
    if row:
        buttons.append(row)
    
    # Audio-only button (full width)
    if 'audio' in qualities:
        buttons.append([
            InlineKeyboardButton(
                "🎵 فقط صدا (بهترین کیفیت)",
                callback_data="yt_dl_audio"
            )
        ])
    
    # Cancel button
    buttons.append([
        InlineKeyboardButton("❌ لغو", callback_data="yt_cancel")
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
                    
                    return temp_file.name
        
        return None
    except Exception as e:
        logger.error(f"Thumbnail download error: {e}")
        return None

@Client.on_message(
    filters.regex(r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})') 
    & filters.private
)
async def handle_youtube_link(client: Client, message: Message):
    """Handler اصلی برای لینک‌های یوتیوب"""
    start_time = time.time()
    user_id = message.from_user.id
    url = message.text.strip()
    
    logger.info(f"YouTube link received from user {user_id}: {url}")
    
    # Check if user is registered
    db = DB()
    if not db.check_user_register(user_id):
        await message.reply_text(
            "⚠️ ابتدا باید ربات را استارت کنید.\n\n"
            "لطفاً دستور /start را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 شروع مجدد", callback_data="start")
            ]])
        )
        return
    
    # Send processing message
    status_msg = await message.reply_text(
        "🔄 در حال پردازش لینک یوتیوب...\n\n"
        "⏳ لطفاً چند لحظه صبر کنید..."
    )
    
    try:
        # Extract video info
        video_info = await extract_video_info(url)
        
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
            f"👤 <b>کانال:</b> {video_info['uploader']}\n"
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
        logger.error(f"Error handling YouTube link: {e}")
        await status_msg.edit_text(
            f"❌ **خطا در پردازش ویدیو**\n\n"
            f"خطا: {str(e)[:100]}\n\n"
            f"لطفاً دوباره تلاش کنید.",
            parse_mode=ParseMode.MARKDOWN
        )
