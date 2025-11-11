#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pornhub Delivery Bot - Fixed version
توضیحات: این نسخه برای حل دو مشکل اصلی شما بازنویسی شده:
1) پیام ویدیویی که به کاربر ارسال می‌شود بعد از timeout مشخص از چت پاک می‌شود.
2) ابعاد ویدیو (width/height) با بررسی rotation و metadata درست استخراج می‌شوند.
همچنین توابع بلوکه‌کننده در thread pool اجرا می‌شوند تا لوپ async بلوکه نشود.
"""

import os
import sys
import re
import json
import logging
import asyncio
import time
import uuid
import shutil
from dotenv import load_dotenv
from typing import Tuple, Optional

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, RPCError

# ---------- Config & Logging ----------
load_dotenv()

API_ID = os.getenv("API_ID", "")
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "79049016"))

if not API_ID or not API_HASH or not BOT_TOKEN:
    print("Missing API_ID / API_HASH / BOT_TOKEN in environment")
    sys.exit(1)

try:
    API_ID = int(API_ID)
except Exception:
    print("API_ID must be an integer")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Client(
    "pornhub_bot_fixed",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

# storage wrapper (فرض بر این است که فایل pornhub_storage.py وجود دارد و این توابع را دارد)
# اگر ندارید، متدهای زیر را جایگزین منطق واقعی خود کنید.
try:
    import pornhub_storage
except Exception:
    # fallback dummy storage to avoid crash during development
    class _DummyStorage:
        def get_file_info(self, code): return None
        def mark_as_downloaded(self, code): pass
        def delete_file(self, code): pass
    pornhub_storage = _DummyStorage()

STORAGE_FILE = "data/pornhub_files.json"
ACTIVE_DOWNLOADS = set()
FILE_REGEX = re.compile(r"FILE_([A-Z0-9]{6,12})", re.IGNORECASE)

# ---------- Utilities ----------
def format_size(n: int) -> str:
    for unit in ['B','KB','MB','GB','TB']:
        if n < 1024.0:
            return f"{n:3.1f}{unit}"
        n /= 1024.0
    return f"{n:.1f}PB"

def ensure_dirs():
    os.makedirs("tmp", exist_ok=True)
    os.makedirs("data", exist_ok=True)

def check_binaries() -> bool:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        logger.error("ffmpeg/ffprobe not found in PATH. Please install them.")
        return False
    return True

# ---------- Media helpers (run-blocking logic executed via asyncio.to_thread) ----------
def _get_video_metadata_blocking(file_path: str) -> Tuple[int, int, int]:
    """
    Blocking function: calls ffprobe and returns (duration_seconds, width, height)
    Also handles rotation tags and swaps width/height when needed.
    """
    import subprocess, json

    duration = 0
    width = 0
    height = 0
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0 or not result.stdout:
            logger.warning("ffprobe returned non-zero or empty output")
            return duration, width, height

        metadata = json.loads(result.stdout)

        if "format" in metadata and "duration" in metadata["format"]:
            try:
                duration = int(float(metadata["format"]["duration"]))
            except Exception:
                duration = 0

        # find first video stream
        rotation = 0
        for stream in metadata.get("streams", []):
            if stream.get("codec_type") == "video":
                width = int(stream.get("width", 0) or 0)
                height = int(stream.get("height", 0) or 0)
                # rotation may be in tags or side_data_list
                tags = stream.get("tags") or {}
                if "rotate" in tags:
                    try:
                        rotation = int(tags["rotate"])
                    except:
                        rotation = 0
                side = stream.get("side_data_list") or []
                for sd in side:
                    if sd.get("rotation") is not None:
                        try:
                            rotation = int(sd.get("rotation") or 0)
                        except:
                            pass
                break

        # if rotated 90/270 swap width/height
        if rotation in (90, 270) and width and height:
            width, height = height, width

        logger.info(f"ffprobe metadata for {file_path}: duration={duration}s, {width}x{height}, rot={rotation}")
    except Exception as e:
        logger.exception("Error during ffprobe metadata extraction: %s", e)

    return duration, width, height

def _generate_thumbnail_blocking(file_path: str, thumb_path: str, time_pos: int = 2) -> bool:
    """
    Blocking: uses ffmpeg to generate a thumbnail at time_pos seconds.
    Returns True on success.
    """
    import subprocess
    try:
        cmd = [
            "ffmpeg", "-y", "-ss", str(time_pos), "-i", file_path,
            "-frames:v", "1", "-q:v", "2", thumb_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and os.path.exists(thumb_path):
            logger.info("Thumbnail created: %s", thumb_path)
            return True
        else:
            logger.warning("ffmpeg thumbnail failed: rc=%s, stderr=%s", result.returncode, result.stderr[:200])
            return False
    except Exception as e:
        logger.exception("Thumbnail generation error: %s", e)
        return False

# ---------- Async wrappers ----------
async def get_video_metadata(file_path: str) -> Tuple[int, int, int]:
    return await asyncio.to_thread(_get_video_metadata_blocking, file_path)

async def generate_thumbnail(file_path: str, thumb_path: str, time_pos: int = 2) -> bool:
    return await asyncio.to_thread(_generate_thumbnail_blocking, file_path, thumb_path, time_pos)

# ---------- Async deletion & cleanup ----------
async def schedule_delete(client: Client, file_code: str, file_path: str, thumb_path: Optional[str], chat_id: int, message_id: int, delay: int = 120):
    """
    پس از delay، فایل محلی و thumbnail را حذف می‌کند، رکورد استوریج را پاک می‌کند
    و پیام ارسالی در چت کاربر را حذف می‌کند.
    این تابع async است و باید با asyncio.create_task فراخوانی شود.
    """
    try:
        logger.info("⏰ Deletion scheduled for %s in %ds (will delete message %s:%s)", file_code, delay, chat_id, message_id)
        await asyncio.sleep(delay)

        # try delete message (bot can delete its own messages)
        try:
            await client.delete_messages(chat_id, message_id)
            logger.info("🗑️ Deleted sent message %s:%s", chat_id, message_id)
        except Exception as e:
            logger.warning("Couldn't delete message %s:%s — %s", chat_id, message_id, e)

        # local files
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info("✅ File deleted: %s", file_path)
        except Exception as e:
            logger.warning("Failed to remove file %s: %s", file_path, e)

        try:
            if thumb_path and os.path.exists(thumb_path):
                os.remove(thumb_path)
                logger.info("✅ Thumb deleted: %s", thumb_path)
        except Exception as e:
            logger.warning("Failed to remove thumb %s: %s", thumb_path, e)

        # delete storage entry (run in thread if blocking)
        try:
            await asyncio.to_thread(pornhub_storage.delete_file, file_code)
            logger.info("✅ Storage entry deleted: %s", file_code)
        except Exception as e:
            logger.exception("Storage deletion failed for %s: %s", file_code, e)

        # cleanup active downloads set
        try:
            ACTIVE_DOWNLOADS.discard(file_code)
        except:
            pass
    except Exception as e:
        logger.exception("Error in schedule_delete for %s: %s", file_code, e)

# ---------- Bot Handlers ----------
@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    await message.reply_text("سلام — ربات آماده است. کد فایل را بفرستید (مثل FILE_ABCD01)")

@app.on_message(filters.command("status"))
async def status_cmd(client: Client, message: Message):
    # ساده سازی: وضعیت کلی را نشان می‌دهد
    try:
        count = 0
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            count = len(data)
        except FileNotFoundError:
            count = 0
        except Exception as e:
            logger.exception("Error reading storage file: %s", e)
            count = 0

        text = f"📦 ذخیره‌سازی: {count} فایل\n🔁 دانلودهای فعال: {len(ACTIVE_DOWNLOADS)}"
        await message.reply_text(text)
    except Exception as e:
        logger.exception("Status command error: %s", e)
        await message.reply_text("❌ خطا در دریافت وضعیت")

@app.on_message(filters.regex(FILE_REGEX))
async def handle_file_code(client: Client, message: Message):
    """
    هندلر اصلی: وقتی کاربر کد فایل شبیه FILE_XXXX فرستاد:
    - اطلاعات را از storage می‌گیرد
    - اگر موجود بود، فایل را از مسیر محلی ارسال می‌کند
    - بعد از ارسال، پیام را برای حذف زمانبندی می‌کند
    """
    m = FILE_REGEX.search(message.text or "")
    if not m:
        return

    file_code = m.group(1).upper()
    user_id = message.from_user.id if message.from_user else None

    if file_code in ACTIVE_DOWNLOADS:
        await message.reply_text("⏳ این فایل در حال آماده‌سازی است. لطفا کمی صبر کنید.")
        return

    # علامت دانلود فعال
    ACTIVE_DOWNLOADS.add(file_code)

    try:
        # گرفتن info از storage (ممکنه blocking باشد — با to_thread اجرا می‌کنیم)
        file_info = await asyncio.to_thread(pornhub_storage.get_file_info, file_code)
        if not file_info:
            await message.reply_text("❌ فایل پیدا نشد یا منبع معتبر نیست.")
            ACTIVE_DOWNLOADS.discard(file_code)
            return

        file_path = file_info.get("path")
        if not file_path or not os.path.exists(file_path):
            await message.reply_text("❌ فایل محلی موجود نیست.")
            ACTIVE_DOWNLOADS.discard(file_code)
            return

        file_size = os.path.getsize(file_path)
        await message.reply_text(f"🔎 پیدا شد — حجم: {format_size(file_size)}\n⏳ در حال آماده‌سازی برای ارسال...")

        # metadata با to_thread
        duration, width, height = await get_video_metadata(file_path)

        # تولید thumbnail امن (نام یکتا)
        thumb_name = f"thumb_{uuid.uuid4().hex}.jpg"
        thumb_path = os.path.join("tmp", thumb_name)
        thumb_created = await generate_thumbnail(file_path, thumb_path, time_pos=2)
        if not thumb_created:
            thumb_path = None

        # آماده‌سازی پارامترهای ارسال ویدیو
        video_params = {
            "caption": f"File {file_code} — size: {format_size(file_size)}",
            "supports_streaming": True,
            "duration": duration or None,
        }
        # only include thumb if exists
        if thumb_path:
            video_params["thumb"] = thumb_path

        # Send video, catch FloodWait etc.
        sent_msg = None
        try:
            logger.info("📤 Uploading %s (size=%s)", file_path, format_size(file_size))
            # use send_video and capture returned Message
            sent_msg = await message.reply_video(file_path, **video_params)
            logger.info("✅ File %s sent to user %s (msg_id=%s)", file_code, user_id, getattr(sent_msg, "message_id", None))
        except FloodWait as fw:
            logger.warning("FloodWait: sleeping %s", fw.x)
            await asyncio.sleep(fw.x + 1)
            sent_msg = await message.reply_video(file_path, **video_params)
        except RPCError as rpc:
            logger.exception("RPCError while sending video: %s", rpc)
            await message.reply_text("❌ خطا در ارسال ویدیو (RPC).")
            # don't schedule deletion of message since not sent
            await asyncio.to_thread(pornhub_storage.mark_as_downloaded, file_code)
            ACTIVE_DOWNLOADS.discard(file_code)
            return
        except Exception as e:
            logger.exception("Unknown error while sending video: %s", e)
            await message.reply_text("❌ خطا در ارسال ویدیو.")
            await asyncio.to_thread(pornhub_storage.mark_as_downloaded, file_code)
            ACTIVE_DOWNLOADS.discard(file_code)
            return

        # حذف status message قبلی در صورت وجود (اینجا ساده است)
        # اگر خواستی پیام وضعیت را نگهداری نکنی، می‌توانی آن را حذف کنی.

        # علامت‌گذاری در storage
        try:
            await asyncio.to_thread(pornhub_storage.mark_as_downloaded, file_code)
        except Exception:
            logger.exception("mark_as_downloaded failed for %s", file_code)

        # schedule deletion: حذف پیام ارسالی + فایل محلی + رکورد storage
        if sent_msg:
            chat_id = sent_msg.chat.id
            message_id = sent_msg.message_id
            # create async task
            asyncio.create_task(schedule_delete(app, file_code, file_path, thumb_path, chat_id, message_id, delay=120))
            logger.info("⏰ Deletion scheduled for %s in 120s", file_code)
        else:
            # fallback: اگر پیام ارسال نشده، فقط فایل را پاک کن (بعد از delay)
            asyncio.create_task(schedule_delete(app, file_code, file_path, thumb_path, message.chat.id, 0, delay=120))

    finally:
        # در هر صورت از active downloads خارج کن
        ACTIVE_DOWNLOADS.discard(file_code)

# ---------- Startup / Shutdown ----------
@app.on_message(filters.command("help"))
async def help_cmd(client: Client, message: Message):
    await message.reply_text("راهنما: فایل را با کد FILE_XXXXX بفرستید تا برایتان ارسال کنم.")

@app.on_message(filters.command("ping"))
async def ping_cmd(client: Client, message: Message):
    await message.reply_text("pong")

@app.on_message(filters.command("debug") & filters.user(ADMIN_ID))
async def debug_cmd(client: Client, message: Message):
    await message.reply_text(f"ACTIVE_DOWNLOADS={len(ACTIVE_DOWNLOADS)}")

# ---------- Main ----------
def main():
    ensure_dirs()
    if not check_binaries():
        logger.error("ffmpeg/ffprobe missing — exiting.")
        sys.exit(1)
    logger.info("Starting bot...")
    app.run()

if __name__ == "__main__":
    main()
