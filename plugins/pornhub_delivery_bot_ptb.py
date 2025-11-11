"""
Pornhub Delivery Bot - نسخه python-telegram-bot
ربات دوم برای ارسال فایل‌ها با استفاده از PTB
"""

import os
import sys
import re
import json
import logging
from telegram import Update, ForceReply
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from telegram.constants import ParseMode

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

# تنظیمات ربات
DELIVERY_BOT_TOKEN = "8311578874:AAELkdM0t3DI_kQWXIAtIT4TeyMzZofCnyk"

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


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندلر دستور /start"""
    user = update.effective_user
    
    welcome_message = (
        f"👋 سلام {user.mention_html()}!\n\n"
        "🤖 به ربات ارسال فایل خوش آمدید!\n\n"
        "📝 <b>نحوه استفاده:</b>\n"
        "1️⃣ پیام حاوی کد فایل را از ربات اصلی فوروارد کنید\n"
        "2️⃣ فایل شما به صورت خودکار ارسال می‌شود\n\n"
        "🔑 <b>فرمت کد:</b> <code>FILE_XXXXXXXX</code>\n\n"
        "⚠️ <b>توجه:</b>\n"
        "• کدها فقط 24 ساعت معتبر هستند\n"
        "• هر کد فقط یک بار قابل استفاده است\n"
        "• فایل‌ها به صورت خودکار پاک می‌شوند\n\n"
        "💡 <b>راهنما:</b>\n"
        "• /start - نمایش این پیام\n"
        "• /help - راهنمای کامل\n"
        "• /status - وضعیت ربات\n\n"
        "✨ آماده دریافت کد فایل شما هستیم!"
    )
    
    await update.message.reply_html(welcome_message)
    logger.info(f"User {user.id} started the bot")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندلر دستور /help"""
    help_message = (
        "📚 <b>راهنمای کامل ربات</b>\n\n"
        "🎯 <b>هدف:</b>\n"
        "این ربات برای دریافت فایل‌های دانلود شده از ربات اصلی طراحی شده است.\n\n"
        "📝 <b>مراحل استفاده:</b>\n\n"
        "1️⃣ <b>دریافت کد:</b>\n"
        "   • در ربات اصلی لینک خود را ارسال کنید\n"
        "   • کیفیت مورد نظر را انتخاب کنید\n"
        "   • کد فایل را دریافت کنید\n\n"
        "2️⃣ <b>فوروارد پیام:</b>\n"
        "   • پیام حاوی کد را به این ربات فوروارد کنید\n"
        "   • یا کد را به صورت دستی ارسال کنید\n\n"
        "3️⃣ <b>دریافت فایل:</b>\n"
        "   • ربات خودکار فایل را برای شما ارسال می‌کند\n"
        "   • پیشرفت آپلود نمایش داده می‌شود\n\n"
        "⚠️ <b>نکات مهم:</b>\n"
        "• کدها 24 ساعت معتبرند\n"
        "• فایل‌های بزرگ ممکن است زمان بیشتری ببرند\n"
        "• در صورت خطا، دوباره تلاش کنید\n\n"
        "🔧 <b>دستورات:</b>\n"
        "/start - شروع ربات\n"
        "/help - این راهنما\n"
        "/status - وضعیت ربات\n\n"
        "💬 در صورت بروز مشکل با پشتیبانی تماس بگیرید."
    )
    
    await update.message.reply_html(help_message)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            "📊 <b>وضعیت ربات</b>\n\n"
            "✅ <b>ربات:</b> آنلاین و فعال\n"
            f"📁 <b>فایل‌های موجود:</b> {total_files}\n"
            f"✔️ <b>فایل‌های ارسال شده:</b> {downloaded_files}\n"
            f"⏳ <b>در انتظار:</b> {total_files - downloaded_files}\n\n"
            "🔄 <b>پاکسازی خودکار:</b> فعال (هر 6 ساعت)\n"
            "⏰ <b>مدت اعتبار:</b> 24 ساعت\n\n"
            "💚 همه چیز عالی کار می‌کند!"
        )
        
        await update.message.reply_html(status_message)
    
    except Exception as e:
        logger.error(f"Status command error: {e}")
        await update.message.reply_text("❌ خطا در دریافت وضعیت")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندلر اصلی برای پیام‌ها"""
    try:
        message = update.message
        text = message.text
        user_id = message.from_user.id
        
        logger.info(f"Received message from user {user_id}: {text[:50]}")
        
        # جستجوی کد فایل
        match = FILE_CODE_REGEX.search(text)
        
        if not match:
            # اگر کد نبود، پیام راهنما
            await message.reply_html(
                "❌ <b>کد فایل یافت نشد!</b>\n\n"
                "لطفاً پیام حاوی کد فایل را فوروارد کنید یا کد را به صورت دستی ارسال کنید.\n\n"
                "🔑 <b>فرمت صحیح:</b> <code>FILE_XXXXXXXX</code>\n\n"
                "💡 برای راهنما از دستور /help استفاده کنید."
            )
            return
        
        # استخراج کد
        file_code = match.group(1).upper()
        logger.info(f"File code detected: {file_code}")
        
        # پیام وضعیت
        status_msg = await message.reply_html(
            "🔍 <b>در حال بررسی کد...</b>\n\n⏳ لطفاً صبر کنید..."
        )
        
        # دریافت اطلاعات فایل
        file_info = pornhub_storage.get_file_info(file_code)
        
        if not file_info:
            await status_msg.edit_text(
                "❌ <b>کد نامعتبر یا منقضی شده</b>\n\n"
                "این کد وجود ندارد یا منقضی شده است.\n\n"
                "💡 <b>راهنمایی:</b>\n"
                "• کد را دوباره بررسی کنید\n"
                "• ممکن است 24 ساعت گذشته باشد\n"
                "• فایل جدید درخواست دهید",
                parse_mode=ParseMode.HTML
            )
            return
        
        # بررسی وجود فایل
        file_path = file_info.get('file_path')
        if not file_path or not os.path.exists(file_path):
            await status_msg.edit_text(
                "❌ <b>فایل یافت نشد</b>\n\n"
                "فایل از سرور حذف شده است.\n\n"
                "🔄 لطفاً فایل جدید درخواست دهید.",
                parse_mode=ParseMode.HTML
            )
            # حذف از storage
            pornhub_storage.delete_file(file_code)
            return
        
        # اطلاعات فایل
        title = file_info.get('title', 'Unknown')
        quality = file_info.get('quality', 'Unknown')
        file_size = file_info.get('file_size', 0)
        
        await status_msg.edit_text(
            f"📥 <b>فایل پیدا شد!</b>\n\n"
            f"🎬 {title[:50]}...\n"
            f"📊 کیفیت: {quality}p\n"
            f"💾 حجم: {format_size(file_size)}\n\n"
            f"⏳ در حال آماده‌سازی...",
            parse_mode=ParseMode.HTML
        )
        
        # ارسال فایل
        try:
            logger.info(f"Starting upload for file: {file_path}")
            
            # Caption
            caption = f"🎬 {title}\n📊 کیفیت: {quality}p"
            
            # آپدیت پیام
            await status_msg.edit_text(
                f"📤 <b>در حال ارسال...</b>\n\n"
                f"🎬 {title[:50]}...\n"
                f"💾 {format_size(file_size)}\n\n"
                f"⏳ لطفاً صبر کنید...",
                parse_mode=ParseMode.HTML
            )
            
            # استخراج metadata ویدیو
            duration = None
            width = None
            height = None
            thumbnail = None
            
            try:
                # بررسی thumbnail از تنظیمات ادمین
                from plugins.adult_content_admin import get_thumbnail_path
                admin_thumb = get_thumbnail_path()
                if admin_thumb and os.path.exists(admin_thumb):
                    thumbnail = admin_thumb
                    logger.info(f"Using admin thumbnail: {admin_thumb}")
            except Exception as e:
                logger.debug(f"No admin thumbnail: {e}")
            
            try:
                # استخراج metadata با ffprobe
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
                    if 'format' in metadata:
                        duration = int(float(metadata['format'].get('duration', 0)))
                    
                    # Width & Height
                    for stream in metadata.get('streams', []):
                        if stream.get('codec_type') == 'video':
                            width = stream.get('width')
                            height = stream.get('height')
                            break
                    
                    logger.info(f"Video metadata: duration={duration}s, {width}x{height}")
            except Exception as e:
                logger.debug(f"Could not extract metadata: {e}")
            
            # ارسال فایل با metadata
            with open(file_path, 'rb') as video_file:
                await message.reply_video(
                    video=video_file,
                    caption=caption,
                    duration=duration,
                    width=width,
                    height=height,
                    thumb=thumbnail,
                    supports_streaming=True,
                    read_timeout=300,
                    write_timeout=300,
                    connect_timeout=60
                )
            
            # حذف پیام وضعیت
            await status_msg.delete()
            
            # علامت‌گذاری به عنوان دریافت شده
            pornhub_storage.mark_as_downloaded(file_code)
            
            logger.info(f"File {file_code} sent successfully to user {user_id}")
            
            # پیام موفقیت
            await message.reply_html(
                "✅ <b>فایل با موفقیت ارسال شد!</b>\n\n"
                "🎉 از استفاده شما متشکریم.\n\n"
                "💡 برای دریافت فایل‌های بیشتر، کد جدید ارسال کنید."
            )
        
        except Exception as upload_error:
            logger.error(f"Upload error: {upload_error}")
            await status_msg.edit_text(
                f"❌ <b>خطا در ارسال فایل</b>\n\n"
                f"خطا: {str(upload_error)[:100]}\n\n"
                f"🔄 لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید.",
                parse_mode=ParseMode.HTML
            )
    
    except Exception as e:
        logger.error(f"Handler error: {e}", exc_info=True)
        try:
            await update.message.reply_html(
                "❌ <b>خطای غیرمنتظره</b>\n\n"
                "لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."
            )
        except:
            pass


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندلر خطاها"""
    logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)


def main() -> None:
    """تابع اصلی"""
    try:
        print("=" * 70)
        print("🚀 Starting Pornhub Delivery Bot (PTB Version)")
        print("=" * 70)
        print()
        
        # ساخت application
        application = Application.builder().token(DELIVERY_BOT_TOKEN).build()
        
        # اضافه کردن هندلرها
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # هندلر خطا
        application.add_error_handler(error_handler)
        
        print("✅ Bot initialized successfully")
        print("🤖 Bot username: @wwwiranbot")
        print("⏳ Starting polling...")
        print("=" * 70)
        print()
        
        logger.info("✅ Delivery bot started successfully")
        logger.info("🤖 Bot username: @wwwiranbot")
        logger.info("⏳ Starting polling...")
        
        # شروع polling
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped by user")
        logger.info("Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Bot error: {e}")
        logger.error(f"Bot error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
