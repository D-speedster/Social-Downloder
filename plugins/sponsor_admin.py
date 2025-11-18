"""
🔧 پنل ادمین برای مدیریت قفل‌های اسپانسری
"""

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from plugins.sponsor_system import get_sponsor_system, SponsorLock
from plugins.admin import ADMIN
from pyrogram.handlers import MessageHandler
from pyrogram import StopPropagation
import logging

logger = logging.getLogger('sponsor_admin')

# State management for admin operations
admin_sponsor_state = {}

def get_admin_state(user_id: int) -> dict:
    """دریافت state ادمین"""
    if user_id not in admin_sponsor_state:
        admin_sponsor_state[user_id] = {
            'action': None,  # 'add', 'remove', 'view'
            'step': 0,
            'data': {}
        }
    return admin_sponsor_state[user_id]

def reset_admin_state(user_id: int):
    """ریست state ادمین"""
    if user_id in admin_sponsor_state:
        del admin_sponsor_state[user_id]


def build_sponsor_admin_menu() -> InlineKeyboardMarkup:
    """منوی اصلی مدیریت اسپانسر"""
    system = get_sponsor_system()
    locks_count = len(system.get_all_locks())
    
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📋 لیست قفل‌ها ({locks_count})", callback_data="sponsor_list")],
        [InlineKeyboardButton("➕ افزودن قفل جدید", callback_data="sponsor_add")],
        [InlineKeyboardButton("🗑 حذف قفل", callback_data="sponsor_remove")],
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data="sponsor_refresh")],
        [InlineKeyboardButton("⬅️ بازگشت", callback_data="back_to_admin")]
    ])


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^sponsor_list$'))
async def sponsor_list_callback(client: Client, callback_query: CallbackQuery):
    """نمایش لیست قفل‌ها"""
    system = get_sponsor_system()
    locks = system.get_all_locks()
    
    if not locks:
        await callback_query.answer("هیچ قفلی تنظیم نشده است!", show_alert=True)
        return
    
    text = "📋 **لیست قفل‌های اسپانسری:**\n\n"
    
    buttons = []
    for i, lock in enumerate(locks, 1):
        name = lock.channel_name or lock.channel_username or lock.channel_id
        text += f"{i}. {name}\n"
        text += f"   └ 👥 {lock.total_bot_starts} استارت | "
        text += f"✅ {lock.joined_through_lock} جوین | "
        text += f"❌ {lock.not_joined} لفت\n\n"
        
        # دکمه برای هر قفل
        buttons.append([
            InlineKeyboardButton(f"📊 {name}", callback_data=f"sponsor_view_{lock.id}")
        ])
    
    buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="sponsor_menu")])
    
    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await callback_query.answer()


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^sponsor_view_(.+)$'))
async def sponsor_view_callback(client: Client, callback_query: CallbackQuery):
    """نمایش جزئیات یک قفل"""
    lock_id = callback_query.data.split('_', 2)[2]
    system = get_sponsor_system()
    lock = system.get_lock(lock_id)
    
    if not lock:
        await callback_query.answer("قفل یافت نشد!", show_alert=True)
        return
    
    text = lock.get_stats_text()
    
    buttons = [
        [InlineKeyboardButton("🗑 حذف این قفل", callback_data=f"sponsor_delete_{lock_id}")],
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"sponsor_view_{lock_id}")],
        [InlineKeyboardButton("⬅️ بازگشت به لیست", callback_data="sponsor_list")]
    ]
    
    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await callback_query.answer()


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^sponsor_add$'))
async def sponsor_add_callback(client: Client, callback_query: CallbackQuery):
    """شروع فرآیند افزودن قفل"""
    user_id = callback_query.from_user.id
    logger.info(f"[SPONSOR_ADD] Callback triggered by user {user_id}")
    
    state = get_admin_state(user_id)
    state['action'] = 'add'
    state['step'] = 1
    
    logger.info(f"[SPONSOR_ADD] State set: action=add, step=1 for user {user_id}")
    
    text = """➕ **افزودن قفل جدید**

لطفاً شناسه کانال را ارسال کنید:

📋 **فرمت‌های مجاز:**
• `@username` (کانال عمومی)
• `-1001234567890` (آی‌دی عددی)

⚠️ **نکات مهم:**
1️⃣ ابتدا ربات را در کانال **ادمین** کنید
2️⃣ برای لغو /cancel بفرستید

👇 **حالا شناسه کانال را بفرستید:**"""
    
    await callback_query.message.edit_text(text)
    await callback_query.answer()


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^sponsor_remove$'))
async def sponsor_remove_callback(client: Client, callback_query: CallbackQuery):
    """شروع فرآیند حذف قفل"""
    system = get_sponsor_system()
    locks = system.get_all_locks()
    
    if not locks:
        await callback_query.answer("هیچ قفلی برای حذف وجود ندارد!", show_alert=True)
        return
    
    text = "🗑 **حذف قفل**\n\nکدام قفل را می‌خواهید حذف کنید؟\n\n"
    
    buttons = []
    for lock in locks:
        name = lock.channel_name or lock.channel_username or lock.channel_id
        buttons.append([
            InlineKeyboardButton(f"🗑 {name}", callback_data=f"sponsor_delete_{lock.id}")
        ])
    
    buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="sponsor_menu")])
    
    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await callback_query.answer()


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^sponsor_delete_(?!confirm_)(.+)$'))
async def sponsor_delete_confirm_callback(client: Client, callback_query: CallbackQuery):
    """تایید حذف قفل"""
    # Parse lock_id correctly
    # Format: sponsor_delete_lock_1_1234567890
    parts = callback_query.data.split('_')
    lock_id = '_'.join(parts[2:])  # Join all parts after "sponsor_delete_"
    
    logger.info(f"[SPONSOR_DELETE] Showing confirmation for lock_id={lock_id}")
    system = get_sponsor_system()
    lock = system.get_lock(lock_id)
    
    if not lock:
        await callback_query.answer("قفل یافت نشد!", show_alert=True)
        return
    
    name = lock.channel_name or lock.channel_username or lock.channel_id
    
    text = f"""⚠️ **تایید حذف**

آیا مطمئن هستید که می‌خواهید این قفل را حذف کنید؟

📌 **کانال:** {name}
📊 **آمار:**
• {lock.total_bot_starts} استارت
• {lock.joined_through_lock} جوین
• {lock.not_joined} لفت

⚠️ **توجه:** این عمل غیرقابل بازگشت است!"""
    
    buttons = [
        [
            InlineKeyboardButton("✅ بله، حذف شود", callback_data=f"sponsor_delete_confirm_{lock_id}"),
            InlineKeyboardButton("❌ خیر", callback_data="sponsor_list")
        ]
    ]
    
    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await callback_query.answer()


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^sponsor_delete_confirm_(.+)$'))
async def sponsor_delete_execute_callback(client: Client, callback_query: CallbackQuery):
    """اجرای حذف قفل"""
    # Parse lock_id correctly
    # Format: sponsor_delete_confirm_lock_1_1234567890
    parts = callback_query.data.split('_')
    lock_id = '_'.join(parts[3:])  # Join all parts after "sponsor_delete_confirm_"
    
    logger.info(f"[SPONSOR_DELETE] Executing delete for lock_id={lock_id}")
    
    system = get_sponsor_system()
    
    if system.remove_lock(lock_id):
        logger.info(f"[SPONSOR_DELETE] Successfully deleted lock_id={lock_id}")
        await callback_query.answer("✅ قفل با موفقیت حذف شد!", show_alert=True)
        # بازگشت به لیست
        await sponsor_list_callback(client, callback_query)
    else:
        logger.error(f"[SPONSOR_DELETE] Failed to delete lock_id={lock_id}")
        await callback_query.answer("❌ خطا در حذف قفل!", show_alert=True)


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^sponsor_stats$'))
async def sponsor_stats_callback(client: Client, callback_query: CallbackQuery):
    """نمایش لیست قفل‌ها با آمار - حذف آمار کلی"""
    # فقط به لیست قفل‌ها هدایت می‌کنیم
    await sponsor_list_callback(client, callback_query)


@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^sponsor_(menu|refresh)$'))
async def sponsor_menu_callback(client: Client, callback_query: CallbackQuery):
    """نمایش منوی اصلی"""
    text = """🔐 **مدیریت قفل‌های اسپانسری**

از این بخش می‌توانید:
• قفل‌های جدید اضافه کنید
• قفل‌های موجود را مدیریت کنید
• آمار هر قفل را مشاهده کنید
• آمار کلی سیستم را ببینید

یک گزینه را انتخاب کنید:"""
    
    await callback_query.message.edit_text(
        text,
        reply_markup=build_sponsor_admin_menu()
    )
    await callback_query.answer()


# Custom filter برای بررسی state ادمین
def sponsor_add_filter(_, __, message):
    """فیلتر برای بررسی اینکه ادمین در حال افزودن قفل است"""
    if not message.from_user:
        logger.debug("[SPONSOR_FILTER] No user in message")
        return False
    
    user_id = message.from_user.id
    state = get_admin_state(user_id)
    
    is_active = state.get('action') == 'add' and state.get('step') == 1
    
    logger.debug(f"[SPONSOR_FILTER] user={user_id}, action={state.get('action')}, step={state.get('step')}, active={is_active}")
    
    return is_active

sponsor_add_active = filters.create(sponsor_add_filter)

# Handler for receiving channel ID when adding new lock
@Client.on_message(filters.user(ADMIN) & filters.private & filters.text & sponsor_add_active, group=0)
async def handle_sponsor_add_input(client: Client, message: Message):
    """دریافت ورودی برای افزودن قفل"""
    user_id = message.from_user.id
    state = get_admin_state(user_id)
    
    # 🔥 DEBUG: لاگ ورودی
    logger.info(f"[SPONSOR_ADD] Handler triggered for user={user_id}")
    logger.info(f"[SPONSOR_ADD] Message text: {message.text}")
    logger.info(f"[SPONSOR_ADD] State: action={state.get('action')}, step={state.get('step')}")
    
    # لغو
    if message.text.startswith('/cancel'):
        logger.info(f"[SPONSOR_ADD] User {user_id} cancelled operation")
        reset_admin_state(user_id)
        await message.reply_text("❌ عملیات لغو شد.")
        raise StopPropagation
    
    channel_ref = message.text.strip()
    
    # 🔥 DEBUG: لاگ channel ref
    logger.info(f"[SPONSOR_ADD] Channel ref: {channel_ref}")
    
    # بررسی فرمت
    if not (channel_ref.startswith('@') or channel_ref.startswith('-100')):
        logger.warning(f"[SPONSOR_ADD] Invalid format: {channel_ref}")
        await message.reply_text(
            "❌ فرمت نادرست!\n\n"
            "لطفاً یکی از فرمت‌های زیر را استفاده کنید:\n"
            "• `@username`\n"
            "• `-1001234567890`"
        )
        raise StopPropagation
    
    logger.info(f"[SPONSOR_ADD] Format valid, proceeding...")
    
    # تلاش برای دریافت اطلاعات کانال
    try:
        logger.info(f"[SPONSOR_ADD] Fetching chat info...")
        
        if channel_ref.startswith('@'):
            username = channel_ref.lstrip('@')
            logger.info(f"[SPONSOR_ADD] Getting chat by username: {username}")
            chat = await client.get_chat(username)
        else:
            logger.info(f"[SPONSOR_ADD] Getting chat by ID: {channel_ref}")
            chat = await client.get_chat(int(channel_ref))
        
        channel_id = str(chat.id)
        channel_name = chat.title
        channel_username = f"@{chat.username}" if chat.username else None
        
        logger.info(f"[SPONSOR_ADD] Chat info: id={channel_id}, name={channel_name}, username={channel_username}")
        
        # بررسی اینکه ربات ادمین است
        try:
            from pyrogram.enums import ChatMemberStatus
            
            logger.info(f"[SPONSOR_ADD] Checking bot admin status...")
            bot_member = await client.get_chat_member(chat.id, "me")
            logger.info(f"[SPONSOR_ADD] Bot status: {bot_member.status}")
            
            # ✅ مقایسه با enum نه string
            if bot_member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                logger.warning(f"[SPONSOR_ADD] Bot is not admin in {channel_id}, status={bot_member.status}")
                await message.reply_text(
                    "⚠️ **ربات ادمین نیست!**\n\n"
                    f"لطفاً ابتدا ربات را در کانال **{channel_name}** ادمین کنید.\n\n"
                    f"وضعیت فعلی: {bot_member.status}\n\n"
                    "سپس دوباره تلاش کنید."
                )
                raise StopPropagation
            
            logger.info(f"[SPONSOR_ADD] ✅ Bot is admin in {channel_id}")
            
        except StopPropagation:
            raise
        except Exception as e:
            logger.error(f"[SPONSOR_ADD] Error checking bot status: {e}", exc_info=True)
            await message.reply_text(
                f"⚠️ **خطا در بررسی دسترسی ربات**\n\n"
                f"لطفاً مطمئن شوید که ربات در کانال عضو و ادمین است.\n\n"
                f"خطا: {str(e)}"
            )
            raise StopPropagation
        
        # افزودن قفل
        logger.info(f"[SPONSOR_ADD] Adding lock to system...")
        system = get_sponsor_system()
        lock = system.add_lock(
            channel_id=channel_id,
            channel_name=channel_name,
            channel_username=channel_username
        )
        logger.info(f"[SPONSOR_ADD] Lock added successfully: {lock.id}")
        
        await message.reply_text(
            f"✅ **قفل با موفقیت اضافه شد!**\n\n"
            f"📌 **کانال:** {channel_name}\n"
            f"🆔 **شناسه:** `{channel_id}`\n"
            f"🔗 **یوزرنیم:** {channel_username or 'ندارد'}\n"
            f"🆔 **Lock ID:** `{lock.id}`\n\n"
            f"✅ از این لحظه کاربران باید در این کانال عضو شوند."
        )
        
        # ریست state
        logger.info(f"[SPONSOR_ADD] Resetting state for user {user_id}")
        reset_admin_state(user_id)
        
        # 🔥 جلوگیری از پردازش توسط handler‌های دیگر
        raise StopPropagation
        
    except StopPropagation:
        # اجازه بده StopPropagation pass بشه
        raise
    except Exception as e:
        logger.error(f"[SPONSOR_ADD] Exception occurred: {e}", exc_info=True)
        await message.reply_text(
            f"❌ **خطا در افزودن قفل**\n\n"
            f"لطفاً بررسی کنید که:\n"
            f"1️⃣ شناسه کانال صحیح است\n"
            f"2️⃣ ربات در کانال عضو است\n"
            f"3️⃣ ربات دسترسی ادمین دارد\n\n"
            f"خطا: {str(e)}"
        )
        # ریست state در صورت خطا
        reset_admin_state(user_id)
        raise StopPropagation


# Integration with verify_join callback
@Client.on_callback_query(filters.regex(r'^verify_multi_join$'))
async def verify_multi_join_callback(client: Client, callback_query: CallbackQuery):
    """تایید جوین در سیستم مولتی قفل"""
    user_id = callback_query.from_user.id
    system = get_sponsor_system()
    
    # بررسی عضویت
    is_member, not_joined = await system.check_user_membership(client, user_id)
    
    if is_member:
        await callback_query.answer("✅ عضویت شما در تمام کانال‌ها تایید شد!", show_alert=True)
        
        # 🔥 Track successful join for all locks
        try:
            all_locks = system.get_all_locks()
            for lock in all_locks:
                await system.track_successful_join(client, user_id, lock.id)
            logger.info(f"[VERIFY_JOIN] Tracked successful join for user {user_id} in {len(all_locks)} locks")
        except Exception as track_error:
            logger.error(f"[VERIFY_JOIN] Error tracking join: {track_error}")
        
        # حذف پیام قفل
        try:
            await callback_query.message.delete()
        except:
            pass
        
        # پردازش لینک معلق (اگر وجود دارد)
        from plugins.start import PENDING_LINKS, YOUTUBE_REGEX, INSTA_REGEX
        pending = PENDING_LINKS.pop(user_id, None)
        
        if pending:
            try:
                logger.info(f"[VERIFY_JOIN] Processing pending link for user {user_id}")
                
                await client.send_message(
                    chat_id=pending['chat_id'],
                    text="🔁 عضویت تایید شد — در حال پردازش لینکی که قبلاً ارسال کرده بودید…"
                )
                
                # دریافت message object اصلی
                try:
                    orig_msg = await client.get_messages(pending['chat_id'], pending['message_id'])
                    
                    if not orig_msg:
                        raise Exception("Message not found")
                    
                    # پردازش بر اساس نوع لینک
                    text = pending.get('text', '')
                    
                    if YOUTUBE_REGEX.search(text):
                        logger.info(f"[VERIFY_JOIN] Processing YouTube link")
                        from plugins.youtube_handler import show_video
                        await show_video(client, orig_msg)
                    elif INSTA_REGEX.search(text):
                        logger.info(f"[VERIFY_JOIN] Processing Instagram link")
                        from plugins.insta_fetch import handle_instagram_link
                        await handle_instagram_link(client, orig_msg)
                    else:
                        # سایر پلتفرم‌ها
                        logger.info(f"[VERIFY_JOIN] Processing universal link")
                        from plugins.universal_downloader import handle_universal_link
                        await handle_universal_link(client, orig_msg)
                        
                except Exception as msg_error:
                    logger.error(f"[VERIFY_JOIN] Error fetching/processing message: {msg_error}")
                    await client.send_message(
                        chat_id=pending['chat_id'],
                        text="❗️ خطا در پردازش لینک. لطفاً دوباره لینک را ارسال کنید."
                    )
                    
            except Exception as e:
                logger.error(f"[VERIFY_JOIN] Error processing pending link: {e}", exc_info=True)
    else:
        # هنوز در برخی کانال‌ها عضو نیست
        channels_text = "\n".join([
            f"• {lock.channel_name or lock.channel_username or lock.channel_id}"
            for lock in not_joined
        ])
        
        await callback_query.answer(
            f"❌ هنوز در این کانال‌ها عضو نشده‌اید:\n\n{channels_text}\n\n"
            f"لطفاً ابتدا عضو شوید.",
            show_alert=True
        )
