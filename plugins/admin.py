import time
import logging

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
import json, os
from pyrogram import Client, filters
import re
from pyrogram.types import Message, CallbackQuery
from pyrogram.errors import FloodWait
import sys, requests
# Fix #5: Remove unused imports (instaloader)
from datetime import datetime as _dt
from plugins import constant
from plugins.db_wrapper import DB
from plugins.admin_statistics import (
    StatisticsCalculator, 
    StatisticsFormatter,
    get_cached_stats,
    set_cached_stats,
    clear_stats_cache
)

import shutil, platform, asyncio, os as _os
import psutil
import subprocess

# Fix #24: Safe directory creation with error handling
try:
    os.makedirs('./logs', exist_ok=True)
except Exception as e:
    # Fix #7: Use logging instead of print for warnings
    import sys
    sys.stderr.write(f"Warning: Could not create logs directory: {e}\n")
admin_logger = logging.getLogger('admin_main')
admin_logger.setLevel(logging.DEBUG)

admin_handler = logging.FileHandler('./logs/admin_main.log', encoding='utf-8')
admin_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
admin_handler.setFormatter(admin_formatter)
admin_logger.addHandler(admin_handler)

PATH = constant.PATH
txt = constant.TEXT
data = constant.DATA

ADMIN = [79049016 , 429273267 , 528815211]  # شناسه کاربری خود را اینجا اضافه کنید

# برای پیدا کردن شناسه کاربری خود:
# 1. ربات را اجرا کنید
# 2. /start را ارسال کنید  
# 3. در لاگ‌های ربات، شناسه کاربری شما نمایش داده می‌شود
# 4. آن را به لیست بالا اضافه کنید: ADMIN = [79049016, YOUR_USER_ID]

# Track bot start time for uptime
START_TIME = _dt.now()

# Fix #1: Per-user state management instead of global admin_step
# Global admin_step is deprecated - use get_admin_user_state() instead
admin_step = {
    'sp': 2,  # Legacy - to be migrated
    'broadcast': 0,
    'broadcast_type': '',
    'manual_recovery': 0,
    'broadcast_content': None,
    'waiting_msg': 0,
    'waiting_msg_type': '',
    'waiting_msg_platform': '',
    'advertisement': 0,
    'ad_content_type': '',
    'ad_file_id': '',
    'ad_caption': '',
}

# ✅ Per-user state management برای جلوگیری از conflict
admin_user_states = {}  # {user_id: {'advertisement': {...}, 'created_at': ...}}

class AdminUserState:
    """
    Fix #1: Per-user state management for all admin operations
    Prevents conflicts when multiple admins use the bot simultaneously
    """
    def __init__(self, user_id):
        self.user_id = user_id
        # Advertisement state
        self.advertisement = {
            'step': 0,
            'content_type': '',
            'file_id': '',
            'caption': '',
            'text': ''
        }
        # Manual recovery state
        self.manual_recovery = {
            'step': 0,  # 0: idle, 1: waiting for minutes
            'minutes': 0
        }
        # Broadcast state
        self.broadcast = {
            'step': 0,  # 0: idle, 1: choosing type, 2: waiting for content, 3: waiting for confirmation
            'type': '',  # 'normal' or 'forward'
            'content': None
        }
        # Waiting message state
        self.waiting_msg = {
            'step': 0,
            'type': '',
            'platform': ''
        }
        # Adult content thumbnail state
        self.waiting_adult_thumb = False
        # Sponsor setup state
        self.sponsor = {
            'step': 0  # 0: idle, 1: waiting for input
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
    
    def reset_manual_recovery(self):
        """Fix #2: Reset manual recovery state"""
        self.manual_recovery = {
            'step': 0,
            'minutes': 0
        }
        self.created_at = time.time()
    
    def reset_broadcast(self):
        """Reset broadcast state"""
        self.broadcast = {
            'step': 0,
            'type': '',
            'content': None
        }
        self.created_at = time.time()
    
    def reset_all(self):
        """Reset all states"""
        self.reset_advertisement()
        self.reset_manual_recovery()
        self.reset_broadcast()
        self.waiting_msg = {'step': 0, 'type': '', 'platform': ''}
        self.sponsor = {'step': 0}

def get_admin_user_state(user_id) -> AdminUserState:
    """Get or create admin state for user"""
    if user_id not in admin_user_states:
        admin_user_states[user_id] = AdminUserState(user_id)
    
    state = admin_user_states[user_id]
    
    # ✅ Auto-reset expired states
    if state.is_expired():
        state.reset_advertisement()
    
    return state

insta = {'level': 0, 'id': "default", 'pass': "defult"}


# Build Admin keyboard dynamically (5 sections)

def admin_inline_maker() -> list:
    power_state = data.get('bot_status', 'ON')
    power_label = f"قدرت: {('🔴 OFF' if power_state == 'OFF' else '🟢 ON')}"
    fj_label = f"قفل عضویت: {'🟢 روشن' if data.get('force_join', True) else '🔴 خاموش'}"
    
    return [
        [
            InlineKeyboardButton("📊 آمار کاربران", callback_data='st'),
            InlineKeyboardButton("🖥 وضعیت سرور", callback_data='srv'),
        ],
        [
            InlineKeyboardButton("📣 ارسال پیام", callback_data='gm'),
            InlineKeyboardButton(txt.get('sponser', 'اسپانسر'), callback_data='sp'),
        ],
        [
            InlineKeyboardButton("💬 پیام انتظار", callback_data='waiting_msg'),
            InlineKeyboardButton("📋 صف درخواست‌ها", callback_data='failed_queue'),
        ],
        [
            InlineKeyboardButton("🍪 مدیریت کوکی", callback_data='cookie_mgmt'),
            InlineKeyboardButton("🔞 تنظیم Thumbnail", callback_data='adult_thumb'),
        ],
        [
            InlineKeyboardButton("✅ بررسی کانال", callback_data='sp_check'),
            InlineKeyboardButton(fj_label, callback_data='fj_toggle'),
        ],
        [
            InlineKeyboardButton(power_label, callback_data='pw'),
        ],
    ]


def admin_reply_kb() -> ReplyKeyboardMarkup:
    """
    کیبورد پنل ادمین با دکمه‌های ثابت
    """
    return ReplyKeyboardMarkup(
        [
            ["📊 آمار کاربران", "🖥 وضعیت سرور"],
            ["📢 ارسال همگانی", "📢 تنظیم اسپانسر"],
            ["💬 پیام انتظار", "🍪 مدیریت کوکی"],
            ["📺 تنظیم تبلیغات", "✅ وضعیت ربات"],
            ["📨 پیام‌های آفلاین", "📋 صف درخواست‌ها"],
            ["🔞 تنظیم Thumbnail", "📘 تنظیم راهنما"],
            ["⬅️ بازگشت"],
        ],
        resize_keyboard=True
    )


@Client.on_message(filters.user(ADMIN) & filters.regex(r'^🛠 مدیریت$'))
async def admin_menu_root_msg(_: Client, message: Message):
    admin_logger.info(f"[ADMIN] open management via text by {message.from_user.id}")
    await message.reply_text("پنل مدیریت", reply_markup=admin_reply_kb())


@Client.on_message(filters.user(ADMIN) & filters.regex(r'^📊 آمار کاربران$'))
async def admin_menu_stats(client: Client, message: Message):
    """نمایش صفحه Overview آمار"""
    admin_logger.info(f"[ADMIN] stats overview via text by {message.from_user.id}")
    
    try:
        # بررسی cache
        cached = get_cached_stats('overview')
        if cached:
            stats = cached
        else:
            # محاسبه آمار
            db = DB()
            calculator = StatisticsCalculator(db)
            stats = calculator.calculate_overview_stats()
            set_cached_stats('overview', stats)
        
        # فرمت کردن
        text = StatisticsFormatter.format_overview_stats(stats)
        
        # کیبورد با دسترسی به آمار تفصیلی
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("👥 جزئیات کاربران", callback_data='stats_users'),
                InlineKeyboardButton("📈 جزئیات درخواست‌ها", callback_data='stats_requests')
            ],
            [
                InlineKeyboardButton("⚡ جزئیات عملکرد", callback_data='stats_performance'),
                InlineKeyboardButton("🔄 بروزرسانی", callback_data='stats_refresh_overview')
            ],
            [
                InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_admin')
            ]
        ])
        
        await message.reply_text(text, reply_markup=keyboard)
        admin_logger.info(f"[ADMIN] Overview stats displayed to {message.from_user.id}")
    
    except Exception as e:
        admin_logger.error(f"Error in admin_menu_stats: {e}")
        await message.reply_text("❌ خطا در دریافت آمار")
    
    return


@Client.on_message(filters.user(ADMIN) & filters.regex(r'^🖥 وضعیت سرور$'))
async def admin_menu_server(_: Client, message: Message):
    admin_logger.info(f"[ADMIN] server status via text by {message.from_user.id}")
    await message.reply_text(_server_status_text(), reply_markup=admin_reply_kb())


@Client.on_message(filters.command('health') & filters.user(ADMIN))
async def health_check_cmd(_: Client, message: Message):
    """دستور بررسی سلامت سیستم"""
    try:
        from plugins.health_monitor import get_health_monitor
        monitor = get_health_monitor()
        
        if not monitor:
            await message.reply_text("⚠️ Health Monitor فعال نیست")
            return
        
        report = monitor.get_status_report()
        await message.reply_text(report)
    except Exception as e:
        await message.reply_text(f"❌ خطا در دریافت گزارش سلامت: {e}")


@Client.on_message(filters.command('clearalerts') & filters.user(ADMIN))
async def clear_alerts_cmd(_: Client, message: Message):
    """پاک کردن cooldown هشدارها (برای تست)"""
    try:
        from plugins.health_monitor import get_health_monitor
        monitor = get_health_monitor()
        
        if not monitor:
            await message.reply_text("⚠️ Health Monitor فعال نیست")
            return
        
        # پاک کردن تمام cooldowns
        count = len(monitor.alerts_sent)
        monitor.alerts_sent.clear()
        
        await message.reply_text(f"✅ {count} cooldown پاک شد\n\nهشدارها اکنون می‌توانند دوباره ارسال شوند.")
    except Exception as e:
        await message.reply_text(f"❌ خطا: {e}")


# 📨 Manual Recovery System
@Client.on_message(filters.user(ADMIN) & filters.regex(r'^📨 پیام‌های آفلاین$'))
async def manual_recovery_menu(_: Client, message: Message):
    """منوی بازیابی دستی پیام‌ها"""
    user_id = message.from_user.id
    admin_logger.info(f"[ADMIN] manual recovery menu opened by {user_id}")
    
    # Reset state
    admin_step['manual_recovery'] = 1
    
    text = (
        "📨 **بازیابی پیام‌های آفلاین**\n\n"
        "این قابلیت به شما اجازه می‌دهد پیام‌های کاربرانی که\n"
        "در زمان آفلاین بودن ربات ارسال کرده‌اند را بازیابی کنید.\n\n"
        "⏱ **چند دقیقه قبل را بررسی کنم؟**\n\n"
        "💡 **راهنما:**\n"
        "• حداقل: 1 دقیقه\n"
        "• حداکثر: 1440 دقیقه (24 ساعت)\n"
        "• مثال: 30 (برای 30 دقیقه اخیر)\n\n"
        "📝 **لطفاً عدد را وارد کنید:**"
    )
    
    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ لغو", callback_data="cancel_recovery")
        ]])
    )


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^cancel_recovery$'))
async def cancel_recovery_cb(_: Client, callback_query: CallbackQuery):
    """لغو بازیابی"""
    admin_step['manual_recovery'] = 0
    await callback_query.message.edit_text(
        "❌ بازیابی لغو شد",
        reply_markup=None
    )
    await callback_query.answer()


# Handler برای دریافت تعداد دقیقه
# Fix #3: Improved filter to avoid conflicts with admin buttons
def recovery_filter_func(_, __, m):
    """
    Fix #3 & #15: Better filter for recovery input
    - Checks admin_step state
    - Excludes admin buttons
    - Excludes commands
    """
    if admin_step.get('manual_recovery') != 1:
        return False
    if not m.text:
        return False
    text = m.text.strip()
    # Fix #3: Exclude admin panel buttons
    admin_buttons = {
        '⬅️ بازگشت', '❌ لغو', '📨 پیام‌های آفلاین', '🛠 مدیریت',
        '📊 آمار کاربران', '🖥 وضعیت سرور', '📢 ارسال همگانی',
        '📢 تنظیم اسپانسر', '💬 پیام انتظار', '🍪 مدیریت کوکی',
        '📺 تنظیم تبلیغات', '✅ وضعیت ربات', '📋 صف درخواست‌ها',
        '📘 تنظیم راهنما', '🔞 تنظیم Thumbnail'
    }
    if text in admin_buttons:
        return False
    # Fix #16: Exclude /cancel command
    if text.startswith('/'):
        return False
    return True

recovery_filter = filters.create(recovery_filter_func)

@Client.on_message(recovery_filter & filters.user(ADMIN), group=15)
async def handle_recovery_minutes(client: Client, message: Message):
    """
    دریافت تعداد دقیقه و شروع بازیابی
    Fix #13: Use finally to ensure state reset
    Fix #16: Handle /cancel command
    """
    user_id = message.from_user.id
    
    try:
        # پارس کردن عدد
        text = message.text.strip()
        
        # Fix #16: Handle cancel command
        if text == '/cancel' or text.lower() == 'cancel':
            admin_step['manual_recovery'] = 0
            state = get_admin_user_state(user_id)
            state.reset_manual_recovery()
            await message.reply_text("❌ بازیابی لغو شد")
            return
        
        # نادیده گرفتن پیام‌های خاص (already filtered, but double-check)
        if text in ['📨 پیام‌های آفلاین', '⬅️ بازگشت', '🛠 مدیریت']:
            return
        
        minutes = int(text)
        
        # اعتبارسنجی
        if minutes < 1 or minutes > 1440:
            await message.reply_text(
                "❌ **عدد نامعتبر**\n\n"
                "لطفاً عددی بین 1 تا 1440 وارد کنید."
            )
            return
        
        # شروع بازیابی
        from config import BOT_TOKEN
        from plugins.manual_recovery import manual_recover_messages
        
        status_msg = await message.reply_text(
            f"🔄 **شروع بازیابی**\n\n"
            f"⏱ بازه زمانی: {minutes} دقیقه اخیر\n"
            f"⏳ لطفاً صبر کنید...\n\n"
            f"💡 این ممکن است چند دقیقه طول بکشد."
        )
        
        # Fix #8 & #14: Run as background task with timeout
        try:
            # اجرای بازیابی با timeout
            result = await asyncio.wait_for(
                manual_recover_messages(client, BOT_TOKEN, minutes, user_id),
                timeout=600  # 10 minutes max
            )
            
            if not result.get('success'):
                await status_msg.edit_text(
                    f"❌ **خطا در بازیابی**\n\n"
                    f"{result.get('message', 'خطای نامشخص')}"
                )
        except asyncio.TimeoutError:
            await status_msg.edit_text(
                "⏱ **زمان بازیابی تمام شد**\n\n"
                "عملیات بیش از 10 دقیقه طول کشید و متوقف شد.\n"
                "لطفاً بازه زمانی کوچک‌تری انتخاب کنید."
            )
            admin_logger.warning(f"Manual recovery timeout for user {user_id}, minutes={minutes}")
        
    except ValueError:
        await message.reply_text(
            "❌ **فرمت نامعتبر**\n\n"
            "لطفاً فقط عدد وارد کنید.\n"
            "مثال: 30"
        )
        # Don't reset state - allow retry
        return
    
    except Exception as e:
        admin_logger.error(f"Error in manual recovery: {e}")
        await message.reply_text(f"❌ خطا: {str(e)[:200]}")
    
    finally:
        # Fix #13: Always reset state in finally block
        admin_step['manual_recovery'] = 0
        state = get_admin_user_state(user_id)
        state.reset_manual_recovery()


@Client.on_message(filters.command('recovery') & filters.user(ADMIN))
async def recovery_stats_cmd(_: Client, message: Message):
    """دستور بررسی آمار بازیابی پیام‌ها"""
    try:
        from plugins.message_recovery import get_recovery_stats
        stats = get_recovery_stats()
        
        if not stats:
            await message.reply_text("⚠️ آماری یافت نشد")
            return
        
        text = "🔄 **آمار بازیابی پیام‌ها**\n\n"
        text += f"🚀 تعداد راه‌اندازی‌ها: {stats.get('total_startups', 0)}\n"
        text += f"📨 کل پیام‌های بازیابی شده: {stats.get('total_recovered', 0)}\n"
        text += f"🆔 آخرین Update ID: {stats.get('last_update_id', 0)}\n\n"
        
        if stats.get('last_startup'):
            text += f"⏰ آخرین راه‌اندازی: {stats['last_startup']}\n"
        if stats.get('last_shutdown'):
            text += f"⏹️ آخرین توقف: {stats['last_shutdown']}\n"
        
        await message.reply_text(text)
    except Exception as e:
        await message.reply_text(f"❌ خطا در دریافت آمار: {e}")


# بخش بررسی پروکسی حذف شد (Phase 2)


@Client.on_message(filters.user(ADMIN) & filters.regex(r'^📢 ارسال همگانی$'))
async def admin_menu_broadcast(_: Client, message: Message):
    admin_logger.info(f"[ADMIN] broadcast start via text by {message.from_user.id}")
    admin_step['broadcast'] = 1
    await message.reply_text(
        "نوع ارسال همگانی را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 ارسال همگانی (بدون نام گیرنده)", callback_data="broadcast_normal")],
            [InlineKeyboardButton("↗️ فوروارد همگانی", callback_data="broadcast_forward")],
            [InlineKeyboardButton("❌ لغو", callback_data="broadcast_cancel")]
        ])
    )


# --- مدیریت کوکی‌ها ---

# منوی تنظیم Thumbnail محتوای بزرگسال
@Client.on_message(filters.user(ADMIN) & filters.regex(r'^🔞 تنظیم Thumbnail$'))
async def admin_adult_thumb_menu(client: Client, message: Message):
    """منوی مدیریت Thumbnail محتوای بزرگسال"""
    try:
        from plugins.adult_content_admin import load_settings
        
        settings = load_settings()
        thumb_path = settings.get('thumbnail_path')
        thumb_status = "✅ تنظیم شده" if thumb_path else "❌ تنظیم نشده"
        
        text = (
            "🔞 **مدیریت Thumbnail محتوای بزرگسال**\n\n"
            f"📸 **وضعیت:** {thumb_status}\n\n"
            "⚙️ **توضیحات:**\n"
            "• این thumbnail روی تمام ویدیوهای بزرگسال اعمال می‌شود\n"
            "• برای تنظیم، یک عکس ارسال کنید\n"
            "• برای حذف، از دکمه زیر استفاده کنید\n\n"
            "💡 **نکته:** Thumbnail به جلوگیری از فیلتر شدن کمک می‌کند"
        )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📸 تنظیم Thumbnail", callback_data='adult_set_thumb'),
                InlineKeyboardButton("🗑 حذف Thumbnail", callback_data='adult_del_thumb')
            ],
            [
                InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_admin')
            ]
        ])
        
        await message.reply_text(text, reply_markup=keyboard)
        admin_logger.info(f"[ADMIN] Adult thumbnail menu opened by {message.from_user.id}")
    
    except Exception as e:
        admin_logger.error(f"Error in admin_adult_thumb_menu: {e}")
        await message.reply_text(f"❌ خطا: {str(e)}")


# منوی اصلی مدیریت کوکی
@Client.on_message(filters.user(ADMIN) & filters.regex(r'^🍪 مدیریت کوکی$'))
async def admin_cookie_menu(_: Client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزودن کوکی متنی", callback_data='cookie_add_text')],
        [InlineKeyboardButton("📄 افزودن کوکی فایل", callback_data='cookie_add_file')],
        [InlineKeyboardButton("📜 لیست کوکی‌ها", callback_data='cookie_list')],
        [InlineKeyboardButton("✅ اعتبارسنجی با شناسه", callback_data='cookie_validate_prompt')],
        [InlineKeyboardButton("🗑 حذف با شناسه", callback_data='cookie_delete_prompt')],
        [InlineKeyboardButton("📥 واردسازی از مسیر نمونه", callback_data='cookie_import_sample')],
    ])
    await message.reply_text("🍪 مدیریت کوکی — یک گزینه را انتخاب کنید:", reply_markup=keyboard)


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^cookie_mgmt$'))
async def admin_cookie_menu_cb(client: Client, callback_query: CallbackQuery):
    await admin_cookie_menu(client, callback_query.message)


from .cookie_manager import import_cookie_text, validate_and_update_cookie_status


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^cookie_add_text$'))
async def cookie_add_text_cb(_: Client, callback_query: CallbackQuery):
    admin_step['add_cookie'] = 'text'
    await callback_query.message.edit_text(
        "لطفاً متن کوکی را ارسال کنید (فرمت‌های پشتیبانی: Netscape، JSON یا txt).\nبرای لغو /cancel را بفرستید.",
        reply_markup=None
    )
    await callback_query.answer()


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^cookie_add_file$'))
async def cookie_add_file_cb(_: Client, callback_query: CallbackQuery):
    admin_step['add_cookie'] = 'file'
    await callback_query.message.edit_text(
        "لطفاً فایل کوکی را ارسال کنید (پسوندهای مجاز: .txt یا .json).\nبرای لغو /cancel را بفرستید.",
        reply_markup=None
    )
    await callback_query.answer()


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^cookie_list$'))
async def cookie_list_cb(_: Client, callback_query: CallbackQuery):
    db = DB()
    rows = db.list_cookies(limit=50)
    if not rows:
        await callback_query.answer("کوکی یافت نشد", show_alert=True)
        return
    lines = [
        "📜 فهرست کوکی‌ها:",
    ]
    for r in rows:
        lines.append(
            f"#{r['id']} • {r['name']} • {r['source_type']} • وضعیت: {r['status']} • استفاده: {r['use_count']}"
        )
    await callback_query.message.edit_text("\n".join(lines))
    await callback_query.answer()


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^cookie_validate_prompt$'))
async def cookie_validate_prompt_cb(_: Client, callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        "شناسه کوکی را برای اعتبارسنجی ارسال کنید. مثال:\nاعتبارسنجی 12",
        reply_markup=None
    )
    await callback_query.answer()


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^cookie_delete_prompt$'))
async def cookie_delete_prompt_cb(_: Client, callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        "شناسه کوکی را برای حذف ارسال کنید. مثال:\nحذف کوکی 12",
        reply_markup=None
    )
    await callback_query.answer()


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^cookie_import_sample$'))
async def cookie_import_sample_cb(_: Client, callback_query: CallbackQuery):
    # مسیر نمونه ارائه‌شده توسط کاربر
    from config import COOKIE_FILE_PATH
    sample_path = COOKIE_FILE_PATH
    try:
        if not os.path.exists(sample_path):
            await callback_query.answer("فایل نمونه یافت نشد", show_alert=True)
            return
        with open(sample_path, 'r', encoding='utf-8') as f:
            text = f.read()
        ok, msg = import_cookie_text(name='sample_cookie', text=text, source_type='auto')
        if not ok:
            await callback_query.answer(msg, show_alert=True)
            return
        # تلاش برای اعتبارسنجی و بروزرسانی وضعیت
        db = DB()
        latest = db.list_cookies(limit=1)
        if latest:
            cid = latest[0]['id']
            valid = validate_and_update_cookie_status(cid)
            await callback_query.message.edit_text(
                f"✅ واردسازی انجام شد. شناسه: {cid}\nنتیجه اعتبارسنجی: {'معتبر' if valid else 'نامعتبر'}"
            )
        else:
            await callback_query.message.edit_text("✅ واردسازی انجام شد")
        await callback_query.answer()
    except Exception as e:
        await callback_query.answer(f"خطا: {e}", show_alert=True)


# دریافت ورودی متن/فایل برای افزودن کوکی
add_cookie_filter = filters.create(lambda _, __, m: admin_step.get('add_cookie') in ['text', 'file'])

@Client.on_message(add_cookie_filter & filters.user(ADMIN), group=8)
async def handle_cookie_input(client: Client, message: Message):
    mode = admin_step.get('add_cookie')
    try:
        if mode == 'text':
            if not message.text:
                await message.reply_text("لطفاً متن کوکی را ارسال کنید.")
                return
            name = f"manual_{int(time.time())}"
            ok, msg = import_cookie_text(name=name, text=message.text, source_type='auto')
            if not ok:
                await message.reply_text(f"❌ {msg}")
                admin_step.pop('add_cookie', None)
                return
            # اعتبارسنجی خودکار
            db = DB()
            latest = db.list_cookies(limit=1)
            valid = False
            cid = None
            if latest:
                cid = latest[0]['id']
                valid = validate_and_update_cookie_status(cid)
            await message.reply_text(
                f"✅ کوکی ذخیره شد. شناسه: {cid if cid else '-'}\nنتیجه اعتبارسنجی: {'معتبر' if valid else 'نامعتبر'}",
                reply_markup=admin_reply_kb()
            )
            admin_step.pop('add_cookie', None)

        elif mode == 'file':
            if not message.document:
                await message.reply_text("لطفاً فایل .txt یا .json ارسال کنید.")
                return
            filename = (message.document.file_name or '').lower()
            ext = 'json' if filename.endswith('.json') else 'txt'
            # دانلود فایل موقت
            tmp_path = await message.download()
            with open(tmp_path, 'r', encoding='utf-8') as f:
                text = f.read()
            name = f"file_{int(time.time())}"
            ok, msg = import_cookie_text(name=name, text=text, source_type=ext)
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            if not ok:
                await message.reply_text(f"❌ {msg}")
                admin_step.pop('add_cookie', None)
                return
            # اعتبارسنجی خودکار
            db = DB()
            latest = db.list_cookies(limit=1)
            valid = False
            cid = None
            if latest:
                cid = latest[0]['id']
                valid = validate_and_update_cookie_status(cid)
            await message.reply_text(
                f"✅ کوکی فایل ذخیره شد. شناسه: {cid if cid else '-'}\nنتیجه اعتبارسنجی: {'معتبر' if valid else 'نامعتبر'}",
                reply_markup=admin_reply_kb()
            )
            admin_step.pop('add_cookie', None)

    except Exception as e:
        await message.reply_text(f"❌ خطا: {e}")
        admin_step.pop('add_cookie', None)


# لیست کوکی‌ها با دستور
@Client.on_message(filters.command('cookies') & filters.user(ADMIN))
async def list_cookies_cmd(_: Client, message: Message):
    rows = DB().list_cookies(limit=50)
    if not rows:
        await message.reply_text("کوکی‌ای ثبت نشده است.")
        return
    text = "\n".join([
        "📜 فهرست کوکی‌ها:",
        *[f"#{r['id']} • {r['name']} • {r['source_type']} • وضعیت: {r['status']} • استفاده: {r['use_count']}" for r in rows]
    ])
    await message.reply_text(text)


# حذف کوکی با متن "حذف کوکی <id>"
@Client.on_message(filters.user(ADMIN) & filters.regex(r'^حذف کوکی\s+(\d+)$'))
async def delete_cookie_text(_: Client, message: Message):
    try:
        cid = int(re.findall(r'\d+', message.text)[0])
        ok = DB().delete_cookie(cid)
        await message.reply_text("✅ حذف شد" if ok else "❌ حذف ناموفق")
    except Exception:
        await message.reply_text("❌ فرمت شناسه نادرست است")


# اعتبارسنجی کوکی با متن "اعتبارسنجی <id>"
@Client.on_message(filters.user(ADMIN) & filters.regex(r'^اعتبارسنجی\s+(\d+)$'))
async def validate_cookie_text(_: Client, message: Message):
    try:
        cid = int(re.findall(r'\d+', message.text)[0])
        ok = validate_and_update_cookie_status(cid)
        await message.reply_text(f"نتیجه اعتبارسنجی: {'✅ معتبر' if ok else '❌ نامعتبر'}")
    except Exception:
        await message.reply_text("❌ فرمت شناسه نادرست است")


# واردسازی از مسیر فایل محلی: /import_cookie_path <path>
@Client.on_message(filters.command('import_cookie_path') & filters.user(ADMIN))
async def import_cookie_path_cmd(_: Client, message: Message):
    try:
        from config import COOKIE_FILE_PATH
        parts = (message.text or '').split(maxsplit=1)
        path = parts[1] if len(parts) > 1 else COOKIE_FILE_PATH
        if not os.path.exists(path):
            await message.reply_text("❌ فایل یافت نشد")
            return
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
        ok, msg = import_cookie_text(name=f"path_{int(time.time())}", text=text, source_type='auto')
        if not ok:
            await message.reply_text(f"❌ {msg}")
            return
        db = DB()
        latest = db.list_cookies(limit=1)
        if latest:
            cid = latest[0]['id']
            valid = validate_and_update_cookie_status(cid)
            await message.reply_text(
                f"✅ واردسازی انجام شد. شناسه: {cid}\nنتیجه اعتبارسنجی: {'معتبر' if valid else 'نامعتبر'}"
            )
        else:
            await message.reply_text("✅ واردسازی انجام شد")
    except Exception as e:
        await message.reply_text(f"❌ خطا: {e}")


@Client.on_message(filters.user(ADMIN) & filters.regex(r'^📢 تنظیم اسپانسر$'))
async def admin_menu_sponsor(_: Client, message: Message):
    """ورود به پنل مدیریت اسپانسر جدید"""
    user_id = message.from_user.id
    admin_logger.info(f"[ADMIN] sponsor management opened by {user_id}")
    
    # ✅ Reset other states
    admin_step['sp'] = 0
    admin_step['broadcast'] = 0
    admin_step['advertisement'] = 0
    admin_step['waiting_msg'] = 0
    
    # نمایش منوی جدید
    from plugins.sponsor_admin import build_sponsor_admin_menu
    from plugins.sponsor_system import get_sponsor_system
    
    system = get_sponsor_system()
    locks_count = len(system.get_all_locks())
    
    text = f"""🔐 **مدیریت قفل‌های اسپانسری**

📊 **وضعیت فعلی:**
• تعداد قفل‌ها: {locks_count}

💡 **قابلیت‌ها:**
• افزودن قفل‌های متعدد (مولتی قفل)
• آمار کامل هر قفل (جوین، لفت، تبدیل)
• مدیریت آسان قفل‌ها
• نمایش زیبای آمار به کاربران

یک گزینه را انتخاب کنید:"""
    
    await message.reply_text(
        text,
        reply_markup=build_sponsor_admin_menu()
    )


# Handler for old power toggle button removed - replaced with new status system


# Handler for old sponsor toggle button removed - replaced with new status system


# Handler for old advertisement toggle button removed - replaced with new status system


@Client.on_message(filters.user(ADMIN) & filters.regex(r'^✅ وضعیت ربات$'))
async def admin_menu_bot_status(_: Client, message: Message):
    admin_logger.info(f"[ADMIN] bot status menu accessed by {message.from_user.id}")
    
    # Get current status of all systems
    bot_status = data.get('bot_status', 'ON')
    sponsor_status = data.get('force_join', True)
    ad_status = data.get('advertisement', {}).get('enabled', False)
    
    # Create status emojis
    bot_emoji = '🟢' if bot_status == 'ON' else '🔴'
    sponsor_emoji = '🟢' if sponsor_status else '🔴'
    ad_emoji = '🟢' if ad_status else '🔴'
    
    # Create inline keyboard with glass-like appearance
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 وضعیت", callback_data="status_header"),
            InlineKeyboardButton("🔄 تغییر", callback_data="toggle_header")
        ],
        [
            InlineKeyboardButton(f"وضعیت ربات {bot_emoji}", callback_data="status_info_bot"),
            InlineKeyboardButton("تغییر", callback_data="toggle_bot")
        ],
        [
            InlineKeyboardButton(f"وضعیت اسپانسری {sponsor_emoji}", callback_data="status_info_sponsor"),
            InlineKeyboardButton("تغییر", callback_data="toggle_sponsor")
        ],
        [
            InlineKeyboardButton(f"وضعیت تبلیغات {ad_emoji}", callback_data="status_info_ad"),
            InlineKeyboardButton("تغییر", callback_data="toggle_ad")
        ],
        [
            InlineKeyboardButton("🔄 بروزرسانی", callback_data="refresh_status"),
            InlineKeyboardButton("🏠 پنل ادمین", callback_data="back_to_admin")
        ]
    ])
    
    status_text = f"""🔧 **پنل وضعیت ربات**

📊 **وضعیت فعلی سیستم‌ها:**

🤖 **وضعیت ربات:** {bot_emoji} {'فعال' if bot_status == 'ON' else 'غیرفعال'}
🔐 **وضعیت اسپانسری:** {sponsor_emoji} {'فعال' if sponsor_status else 'غیرفعال'}
📺 **وضعیت تبلیغات:** {ad_emoji} {'فعال' if ad_status else 'غیرفعال'}

💡 **راهنما:** برای تغییر هر وضعیت، روی دکمه "تغییر" مربوطه کلیک کنید."""
    
    await message.reply_text(
        status_text,
        reply_markup=keyboard
    )


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^toggle_'))
async def status_toggle_handler(client: Client, callback_query: CallbackQuery):
    """Handle status toggle callbacks"""
    action = callback_query.data
    user_id = callback_query.from_user.id
    
    admin_logger.info(f"[ADMIN] Status toggle: {action} by {user_id}")
    
    try:
        if action == "toggle_bot":
            # Toggle bot status
            current = data.get('bot_status', 'ON')
            new_state = 'OFF' if current == 'ON' else 'ON'
            data['bot_status'] = new_state
            
        elif action == "toggle_sponsor":
            # Toggle sponsor status
            current = data.get('force_join', True)
            new_state = not current
            data['force_join'] = new_state
            
        elif action == "toggle_ad":
            # Toggle advertisement status
            current = data.get('advertisement', {}).get('enabled', False)
            new_state = not current
            if 'advertisement' not in data:
                data['advertisement'] = {}
            data['advertisement']['enabled'] = new_state
        
        # Save changes to database
        try:
            # ✅ Use local database.json
            json_db_path = os.path.join(os.path.dirname(__file__), 'database.json')
            
            # Create backup before writing
            backup_path = json_db_path + '.bak'
            if os.path.exists(json_db_path):
                shutil.copy2(json_db_path, backup_path)
            
            with open(json_db_path, 'w', encoding='utf-8') as outfile:
                json.dump(data, outfile, indent=4, ensure_ascii=False)
        except Exception as e:
            admin_logger.error(f"Failed to write status change: {e}")
            # Try to restore backup if write failed
            try:
                if os.path.exists(backup_path):
                    shutil.copy2(backup_path, json_db_path)
            except Exception:
                pass
            await callback_query.answer("❌ خطا در ذخیره تغییرات!", show_alert=True)
            return
        
        # Update the status display
        await refresh_status_display(client, callback_query)
        await callback_query.answer("✅ تغییرات با موفقیت اعمال شد!")
        
    except Exception as e:
        admin_logger.error(f"Error in status toggle: {e}")
        await callback_query.answer("❌ خطا در تغییر وضعیت!", show_alert=True)


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^refresh_status$'))
async def refresh_status_callback(client: Client, callback_query: CallbackQuery):
    """Handle refresh status callback"""
    await refresh_status_display(client, callback_query)
    await callback_query.answer("🔄 وضعیت بروزرسانی شد!")


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^back_to_admin$'))
async def back_to_admin_callback(client: Client, callback_query: CallbackQuery):
    """Handle back to admin panel callback"""
    # حذف پیام و بازگشت به کیبورد ثابت
    await callback_query.message.delete()
    await callback_query.answer("🔙 بازگشت به پنل اصلی")


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^status_(header|info_)'))
async def status_info_callback(client: Client, callback_query: CallbackQuery):
    """Handle status info callbacks (non-functional buttons)"""
    await callback_query.answer()


async def refresh_status_display(client: Client, callback_query: CallbackQuery):
    """Refresh the status display with current values"""
    # Get current status of all systems
    bot_status = data.get('bot_status', 'ON')
    sponsor_status = data.get('force_join', True)
    ad_status = data.get('advertisement', {}).get('enabled', False)
    
    # Create status emojis
    bot_emoji = '🟢' if bot_status == 'ON' else '🔴'
    sponsor_emoji = '🟢' if sponsor_status else '🔴'
    ad_emoji = '🟢' if ad_status else '🔴'
    
    # Create updated inline keyboard
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 وضعیت", callback_data="status_header"),
            InlineKeyboardButton("🔄 تغییر", callback_data="toggle_header")
        ],
        [
            InlineKeyboardButton(f"وضعیت ربات {bot_emoji}", callback_data="status_info_bot"),
            InlineKeyboardButton("تغییر", callback_data="toggle_bot")
        ],
        [
            InlineKeyboardButton(f"وضعیت اسپانسری {sponsor_emoji}", callback_data="status_info_sponsor"),
            InlineKeyboardButton("تغییر", callback_data="toggle_sponsor")
        ],
        [
            InlineKeyboardButton(f"وضعیت تبلیغات {ad_emoji}", callback_data="status_info_ad"),
            InlineKeyboardButton("تغییر", callback_data="toggle_ad")
        ],
        [
            InlineKeyboardButton("🔄 بروزرسانی", callback_data="refresh_status"),
            InlineKeyboardButton("🏠 پنل ادمین", callback_data="back_to_admin")
        ]
    ])
    
    status_text = f"""🔧 **پنل وضعیت ربات**

📊 **وضعیت فعلی سیستم‌ها:**

🤖 **وضعیت ربات:** {bot_emoji} {'فعال' if bot_status == 'ON' else 'غیرفعال'}
🔐 **وضعیت اسپانسری:** {sponsor_emoji} {'فعال' if sponsor_status else 'غیرفعال'}
📺 **وضعیت تبلیغات:** {ad_emoji} {'فعال' if ad_status else 'غیرفعال'}

💡 **راهنما:** برای تغییر هر وضعیت، روی دکمه "تغییر" مربوطه کلیک کنید."""
    
    await callback_query.message.edit_text(
        status_text,
        reply_markup=keyboard
    )


# Duplicate handlers removed - keeping only the first set


# Duplicate waiting message and power toggle handlers removed


# منوی مدیریت کوکی حذف شد


@Client.on_message(filters.user(ADMIN) & filters.regex(r'^📺 تنظیم تبلیغات$'))
async def admin_menu_advertisement(_: Client, message: Message):
    user_id = message.from_user.id
    admin_logger.info(f"[ADMIN] Advertisement setup started by {user_id}")
    
    # ✅ Get per-user state
    state = get_admin_user_state(user_id)
    state.reset_advertisement()
    
    # Get current advertisement settings
    ad_settings = data.get('advertisement', {})
    enabled = ad_settings.get('enabled', False)
    content_type = ad_settings.get('content_type', 'text')
    position = ad_settings.get('position', 'after')
    
    status_text = "🟢 فعال" if enabled else "🔴 غیرفعال"
    position_text = "بالای محتوا" if position == "before" else "پایین محتوا"
    
    text = (
        "📺 <b>تنظیم تبلیغات</b>\n\n"
        f"وضعیت فعلی: {status_text}\n"
        f"نوع محتوا: {content_type.upper()}\n"
        f"مکیدیو\n"
        "• موزیک\n\n"
        "برای لغو /cancel را بفرستید."
    )
    
    admin_step['advertisement'] = 1
    await message.reply_text(text, reply_markup=admin_reply_kb())

# منوی کوکی یوتیوب حذف شد

# Instagram cookie management removed - using API now

@Client.on_message(filters.user(ADMIN) & filters.regex(r'^⬅️ بازگشت$'))
async def admin_menu_back(_: Client, message: Message):
    admin_logger.info(f"[ADMIN] back pressed by {message.from_user.id}")
    # Reset any transient admin steps
    admin_step['broadcast'] = 0
    admin_step['broadcast_type'] = ''
    admin_step['broadcast_content'] = None
    admin_step['advertisement'] = 0
    admin_step['waiting_msg'] = 0
    admin_step['sp'] = 2
    if 'add_cookie' in admin_step:
        del admin_step['add_cookie']
    # Remove admin reply keyboard to exit panel
    await message.reply_text("از پنل مدیریت خارج شدید.", reply_markup=ReplyKeyboardRemove())

# افزودن کوکی یوتیوب حذف شد

# Process YouTube cookie text
# پردازش متن کوکی یوتیوب حذف شد

# مشاهده کوکی‌های یوتیوب حذف شد

# حذف همه کوکی‌های یوتیوب حذف شد

# Instagram Cookie Operations removed - using API now

# Instagram cookie listing removed - using API now

# Instagram cookie clearing removed - using API now

# Confirmation handlers
# تایید حذف کوکی‌های یوتیوب حذف شد

# Instagram cookie confirmation removed - using API now

@Client.on_message(filters.user(ADMIN) & filters.regex(r'^❌ لغو$'))
async def cancel_operation(_: Client, message: Message):
    """Cancel current operation"""
    # Reset admin steps
    if 'add_cookie' in admin_step:
        del admin_step['add_cookie']
    # Reset sponsor/ad/waiting/broadcast states
    admin_step['sp'] = 0
    admin_step['advertisement'] = 0
    admin_step['waiting_msg'] = 0
    admin_step['broadcast'] = 0
    admin_step['broadcast_type'] = ''
    admin_step['broadcast_content'] = None

    await message.reply("❌ عملیات لغو شد.", reply_markup=admin_reply_kb())


@Client.on_message(filters.command('panel') & filters.user(ADMIN))
async def admin_panel(_: Client, message: Message):
    admin_logger.info(f"[ADMIN] panel command by {message.from_user.id}")
    await message.reply_text(
        "پنل مدیریت",
        reply_markup=admin_reply_kb()
    )


# Admin root handler removed - now using reply keyboard directly from start


# ✅ فیلتر ساده‌تر برای تنظیم اسپانسر
def sponsor_input_filter(_, __, message: Message):
    """فیلتر برای دریافت ورودی اسپانسر"""
    try:
        admin_logger.debug(f"[ADMIN] sponsor_input_filter checking... sp={admin_step.get('sp')}")
        
        # فقط وقتی که در حالت تنظیم اسپانسر هستیم
        if admin_step.get('sp') != 1:
            admin_logger.debug(f"[ADMIN] Filter failed: sp != 1 (sp={admin_step.get('sp')})")
            return False
        
        # فقط ادمین‌ها
        if not message.from_user or message.from_user.id not in ADMIN:
            admin_logger.debug("[ADMIN] Filter failed: not admin")
            return False
        
        # فقط پیام متنی
        if not message.text:
            admin_logger.debug("[ADMIN] Filter failed: no text")
            return False
        
        text = message.text.strip()
        admin_logger.debug(f"[ADMIN] Text received: {text}")
        
        # نادیده گرفتن دکمه‌های پنل ادمین
        admin_buttons = {
            "🛠 مدیریت", "📊 آمار کاربران", "🖥 وضعیت سرور",
            "📢 ارسال همگانی", "📢 تنظیم اسپانسر", "💬 پیام انتظار",
            "🍪 مدیریت کوکی", "📺 تنظیم تبلیغات", "✅ وضعیت ربات",
            "📘 تنظیم راهنما", "🔞 تنظیم Thumbnail", "⬅️ بازگشت", "❌ لغو"
        }
        if text in admin_buttons:
            admin_logger.debug("[ADMIN] Filter failed: admin button")
            return False
        
        # نادیده گرفتن دستورات
        if text.startswith('/'):
            admin_logger.debug("[ADMIN] Filter failed: command")
            return False
        
        admin_logger.info(f"[ADMIN] sponsor_input_filter PASSED for: {text}")
        return True
        
    except Exception as e:
        admin_logger.error(f"[ADMIN] sponsor_input_filter error: {e}")
        return False


sp_filter = filters.create(sponsor_input_filter)


async def admin_panel_custom(_, __, query):
    # Only match our specific admin action tokens, بدون توکن‌های کوکی
    return bool(re.match(r'^(st|srv|gm|sg|sp|pw|waiting_msg|fj_toggle|sp_check|edit_waiting_youtube|edit_waiting_instagram|admin_back)$', query.data))


static_data_filter = filters.create(admin_panel_custom)

# دستور setcookies حذف شد


def _detect_cookie_dest(filename: str) -> str:
    fn = (filename or '').lower()
    if any(k in fn for k in ['instagram', 'insta', 'ig']):
        return 'instagram.txt'
    if any(k in fn for k in ['youtube', 'yt', 'youtub']):
        return 'youtube.txt'
    return ''


# Old cookie file handler removed - using new cookie_manager system


def user_counter():
    users = DB().get_users_id()
    return len(users)


# Helper: server status text

def _server_status_text() -> str:
    now = _dt.now()
    uptime = now - START_TIME
    
    # Server ping (to Google DNS)
    try:
        if _os.name == 'nt':
            # Windows ping command
            result = subprocess.run(['ping', '-n', '1', '8.8.8.8'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # Extract ping time from Windows ping output
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'time=' in line or 'time<' in line:
                        if 'time=' in line:
                            ping_ms = line.split('time=')[1].split('ms')[0]
                        else:
                            ping_ms = '<1'
                        ping_line = f"🏓 پینگ سرور: {ping_ms}ms"
                        break
                else:
                    ping_line = "🏓 پینگ سرور: نامشخص"
            else:
                ping_line = "🏓 پینگ سرور: خطا"
        else:
            # Unix ping command
            result = subprocess.run(['ping', '-c', '1', '8.8.8.8'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and 'time=' in result.stdout:
                ping_ms = result.stdout.split('time=')[1].split(' ')[0]
                ping_line = f"🏓 پینگ سرور: {ping_ms}ms"
            else:
                ping_line = "🏓 پینگ سرور: خطا"
    except Exception:
        ping_line = "🏓 پینگ سرور: نامشخص"
    
    # CPU usage percentage
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_line = f"🔥 میزان استفاده CPU: {cpu_percent:.1f}%"
    except Exception:
        cpu_line = "🔥 میزان استفاده CPU: نامشخص"
    
    # Operating system type
    try:
        os_name = platform.system()
        os_release = platform.release()
        os_line = f"💻 نوع سیستم عامل: {os_name} {os_release}"
    except Exception:
        os_line = "💻 نوع سیستم عامل: نامشخص"
    
    # Uptime
    uptime_line = f"⏱ مدت زمان روشن بودن: {uptime.days}d {uptime.seconds//3600:02d}:{(uptime.seconds//60)%60:02d}:{uptime.seconds%60:02d}"
    
    # Memory usage (5th item)
    try:
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_gb = memory.used / (1024**3)
        memory_total_gb = memory.total / (1024**3)
        memory_line = f"🧠 استفاده از حافظه: {memory_used_gb:.1f}GB/{memory_total_gb:.1f}GB ({memory_percent:.1f}%)"
    except Exception:
        memory_line = "🧠 استفاده از حافظه: نامشخص"
    
    # Disk usage (6th item)
    try:
        if _os.name == 'nt':
            # Windows: get current drive
            current_drive = _os.getcwd().split(':')[0] + ':\\'
        else:
            # Unix-like: use root
            current_drive = '/'
        
        du = shutil.disk_usage(current_drive)
        total_gb = du.total / (1024**3)
        used_gb = (du.total - du.free) / (1024**3)
        usage_percent = (used_gb / total_gb * 100) if total_gb > 0 else 0
        disk_line = f"💽 استفاده از دیسک: {used_gb:.1f}GB/{total_gb:.1f}GB ({usage_percent:.1f}%)"
    except Exception:
        disk_line = "💽 استفاده از دیسک: نامشخص"
    
    return (
        f"{ping_line}\n"
        f"{cpu_line}\n"
        f"{os_line}\n"
        f"{uptime_line}\n"
        f"{memory_line}\n"
        f"{disk_line}"
    )


# Old inline callback handlers removed - now using reply keyboard message handlers


# Sponsor check callback handler removed - now handled by message handlers


# Force join toggle callback handler removed - now handled by message handlers


# Legacy send_to_all command removed - replaced with new broadcast system


# NEW: Broadcast flow via admin panel
@Client.on_message(filters.user(ADMIN), group=5)
async def handle_broadcast(client: Client, message: Message):
    if admin_step.get('broadcast') != 2:
        return
    
    # Store the broadcast content for confirmation
    admin_step['broadcast_content'] = {
        'message_id': message.id,
        'chat_id': message.chat.id,
        'type': admin_step.get('broadcast_type', 'normal')
    }
    
    # Show confirmation
    admin_step['broadcast'] = 3  # waiting for confirmation
    
    all_users = DB().get_users_id()
    total = len(all_users)
    
    broadcast_type_text = "ارسال همگانی" if admin_step['broadcast_type'] == 'normal' else "فوروارد همگانی"
    
    await message.reply_text(
        f"📋 **تأیید {broadcast_type_text}**\n\n"
        f"👥 تعداد کاربران: {total}\n\n"
        f"آیا مطمئن هستید که می‌خواهید این پیام را به همه کاربران ارسال کنید؟",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ تأیید و ارسال", callback_data="broadcast_confirm")],
            [InlineKeyboardButton("❌ لغو", callback_data="broadcast_cancel"),
             InlineKeyboardButton("🔄 تغییر محتوا", callback_data="broadcast_reject")]
        ])
    )

async def start_broadcast_process(client: Client, callback_query: CallbackQuery):
    """Start the actual broadcast process with real-time progress updates every 10 seconds"""
    import time
    
    content = admin_step.get('broadcast_content')
    if not content:
        await callback_query.edit_message_text("❌ خطا: محتوای پیام یافت نشد.")
        return
    
    all_users = DB().get_users_id()
    total = len(all_users)
    sent = 0
    fail = 0
    start_time = time.time()
    last_update_time = start_time
    
    # Update message to show progress
    await callback_query.edit_message_text(
        f"📤 در حال ارسال به {total} کاربر...\n\n"
        f"✅ ارسال شده: 0\n"
        f"❌ ناموفق: 0\n"
        f"📊 پیشرفت: 0/{total} (0.0%)\n"
        f"⏱ زمان سپری شده: 0 ثانیه",
        reply_markup=None
    )
    
    broadcast_type = content.get('type', 'normal')
    
    for i, user in enumerate(all_users):
        uid = user[0] if isinstance(user, (list, tuple)) else user
        try:
            if broadcast_type == 'forward':
                await client.forward_messages(
                    chat_id=uid,
                    from_chat_id=content['chat_id'],
                    message_ids=content['message_id']
                )
            else:  # normal copy
                await client.copy_message(
                    chat_id=uid,
                    from_chat_id=content['chat_id'],
                    message_id=content['message_id']
                )
            sent += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
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
            except Exception:
                fail += 1
        except Exception:
            fail += 1
        
        # Update progress every 10 seconds
        current_time = time.time()
        if current_time - last_update_time >= 10.0:  # 10 seconds
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
    
    # Final result with complete statistics
    final_time = time.time()
    total_elapsed = int(final_time - start_time)
    
    # Calculate sending rate
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
        
        # Send admin panel back
        await callback_query.message.reply_text(
            "🏠 پنل ادمین",
            reply_markup=admin_reply_kb()
        )
    except Exception:
        pass
    
    # Reset admin step
    admin_step['broadcast'] = 0
    admin_step['broadcast_type'] = ''
    admin_step['broadcast_content'] = None


# Broadcast callback handlers
@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^broadcast_'))
async def broadcast_callback_handler(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    
    if data == "broadcast_normal":
        admin_step['broadcast'] = 2
        admin_step['broadcast_type'] = 'normal'
        await callback_query.edit_message_text(
            "📤 **ارسال همگانی (بدون نام گیرنده)**\n\n"
            "محتوای مورد نظر خود را ارسال کنید:\n"
            "• متن، عکس، ویدیو، فایل، استیکر، GIF و... پشتیبانی می‌شود\n"
            "• برای لغو از دکمه زیر استفاده کنید",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ لغو", callback_data="broadcast_cancel")]
            ])
        )
    
    elif data == "broadcast_forward":
        admin_step['broadcast'] = 2
        admin_step['broadcast_type'] = 'forward'
        await callback_query.edit_message_text(
            "↗️ **فوروارد همگانی**\n\n"
            "محتوای مورد نظر خود را ارسال کنید:\n"
            "• متن، عکس، ویدیو، فایل، استیکر، GIF و... پشتیبانی می‌شود\n"
            "• برای لغو از دکمه زیر استفاده کنید",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ لغو", callback_data="broadcast_cancel")]
            ])
        )
    
    elif data == "broadcast_cancel":
        admin_step['broadcast'] = 0
        admin_step['broadcast_type'] = ''
        admin_step['broadcast_content'] = None
        await callback_query.edit_message_text(
            "❌ عملیات ارسال همگانی لغو شد.",
            reply_markup=None
        )
        await callback_query.message.reply_text(
            "🏠 پنل ادمین",
            reply_markup=admin_reply_kb()
        )
    
    elif data == "broadcast_confirm":
        # Start broadcasting
        await start_broadcast_process(client, callback_query)
    
    elif data == "broadcast_reject":
        admin_step['broadcast'] = 2  # Go back to content input
        admin_step['broadcast_content'] = None
        await callback_query.edit_message_text(
            f"{'📤 **ارسال همگانی (بدون نام گیرنده)**' if admin_step['broadcast_type'] == 'normal' else '↗️ **فوروارد همگانی**'}\n\n"
            "محتوای مورد نظر خود را مجدداً ارسال کنید:\n"
            "• متن، عکس، ویدیو، فایل، استیکر، GIF و... پشتیبانی می‌شود\n"
            "• برای لغو از دکمه زیر استفاده کنید",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ لغو", callback_data="broadcast_cancel")]
            ])
        )

@Client.on_message(filters.command('cancel') & filters.user(ADMIN))
async def cancel_all_operations(_, message: Message):
    """
    Cancel all active admin operations
    Fix #2: Include manual_recovery in cancel operations
    """
    user_id = message.from_user.id
    cancelled_operations = []
    
    # Cancel broadcast
    if admin_step.get('broadcast', 0) > 0:
        admin_step['broadcast'] = 0
        admin_step['broadcast_type'] = ''
        admin_step['broadcast_content'] = None
        cancelled_operations.append("ارسال همگانی")
    
    # Cancel sponsor setup
    if admin_step.get('sp', 0) == 1:
        admin_step['sp'] = 0
        cancelled_operations.append("تنظیم اسپانسر")
    
    # Fix #2: Cancel manual recovery
    if admin_step.get('manual_recovery', 0) > 0:
        admin_step['manual_recovery'] = 0
        cancelled_operations.append("بازیابی دستی")
    
    # Cancel advertisement setup
    if admin_step.get('advertisement', 0) > 0:
        admin_step['advertisement'] = 0
        admin_step['ad_content_type'] = ''
        admin_step['ad_file_id'] = ''
        admin_step['ad_caption'] = ''
        admin_step['ad_text'] = ''
        cancelled_operations.append("تنظیم تبلیغات")
    
    # Cancel waiting message setup
    if admin_step.get('waiting_msg', 0) > 0:
        admin_step['waiting_msg'] = 0
        admin_step['waiting_msg_type'] = ''
        admin_step['waiting_msg_platform'] = ''
        cancelled_operations.append("تنظیم پیام انتظار")
    
    # Cancel help message setup
    if admin_step.get('help_setup', 0) == 1:
        admin_step['help_setup'] = 0
        cancelled_operations.append("تنظیم پیام راهنما")
    
    # Cancel cookie operations
    if 'add_cookie' in admin_step:
        del admin_step['add_cookie']
        cancelled_operations.append("افزودن کوکی")
    
    # Fix #1: Reset per-user state
    state = get_admin_user_state(user_id)
    state.reset_all()
    
    if cancelled_operations:
        operations_text = "، ".join(cancelled_operations)
        await message.reply_text(
            f"❌ عملیات‌های زیر لغو شدند:\n• {operations_text}",
            reply_markup=admin_reply_kb()
        )
        admin_logger.info(f"[ADMIN] Operations cancelled by {message.from_user.id}: {operations_text}")
    else:
        await message.reply_text(
            "ℹ️ عملیات فعالی برای لغو وجود ندارد.",
            reply_markup=admin_reply_kb()
        )


# Global lock برای جلوگیری از race condition
_json_write_lock = asyncio.Lock()

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

@Client.on_message(filters.user(ADMIN) & filters.private & filters.text, group=5)
async def set_sp(client: Client, message: Message):
    """Handler جدید و بهبود یافته برای تنظیم اسپانسر"""
    
    # ✅ بررسی دستی: فقط در حالت تنظیم اسپانسر
    if admin_step.get('sp') != 1:
        return
    
    # ✅ نادیده گرفتن دکمه‌های پنل
    admin_buttons = {
        "🛠 مدیریت", "📊 آمار کاربران", "🖥 وضعیت سرور",
        "📢 ارسال همگانی", "📢 تنظیم اسپانسر", "💬 پیام انتظار",
        "🍪 مدیریت کوکی", "📺 تنظیم تبلیغات", "✅ وضعیت ربات",
        "📘 تنظیم راهنما", "🔞 تنظیم Thumbnail", "⬅️ بازگشت", "❌ لغو"
    }
    if message.text.strip() in admin_buttons:
        return
    
    # ✅ نادیده گرفتن دستورات
    if message.text.strip().startswith('/'):
        return
    
    # ✅ حالا پردازش کن
    user_id = message.from_user.id
    raw_text = (message.text or '').strip()
    
    admin_logger.info(f"[ADMIN] set_sp called by {user_id} with text: {raw_text}")
    
    try:
        # ✅ مرحله 1: Normalize ورودی
        sponsor_value = None
        
        # بررسی لینک t.me
        if raw_text.startswith('http://t.me/') or raw_text.startswith('https://t.me/') or raw_text.startswith('t.me/'):
            # استخراج username از لینک
            username = raw_text.split('t.me/')[-1].strip('/')
            if username.startswith('+'):
                await message.reply_text(
                    "❌ **لینک دعوت خصوصی پشتیبانی نمی‌شود**\n\n"
                    "لطفاً از یکی از فرمت‌های زیر استفاده کنید:\n"
                    "• `@username`\n"
                    "• `-1001234567890`"
                )
                admin_step['sp'] = 0
                return
            sponsor_value = '@' + username if not username.startswith('@') else username
        
        # بررسی @username
        elif raw_text.startswith('@'):
            sponsor_value = raw_text
        
        # بررسی ID عددی
        elif raw_text.startswith('-100') and raw_text[1:].isdigit():
            sponsor_value = raw_text
        
        # فرمت نامعتبر
        else:
            await message.reply_text(
                "❌ **فرمت نامعتبر!**\n\n"
                "📋 **فرمت‌های صحیح:**\n"
                "• `@username` → مثال: `@OkAlef`\n"
                "• `-1001234567890` → آی‌دی عددی\n"
                "• `https://t.me/username` → لینک کانال\n\n"
                "💡 **دوباره تلاش کنید یا /cancel بزنید**"
            )
            return  # نه admin_step['sp'] = 0 تا بتواند دوباره تلاش کند
        
        admin_logger.debug(f"[ADMIN] Normalized sponsor value: {sponsor_value}")
        
        # ✅ مرحله 2: بررسی دسترسی به کانال
        status_msg = await message.reply_text("🔄 **در حال بررسی دسترسی...**")
        
        try:
            # دریافت اطلاعات کانال
            chat = await client.get_chat(sponsor_value)
            chat_title = getattr(chat, 'title', 'نامشخص')
            chat_username = getattr(chat, 'username', None)
            
            admin_logger.debug(f"[ADMIN] Chat found: {chat_title} (username: {chat_username})")
            
            # دریافت اطلاعات ربات
            bot = await client.get_me()
            bot_id = bot.id
            
            # بررسی عضویت و ادمین بودن ربات
            try:
                bot_member = await client.get_chat_member(sponsor_value, bot_id)
                bot_status = bot_member.status
                
                admin_logger.debug(f"[ADMIN] Bot status in channel: {bot_status}")
                
                if bot_status not in ["administrator", "creator"]:
                    await status_msg.edit_text(
                        f"❌ **ربات در کانال ادمین نیست!**\n\n"
                        f"📢 کانال: **{chat_title}**\n"
                        f"🤖 وضعیت ربات: `{bot_status}`\n\n"
                        f"⚠️ لطفاً ابتدا ربات را در کانال **ادمین** کنید."
                    )
                    admin_step['sp'] = 0
                    return
                
            except Exception as member_error:
                admin_logger.warning(f"[ADMIN] Error checking bot membership: {member_error}")
                await status_msg.edit_text(
                    f"❌ **ربات در کانال عضو نیست!**\n\n"
                    f"📢 کانال: **{chat_title}**\n\n"
                    f"⚠️ لطفاً ابتدا ربات را به کانال اضافه کنید.\n\n"
                    f"🔍 خطا: `{str(member_error)[:80]}`"
                )
                admin_step['sp'] = 0
                return
            
            await status_msg.edit_text("✅ **دسترسی تأیید شد!**\n\n🔄 در حال ذخیره...")
            
        except Exception as chat_error:
            admin_logger.warning(f"[ADMIN] Error getting chat: {chat_error}")
            await status_msg.edit_text(
                f"❌ **خطا در دسترسی به کانال!**\n\n"
                f"🔍 خطا: `{str(chat_error)[:100]}`\n\n"
                f"💡 **بررسی کنید:**\n"
                f"• شناسه کانال صحیح باشد\n"
                f"• ربات در کانال عضو باشد\n"
                f"• ربات ادمین باشد"
            )
            admin_step['sp'] = 0
            return
        
        # ✅ مرحله 3: ذخیره در database
        async with _json_write_lock:
            try:
                json_db_path = os.path.join(os.path.dirname(__file__), 'database.json')
                
                # Backup
                backup_path = json_db_path + '.bak'
                if os.path.exists(json_db_path):
                    shutil.copy2(json_db_path, backup_path)
                
                # Read-Modify-Write
                with open(json_db_path, 'r', encoding='utf-8') as f:
                    current_data = json.load(f)
                
                current_data['sponser'] = sponsor_value
                
                # Atomic write
                temp_path = json_db_path + '.tmp'
                with open(temp_path, 'w', encoding='utf-8') as outfile:
                    json.dump(current_data, outfile, indent=4, ensure_ascii=False)
                
                os.replace(temp_path, json_db_path)
                
                # Update in-memory
                data['sponser'] = sponsor_value
                
                admin_logger.info(f"[ADMIN] ✅ Sponsor successfully set by {user_id}: {sponsor_value}")
                
                # پیام موفقیت
                success_text = (
                    f"✅ **اسپانسر با موفقیت تنظیم شد!**\n\n"
                    f"📢 **کانال:** {chat_title}\n"
                    f"🆔 **شناسه:** `{sponsor_value}`\n"
                )
                if chat_username:
                    success_text += f"🔗 **لینک:** https://t.me/{chat_username}\n"
                
                success_text += "\n✅ **قفل عضویت فعال است**"
                
                await status_msg.edit_text(success_text)
                
            except Exception as save_error:
                admin_logger.error(f"[ADMIN] Error saving sponsor: {save_error}")
                
                # Restore backup
                try:
                    if os.path.exists(backup_path):
                        shutil.copy2(backup_path, json_db_path)
                except Exception:
                    pass
                
                await status_msg.edit_text(
                    f"❌ **خطا در ذخیره‌سازی!**\n\n"
                    f"🔍 خطا: `{str(save_error)[:100]}`\n\n"
                    f"💡 لطفاً دوباره تلاش کنید."
                )
                admin_step['sp'] = 0
                return
        
        # ✅ Reset state
        admin_step['sp'] = 0
        admin_logger.info("[ADMIN] Sponsor setup completed successfully!")
        
    except Exception as e:
        admin_logger.error(f"[ADMIN] Unexpected error in set_sp: {e}")
        await message.reply_text(
            f"❌ **خطای غیرمنتظره!**\n\n"
            f"🔍 خطا: `{str(e)[:100]}`\n\n"
            f"💡 لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."
        )
        admin_step['sp'] = 0


# Remaining callback handler code removed - now handled by message handlers


@Client.on_message(filters.user(ADMIN) & filters.regex(r'^🔄 آپدیت انتظار$'))
async def pending_update_menu_text(client: Client, message: Message):
    """منوی مدیریت آپدیت انتظار"""
    # Clear other states
    admin_step['sp'] = 2
    admin_step['broadcast'] = 0
    admin_step['waiting_msg'] = 0
    
    text = "🔄 <b>سیستم آپدیت انتظار</b>\n\n"
    text += "از این بخش می‌توانید پیام‌های کاربرانی که در زمان خاموش بودن ربات پیام داده‌اند را پردازش کنید.\n\n"
    text += "💡 <b>نحوه کار:</b>\n"
    text += "• ادمین تعداد دقیقه‌های گذشته را وارد می‌کند\n"
    text += "• ربات پیام‌های آن بازه زمانی را پردازش می‌کند\n"
    text += "• به کاربران پیام اطلاع‌رسانی ارسال می‌شود\n\n"
    text += "📝 لطفاً تعداد دقیقه‌های گذشته را وارد کنید (1-1440):"
    
    await message.reply_text(
        text,
        reply_markup=ReplyKeyboardRemove()
    )
    # Set state for minutes input
    admin_step['pending_update'] = 1


@Client.on_message(filters.user(ADMIN) & filters.regex(r'^💬 پیام انتظار$'))
async def waiting_msg_menu_text(client: Client, message: Message):
    """Show waiting message management menu via text"""
    # Clear sponsor state to avoid unintended captures
    admin_step['sp'] = 2
    admin_step['broadcast'] = 0
    db = DB()
    messages = db.get_all_waiting_messages()
    
    text = "💬 <b>مدیریت پیام‌های انتظار</b>\n\n"
    text += "پیام‌های فعلی:\n"
    for msg_data in messages:
        platform = msg_data.get('platform', 'نامشخص')
        msg_type = msg_data.get('type', 'text')
        content = msg_data.get('content', 'نامشخص')
        if msg_type == 'text':
            preview = content[:30] + '...' if len(content) > 30 else content
        else:
            preview = f"{msg_type.upper()}: {content[:20]}..."
        text += f"• {platform}: {preview}\n"
    
    keyboard = [
        [InlineKeyboardButton("📝 تغییر پیام یوتیوب", callback_data='edit_waiting_youtube')],
        [InlineKeyboardButton("📝 تغییر پیام اینستاگرام", callback_data='edit_waiting_instagram')],
    ]
    
    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# Handle waiting message content input
waiting_msg_filter = filters.create(
    lambda _, __, message: admin_step.get('waiting_msg') == 2
)

# Handle pending update minutes input
pending_update_filter = filters.create(
    lambda _, __, message: admin_step.get('pending_update') == 1
)

@Client.on_message(pending_update_filter & filters.user(ADMIN), group=8)
async def handle_pending_update_minutes(client: Client, message: Message):
    """Handle pending update minutes input"""
    if not message.text or not message.text.strip().isdigit():
        await message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید (1-1440).")
        return
    
    minutes = int(message.text.strip())
    
    if minutes < 1 or minutes > 1440:
        await message.reply_text("❌ تعداد دقیقه باید بین 1 تا 1440 باشد.")
        return
    
    # Reset admin step
    admin_step['pending_update'] = 0
    
    # Process pending updates
    try:
        from plugins.message_recovery import process_pending_updates
        result = await process_pending_updates(minutes)
        
        await message.reply_text(
            f"✅ آپدیت انتظار با موفقیت انجام شد!\n\n"
            f"⏰ بازه زمانی: {minutes} دقیقه گذشته\n"
            f"📨 پیام‌های پردازش شده: {result.get('processed', 0)}\n"
            f"👥 کاربران اطلاع‌رسانی شده: {result.get('notified', 0)}",
            reply_markup=admin_reply_kb()
        )
        
    except Exception as e:
        admin_logger.error(f"[ERROR] Failed to process pending updates: {e}")
        await message.reply_text(
            f"❌ خطا در پردازش آپدیت انتظار: {e}",
            reply_markup=admin_reply_kb()
        )


@Client.on_message(waiting_msg_filter & filters.user(ADMIN), group=7)
async def handle_waiting_message_input(client: Client, message: Message):
    """Handle waiting message content input"""
    msg_type = admin_step.get('waiting_msg_type')
    platform = admin_step.get('waiting_msg_platform')
    
    if not msg_type or not platform:
        await message.reply_text("خطا در دریافت اطلاعات. لطفاً دوباره تلاش کنید.")
        admin_step['waiting_msg'] = 0
        return
    
    db = DB()
    
    try:
        if msg_type == 'text':
            if not message.text:
                await message.reply_text("لطفاً یک متن ارسال کنید.")
                return
            content = message.text.strip()
            
        elif msg_type == 'gif':
            if not message.animation:
                await message.reply_text("لطفاً یک فایل GIF ارسال کنید.")
                return
            content = message.animation.file_id
            
        elif msg_type == 'sticker':
            if not message.sticker:
                await message.reply_text("لطفاً یک استیکر ارسال کنید.")
                return
            content = message.sticker.file_id
        
        # Save to database
        db.set_waiting_message(platform, msg_type, content)
        
        # Reset admin step
        admin_step['waiting_msg'] = 0
        admin_step['waiting_msg_type'] = ''
        admin_step['waiting_msg_platform'] = ''
        
        await message.reply_text(
            f"✅ پیام انتظار {platform.title()} با موفقیت تغییر کرد!\n\n"
            f"نوع: {msg_type.upper()}\n"
            f"محتوا: {'متن ذخیره شد' if msg_type == 'text' else 'فایل ذخیره شد'}"
        )
        
    except Exception as e:
        # Fix #9: Use logger instead of print
        admin_logger.error(f"[ERROR] Failed to save waiting message: {e}")
        await message.reply_text("خطا در ذخیره‌سازی پیام. لطفاً دوباره تلاش کنید.")
        admin_step['waiting_msg'] = 0


# Admin callback query handler
# Waiting message callback handlers
@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^edit_waiting_'))
async def waiting_message_callback_handler(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    
    if data == 'edit_waiting_youtube':
        platform = 'youtube'
    elif data == 'edit_waiting_instagram':
        platform = 'instagram'
    else:
        await callback_query.answer("❌ پلتفرم نامشخص")
        return
    
    # Show message type selection
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 متن", callback_data=f"waiting_type_{platform}_text")],
        [InlineKeyboardButton("🎭 استیکر", callback_data=f"waiting_type_{platform}_sticker")],
        [InlineKeyboardButton("🎬 GIF", callback_data=f"waiting_type_{platform}_gif")],
        [InlineKeyboardButton("❌ لغو", callback_data="waiting_cancel")]
    ])
    
    await callback_query.edit_message_text(
        f"💬 **تغییر پیام انتظار {platform.title()}**\n\n"
        f"نوع محتوای مورد نظر را انتخاب کنید:",
        reply_markup=keyboard
    )

@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^waiting_type_'))
async def waiting_type_callback_handler(client: Client, callback_query: CallbackQuery):
    # Parse callback data: waiting_type_platform_type
    parts = callback_query.data.split('_')
    if len(parts) != 3:
        await callback_query.answer("❌ خطا در پردازش درخواست")
        return
    
    platform = parts[1]  # youtube or instagram
    msg_type = parts[2]   # text, sticker, gif
    
    admin_step['waiting_msg'] = 2
    admin_step['waiting_msg_type'] = msg_type
    admin_step['waiting_msg_platform'] = platform
    
    type_text = {
        'text': 'متن',
        'sticker': 'استیکر', 
        'gif': 'فایل GIF'
    }.get(msg_type, msg_type)
    
    await callback_query.edit_message_text(
        f"💬 **تغییر پیام انتظار {platform.title()}**\n\n"
        f"نوع انتخابی: {type_text}\n\n"
        f"لطفاً {type_text} مورد نظر خود را ارسال کنید:\n\n"
        f"❌ برای لغو /cancel را بفرستید.",
        reply_markup=None
    )

@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^sp$'))
async def sponsor_menu_callback(client: Client, callback_query: CallbackQuery):
    """نمایش منوی مدیریت اسپانسر"""
    from plugins.sponsor_admin import build_sponsor_admin_menu
    from plugins.sponsor_system import get_sponsor_system
    
    system = get_sponsor_system()
    locks_count = len(system.get_all_locks())
    
    text = f"""🔐 **مدیریت قفل‌های اسپانسری**

📊 **وضعیت فعلی:**
• تعداد قفل‌ها: {locks_count}

💡 **قابلیت‌ها:**
• افزودن قفل‌های متعدد (مولتی قفل)
• آمار کامل هر قفل (جوین، لفت، تبدیل)
• مدیریت آسان قفل‌ها
• نمایش زیبای آمار به کاربران

یک گزینه را انتخاب کنید:"""
    
    await callback_query.message.edit_text(
        text,
        reply_markup=build_sponsor_admin_menu()
    )
    await callback_query.answer()


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^cancel_sponsor_setup$'))
async def cancel_sponsor_setup_callback(client: Client, callback_query: CallbackQuery):
    """لغو تنظیم اسپانسر"""
    admin_step['sp'] = 0
    await callback_query.edit_message_text(
        "❌ **تنظیم اسپانسر لغو شد**\n\n"
        "می‌توانید از پنل ادمین دوباره شروع کنید."
    )
    await callback_query.answer("لغو شد")


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^waiting_cancel$'))
async def waiting_cancel_callback_handler(client: Client, callback_query: CallbackQuery):
    admin_step['waiting_msg'] = 0
    admin_step['waiting_msg_type'] = ''
    admin_step['waiting_msg_platform'] = ''
    
    await callback_query.edit_message_text(
        "❌ عملیات تغییر پیام انتظار لغو شد.",
        reply_markup=None
    )


# Handle advertisement content input
async def handle_advertisement_content(client: Client, message: Message):
    """Handle advertisement content input from admin with validation"""
    try:
        # Ignore admin panel buttons
        if message.text and message.text.strip() in {
            "🛠 مدیریت","📊 آمار کاربران","🖥 وضعیت سرور",
            "📢 ارسال همگانی","📢 تنظیم اسپانسر","💬 پیام انتظار","🍪 مدیریت کوکی",
            "📺 تنظیم تبلیغات","✅ وضعیت ربات","📘 تنظیم راهنما","🔞 تنظیم Thumbnail",
            "⬅️ بازگشت","❌ لغو","🔝 بالای محتوا","🔻 پایین محتوا"
        }:
            return
        
        # ✅ Validation محتوا
        is_valid, error_msg = await validate_ad_content(message)
        if not is_valid:
            await message.reply_text(error_msg)
            admin_step['advertisement'] = 0
            return
        
        ad_data = {
            'enabled': True,
            'position': 'after'  # default position
        }
        
        if message.text:
            ad_data['content_type'] = 'text'
            ad_data['content'] = message.text
            ad_data['file_id'] = ''
            ad_data['caption'] = ''
            admin_step['ad_text'] = message.text
        elif message.photo:
            ad_data['content_type'] = 'photo'
            ad_data['file_id'] = message.photo.file_id
            ad_data['caption'] = message.caption or ''
            ad_data['content'] = 'photo_content'
            admin_step['ad_text'] = ''
        elif message.video:
            ad_data['content_type'] = 'video'
            ad_data['file_id'] = message.video.file_id
            ad_data['caption'] = message.caption or ''
            ad_data['content'] = 'video_content'
            admin_step['ad_text'] = ''
        elif message.animation:
            ad_data['content_type'] = 'gif'
            ad_data['file_id'] = message.animation.file_id
            ad_data['caption'] = message.caption or ''
            ad_data['content'] = 'gif_content'
            admin_step['ad_text'] = ''
        elif message.sticker:
            ad_data['content_type'] = 'sticker'
            ad_data['file_id'] = message.sticker.file_id
            ad_data['caption'] = ''
            ad_data['content'] = 'sticker_content'
            admin_step['ad_text'] = ''
        elif message.audio:
            ad_data['content_type'] = 'audio'
            ad_data['file_id'] = message.audio.file_id
            ad_data['caption'] = message.caption or ''
            ad_data['content'] = 'audio_content'
            admin_step['ad_text'] = ''
        else:
            await message.reply_text("❌ نوع محتوای ارسالی پشتیبانی نمی‌شود.")
            admin_step['advertisement'] = 0
            return
        
        # Store advertisement data
        admin_step['ad_content_type'] = ad_data['content_type']
        admin_step['ad_file_id'] = ad_data.get('file_id', '')
        admin_step['ad_caption'] = ad_data.get('caption', '')
        
        # ✅ Log
        admin_logger.info(f"[ADMIN] Advertisement content received: {ad_data['content_type']}")
        
        # Ask for position
        keyboard = ReplyKeyboardMarkup([
            ["🔝 بالای محتوا", "🔻 پایین محتوا"],
            ["⬅️ بازگشت"]
        ], resize_keyboard=True)
        
        admin_step['advertisement'] = 2  # waiting for position
        await message.reply_text(
            "✅ محتوای تبلیغات دریافت شد!\n\n"
            "حالا مکان نمایش تبلیغات را انتخاب کنید:",
            reply_markup=keyboard
        )
        
    except Exception as e:
        # Fix #9: Remove duplicate print, keep logger only
        admin_logger.error(f"[ADMIN] Advertisement content error: {e}")
        await message.reply_text(f"❌ خطا در پردازش محتوای تبلیغات: {str(e)}")
        admin_step['advertisement'] = 0


# هندلر دریافت متن کوکی حذف شد

# هندلر دریافت فایل کوکی حذف شد

@Client.on_message(filters.text & filters.user(ADMIN), group=3)
async def admin_text_handler(client: Client, message: Message):
    # This handler now only deals with other admin text commands,
    # not cookie inputs, as those are handled by the more specific handlers above.
    # Existing logic for other admin commands remains here.
    pass  # unchanged existing logic follows...

# NEW: Activate advertisement content handler when in step 1
ad_content_filter = filters.create(lambda _, __, m: admin_step.get('advertisement') == 1)

@Client.on_message(ad_content_filter & filters.user(ADMIN), group=7)
async def admin_ad_content_entry(client: Client, message: Message):
    await handle_advertisement_content(client, message)

# NEW: Handle advertisement position selection and persist settings
@Client.on_message(filters.user(ADMIN) & filters.regex(r'^(🔝 بالای محتوا|🔻 پایین محتوا)$'), group=4)
async def admin_ad_position_handler(_: Client, message: Message):
    try:
        pos = 'before' if 'بالا' in (message.text or '') else 'after'
        ad_settings = {
            'enabled': True,
            'position': pos,
            'content_type': admin_step.get('ad_content_type', 'text'),
            'file_id': admin_step.get('ad_file_id', ''),
            'caption': admin_step.get('ad_caption', ''),
        }
        if ad_settings['content_type'] == 'text':
            ad_settings['content'] = admin_step.get('ad_text', '')
        else:
            ad_settings['content'] = ''

        # ✅ Persist to database.json safely با lock
        async with _json_write_lock:
            try:
                # ✅ Use local database.json
                json_db_path = os.path.join(os.path.dirname(__file__), 'database.json')
                
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
                
                # ✅ Log
                admin_logger.info(f"[ADMIN] Advertisement settings saved: {ad_settings['content_type']}, position={pos}")
                
            except Exception as e:
                # Fix #9: Remove duplicate print, keep logger only
                admin_logger.error(f"[ADMIN] Failed to save advertisement: {e}")
                try:
                    if os.path.exists(backup_path):
                        shutil.copy2(backup_path, json_db_path)
                except Exception:
                    pass
                await message.reply_text("❌ خطا در ذخیره تنظیمات تبلیغات.")
                return

        # Reset steps
        admin_step['advertisement'] = 0
        admin_step['ad_content_type'] = ''
        admin_step['ad_file_id'] = ''
        admin_step['ad_caption'] = ''
        admin_step['ad_text'] = ''

        await message.reply_text(
            "✅ تبلیغات با موفقیت تنظیم شد!",
            reply_markup=admin_reply_kb()
        )
    except Exception as e:
        # Fix #9: Remove duplicate print, keep logger only
        admin_logger.error(f"[ADMIN] Error in ad position handler: {e}")
        await message.reply_text("❌ خطای غیرمنتظره در تنظیم تبلیغات.")


# Fix #13: Remove duplicate _server_status_text definition
# The first definition (line 1147) is kept, this duplicate is removed


# ============================================================================
# Failed Request Queue Management
# مدیریت صف درخواست‌های ناموفق
# ============================================================================

@Client.on_message(filters.user(ADMIN) & filters.regex(r'^📋 صف درخواست‌ها$'))
async def admin_queue_menu(_: Client, message: Message):
    """منوی مدیریت صف درخواست‌های ناموفق"""
    user_id = message.from_user.id
    # Fix #9: Use logger instead of print
    admin_logger.info(f"[ADMIN] queue menu opened by {user_id}")
    
    try:
        from plugins.failed_request_queue import FailedRequestQueue
        from plugins.db_wrapper import DB
        
        db = DB()
        queue = FailedRequestQueue(db)
        
        # دریافت آمار صف
        stats = queue.get_queue_stats()
        
        # ساخت متن آمار
        text = (
            "📋 **صف درخواست‌های ناموفق**\n\n"
            "📊 **آمار:**\n"
            f"• مجموع: {stats.get('total', 0)}\n"
            f"• در انتظار: {stats.get('pending', 0)}\n"
            f"• در حال پردازش: {stats.get('processing', 0)}\n"
            f"• تکمیل شده: {stats.get('completed', 0)}\n"
            f"• شکست خورده: {stats.get('failed', 0)}\n\n"
            "💡 **گزینه‌ها:**"
        )
        
        # ساخت کیبورد
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📜 لیست صف", callback_data="queue_list"),
                InlineKeyboardButton("📊 آمار کامل", callback_data="queue_stats")
            ],
            [
                InlineKeyboardButton("🗑 پاک‌سازی قدیمی‌ها", callback_data="queue_cleanup"),
            ],
            [
                InlineKeyboardButton("🔄 بروزرسانی", callback_data="queue_refresh"),
                InlineKeyboardButton("🏠 بازگشت", callback_data="admin_back")
            ]
        ])
        
        await message.reply_text(text, reply_markup=keyboard)
        # Fix #10: Add return to prevent handler conflicts
        return
    
    except Exception as e:
        admin_logger.error(f"Error in queue menu: {e}")
        await message.reply_text(f"❌ خطا در نمایش منوی صف: {str(e)[:200]}")
        return


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^failed_queue$'))
async def admin_queue_menu_callback(client: Client, callback_query: CallbackQuery):
    """Callback handler برای دکمه صف درخواست‌ها در پنل اصلی"""
    try:
        from plugins.failed_request_queue import FailedRequestQueue
        from plugins.db_wrapper import DB
        
        db = DB()
        queue = FailedRequestQueue(db)
        
        # دریافت آمار صف
        stats = queue.get_queue_stats()
        
        # ساخت متن آمار
        text = (
            "📋 **صف درخواست‌های ناموفق**\n\n"
            "📊 **آمار:**\n"
            f"• مجموع: {stats.get('total', 0)}\n"
            f"• در انتظار: {stats.get('pending', 0)}\n"
            f"• در حال پردازش: {stats.get('processing', 0)}\n"
            f"• تکمیل شده: {stats.get('completed', 0)}\n"
            f"• شکست خورده: {stats.get('failed', 0)}\n\n"
            "💡 **گزینه‌ها:**"
        )
        
        # ساخت کیبورد
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📜 لیست صف", callback_data="queue_list"),
                InlineKeyboardButton("📊 آمار کامل", callback_data="queue_stats")
            ],
            [
                InlineKeyboardButton("🗑 پاک‌سازی قدیمی‌ها", callback_data="queue_cleanup"),
            ],
            [
                InlineKeyboardButton("🔄 بروزرسانی", callback_data="queue_refresh"),
                InlineKeyboardButton("🏠 بازگشت", callback_data="admin_back")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        await callback_query.answer()
    
    except Exception as e:
        admin_logger.error(f"Error in queue menu callback: {e}")
        await callback_query.answer(f"❌ خطا: {str(e)[:100]}", show_alert=True)


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^queue_list'))
async def queue_list_callback(client: Client, callback_query: CallbackQuery):
    """نمایش لیست درخواست‌های در انتظار با دکمه‌های inline"""
    try:
        from plugins.failed_request_queue import FailedRequestQueue
        from plugins.db_wrapper import DB
        
        db = DB()
        queue = FailedRequestQueue(db)
        
        # دریافت لیست درخواست‌های pending
        requests = queue.get_pending_requests(limit=5)
        
        if not requests:
            await callback_query.answer("✅ صف خالی است!", show_alert=True)
            # بروزرسانی به منوی اصلی
            await queue_refresh_callback(client, callback_query)
            return
        
        # ساخت متن لیست
        text = "📜 **لیست درخواست‌های در انتظار** (5 مورد اول)\n\n"
        
        buttons = []
        for i, req in enumerate(requests, 1):
            req_id = req.get('id', 0)
            user_id = req.get('user_id', 0)
            platform = req.get('platform', 'نامشخص')
            url = req.get('url', '')
            created_at = req.get('created_at', '')
            error_msg = req.get('error_message', '')
            
            # محدود کردن طول URL
            url_display = url[:40] + "..." if len(url) > 40 else url
            
            # محدود کردن طول خطا
            error_display = error_msg[:50] + "..." if len(error_msg) > 50 else error_msg
            
            text += (
                f"**{i}. درخواست #{req_id}**\n"
                f"👤 کاربر: `{user_id}`\n"
                f"🌐 پلتفرم: {platform}\n"
                f"🔗 لینک: `{url_display}`\n"
                f"❌ خطا: {error_display}\n"
                f"⏰ زمان: {created_at}\n\n"
            )
            
            # اضافه کردن دکمه‌های inline برای هر درخواست
            buttons.append([
                InlineKeyboardButton(
                    f"✅ پردازش #{req_id}",
                    callback_data=f"queue_process_{req_id}"
                ),
                InlineKeyboardButton(
                    f"🗑 حذف #{req_id}",
                    callback_data=f"queue_delete_{req_id}"
                )
            ])
        
        # ساخت کیبورد با دکمه‌های مدیریت
        buttons.append([
            InlineKeyboardButton("🔄 بروزرسانی", callback_data="queue_list"),
            InlineKeyboardButton("🏠 بازگشت", callback_data="queue_refresh")
        ])
        
        keyboard = InlineKeyboardMarkup(buttons)
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        await callback_query.answer()
    
    except Exception as e:
        admin_logger.error(f"Error in queue list: {e}")
        await callback_query.answer(f"❌ خطا: {str(e)[:100]}", show_alert=True)


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^queue_stats$'))
async def queue_stats_callback(client: Client, callback_query: CallbackQuery):
    """نمایش آمار کامل صف با تفکیک پلتفرم و میانگین زمان پردازش"""
    try:
        from plugins.failed_request_queue import FailedRequestQueue
        from plugins.db_wrapper import DB
        
        db = DB()
        queue = FailedRequestQueue(db)
        
        # دریافت آمار کلی
        stats = queue.get_queue_stats()
        
        # محاسبه نرخ موفقیت
        total = stats.get('total', 0)
        completed = stats.get('completed', 0)
        failed = stats.get('failed', 0)
        
        success_rate = 0
        if total > 0:
            success_rate = (completed / total) * 100
        
        # دریافت آمار به تفکیک پلتفرم
        platform_stats = db.get_failed_requests_by_platform()
        
        # دریافت میانگین زمان پردازش
        avg_time = db.get_average_processing_time()
        
        # تبدیل ثانیه به فرمت قابل خواندن
        if avg_time > 0:
            if avg_time < 60:
                avg_time_str = f"{avg_time:.1f} ثانیه"
            elif avg_time < 3600:
                avg_time_str = f"{avg_time/60:.1f} دقیقه"
            else:
                avg_time_str = f"{avg_time/3600:.1f} ساعت"
        else:
            avg_time_str = "نامشخص"
        
        # ساخت متن آمار کامل
        text = (
            "📊 **آمار کامل صف درخواست‌ها**\n\n"
            "📈 **آمار کلی:**\n"
            f"• مجموع: {total}\n"
            f"• در انتظار: {stats.get('pending', 0)}\n"
            f"• در حال پردازش: {stats.get('processing', 0)}\n"
            f"• تکمیل شده: {completed}\n"
            f"• شکست خورده: {failed}\n\n"
            f"📊 **نرخ موفقیت:** {success_rate:.1f}%\n"
            f"⏱ **میانگین زمان پردازش:** {avg_time_str}\n"
        )
        
        # اضافه کردن آمار به تفکیک پلتفرم (محدود به 5 پلتفرم برتر)
        if platform_stats:
            text += "\n🌐 **آمار به تفکیک پلتفرم:**\n"
            sorted_platforms = sorted(platform_stats.items(), key=lambda x: x[1]['total'], reverse=True)[:5]
            
            for platform, pstats in sorted_platforms:
                platform_total = pstats.get('total', 0)
                platform_completed = pstats.get('completed', 0)
                platform_pending = pstats.get('pending', 0)
                
                platform_success_rate = 0
                if platform_total > 0:
                    platform_success_rate = (platform_completed / platform_total) * 100
                
                text += (
                    f"\n**{platform}:**\n"
                    f"  کل: {platform_total} | "
                    f"انتظار: {platform_pending} | "
                    f"موفق: {platform_completed} ({platform_success_rate:.0f}%)\n"
                )
        
        # ساخت کیبورد
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 بروزرسانی", callback_data="queue_stats"),
                InlineKeyboardButton("🏠 بازگشت", callback_data="queue_refresh")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        await callback_query.answer()
    
    except Exception as e:
        admin_logger.error(f"Error in queue stats: {e}")
        await callback_query.answer(f"❌ خطا: {str(e)[:100]}", show_alert=True)


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^queue_cleanup$'))
async def queue_cleanup_callback(client: Client, callback_query: CallbackQuery):
    """پاک‌سازی درخواست‌های قدیمی (بیش از 7 روز) با تأیید"""
    try:
        from plugins.failed_request_queue import FailedRequestQueue
        from plugins.db_wrapper import DB
        
        db = DB()
        queue = FailedRequestQueue(db)
        
        # دریافت آمار برای نمایش قبل از حذف
        stats = queue.get_queue_stats()
        completed = stats.get('completed', 0)
        failed = stats.get('failed', 0)
        total_to_delete = completed + failed
        
        if total_to_delete == 0:
            await callback_query.answer("✅ هیچ درخواست قدیمی برای پاک کردن وجود ندارد!", show_alert=True)
            return
        
        # ارسال پیام تأیید
        text = (
            "⚠️ **تأیید پاک‌سازی صف**\n\n"
            f"🗑 تعداد درخواست‌های قابل حذف:\n"
            f"• تکمیل شده: {completed}\n"
            f"• شکست خورده: {failed}\n"
            f"• **مجموع: {total_to_delete}**\n\n"
            "📅 درخواست‌های قدیمی‌تر از 7 روز حذف خواهند شد.\n\n"
            "❓ آیا مطمئن هستید؟"
        )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ بله، پاک کن", callback_data="queue_clear_confirm"),
                InlineKeyboardButton("❌ لغو", callback_data="queue_clear_cancel")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        await callback_query.answer()
    
    except Exception as e:
        admin_logger.error(f"Error in queue cleanup: {e}")
        await callback_query.answer(f"❌ خطا: {str(e)[:100]}", show_alert=True)


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^queue_clear_confirm$'))
async def queue_clear_confirm_callback(client: Client, callback_query: CallbackQuery):
    """تأیید پاک‌سازی صف"""
    try:
        from plugins.failed_request_queue import FailedRequestQueue
        from plugins.db_wrapper import DB
        
        db = DB()
        queue = FailedRequestQueue(db)
        
        # پاک‌سازی درخواست‌های قدیمی
        deleted_count = queue.cleanup_old_requests(days=7)
        
        await callback_query.answer(
            f"✅ {deleted_count} درخواست قدیمی پاک شد",
            show_alert=True
        )
        
        # بروزرسانی نمایش به منوی اصلی
        await queue_refresh_callback(client, callback_query)
    
    except Exception as e:
        admin_logger.error(f"Error in queue clear confirm: {e}")
        await callback_query.answer(f"❌ خطا: {str(e)[:100]}", show_alert=True)


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^queue_clear_cancel$'))
async def queue_clear_cancel_callback(client: Client, callback_query: CallbackQuery):
    """لغو پاک‌سازی صف"""
    try:
        await callback_query.answer("❌ پاک‌سازی لغو شد")
        
        # بازگشت به منوی اصلی
        await queue_refresh_callback(client, callback_query)
    
    except Exception as e:
        admin_logger.error(f"Error in queue clear cancel: {e}")
        await callback_query.answer(f"❌ خطا: {str(e)[:100]}", show_alert=True)


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^queue_refresh$'))
async def queue_refresh_callback(client: Client, callback_query: CallbackQuery):
    """بروزرسانی نمایش صف"""
    try:
        from plugins.failed_request_queue import FailedRequestQueue
        from plugins.db_wrapper import DB
        
        db = DB()
        queue = FailedRequestQueue(db)
        
        # دریافت آمار صف
        stats = queue.get_queue_stats()
        
        # ساخت متن آمار
        text = (
            "📋 **صف درخواست‌های ناموفق**\n\n"
            "📊 **آمار:**\n"
            f"• مجموع: {stats.get('total', 0)}\n"
            f"• در انتظار: {stats.get('pending', 0)}\n"
            f"• در حال پردازش: {stats.get('processing', 0)}\n"
            f"• تکمیل شده: {stats.get('completed', 0)}\n"
            f"• شکست خورده: {stats.get('failed', 0)}\n\n"
            "💡 **گزینه‌ها:**"
        )
        
        # ساخت کیبورد
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📜 لیست صف", callback_data="queue_list"),
                InlineKeyboardButton("📊 آمار کامل", callback_data="queue_stats")
            ],
            [
                InlineKeyboardButton("🗑 پاک‌سازی قدیمی‌ها", callback_data="queue_cleanup"),
            ],
            [
                InlineKeyboardButton("🔄 بروزرسانی", callback_data="queue_refresh"),
                InlineKeyboardButton("🏠 بازگشت", callback_data="admin_back")
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        await callback_query.answer("🔄 بروزرسانی شد")
    
    except Exception as e:
        admin_logger.error(f"Error in queue refresh: {e}")
        await callback_query.answer(f"❌ خطا: {str(e)[:100]}", show_alert=True)


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^queue_process_(\d+)$'))
async def queue_process_callback(client: Client, callback_query: CallbackQuery):
    """Callback handler برای دکمه پردازش درخواست از صف"""
    try:
        # استخراج request_id از callback data
        match = re.match(r'^queue_process_(\d+)$', callback_query.data)
        if not match:
            await callback_query.answer("❌ فرمت نامعتبر", show_alert=True)
            return
        
        request_id = int(match.group(1))
        
        # فراخوانی handler از admin_notification
        from plugins.admin_notification import handle_retry_callback
        
        await handle_retry_callback(client, callback_query, request_id)
    
    except Exception as e:
        admin_logger.error(f"Error in queue_process_callback: {e}")
        await callback_query.answer(f"❌ خطا: {str(e)[:100]}", show_alert=True)


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^queue_delete_(\d+)$'))
async def queue_delete_callback(client: Client, callback_query: CallbackQuery):
    """Callback handler برای دکمه حذف درخواست از صف"""
    try:
        # استخراج request_id از callback data
        match = re.match(r'^queue_delete_(\d+)$', callback_query.data)
        if not match:
            await callback_query.answer("❌ فرمت نامعتبر", show_alert=True)
            return
        
        request_id = int(match.group(1))
        
        from plugins.failed_request_queue import FailedRequestQueue
        from plugins.db_wrapper import DB
        
        db = DB()
        queue = FailedRequestQueue(db)
        
        # حذف درخواست با علامت‌گذاری به عنوان failed
        success = queue.mark_as_failed(request_id, "Deleted by admin")
        
        if success:
            await callback_query.answer("✅ درخواست حذف شد", show_alert=True)
            
            # بروزرسانی نمایش
            try:
                # دریافت لیست جدید
                requests = queue.get_pending_requests(limit=5)
                
                if not requests:
                    await callback_query.message.edit_text("✅ صف خالی است!")
                    return
                
                # ساخت متن لیست جدید
                text = "📜 **لیست درخواست‌های در انتظار** (5 مورد اول)\n\n"
                
                buttons = []
                for i, req in enumerate(requests, 1):
                    req_id = req.get('id', 0)
                    user_id = req.get('user_id', 0)
                    platform = req.get('platform', 'نامشخص')
                    url = req.get('url', '')
                    created_at = req.get('created_at', '')
                    error_msg = req.get('error_message', '')
                    
                    url_display = url[:40] + "..." if len(url) > 40 else url
                    error_display = error_msg[:50] + "..." if len(error_msg) > 50 else error_msg
                    
                    text += (
                        f"**{i}. درخواست #{req_id}**\n"
                        f"👤 کاربر: `{user_id}`\n"
                        f"🌐 پلتفرم: {platform}\n"
                        f"🔗 لینک: `{url_display}`\n"
                        f"❌ خطا: {error_display}\n"
                        f"⏰ زمان: {created_at}\n\n"
                    )
                    
                    buttons.append([
                        InlineKeyboardButton(
                            f"✅ پردازش #{req_id}",
                            callback_data=f"queue_process_{req_id}"
                        ),
                        InlineKeyboardButton(
                            f"🗑 حذف #{req_id}",
                            callback_data=f"queue_delete_{req_id}"
                        )
                    ])
                
                buttons.append([
                    InlineKeyboardButton("🔄 بروزرسانی", callback_data="queue_list_page_0"),
                    InlineKeyboardButton("📊 آمار", callback_data="queue_stats")
                ])
                
                keyboard = InlineKeyboardMarkup(buttons)
                await callback_query.message.edit_text(text, reply_markup=keyboard)
            except Exception as update_error:
                admin_logger.error(f"Error updating queue list after delete: {update_error}")
        else:
            await callback_query.answer("❌ خطا در حذف درخواست", show_alert=True)
    
    except Exception as e:
        admin_logger.error(f"Error in queue_delete_callback: {e}")
        await callback_query.answer(f"❌ خطا: {str(e)[:100]}", show_alert=True)


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^retry_failed_(\d+)$'))
async def retry_failed_callback(client: Client, callback_query: CallbackQuery):
    """
    Callback handler برای دکمه "پردازش مجدد" در گزارش‌های ادمین
    این handler به admin_notification.handle_retry_callback متصل می‌شود
    """
    try:
        # استخراج request_id از callback data
        match = re.match(r'^retry_failed_(\d+)$', callback_query.data)
        if not match:
            await callback_query.answer("❌ فرمت نامعتبر", show_alert=True)
            return
        
        request_id = int(match.group(1))
        
        # فراخوانی handler از admin_notification
        from plugins.admin_notification import handle_retry_callback
        
        await handle_retry_callback(client, callback_query, request_id)
    
    except Exception as e:
        admin_logger.error(f"Error in retry_failed_callback: {e}")
        await callback_query.answer(f"❌ خطا: {str(e)[:100]}", show_alert=True)


# دستورات مدیریت صف
@Client.on_message(filters.command('queue') & filters.user(ADMIN))
async def queue_command(_: Client, message: Message):
    """دستور نمایش صف درخواست‌های ناموفق با pagination و دکمه‌های inline"""
    try:
        from plugins.failed_request_queue import FailedRequestQueue
        from plugins.db_wrapper import DB
        
        db = DB()
        queue = FailedRequestQueue(db)
        
        # دریافت لیست درخواست‌های pending
        requests = queue.get_pending_requests(limit=5)
        
        if not requests:
            await message.reply_text("✅ صف خالی است!")
            return
        
        # ساخت متن لیست
        text = "📜 **لیست درخواست‌های در انتظار** (5 مورد اول)\n\n"
        
        buttons = []
        for i, req in enumerate(requests, 1):
            req_id = req.get('id', 0)
            user_id = req.get('user_id', 0)
            platform = req.get('platform', 'نامشخص')
            url = req.get('url', '')
            created_at = req.get('created_at', '')
            error_msg = req.get('error_message', '')
            
            # محدود کردن طول URL
            url_display = url[:40] + "..." if len(url) > 40 else url
            
            # محدود کردن طول خطا
            error_display = error_msg[:50] + "..." if len(error_msg) > 50 else error_msg
            
            text += (
                f"**{i}. درخواست #{req_id}**\n"
                f"👤 کاربر: `{user_id}`\n"
                f"🌐 پلتفرم: {platform}\n"
                f"🔗 لینک: `{url_display}`\n"
                f"❌ خطا: {error_display}\n"
                f"⏰ زمان: {created_at}\n\n"
            )
            
            # اضافه کردن دکمه‌های inline برای هر درخواست
            buttons.append([
                InlineKeyboardButton(
                    f"✅ پردازش #{req_id}",
                    callback_data=f"queue_process_{req_id}"
                ),
                InlineKeyboardButton(
                    f"🗑 حذف #{req_id}",
                    callback_data=f"queue_delete_{req_id}"
                )
            ])
        
        # اضافه کردن دکمه‌های navigation
        buttons.append([
            InlineKeyboardButton("🔄 بروزرسانی", callback_data="queue_list_page_0"),
            InlineKeyboardButton("📊 آمار", callback_data="queue_stats")
        ])
        
        keyboard = InlineKeyboardMarkup(buttons)
        
        await message.reply_text(text, reply_markup=keyboard)
    
    except Exception as e:
        admin_logger.error(f"Error in queue command: {e}")
        await message.reply_text(f"❌ خطا: {str(e)[:200]}")


@Client.on_message(filters.command('queue_stats') & filters.user(ADMIN))
async def queue_stats_command(_: Client, message: Message):
    """دستور نمایش آمار کامل صف با تفکیک پلتفرم و میانگین زمان پردازش"""
    try:
        from plugins.failed_request_queue import FailedRequestQueue
        from plugins.db_wrapper import DB
        
        db = DB()
        queue = FailedRequestQueue(db)
        
        # دریافت آمار کلی
        stats = queue.get_queue_stats()
        
        # محاسبه نرخ موفقیت
        total = stats.get('total', 0)
        completed = stats.get('completed', 0)
        
        success_rate = 0
        if total > 0:
            success_rate = (completed / total) * 100
        
        # دریافت آمار به تفکیک پلتفرم
        platform_stats = db.get_failed_requests_by_platform()
        
        # دریافت میانگین زمان پردازش
        avg_time = db.get_average_processing_time()
        
        # تبدیل ثانیه به فرمت قابل خواندن
        if avg_time > 0:
            if avg_time < 60:
                avg_time_str = f"{avg_time:.1f} ثانیه"
            elif avg_time < 3600:
                avg_time_str = f"{avg_time/60:.1f} دقیقه"
            else:
                avg_time_str = f"{avg_time/3600:.1f} ساعت"
        else:
            avg_time_str = "نامشخص"
        
        # ساخت متن آمار کلی
        text = (
            "📊 **آمار کامل صف درخواست‌ها**\n\n"
            "📈 **آمار کلی:**\n"
            f"• مجموع: {total}\n"
            f"• در انتظار: {stats.get('pending', 0)}\n"
            f"• در حال پردازش: {stats.get('processing', 0)}\n"
            f"• تکمیل شده: {completed}\n"
            f"• شکست خورده: {stats.get('failed', 0)}\n\n"
            f"📊 **نرخ موفقیت:** {success_rate:.1f}%\n"
            f"⏱ **میانگین زمان پردازش:** {avg_time_str}\n"
        )
        
        # اضافه کردن آمار به تفکیک پلتفرم
        if platform_stats:
            text += "\n🌐 **آمار به تفکیک پلتفرم:**\n"
            for platform, pstats in sorted(platform_stats.items(), key=lambda x: x[1]['total'], reverse=True):
                platform_total = pstats.get('total', 0)
                platform_completed = pstats.get('completed', 0)
                platform_pending = pstats.get('pending', 0)
                
                platform_success_rate = 0
                if platform_total > 0:
                    platform_success_rate = (platform_completed / platform_total) * 100
                
                text += (
                    f"\n**{platform}:**\n"
                    f"  • کل: {platform_total} | "
                    f"در انتظار: {platform_pending} | "
                    f"موفق: {platform_completed} ({platform_success_rate:.0f}%)\n"
                )
        
        await message.reply_text(text)
    
    except Exception as e:
        admin_logger.error(f"Error in queue_stats command: {e}")
        await message.reply_text(f"❌ خطا: {str(e)[:200]}")


@Client.on_message(filters.command('queue_clear') & filters.user(ADMIN))
async def queue_clear_command(_: Client, message: Message):
    """دستور پاک کردن درخواست‌های قدیمی از صف با تأیید"""
    try:
        from plugins.failed_request_queue import FailedRequestQueue
        from plugins.db_wrapper import DB
        
        db = DB()
        queue = FailedRequestQueue(db)
        
        # دریافت آمار برای نمایش قبل از حذف
        stats = queue.get_queue_stats()
        completed = stats.get('completed', 0)
        failed = stats.get('failed', 0)
        total_to_delete = completed + failed
        
        if total_to_delete == 0:
            await message.reply_text("✅ هیچ درخواست قدیمی برای پاک کردن وجود ندارد!")
            return
        
        # ارسال پیام تأیید با دکمه‌های inline
        text = (
            "⚠️ **تأیید پاک‌سازی صف**\n\n"
            f"🗑 تعداد درخواست‌های قابل حذف:\n"
            f"• تکمیل شده: {completed}\n"
            f"• شکست خورده: {failed}\n"
            f"• **مجموع: {total_to_delete}**\n\n"
            "📅 درخواست‌های قدیمی‌تر از 7 روز حذف خواهند شد.\n\n"
            "❓ آیا مطمئن هستید؟"
        )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ بله، پاک کن", callback_data="queue_clear_confirm"),
                InlineKeyboardButton("❌ لغو", callback_data="queue_clear_cancel")
            ]
        ])
        
        await message.reply_text(text, reply_markup=keyboard)
    
    except Exception as e:
        admin_logger.error(f"Error in queue_clear command: {e}")
        await message.reply_text(f"❌ خطا: {str(e)[:200]}")


@Client.on_message(filters.command('retry_metrics') & filters.user(ADMIN))
async def retry_metrics_command(_: Client, message: Message):
    """دستور نمایش metrics سیستم retry"""
    try:
        from plugins.retry_metrics import retry_metrics
        
        # دریافت گزارش فرمت شده
        report = retry_metrics.get_formatted_report()
        
        await message.reply_text(report)
        
        # لاگ خلاصه metrics
        retry_metrics.log_summary()
    
    except ImportError:
        await message.reply_text(
            "❌ **سیستم metrics فعال نیست**\n\n"
            "ماژول retry_metrics در دسترس نیست."
        )
    except Exception as e:
        admin_logger.error(f"Error in retry_metrics command: {e}")
        await message.reply_text(f"❌ خطا: {str(e)[:200]}")


@Client.on_message(filters.command('retry_stats') & filters.user(ADMIN))
async def retry_stats_command(_: Client, message: Message):
    """دستور نمایش آمار خلاصه retry (نسخه کوتاه)"""
    try:
        from plugins.retry_metrics import retry_metrics
        
        stats = retry_metrics.get_comprehensive_stats()
        
        # ساخت متن خلاصه
        text = "📊 **آمار Smart Retry**\n\n"
        text += f"⏱️ زمان فعالیت: {stats['uptime_hours']:.1f} ساعت\n"
        text += f"🔄 کل تلاش‌ها: {stats['total_retries']}\n"
        text += f"✅ نرخ موفقیت کلی: {stats['overall_success_rate']:.1f}%\n\n"
        
        text += "**نرخ موفقیت به تفکیک تلاش:**\n"
        for attempt, rate in stats['attempt_success_rates'].items():
            text += f"  • تلاش {attempt}: {rate:.1f}%\n"
        
        queue = stats['queue_stats']
        text += f"\n**صف:**\n"
        text += f"  • اندازه: {queue['current_size']}\n"
        text += f"  • نرخ موفقیت: {queue['queue_success_rate']:.1f}%\n"
        
        text += f"\n⚡ فعالیت اخیر: {stats['recent_activity_rate']:.1f} retry/دقیقه"
        
        await message.reply_text(text)
    
    except ImportError:
        await message.reply_text(
            "❌ **سیستم metrics فعال نیست**\n\n"
            "ماژول retry_metrics در دسترس نیست."
        )
    except Exception as e:
        admin_logger.error(f"Error in retry_stats command: {e}")
        await message.reply_text(f"❌ خطا: {str(e)[:200]}")


admin_logger.info("Failed request queue management handlers loaded")
admin_logger.info("Retry metrics handlers loaded")


@Client.on_message(filters.command('clearcache') & filters.user(ADMIN))
async def clear_cache_command(_: Client, message: Message):
    """دستور پاک کردن cache آمار"""
    try:
        clear_stats_cache()
        await message.reply_text(
            "✅ **Cache پاک شد**\n\n"
            "تمام آمارهای ذخیره شده در cache پاک شدند.\n"
            "آمار جدید از دیتابیس بارگذاری خواهد شد."
        )
        admin_logger.info(f"[ADMIN] Cache cleared by {message.from_user.id}")
    except Exception as e:
        admin_logger.error(f"Error in clear_cache command: {e}")
        await message.reply_text(f"❌ خطا: {str(e)[:200]}")


@Client.on_message(filters.command('debugstats') & filters.user(ADMIN))
async def debug_stats_command(_: Client, message: Message):
    """دستور debug آمار درخواست‌ها"""
    try:
        await message.reply_text("⏳ در حال بررسی...")
        
        db = DB()
        
        # بررسی تعداد رکوردها
        if db.db_type == 'mysql':
            db.cursor.execute("SELECT COUNT(*) FROM requests")
        else:
            db.cursor.execute("SELECT COUNT(*) FROM requests")
        total_records = db.cursor.fetchone()[0]
        
        # آمار پلتفرم‌ها
        platforms_stats = {}
        for platform in ['youtube', 'aparat', 'adult', 'universal']:
            count = db.get_requests_by_platform(platform)
            platforms_stats[platform] = count
        
        # آمار وضعیت‌ها
        success = db.get_successful_requests()
        failed = db.get_failed_requests()
        
        # آخرین درخواست
        if db.db_type == 'mysql':
            db.cursor.execute("SELECT platform, status, created_at FROM requests ORDER BY id DESC LIMIT 1")
        else:
            db.cursor.execute("SELECT platform, status, created_at FROM requests ORDER BY id DESC LIMIT 1")
        last_request = db.cursor.fetchone()
        
        # ساخت متن
        text = (
            "🔍 **Debug آمار درخواست‌ها**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 **دیتابیس:** `{db.db_type}`\n"
            f"📋 **کل رکوردها:** `{total_records}`\n\n"
            "**پلتفرم‌ها:**\n"
            f"├ YouTube: `{platforms_stats['youtube']}`\n"
            f"├ Aparat: `{platforms_stats['aparat']}`\n"
            f"├ Adult: `{platforms_stats['adult']}`\n"
            f"└ Universal: `{platforms_stats['universal']}`\n\n"
            "**وضعیت:**\n"
            f"├ موفق: `{success}`\n"
            f"└ ناموفق: `{failed}`\n\n"
        )
        
        if last_request:
            text += (
                "**آخرین درخواست:**\n"
                f"├ پلتفرم: `{last_request[0]}`\n"
                f"├ وضعیت: `{last_request[1]}`\n"
                f"└ زمان: `{last_request[2]}`\n\n"
            )
        
        # بررسی cache
        from plugins.admin_statistics import STATS_CACHE
        text += f"💾 **Cache:** `{len(STATS_CACHE)}` آیتم\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        text += "💡 برای پاک کردن cache: `/clearcache`"
        
        await message.reply_text(text)
        admin_logger.info(f"[ADMIN] Debug stats by {message.from_user.id}")
        
    except Exception as e:
        admin_logger.error(f"Error in debug_stats command: {e}")
        await message.reply_text(f"❌ خطا: {str(e)[:200]}")


# ==================== Adult Content Thumbnail Management ====================

@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^adult_thumb$'))
async def adult_thumb_callback(client: Client, callback_query: CallbackQuery):
    """مدیریت Thumbnail محتوای بزرگسال"""
    try:
        from plugins.adult_content_admin import load_settings, save_settings
        
        settings = load_settings()
        thumb_path = settings.get('thumbnail_path')
        thumb_status = "✅ تنظیم شده" if thumb_path else "❌ تنظیم نشده"
        
        text = (
            "🔞 **مدیریت Thumbnail محتوای بزرگسال**\n\n"
            f"📸 **وضعیت:** {thumb_status}\n\n"
            "⚙️ **توضیحات:**\n"
            "• این thumbnail روی تمام ویدیوهای بزرگسال اعمال می‌شود\n"
            "• برای تنظیم، یک عکس ارسال کنید\n"
            "• برای حذف، از دکمه زیر استفاده کنید\n\n"
            "💡 **نکته:** Thumbnail به جلوگیری از فیلتر شدن کمک می‌کند"
        )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📸 تنظیم Thumbnail", callback_data='adult_set_thumb'),
                InlineKeyboardButton("🗑 حذف Thumbnail", callback_data='adult_del_thumb')
            ],
            [
                InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_admin')
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        await callback_query.answer()
    
    except Exception as e:
        admin_logger.error(f"Error in adult_thumb_callback: {e}")
        await callback_query.answer(f"❌ خطا: {str(e)[:50]}", show_alert=True)


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^adult_set_thumb$'))
async def adult_set_thumb_callback(client: Client, callback_query: CallbackQuery):
    """درخواست ارسال عکس برای thumbnail"""
    # تنظیم state برای دریافت عکس
    user_id = callback_query.from_user.id
    if user_id not in admin_user_states:
        admin_user_states[user_id] = AdminUserState(user_id)
    
    # تنظیم state
    admin_user_states[user_id].waiting_adult_thumb = True
    
    await callback_query.answer("📸 لطفاً عکس را ارسال کنید", show_alert=True)
    await callback_query.message.reply_text(
        "📸 **تنظیم Thumbnail**\n\n"
        "لطفاً عکس مورد نظر را ارسال کنید.\n"
        "این عکس روی تمام ویدیوهای بزرگسال اعمال خواهد شد.\n\n"
        "💡 برای لغو، /cancel ارسال کنید."
    )


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^adult_del_thumb$'))
async def adult_del_thumb_callback(client: Client, callback_query: CallbackQuery):
    """حذف thumbnail"""
    try:
        from plugins.adult_content_admin import load_settings, save_settings
        import os
        
        settings = load_settings()
        old_path = settings.get('thumbnail_path')
        
        if old_path and os.path.exists(old_path):
            try:
                os.unlink(old_path)
            except:
                pass
        
        settings['thumbnail_path'] = None
        save_settings(settings)
        
        await callback_query.answer("✅ Thumbnail حذف شد", show_alert=True)
        
        # بازگشت به منوی thumbnail
        await adult_thumb_callback(client, callback_query)
    
    except Exception as e:
        admin_logger.error(f"Error in adult_del_thumb_callback: {e}")
        await callback_query.answer(f"❌ خطا: {str(e)[:50]}", show_alert=True)


# Handler برای دریافت عکس thumbnail از ادمین
@Client.on_message(filters.photo & filters.user(ADMIN) & filters.private)
async def handle_admin_photo(client: Client, message: Message):
    """دریافت عکس از ادمین (برای thumbnail یا سایر موارد)"""
    user_id = message.from_user.id
    
    # بررسی state
    if user_id in admin_user_states and hasattr(admin_user_states[user_id], 'waiting_adult_thumb') and admin_user_states[user_id].waiting_adult_thumb:
        try:
            from plugins.adult_content_admin import load_settings, save_settings
            
            # دانلود عکس
            photo = message.photo
            file_path = f"data/adult_thumbnail_{photo.file_id}.jpg"
            
            status_msg = await message.reply_text("⏳ در حال دانلود عکس...")
            
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
                
                # ریست state
                admin_user_states[user_id].waiting_adult_thumb = False
                
                await status_msg.edit_text(
                    "✅ **Thumbnail با موفقیت تنظیم شد!**\n\n"
                    "این عکس روی تمام ویدیوهای بزرگسال اعمال خواهد شد."
                )
                admin_logger.info(f"Thumbnail set by admin {user_id}: {downloaded}")
            else:
                await status_msg.edit_text("❌ خطا در دانلود عکس")
        
        except Exception as e:
            admin_logger.error(f"Error handling admin photo: {e}")
            await message.reply_text(f"❌ خطا: {str(e)}")


# ==================== Statistics System ====================

@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^(st|stats_overview)$'))
async def stats_overview_callback(client: Client, callback_query: CallbackQuery):
    """نمایش صفحه Overview"""
    try:
        await callback_query.answer("⏳ در حال محاسبه...")
        
        # بررسی cache
        cached = get_cached_stats('overview')
        if cached:
            stats = cached
        else:
            # محاسبه آمار
            db = DB()
            calculator = StatisticsCalculator(db)
            stats = calculator.calculate_overview_stats()
            set_cached_stats('overview', stats)
        
        # فرمت کردن
        text = StatisticsFormatter.format_overview_stats(stats)
        
        # کیبورد
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("👥 جزئیات کاربران", callback_data='stats_users'),
                InlineKeyboardButton("📈 جزئیات درخواست‌ها", callback_data='stats_requests')
            ],
            [
                InlineKeyboardButton("⚡ جزئیات عملکرد", callback_data='stats_performance'),
                InlineKeyboardButton("🔄 بروزرسانی", callback_data='stats_refresh_overview')
            ],
            [
                InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_admin')
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        admin_logger.info(f"[ADMIN] Overview stats viewed by {callback_query.from_user.id}")
    
    except Exception as e:
        admin_logger.error(f"Error in stats_overview_callback: {e}")
        await callback_query.answer("❌ خطا در دریافت آمار", show_alert=True)


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^stats_users$'))
async def stats_users_callback(client: Client, callback_query: CallbackQuery):
    """نمایش آمار کاربران"""
    try:
        await callback_query.answer("⏳ در حال محاسبه...")
        
        # بررسی cache
        cached = get_cached_stats('users')
        if cached:
            stats = cached
        else:
            # محاسبه آمار
            db = DB()
            calculator = StatisticsCalculator(db)
            stats = calculator.calculate_users_stats()
            set_cached_stats('users', stats)
        
        # فرمت کردن
        text = StatisticsFormatter.format_users_stats(stats)
        
        # کیبورد
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 بروزرسانی", callback_data='stats_refresh_users'),
                InlineKeyboardButton("🔙 بازگشت", callback_data='stats_overview')
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        admin_logger.info(f"[ADMIN] Users stats viewed by {callback_query.from_user.id}")
    
    except Exception as e:
        admin_logger.error(f"Error in stats_users_callback: {e}")
        await callback_query.answer("❌ خطا در دریافت آمار", show_alert=True)


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^stats_requests$'))
async def stats_requests_callback(client: Client, callback_query: CallbackQuery):
    """نمایش آمار درخواست‌ها"""
    try:
        await callback_query.answer("⏳ در حال محاسبه...")
        
        # بررسی cache
        cached = get_cached_stats('requests')
        if cached:
            stats = cached
        else:
            # محاسبه آمار
            db = DB()
            calculator = StatisticsCalculator(db)
            stats = calculator.calculate_requests_stats()
            set_cached_stats('requests', stats)
        
        # فرمت کردن
        text = StatisticsFormatter.format_requests_stats(stats)
        
        # کیبورد
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 بروزرسانی", callback_data='stats_refresh_requests'),
                InlineKeyboardButton("🔙 بازگشت", callback_data='stats_overview')
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        admin_logger.info(f"[ADMIN] Requests stats viewed by {callback_query.from_user.id}")
    
    except Exception as e:
        admin_logger.error(f"Error in stats_requests_callback: {e}")
        await callback_query.answer("❌ خطا در دریافت آمار", show_alert=True)


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^stats_performance$'))
async def stats_performance_callback(client: Client, callback_query: CallbackQuery):
    """نمایش آمار عملکرد"""
    try:
        await callback_query.answer("⏳ در حال محاسبه...")
        
        # بررسی cache
        cached = get_cached_stats('performance')
        if cached:
            stats = cached
        else:
            # محاسبه آمار
            db = DB()
            calculator = StatisticsCalculator(db)
            stats = calculator.calculate_performance_stats()
            set_cached_stats('performance', stats)
        
        # فرمت کردن
        text = StatisticsFormatter.format_performance_stats(stats)
        
        # کیبورد
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 بروزرسانی", callback_data='stats_refresh_performance'),
                InlineKeyboardButton("🔙 بازگشت", callback_data='stats_overview')
            ]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard)
        admin_logger.info(f"[ADMIN] Performance stats viewed by {callback_query.from_user.id}")
    
    except Exception as e:
        admin_logger.error(f"Error in stats_performance_callback: {e}")
        await callback_query.answer("❌ خطا در دریافت آمار", show_alert=True)


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^stats_menu$'))
async def stats_menu_callback(client: Client, callback_query: CallbackQuery):
    """بازگشت به منوی آمار"""
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👥 آمار کاربران", callback_data='stats_users'),
            InlineKeyboardButton("📈 آمار درخواست‌ها", callback_data='stats_requests')
        ],
        [
            InlineKeyboardButton("⚡ آمار عملکرد", callback_data='stats_performance'),
            InlineKeyboardButton("🔄 بروزرسانی", callback_data='stats_refresh')
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_admin')
        ]
    ])
    
    await callback_query.message.edit_text(
        "📊 **آمار و گزارشات**\n\n"
        "انتخاب کنید:",
        reply_markup=keyboard
    )
    await callback_query.answer()


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^stats_refresh'))
async def stats_refresh_callback(client: Client, callback_query: CallbackQuery):
    """به‌روزرسانی آمار"""
    try:
        # پاک کردن cache
        clear_stats_cache()
        
        # تشخیص نوع آمار
        data = callback_query.data
        
        if 'overview' in data:
            await stats_overview_callback(client, callback_query)
        elif 'users' in data:
            await stats_users_callback(client, callback_query)
        elif 'requests' in data:
            await stats_requests_callback(client, callback_query)
        elif 'performance' in data:
            await stats_performance_callback(client, callback_query)
        else:
            await callback_query.answer("✅ Cache پاک شد", show_alert=True)
    
    except Exception as e:
        admin_logger.error(f"Error in stats_refresh_callback: {e}")
        await callback_query.answer("❌ خطا در بروزرسانی", show_alert=True)


# ==================== تنظیم پیام راهنما ====================

@Client.on_message(filters.user(ADMIN) & filters.regex(r'^📘 تنظیم راهنما$'), group=2)
async def admin_menu_help_message(_: Client, message: Message):
    """ورود به پنل تنظیم پیام راهنما"""
    user_id = message.from_user.id
    print(f"[DEBUG] Help message handler triggered by user {user_id}")
    admin_logger.info(f"[ADMIN] Help message setup started by {user_id}")
    
    # دریافت پیام راهنمای فعلی
    import json
    db = DB()
    help_data = db.get_bot_setting('help_message')
    
    if help_data:
        try:
            help_config = json.loads(help_data)
            content_type = help_config.get('type', 'text')
            status_text = "✅ فعال (سفارشی)"
        except:
            content_type = 'text'
            status_text = "⚠️ پیش‌فرض"
    else:
        content_type = 'text'
        status_text = "⚠️ پیش‌فرض"
    
    text = (
        "📘 <b>تنظیم پیام راهنما</b>\n\n"
        f"وضعیت فعلی: {status_text}\n"
        f"نوع محتوا: {content_type.upper()}\n\n"
        "💡 <b>راهنما:</b>\n"
        "• می‌توانید متن، عکس، ویدیو، گیف یا استیکر ارسال کنید\n"
        "• پیام شما به عنوان پاسخ /help نمایش داده می‌شود\n"
        "• برای بازگشت به پیام پیش‌فرض، از دکمه حذف استفاده کنید\n\n"
        "📤 <b>لطفاً پیام راهنمای جدید را ارسال کنید:</b>"
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👁 مشاهده فعلی", callback_data="view_help_message"),
            InlineKeyboardButton("🗑 حذف سفارشی", callback_data="delete_help_message")
        ],
        [InlineKeyboardButton("❌ لغو", callback_data="cancel_help_setup")]
    ])
    
    # تنظیم state برای دریافت پیام
    admin_step['help_setup'] = 1
    
    await message.reply_text(text, reply_markup=keyboard)


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^view_help_message$'))
async def view_help_message_callback(client: Client, callback_query: CallbackQuery):
    """نمایش پیام راهنمای فعلی"""
    try:
        import json
        db = DB()
        help_data = db.get_bot_setting('help_message')
        
        if not help_data:
            await callback_query.answer("⚠️ پیام سفارشی تنظیم نشده است", show_alert=True)
            return
        
        help_config = json.loads(help_data)
        content_type = help_config.get('type', 'text')
        
        await callback_query.answer("در حال ارسال...")
        
        if content_type == 'text':
            await callback_query.message.reply_text(
                f"📘 <b>پیام راهنمای فعلی:</b>\n\n{help_config.get('text', '')}"
            )
        elif content_type == 'photo':
            await callback_query.message.reply_photo(
                photo=help_config.get('file_id'),
                caption=help_config.get('caption', '')
            )
        elif content_type == 'video':
            await callback_query.message.reply_video(
                video=help_config.get('file_id'),
                caption=help_config.get('caption', '')
            )
        elif content_type == 'animation':
            await callback_query.message.reply_animation(
                animation=help_config.get('file_id'),
                caption=help_config.get('caption', '')
            )
        elif content_type == 'sticker':
            await callback_query.message.reply_sticker(
                sticker=help_config.get('file_id')
            )
        elif content_type == 'document':
            await callback_query.message.reply_document(
                document=help_config.get('file_id'),
                caption=help_config.get('caption', '')
            )
    
    except Exception as e:
        admin_logger.error(f"Error viewing help message: {e}")
        await callback_query.answer("❌ خطا در نمایش پیام", show_alert=True)


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^delete_help_message$'))
async def delete_help_message_callback(client: Client, callback_query: CallbackQuery):
    """حذف پیام راهنمای سفارشی"""
    try:
        db = DB()
        db.delete_bot_setting('help_message')
        admin_step['help_setup'] = 0
        
        await callback_query.edit_message_text(
            "✅ <b>پیام راهنمای سفارشی حذف شد</b>\n\n"
            "از این پس پیام پیش‌فرض نمایش داده می‌شود.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 پنل ادمین", callback_data="back_to_admin")
            ]])
        )
        admin_logger.info(f"[ADMIN] Help message deleted by {callback_query.from_user.id}")
    
    except Exception as e:
        admin_logger.error(f"Error deleting help message: {e}")
        await callback_query.answer("❌ خطا در حذف پیام", show_alert=True)


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^cancel_help_setup$'))
async def cancel_help_setup_callback(client: Client, callback_query: CallbackQuery):
    """لغو تنظیم پیام راهنما"""
    admin_step['help_setup'] = 0
    await callback_query.edit_message_text(
        "❌ <b>تنظیم پیام راهنما لغو شد</b>\n\n"
        "می‌توانید از پنل ادمین دوباره شروع کنید.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 پنل ادمین", callback_data="back_to_admin")
        ]])
    )


# Handler برای دریافت پیام راهنمای جدید
@Client.on_message(filters.user(ADMIN) & filters.private, group=6)
async def handle_help_message_input(client: Client, message: Message):
    """دریافت پیام راهنمای جدید از ادمین"""
    
    # بررسی state
    if admin_step.get('help_setup') != 1:
        return
    
    # بررسی دکمه‌های ادمین
    admin_buttons = {
        "🛠 مدیریت", "📊 آمار کاربران", "🖥 وضعیت سرور",
        "📢 ارسال همگانی", "📢 تنظیم اسپانسر", "💬 پیام انتظار",
        "🍪 مدیریت کوکی", "📺 تنظیم تبلیغات", "✅ وضعیت ربات",
        "📘 تنظیم راهنما", "⬅️ بازگشت", "❌ لغو"
    }
    
    if message.text and message.text.strip() in admin_buttons:
        return
    
    try:
        import json
        db = DB()
        help_config = {}
        
        if message.text:
            help_config['type'] = 'text'
            help_config['text'] = message.text
        elif message.photo:
            help_config['type'] = 'photo'
            help_config['file_id'] = message.photo.file_id
            help_config['caption'] = message.caption or ''
        elif message.video:
            help_config['type'] = 'video'
            help_config['file_id'] = message.video.file_id
            help_config['caption'] = message.caption or ''
        elif message.animation:
            help_config['type'] = 'animation'
            help_config['file_id'] = message.animation.file_id
            help_config['caption'] = message.caption or ''
        elif message.sticker:
            help_config['type'] = 'sticker'
            help_config['file_id'] = message.sticker.file_id
        elif message.document:
            help_config['type'] = 'document'
            help_config['file_id'] = message.document.file_id
            help_config['caption'] = message.caption or ''
        else:
            await message.reply_text("❌ نوع پیام پشتیبانی نمی‌شود. لطفاً متن، عکس، ویدیو، گیف یا استیکر ارسال کنید.")
            return
        
        # ذخیره در دیتابیس
        success = db.set_bot_setting('help_message', json.dumps(help_config, ensure_ascii=False))
        
        if success:
            admin_step['help_setup'] = 0
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("👁 مشاهده", callback_data="view_help_message"),
                    InlineKeyboardButton("🏠 پنل ادمین", callback_data="back_to_admin")
                ]
            ])
            
            await message.reply_text(
                "✅ <b>پیام راهنما با موفقیت تنظیم شد!</b>\n\n"
                "از این پس کاربران با دستور /help این پیام را دریافت می‌کنند.",
                reply_markup=keyboard
            )
            admin_logger.info(f"[ADMIN] Help message updated by {message.from_user.id}, type: {help_config['type']}")
        else:
            await message.reply_text("❌ خطا در ذخیره پیام. لطفاً دوباره تلاش کنید.")
    
    except Exception as e:
        admin_logger.error(f"Error handling help message input: {e}")
        await message.reply_text("❌ خطای غیرمنتظره. لطفاً دوباره تلاش کنید.")
