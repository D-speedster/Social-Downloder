"""
Pornhub Delivery Bot - نسخه Pyrogram ساده
ربات دوم برای ارسال فایل‌های بزرگ (تا 2GB)
"""

import os
import sys
import re
import json
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv

# بارگذاری environment variables
load_dotenv()

# تنظیمات ربات
DELIVERY_BOT_TOKEN = os.getenv("DELIVERY_BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

if not DELIVERY_BOT_TOKEN or not API_ID or not API_HASH:
    print("❌ Error: Missing environment variables")
    sys.exit(1)

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('logs/pornhub_delivery.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# اضافه کردن مسیر پروژه
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plugins.pornhub_storage import pornhub_storage

# Regex برای تشخیص کد فایل
FILE_CODE_REGEX = re.compile(r'FILE_([A-Z0-9]{8})', re.IGNORECASE)

# ساخت client
app = Client(
    "delivery_bot",
    api_id=int(API_ID),
    api_hash=API_HASH,
    bot_token=DELIVERY_BOT_TOKEN,
    workdir="."
)


def format_size(bytes_size: int) -> str:
    """فرمت کردن حجم فایل"""
    if bytes_size >= 1024 * 1024 * 1024:
        return f"{bytes_size / (1024*1024*1024):.2f} GB"
    elif bytes_size >= 1024 * 1024:
        return f"{bytes_size / (1024*1024):.2f} MB"
    elif bytes_size >= 1024:
        return f"{bytes_size / 1024:.2f} KB"
    return f"{bytes_size} B"


def get_video_metadata(file_path: str) -> tuple:
    """استخراج metadata ویدیو با ffprobe"""
    import subprocess
    import json as json_lib
    
    duration = 0
    width = 0
    height = 0
    
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            metadata = json_lib.loads(result.stdout)
            
            # Duration
            if 'format' in metadata and 'duration' in metadata['format']:
                duration = int(float(metadata['format']['duration']))
            
            # Width & Height با بررسی rotation
            for stream in metadata.get('streams', []):
                if stream.get('codec_type') == 'video':
                    w = stream.get('width', 0)
                    h = stream.get('height', 0)
                    
                    # بررسی rotation
                    rotation = 0
                    tags = stream.get('tags', {})
                    if 'rotate' in tags:
                        try:
                            rotation = int(tags['rotate'])
                        except:
                            pass
                    
                    # اگر 90 یا 270 درجه چرخیده، width/height رو عوض کن
                    if rotation in (90, 270):
                        width, height = h, w
                    else:
                        width, height = w, h
                    break
            
            logger.info(f"Video metadata: duration={duration}s, {width}x{height}")
    except Exception as e:
        logger.warning(f"Could not extract metadata: {e}")
    
    return duration, width, height


async def delete_message_after_delay(client: Client, chat_id: int, message_id: int, file_code: str, file_path: str, delay: int = 120):
    """حذف پیام و فایل بعد از delay ثانیه"""
    try:
        logger.info(f"⏰ Scheduled deletion for message {message_id} and file {file_code} in {delay}s")
        await asyncio.sleep(delay)
        
        # حذف پیام
        try:
            await client.delete_messages(chat_id, message_id)
            logger.info(f"🗑️ Message {message_id} deleted from chat {chat_id}")
        except Exception as e:
            logger.warning(f"Could not delete message: {e}")
        
        # حذف فایل از دیسک
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"🗑️ File deleted: {file_path}")
        except Exception as e:
            logger.warning(f"Could not delete file: {e}")
        
        # حذف از storage
        try:
            pornhub_storage.delete_file(file_code)
            logger.info(f"🗑️ Storage entry deleted: {file_code}")
        except Exception as e:
            logger.warning(f"Could not delete storage entry: {e}")
    
    except Exception as e:
        logger.error(f"Error in delete_message_after_delay: {e}")


@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """هندلر دستور /start"""
    await message.reply_text(
        "👋 سلام!\n\n"
        "🤖 به ربات ارسال فایل خوش آمدید!\n\n"
        "📝 کد فایل را ارسال کنید یا پیام را فوروارد کنید."
    )


@app.on_message(filters.command("status"))
async def status_command(client: Client, message: Message):
    """هندلر دستور /status"""
    try:
        storage_file = "data/pornhub_files.json"
        if os.path.exists(storage_file):
            with open(storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                total_files = len(data)
        else:
            total_files = 0
        
        await message.reply_text(
            f"📊 **وضعیت ربات**\n\n"
            f"✅ آنلاین و فعال\n"
            f"📁 فایل‌های موجود: {total_files}\n"
            f"📦 حداکثر سایز: 2 GB"
        )
    except Exception as e:
        logger.error(f"Status error: {e}")
        await message.reply_text("❌ خطا در دریافت وضعیت")


@app.on_message(filters.text & filters.private)
async def handle_message(client: Client, message: Message):
    """هندلر اصلی برای پیام‌ها"""
    try:
        text = message.text
        user_id = message.from_user.id
        
        # جستجوی کد فایل
        match = FILE_CODE_REGEX.search(text)
        
        if not match:
            await message.reply_text("❌ کد فایل یافت نشد!\n\n🔑 فرمت: FILE_XXXXXXXX")
            return
        
        file_code = match.group(1).upper()
        logger.info(f"File code detected: {file_code}")
        
        # پیام وضعیت
        status_msg = await message.reply_text("🔍 در حال بررسی...")
        
        # دریافت اطلاعات فایل
        file_info = pornhub_storage.get_file_info(file_code)
        
        if not file_info:
            await status_msg.edit_text("❌ کد نامعتبر یا منقضی شده")
            return
        
        # بررسی وجود فایل
        file_path = file_info.get('file_path')
        if not file_path or not os.path.exists(file_path):
            await status_msg.edit_text("❌ فایل یافت نشد")
            pornhub_storage.delete_file(file_code)
            return
        
        # اطلاعات فایل
        quality = file_info.get('quality', 'Unknown')
        file_size = file_info.get('file_size', 0)
        
        await status_msg.edit_text(
            f"📥 فایل پیدا شد!\n\n"
            f"📊 کیفیت: {quality}p\n"
            f"💾 حجم: {format_size(file_size)}\n\n"
            f"⏳ در حال ارسال..."
        )
        
        # استخراج metadata
        duration, width, height = get_video_metadata(file_path)
        
        # بررسی thumbnail
        thumbnail = None
        try:
            from plugins.adult_content_admin import get_thumbnail_path
            admin_thumb = get_thumbnail_path()
            if admin_thumb and os.path.exists(admin_thumb):
                thumbnail = admin_thumb
        except:
            pass
        
        # ارسال فایل
        try:
            logger.info(f"Sending file: {file_path}")
            
            # Caption ساده
            caption = f"📊 کیفیت: {quality}p"
            
            # پارامترهای ارسال
            video_params = {
                'video': file_path,
                'caption': caption,
                'supports_streaming': True
            }
            
            # اضافه کردن thumbnail
            if thumbnail:
                video_params['thumb'] = thumbnail
            
            # اضافه کردن metadata فقط اگر معتبر باشه
            if duration > 0:
                video_params['duration'] = duration
            
            if width > 0 and height > 0:
                video_params['width'] = width
                video_params['height'] = height
            
            # ارسال ویدیو
            sent_message = await message.reply_video(**video_params)
            
            # حذف پیام وضعیت
            await status_msg.delete()
            
            # علامت‌گذاری
            pornhub_storage.mark_as_downloaded(file_code)
            
            logger.info(f"File {file_code} sent successfully (msg_id={sent_message.id})")
            
            # پیام موفقیت
            await message.reply_text(
                "✅ **فایل ارسال شد!**\n\n"
                "⚠️ **توجه:** سریعاً فایل را ذخیره کنید!\n"
                "⏰ **2 دقیقه دیگر از ربات حذف می‌شود.**"
            )
            
            # زمان‌بندی حذف پیام و فایل
            asyncio.create_task(
                delete_message_after_delay(
                    client,
                    sent_message.chat.id,
                    sent_message.id,
                    file_code,
                    file_path,
                    delay=120
                )
            )
        
        except Exception as e:
            logger.error(f"Upload error: {e}", exc_info=True)
            await status_msg.edit_text(f"❌ خطا در ارسال: {str(e)[:100]}")
    
    except Exception as e:
        logger.error(f"Handler error: {e}", exc_info=True)
        try:
            await message.reply_text("❌ خطای غیرمنتظره")
        except:
            pass


def main():
    """تابع اصلی"""
    try:
        print("=" * 70)
        print("🚀 Starting Delivery Bot (Pyrogram)")
        print("=" * 70)
        print()
        
        logger.info("✅ Delivery bot started")
        logger.info("📦 Max file size: 2 GB")
        
        # شروع ربات
        app.run()
    
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped")
        logger.info("Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Bot error: {e}")
        logger.error(f"Bot error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
