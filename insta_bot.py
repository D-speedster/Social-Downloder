import logging
import json
import http.client
import tempfile
import os
import requests
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ----------------- تنظیمات لاگ -----------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ----------------- دستور /start -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! لینک اینستاگرام رو برام بفرست تا فایل ویدیو یا صوت رو برات بفرستم."
    )

# ----------------- دریافت پیام -----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if "instagram.com" not in url:
        await update.message.reply_text("لطفاً یک لینک اینستاگرام معتبر بفرستید.")
        return

    await update.message.reply_text("در حال پردازش لینک و دریافت فایل...")

    # ------------- درخواست به API -------------
    conn = http.client.HTTPSConnection("social-download-all-in-one.p.rapidapi.com")
    payload = json.dumps({"url": url})
    headers = {
        'x-rapidapi-key': "d51a95d960mshb5f65a8e122bb7fp11b675jsn63ff66cbc6cf",
        'x-rapidapi-host': "social-download-all-in-one.p.rapidapi.com",
        'Content-Type': "application/json"
    }
    conn.request("POST", "/v1/social/autolink", payload, headers)
    res = conn.getresponse()
    data = res.read()
    conn.close()

    try:
        result = json.loads(data)
    except Exception as e:
        await update.message.reply_text(f"خطا در پردازش پاسخ API: {e}")
        return

    medias = result.get("medias", [])
    if not medias:
        await update.message.reply_text("هیچ فایل ویدیویی یا صوتی پیدا نشد.")
        return

    # ------------ انتخاب فایل mp4 یا m4a ----------
    media_url = None
    is_video = True
    for media in medias:
        ext = media.get("extension", "")
        if ext in ["mp4", "m4a"]:
            media_url = media.get("url")
            is_video = ext == "mp4"
            break

    if not media_url:
        await update.message.reply_text("هیچ فایل مناسب پیدا نشد.")
        return

    # ------------ دانلود موقت روی سرور (ویندوز-سازگار) ----------
    try:
        response = requests.get(media_url, stream=True)
        response.raise_for_status()
    except Exception as e:
        await update.message.reply_text(f"خطا در دانلود فایل: {e}")
        return

    suffix = ".mp4" if is_video else ".m4a"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)

    try:
        with open(tmp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # ------------ اطلاع‌رسانی در حال آپلود ------------
        await update.message.chat.send_action(action=ChatAction.UPLOAD_VIDEO if is_video else ChatAction.UPLOAD_AUDIO)

        # ------------ ارسال به تلگرام بدون timeout مستقیم ----------
        if is_video:
            with open(tmp_path, "rb") as f:
                await update.message.reply_video(video=f, caption=result.get("title", ""))
        else:
            with open(tmp_path, "rb") as f:
                await update.message.reply_audio(audio=f, caption=result.get("title", ""))

    except Exception as e:
        await update.message.reply_text(f"خطا در ارسال فایل: {e}")

    finally:
        os.remove(tmp_path)

# ----------------- برنامه اصلی -----------------
if __name__ == "__main__":
    # افزایش timeout کلی در ساخت Application
    app = ApplicationBuilder()\
        .token("213165527:AAHfSWAD5jmHbabQGxfgtkTFABlZKEtg1is")\
        .connect_timeout(180)\
        .read_timeout(180)\
        .build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()
