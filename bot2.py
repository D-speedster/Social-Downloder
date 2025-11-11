"""
Pornhub Delivery Bot - نسخه Pyrogram
ربات دوم برای ارسال فایل‌های بزرگ (تا 2GB) با استفاده از Pyrogram
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

# اضافه کردن مسیر پروژه
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plugins.pornhub_storage import pornhub_storage

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
    workdir=".",
    plugins=dict(root="plugins")  # بارگذاری plugins از پوشه plugins
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


async def schedule_file_deletion(file_code: str, file_path: str, delay_seconds: int) -> None:
    """حذف خودکار فایل بعد از مدت زمان مشخص"""
    try:
        logger.info(f"Scheduled deletion for {file_code} in {delay_seconds} seconds")
        await asyncio.sleep(delay_seconds)
        
        # حذف فایل از دیسک
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"File deleted from disk: {file_path}")
        
        # حذف از storage
        pornhub_storage.delete_file(file_code)
        logger.info(f"File {file_code} deleted from storage after {delay_seconds} seconds")
    
    except Exception as e:
        logger.error(f"Error deleting file {file_code}: {e}")


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
        "• سریع فایل را فوروارد کنید\n\n"
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
        # بررسی تعداد فایل‌های موجود
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
            f"⏳ **در انتظار:** {total_files - downloaded_files}\n\n"
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
        
        logger.info(f"Received message from user {user_id}: {text[:50]}")
        
        # جستجوی کد فایل
        match = FILE_CODE_REGEX.search(text)
        
        if not match:
            # اگر کد نبود، پیام راهنما
            await message.reply_text(
                "❌ **کد فایل یافت نشد!**\n\n"
                "لطفاً پیام حاوی کد فایل را فوروارد کنید یا کد را به صورت دستی ارسال کنید.\n\n"
                "🔑 **فرمت صحیح:** `FILE_XXXXXXXX`\n\n"
                "💡 برای راهنما از دستور /help استفاده کنید."
            )
            return
        
        # استخراج کد
        file_code = match.group(1).upper()
        logger.info(f"File code detected: {file_code}")
        
        # پیام وضعیت
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
        
        # بررسی وجود فایل
        file_path = file_info.get('file_path')
        if not file_path or not os.path.exists(file_path):
            await status_msg.edit_text(
                "❌ **فایل یافت نشد**\n\n"
                "فایل از سرور حذف شده است.\n\n"
                "🔄 لطفاً فایل جدید درخواست دهید."
            )
            # حذف از storage
            pornhub_storage.delete_file(file_code)
            return
        
        # اطلاعات فایل
        quality = file_info.get('quality', 'Unknown')
        file_size = file_info.get('file_size', 0)
        
        await status_msg.edit_text(
            f"📥 **فایل پیدا شد!**\n\n"
            f"📊 کیفیت: {quality}p\n"
            f"💾 حجم: {format_size(file_size)}\n\n"
            f"⏳ در حال آماده‌سازی..."
        )
        
        # ارسال فایل
        try:
            logger.info(f"Starting upload for file: {file_path}")
            
            # Caption - بدون تایتل برای محتوای بزرگسال
            caption = f"📊 کیفیت: {quality}p"
            
            # آپدیت پیام
            await status_msg.edit_text(
                f"📤 **در حال ارسال...**\n\n"
                f"💾 {format_size(file_size)}\n\n"
                f"⏳ لطفاً صبر کنید..."
            )
            
            # بررسی thumbnail از تنظیمات ادمین
            thumbnail = None
            try:
                from plugins.adult_content_admin import get_thumbnail_path
                admin_thumb = get_thumbnail_path()
                if admin_thumb and os.path.exists(admin_thumb):
                    thumbnail = admin_thumb
                    logger.info(f"Using admin thumbnail: {admin_thumb}")
            except Exception as e:
                logger.debug(f"No admin thumbnail: {e}")
            
            # استخراج metadata ویدیو با ffprobe
            duration = 0
            width = 0
            height = 0
            
            try:
                import subprocess
                import json as json_lib
                
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
                    
                    # Width & Height
                    for stream in metadata.get('streams', []):
                        if stream.get('codec_type') == 'video':
                            width = stream.get('width', 0)
                            height = stream.get('height', 0)
                            break
                    
                    logger.info(f"Video metadata: duration={duration}s, {width}x{height}")
            except Exception as e:
                logger.warning(f"Could not extract metadata: {e}")
            
            # ارسال فایل با Pyrogram (پشتیبانی تا 2GB)
            file_size_mb = file_size / (1024 * 1024)
            logger.info(f"Sending file ({file_size_mb:.2f}MB) with Pyrogram")
            
            # ارسال به عنوان video با metadata
            # اگر width/height صفر باشه، اصلاً ارسال نکن تا Telegram خودش تشخیص بده
            video_params = {
                'video': file_path,
                'caption': caption,
                'supports_streaming': True
            }
            
            # اضافه کردن thumbnail
            if thumbnail:
                video_params['thumb'] = thumbnail
            
            # اضافه کردن metadata فقط اگر معتبر باشه
            if duration and duration > 0:
                video_params['duration'] = duration
            
            if width and width > 0 and height and height > 0:
                video_params['width'] = width
                video_params['height'] = height
                logger.info(f"Sending with dimensions: {width}x{height}")
            else:
                logger.info("Sending without dimensions (Telegram will auto-detect)")
            
            await message.reply_video(**video_params)
            
            # حذف پیام وضعیت
            await status_msg.delete()
            
            # علامت‌گذاری به عنوان دریافت شده
            pornhub_storage.mark_as_downloaded(file_code)
            
            logger.info(f"File {file_code} sent successfully to user {user_id}")
            
            # پیام موفقیت با هشدار حذف
            await message.reply_text(
                "✅ **فایل با موفقیت ارسال شد!**\n\n"
                "⚠️ **توجه مهم:**\n"
                "سریعاً این فایل را به جایی فوروارد کنید!\n"
                "⏰ **2 دقیقه دیگر فایل از ربات حذف می‌شود.**\n\n"
                "💡 برای دریافت فایل‌های بیشتر، کد جدید ارسال کنید."
            )
            
            # زمان‌بندی حذف فایل بعد از 2 دقیقه
            # استفاده از threading برای اطمینان از اجرا
            import threading
            
            def delete_file_thread():
                import time
                time.sleep(120)  # 2 دقیقه
                try:
                    # حذف فایل از دیسک
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.info(f"File deleted from disk: {file_path}")
                    
                    # حذف از storage
                    pornhub_storage.delete_file(file_code)
                    logger.info(f"File {file_code} deleted after 120 seconds")
                except Exception as e:
                    logger.error(f"Error deleting file {file_code}: {e}")
            
            # شروع thread
            delete_thread = threading.Thread(target=delete_file_thread, daemon=True)
            delete_thread.start()
            logger.info(f"Deletion thread started for {file_code}")
        
        except Exception as upload_error:
            logger.error(f"Upload error: {upload_error}", exc_info=True)
            await status_msg.edit_text(
                f"❌ **خطا در ارسال فایل**\n\n"
                f"خطا: {str(upload_error)[:100]}\n\n"
                f"🔄 لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."
            )
    
    except Exception as e:
        logger.error(f"Handler error: {e}", exc_info=True)
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
        print("🚀 Starting Pornhub Delivery Bot (Pyrogram Version)")
        print("=" * 70)
        print()
        print("✅ Bot initialized successfully")
        print("🤖 Bot username: @wwwiranbot")
        print("📦 Max file size: 2 GB")
        print("⏳ Starting...")
        print("=" * 70)
        print()
        
        logger.info("✅ Delivery bot started successfully (Pyrogram)")
        logger.info("🤖 Bot username: @wwwiranbot")
        logger.info("📦 Max file size: 2 GB")
        
        # شروع ربات
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
