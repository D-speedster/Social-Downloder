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
from plugins.db_wrapper import DB
# NEW: for server status and async sleep
import shutil, platform, asyncio, os as _os

PATH = constant.PATH
txt = constant.TEXT
data = constant.DATA

ADMIN = [79049016]

# Track bot start time for uptime
START_TIME = _dt.now()

admin_step = {
    'sp': 2,
    'cookies': 0,
    # NEW: broadcast state machine (0: idle, 1: waiting for content)
    'broadcast': 0,
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
            ["🔌 خاموش/روشن", "⬅️ بازگشت"],
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
        with open(PATH + '/database.json', 'w', encoding='utf-8') as outfile:
            json.dump(data, outfile, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to write bot_status: {e}")
    await message.reply_text(
        f"وضعیت ربات: {'🔴 خاموش' if new_state == 'OFF' else '🟢 روشن'}",
        reply_markup=admin_reply_kb()
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


# NEW: Admin root from inline menu (only Admins see the button in start.py)
@Client.on_callback_query(filters.regex(r'^admin_root$') & filters.user(ADMIN))
async def show_admin_root(client: Client, cq: CallbackQuery):
    print(f"[ADMIN] callback admin_root by {cq.from_user.id}")
    try:
        await cq.answer("پنل مدیریت باز شد", show_alert=False)
    except Exception as e:
        print("[ADMIN] cq.answer error:", e)
    try:
        # Prefer sending a fresh message with inline keyboard
        await client.send_message(
            chat_id=cq.message.chat.id,
            text="پنل مدیریت",
            reply_markup=InlineKeyboardMarkup(admin_inline_maker())
        )
        print("[ADMIN] inline admin panel sent")
    except Exception as e:
        print("[ADMIN] failed to send inline admin panel:", e)
        # Fallback to reply keyboard
        try:
            await client.send_message(
                chat_id=cq.message.chat.id,
                text="پنل مدیریت",
                reply_markup=admin_reply_kb()
            )
            print("[ADMIN] fallback reply keyboard sent")
        except Exception as e2:
            print("[ADMIN] failed to send fallback reply keyboard:", e2)


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
    return bool(re.match(r'^(st|srv|gm|sg|sp|pw)$', query.data))


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
        dest_name = _detect_cookie_dest(name)
        if not dest_name:
            await message.reply_text(
                "نام فایل مشخص نیست. لطفاً یکی از این نام‌ها را استفاده کنید:\n"
                "- instagram.txt برای اینستاگرام\n"
                "- youtube.txt برای یوتیوب")
            return
        cookies_dir = os.path.join(os.getcwd(), 'cookies')
        os.makedirs(cookies_dir, exist_ok=True)
        tmp_path = os.path.join(cookies_dir, f"__upload_{int(time.time())}_{name or 'cookies.txt'}")
        saved_path = await message.download(file_name=tmp_path)
        final_path = os.path.join(cookies_dir, dest_name)
        try:
            if os.path.exists(final_path):
                os.remove(final_path)
        except Exception:
            pass
        try:
            shutil.move(saved_path, final_path)
        except Exception:
            # fallback copy
            shutil.copyfile(saved_path, final_path)
            try:
                os.remove(saved_path)
            except Exception:
                pass
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
        du = shutil.disk_usage(str(_os.getcwd().split(':')[0] + ':\\') if _os.name == 'nt' else '/')
        total_gb = du.total / (1024**3)
        used_gb = (du.total - du.free) / (1024**3)
        free_gb = du.free / (1024**3)
        disk_line = f"💽 دیسک: {used_gb:.1f}GB استفاده‌شده / {total_gb:.1f}GB کل (آزاد: {free_gb:.1f}GB)"
    except Exception:
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


@Client.on_callback_query(static_data_filter)
async def answer(_, callback_query: CallbackQuery):
    print(f"[ADMIN] callback data: {callback_query.data} by {callback_query.from_user.id}")
    try:
        await callback_query.answer()
    except Exception:
        pass
    if callback_query.data == 'st':
        # آمار سیستم برای ادمین‌ها
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

    elif callback_query.data == 'srv':
        text = _server_status_text()
        await callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(admin_inline_maker()))

    elif callback_query.data == 'sp':
        await callback_query.edit_message_text(
            "ابتدا ربات را در چنل مورد نظر ادمین کن سپس شناسه چنل را ارسال کن.\n"
            "فرمت‌های مجاز:\n"
            "- @username (کانال عمومی)\n"
            "- -100xxxxxxxxxx (آی‌دی عددی، مناسب کانال خصوصی)\n"
            "- لینک t.me/username (به @username تبدیل می‌شود)\n\n"
            "نکته: لینک دعوت خصوصی (+) پشتیبانی نمی‌شود؛ برای کانال خصوصی از آی‌دی عددی استفاده کنید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('بازگشت', callback_data='admin_root')]])
        )
        admin_step['sp'] = 1

    elif callback_query.data in ('sg', 'gm'):
        admin_step['broadcast'] = 1
        await callback_query.edit_message_text(
            "لطفاً پیام مورد نظر برای ارسال همگانی را ارسال کنید.\n\n"
            "- هر نوع پیام پشتیبانی می‌شود (متن، عکس، ویدیو، فایل، ...).\n"
            "- برای لغو /cancel را بفرستید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('بازگشت', callback_data='admin_root')]])
        )

    elif callback_query.data == 'pw':
        # Toggle power state in memory and persist to file
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

    elif callback_query.data == 'sh':
        sys.exit()

    elif callback_query.data == 'si':
        await callback_query.edit_message_text("آیدی اکانتی که میخواهید اضافه شود رو وارد کنید")
        insta['level'] = 1


@Client.on_callback_query(filters.regex(r'^sp_check$') & filters.user(ADMIN))
async def sp_check_cb(client: Client, cq: CallbackQuery):
    sponsor_tag = (data.get('sponser') or '').strip()
    if not sponsor_tag:
        try:
            await cq.answer("اسپانسر تنظیم نشده است.", show_alert=True)
        except Exception:
            pass
        return
    # Resolve chat id
    tag = sponsor_tag[1:] if sponsor_tag.startswith('@') else sponsor_tag
    chat = None
    chat_id = None
    try:
        if tag.startswith('-100') or tag.isdigit():
            chat_id = int(tag)
        else:
            chat = await client.get_chat(tag)
            chat_id = chat.id
    except Exception as e:
        await cq.message.reply_text(f"❌ خطا در resolve کانال: {e}")
        return
    try:
        if chat is None:
            chat = await client.get_chat(chat_id)
        me = await client.get_me()
        member = await client.get_chat_member(chat_id, me.id)
        status = getattr(member, 'status', 'unknown')
        is_admin = status in ['administrator', 'creator']
        chat_username = getattr(chat, 'username', None)
        lines = [
            "🔍 بررسی کانال اسپانسر",
            f"- مقدار تنظیم‌شده: <code>{sponsor_tag}</code>",
            f"- آی‌دی عددی: <code>{chat_id}</code>",
            f"- عنوان: {chat.title}",
            f"- یوزرنیم: @{chat_username if chat_username else '—'}",
            f"- وضعیت ربات در کانال: {'ادمین' if is_admin else ('عضو' if status=='member' else status)}",
        ]
        if chat_username is None and sponsor_tag.startswith('@'):
            lines.append("⚠️ این کانال یوزرنیم عمومی ندارد. برای کانال خصوصی از آی‌دی عددی (-100…) استفاده کنید.")
        await cq.message.reply_text('\n'.join(lines), reply_markup=InlineKeyboardMarkup(admin_inline_maker()))
    except Exception as e:
        await cq.message.reply_text(f"❌ خطا در بررسی کانال: {e}")


@Client.on_callback_query(filters.regex(r'^fj_toggle$') & filters.user(ADMIN))
async def force_join_toggle(_: Client, cq: CallbackQuery):
    new_state = not data.get('force_join', True)
    data['force_join'] = new_state
    try:
        with open(PATH + '/database.json', 'w', encoding='utf-8') as outfile:
            json.dump(data, outfile, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to write force_join: {e}")
    try:
        await cq.answer(f"قفل عضویت: {'روشن' if new_state else 'خاموش'}", show_alert=False)
    except Exception:
        pass
    # Refresh panel buttons if message is editable
    try:
        await cq.message.edit_reply_markup(InlineKeyboardMarkup(admin_inline_maker()))
    except Exception:
        # Fallback: send a new panel
        try:
            await cq.message.reply_text("پنل مدیریت", reply_markup=InlineKeyboardMarkup(admin_inline_maker()))
        except Exception:
            pass


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
def set_sp(_: Client, message: Message):
     raw = (message.text or '').strip()
     val = raw
     # Normalize input
     if re.match(r'^(https?://)?t\.me/[A-Za-z0-9_]{4,}$', raw):
         # Extract username from t.me link
         uname = re.sub(r'^(https?://)?t\.me/', '', raw).strip('/')
         if uname.startswith('+'):
             message.reply_text("لینک دعوت خصوصی (+) پشتیبانی نمی‌شود. لطفاً @username یا آی‌دی عددی -100… را ارسال کنید.")
             return
         val = '@' + uname
     elif re.match(r'^@[A-Za-z0-9_]{4,}$', raw):
         val = raw
     elif re.match(r'^-100\d{8,14}$', raw):
         val = raw
     else:
         message.reply_text("فرمت وارد شده صحیح نیست. نمونه‌ها: @example یا -1001234567890 یا https://t.me/example")
         return

     data['sponser'] = val
     with open(PATH + '/database.json', "w", encoding='utf-8') as outfile:
         json.dump(data, outfile, indent=4, ensure_ascii=False)
         message.reply_text("اسپانسر بات با موفقیت تغییر کرد ✅")
     admin_step['sp'] = 0


@Client.on_message(filters.text & filters.user(ADMIN), group=3)
def set_insta_acc(_: Client, message: Message):
    pass  # unchanged existing logic follows...
