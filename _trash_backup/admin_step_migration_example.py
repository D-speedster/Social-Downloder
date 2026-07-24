"""
نمونه مهاجرت admin_step به AdminUserState
این فایل فقط برای آموزش است و نباید اجرا شود
"""

# ============================================================
# مثال 1: Manual Recovery (بخشی مهاجرت شده)
# ============================================================

# ❌ قبل از مهاجرت:
@Client.on_message(filters.user(ADMIN) & filters.regex(r'^📨 پیام‌های آفلاین$'))
async def manual_recovery_menu(_: Client, message: Message):
    admin_logger.info(f"[ADMIN] manual recovery menu opened by {message.from_user.id}")
    
    # ❌ استفاده از global admin_step
    admin_step['manual_recovery'] = 1
    
    await message.reply_text("...")


# ✅ بعد از مهاجرت:
@Client.on_message(filters.user(ADMIN) & filters.regex(r'^📨 پیام‌های آفلاین$'))
async def manual_recovery_menu(_: Client, message: Message):
    user_id = message.from_user.id  # ✅ دریافت user_id
    admin_logger.info(f"[ADMIN] manual recovery menu opened by {user_id}")
    
    # ✅ استفاده از per-user state
    state = get_admin_user_state(user_id)
    state.manual_recovery['step'] = 1
    
    await message.reply_text("...")


# ============================================================
# مثال 2: Broadcast System
# ============================================================

# ❌ قبل از مهاجرت:
@Client.on_message(filters.user(ADMIN) & filters.regex(r'^📢 ارسال همگانی$'))
async def admin_menu_broadcast(_: Client, message: Message):
    admin_logger.info(f"[ADMIN] broadcast start via text by {message.from_user.id}")
    
    # ❌ Global state - conflict بین ادمین‌ها
    admin_step['broadcast'] = 1
    
    await message.reply_text(
        "نوع ارسال همگانی را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 ارسال همگانی", callback_data="broadcast_normal")],
            [InlineKeyboardButton("↗️ فوروارد همگانی", callback_data="broadcast_forward")],
            [InlineKeyboardButton("❌ لغو", callback_data="broadcast_cancel")]
        ])
    )


# ✅ بعد از مهاجرت:
@Client.on_message(filters.user(ADMIN) & filters.regex(r'^📢 ارسال همگانی$'))
async def admin_menu_broadcast(_: Client, message: Message):
    user_id = message.from_user.id  # ✅ شناسایی ادمین
    admin_logger.info(f"[ADMIN] broadcast start via text by {user_id}")
    
    # ✅ Per-user state
    state = get_admin_user_state(user_id)
    state.broadcast['step'] = 1
    
    await message.reply_text(
        "نوع ارسال همگانی را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 ارسال همگانی", callback_data="broadcast_normal")],
            [InlineKeyboardButton("↗️ فوروارد همگانی", callback_data="broadcast_forward")],
            [InlineKeyboardButton("❌ لغو", callback_data="broadcast_cancel")]
        ])
    )


# ============================================================
# مثال 3: Broadcast Callback Handler
# ============================================================

# ❌ قبل از مهاجرت:
@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^broadcast_.*$'))
async def handle_broadcast_callbacks(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    
    if data == "broadcast_normal":
        # ❌ تغییر global state
        admin_step['broadcast'] = 2
        admin_step['broadcast_type'] = 'normal'
        
        await callback_query.edit_message_text("محتوای خود را ارسال کنید")
    
    elif data == "broadcast_cancel":
        # ❌ Reset global state
        admin_step['broadcast'] = 0
        admin_step['broadcast_type'] = ''
        admin_step['broadcast_content'] = None
        
        await callback_query.edit_message_text("❌ لغو شد")


# ✅ بعد از مهاجرت:
@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^broadcast_.*$'))
async def handle_broadcast_callbacks(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    user_id = callback_query.from_user.id  # ✅ شناسایی ادمین
    state = get_admin_user_state(user_id)  # ✅ دریافت state شخصی
    
    if data == "broadcast_normal":
        # ✅ تغییر per-user state
        state.broadcast['step'] = 2
        state.broadcast['type'] = 'normal'
        
        await callback_query.edit_message_text("محتوای خود را ارسال کنید")
    
    elif data == "broadcast_cancel":
        # ✅ Reset per-user state (با متد helper)
        state.reset_broadcast()
        
        await callback_query.edit_message_text("❌ لغو شد")


# ============================================================
# مثال 4: Broadcast Content Handler با Filter
# ============================================================

# ❌ قبل از مهاجرت:
# فیلتر global state را چک می‌کند
broadcast_content_filter = filters.create(
    lambda _, __, m: admin_step.get('broadcast') == 2 and admin_step.get('broadcast_type') != ''
)

@Client.on_message(broadcast_content_filter & filters.user(ADMIN))
async def handle_broadcast_content(client: Client, message: Message):
    # ❌ استفاده از global state
    broadcast_type = admin_step['broadcast_type']
    
    # ذخیره محتوا
    admin_step['broadcast_content'] = {
        'message_id': message.id,
        'chat_id': message.chat.id,
    }
    admin_step['broadcast'] = 3  # waiting confirmation
    
    await message.reply_text("آیا مطمئن هستید؟")


# ✅ بعد از مهاجرت:
# فیلتر per-user state را چک می‌کند
def broadcast_content_filter_func(_, __, m):
    """
    فیلتر برای دریافت محتوای broadcast
    فقط زمانی که کاربر در مرحله 2 است
    """
    if not m.from_user:
        return False
    
    user_id = m.from_user.id
    state = get_admin_user_state(user_id)
    
    # ✅ چک per-user state
    return (
        state.broadcast['step'] == 2 and 
        state.broadcast['type'] != ''
    )

broadcast_content_filter = filters.create(broadcast_content_filter_func)

@Client.on_message(broadcast_content_filter & filters.user(ADMIN))
async def handle_broadcast_content(client: Client, message: Message):
    user_id = message.from_user.id  # ✅ شناسایی ادمین
    state = get_admin_user_state(user_id)  # ✅ دریافت state
    
    # ✅ استفاده از per-user state
    broadcast_type = state.broadcast['type']
    
    # ذخیره محتوا
    state.broadcast['content'] = {
        'message_id': message.id,
        'chat_id': message.chat.id,
    }
    state.broadcast['step'] = 3  # waiting confirmation
    
    await message.reply_text("آیا مطمئن هستید؟")


# ============================================================
# مثال 5: Cookie Management
# ============================================================

# ❌ قبل از مهاجرت:
@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^cookie_add_text$'))
async def cookie_add_text_cb(_: Client, callback_query: CallbackQuery):
    # ❌ Global state
    admin_step['add_cookie'] = 'text'
    await callback_query.message.edit_text("متن کوکی را ارسال کنید")


add_cookie_filter = filters.create(
    lambda _, __, m: admin_step.get('add_cookie') in ['text', 'file']
)

@Client.on_message(add_cookie_filter & filters.user(ADMIN), group=8)
async def handle_cookie_input(client: Client, message: Message):
    # ❌ استفاده از global state
    mode = admin_step.get('add_cookie')
    
    if mode == 'text':
        # پردازش کوکی متنی
        pass
    
    # ❌ پاکسازی global state
    admin_step.pop('add_cookie', None)


# ✅ بعد از مهاجرت:
@Client.on_callback_query(filters.user(ADMIN) & filters.regex(r'^cookie_add_text$'))
async def cookie_add_text_cb(_: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id  # ✅ شناسایی ادمین
    state = get_admin_user_state(user_id)  # ✅ دریافت state
    
    # ✅ Per-user state
    state.add_cookie = 'text'
    
    await callback_query.message.edit_text("متن کوکی را ارسال کنید")


def add_cookie_filter_func(_, __, m):
    """فیلتر برای دریافت ورودی cookie"""
    if not m.from_user:
        return False
    
    user_id = m.from_user.id
    state = get_admin_user_state(user_id)
    
    # ✅ چک per-user state
    return state.add_cookie in ['text', 'file']

add_cookie_filter = filters.create(add_cookie_filter_func)

@Client.on_message(add_cookie_filter & filters.user(ADMIN), group=8)
async def handle_cookie_input(client: Client, message: Message):
    user_id = message.from_user.id  # ✅ شناسایی ادمین
    state = get_admin_user_state(user_id)  # ✅ دریافت state
    
    # ✅ استفاده از per-user state
    mode = state.add_cookie
    
    if mode == 'text':
        # پردازش کوکی متنی
        pass
    
    # ✅ پاکسازی per-user state
    state.add_cookie = None


# ============================================================
# مثال 6: Cancel Command (Multi-State Reset)
# ============================================================

# ❌ قبل از مهاجرت:
@Client.on_message(filters.command('cancel') & filters.user(ADMIN))
async def cancel_admin_operations(client: Client, message: Message):
    cancelled_operations = []
    
    # ❌ Reset global states یکی یکی
    if admin_step.get('broadcast', 0) > 0:
        admin_step['broadcast'] = 0
        admin_step['broadcast_type'] = ''
        admin_step['broadcast_content'] = None
        cancelled_operations.append("ارسال همگانی")
    
    if admin_step.get('sp', 0) == 1:
        admin_step['sp'] = 0
        cancelled_operations.append("تنظیم اسپانسر")
    
    if admin_step.get('manual_recovery', 0) > 0:
        admin_step['manual_recovery'] = 0
        cancelled_operations.append("بازیابی دستی")
    
    if admin_step.get('advertisement', 0) > 0:
        admin_step['advertisement'] = 0
        cancelled_operations.append("تنظیم تبلیغات")
    
    if 'add_cookie' in admin_step:
        del admin_step['add_cookie']
        cancelled_operations.append("افزودن کوکی")
    
    if cancelled_operations:
        text = f"✅ عملیات‌های زیر لغو شدند:\n• " + "\n• ".join(cancelled_operations)
    else:
        text = "ℹ️ عملیات فعالی برای لغو وجود ندارد"
    
    await message.reply(text, reply_markup=admin_reply_kb())


# ✅ بعد از مهاجرت:
@Client.on_message(filters.command('cancel') & filters.user(ADMIN))
async def cancel_admin_operations(client: Client, message: Message):
    user_id = message.from_user.id  # ✅ شناسایی ادمین
    state = get_admin_user_state(user_id)  # ✅ دریافت state شخصی
    
    cancelled_operations = []
    
    # ✅ چک و reset per-user states با متدهای helper
    if state.broadcast['step'] > 0:
        state.reset_broadcast()
        cancelled_operations.append("ارسال همگانی")
    
    if state.sponsor['step'] == 1:
        state.sponsor['step'] = 0
        cancelled_operations.append("تنظیم اسپانسر")
    
    if state.manual_recovery['step'] > 0:
        state.reset_manual_recovery()
        cancelled_operations.append("بازیابی دستی")
    
    if state.advertisement['step'] > 0:
        state.reset_advertisement()
        cancelled_operations.append("تنظیم تبلیغات")
    
    if state.add_cookie is not None:
        state.add_cookie = None
        cancelled_operations.append("افزودن کوکی")
    
    # یا استفاده از متد reset_all()
    # state.reset_all()
    # cancelled_operations = ["همه عملیات"]
    
    if cancelled_operations:
        text = f"✅ عملیات‌های زیر لغو شدند:\n• " + "\n• ".join(cancelled_operations)
    else:
        text = "ℹ️ عملیات فعالی برای لغو وجود ندارد"
    
    await message.reply(text, reply_markup=admin_reply_kb())


# ============================================================
# مثال 7: Sponsor Setup (پیچیده‌ترین مورد)
# ============================================================

# ❌ قبل از مهاجرت:
@Client.on_message(filters.user(ADMIN) & filters.regex(r'^📢 تنظیم اسپانسر$'))
async def admin_menu_sponsor(_: Client, message: Message):
    user_id = message.from_user.id
    
    # ❌ Reset other global states
    admin_step['sp'] = 0
    admin_step['broadcast'] = 0
    admin_step['advertisement'] = 0
    admin_step['waiting_msg'] = 0
    
    # Set sponsor state
    admin_step['sp'] = 1
    
    await message.reply_text("لطفاً آیدی یا یوزرنیم کانال را ارسال کنید:")


# فیلتر sponsor input
sponsor_input_filter = filters.create(
    lambda _, __, m: admin_step.get('sp') == 1
)

@Client.on_message(sponsor_input_filter & filters.user(ADMIN), group=10)
async def handle_sponsor_input(client: Client, message: Message):
    text = message.text.strip()
    
    # پردازش و validation
    # ...
    
    # ❌ Reset global state
    admin_step['sp'] = 0
    
    await message.reply_text("✅ اسپانسر تنظیم شد")


# ✅ بعد از مهاجرت:
@Client.on_message(filters.user(ADMIN) & filters.regex(r'^📢 تنظیم اسپانسر$'))
async def admin_menu_sponsor(_: Client, message: Message):
    user_id = message.from_user.id
    state = get_admin_user_state(user_id)  # ✅ دریافت state
    
    # ✅ Reset only relevant per-user states
    state.broadcast['step'] = 0
    state.advertisement['step'] = 0
    state.waiting_msg['step'] = 0
    
    # Set sponsor state
    state.sponsor['step'] = 1
    
    await message.reply_text("لطفاً آیدی یا یوزرنیم کانال را ارسال کنید:")


# فیلتر sponsor input
def sponsor_input_filter_func(_, __, m):
    if not m.from_user:
        return False
    
    user_id = m.from_user.id
    state = get_admin_user_state(user_id)
    
    # ✅ چک per-user state
    return state.sponsor['step'] == 1

sponsor_input_filter = filters.create(sponsor_input_filter_func)

@Client.on_message(sponsor_input_filter & filters.user(ADMIN), group=10)
async def handle_sponsor_input(client: Client, message: Message):
    user_id = message.from_user.id
    state = get_admin_user_state(user_id)  # ✅ دریافت state
    
    text = message.text.strip()
    
    # پردازش و validation
    # ...
    
    # ✅ Reset per-user state
    state.sponsor['step'] = 0
    
    await message.reply_text("✅ اسپانسر تنظیم شد")


# ============================================================
# خلاصه مزایا:
# ============================================================

"""
✅ مزایای استفاده از AdminUserState:

1. عدم تداخل (No Conflicts):
   - هر ادمین state مستقل دارد
   - ادمین 1 می‌تواند broadcast کند، ادمین 2 sponsor setup کند

2. Thread-Safe:
   - هر user_id یک instance جداگانه دارد
   - از race condition جلوگیری می‌کند

3. Auto-Expiration:
   - state بعد از 5 دقیقه (timeout) خودکار expire می‌شود
   - از memory leak جلوگیری می‌کند

4. Clean Code:
   - منطق واضح‌تر با state.field به جای admin_step['field']
   - متدهای helper مثل reset_broadcast()

5. Easier Debugging:
   - می‌توانید state هر ادمین را جداگانه بررسی کنید
   - admin_logger.debug(f"State for {user_id}: {state.__dict__}")

6. Scalability:
   - به راحتی فیلدهای جدید اضافه می‌شود
   - بدون نیاز به تغییر global dictionary
"""
