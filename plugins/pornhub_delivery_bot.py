"""
Pornhub Delivery Bot - ربات دوم برای ارسال فایل‌ها
این ربات کدهای فوروارد شده را می‌خواند و فایل‌ها را برای کاربران ارسال می‌کند
"""

import os
import sys
import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from dotenv import load_dotenv

# بارگذاری تنظیمات
load_dotenv()

# اضافه کردن مسیر پروژه اصلی
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plugins.pornhub_storage import pornhub_storage
from plugins.logger_config import get_logger

logger = get_logger('pornhub_delivery')

# تنظیمات ربات دوم
DELIVERY_BOT_TOKEN = "8311578874:AAELkdM0t3DI_kQWXIAtIT4TeyMzZofCnyk"

# دریافت API_ID و API_HASH از config اصلی
try:
    from config import API_ID, API_HASH
except ImportError:
    logger.error("Could not import API_ID and API_HASH from config")
    sys.exit(1)

# Regex برای تشخیص کد فایل
FILE_CODE_REGEX = re.compile(r'FILE_([A-Z0-9]{8})', re.IGNORECASE)


def format_size(bytes_size: int) -> str:
    """فرمت کردن حجم فایل"""
    if bytes_size >= 1024 * 1024 * 1024:
        return f"{bytes_size / (1024*1024*1024):.2f} GB"
    elif bytes_size >= 1024 * 1024:
        return f"{bytes_size / (1024*1024):.2f} MB"
    elif bytes_size >= 1024:
        return f"{bytes_size / 1024:.2f} KB"
    return f"{bytes_size} B"


async def upload_progress(current, total, status_msg, title):
    """نمایش پیشرفت آپلود"""
    try:
        percent = (current / total) * 100
        
        # فقط هر 5% یک بار آپدیت کن
        if int(percent) % 5 == 0:
            await status_msg.edit_text(
                f"📤 **در حال ارسال**\n\n"
                f"🎬 {title[:50]}...\n\n"
                f"📊 پیشرفت: {percent:.1f}%\n"
                f"💾 {format_size(current)} / {format_size(total)}",
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        logger.debug(f"Progress update error: {e}")


@Client.on_message(filters.private & filters.text)
async def handle_file_code(client: Client, message: Message):
    """هندلر اصلی برای دریافت کد فایل"""
    try:
        text = message.text.strip()
        user_id = message.from_user.id
        
        logger.info(f"Received message from user {user_id}: {text[:50]}")
        
        # جستجوی کد فایل در متن
        match = FILE_CODE_REGEX.search(text)
        
        if not match:
            # اگر کد نبود، پیام راهنما بفرست
            await message.reply_text(
                "👋 **سلام!**\n\n"
                "این ربات برای دریافت فایل‌های دانلود شده از ربات اصلی است.\n\n"
                "📝 **نحوه استفاده:**\n"
                "1️⃣ پیام حاوی کد فایل را از ربات اصلی فوروارد کنید\n"
                "2️⃣ فایل شما ارسال خواهد شد\n\n"
                "⚠️ **توجه:** کدها فقط 24 ساعت معتبر هستند.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # استخراج کد
        file_code = match.group(1).upper()
        logger.info(f"File code detected: {file_code}")
        
        # پیام وضعیت
        status_msg = await message.reply_text(
            "🔍 **در حال بررسی کد...**\n\n⏳ لطفاً صبر کنید...",
            parse_mode=ParseMode.MARKDOWN
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
                "• فایل جدید درخواست دهید",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # بررسی وجود فایل فیزیکی
        file_path = file_info.get('file_path')
        if not file_path or not os.path.exists(file_path):
            await status_msg.edit_text(
                "❌ **فایل یافت نشد**\n\n"
                "فایل از سرور حذف شده است.\n\n"
                "🔄 لطفاً فایل جدید درخواست دهید.",
                parse_mode=ParseMode.MARKDOWN
            )
            # حذف از storage
            pornhub_storage.delete_file(file_code)
            return
        
        # آماده‌سازی برای ارسال
        title = file_info.get('title', 'Unknown')
        quality = file_info.get('quality', 'Unknown')
        file_size = file_info.get('file_size', 0)
        
        await status_msg.edit_text(
            f"📥 **فایل پیدا شد!**\n\n"
            f"🎬 {title[:50]}...\n"
            f"📊 کیفیت: {quality}p\n"
            f"💾 حجم: {format_size(file_size)}\n\n"
            f"⏳ در حال آماده‌سازی...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # ارسال فایل
        try:
            logger.info(f"Starting upload for file: {file_path}")
            
            # تعیین نوع فایل
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Caption
            caption = f"🎬 {title}\n📊 کیفیت: {quality}p"
            
            # ارسال به عنوان ویدیو
            await client.send_video(
                chat_id=message.chat.id,
                video=file_path,
                caption=caption,
                supports_streaming=True,
                progress=lambda c, t: upload_progress(c, t, status_msg, title)
            )
            
            # حذف پیام وضعیت
            await status_msg.delete()
            
            # علامت‌گذاری به عنوان دریافت شده
            pornhub_storage.mark_as_downloaded(file_code)
            
            logger.info(f"File {file_code} sent successfully to user {user_id}")
            
            # پیام موفقیت
            await message.reply_text(
                "✅ **فایل با موفقیت ارسال شد!**\n\n"
                "🎉 از استفاده شما متشکریم.",
                parse_mode=ParseMode.MARKDOWN
            )
        
        except Exception as upload_error:
            logger.error(f"Upload error: {upload_error}")
            await status_msg.edit_text(
                f"❌ **خطا در ارسال فایل**\n\n"
                f"خطا: {str(upload_error)[:100]}\n\n"
                f"🔄 لطفاً دوباره تلاش کنید.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    except Exception as e:
        logger.error(f"Handler error: {e}")
        try:
            await message.reply_text(
                "❌ **خطای غیرمنتظره**\n\n"
                "لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید.",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass


async def cleanup_task():
    """تسک پاکسازی خودکار فایل‌های قدیمی"""
    while True:
        try:
            # هر 6 ساعت یک بار پاکسازی کن
            await asyncio.sleep(6 * 3600)
            
            logger.info("Starting automatic cleanup...")
            deleted_count = pornhub_storage.cleanup_old_files(max_age_hours=24)
            logger.info(f"Cleanup completed: {deleted_count} files deleted")
        
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")


async def main():
    """تابع اصلی"""
    app = None
    cleanup = None
    
    try:
        print("=" * 70)
        print("🚀 Starting Pornhub Delivery Bot...")
        print("=" * 70)
        logger.info("Starting Pornhub Delivery Bot...")
        
        # ساخت client با session جداگانه
        app = Client(
            name="delivery_bot_session",  # نام متفاوت برای session جداگانه
            bot_token=DELIVERY_BOT_TOKEN,
            api_id=API_ID,
            api_hash=API_HASH,
            workdir="./delivery_bot_data"  # پوشه جداگانه
        )
        
        # ساخت پوشه اگر وجود نداره
        os.makedirs("./delivery_bot_data", exist_ok=True)
        
        # شروع ربات
        print("🔄 Connecting to Telegram...")
        await app.start()
        
        # دریافت اطلاعات ربات
        me = await app.get_me()
        
        print("✅ Delivery bot started successfully")
        print(f"🤖 Bot username: @{me.username}")
        print(f"📝 Bot name: {me.first_name}")
        print("⏳ Waiting for messages...")
        print("=" * 70)
        
        logger.info("✅ Delivery bot started successfully")
        logger.info(f"🤖 Bot username: @{me.username}")
        logger.info("⏳ Waiting for messages...")
        
        # شروع تسک پاکسازی
        cleanup = asyncio.create_task(cleanup_task())
        
        # نگه داشتن ربات
        from pyrogram import idle
        await idle()
        
        # توقف
        if cleanup:
            cleanup.cancel()
        if app:
            await app.stop()
        logger.info("Bot stopped")
    
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped by user")
        logger.info("Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Bot error: {e}")
        logger.error(f"Bot error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Cleanup
        if cleanup and not cleanup.done():
            cleanup.cancel()
        if app:
            try:
                await app.stop()
            except:
                pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
