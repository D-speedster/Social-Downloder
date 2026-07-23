"""
🔧 رفع مشکلات پنل ادمین
این فایل شامل کدهای بهبود یافته برای جایگزینی در admin.py است
"""

import asyncio
import time
import shutil
import os
import json
from pyrogram.types import Message

# ============================================
# 1️⃣ رفع مشکل Race Condition در تنظیم اسپانسر
# ============================================

# Global lock برای جلوگیری از race condition
_json_write_lock = asyncio.Lock()

async def set_sponsor_safe(client, message: Message, val: str, data: dict, admin_logger):
    """
    تنظیم اسپانسر با validation و thread-safety کامل
    
    Args:
        client: Pyrogram client
        message: پیام کاربر
        val: مقدار اسپانسر (@username یا -100...)
        data: دیکشنری data
        admin_logger: logger
    """
    user_id = message.from_user.id
    
    # ✅ Validation: بررسی دسترسی به کانال
    try:
        status_msg = await message.reply_text("🔄 در حال بررسی دسترسی...")
        
        try:
            # دریافت اطلاعات کانال
            chat = await client.get_chat(val)
            
            # بررسی اینکه ربات عضو و ادمین است
            try:
                bot_member = await client.get_chat_member(val, "me")
                if bot_member.status not in ["administrator", "creator"]:
                    await status_msg.edit_text(
                        "❌ ربات در این کانال ادمین نیست!\n\n"
                        "لطفاً ابتدا ربات را در کانال ادمین کنید."
                    )
                    return False
            except Exception:
                await status_msg.edit_text(
                    "❌ ربات در این کانال عضو نیست!\n\n"
                    "لطفاً ابتدا ربات را به کانال اضافه کنید."
                )
                return False
            
            await status_msg.edit_text("✅ دسترسی تأیید شد. در حال ذخیره...")
            
        except Exception as e:
            await status_msg.edit_text(
                f"❌ خطا در دسترسی به کانال!\n\n"
                f"لطفاً مطمئن شوید:\n"
                f"• شناسه کانال صحیح است\n"
                f"• ربات در کانال عضو است\n"
                f"• ربات ادمین است\n\n"
                f"خطا: {str(e)[:100]}"
            )
            return False
    
    except Exception as e:
        await message.reply_text(f"❌ خطا در بررسی دسترسی: {e}")
        return False
    
    # ✅ Thread-safe write با lock
    async with _json_write_lock:
        try:
            from plugins.db_path_manager import db_path_manager
            json_db_path = db_path_manager.get_json_db_path()
            
            # ✅ Backup قبل از نوشتن
            backup_path = json_db_path + '.bak'
            if os.path.exists(json_db_path):
                shutil.copy2(json_db_path, backup_path)
            
            # ✅ Read-Modify-Write pattern
            with open(json_db_path, 'r', encoding='utf-8') as f:
                current_data = json.load(f)
            
            current_data['sponser'] = val
            
            # ✅ Atomic write
            temp_path = json_db_path + '.tmp'
            with open(temp_path, 'w', encoding='utf-8') as outfile:
                json.dump(current_data, outfile, indent=4, ensure_ascii=False)
            
            # ✅ Atomic rename
            os.replace(temp_path, json_db_path)
            
            # ✅ Update in-memory data
            data['sponser'] = val
            
            # ✅ Log
            admin_logger.info(f"[ADMIN] Sponsor set by {user_id}: {val}")
            
            await status_msg.edit_text(
                f"✅ اسپانسر با موفقیت تنظیم شد!\n\n"
                f"کانال: {val}\n"
                f"نام: {chat.title if hasattr(chat, 'title') else 'نامشخص'}"
            )
            
            return True
            
        except Exception as e:
            # ✅ Restore backup در صورت خطا
            admin_logger.error(f"[ADMIN] Error setting sponsor: {e}")
            try:
                if os.path.exists(backup_path):
                    shutil.copy2(backup_path, json_db_path)
            except Exception:
                pass
            
            await message.reply_text(f"❌ خطا در ذخیره: {e}")
            return False


# ============================================
# 2️⃣ رفع مشکل State Management در تبلیغات
# ============================================

class AdminUserState:
    """State management برای هر ادمین"""
    def __init__(self, user_id):
        self.user_id = user_id
        self.advertisement = {
            'step': 0,
            'content_type': '',
            'file_id': '',
            'caption': '',
            'text': ''
        }
        self.created_at = time.time()
        self.timeout = 300  # 5 minutes
    
    def is_expired(self):
        return time.time() - self.created_at > self.timeout
    
    def reset_advertisement(self):
        self.advertisement = {
            'step': 0,
            'content_type': '',
            'file_id': '',
            'caption': '',
            'text': ''
        }
        self.created_at = time.time()


# Global per-user states
admin_user_states = {}

def get_admin_user_state(user_id) -> AdminUserState:
    """Get or create admin state for user"""
    if user_id not in admin_user_states:
        admin_user_states[user_id] = AdminUserState(user_id)
    
    state = admin_user_states[user_id]
    
    # ✅ Auto-reset expired states
    if state.is_expired():
        state.reset_advertisement()
    
    return state


# ============================================
# 3️⃣ Validation محتوای تبلیغات
# ============================================

async def validate_ad_content(message: Message) -> tuple:
    """
    Validate advertisement content
    
    Returns:
        (is_valid, error_message)
    """
    # ✅ Text validation
    if message.text:
        if len(message.text) > 4096:
            return False, "❌ متن تبلیغات نباید بیشتر از 4096 کاراکتر باشد."
        return True, ""
    
    # ✅ Photo validation
    if message.photo:
        file_size = message.photo.file_size or 0
        if file_size > 10 * 1024 * 1024:  # 10 MB
            return False, "❌ حجم عکس نباید بیشتر از 10 MB باشد."
        return True, ""
    
    # ✅ Video validation
    if message.video:
        file_size = message.video.file_size or 0
        if file_size > 50 * 1024 * 1024:  # 50 MB
            return False, "❌ حجم ویدیو نباید بیشتر از 50 MB باشد."
        duration = message.video.duration or 0
        if duration > 60:  # 1 minute
            return False, "❌ مدت زمان ویدیو نباید بیشتر از 1 دقیقه باشد."
        return True, ""
    
    # ✅ Animation (GIF) validation
    if message.animation:
        file_size = message.animation.file_size or 0
        if file_size > 10 * 1024 * 1024:  # 10 MB
            return False, "❌ حجم GIF نباید بیشتر از 10 MB باشد."
        return True, ""
    
    # ✅ Audio validation
    if message.audio:
        file_size = message.audio.file_size or 0
        if file_size > 50 * 1024 * 1024:  # 50 MB
            return False, "❌ حجم موزیک نباید بیشتر از 50 MB باشد."
        return True, ""
    
    # ✅ Sticker validation
    if message.sticker:
        return True, ""
    
    return False, "❌ نوع محتوای ارسالی پشتیبانی نمی‌شود."


# ============================================
# 4️⃣ ذخیره امن تنظیمات تبلیغات
# ============================================

async def save_advertisement_safe(ad_settings: dict, data: dict, admin_logger) -> bool:
    """
    ذخیره امن تنظیمات تبلیغات با backup و atomic write
    
    Args:
        ad_settings: تنظیمات تبلیغات
        data: دیکشنری data
        admin_logger: logger
    
    Returns:
        bool: موفقیت یا عدم موفقیت
    """
    async with _json_write_lock:
        try:
            from plugins.db_path_manager import db_path_manager
            json_db_path = db_path_manager.get_json_db_path()
            
            # ✅ Backup
            backup_path = json_db_path + '.bak'
            if os.path.exists(json_db_path):
                shutil.copy2(json_db_path, backup_path)
            
            # ✅ Read-Modify-Write
            with open(json_db_path, 'r', encoding='utf-8') as f:
                current_data = json.load(f)
            
            current_data['advertisement'] = ad_settings
            
            # ✅ Atomic write
            temp_path = json_db_path + '.tmp'
            with open(temp_path, 'w', encoding='utf-8') as outfile:
                json.dump(current_data, outfile, indent=4, ensure_ascii=False)
            
            os.replace(temp_path, json_db_path)
            
            # ✅ Update in-memory
            data['advertisement'] = ad_settings
            
            admin_logger.info(f"[ADMIN] Advertisement settings saved")
            return True
            
        except Exception as e:
            admin_logger.error(f"[ADMIN] Error saving advertisement: {e}")
            # ✅ Restore backup
            try:
                if os.path.exists(backup_path):
                    shutil.copy2(backup_path, json_db_path)
            except Exception:
                pass
            return False


# ============================================
# 5️⃣ Rate Limiting برای ارسال همگانی
# ============================================

BROADCAST_DELAY = 0.05  # 50ms delay بین هر ارسال
BROADCAST_BATCH_SIZE = 20  # هر 20 ارسال، 1 ثانیه صبر

async def broadcast_with_rate_limit(client, users, content, broadcast_type, callback_query, admin_logger):
    """
    ارسال همگانی با rate limiting
    
    Args:
        client: Pyrogram client
        users: لیست کاربران
        content: محتوای پیام
        broadcast_type: نوع ارسال ('normal' یا 'forward')
        callback_query: callback query برای update
        admin_logger: logger
    """
    import time
    
    total = len(users)
    sent = 0
    fail = 0
    start_time = time.time()
    last_update_time = start_time
    
    # Update initial message
    await callback_query.edit_message_text(
        f"📤 در حال ارسال به {total} کاربر...\n\n"
        f"✅ ارسال شده: 0\n"
        f"❌ ناموفق: 0\n"
        f"📊 پیشرفت: 0/{total} (0.0%)\n"
        f"⏱ زمان سپری شده: 0 ثانیه",
        reply_markup=None
    )
    
    for i, user in enumerate(users):
        uid = user[0] if isinstance(user, (list, tuple)) else user
        
        try:
            if broadcast_type == 'forward':
                await client.forward_messages(
                    chat_id=uid,
                    from_chat_id=content['chat_id'],
                    message_ids=content['message_id']
                )
            else:
                await client.copy_message(
                    chat_id=uid,
                    from_chat_id=content['chat_id'],
                    message_id=content['message_id']
                )
            sent += 1
        except Exception as e:
            fail += 1
            admin_logger.debug(f"[BROADCAST] Failed to send to {uid}: {e}")
        
        # ✅ Rate limiting
        await asyncio.sleep(BROADCAST_DELAY)
        
        # ✅ Batch delay
        if (i + 1) % BROADCAST_BATCH_SIZE == 0:
            await asyncio.sleep(1.0)
        
        # Update progress every 10 seconds
        current_time = time.time()
        if current_time - last_update_time >= 10.0:
            elapsed_time = int(current_time - start_time)
            progress_percent = ((i + 1) / total) * 100
            
            try:
                await callback_query.edit_message_text(
                    f"📤 در حال ارسال به {total} کاربر...\n\n"
                    f"✅ ارسال شده: {sent}\n"
                    f"❌ ناموفق: {fail}\n"
                    f"📊 پیشرفت: {i + 1}/{total} ({progress_percent:.1f}%)\n"
                    f"⏱ زمان سپری شده: {elapsed_time} ثانیه"
                )
                last_update_time = current_time
            except Exception:
                pass
    
    # Final result
    final_time = time.time()
    total_elapsed = int(final_time - start_time)
    rate = sent / total_elapsed if total_elapsed > 0 else 0
    
    try:
        await callback_query.edit_message_text(
            f"🎉 **ارسال همگانی تکمیل شد!**\n\n"
            f"📊 **نتایج نهایی:**\n"
            f"✅ ارسال موفق: {sent}\n"
            f"❌ ارسال ناموفق: {fail}\n"
            f"👥 مجموع کاربران: {total}\n\n"
            f"📈 نرخ موفقیت: {(sent/total*100):.1f}%\n" if total > 0 else "📈 نرخ موفقیت: 0%\n"
            f"⏱ زمان کل: {total_elapsed} ثانیه\n"
            f"🚀 سرعت ارسال: {rate:.1f} پیام/ثانیه"
        )
    except Exception:
        pass
    
    admin_logger.info(f"[BROADCAST] Completed: {sent} sent, {fail} failed, {total_elapsed}s")
    
    return sent, fail


print("✅ Admin fixes module loaded")
print("   - Thread-safe sponsor setting")
print("   - Per-user state management")
print("   - Content validation")
print("   - Rate-limited broadcast")
