"""
RadioJavan Handler - سیستم دانلود از رادیو جوان
مستقل از سایر بخش‌ها
نویسنده: Kiro AI Assistant
تاریخ: 2025-11-01
"""

import os
import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from plugins.db_wrapper import DB
from plugins.logger_config import get_logger
from plugins.start import join  # 🔒 Import فیلتر عضویت اسپانسری
from radiojavanapi import Client as RJClient
import requests
from urllib.parse import urlparse

# Initialize logger
logger = get_logger('radiojavan_handler')

# RadioJavan URL pattern
RADIOJAVAN_REGEX = re.compile(
    r'^(?:https?://)?(?:www\.)?(?:play\.)?radiojavan\.com/(?:song|podcast|video)/[\w\-\(\)]+/?$',
    re.IGNORECASE
)


def sanitize_filename(filename: str) -> str:
    """حذف کاراکترهای نامعتبر از نام فایل"""
    return re.sub(r'[<>:"/\\|?*]', '', filename)


async def download_file(url: str, filename: str, download_dir: str = "downloads") -> str:
    """دانلود فایل از URL"""
    try:
        # ایجاد پوشه downloads اگر وجود ندارد
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        
        # دریافت پسوند فایل از URL
        parsed_url = urlparse(url)
        file_extension = os.path.splitext(parsed_url.path)[1] or '.mp3'
        
        # ایجاد مسیر کامل فایل
        full_filename = f"{filename}{file_extension}"
        file_path = os.path.join(download_dir, full_filename)
        
        logger.info(f"Downloading: {full_filename}")
        
        # دانلود فایل
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(url, stream=True, timeout=60)
        )
        response.raise_for_status()
        
        # ذخیره فایل
        def _save_file():
            with open(file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
        
        await loop.run_in_executor(None, _save_file)
        
        logger.info(f"Download completed: {file_path}")
        return file_path
        
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise


async def get_song_info(url: str) -> dict:
    """دریافت اطلاعات آهنگ از رادیو جوان"""
    try:
        logger.info(f"Fetching song info from: {url}")
        
        # ایجاد client رادیو جوان
        loop = asyncio.get_event_loop()
        
        def _get_info():
            client = RJClient()
            return client.get_song_by_url(url)
        
        song = await loop.run_in_executor(None, _get_info)
        
        if not song:
            logger.error("Failed to fetch song info")
            return None
        
        # استخراج اطلاعات
        info = {
            'name': song.name,
            'artist': song.artist,
            'album': song.album if song.album else 'نامشخص',
            'date': song.date,
            'duration': song.duration,
            'likes': song.likes,
            'dislikes': song.dislikes,
            'downloads': song.downloads,
            'hq_link': str(song.hq_link) if song.hq_link else None,
            'link': str(song.link) if song.link else None,
            'lq_link': str(song.lq_link) if song.lq_link else None,
            'photo': str(song.photo) if song.photo else None,
            'thumbnail': str(song.thumbnail) if song.thumbnail else None,
        }
        
        logger.info(f"Song info fetched: {info['artist']} - {info['name']}")
        return info
        
    except Exception as e:
        logger.error(f"Error fetching song info: {e}")
        return None


def format_number(num: int) -> str:
    """فرمت کردن اعداد با کاما"""
    return f"{num:,}"


@Client.on_message(filters.private & filters.regex(RADIOJAVAN_REGEX) & join)
async def radiojavan_handler(client: Client, message: Message):
    """Handler اصلی برای لینک‌های رادیو جوان"""
    try:
        text = message.text.strip()
        
        # 🔥 Debug: لاگ کردن
        logger.info(f"RadioJavan handler received text: {text[:50]}")
        print(f"[RADIOJAVAN] Handler triggered: {text[:50]}")
        
        user_id = message.from_user.id
        logger.info(f"RadioJavan request from user {user_id}: {text}")
        
        # ارسال پیام در حال پردازش
        status_msg = await message.reply_text(
            "🎵 **در حال پردازش...**\n\n"
            "⏳ لطفاً صبر کنید، در حال دریافت اطلاعات آهنگ از رادیو جوان...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # دریافت اطلاعات آهنگ
        song_info = await get_song_info(text)
        
        if not song_info:
            await status_msg.edit_text(
                "❌ **خطا در دریافت اطلاعات**\n\n"
                "متأسفانه نتوانستیم اطلاعات این آهنگ را از رادیو جوان دریافت کنیم.\n"
                "لطفاً لینک را بررسی کنید و دوباره تلاش کنید."
            )
            return
        
        # بررسی لینک دانلود
        download_url = song_info.get('hq_link') or song_info.get('link')
        if not download_url:
            await status_msg.edit_text(
                "❌ **لینک دانلود یافت نشد**\n\n"
                "متأسفانه لینک دانلود برای این آهنگ در دسترس نیست."
            )
            return
        
        # بروزرسانی پیام وضعیت
        await status_msg.edit_text(
            f"🎵 **{song_info['artist']} - {song_info['name']}**\n\n"
            f"⬇️ در حال دانلود...\n"
            f"⏳ لطفاً صبر کنید..."
        )
        
        # دانلود فایل
        filename = sanitize_filename(f"{song_info['artist']} - {song_info['name']}")
        file_path = await download_file(download_url, filename)
        
        # بروزرسانی پیام وضعیت
        await status_msg.edit_text(
            f"🎵 **{song_info['artist']} - {song_info['name']}**\n\n"
            f"⬆️ در حال آپلود...\n"
            f"⏳ لطفاً صبر کنید..."
        )
        
        # ساخت کپشن
        caption = (
            f"🎧 **{song_info['artist']}** - \"{song_info['name']}\"\n\n"
            f"📯 **Plays:** {format_number(song_info['downloads'])}\n"
            f"📥 **Downloads:** {format_number(song_info['downloads'])}\n"
            f"👍 **Likes:** {format_number(song_info['likes'])}\n\n"
            f"🎵 **از رادیو جوان دانلود شد**"
        )
        
        # ارسال فایل به کاربر
        await client.send_audio(
            chat_id=message.chat.id,
            audio=file_path,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
            title=song_info['name'],
            performer=song_info['artist'],
            duration=int(song_info['duration']) if song_info['duration'] else None,
            reply_to_message_id=message.id
        )
        
        # حذف پیام وضعیت
        await status_msg.delete()
        
        # حذف فایل محلی
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted local file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete local file: {e}")
        
        # ثبت آمار
        try:
            db = DB()
            db.increment_user_requests(user_id)
            logger.info(f"Stats updated for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to update stats: {e}")
        
        logger.info(f"RadioJavan download completed for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in radiojavan_handler: {e}")
        try:
            await message.reply_text(
                "❌ **خطا در پردازش**\n\n"
                f"متأسفانه خطایی رخ داد: {str(e)[:100]}\n"
                "لطفاً دوباره تلاش کنید."
            )
        except:
            pass


print("✅ RadioJavan Handler loaded")
print("   - Pattern: radiojavan.com/song/...")
print("   - Independent from other downloaders")
