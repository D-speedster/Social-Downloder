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
import logging

# 🔥 Import metrics برای tracking
try:
    from plugins.simple_metrics import metrics
    METRICS_ENABLED = True
except ImportError:
    METRICS_ENABLED = False
    print("⚠️ Metrics not available")

# Configure Start module logger
start_logger = logging.getLogger('start_main')
start_logger.setLevel(logging.DEBUG)

# Create logs directory if it doesn't exist
os.makedirs('./logs', exist_ok=True)

start_handler = logging.FileHandler('./logs/start_main.log', encoding='utf-8')
start_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
start_handler.setFormatter(start_formatter)
start_logger.addHandler(start_handler)

step = {
    'sp': 2,
    'start': 0
}

PATH = constant.PATH
txt = constant.TEXT
data = constant.DATA

# New: patterns for supported links and pending link storage
YOUTUBE_REGEX = re.compile(r"^(?:https?://)?(?:www\.)?(?:m\.)?(?:youtube\.com|youtu\.be)/", re.IGNORECASE)
INSTA_REGEX = re.compile(r"(?:https?://)?(?:www\.|m\.)?(?:dd)?(?:instagram\.com|instagr\.am)/(?:p|reel|tv|stories|igtv)/[a-zA-Z0-9_-]+(?:\?[^\s]*)?", re.IGNORECASE)
SPOTIFY_REGEX = re.compile(r"^(?:https?://)?(?:open\.)?spotify\.com/", re.IGNORECASE)
TIKTOK_REGEX = re.compile(r"^(?:https?://)?(?:www\.|vm\.|m\.)?tiktok\.com/", re.IGNORECASE)
SOUNDCLOUD_REGEX = re.compile(r"^(?:https?://)?(?:www\.|m\.|on\.)?soundcloud\.com/", re.IGNORECASE)
PINTEREST_REGEX = re.compile(r"^(?:https?://)?(?:www\.)?pinterest\.com/", re.IGNORECASE)
TWITTER_REGEX = re.compile(r"^(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/", re.IGNORECASE)
THREADS_REGEX = re.compile(r"^(?:https?://)?(?:www\.)?threads\.net/", re.IGNORECASE)
FACEBOOK_REGEX = re.compile(r"^(?:https?://)?(?:www\.)?(?:facebook\.com|fb\.watch)/", re.IGNORECASE)
REDDIT_REGEX = re.compile(r"^(?:https?://)?(?:www\.)?reddit\.com/", re.IGNORECASE)
IMGUR_REGEX = re.compile(r"^(?:https?://)?(?:www\.)?imgur\.com/", re.IGNORECASE)
SNAPCHAT_REGEX = re.compile(r"^(?:https?://)?(?:www\.)?snapchat\.com/", re.IGNORECASE)
TUMBLR_REGEX = re.compile(r"^(?:https?://)?(?:www\.)?tumblr\.com/", re.IGNORECASE)
RUMBLE_REGEX = re.compile(r"^(?:https?://)?(?:www\.)?rumble\.com/", re.IGNORECASE)
IFUNNY_REGEX = re.compile(r"^(?:https?://)?(?:www\.)?ifunny\.(?:co|com)/", re.IGNORECASE)
DEEZER_REGEX = re.compile(r"^(?:https?://)?(?:www\.)?deezer\.com/", re.IGNORECASE)
RADIOJAVAN_REGEX = re.compile(r"^(?:https?://)?(?:www\.)?(?:play\.)?radiojavan\.com/(?:song|podcast|video)/[\w\-\(\)]+/?$", re.IGNORECASE)
APARAT_REGEX = re.compile(r"^(?:https?://)?(?:www\.)?aparat\.com/v/[\w\-]+/?$", re.IGNORECASE)
PENDING_LINKS = {}
# Cache برای جلوگیری از بررسی تکراری عضویت
JOIN_CHECK_CACHE = {}  # {user_id: (result, timestamp)}
JOIN_CACHE_TTL = 5  # 5 seconds


def _store_pending_link_if_any(message: Message):
    try:
        uid = getattr(message.from_user, 'id', None)
        text = getattr(message, 'text', None) or ''
        if not uid or not text:
            return
        if (YOUTUBE_REGEX.search(text) or INSTA_REGEX.search(text) or 
            SPOTIFY_REGEX.search(text) or TIKTOK_REGEX.search(text) or 
            SOUNDCLOUD_REGEX.search(text) or PINTEREST_REGEX.search(text) or TWITTER_REGEX.search(text) or 
            THREADS_REGEX.search(text) or FACEBOOK_REGEX.search(text) or REDDIT_REGEX.search(text) or 
            IMGUR_REGEX.search(text) or SNAPCHAT_REGEX.search(text) or TUMBLR_REGEX.search(text) or 
            RUMBLE_REGEX.search(text) or IFUNNY_REGEX.search(text) or DEEZER_REGEX.search(text) or 
            RADIOJAVAN_REGEX.search(text)):
            PENDING_LINKS[uid] = {
                'chat_id': message.chat.id,
                'message_id': message.id,
                'text': text,
                'ts': datetime.now().isoformat()
            }
            start_logger.info(f"Stored pending link for user={uid} msg_id={message.id}")
    except Exception as e:
        start_logger.error(f"Failed to store pending link: {e}")


# Build sponsor join markup dynamically (reflects latest @channel set by admin)
def sponsor_join_markup() -> InlineKeyboardMarkup:
    tag = data.get('sponser', '') or ''
    buttons = []
    
    # ✅ Support both @username and numeric IDs
    if tag.startswith('@') and len(tag) > 1:
        # Public channel with @username
        uname = tag[1:]
        url = f"https://t.me/{uname}"
        buttons.append([InlineKeyboardButton("🔗 عضویت در چنل ما", url=url)])
    elif tag.startswith('-100'):
        # Private channel with numeric ID - try to get invite link from sponsors list
        sponsors_list = data.get('sponsors', [])
        channel_name = "کانال اسپانسر"
        for sponsor in sponsors_list:
            if sponsor.get('id') == tag:
                channel_name = sponsor.get('name', channel_name)
                # If there's a username in the list, use it
                if sponsor.get('type') == 'username':
                    username = sponsor.get('id', '').lstrip('@')
                    if username:
                        url = f"https://t.me/{username}"
                        buttons.append([InlineKeyboardButton(f"🔗 عضویت در {channel_name}", url=url)])
                break
        
        # If no button was added, show a generic message
        if not buttons:
            buttons.append([InlineKeyboardButton("⚠️ لطفاً در کانال اسپانسر عضو شوید", callback_data="sponsor_info")])
    
    # Add verify button
    buttons.append([InlineKeyboardButton("✅ جوین شدم", callback_data="verify_join")])
    
    return InlineKeyboardMarkup(buttons)

# Maintenance mode gate (applies to ALL messages before other handlers)
@Client.on_message(filters.private & ~filters.user(ADMIN), group=-3)
async def maintenance_gate_msg(client: Client, message: Message):
    try:
        if data.get('bot_status', 'ON') == 'OFF':
            start_logger.info(f"Bot is in maintenance mode, blocking user {message.from_user.id}")
            await message.reply_text("ربات موقتا خاموش است. لطفاً بعداً مجدد تلاش کنید.")
            raise StopPropagation
    except Exception as e:
        start_logger.error(f"Error in maintenance gate: {e}")
        # Fail-open to avoid breaking bot if something goes wrong
        return


@Client.on_callback_query(~filters.user(ADMIN), group=-3)
async def maintenance_gate_cb(client: Client, callback_query: CallbackQuery):
    try:
        if data.get('bot_status', 'ON') == 'OFF':
            start_logger.info(f"Bot is in maintenance mode, blocking callback from user {callback_query.from_user.id}")
            await callback_query.answer("ربات موقتا خاموش است.", show_alert=True)
            raise StopPropagation
    except Exception as e:
        start_logger.error(f"Error in maintenance gate callback: {e}")
        return

# Helper to build main menu; for admins show admin panel keyboard, for others show nothing

def build_main_menu(user_id: int):
    if user_id in ADMIN:
        # Return admin panel reply keyboard instead of inline
        from plugins.admin import admin_reply_kb
        return admin_reply_kb()
    # Normal users: no menu after /start
    return None


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
            start_logger.warning("No user information available in join check")
            return False
    except Exception:
        return False
    
    uid = message.from_user.id
    
    # ✅ فقط برای پیام‌هایی که لینک هستند بررسی کن
    text = getattr(message, 'text', '') or ''
    if text and not any([
        'http' in text.lower(),
        'www.' in text.lower(),
        '.com' in text.lower(),
        '.net' in text.lower(),
        '.org' in text.lower(),
        'youtu' in text.lower(),
        'instagram' in text.lower(),
        'spotify' in text.lower(),
        'tiktok' in text.lower()
    ]):
        # این پیام لینک نیست، اجازه بده
        return True
    
    # ✅ Check cache first to avoid duplicate checks
    import time
    current_time = time.time()
    if uid in JOIN_CHECK_CACHE:
        cached_result, cached_time = JOIN_CHECK_CACHE[uid]
        if current_time - cached_time < JOIN_CACHE_TTL:
            start_logger.debug(f"Using cached join result for user={uid}: {cached_result}")
            return cached_result
        
    # Admins bypass sponsor check
    try:
        if uid in ADMIN:
            start_logger.info(f"Admin bypass for user={uid}")
            JOIN_CHECK_CACHE[uid] = (True, current_time)
            return True
    except Exception:
        pass
        
    # Respect force-join toggle (default: True)
    try:
        fj = data.get('force_join', True)
    except Exception:
        fj = True
    if not fj:
        start_logger.info(f"Force join disabled, allowing user={message.from_user.id}")
        JOIN_CHECK_CACHE[uid] = (True, current_time)
        return True
    
    # ✅ استفاده از سیستم جدید قفل‌های چندگانه
    try:
        from plugins.sponsor_system import get_sponsor_system
        system = get_sponsor_system()
        
        # بررسی عضویت در تمام قفل‌ها
        is_member, not_joined_locks = await system.check_user_membership(client, uid)
        
        if is_member:
            # کاربر در تمام قفل‌ها عضو است
            JOIN_CHECK_CACHE[uid] = (True, current_time)
            return True
        else:
            # کاربر در برخی قفل‌ها عضو نیست
            # فقط یک بار پیام بفرست
            if uid not in JOIN_CHECK_CACHE or JOIN_CHECK_CACHE[uid][0] != False:
                _store_pending_link_if_any(message)
                
                # ساخت پیام با لیست قفل‌ها
                locks_text = "\n".join([
                    f"• {lock.channel_name or lock.channel_username or lock.channel_id}"
                    for lock in not_joined_locks
                ])
                
                await message.reply_text(
                    f"🔒 **برای استفاده از ربات عضویت الزامی است**\n\n"
                    f"📢 **کانال‌های مورد نیاز:**\n{locks_text}\n\n"
                    f"💡 **مراحل:**\n"
                    f"1️⃣ روی دکمه‌های زیر کلیک کنید\n"
                    f"2️⃣ در تمام کانال‌ها عضو شوید\n"
                    f"3️⃣ روی «✅ جوین شدم» بزنید\n"
                    f"4️⃣ لینک شما خودکار پردازش می‌شود",
                    reply_markup=system.build_join_markup(not_joined_locks)
                )
            
            JOIN_CHECK_CACHE[uid] = (False, current_time)
            return False
            
    except Exception as e:
        start_logger.error(f"Error in new sponsor system: {e}")
        # Fallback به سیستم قدیمی
        pass
        
    try:
        sponsor_tag = data.get('sponser')
        if not sponsor_tag or not sponsor_tag.strip():
            start_logger.info("No sponsor configured, allowing access")
            return True
            
        chat_ref = _resolve_sponsor_chat_id(client, sponsor_tag)
        uid = message.from_user.id
        start_logger.debug(f"Checking join status for user={uid} sponsor={sponsor_tag} resolved={chat_ref}")
        
        if not chat_ref:
            start_logger.warning("Failed to resolve sponsor chat, allowing access")
            return True
            
        # Resolve username to chat id if needed
        if isinstance(chat_ref, str):
            try:
                chat = await client.get_chat(chat_ref)
                chat_id = chat.id
                start_logger.debug(f"Resolved username to chat_id={chat_id} title={getattr(chat,'title',None)}")
            except Exception as e:
                start_logger.error(f"Failed to resolve chat {chat_ref}: {e}")
                return True  # Allow on resolution failure
        else:
            chat_id = chat_ref
            start_logger.debug(f"Using numeric chat_id={chat_id}")
        try:
            status = await client.get_chat_member(chat_id=chat_id, user_id=uid)
            st = getattr(status, 'status', None)
            start_logger.debug(f"Member status for user={uid} in chat_id={chat_id} -> {st}")
            # اگر کاربر عضو باشد (member, administrator, creator, restricted) اجازه دسترسی دارد
            if (
                st in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER, ChatMemberStatus.RESTRICTED)
                or (isinstance(st, str) and st.lower() in ("member", "administrator", "creator", "restricted"))
                or (hasattr(st, 'value') and str(st.value).lower() in ("member", "administrator", "creator", "restricted"))
            ):
                # ✅ Cache successful result
                JOIN_CHECK_CACHE[uid] = (True, current_time)
                return True
            else:
                # اگر کاربر left یا kicked باشد
                # ✅ فقط یک بار پیام بفرست (اولین بار که cache نیست)
                if uid not in JOIN_CHECK_CACHE or JOIN_CHECK_CACHE[uid][0] != False:
                    _store_pending_link_if_any(message)
                    await message.reply_text(
                        "🔒 **برای استفاده از ربات عضویت در چنل الزامی است**\n\n"
                        "💡 **مراحل:**\n"
                        "1️⃣ روی دکمه زیر کلیک کنید\n"
                        "2️⃣ در چنل عضو شوید\n"
                        "3️⃣ روی «✅ جوین شدم» بزنید\n"
                        "4️⃣ لینک شما خودکار پردازش می‌شود\n\n"
                        "🎯 **پس از عضویت تمام قابلیت‌ها در اختیار شماست:**\n"
                        "• دانلود از یوتیوب با کیفیت‌های مختلف\n"
                        "• دانلود از اینستاگرام (پست/ریل/استوری)\n"
                        "• دانلود از اسپاتیفای، تیک‌تاک و 10+ پلتفرم دیگر",
                        reply_markup=sponsor_join_markup()
                    )
                # ✅ Cache failed result
                JOIN_CHECK_CACHE[uid] = (False, current_time)
                return False
        except Exception as admin_error:
            start_logger.warning(f"CHAT_ADMIN_REQUIRED or other error: {admin_error}")
            # اگر ربات ادمین نیست، کاربر را به عضویت دعوت می‌کنیم
            # ✅ فقط یک بار پیام بفرست
            if uid not in JOIN_CHECK_CACHE or JOIN_CHECK_CACHE[uid][0] != False:
                _store_pending_link_if_any(message)
                await message.reply_text(
                    "🔒 **برای استفاده از ربات عضویت در چنل الزامی است**\n\n"
                    "💡 **مراحل:**\n"
                    "1️⃣ روی دکمه زیر کلیک کنید\n"
                    "2️⃣ در چنل عضو شوید\n"
                    "3️⃣ روی «✅ جوین شدم» بزنید\n"
                    "4️⃣ لینک شما خودکار پردازش می‌شود\n\n"
                    "🎯 **پس از عضویت تمام قابلیت‌ها در اختیار شماست:**\n"
                    "• دانلود از یوتیوب با کیفیت‌های مختلف\n"
                    "• دانلود از اینستاگرام (پست/ریل/استوری)\n"
                    "• دانلود از اسپاتیفای، تیک‌تاک و 10+ پلتفرم دیگر",
                    reply_markup=sponsor_join_markup()
                )
            # ✅ Cache failed result
            JOIN_CHECK_CACHE[uid] = (False, current_time)
            return False

    except UserNotParticipant:
        start_logger.info(f"UserNotParticipant for user={getattr(message.from_user,'id',None)}")
        # ✅ فقط یک بار پیام بفرست
        if uid not in JOIN_CHECK_CACHE or JOIN_CHECK_CACHE[uid][0] != False:
            _store_pending_link_if_any(message)
            await message.reply_text(
                "🔒 **برای استفاده از ربات عضویت در چنل الزامی است**\n\n"
                "💡 **مراحل:**\n"
                "1️⃣ روی دکمه زیر کلیک کنید\n"
                "2️⃣ در چنل عضو شوید\n"
                "3️⃣ روی «✅ جوین شدم» بزنید\n"
                "4️⃣ لینک شما خودکار پردازش می‌شود\n\n"
                "🎯 **پس از عضویت تمام قابلیت‌ها در اختیار شماست:**\n"
                "• دانلود از یوتیوب با کیفیت‌های مختلف\n"
                "• دانلود از اینستاگرام (پست/ریل/استوری)\n"
                "• دانلود از اسپاتیفای، تیک‌تاک و 10+ پلتفرم دیگر",
                reply_markup=sponsor_join_markup()
            )
        # ✅ Cache failed result
        JOIN_CHECK_CACHE[uid] = (False, current_time)
        return False
    except Exception as e:
        start_logger.error(f"Error checking membership: {e}")
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
            start_logger.warning("Start command received without user information")
            await message.reply_text("❌ خطا در شناسایی کاربر")
            return
            
        start_logger.info(f"Start command received from user {user_id}")
        
        # 🔥 Track bot start in sponsor system
        try:
            from plugins.sponsor_system import get_sponsor_system
            sponsor_system = get_sponsor_system()
            if len(sponsor_system.get_all_locks()) > 0:
                await sponsor_system.track_bot_start(client, user_id)
                start_logger.debug(f"Tracked bot start for user {user_id} in sponsor system")
        except Exception as track_error:
            start_logger.error(f"Error tracking bot start: {track_error}")
        
        check_user = DB().check_user_register(user_id)
        welcome_text = (
            "🔴 به ربات YouTube | Instagram Save خوش آمدید\n\n"
            "⛱ شما می‌توانید لینک‌های یوتیوب و اینستاگرام خود را برای ربات ارسال کرده و فایل آن‌ها را در سریع‌ترین زمان ممکن با کیفیت دلخواه دریافت کنید"
        )
        
        if check_user:
            start_logger.debug(f"Existing user {user_id} started bot")
            await message.reply_text(welcome_text, reply_markup=build_main_menu(user_id))
            step['start'] = 1
        else:
            start_logger.info(f"New user {user_id} registering")
            now = datetime.now().isoformat()
            try:
                DB().register_user(user_id, now)
                start_logger.info(f"Successfully registered new user {user_id}")
                await message.reply_text(welcome_text, reply_markup=build_main_menu(user_id))
                step['start'] = 1
            except Exception as e:
                start_logger.error(f"Error registering user {user_id}: {e}")
                await message.reply_text("❌ خطا در ثبت کاربر. لطفاً مجدداً تلاش کنید.")
    except Exception as e:
        start_logger.error(f"Start command error: {e}")
        await message.reply_text("❌ خطای غیرمنتظره رخ داد")


# === Slash command handlers ===
@Client.on_message(filters.private & filters.command(["help"]))
async def help_command_handler(client: Client, message: Message):
    print(f"[DEBUG] /help command received from user {message.from_user.id}")
    
    # بررسی پیام راهنمای سفارشی
    import json
    from plugins.db_wrapper import DB
    
    try:
        db = DB()
        help_data = db.get_bot_setting('help_message')
        print(f"[DEBUG] Help data from DB: {help_data[:100] if help_data else 'None'}")
    except Exception as e:
        print(f"[ERROR] Error accessing database for help message: {e}")
        import traceback
        traceback.print_exc()
        help_data = None
    
    if help_data:
        try:
            help_config = json.loads(help_data)
            content_type = help_config.get('type', 'text')
            
            if content_type == 'text':
                await message.reply_text(
                    help_config.get('text', ''),
                    reply_markup=build_main_menu(message.from_user.id)
                )
            elif content_type == 'photo':
                await message.reply_photo(
                    photo=help_config.get('file_id'),
                    caption=help_config.get('caption', ''),
                    reply_markup=build_main_menu(message.from_user.id)
                )
            elif content_type == 'video':
                await message.reply_video(
                    video=help_config.get('file_id'),
                    caption=help_config.get('caption', ''),
                    reply_markup=build_main_menu(message.from_user.id)
                )
            elif content_type == 'animation':
                await message.reply_animation(
                    animation=help_config.get('file_id'),
                    caption=help_config.get('caption', ''),
                    reply_markup=build_main_menu(message.from_user.id)
                )
            elif content_type == 'sticker':
                await message.reply_sticker(
                    sticker=help_config.get('file_id')
                )
                # ارسال منو بعد از استیکر
                await message.reply_text("📱 منوی اصلی:", reply_markup=build_main_menu(message.from_user.id))
            elif content_type == 'document':
                await message.reply_document(
                    document=help_config.get('file_id'),
                    caption=help_config.get('caption', ''),
                    reply_markup=build_main_menu(message.from_user.id)
                )
            return
        except Exception as e:
            print(f"Error loading custom help message: {e}")
            # در صورت خطا، از پیام پیش‌فرض استفاده می‌شود
    
    # پیام پیش‌فرض
    text = (
        "📘 راهنما\n\n"
        "🔗 **پلتفرم‌های پشتیبانی شده:**\n"
        "📺 **یوتیوب** - youtube.com, youtu.be\n"
        "🎬 **آپارات** - aparat.com\n"
        "📷 **اینستاگرام** - instagram.com (پست/ریل/استوری)\n"
        "🎵 **اسپاتیفای** - spotify.com\n"
        "🎬 **تیک‌تاک** - tiktok.com\n"
        "🎧 **ساندکلود** - soundcloud.com\n"
        "📻 **رادیو جوان** - radiojavan.com\n\n"
        "💡 **نحوه استفاده:**\n"
        "- فقط لینک را ارسال کنید تا به‌طور خودکار پردازش شود\n"
        "- برای یوتیوب و آپارات لیست کیفیت‌ها نمایش داده می‌شود\n"
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
        "🎧 **ساندکلود** - soundcloud.com\n"
        "🖼 **پینترست** - pinterest.com\n"
        "🐦 **توییتر/X** - twitter.com, x.com\n"
        "🧵 **تردز** - threads.net\n"
        "🔵 **فیسبوک** - facebook.com, fb.watch\n"
        "🔷 **ردیت** - reddit.com\n"
        "🖼 **ایمگور** - imgur.com\n"
        "👻 **اسنپ‌چت** - snapchat.com\n"
        "📝 **تامبلر** - tumblr.com\n"
        "📺 **رامبل** - rumble.com\n"
        "😂 **آی‌فانی** - ifunny.co\n"
        "📻 **رادیوجوان** - radiojavan.com\n"
        "💽 **دیزر** - deezer.com\n\n"
        "💡 **نحوه استفاده:**\n"
        "- فقط لینک را ارسال کنید تا به‌طور خودکار پردازش شود\n"
        "- برای یوتیوب لیست کیفیت‌ها نمایش داده می‌شود\n"
        "- سایر پلتفرم‌ها به‌طور مستقیم دانلود می‌شوند (ویدیو/عکس/صوت)\n\n"
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

@Client.on_callback_query(filters.regex(r'^sponsor_info$'))
async def sponsor_info_callback(client: Client, callback_query: CallbackQuery):
    """Show sponsor channel information"""
    try:
        sponsor_tag = data.get('sponser', '')
        if sponsor_tag:
            await callback_query.answer(
                f"لطفاً در کانال اسپانسر عضو شوید.\nشناسه: {sponsor_tag}",
                show_alert=True
            )
        else:
            await callback_query.answer("کانال اسپانسر تنظیم نشده است.", show_alert=True)
    except Exception as e:
        await callback_query.answer("خطا در نمایش اطلاعات", show_alert=True)


@Client.on_callback_query(filters.regex(r'^verify_join$'))
async def verify_join_callback(client: Client, callback_query: CallbackQuery):
    try:
        uid = getattr(callback_query.from_user, 'id', None)
        
        # ✅ Clear cache for this user to force fresh check
        if uid in JOIN_CHECK_CACHE:
            del JOIN_CHECK_CACHE[uid]
            print(f"[VERIFY] Cleared join cache for user={uid}")
        
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
                            # Instagram handled by universal_downloader with SmartRetryWrapper
                            try:
                                from plugins.smart_retry_wrapper import smart_retry_wrapper
                                from plugins.insta_fetch import handle_instagram_link
                                
                                # Use dedicated Instagram handler
                                await handle_instagram_link(client, orig_msg)
                                
                                start_logger.info(f"Instagram download via dedicated handler")
                                
                            except ImportError:
                                # Fallback if insta_fetch not available
                                start_logger.error("insta_fetch not available!")
                                await client.send_message(
                                    chat_id=pending['chat_id'],
                                    text="❌ خطا در پردازش Instagram. لطفاً دوباره تلاش کنید."
                                )
                        elif (
                              SPOTIFY_REGEX.search(text) or TIKTOK_REGEX.search(text) or SOUNDCLOUD_REGEX.search(text) or 
                              PINTEREST_REGEX.search(text) or TWITTER_REGEX.search(text) or THREADS_REGEX.search(text) or 
                              FACEBOOK_REGEX.search(text) or REDDIT_REGEX.search(text) or IMGUR_REGEX.search(text) or 
                              SNAPCHAT_REGEX.search(text) or TUMBLR_REGEX.search(text) or RUMBLE_REGEX.search(text) or 
                              IFUNNY_REGEX.search(text) or DEEZER_REGEX.search(text) or RADIOJAVAN_REGEX.search(text)
                             ):
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


# === General Message Handler for Universal URLs (Spotify, TikTok, SoundCloud) ===
@Client.on_message(filters.private & filters.text & join & ~filters.command(["start", "help", "settings", "language", "upgrade", "dash", "dashboard"]) & ~filters.regex(r'^(🛠 مدیریت|📊 آمار کاربران|🖥 وضعیت سرور|📢 ارسال همگانی|📢 تنظیم اسپانسر|🔌 خاموش/روشن|🔐 خاموش/روشن اسپانسری|📺 خاموش/روشن تبلیغات|🍪 مدیریت کوکی|📺 تنظیم تبلیغات|📺 کوکی یوتیوب|⬅️ بازگشت|➕ افزودن کوکی یوتیوب|📋 مشاهده کوکی‌های یوتیوب|🗑 حذف همه کوکی‌های یوتیوب|✅ بله، حذف کن یوتیوب|❌ لغو|💬 پیام انتظار|🔝 بالای محتوا|🔻 پایین محتوا|🔌 بررسی پروکسی|✅ وضعیت ربات|📘 تنظیم راهنما|🔞 تنظیم Thumbnail)$'), group=10)
async def handle_text_messages(client: Client, message: Message):
    """Handle universal URLs (Spotify, TikTok, SoundCloud) - YouTube and Instagram have dedicated handlers"""
    try:
        # ✅ اگر ادمین در حالت تنظیم است، این handler را رد کن
        from plugins.admin import ADMIN, admin_step
        if message.from_user and message.from_user.id in ADMIN:
            # بررسی کن که آیا در حالت تنظیم است
            if (admin_step.get('sp') == 1 or 
                admin_step.get('broadcast') > 0 or 
                admin_step.get('advertisement') > 0 or 
                admin_step.get('waiting_msg') > 0):
                print(f"[START] Skipping handle_text_messages for admin in setup mode")
                return
        
        text = message.text.strip()
        
        # Only handle universal platforms (expanded list)
        # YouTube, Instagram, and RadioJavan are handled by their dedicated handlers with join filters
        if (SPOTIFY_REGEX.search(text) or TIKTOK_REGEX.search(text) or SOUNDCLOUD_REGEX.search(text) or 
            PINTEREST_REGEX.search(text) or TWITTER_REGEX.search(text) or THREADS_REGEX.search(text) or 
            FACEBOOK_REGEX.search(text) or REDDIT_REGEX.search(text) or IMGUR_REGEX.search(text) or 
            SNAPCHAT_REGEX.search(text) or TUMBLR_REGEX.search(text) or RUMBLE_REGEX.search(text) or 
            IFUNNY_REGEX.search(text) or DEEZER_REGEX.search(text)):
            from plugins.universal_downloader import handle_universal_link
            await handle_universal_link(client, message)
        elif YOUTUBE_REGEX.search(text) or INSTA_REGEX.search(text) or RADIOJAVAN_REGEX.search(text) or APARAT_REGEX.search(text):
            # These are handled by dedicated handlers, do nothing here
            pass
        else:
            # بررسی لینک‌های محتوای بزرگسال (نباید پیام راهنما نشون بده)
            adult_domains = ['pornhub.com', 'xvideos.com', 'youporn.com', 'xhamster.com']
            is_adult_link = any(domain in text.lower() for domain in adult_domains)
            
            # Only show help for text that looks like a URL (but not adult content)
            if not is_adult_link and ('http' in text.lower() or 'www.' in text.lower() or '.com' in text.lower() or 
                '.org' in text.lower() or '.net' in text.lower() or text.startswith('@')):
                # Looks like a URL but not supported
                await message.reply_text(
                    "🔗 **لینک پشتیبانی شده ارسال کنید:**\n\n"
                    "📺 **یوتیوب** - youtube.com, youtu.be\n"
                    "🎬 **آپارات** - aparat.com\n"
                    "📷 **اینستاگرام** - instagram.com (پست/ریل/استوری)\n"
                    "🎵 **اسپاتیفای** - spotify.com\n"
                    "🎬 **تیک‌تاک** - tiktok.com\n"
                    "🎧 **ساندکلود** - soundcloud.com\n"
                    "📻 **رادیو جوان** - radiojavan.com\n\n"
                    "💡 فقط لینک را ارسال کنید تا پردازش شود.",
                    reply_markup=build_main_menu(message.from_user.id)
                )
            # For regular text, do nothing (let other handlers handle it)
    except Exception as e:
        print(f"Error handling text message: {e}")
        try:
            await message.reply_text("❌ خطا در پردازش پیام. لطفاً دوباره تلاش کنید.")
        except:
            pass