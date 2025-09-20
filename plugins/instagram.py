from pyrogram import Client, filters
from pyrogram.types import Message
from plugins import constant
from plugins.sqlite_db_wrapper import DB
from datetime import datetime
from dateutil import parser
import os, re, time
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import MessageNotModified
import os
from utils.util import convert_size
from plugins.start import join

PATH = constant.PATH
txt = constant.TEXT
instaregex = r"^((?:https?:)?\/\/)?((?:www|m)\.)?((?:instagram\.com))(\/(?:p\/|reel\/|tv\/|stories\/))([\w\-]+)(\S+)?$"

@Client.on_message(filters.regex(instaregex) & filters.private & join)
async def download_instagram(_: Client, message: Message):
    # Helpers (async-safe)
    async def _safe_edit(msg, text, reply_markup=None):
        try:
            await msg.edit_text(text, reply_markup=reply_markup)
        except MessageNotModified:
            pass
        except Exception:
            pass

    def _format_status_text(title: str, type_label: str, size_mb: str, status: str):
        title_line = f"عنوان:\n{title}" if title else "عنوان:\nنامشخص"
        size_line = f"{size_mb} MB" if size_mb not in (None, "", "نامشخص") else "نامشخص"
        return (
            "وضعیت دانلود 📥\n\n"
            f"{title_line}\n"
            f"نوع: {type_label}\n"
            f"حجم: {size_line}\n"
            f"وضعیت: {status}"
        )

    # Track info
    title = None
    type_label = "📄 فایل"
    total_bytes = None

    # Enforce daily block if present
    try:
        now = datetime.now()
        blocked_until_str = DB().get_blocked_until(message.from_user.id)
        if blocked_until_str:
            bu = None
            try:
                bu = datetime.fromisoformat(blocked_until_str)
            except Exception:
                try:
                    bu = datetime.strptime(blocked_until_str, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    bu = None
            if bu and now < bu:
                seconds = int((bu - now).total_seconds())
                await message.reply_text(txt['rate_limit'].format(seconds=seconds))
                return
    except Exception as e:
        print(f"Error checking blocked_until: {e}")

    # Try to send typing action compatibly
    try:
        from pyrogram.enums import ChatAction as _ChatAction
        await client.send_chat_action(message.chat.id, _ChatAction.TYPING)
    except Exception:
        try:
            await client.send_chat_action(message.chat.id, "typing")
        except Exception:
            pass  # Ignore if typing action fails

    # Get custom waiting message from database
    db = DB()
    custom_message_data = db.get_waiting_message_full('instagram')
    
    # Send waiting message based on type
    if custom_message_data and custom_message_data.get('type') == 'gif':
        status_msg = await message.reply_animation(
            animation=custom_message_data['content'],
            caption="⏳ در حال آماده‌سازی لینک اینستاگرام..."
        )
    elif custom_message_data and custom_message_data.get('type') == 'sticker':
        await message.reply_sticker(sticker=custom_message_data['content'])
        status_msg = await message.reply_text("⏳ در حال آماده‌سازی لینک اینستاگرام...")
    else:
        # Text message (default or custom)
        waiting_text = custom_message_data.get('content', "⏳ در حال آماده‌سازی لینک اینستاگرام...") if custom_message_data else "⏳ در حال آماده‌سازی لینک اینستاگرام..."
        status_msg = await message.reply_text(waiting_text)

    try:
        from yt_dlp import YoutubeDL
        out_dir = os.path.join(".", "Downloads", "instagram")
        os.makedirs(out_dir, exist_ok=True)

        last = {"t": 0.0, "p": -1}
        def on_download_hook(d):
            nonlocal total_bytes
            try:
                st = d.get('status')
                if st in ("downloading", "finished"):
                    tb = d.get('total_bytes') or d.get('total_bytes_estimate')
                    if tb:
                        total_bytes = tb
                if st == 'downloading':
                    downloaded = d.get('downloaded_bytes') or 0
                    if total_bytes:
                        percent = int(downloaded * 100 / total_bytes)
                        size_mb = f"{(total_bytes/1024/1024):.2f}"
                    else:
                        percent_str = (d.get('_percent_str') or '').strip().replace('%', '').strip()
                        try:
                            percent = int(float(percent_str))
                        except Exception:
                            percent = 0
                        size_mb = "نامشخص"
                    now = time.time()
                    if percent == last["p"] and (now - last["t"]) < 1.0:
                        return
                    last["p"], last["t"] = percent, now
                    text = _format_status_text(title or "Instagram", type_label, size_mb, "در حال دانلود ...")
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"🚀 پیشرفت: {percent}٪", callback_data="ignore")]])
                    # Use async version for yt-dlp hook
                    try:
                        import asyncio
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(status_msg.edit_text(text, reply_markup=kb))
                        else:
                            loop.run_until_complete(status_msg.edit_text(text, reply_markup=kb))
                    except Exception:
                        pass
                elif st == 'finished':
                    # Use async version for yt-dlp hook
                    try:
                        import asyncio
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(status_msg.edit_text("🔁 دانلود پایان یافت. در حال آماده‌سازی برای ارسال…"))
                        else:
                            loop.run_until_complete(status_msg.edit_text("🔁 دانلود پایان یافت. در حال آماده‌سازی برای ارسال…"))
                    except Exception:
                        pass
            except Exception:
                pass

        ydl_opts = {
            'outtmpl': os.path.join(out_dir, '%(title)s.%(ext)s'),
            'format': 'mp4/best',
            'quiet': True,
            'noplaylist': True,
            'progress_hooks': [on_download_hook],
            'socket_timeout': 30,
            'no_warnings': True,
            'extract_flat': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
        }
        # Instagram cookies support from cookie pool
        from cookie_manager import cookie_manager
        
        cookie_content = cookie_manager.get_cookie('instagram')
        use_cookies = cookie_content is not None
        
        if use_cookies:
            try:
                import tempfile
                temp_cookie_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                temp_cookie_file.write(cookie_content)
                temp_cookie_file.close()
                ydl_opts['cookiefile'] = temp_cookie_file.name
            except Exception as e:
                print(f"Failed to set Instagram cookies: {e}")
                use_cookies = False
        else:
            print("Warning: No Instagram cookies available in pool")

        temp_cookie_file_path = None
        try:
            with YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(message.text, download=True)
                    if not info:
                        raise Exception("No video information extracted")
                    file_path = ydl.prepare_filename(info)
                    if not os.path.exists(file_path):
                        raise Exception("Downloaded file not found")
                    
                    # Update cookie usage stats on success
                    if use_cookies:
                        # Find cookie ID to update usage
                        cookies = cookie_manager.get_cookies('instagram', active_only=True)
                        for cookie in cookies:
                            if cookie.get('data') == cookie_content:
                                cookie_manager.update_usage('instagram', cookie['id'])
                                break
                        
                except Exception as e:
                    # Mark cookie as invalid if download failed with cookies
                    if use_cookies:
                        # Find cookie ID to mark as invalid
                        cookies = cookie_manager.get_cookies('instagram', active_only=True)
                        for cookie in cookies:
                            if cookie.get('data') == cookie_content:
                                cookie_manager.mark_invalid('instagram', cookie['id'])
                                break
                    raise Exception(f"Download failed: {str(e)}")
        finally:
            # Clean up temporary cookie file
            if use_cookies and 'temp_cookie_file' in locals():
                temp_cookie_file_path = temp_cookie_file.name
                try:
                    os.unlink(temp_cookie_file_path)
                except:
                    pass

        # determine title and type
        title = info.get('title') or "Instagram"
        ext = (info.get('ext') or "").lower()
        if ext in ("mp4", "mov", "mkv", "avi", "webm"):
            type_label = "🎥 ویدیو"
        elif ext in ("jpg", "jpeg", "png", "webp"):
            type_label = "🖼️ عکس"
        else:
            type_label = "📄 فایل"

        total_mb_text = f"{(total_bytes/1024/1024):.2f}" if total_bytes else "نامشخص"
        await _safe_edit(
            status_msg,
            _format_status_text(title, type_label, total_mb_text, "در حال آپلود ..."),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚀 پیشرفت: 0٪", callback_data="ignore")]])
        )

        def on_upload_progress(current, total):
            try:
                percent = int(current * 100 / total) if total else 0
                kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"🚀 پیشرفت: {percent}٪", callback_data="ignore")]])
                text = _format_status_text(title, type_label, total_mb_text, "در حال آپلود ...")
                # Use sync version for progress callback
                try:
                    status_msg.edit_text(text, reply_markup=kb)
                except Exception:
                    pass
            except Exception:
                pass

        sent = None
        try:
            if "ویدیو" in type_label:
                sent = await message.reply_video(
                    video=file_path,
                    caption=title or "",
                    progress=on_upload_progress
                )
            else:
                sent = await message.reply_document(
                    document=file_path,
                    caption=title or "",
                    progress=on_upload_progress
                )
            try:
                await _safe_edit(status_msg, "✅ فایل با موفقیت ارسال شد")
            except Exception:
                pass
        except Exception:
            try:
                sent = await message.reply_document(
                    document=file_path,
                    caption=title or "",
                    progress=on_upload_progress
                )
            except Exception:
                await message.reply_text("❌ خطا در ارسال فایل.")
                sent = None

        # Tag message under the media
        if sent:
            try:
                await sent.reply_text("📥 دریافت شده توسط ربات YouTube | Instagram Save Bot")
            except Exception:
                pass

        # Update request counters and last_download with current time (no per-minute limit)
        DB().increment_request(message.from_user.id, datetime.now().isoformat())

        # Clean up: delete local file after upload
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                # Also clean up any temporary files
                temp_files = [f for f in os.listdir(out_dir) if f.startswith('tmp') or f.endswith('.part')]
                for temp_file in temp_files:
                    try:
                        os.remove(os.path.join(out_dir, temp_file))
                    except Exception:
                        pass
        except Exception as e:
            print(f"Cleanup error: {e}")

    except Exception as e:
        # Improved guidance for login-required / rate-limit cases
        err = str(e)
        if any(s in err.lower() for s in ["login", "rate", "cookies", "cookie", "authentication", "not available"]):
            await message.reply_text(
                "❌ خطا در دانلود اینستاگرام: نیاز به احراز هویت یا دور زدن محدودیت است.\n"
                "لطفاً کوکی‌های اینستاگرام را با دستور /setcookies آپلود کنید (فایل instagram.txt)."
            )
        else:
            await message.reply_text("❌ خطا در دانلود اینستاگرام: " + err)
        print("IG error:", e)


# @Client.on_message(filters.regex(r"instagram\.\|instagr\.am"))
async def download_instagram_async_disabled(client, message):
    pass