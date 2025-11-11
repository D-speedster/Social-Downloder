"""
Adult Content Admin Panel - پنل ادمین برای تنظیمات محتوای بزرگسال
"""

import os
import json
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from plugins.logger_config import get_logger

logger = get_logger('adult_content_admin')

# مسیر فایل تنظیمات
SETTINGS_FILE = "data/adult_content_settings.json"

# شناسه ادمین (باید از config بیاد)
try:
    from plugins.admin import ADMIN
    ADMIN_ID = ADMIN
except:
    ADMIN_ID = 79049016  # پیش‌فرض


def load_settings() -> dict:
    """بارگذاری تنظیمات"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'thumbnail_path': None,
            'enabled': True
        }
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        return {'thumbnail_path': None, 'enabled': True}


def save_settings(settings: dict):
    """ذخیره تنظیمات"""
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        logger.info("Settings saved successfully")
    except Exception as e:
        logger.error(f"Error saving settings: {e}")


def get_thumbnail_path() -> str:
    """دریافت مسیر thumbnail"""
    settings = load_settings()
    return settings.get('thumbnail_path')


@Client.on_message(filters.command("adult_admin") & filters.user(ADMIN_ID))
async def adult_admin_panel(client: Client, message: Message):
    """پنل ادمین محتوای بزرگسال"""
    settings = load_settings()
    
    thumbnail_status = "✅ تنظیم شده" if settings.get('thumbnail_path') else "❌ تنظیم نشده"
    enabled_status = "✅ فعال" if settings.get('enabled') else "❌ غیرفعال"
    
    text = (
        "🔞 <b>پنل مدیریت محتوای بزرگسال</b>\n\n"
        f"📸 <b>Thumbnail:</b> {thumbnail_status}\n"
        f"🔧 <b>وضعیت:</b> {enabled_status}\n\n"
        "⚙️ <b>تنظیمات:</b>\n"
        "• برای تنظیم thumbnail، یک عکس ارسال کنید\n"
        "• thumbnail روی تمام ویدیوها اعمال می‌شود\n"
        "• برای حذف thumbnail از دکمه زیر استفاده کنید"
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📸 تنظیم Thumbnail", callback_data="adult_set_thumb"),
            InlineKeyboardButton("🗑 حذف Thumbnail", callback_data="adult_del_thumb")
        ],
        [
            InlineKeyboardButton(
                "✅ فعال" if not settings.get('enabled') else "❌ غیرفعال",
                callback_data="adult_toggle"
            )
        ],
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data="adult_refresh")]
    ])
    
    await message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


@Client.on_callback_query(filters.regex(r'^adult_'))
async def adult_admin_callback(client: Client, callback: CallbackQuery):
    """هندلر callback های پنل ادمین"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ فقط ادمین دسترسی دارد", show_alert=True)
        return
    
    data = callback.data
    settings = load_settings()
    
    if data == "adult_set_thumb":
        await callback.answer("📸 لطفاً یک عکس ارسال کنید", show_alert=True)
        await callback.message.reply_text(
            "📸 <b>تنظیم Thumbnail</b>\n\n"
            "لطفاً عکس مورد نظر را ارسال کنید.\n"
            "این عکس روی تمام ویدیوهای بزرگسال اعمال خواهد شد.",
            parse_mode=ParseMode.HTML
        )
    
    elif data == "adult_del_thumb":
        old_path = settings.get('thumbnail_path')
        if old_path and os.path.exists(old_path):
            try:
                os.unlink(old_path)
            except:
                pass
        
        settings['thumbnail_path'] = None
        save_settings(settings)
        
        await callback.answer("✅ Thumbnail حذف شد", show_alert=True)
        await adult_admin_panel(client, callback.message)
    
    elif data == "adult_toggle":
        settings['enabled'] = not settings.get('enabled', True)
        save_settings(settings)
        
        status = "فعال" if settings['enabled'] else "غیرفعال"
        await callback.answer(f"✅ وضعیت: {status}", show_alert=True)
        await adult_admin_panel(client, callback.message)
    
    elif data == "adult_refresh":
        await callback.answer("🔄 بروزرسانی شد")
        await adult_admin_panel(client, callback.message)


@Client.on_message(filters.photo & filters.user(ADMIN_ID) & filters.private)
async def handle_thumbnail_upload(client: Client, message: Message):
    """دریافت thumbnail از ادمین"""
    try:
        # دانلود عکس
        photo = message.photo
        file_path = f"data/adult_thumbnail_{photo.file_id}.jpg"
        
        await message.reply_text("⏳ در حال دانلود عکس...")
        
        downloaded = await client.download_media(photo.file_id, file_name=file_path)
        
        if downloaded:
            # حذف thumbnail قبلی
            settings = load_settings()
            old_path = settings.get('thumbnail_path')
            if old_path and os.path.exists(old_path) and old_path != downloaded:
                try:
                    os.unlink(old_path)
                except:
                    pass
            
            # ذخیره تنظیمات جدید
            settings['thumbnail_path'] = downloaded
            save_settings(settings)
            
            await message.reply_text(
                "✅ <b>Thumbnail با موفقیت تنظیم شد!</b>\n\n"
                "این عکس روی تمام ویدیوهای بزرگسال اعمال خواهد شد.",
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Thumbnail set: {downloaded}")
        else:
            await message.reply_text("❌ خطا در دانلود عکس")
    
    except Exception as e:
        logger.error(f"Error handling thumbnail: {e}")
        await message.reply_text(f"❌ خطا: {str(e)}")
