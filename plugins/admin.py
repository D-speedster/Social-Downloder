import time
import logging

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
import json, os
from pyrogram import Client, filters
import re
from pyrogram.types import Message, CallbackQuery
from pyrogram.errors import FloodWait
import sys, requests
import instaloader
from instaloader import InstaloaderException
from datetime import datetime as _dt
from plugins import constant
from plugins.sqlite_db_wrapper import DB

import shutil, platform, asyncio, os as _os
import psutil
import subprocess

# Configure Admin logger
os.makedirs('./logs', exist_ok=True)
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

admin_step = {
    'sp': 2,
    # NEW: broadcast state machine
    'broadcast': 0,  # 0: idle, 1: choosing type, 2: waiting for content, 3: waiting for confirmation
    'broadcast_type': '',  # 'normal' or 'forward'
    'broadcast_content': None,  # stored message for confirmation
    # NEW: waiting message management
    'waiting_msg': 0,
    'waiting_msg_type': '',
    'waiting_msg_platform': '',
    # NEW: advertisement management
    'advertisement': 0,  # 0: idle, 1: waiting for content, 2: waiting for position
    'ad_content_type': '',
    'ad_file_id': '',
    'ad_caption': '',
}

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
        ],
        [
            InlineKeyboardButton("🍪 مدیریت کوکی", callback_data='cookie_mgmt'),
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
    return ReplyKeyboardMarkup(
        [
            ["📊 آمار کاربران", "🖥 وضعیت سرور"],
            ["🔌 بررسی پروکسی"],
            ["📢 ارسال همگانی", "📢 تنظیم اسپانسر"],
            ["💬 پیام انتظار"],
            ["🍪 مدیریت کوکی"],
            ["📺 تنظیم تبلیغات", "✅ وضعیت ربات"],
            ["⬅️ بازگشت"],
        ],
        resize_keyboard=True
    )


@Client.on_message(filters.user(ADMIN) & filters.regex(r'^🛠 مدیریت$'))
async def admin_menu_root_msg(_: Client, message: Message):
    print("[ADMIN] open management via text by", message.from_user.id)
    await message.reply_text("پنل مدیریت", reply_markup=admin_reply_kb())


@Client.on_message(filters.user(ADMIN) & filters.regex(r'^📊 آمار کاربران$'))
async def admin_menu_stats(_: Client, message: Message):
    print("[ADMIN] stats via text by", message.from_user.id)
    stats = DB().get_system_stats()
    text = (
        "\u200F<b>📊 آمار سیستم</b>\n\n"
        f"👥 مجموع کاربران: <b>{stats.get('total_users', 0)}</b>\n"
        f"🆕 کاربران امروز: <b>{stats.get('users_today', 0)}</b>\n"
        f"✅ کاربران فعال امروز: <b>{stats.get('active_today', 0)}</b>\n"
        f"📈 مجموع درخواست‌ها: <b>{stats.get('total_requests_sum', 0)}</b>\n"
        f"⛔️ کاربران در محدودیت: <b>{stats.get('blocked_count', 0)}</b>\n\n"
        f"🗂 مجموع وظایف: <b>{stats.get('total_jobs', 0)}</b>\n"
        f"⏳ در انتظار: <b>{stats.get('jobs_pending', 0)}</b>\n"
        f"🟡 آماده: <b>{stats.get('jobs_ready', 0)}</b>\n"
        f"✅ تکمیل‌شده: <b>{stats.get('jobs_completed', 0)}</b>\n"
    )
    await message.reply_text(text, reply_markup=admin_reply_kb())


@Client.on_message(filters.user(ADMIN) & filters.regex(r'^🖥 وضعیت سرور$'))
async def admin_menu_server(_: Client, message: Message):
    print("[ADMIN] server status via text by", message.from_user.id)
    await message.reply_text(_server_status_text(), reply_markup=admin_reply_kb())


# --- بررسی پروکسی‌ها ---
import socket

def check_proxy_port(host='127.0.0.1', port=1084):
    """Check if proxy port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

@Client.on_message(filters.user(ADMIN) & filters.regex(r'^🔌 بررسی پروکسی$'))
async def admin_menu_proxy_check(_: Client, message: Message):
    # Check the fixed proxy port 1084
    proxy_host = '127.0.0.1'
    proxy_port = 1084
    
    is_open = check_proxy_port(proxy_host, proxy_port)
    
    if is_open:
        status_text = f"🟢 پروکسی فعال است\n\n📍 آدرس: socks5h://{proxy_host}:{proxy_port}\n🔌 وضعیت پورت {proxy_port}: باز\n\n✅ ربات از این پروکسی برای دانلود استفاده می‌کند."
    else:
        status_text = f"🔴 پروکسی غیرفعال است\n\n📍 آدرس: socks5h://{proxy_host}:{proxy_port}\n🔌 وضعیت پورت {proxy_port}: بسته\n\n⚠️ لطفاً سرویس پروکسی را روشن کنید."
    
    await message.reply_text(status_text, reply_markup=admin_reply_kb())


@Client.on_message(filters.user(ADMIN) & filters.regex(r'^📢 ارسال همگانی$'))
async def admin_menu_broadcast(_: Client, message: Message):
    print("[ADMIN] broadcast start via text by", message.from_user.id)
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
    print("[ADMIN] sponsor setup via text by", message.from_user.id)
    await message.reply_text(
        "ابتدا ربات را در چنل مورد نظر ادمین کن سپس شناسه چنل را ارسال کن.\n"
        "فرمت‌های مجاز:\n"
        "- @username (کانال عمومی)\n"
        "- -100xxxxxxxxxx (آی‌دی عددی، مناسب کانال خصوصی)\n"
        "- لینک t.me/username (به @username تبدیل می‌شود)\n\n"
        "نکته: لینک دعوت خصوصی (+) پشتیبانی نمی‌شود؛ برای کانال خصوصی از آی‌دی عددی استفاده کنید.\n\n"
        "برای لغو، روی «❌ لغو» بزنید یا /cancel.",
        reply_markup=admin_reply_kb()
    )
    admin_step['sp'] = 1


# Handler for old power toggle button removed - replaced with new status system


# Handler for old sponsor toggle button removed - replaced with new status system


# Handler for old advertisement toggle button removed - replaced with new status system


@Client.on_message(filters.user(ADMIN) & filters.regex(r'^✅ وضعیت ربات$'))
async def admin_menu_bot_status(_: Client, message: Message):
    print("[ADMIN] bot status menu accessed by", message.from_user.id)
    
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
    
    print(f"[ADMIN] Status toggle: {action} by {user_id}")
    
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
            from .db_path_manager import db_path_manager
            json_db_path = db_path_manager.get_json_db_path()
            
            # Create backup before writing
            backup_path = json_db_path + '.bak'
            if os.path.exists(json_db_path):
                shutil.copy2(json_db_path, backup_path)
            
            with open(json_db_path, 'w', encoding='utf-8') as outfile:
                json.dump(data, outfile, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to write status change: {e}")
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
        print(f"Error in status toggle: {e}")
        await callback_query.answer("❌ خطا در تغییر وضعیت!", show_alert=True)


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^refresh_status$'))
async def refresh_status_callback(client: Client, callback_query: CallbackQuery):
    """Handle refresh status callback"""
    await refresh_status_display(client, callback_query)
    await callback_query.answer("🔄 وضعیت بروزرسانی شد!")


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^back_to_admin$'))
async def back_to_admin_callback(client: Client, callback_query: CallbackQuery):
    """Handle back to admin panel callback"""
    await callback_query.message.edit_text(
        "🛠 **پنل مدیریت**\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(admin_inline_maker())
    )
    await callback_query.answer()


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
    print("[ADMIN] advertisement setup via text by", message.from_user.id)
    
    # Get current advertisement settings
    ad_settings = data.get('advertisement', {})
    enabled = ad_settings.get('enabled', False)
    content_type = ad_settings.get('content_type', 'text')
    position = ad_settings.get('position', 'after')
    
    status_text = "🟢 فعال" if enabled else "🔴 غیرفعال"
    position_text = "بالای محتوا" if position == "before" else "پایین محتوا"
    
    text = (
        "📺 <b>تنظیم تبلیغات</b>\n\n"
        f"وضعیت: {status_text}\n"
        f"نوع محتوا: {content_type.upper()}\n"
        f"مکان نمایش: {position_text}\n\n"
        "برای تنظیم تبلیغات جدید، محتوای مورد نظر خود را ارسال کنید:\n\n"
        "• متن ساده\n"
        "• عکس (با یا بدون متن)\n"
        "• استیکر\n"
        "• GIF\n"
        "• ویدیو\n"
        "• موزیک\n\n"
        "برای لغو /cancel را بفرستید."
    )
    
    admin_step['advertisement'] = 1
    await message.reply_text(text, reply_markup=admin_reply_kb())

# منوی کوکی یوتیوب حذف شد

# Instagram cookie management removed - using API now

@Client.on_message(filters.user(ADMIN) & filters.regex(r'^⬅️ بازگشت$'))
async def admin_menu_back(_: Client, message: Message):
    print("[ADMIN] back pressed by", message.from_user.id)
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
    print("admin panel")
    await message.reply_text(
        "پنل مدیریت",
        reply_markup=admin_reply_kb()
    )


# Admin root handler removed - now using reply keyboard directly from start


async def set_sp_custom(_, __, message: Message):
    try:
        # Only active when we are in sponsor input step
        if admin_step.get('sp') != 1:
            return False
        # Only consider messages from admins
        if not message.from_user or message.from_user.id not in ADMIN:
            return False
        # Only allow text messages
        if not message.text:
            return False
        # Ignore admin panel buttons texts (reply keyboard)
        if message.text.strip() in {
            "🛠 مدیریت","📊 آمار کاربران","🖥 وضعیت سرور","🔌 بررسی پروکسی",
            "📢 ارسال همگانی","📢 تنظیم اسپانسر","💬 پیام انتظار","🍪 مدیریت کوکی",
            "📺 تنظیم تبلیغات","✅ وضعیت ربات","⬅️ بازگشت","❌ لغو",
            "🔝 بالای محتوا","🔻 پایین محتوا"
        }:
            return False
        # Do NOT capture commands like /language, /start, etc.
        if message.text.strip().startswith('/'):
            return False
        return True
    except Exception:
        return False


sp_filter = filters.create(set_sp_custom)


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
async def cancel_broadcast(_, message: Message):
    if admin_step.get('broadcast') > 0:
        admin_step['broadcast'] = 0
        admin_step['broadcast_type'] = ''
        admin_step['broadcast_content'] = None
        await message.reply_text(
            "❌ عملیات ارسال همگانی لغو شد.",
            reply_markup=admin_reply_kb()
        )
    else:
        await message.reply_text("عملیات فعالی برای لغو وجود ندارد.")


@Client.on_message(sp_filter & filters.user(ADMIN), group=6)
async def set_sp(_: Client, message: Message):
     raw = (message.text or '').strip()
     val = raw
     # Normalize input
     if re.match(r'^(https?://)?t\.me/[A-Za-z0-9_]{4,}$', raw):
         # Extract username from t.me link
         uname = re.sub(r'^(https?://)?t\.me/', '', raw).strip('/')
         if uname.startswith('+'):
             await message.reply_text("لینک دعوت خصوصی (+) پشتیبانی نمی‌شود. لطفاً @username یا آی‌دی عددی -100… را ارسال کنید.")
             return
         val = '@' + uname
     elif re.match(r'^@[A-Za-z0-9_]{4,}$', raw):
         val = raw
     elif re.match(r'^-100\d{8,14}$', raw):
         val = raw
     else:
         await message.reply_text("فرمت وارد شده صحیح نیست. نمونه‌ها: @example یا -1001234567890 یا https://t.me/example")
         return

     data['sponser'] = val
     from .db_path_manager import db_path_manager
     json_db_path = db_path_manager.get_json_db_path()
     
     with open(json_db_path, "w", encoding='utf-8') as outfile:
         json.dump(data, outfile, indent=4, ensure_ascii=False)
     await message.reply_text("اسپانسر بات با موفقیت تغییر کرد ✅")
     admin_step['sp'] = 0


# Remaining callback handler code removed - now handled by message handlers


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
        print(f"[ERROR] Failed to save waiting message: {e}")
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
    """Handle advertisement content input from admin"""
    try:
        if message.text and message.text.strip() in {
            "🛠 مدیریت","📊 آمار کاربران","🖥 وضعیت سرور","🔌 بررسی پروکسی",
            "📢 ارسال همگانی","📢 تنظیم اسپانسر","💬 پیام انتظار","🍪 مدیریت کوکی",
            "📺 تنظیم تبلیغات","✅ وضعیت ربات","⬅️ بازگشت","❌ لغو",
            "🔝 بالای محتوا","🔻 پایین محتوا"
        }:
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
            # Store text content for later save
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
        print(f"[ERROR] Advertisement content processing error: {e}")
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

@Client.on_message(ad_content_filter & filters.user(ADMIN), group=6)
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

        # Persist to database.json safely
        try:
            from .db_path_manager import db_path_manager
            json_db_path = db_path_manager.get_json_db_path()
            
            backup_path = json_db_path + '.bak'
            if os.path.exists(json_db_path):
                shutil.copy2(json_db_path, backup_path)
            data['advertisement'] = ad_settings
            with open(json_db_path, 'w', encoding='utf-8') as outfile:
                json.dump(data, outfile, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[ADMIN] Failed to save advertisement settings: {e}")
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
        print(f"[ADMIN] Error in ad position handler: {e}")
        await message.reply_text("❌ خطای غیرمنتظره در تنظیم تبلیغات.")
def _server_status_text():
    """Override: Build improved server status text without disk line, include network speed."""
    try:
        # Local helper to format bytes into human-readable units
        def format_bytes(n):
            try:
                units = ['B', 'KB', 'MB', 'GB', 'TB']
                n = int(n) if n is not None else 0
                i = 0
                while n >= 1024 and i < len(units) - 1:
                    n /= 1024.0
                    i += 1
                return f"{n:.2f} {units[i]}"
            except Exception:
                return str(n)
        import time as _t
        import platform as _pf
        cpu_percent = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        # Approximate network throughput over 1s
        net1 = psutil.net_io_counters()
        _t.sleep(1)
        net2 = psutil.net_io_counters()
        up_bps = max(0, net2.bytes_sent - net1.bytes_sent)
        down_bps = max(0, net2.bytes_recv - net1.bytes_recv)
        up_speed = f"{format_bytes(up_bps)}/s"
        down_speed = f"{format_bytes(down_bps)}/s"

        # OS and uptime
        os_line = f"🖥 سیستم‌عامل: {_pf.system()} {_pf.release()}"
        try:
            boot_ts = psutil.boot_time()
            uptime_sec = int(_t.time() - boot_ts)
            days = uptime_sec // 86400
            hours = (uptime_sec % 86400) // 3600
            minutes = (uptime_sec % 3600) // 60
            uptime_line = f"⏱ زمان روشن بودن: {days}روز {hours}ساعت {minutes}دقیقه"
        except Exception:
            uptime_line = "⏱ زمان روشن بودن: نامشخص"

        mem_line = f"🧠 استفاده از حافظه: {format_bytes(mem.used)}/{format_bytes(mem.total)} ({mem.percent}%)"
        cpu_line = f"⚙️ مصرف CPU: {cpu_percent}%"
        net_line = f"🌐 سرعت شبکه تقریبی: ↑ {up_speed} | ↓ {down_speed}"

        return "\n".join([
            cpu_line,
            os_line,
            uptime_line,
            mem_line,
            net_line
        ])
    except Exception as e:
        return f"❌ خطا در دریافت وضعیت سرور: {e}"
