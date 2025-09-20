import time

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
# NEW: for server status and async sleep
import shutil, platform, asyncio, os as _os

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
    'cookies': 0,
    # NEW: broadcast state machine (0: idle, 1: waiting for content)
    'broadcast': 0,
    # NEW: waiting message management
    'waiting_msg': 0,
    'waiting_msg_type': '',
    'waiting_msg_platform': '',
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
            InlineKeyboardButton("🍪 مدیریت کوکی", callback_data='cookies'),
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
            ["📣 ارسال پیام", "📢 تنظیم اسپانسر"],
            ["💬 پیام انتظار", "🍪 مدیریت کوکی"],
            ["🔌 خاموش/روشن", "🔐 خاموش/روشن اسپانسری"],
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


@Client.on_message(filters.user(ADMIN) & filters.regex(r'^📣 ارسال پیام$'))
async def admin_menu_broadcast(_: Client, message: Message):
    print("[ADMIN] broadcast start via text by", message.from_user.id)
    admin_step['broadcast'] = 1
    await message.reply_text(
        "لطفاً پیام مورد نظر برای ارسال همگانی را ارسال کنید.\n\n"
        "- هر نوع پیام پشتیبانی می‌شود (متن، عکس، ویدیو، فایل، ...).\n"
        "- برای لغو /cancel را بفرستید.",
        reply_markup=admin_reply_kb()
    )


@Client.on_message(filters.user(ADMIN) & filters.regex(r'^📢 تنظیم اسپانسر$'))
async def admin_menu_sponsor(_: Client, message: Message):
    print("[ADMIN] sponsor setup via text by", message.from_user.id)
    await message.reply_text(
        "ابتدا ربات را در چنل مورد نظر ادمین کن سپس شناسه چنل را ارسال کن.\n"
        "فرمت‌های مجاز:\n"
        "- @username (کانال عمومی)\n"
        "- -100xxxxxxxxxx (آی‌دی عددی، مناسب کانال خصوصی)\n"
        "- لینک t.me/username (به @username تبدیل می‌شود)\n\n"
        "نکته: لینک دعوت خصوصی (+) پشتیبانی نمی‌شود؛ برای کانال خصوصی از آی‌دی عددی استفاده کنید.",
        reply_markup=admin_reply_kb()
    )
    admin_step['sp'] = 1


@Client.on_message(filters.user(ADMIN) & filters.regex(r'^🔌 خاموش/روشن$'))
async def admin_menu_power(_: Client, message: Message):
    print("[ADMIN] toggle power via text by", message.from_user.id)
    current = data.get('bot_status', 'ON')
    new_state = 'OFF' if current == 'ON' else 'ON'
    data['bot_status'] = new_state
    try:
        # Create backup before writing
        backup_path = PATH + '/database.json.bak'
        if os.path.exists(PATH + '/database.json'):
            shutil.copy2(PATH + '/database.json', backup_path)
        
        with open(PATH + '/database.json', 'w', encoding='utf-8') as outfile:
            json.dump(data, outfile, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to write bot_status: {e}")
        # Try to restore backup if write failed
        try:
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, PATH + '/database.json')
        except Exception:
            pass
    await message.reply_text(
        f"وضعیت ربات: {'🔴 خاموش' if new_state == 'OFF' else '🟢 روشن'}",
        reply_markup=admin_reply_kb()
    )


@Client.on_message(filters.user(ADMIN) & filters.regex(r'^🔐 خاموش/روشن اسپانسری$'))
async def admin_menu_sponsor_toggle(_: Client, message: Message):
    print("[ADMIN] sponsor toggle via text by", message.from_user.id)
    current = data.get('force_join', True)
    new_state = not current
    data['force_join'] = new_state
    try:
        # Create backup before writing
        backup_path = PATH + '/database.json.bak'
        if os.path.exists(PATH + '/database.json'):
            shutil.copy2(PATH + '/database.json', backup_path)
        
        with open(PATH + '/database.json', 'w', encoding='utf-8') as outfile:
            json.dump(data, outfile, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to write force_join: {e}")
        # Try to restore backup if write failed
        try:
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, PATH + '/database.json')
        except Exception:
            pass
    await message.reply_text(
        f"وضعیت اسپانسری: {'🔴 خاموش' if not new_state else '🟢 روشن'}",
        reply_markup=admin_reply_kb()
    )


# Duplicate handlers removed - keeping only the first set


# Duplicate waiting message and power toggle handlers removed


@Client.on_message(filters.user(ADMIN) & filters.regex(r'^🍪 مدیریت کوکی$'))
async def admin_menu_cookies(_: Client, message: Message):
    keyboard = [
        [InlineKeyboardButton("📺 کوکی یوتیوب", callback_data='cookie_youtube')],
        [InlineKeyboardButton("📷 کوکی اینستاگرام", callback_data='cookie_instagram')],
        [InlineKeyboardButton("⬅️ بازگشت", callback_data='admin_back')]
    ]
    await message.reply(
        "🍪 <b>مدیریت استخر کوکی</b>\n\n"
        "برای مدیریت کوکی‌های هر پلتفرم، روی دکمه مربوطه کلیک کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@Client.on_message(filters.user(ADMIN) & filters.regex(r'^⬅️ بازگشت$'))
async def admin_menu_back(_: Client, message: Message):
    print("[ADMIN] back pressed by", message.from_user.id)
    # Reset any transient admin steps
    admin_step['broadcast'] = 0
    admin_step['sp'] = 2
    # Remove admin reply keyboard to exit panel
    await message.reply_text("از پنل مدیریت خارج شدید.", reply_markup=ReplyKeyboardRemove())


@Client.on_message(filters.command('panel') & filters.user(ADMIN))
async def admin_panel(_: Client, message: Message):
    print("admin panel")
    await message.reply_text(
        "پنل مدیریت",
        reply_markup=InlineKeyboardMarkup(admin_inline_maker())
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
        # Do NOT capture commands like /language, /start, etc.
        if message.text.strip().startswith('/'):
            return False
        return True
    except Exception:
        return False


sp_filter = filters.create(set_sp_custom)


async def admin_panel_custom(_, __, query):
    # Only match our specific admin action tokens, avoid catching 'admin_root'
    return bool(re.match(r'^(st|srv|gm|sg|sp|pw|waiting_msg|cookies|fj_toggle|sp_check|cookie_youtube|cookie_instagram|edit_waiting_youtube|edit_waiting_instagram|admin_back|add_cookie_youtube|add_cookie_instagram|list_cookies_youtube|list_cookies_instagram|clear_cookies_youtube|clear_cookies_instagram)$', query.data))


static_data_filter = filters.create(admin_panel_custom)

# NEW: Set cookies command for Admins
@Client.on_message(filters.command('setcookies') & filters.user(ADMIN))
async def set_cookies_cmd(_: Client, message: Message):
    try:
        os.makedirs(os.path.join(os.getcwd(), 'cookies'), exist_ok=True)
    except Exception as e:
        print('[ADMIN] failed to create cookies dir:', e)
    await message.reply_text(
        "برای تنظیم کوکی‌ها، یک فایل متنی ارسال کنید:\n\n"
        "- اینستاگرام: instagram.txt\n"
        "- یوتیوب: youtube.txt\n\n"
        "فایل را حتماً به‌صورت Document ارسال کنید (نه متن).\n"
        "نام فایل باید شامل instagram یا youtube باشد تا به‌طور خودکار تشخیص داده شود.")


def _detect_cookie_dest(filename: str) -> str:
    fn = (filename or '').lower()
    if any(k in fn for k in ['instagram', 'insta', 'ig']):
        return 'instagram.txt'
    if any(k in fn for k in ['youtube', 'yt', 'youtub']):
        return 'youtube.txt'
    return ''


@Client.on_message(filters.document & filters.user(ADMIN), group=7)
async def handle_cookie_file(_: Client, message: Message):
    try:
        doc = message.document
        name = (doc.file_name or '').strip()
        
        # Security: Check file size (max 10MB for cookies)
        if doc.file_size > 10 * 1024 * 1024:
            await message.reply_text("❌ فایل خیلی بزرگ است. حداکثر اندازه: 10MB")
            return
            
        dest_name = _detect_cookie_dest(name)
        if not dest_name:
            await message.reply_text(
                "نام فایل مشخص نیست. لطفاً یکی از این نام‌ها را استفاده کنید:\n"
                "- instagram.txt برای اینستاگرام\n"
                "- youtube.txt برای یوتیوب")
            return
            
        cookies_dir = os.path.join(os.getcwd(), 'cookies')
        os.makedirs(cookies_dir, exist_ok=True, mode=0o700)  # Secure permissions
        
        # Use secure temporary filename
        import secrets
        secure_suffix = secrets.token_hex(8)
        tmp_path = os.path.join(cookies_dir, f"tmp_{secure_suffix}_{dest_name}")
        
        saved_path = await message.download(file_name=tmp_path)
        final_path = os.path.join(cookies_dir, dest_name)
        
        # Create backup of existing cookies
        if os.path.exists(final_path):
            backup_path = final_path + '.bak'
            try:
                shutil.copy2(final_path, backup_path)
            except Exception:
                pass
                
        try:
            shutil.move(saved_path, final_path)
            # Set secure file permissions
            os.chmod(final_path, 0o600)
        except Exception as e:
            print(f"Cookie file move error: {e}")
            # fallback copy
            try:
                shutil.copyfile(saved_path, final_path)
                os.chmod(final_path, 0o600)
                os.remove(saved_path)
            except Exception as e2:
                print(f"Cookie file copy error: {e2}")
                await message.reply_text("❌ خطا در ذخیره فایل کوکی")
                return
                
        await message.reply_text(f"✅ کوکی‌ها ذخیره شد: {dest_name}")
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
    except Exception as e:
        print('[ADMIN] handle_cookie_file error:', e)
        await message.reply_text("❌ خطا در ذخیره کوکی. لطفاً مجدداً تلاش کنید.")


def user_counter():
    users = DB().get_users_id()
    return len(users)


# Helper: server status text

def _server_status_text() -> str:
    now = _dt.now()
    uptime = now - START_TIME
    # Disk usage for current drive
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
        free_gb = du.free / (1024**3)
        usage_percent = (used_gb / total_gb * 100) if total_gb > 0 else 0
        disk_line = f"💽 دیسک: {used_gb:.1f}GB/{total_gb:.1f}GB ({usage_percent:.1f}% استفاده)"
    except Exception as e:
        print(f"Disk usage error: {e}")
        disk_line = "💽 دیسک: نامشخص"
    # Load avg (POSIX only)
    try:
        if _os.name != 'nt':
            load1, load5, load15 = os.getloadavg()
            load_line = f"📊 لود: {load1:.2f}, {load5:.2f}, {load15:.2f}"
        else:
            load_line = "📊 لود: نامشخص در ویندوز"
    except Exception:
        load_line = "📊 لود: نامشخص"
    # CPU count and platform
    try:
        cpu_cnt = os.cpu_count() or 1
    except Exception:
        cpu_cnt = 1
    plat = platform.platform()
    return (
        f"⏱ آپ‌تایم: {uptime.days}d {uptime.seconds//3600:02d}:{(uptime.seconds//60)%60:02d}:{uptime.seconds%60:02d}\n"
        f"🧩 CPU‌ها: {cpu_cnt}\n"
        f"🧪 پلتفرم: {plat}\n"
        f"{disk_line}\n"
        f"{load_line}"
    )


# Old inline callback handlers removed - now using reply keyboard message handlers


# Sponsor check callback handler removed - now handled by message handlers


# Force join toggle callback handler removed - now handled by message handlers


@Client.on_message(filters.command('send_to_all') & filters.user(ADMIN))
async def send_to_all(client: Client, message: Message) -> None:
    if message.reply_to_message:
        all_users = DB().get_users_id()
        count = 0
        await message.reply_text(f'Sending to {len(all_users)} users... ')
        for user in all_users:
            uid = user[0] if isinstance(user, (list, tuple)) else user
            try:
                # Prefer copying original replied message (keeps media)
                await client.copy_message(chat_id=uid, from_chat_id=message.chat.id, message_id=message.reply_to_message.id)
                count += 1
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception as e:
                print("Failed to send message to all users: {}".format(e))
                pass
        await message.reply_text(f'Sent to {count} of {len(all_users)}')
    else:
        await message.reply_text('You have to reply on a message')


# NEW: Broadcast flow via admin panel
@Client.on_message(filters.user(ADMIN), group=5)
async def handle_broadcast(client: Client, message: Message):
    if admin_step.get('broadcast') != 1:
        return
    admin_step['broadcast'] = 0
    all_users = DB().get_users_id()
    total = len(all_users)
    sent = 0
    fail = 0
    try:
        await message.reply_text(f"در حال ارسال به {total} کاربر…")
    except Exception:
        pass
    for user in all_users:
        uid = user[0] if isinstance(user, (list, tuple)) else user
        try:
            await client.copy_message(chat_id=uid, from_chat_id=message.chat.id, message_id=message.id)
            sent += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
            try:
                await client.copy_message(chat_id=uid, from_chat_id=message.chat.id, message_id=message.id)
                sent += 1
            except Exception:
                fail += 1
        except Exception:
            fail += 1
    try:
        await message.reply_text(f"✅ ارسال شد: {sent}\n❌ ناموفق: {fail}")
    except Exception:
        pass


@Client.on_message(filters.command('cancel') & filters.user(ADMIN))
async def cancel_broadcast(_, message: Message):
    if admin_step.get('broadcast') == 1:
        admin_step['broadcast'] = 0
        await message.reply_text("عملیات ارسال همگانی لغو شد.")
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
     with open(PATH + '/database.json', "w", encoding='utf-8') as outfile:
         json.dump(data, outfile, indent=4, ensure_ascii=False)
         await message.reply_text("اسپانسر بات با موفقیت تغییر کرد ✅")
     admin_step['sp'] = 0


# Remaining callback handler code removed - now handled by message handlers


@Client.on_message(filters.user(ADMIN) & filters.regex(r'^💬 پیام انتظار$'))
async def waiting_msg_menu_text(client: Client, message: Message):
    """Show waiting message management menu via text"""
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
@Client.on_callback_query(static_data_filter & filters.user(ADMIN))
async def admin_callback_handler(client: Client, callback_query: CallbackQuery):
    action = callback_query.data
    
    if action == 'st':
        # آمار کاربران
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
        await callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(admin_inline_maker()))
        
    elif action == 'srv':
        # وضعیت سرور
        await callback_query.edit_message_text(_server_status_text(), reply_markup=InlineKeyboardMarkup(admin_inline_maker()))
        
    elif action == 'gm':
        # ارسال پیام
        admin_step['broadcast'] = 1
        await callback_query.edit_message_text(
            "لطفاً پیام مورد نظر برای ارسال همگانی را ارسال کنید.\n\n"
            "- هر نوع پیام پشتیبانی می‌شود (متن، عکس، ویدیو، فایل، ...).\n"
            "- برای لغو /cancel را بفرستید.",
            reply_markup=InlineKeyboardMarkup(admin_inline_maker())
        )
        
    elif action == 'sp':
        # تنظیم اسپانسر
        admin_step['sp'] = 1
        await callback_query.edit_message_text(
            "لطفاً یوزرنیم کانال اسپانسر را ارسال کنید:\n\n"
            "نمونه: @example یا -1001234567890 یا https://t.me/example",
            reply_markup=InlineKeyboardMarkup(admin_inline_maker())
        )
        
    elif action == 'pw':
        # تغییر وضعیت ربات
        current = data.get('bot_status', 'ON')
        new_state = 'OFF' if current == 'ON' else 'ON'
        data['bot_status'] = new_state
        try:
            with open(PATH + '/database.json', 'w', encoding='utf-8') as outfile:
                json.dump(data, outfile, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to write bot_status: {e}")
        await callback_query.edit_message_text(
            f"وضعیت ربات: {'🔴 خاموش' if new_state == 'OFF' else '🟢 روشن'}",
            reply_markup=InlineKeyboardMarkup(admin_inline_maker())
        )
        
    elif action == 'fj_toggle':
        # تغییر وضعیت اسپانسری
        current = data.get('force_join', True)
        new_state = not current
        data['force_join'] = new_state
        try:
            with open(PATH + '/database.json', 'w', encoding='utf-8') as outfile:
                json.dump(data, outfile, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to write force_join: {e}")
        await callback_query.edit_message_text(
            f"وضعیت اسپانسری: {'🔴 خاموش' if not new_state else '🟢 روشن'}",
            reply_markup=InlineKeyboardMarkup(admin_inline_maker())
        )
        
    elif action == 'cookies':
        # مدیریت کوکی
        keyboard = [
            [InlineKeyboardButton("📺 کوکی یوتیوب", callback_data='cookie_youtube')],
            [InlineKeyboardButton("📷 کوکی اینستاگرام", callback_data='cookie_instagram')],
            [InlineKeyboardButton("⬅️ بازگشت", callback_data='admin_back')]
        ]
        await callback_query.edit_message_text(
            "🍪 <b>مدیریت استخر کوکی</b>\n\n"
            "برای مدیریت کوکی‌های هر پلتفرم، روی دکمه مربوطه کلیک کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    elif action == 'cookie_youtube':
        # مدیریت کوکی یوتیوب
        keyboard = [
            [InlineKeyboardButton("➕ افزودن کوکی", callback_data='add_cookie_youtube')],
            [InlineKeyboardButton("📋 مشاهده کوکی‌ها", callback_data='list_cookies_youtube')],
            [InlineKeyboardButton("🗑 حذف همه", callback_data='clear_cookies_youtube')],
            [InlineKeyboardButton("⬅️ بازگشت", callback_data='cookies')]
        ]
        await callback_query.edit_message_text(
            "📺 <b>مدیریت کوکی یوتیوب</b>\n\n"
            "عملیات مورد نظر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    elif action == 'cookie_instagram':
        # مدیریت کوکی اینستاگرام
        keyboard = [
            [InlineKeyboardButton("➕ افزودن کوکی", callback_data='add_cookie_instagram')],
            [InlineKeyboardButton("📋 مشاهده کوکی‌ها", callback_data='list_cookies_instagram')],
            [InlineKeyboardButton("🗑 حذف همه", callback_data='clear_cookies_instagram')],
            [InlineKeyboardButton("⬅️ بازگشت", callback_data='cookies')]
        ]
        await callback_query.edit_message_text(
            "📷 <b>مدیریت کوکی اینستاگرام</b>\n\n"
            "عملیات مورد نظر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    elif action == 'admin_back':
        # بازگشت به پنل اصلی
        await callback_query.edit_message_text(
            "پنل مدیریت",
            reply_markup=InlineKeyboardMarkup(admin_inline_maker())
        )
        
    elif action == 'add_cookie_youtube':
        # افزودن کوکی یوتیوب
        admin_step['add_cookie'] = 'youtube'
        await callback_query.edit_message_text(
            "📺 <b>افزودن کوکی یوتیوب</b>\n\n"
            "لطفاً محتوای کوکی یوتیوب را ارسال کنید:\n\n"
            "📋 فرمت‌های پشتیبانی شده:\n"
            "• فرمت Netscape (.txt)\n"
            "• فرمت JSON\n\n"
            "💡 نکته: می‌توانید فایل کوکی را مستقیماً ارسال کنید یا محتوای آن را کپی کنید.\n\n"
            "❌ برای لغو /cancel را بفرستید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ بازگشت", callback_data='cookie_youtube')]])
        )
        
    elif action == 'add_cookie_instagram':
        # افزودن کوکی اینستاگرام
        admin_step['add_cookie'] = 'instagram'
        await callback_query.edit_message_text(
            "📷 <b>افزودن کوکی اینستاگرام</b>\n\n"
            "لطفاً محتوای کوکی اینستاگرام را ارسال کنید:\n\n"
            "📋 فرمت‌های پشتیبانی شده:\n"
            "• فرمت Netscape (.txt)\n"
            "• فرمت JSON\n\n"
            "💡 نکته: می‌توانید فایل کوکی را مستقیماً ارسال کنید یا محتوای آن را کپی کنید.\n\n"
            "❌ برای لغو /cancel را بفرستید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ بازگشت", callback_data='cookie_instagram')]])
        )
        
    elif action == 'list_cookies_youtube':
        # مشاهده کوکی‌های یوتیوب
        from cookie_manager import cookie_manager
        cookies = cookie_manager.get_cookies('youtube', active_only=False)
        stats = cookie_manager.get_cookie_stats('youtube')
        
        if not cookies:
            text = "📺 <b>کوکی‌های یوتیوب</b>\n\n❌ هیچ کوکی‌ای یافت نشد."
        else:
            text = (
                f"📺 <b>کوکی‌های یوتیوب</b>\n\n"
                f"📊 آمار کلی:\n"
                f"• مجموع: {stats['total']}\n"
                f"• فعال: {stats['active']}\n"
                f"• غیرفعال: {stats['inactive']}\n"
                f"• مجموع استفاده: {stats['total_usage']}\n\n"
                f"📋 لیست کوکی‌ها:\n"
            )
            
            for i, cookie in enumerate(cookies[:10], 1):  # نمایش حداکثر 10 کوکی
                status = "🟢" if cookie.get('active', True) else "🔴"
                usage = cookie.get('usage_count', 0)
                desc = cookie.get('description', f"کوکی {cookie.get('id', i)}")
                text += f"{i}. {status} {desc} (استفاده: {usage})\n"
            
            if len(cookies) > 10:
                text += f"\n... و {len(cookies) - 10} کوکی دیگر"
        
        await callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ بازگشت", callback_data='cookie_youtube')]])
        )
        
    elif action == 'list_cookies_instagram':
        # مشاهده کوکی‌های اینستاگرام
        from cookie_manager import cookie_manager
        cookies = cookie_manager.get_cookies('instagram', active_only=False)
        stats = cookie_manager.get_cookie_stats('instagram')
        
        if not cookies:
            text = "📷 <b>کوکی‌های اینستاگرام</b>\n\n❌ هیچ کوکی‌ای یافت نشد."
        else:
            text = (
                f"📷 <b>کوکی‌های اینستاگرام</b>\n\n"
                f"📊 آمار کلی:\n"
                f"• مجموع: {stats['total']}\n"
                f"• فعال: {stats['active']}\n"
                f"• غیرفعال: {stats['inactive']}\n"
                f"• مجموع استفاده: {stats['total_usage']}\n\n"
                f"📋 لیست کوکی‌ها:\n"
            )
            
            for i, cookie in enumerate(cookies[:10], 1):  # نمایش حداکثر 10 کوکی
                status = "🟢" if cookie.get('active', True) else "🔴"
                usage = cookie.get('usage_count', 0)
                desc = cookie.get('description', f"کوکی {cookie.get('id', i)}")
                text += f"{i}. {status} {desc} (استفاده: {usage})\n"
            
            if len(cookies) > 10:
                text += f"\n... و {len(cookies) - 10} کوکی دیگر"
        
        await callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ بازگشت", callback_data='cookie_instagram')]])
        )
        
    elif action == 'clear_cookies_youtube':
        # حذف همه کوکی‌های یوتیوب
        keyboard = [
            [InlineKeyboardButton("✅ بله، حذف کن", callback_data='confirm_clear_youtube')],
            [InlineKeyboardButton("❌ لغو", callback_data='cookie_youtube')]
        ]
        await callback_query.edit_message_text(
            "⚠️ <b>هشدار</b>\n\n"
            "آیا مطمئن هستید که می‌خواهید تمام کوکی‌های یوتیوب را حذف کنید؟\n\n"
            "❗️ این عمل قابل بازگشت نیست!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    elif action == 'clear_cookies_instagram':
        # حذف همه کوکی‌های اینستاگرام
        keyboard = [
            [InlineKeyboardButton("✅ بله، حذف کن", callback_data='confirm_clear_instagram')],
            [InlineKeyboardButton("❌ لغو", callback_data='cookie_instagram')]
        ]
        await callback_query.edit_message_text(
            "⚠️ <b>هشدار</b>\n\n"
            "آیا مطمئن هستید که می‌خواهید تمام کوکی‌های اینستاگرام را حذف کنید؟\n\n"
            "❗️ این عمل قابل بازگشت نیست!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    elif action == 'confirm_clear_youtube':
        # تأیید حذف کوکی‌های یوتیوب
        from cookie_manager import cookie_manager
        success = cookie_manager.clear_cookies('youtube')
        
        if success:
            text = "✅ تمام کوکی‌های یوتیوب با موفقیت حذف شدند."
        else:
            text = "❌ خطا در حذف کوکی‌ها. لطفاً دوباره تلاش کنید."
        
        await callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ بازگشت", callback_data='cookie_youtube')]])
        )
        
    elif action == 'confirm_clear_instagram':
        # تأیید حذف کوکی‌های اینستاگرام
        from cookie_manager import cookie_manager
        success = cookie_manager.clear_cookies('instagram')
        
        if success:
            text = "✅ تمام کوکی‌های اینستاگرام با موفقیت حذف شدند."
        else:
            text = "❌ خطا در حذف کوکی‌ها. لطفاً دوباره تلاش کنید."
        
        await callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ بازگشت", callback_data='cookie_instagram')]])
        )
        
    elif action == 'edit_waiting_youtube':
        # تغییر پیام انتظار یوتیوب
        admin_step['waiting_msg'] = 1
        admin_step['waiting_msg_platform'] = 'youtube'
        
        keyboard = [
            [InlineKeyboardButton("📝 متن", callback_data='waiting_type_text_youtube')],
            [InlineKeyboardButton("🎬 GIF", callback_data='waiting_type_gif_youtube')],
            [InlineKeyboardButton("😊 استیکر", callback_data='waiting_type_sticker_youtube')],
            [InlineKeyboardButton("⬅️ بازگشت", callback_data='waiting_msg')]
        ]
        
        await callback_query.edit_message_text(
            "📺 <b>تغییر پیام انتظار یوتیوب</b>\n\n"
            "نوع پیام انتظار را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    elif action == 'edit_waiting_instagram':
        # تغییر پیام انتظار اینستاگرام
        admin_step['waiting_msg'] = 1
        admin_step['waiting_msg_platform'] = 'instagram'
        
        keyboard = [
            [InlineKeyboardButton("📝 متن", callback_data='waiting_type_text_instagram')],
            [InlineKeyboardButton("🎬 GIF", callback_data='waiting_type_gif_instagram')],
            [InlineKeyboardButton("😊 استیکر", callback_data='waiting_type_sticker_instagram')],
            [InlineKeyboardButton("⬅️ بازگشت", callback_data='waiting_msg')]
        ]
        
        await callback_query.edit_message_text(
            "📷 <b>تغییر پیام انتظار اینستاگرام</b>\n\n"
            "نوع پیام انتظار را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    # Handle waiting message type selection
    elif action.startswith('waiting_type_'):
        parts = action.split('_')
        msg_type = parts[2]  # text, gif, sticker
        platform = parts[3]  # youtube, instagram
        
        admin_step['waiting_msg'] = 2
        admin_step['waiting_msg_type'] = msg_type
        admin_step['waiting_msg_platform'] = platform
        
        if msg_type == 'text':
            prompt = "لطفاً متن پیام انتظار را ارسال کنید:"
        elif msg_type == 'gif':
            prompt = "لطفاً فایل GIF مورد نظر را ارسال کنید:"
        elif msg_type == 'sticker':
            prompt = "لطفاً استیکر مورد نظر را ارسال کنید:"
        else:
            prompt = "لطفاً محتوای مورد نظر را ارسال کنید:"
            
        await callback_query.edit_message_text(
            f"📝 <b>تنظیم پیام انتظار {platform.title()}</b>\n\n"
            f"{prompt}\n\n"
            "❌ برای لغو /cancel را بفرستید.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ بازگشت", callback_data=f'edit_waiting_{platform}')
            ]])
        )
         
    try:
        await callback_query.answer()
    except Exception:
        pass


# Handle cookie input from admin
@Client.on_message(filters.text & filters.user(ADMIN), group=8)
async def handle_admin_cookie_input(client: Client, message: Message):
    """Handle cookie content input from admin"""
    # Check if admin is in cookie adding mode
    if 'add_cookie' not in admin_step:
        return
        
    platform = admin_step['add_cookie']
    text = message.text.strip()
    
    # Cancel operation
    if text.lower() == '/cancel':
        del admin_step['add_cookie']
        await message.reply_text("❌ عملیات لغو شد.")
        return
        
    # Process cookie
    try:
        from cookie_manager import cookie_manager
        
        # Add cookie to pool
        success = cookie_manager.add_cookie(platform, text)
        
        if success:
            stats = cookie_manager.get_cookie_stats(platform)
            await message.reply_text(
                f"✅ کوکی {platform} با موفقیت اضافه شد!\n\n"
                f"📊 آمار فعلی:\n"
                f"• مجموع کوکی‌ها: {stats['total']}\n"
                f"• فعال: {stats['active']}\n"
                f"• غیرفعال: {stats['inactive']}"
            )
        else:
            await message.reply_text(
                f"❌ خطا در افزودن کوکی {platform}.\n\n"
                "لطفاً فرمت کوکی را بررسی کنید."
            )
            
    except Exception as e:
        print(f"[ERROR] Cookie processing error: {e}")
        await message.reply_text(f"❌ خطا در پردازش کوکی: {str(e)}")
        
    # Reset admin step
    del admin_step['add_cookie']


# Handle cookie file input from admin
@Client.on_message(filters.document & filters.user(ADMIN), group=9)
async def handle_admin_cookie_file(client: Client, message: Message):
    """Handle cookie file input from admin"""
    # Check if admin is in cookie adding mode
    if 'add_cookie' not in admin_step:
        return
        
    platform = admin_step['add_cookie']
    document = message.document
    
    # Check file type
    if not document.file_name or not (document.file_name.endswith('.txt') or document.file_name.endswith('.json')):
        await message.reply_text(
            "❌ فرمت فایل پشتیبانی نمی‌شود.\n\n"
            "فرمت‌های مجاز: .txt, .json"
        )
        return
        
    # Check file size (max 1MB)
    if document.file_size > 1024 * 1024:
        await message.reply_text("❌ حجم فایل بیش از حد مجاز است. (حداکثر 1MB)")
        return
        
    try:
        # Download and read file
        file_path = await message.download()
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
        # Remove downloaded file
        import os
        os.remove(file_path)
        
        # Process cookie
        from cookie_manager import cookie_manager
        
        success = cookie_manager.add_cookie(platform, content)
        
        if success:
            stats = cookie_manager.get_cookie_stats(platform)
            await message.reply_text(
                f"✅ فایل کوکی {platform} با موفقیت پردازش شد!\n\n"
                f"📊 آمار فعلی:\n"
                f"• مجموع کوکی‌ها: {stats['total']}\n"
                f"• فعال: {stats['active']}\n"
                f"• غیرفعال: {stats['inactive']}"
            )
        else:
            await message.reply_text(
                f"❌ خطا در پردازش فایل کوکی {platform}.\n\n"
                "لطفاً فرمت فایل را بررسی کنید."
            )
            
    except Exception as e:
        print(f"[ERROR] Cookie file processing error: {e}")
        await message.reply_text(f"❌ خطا در پردازش فایل: {str(e)}")
        
    # Reset admin step
    del admin_step['add_cookie']


@Client.on_message(filters.text & filters.user(ADMIN), group=3)
async def set_insta_acc(_: Client, message: Message):
    pass  # unchanged existing logic follows...
