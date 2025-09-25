from pyrogram import Client, filters, StopPropagation
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, CallbackQuery, ReplyKeyboardRemove
from pyrogram.errors import UserNotParticipant
from pyrogram.enums import ChatMemberStatus
import json, string, random
import os
from plugins import constant
from datetime import datetime
from plugins.db_wrapper import DB
import re
from plugins.dashboard import _render_dashboard, _build_markup as _build_dash_markup
# NEW: import ADMIN to show admin-only controls
from plugins.admin import ADMIN

step = {
    'sp': 2,
    'start': 0
}

PATH = constant.PATH
txt = constant.TEXT
data = constant.DATA

# New: patterns for supported links and pending link storage
YOUTUBE_REGEX = re.compile(r"^(?:https?://)?(?:www\.)?(?:m\.)?(?:youtube\.com|youtu\.be)/", re.IGNORECASE)
INSTA_REGEX = re.compile(r"^((?:https?:)?//)?(?:(?:www|m)\.)?((?:instagram\.com))(\/(?:p\/|reel\/|tv\/|stories\/))([\w\-]+)(\S+)?$", re.IGNORECASE)
SPOTIFY_REGEX = re.compile(r"^(?:https?://)?(?:open\.)?spotify\.com/", re.IGNORECASE)
TIKTOK_REGEX = re.compile(r"^(?:https?://)?(?:www\.|vm\.|m\.)?tiktok\.com/", re.IGNORECASE)
SOUNDCLOUD_REGEX = re.compile(r"^(?:https?://)?(?:www\.|m\.|on\.)?soundcloud\.com/", re.IGNORECASE)
PENDING_LINKS = {}


def _store_pending_link_if_any(message: Message):
    try:
        uid = getattr(message.from_user, 'id', None)
        text = getattr(message, 'text', None) or ''
        if not uid or not text:
            return
        if (YOUTUBE_REGEX.search(text) or INSTA_REGEX.search(text) or 
            SPOTIFY_REGEX.search(text) or TIKTOK_REGEX.search(text) or 
            SOUNDCLOUD_REGEX.search(text)):
            PENDING_LINKS[uid] = {
                'chat_id': message.chat.id,
                'message_id': message.id,
                'text': text,
                'ts': datetime.now().isoformat()
            }
            print(f"[PENDING] stored link for user={uid} msg_id={message.id}")
    except Exception as e:
        print(f"[PENDING] failed to store link: {e}")


# Build sponsor join markup dynamically (reflects latest @channel set by admin)
def sponsor_join_markup() -> InlineKeyboardMarkup:
    tag = data.get('sponser', '') or ''
    # Only build a URL button when we have a public @username
    buttons = []
    if tag.startswith('@') and len(tag) > 1:
        uname = tag[1:]
        url = f"https://t.me/{uname}"
        buttons.append([InlineKeyboardButton("عضویت در چنل ما", url=url)])
    return InlineKeyboardMarkup(buttons + [[InlineKeyboardButton("✅ جوین شدم", callback_data="verify_join")]])

# Maintenance mode gate (applies to ALL messages before other handlers)
@Client.on_message(filters.private & ~filters.user(ADMIN), group=-3)
async def maintenance_gate_msg(client: Client, message: Message):
    try:
        if data.get('bot_status', 'ON') == 'OFF':
            await message.reply_text("ربات موقتا خاموش است. لطفاً بعداً مجدد تلاش کنید.")
            raise StopPropagation
    except Exception:
        # Fail-open to avoid breaking bot if something goes wrong
        return


@Client.on_callback_query(~filters.user(ADMIN), group=-3)
async def maintenance_gate_cb(client: Client, callback_query: CallbackQuery):
    try:
        if data.get('bot_status', 'ON') == 'OFF':
            await callback_query.answer("ربات موقتا خاموش است.", show_alert=True)
            raise StopPropagation
    except Exception:
        return

# Helper to build main menu; for admins show admin panel keyboard, for others show nothing

def build_main_menu(user_id: int):
    if user_id in ADMIN:
        # Return admin panel reply keyboard instead of inline
        from plugins.admin import admin_reply_kb
        return admin_reply_kb()
    # Normal users: no menu after /start
    return None


# Disabled old persistent keyboard (YouTube / Instagram / Dashboard / Settings)
# persistentMenu = ReplyKeyboardMarkup([
#     [txt['main_youtube'], txt['main_instagram']],
#     [txt['main_dashboard'], txt['main_settings']]
# ], resize_keyboard=True)


async def start_acc(_, client: Client, message: Message):
    if step['start'] == 1:
        return True


start_accept = filters.create(start_acc)


def _resolve_sponsor_chat_id(client: Client, sponsor_tag: str):
    # Helper to resolve chat id from username or numeric id (sync wrapper will be awaited by callers)
    sponsor_tag = (sponsor_tag or '').strip()
    if not sponsor_tag:
        return None
    # Remove '@' if present
    tag = sponsor_tag[1:] if sponsor_tag.startswith('@') else sponsor_tag
    # Try numeric id
    try:
        if tag.startswith("-100") or tag.isdigit():
            return int(tag)
    except Exception:
        pass
    # Fallback to username string (return as-is, get_chat will resolve)
    return tag


async def join_check(_, client: Client, message: Message):
    # Security: Check if user exists
    try:
        if not message.from_user or not message.from_user.id:
            print("[JOIN] No user information available")
            return False
    except Exception:
        return False
        
    # Admins bypass sponsor check
    try:
        if message.from_user.id in ADMIN:
            print(f"[JOIN] admin bypass user={message.from_user.id}")
            return True
    except Exception:
        pass
        
    # Respect force-join toggle (default: True)
    try:
        fj = data.get('force_join', True)
    except Exception:
        fj = True
    if not fj:
        print(f"[JOIN] force_join disabled -> allow user={message.from_user.id}")
        return True
        
    try:
        sponsor_tag = data.get('sponser')
        if not sponsor_tag or not sponsor_tag.strip():
            print("[JOIN] no sponsor configured -> allow")
            return True
            
        chat_ref = _resolve_sponsor_chat_id(client, sponsor_tag)
        uid = message.from_user.id
        print(f"[JOIN] user={uid} sponsor={sponsor_tag} resolved={chat_ref}")
        
        if not chat_ref:
            print("[JOIN] failed to resolve sponsor -> allow")
            return True
            
        # Resolve username to chat id if needed
        if isinstance(chat_ref, str):
            try:
                chat = await client.get_chat(chat_ref)
                chat_id = chat.id
                print(f"[JOIN] resolved username to chat_id={chat_id} title={getattr(chat,'title',None)} username={getattr(chat,'username',None)}")
            except Exception as e:
                print(f"[JOIN] failed to resolve chat {chat_ref}: {e}")
                return True  # Allow on resolution failure
        else:
            chat_id = chat_ref
            print(f"[JOIN] using numeric chat_id={chat_id}")
        try:
            status = await client.get_chat_member(chat_id=chat_id, user_id=uid)
            st = getattr(status, 'status', None)
            print(f"[JOIN] member status for user={uid} in chat_id={chat_id} -> {st}")
            # اگر کاربر عضو باشد (member, administrator, creator, restricted) اجازه دسترسی دارد
            if (
                st in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER, ChatMemberStatus.RESTRICTED)
                or (isinstance(st, str) and st.lower() in ("member", "administrator", "creator", "restricted"))
                or (hasattr(st, 'value') and str(st.value).lower() in ("member", "administrator", "creator", "restricted"))
            ):
                return True
            else:
                # اگر کاربر left یا kicked باشد
                _store_pending_link_if_any(message)
                await message.reply_text(
                    "برای حمایت از ربات، لطفاً ابتدا در کانال زیر عضو شوید و سپس روی دکمهٔ 'جوین شدم' بزنید.",
                    reply_markup=sponsor_join_markup()
                )
                return False
        except Exception as admin_error:
            print(f"[JOIN] CHAT_ADMIN_REQUIRED or other error: {admin_error}")
            # اگر ربات ادمین نیست، کاربر را به عضویت دعوت می‌کنیم
            _store_pending_link_if_any(message)
            await message.reply_text(
                "برای حمایت از ربات، لطفاً ابتدا در کانال زیر عضو شوید و سپس روی دکمهٔ 'جوین شدم' بزنید.",
                reply_markup=sponsor_join_markup()
            )
            return False

    except UserNotParticipant:
        print(f"[JOIN] UserNotParticipant for user={getattr(message.from_user,'id',None)}")
        _store_pending_link_if_any(message)
        await message.reply_text(
            "برای حمایت از ربات، لطفاً ابتدا در کانال زیر عضو شوید و سپس روی دکمهٔ ‘جوین شدم’ بزنید.",
            reply_markup=sponsor_join_markup()
        )
        return False
    except Exception as e:
        print(f"[JOIN] Error checking membership: {e}")
        # برای جلوگیری از مشکل، بررسی عضویت را غیرفعال می‌کنیم
        return True


join = filters.create(join_check)




def get_random_string():
    # Use secure random generation
    import secrets
    letters = string.ascii_lowercase + string.digits
    result_str = ''.join(secrets.choice(letters) for i in range(8))
    return result_str


@Client.on_message(filters.command("start"), group=-2)
async def start(client: Client, message: Message):
    try:
        user_id = message.from_user.id if message.from_user else None
        if not user_id:
            await message.reply_text("❌ خطا در شناسایی کاربر")
            return
            
        check_user = DB().check_user_register(user_id)
        welcome_text = (
            "🔴 به ربات YouTube | Instagram Save خوش آمدید\n\n"
            "⛱ شما می‌توانید لینک‌های یوتیوب و اینستاگرام خود را برای ربات ارسال کرده و فایل آن‌ها را در سریع‌ترین زمان ممکن با کیفیت دلخواه دریافت کنید"
        )
        
        if check_user:
            await message.reply_text(welcome_text, reply_markup=build_main_menu(user_id))
            step['start'] = 1
        else:
            now = datetime.now().isoformat()
            try:
                DB().register_user(user_id, now)
                await message.reply_text(welcome_text, reply_markup=build_main_menu(user_id))
                step['start'] = 1
            except Exception as e:
                print(f"Error registering user {user_id}: {e}")
                await message.reply_text("❌ خطا در ثبت کاربر. لطفاً مجدداً تلاش کنید.")
    except Exception as e:
        print(f"Start command error: {e}")
        await message.reply_text("❌ خطای غیرمنتظره رخ داد")


# === Slash command handlers ===
@Client.on_message(filters.private & filters.command(["help"]))
async def help_command_handler(client: Client, message: Message):
    text = (
        "📘 راهنما\n\n"
        "🔗 **پلتفرم‌های پشتیبانی شده:**\n"
        "📺 **یوتیوب** - youtube.com, youtu.be\n"
        "📷 **اینستاگرام** - instagram.com (پست/ریل/استوری)\n"
        "🎵 **اسپاتیفای** - spotify.com\n"
        "🎬 **تیک‌تاک** - tiktok.com\n"
        "🎧 **ساندکلود** - soundcloud.com\n\n"
        "💡 **نحوه استفاده:**\n"
        "- فقط لینک را ارسال کنید تا به‌طور خودکار پردازش شود\n"
        "- برای یوتیوب لیست کیفیت‌ها نمایش داده می‌شود\n"
        "- سایر پلتفرم‌ها به‌طور مستقیم دانلود می‌شوند\n\n"
        "📊 از بخش حساب کاربری می‌توانید آمار خود را ببینید."
    )
    await message.reply_text(text, reply_markup=build_main_menu(message.from_user.id))


@Client.on_message(filters.private & filters.command(["settings"]))
async def settings_command_handler(client: Client, message: Message):
    await message.reply_text("⚙️ تنظیمات", reply_markup=_settings_main_kb())


@Client.on_message(filters.private & filters.command(["language"]))
async def language_command_handler(client: Client, message: Message):
    await message.reply_text("🌐 تغییر زبان به‌زودی در دسترس خواهد بود.")


@Client.on_message(filters.private & filters.command(["upgrade"]))
async def upgrade_command_handler(client: Client, message: Message):
    await message.reply_text("🚀 سرویس ارتقا به‌زودی فعال می‌شود. در حال حاضر ربات به‌صورت رایگان قابل استفاده است.")


@Client.on_message(filters.regex(r'^👤 حساب کاربری$'))
async def account_info_message(client: Client, message: Message):
    user = message.from_user
    profile = DB().get_user_profile(user.id)
    username = f"@{user.username}" if user.username else "-"

    # Build new UI without join date, last activity, or channel status
    text = (
        "\u200F<b>👤 حساب کاربری شما</b>\n\n"
        f"🆔 آیدی : <code>{user.id}</code>\n"
        f"🧑‍💻 یوزرنیم: {username if username else '—'}\n"
        f"📊 کل درخواست‌ها: {profile.get('total_requests', 0)}\n"
        f"📅 درخواست‌های امروز: {profile.get('daily_requests', 0)}\n"
        f"🧾 نوع حساب: <b>کاربر عادی</b>"
    )
    await message.reply_text(text, reply_markup=build_main_menu(message.from_user.id))


@Client.on_callback_query(filters.regex(r'^account$'))
async def account_info_callback(client: Client, callback_query):
    user = callback_query.from_user
    profile = DB().get_user_profile(user.id)
    username = f"@{user.username}" if user.username else "-"

    text = (
        "\u200F<b>👤 حساب کاربری شما</b>\n\n"
        f"🆔 آیدی: <code>{user.id}</code>\n"
        f"🧑‍💻 یوزرنیم: {username if username else '—'}\n"
        f"📊 کل درخواست‌ها: {profile.get('total_requests', 0)}\n"
        f"📅 درخواست‌های امروز: {profile.get('daily_requests', 0)}\n"
        f"🧾 نوع حساب: <b>کاربر عادی</b>"
    )
    await callback_query.edit_message_text(text, reply_markup=build_main_menu(user.id))


@Client.on_message(filters.regex(r'^📘 راهنما$'))
async def help_menu_message(client: Client, message: Message):
    text = (
        "📘 راهنما\n\n"
        "🔗 **پلتفرم‌های پشتیبانی شده:**\n"
        "📺 **یوتیوب** - youtube.com, youtu.be\n"
        "📷 **اینستاگرام** - instagram.com (پست/ریل/استوری)\n"
        "🎵 **اسپاتیفای** - spotify.com\n"
        "🎬 **تیک‌تاک** - tiktok.com\n"
        "🎧 **ساندکلود** - soundcloud.com\n\n"
        "💡 **نحوه استفاده:**\n"
        "- فقط لینک را ارسال کنید تا به‌طور خودکار پردازش شود\n"
        "- برای یوتیوب لیست کیفیت‌ها نمایش داده می‌شود\n"
        "- سایر پلتفرم‌ها به‌طور مستقیم دانلود می‌شوند\n\n"
        "📊 از بخش حساب کاربری می‌توانید آمار خود را ببینید."
    )
    await message.reply_text(text, reply_markup=build_main_menu(message.from_user.id))


@Client.on_callback_query(filters.regex(r'^help$'))
async def help_menu_callback(client: Client, callback_query):
    text = (
        "📘 راهنما\n\n"
        "- لینک یوتیوب را ارسال کنید تا لیست کیفیت‌ها نمایش داده شود.\n"
        "- برای اینستاگرام، لینک پست/ریل/استوری را ارسال کنید.\n"
        "- از بخش حساب کاربری می‌توانید آمار خود را ببینید."
    )
    await callback_query.edit_message_text(text, reply_markup=build_main_menu(callback_query.from_user.id))


# ===== Disabled old Main Menu Handlers (replaced by commands) =====
# @Client.on_message(filters.private & filters.regex(r'^' + re.escape(txt['main_youtube']) + r'$'))
# async def menu_youtube(client: Client, message: Message):
#     await message.reply_text(txt['prompt_send_youtube'])
#
#
# @Client.on_message(filters.private & filters.regex(r'^' + re.escape(txt['main_instagram']) + r'$'))
# async def menu_instagram(client: Client, message: Message):
#     await message.reply_text(txt['prompt_send_instagram'])
#
#
# @Client.on_message(filters.private & filters.regex(r'^' + re.escape(txt['main_dashboard']) + r'$'))
# async def menu_dashboard(client: Client, message: Message):
#     user_id = message.from_user.id
#     text_dash = await _render_dashboard(user_id)
#     await message.reply_text(text_dash, reply_markup=_build_dash_markup(), disable_web_page_preview=True)
#
#
# @Client.on_message(filters.private & filters.regex(r'^' + re.escape(txt['main_settings']) + r'$'))
# async def menu_settings(client: Client, message: Message):
#     text_settings = _settings_text(message.from_user.id)
#     await message.reply_text(text_settings, reply_markup=_settings_main_kb())


# Whitespace-tolerant alias for /dash and /dashboard to handle leading/trailing spaces
@Client.on_message(filters.private & filters.regex(r'^\s*/(dash|dashboard)\s*$'))
async def menu_dashboard_cmd_alias(client: Client, message: Message):
    # If there are no extra spaces, let the original command handler in dashboard.py handle it
    try:
        if message.text and message.text.strip() == message.text:
            return
    except Exception:
        pass
    user_id = message.from_user.id
    text_dash = await _render_dashboard(user_id)
    await message.reply_text(text_dash, reply_markup=_build_dash_markup(), disable_web_page_preview=True)


def _settings_main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(txt['settings_quality'], callback_data='settings_q')],
        [InlineKeyboardButton(txt['settings_language'], callback_data='settings_lang')],
        [InlineKeyboardButton(txt['settings_clear_history'], callback_data='settings_clear')]
    ])

@Client.on_callback_query(filters.regex(r'^verify_join$'))
async def verify_join_callback(client: Client, callback_query: CallbackQuery):
    try:
        uid = getattr(callback_query.from_user, 'id', None)
        # Admins bypass
        if uid in ADMIN:
            print(f"[VERIFY] admin bypass user={uid}")
            await callback_query.answer("شما ادمین هستید و نیاز به عضویت ندارید.", show_alert=True)
            return
        try:
            fj = data.get('force_join', True)
        except Exception:
            fj = True
        if not fj:
            print(f"[VERIFY] force_join disabled -> allow user={uid}")
            try:
                await callback_query.answer("قفل عضویت برای کاربران خاموش است.", show_alert=True)
            except Exception:
                pass
            return
        sponsor_tag = data.get('sponser')
        chat_ref = _resolve_sponsor_chat_id(client, sponsor_tag)
        print(f"[VERIFY] user={uid} sponsor={sponsor_tag} resolved={chat_ref}")
        if not chat_ref:
            try:
                await callback_query.answer("اسپانسر تنظیم نشده است.", show_alert=True)
            except Exception:
                pass
            return
        try:
            if isinstance(chat_ref, str):
                chat = await client.get_chat(chat_ref)
                chat_id = chat.id
                print(f"[VERIFY] resolved username to chat_id={chat_id} title={getattr(chat,'title',None)} username={getattr(chat,'username',None)}")
            else:
                chat_id = chat_ref
                print(f"[VERIFY] using numeric chat_id={chat_id}")
            status = await client.get_chat_member(chat_id=chat_id, user_id=uid)
            st = getattr(status, 'status', None)
            print(f"[VERIFY] member status for user={uid} in chat_id={chat_id} -> {st}")
            if (
                st in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER, ChatMemberStatus.RESTRICTED)
                or (isinstance(st, str) and st.lower() in ("member", "administrator", "creator", "restricted"))
                or (hasattr(st, 'value') and str(st.value).lower() in ("member", "administrator", "creator", "restricted"))
            ):
                await callback_query.answer("✅ عضویت شما تایید شد!", show_alert=True)
                try:
                    await callback_query.message.delete()
                except Exception:
                    pass
                # Auto-process pending link if any
                pending = PENDING_LINKS.pop(uid, None)
                if pending:
                    try:
                        # Security: Validate pending data
                        if not isinstance(pending, dict) or 'chat_id' not in pending or 'message_id' not in pending:
                            print(f"[PENDING] Invalid pending data for user={uid}")
                            await client.send_message(chat_id=uid, text="❗️ داده‌های معلق نامعتبر. لطفاً دوباره لینک را ارسال کنید.")
                            return
                            
                        # Notify user
                        await client.send_message(chat_id=pending['chat_id'], text="🔁 عضویت تایید شد — در حال پردازش لینکی که قبلاً ارسال کرده بودید…")
                        
                        # Fetch original message with timeout
                        try:
                            orig_msg = await client.get_messages(pending['chat_id'], pending['message_id'])
                            if not orig_msg:
                                raise Exception("Message not found")
                        except Exception as e:
                            print(f"[PENDING] Failed to fetch original message: {e}")
                            await client.send_message(chat_id=pending['chat_id'], text="❗️ پیام اصلی یافت نشد. لطفاً دوباره لینک را ارسال کنید.")
                            return
                            
                        text = pending.get('text') or ''
                        # Lazy imports to avoid circular
                        if YOUTUBE_REGEX.search(text):
                            from plugins.youtube import show_video
                            await show_video(client, orig_msg)
                        elif INSTA_REGEX.search(text):
                            from plugins.instagram import download_instagram
                            download_instagram(client, orig_msg)
                        elif (SPOTIFY_REGEX.search(text) or TIKTOK_REGEX.search(text) or 
                              SOUNDCLOUD_REGEX.search(text)):
                            from plugins.universal_downloader import handle_universal_link
                            await handle_universal_link(client, orig_msg)
                        else:
                            # Not a supported link anymore; prompt user
                            await client.send_message(chat_id=pending['chat_id'], text="حالا می‌توانید لینک را بفرستید ✍️")
                    except Exception as perr:
                        print(f"[PENDING] failed to auto-process pending link for user={uid}: {perr}")
                        try:
                            chat_id = pending.get('chat_id', uid) if isinstance(pending, dict) else uid
                            await client.send_message(chat_id=chat_id, text="❗️ خطا در پردازش خودکار لینک. لطفاً دوباره لینک را ارسال کنید.")
                        except Exception:
                            pass
                else:
                    # No pending link, just guide the user
                    try:
                        await client.send_message(chat_id=uid, text="✅ عضویت شما تایید شد! حالا می‌توانید لینکتون رو بفرستید ✍️")
                    except Exception:
                        pass
            else:
                await callback_query.answer("❌ هنوز عضو کانال نیستید. لطفاً ابتدا عضو شوید.", show_alert=True)
        except UserNotParticipant:
            print(f"[VERIFY] UserNotParticipant for user={uid}")
            await callback_query.answer("❌ هنوز عضو کانال نیستید. لطفاً ابتدا عضو شوید.", show_alert=True)
    except Exception as e:
            print(f"[VERIFY] Error during verify: {e}")
            try:
                await callback_query.answer("خطای غیرمنتظره رخ داد.", show_alert=True)
            except Exception:
                pass


# === General Message Handler for URLs ===
@Client.on_message(filters.private & filters.text & ~filters.command(["start", "help", "settings", "language", "upgrade", "dash", "dashboard"]) & ~filters.regex(r'^(🛠 مدیریت|📊 آمار کاربران|🖥 وضعیت سرور|📣 ارسال پیام|📢 تنظیم اسپانسر|🔌 خاموش/روشن|🔐 خاموش/روشن اسپانسری|📺 خاموش/روشن تبلیغات|🍪 مدیریت کوکی|📺 تنظیم تبلیغات|📺 کوکی یوتیوب|⬅️ بازگشت|➕ افزودن کوکی یوتیوب|📋 مشاهده کوکی‌های یوتیوب|🗑 حذف همه کوکی‌های یوتیوب|✅ بله، حذف کن یوتیوب|❌ لغو|💬 پیام انتظار|🔝 بالای محتوا|🔻 پایین محتوا)$'), group=1)
async def handle_text_messages(client: Client, message: Message):
    """Handle all text messages and route URLs to appropriate handlers"""
    try:
        text = message.text.strip()
        
        # Check if it's a supported URL
        if YOUTUBE_REGEX.search(text):
            from plugins.youtube import show_video
            await show_video(client, message)
        elif INSTA_REGEX.search(text):
            from plugins.instagram import download_instagram
            download_instagram(client, message)
        elif (SPOTIFY_REGEX.search(text) or TIKTOK_REGEX.search(text) or 
              SOUNDCLOUD_REGEX.search(text)):
            from plugins.universal_downloader import handle_universal_link
            await handle_universal_link(client, message)
        else:
            # Not a supported URL, send help message
            await message.reply_text(
                "🔗 **لینک پشتیبانی شده ارسال کنید:**\n\n"
                "📺 **یوتیوب** - youtube.com, youtu.be\n"
                "📷 **اینستاگرام** - instagram.com (پست/ریل/استوری)\n"
                "🎵 **اسپاتیفای** - spotify.com\n"
                "🎬 **تیک‌تاک** - tiktok.com\n"
                "🎧 **ساندکلود** - soundcloud.com\n\n"
                "💡 فقط لینک را ارسال کنید تا پردازش شود.",
                reply_markup=build_main_menu(message.from_user.id)
            )
    except Exception as e:
        print(f"Error handling text message: {e}")
        try:
            await message.reply_text("❌ خطا در پردازش پیام. لطفاً دوباره تلاش کنید.")
        except:
            pass
