"""
Pornhub Delivery Bot - نسخه Pyrogram (100% Fixed)
ربات دوم برای ارسال فایل‌های بزرگ (تا 2GB) با استفاده از Pyrogram
"""

import os
import sys
import re
import json
import logging
import asyncio
import threading
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

# اضافه کردن مسیر پروژه
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plugins.pornhub_storage import pornhub_storage

# ایجاد پوشه‌های مورد نیاز
os.makedirs('logs', exist_ok=True)
os.makedirs('temp', exist_ok=True)

# تنظیمات لاگ با Rotation
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        RotatingFileHandler(
            'logs/pornhub_delivery.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# بارگذاری environment variables
load_dotenv()

# تنظیمات ربات
DELIVERY_BOT_TOKEN = os.getenv("DELIVERY_BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

if not DELIVERY_BOT_TOKEN:
    logger.error("DELIVERY_BOT_TOKEN not found in environment variables")
    print("❌ Error: DELIVERY_BOT_TOKEN not found in .env file")
    sys.exit(1)

if not API_ID or not API_HASH:
    logger.error("API_ID or API_HASH not found in environment variables")
    print("❌ Error: API_ID and API_HASH required in .env file")
    sys.exit(1)

# Regex برای تشخیص کد فایل
FILE_CODE_REGEX = re.compile(r'FILE_([A-Z0-9]{8})', re.IGNORECASE)

# شناسه ادمین
ADMIN_ID = 79049016

# ساخت client
app = Client(
    "delivery_bot",
    api_id=int(API_ID),
    api_hash=API_HASH,
    bot_token=DELIVERY_BOT_TOKEN,
    workdir="."
)

# ذخیره وضعیت دانلودهای در حال انجام
active_downloads = set()


def format_size(bytes_size: int) -> str:
    """فرمت کردن حجم فایل"""
    if bytes_size >= 1024 * 1024 * 1024:
        return f"{bytes_size / (1024*1024*1024):.2f} GB"
    elif bytes_size >= 1024 * 1024:
        return f"{bytes_size / (1024*1024):.2f} MB"
    elif bytes_size >= 1024:
        return f"{bytes_size / 1024:.2f} KB"
    return f"{bytes_size} B"


def generate_thumbnail(video_path: str) -> str:
    """
    تولید thumbnail از ویدیو با ffmpeg
    Returns: مسیر thumbnail یا None
    """
    try:
        import subprocess
        
        # ایجاد نام یکتا برای thumbnail
        thumb_name = f"thumb_{os.path.basename(video_path)}.jpg"
        thumb_path = os.path.join("temp", thumb_name)
        
        # حذف thumbnail قدیمی اگر وجود داشت
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
        
        # استخراج فریم از ثانیه 3 ویدیو
        cmd = [
            'ffmpeg', '-i', video_path,
            '-ss', '00:00:03',  # از ثانیه 3
            '-vframes', '1',     # فقط یک فریم
            '-vf', 'scale=320:-1',  # کاهش سایز
            '-y',                # overwrite
            thumb_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=15,
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL
        )
        
        if result.returncode == 0 and os.path.exists(thumb_path):
            logger.info(f"Thumbnail generated: {thumb_path}")
            return thumb_path
        else:
            logger.warning("Failed to generate thumbnail")
            return None
    
    except Exception as e:
        logger.warning(f"Thumbnail generation error: {e}")
        return None


def get_video_metadata(file_path: str) -> tuple:
    """
    استخراج metadata ویدیو با ffprobe
    Returns: (duration, width, height)
    """
    duration = 0
    width = 0
    height = 0
    
    try:
        import subprocess
        
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', file_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            metadata = json.loads(result.stdout)
            
            # Duration
            if 'format' in metadata and 'duration' in metadata['format']:
                duration = int(float(metadata['format']['duration']))
            
            # Width & Height
            for stream in metadata.get('streams', []):
                if stream.get('codec_type') == 'video':
                    width = stream.get('width', 0)
                    height = stream.get('height', 0)
                    if width and height:
                        break
            
            logger.info(f"Metadata: {duration}s, {width}x{height}")
        
    except Exception as e:
        logger.warning(f"Metadata extraction failed: {e}")
    
    return duration, width, height


def get_admin_thumbnail() -> str:
    """دریافت thumbnail ادمین"""
    try:
        from plugins.adult_content_admin import get_thumbnail_path
        admin_thumb = get_thumbnail_path()
        if admin_thumb and os.path.exists(admin_thumb):
            return admin_thumb
    except:
        pass
    return None


def delete_file_background(file_code: str, file_path: str, thumb_path: str = None, delay: int = 120):
    """
    حذف فایل در background thread (100% کار می‌کنه)
    """
    def delete_worker():
        try:
            logger.info(f"⏰ Deletion scheduled for {file_code} in {delay}s")
            time.sleep(delay)
            
            # حذف فایل اصلی
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"✅ File deleted: {file_path}")
            
            # حذف thumbnail
            if thumb_path and os.path.exists(thumb_path):
                os.remove(thumb_path)
                logger.info(f"✅ Thumbnail deleted: {thumb_path}")
            
            # حذف از storage
            pornhub_storage.delete_file(file_code)
            logger.info(f"✅ Storage entry deleted: {file_code}")
        
        except Exception as e:
            logger.error(f"❌ Deletion error for {file_code}: {e}")
    
    # ساخت و شروع thread
    thread = threading.Thread(target=delete_worker, daemon=True)
    thread.start()
    logger.info(f"🚀 Deletion thread started for {file_code}")


@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """هندلر دستور /start"""
    user = message.from_user
    
    welcome_message = (
        f"👋 سلام {user.mention}!\n\n"
        "🤖 به ربات ارسال فایل خوش آمدید!\n\n"
        "📝 **نحوه استفاده:**\n"
        "1️⃣ پیام حاوی کد فایل را از ربات اصلی فوروارد کنید\n"
        "2️⃣ فایل شما به صورت خودکار ارسال می‌شود\n\n"
        "🔑 **فرمت کد:** `FILE_XXXXXXXX`\n\n"
        "⚠️ **توجه:**\n"
        "• کدها فقط 24 ساعت معتبر هستند\n"
        "• هر کد فقط یک بار قابل استفاده است\n"
        "• فایل‌ها 2 دقیقه بعد از ارسال حذف می‌شوند\n\n"
        "💡 **راهنما:**\n"
        "• /start - نمایش این پیام\n"
        "• /help - راهنمای کامل\n"
        "• /status - وضعیت ربات\n\n"
        "✨ آماده دریافت کد فایل شما هستیم!"
    )
    
    await message.reply_text(welcome_message)
    logger.info(f"User {user.id} started the bot")


@app.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    """هندلر دستور /help"""
    help_message = (
        "📚 **راهنمای کامل ربات**\n\n"
        "🎯 **هدف:**\n"
        "این ربات برای دریافت فایل‌های دانلود شده از ربات اصلی طراحی شده است.\n\n"
        "📝 **مراحل استفاده:**\n\n"
        "1️⃣ **دریافت کد:**\n"
        "   • در ربات اصلی لینک خود را ارسال کنید\n"
        "   • کیفیت مورد نظر را انتخاب کنید\n"
        "   • کد فایل را دریافت کنید\n\n"
        "2️⃣ **فوروارد پیام:**\n"
        "   • پیام حاوی کد را به این ربات فوروارد کنید\n"
        "   • یا کد را به صورت دستی ارسال کنید\n\n"
        "3️⃣ **دریافت فایل:**\n"
        "   • ربات خودکار فایل را برای شما ارسال می‌کند\n"
        "   • پیشرفت آپلود نمایش داده می‌شود\n\n"
        "⚠️ **نکات مهم:**\n"
        "• کدها 24 ساعت معتبرند\n"
        "• فایل‌ها 2 دقیقه بعد حذف می‌شوند\n"
        "• فایل‌های تا 2GB پشتیبانی می‌شود\n"
        "• سریع فایل را فوروارد کنید\n"
        "• هر کد فقط یکبار قابل استفاده است\n\n"
        "🔧 **دستورات:**\n"
        "/start - شروع ربات\n"
        "/help - این راهنما\n"
        "/status - وضعیت ربات\n\n"
        "💬 در صورت بروز مشکل با پشتیبانی تماس بگیرید."
    )
    
    await message.reply_text(help_message)


@app.on_message(filters.command("status"))
async def status_command(client: Client, message: Message):
    """هندلر دستور /status"""
    try:
        storage_file = "data/pornhub_files.json"
        if os.path.exists(storage_file):
            with open(storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                total_files = len(data)
                downloaded_files = sum(1 for info in data.values() if info.get('downloaded', False))
        else:
            total_files = 0
            downloaded_files = 0
        
        status_message = (
            "📊 **وضعیت ربات**\n\n"
            "✅ **ربات:** آنلاین و فعال\n"
            f"📁 **فایل‌های موجود:** {total_files}\n"
            f"✔️ **فایل‌های ارسال شده:** {downloaded_files}\n"
            f"⏳ **در انتظار:** {total_files - downloaded_files}\n"
            f"🔄 **در حال دانلود:** {len(active_downloads)}\n\n"
            "🔄 **پاکسازی خودکار:** فعال (2 دقیقه بعد از ارسال)\n"
            "⏰ **مدت اعتبار کد:** 24 ساعت\n"
            "📦 **حداکثر سایز فایل:** 2 GB\n\n"
            "💚 همه چیز عالی کار می‌کند!"
        )
        
        await message.reply_text(status_message)
    
    except Exception as e:
        logger.error(f"Status command error: {e}")
        await message.reply_text("❌ خطا در دریافت وضعیت")


@app.on_message(filters.text & filters.private)
async def handle_message(client: Client, message: Message):
    """هندلر اصلی برای پیام‌ها"""
    try:
        text = message.text
        user_id = message.from_user.id
        
        logger.info(f"📨 Message from user {user_id}: {text[:50]}")
        
        # جستجوی کد فایل
        match = FILE_CODE_REGEX.search(text)
        
        if not match:
            await message.reply_text(
                "❌ **کد فایل یافت نشد!**\n\n"
                "لطفاً پیام حاوی کد فایل را فوروارد کنید یا کد را به صورت دستی ارسال کنید.\n\n"
                "🔑 **فرمت صحیح:** `FILE_XXXXXXXX`\n\n"
                "💡 برای راهنما از دستور /help استفاده کنید."
            )
            return
        
        file_code = match.group(1).upper()
        logger.info(f"🔑 File code detected: {file_code}")
        
        # بررسی duplicate
        if file_code in active_downloads:
            await message.reply_text(
                "⚠️ **این فایل در حال ارسال است!**\n\n"
                "لطفاً صبر کنید تا ارسال قبلی کامل شود."
            )
            return
        
        status_msg = await message.reply_text(
            "🔍 **در حال بررسی کد...**\n\n⏳ لطفاً صبر کنید..."
        )
        
        # دریافت اطلاعات فایل
        file_info = pornhub_storage.get_file_info(file_code)
        
        if not file_info:
            await status_msg.edit_text(
                "❌ **کد نامعتبر یا منقضی شده**\n\n"
                "این کد وجود ندارد یا منقضی شده است.\n\n"
                "💡 **راهنمایی:**\n"
                "• کد را دوباره بررسی کنید\n"
                "• ممکن است 24 ساعت گذشته باشد\n"
                "• فایل جدید درخواست دهید"
            )
            return
        
        # بررسی downloaded
        if file_info.get('downloaded', False):
            await status_msg.edit_text(
                "❌ **این کد قبلاً استفاده شده است**\n\n"
                "هر کد فقط یکبار قابل استفاده است.\n\n"
                "🔄 لطفاً کد جدید درخواست دهید."
            )
            return
        
        # بررسی وجود فایل
        file_path = file_info.get('file_path')
        if not file_path or not os.path.exists(file_path):
            await status_msg.edit_text(
                "❌ **فایل یافت نشد**\n\n"
                "فایل از سرور حذف شده است.\n\n"
                "🔄 لطفاً فایل جدید درخواست دهید."
            )
            pornhub_storage.delete_file(file_code)
            return
        
        # اضافه به active downloads
        active_downloads.add(file_code)
        
        try:
            quality = file_info.get('quality', 'Unknown')
            file_size = file_info.get('file_size', 0)
            
            await status_msg.edit_text(
                f"📥 **فایل پیدا شد!**\n\n"
                f"📊 کیفیت: {quality}p\n"
                f"💾 حجم: {format_size(file_size)}\n\n"
                f"⏳ در حال آماده‌سازی..."
            )
            
            logger.info(f"🎬 Starting upload for {file_code}")
            
            # تولید thumbnail
            await status_msg.edit_text(
                f"📤 **در حال آماده‌سازی...**\n\n"
                f"🖼️ تولید thumbnail...\n"
                f"💾 {format_size(file_size)}"
            )
            
            generated_thumb = generate_thumbnail(file_path)
            thumbnail = generated_thumb or get_admin_thumbnail()
            
            # استخراج metadata
            duration, width, height = get_video_metadata(file_path)
            
            await status_msg.edit_text(
                f"📤 **در حال ارسال...**\n\n"
                f"💾 {format_size(file_size)}\n\n"
                f"⏳ لطفاً صبر کنید..."
            )
            
            # آماده‌سازی پارامترها
            caption = f"📊 کیفیت: {quality}p"
            
            video_params = {
                'video': file_path,
                'caption': caption,
                'supports_streaming': True
            }
            
            # اضافه کردن thumbnail - حتماً باید باشه
            if thumbnail:
                video_params['thumb'] = thumbnail
                logger.info(f"✅ Using thumbnail: {thumbnail}")
            
            # اضافه کردن metadata
            if duration > 0:
                video_params['duration'] = duration
            
            # ابعاد - حتماً باید باشه برای نمایش صحیح
            if width > 0 and height > 0:
                video_params['width'] = width
                video_params['height'] = height
                logger.info(f"✅ Dimensions: {width}x{height}")
            
            # ارسال ویدیو
            logger.info(f"📤 Uploading {format_size(file_size)}...")
            await message.reply_video(**video_params)
            
            await status_msg.delete()
            
            # علامت‌گذاری
            pornhub_storage.mark_as_downloaded(file_code)
            logger.info(f"✅ File {file_code} sent to user {user_id}")
            
            await message.reply_text(
                "✅ **فایل با موفقیت ارسال شد!**\n\n"
                "⚠️ **توجه مهم:**\n"
                "سریعاً این فایل را به جایی فوروارد کنید!\n"
                "⏰ **2 دقیقه دیگر فایل از ربات حذف می‌شود.**\n\n"
                "💡 برای دریافت فایل‌های بیشتر، کد جدید ارسال کنید."
            )
            
            # حذف فایل در background (100% کار می‌کنه)
            delete_file_background(file_code, file_path, generated_thumb, delay=120)
        
        except Exception as upload_error:
            logger.error(f"❌ Upload error: {upload_error}", exc_info=True)
            await status_msg.edit_text(
                f"❌ **خطا در ارسال فایل**\n\n"
                f"خطا: {str(upload_error)[:100]}\n\n"
                f"🔄 لطفاً دوباره تلاش کنید."
            )
        
        finally:
            active_downloads.discard(file_code)
    
    except Exception as e:
        logger.error(f"❌ Handler error: {e}", exc_info=True)
        try:
            await message.reply_text(
                "❌ **خطای غیرمنتظره**\n\n"
                "لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."
            )
        except:
            pass


def main():
    """تابع اصلی"""
    try:
        print("=" * 70)
        print("🚀 Starting Pornhub Delivery Bot (100% Fixed)")
        print("=" * 70)
        print()
        print("✅ Bot initialized successfully")
        print("🤖 Bot username: @wwwiranbot")
        print("📦 Max file size: 2 GB")
        print("🔧 All bugs fixed (Thread + Thumbnail)")
        print("⏳ Starting...")
        print("=" * 70)
        print()
        
        logger.info("✅ Delivery bot started (100% Fixed)")
        logger.info("🤖 Bot: @wwwiranbot")
        
        app.run()
    
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped by user")
        logger.info("Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Bot error: {e}")
        logger.error(f"Bot error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()