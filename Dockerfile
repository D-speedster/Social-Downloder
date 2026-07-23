# ============================================================
# Dockerfile — Social-Downloader (Main Bot)
# Base service برای هر دو سرویس (main-bot و delivery-bot)
# فاز ۱: ربات اصلی (main.py) | فاز ۲: delivery-bot از همین image
# ============================================================

# --- Stage: builder ---
# جدا کردن نصب dependency از image نهایی برای لایه cache بهتر
FROM python:3.11-slim AS builder

# متغیرهای محیطی برای pip
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# نصب build dependencies (برای برخی پکیج‌های native مثل Pillow/cryptography)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# کپی requirements و نصب — این لایه فقط وقتی requirements تغییر کند دوباره build می‌شود
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt


# ============================================================
# --- Stage: runtime ---
# ============================================================
FROM python:3.11-slim AS runtime

# متغیرهای محیطی Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    # مسیر ffmpeg در PATH سیستم (نه مسیر ویندوزی)
    FFMPEG_PATH=ffmpeg \
    # مسیر دیتابیس SQLite روی Linux
    DB_BASE_PATH_LINUX=/var/lib/social-db \
    # لاگ به stdout فعال باشد
    LOG_TO_CONSOLE=1

# نصب وابستگی‌های سطح سیستم
# ffmpeg: برای yt-dlp (merge ویدیو/صدا) و استخراج metadata
# ffprobe: با بسته ffmpeg نصب می‌شود — مورد نیاز bot2.py
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && ffmpeg -version

# کپی packages نصب‌شده از stage builder
COPY --from=builder /install /usr/local

# ایجاد کاربر غیر-root برای امنیت
# UID/GID ثابت برای سازگاری با volume permissions
RUN groupadd --gid 1001 botuser \
    && useradd --uid 1001 --gid 1001 --no-create-home --shell /bin/sh botuser

# ساخت و تنظیم پوشه کاری
WORKDIR /app

# کپی کد پروژه (فایل‌های حساس و runtime در .dockerignore مستثنی شده‌اند)
COPY --chown=botuser:botuser . .

# ساخت فایل .env خالی placeholder تا bot.py wizard را trigger نکند
# مقادیر واقعی از env_file در docker-compose.yml inject می‌شوند
RUN touch /app/.env && chown botuser:botuser /app/.env

# کپی و اجرایی کردن entrypoint
COPY --chown=botuser:botuser entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ساخت پوشه‌های ضروری و تنظیم ownership
# این پوشه‌ها در اجرا توسط volume جایگزین می‌شوند
RUN mkdir -p \
        /app/logs \
        /app/downloads \
        /app/data \
        /app/data/cookies_tmp \
        /app/data/sessions \
        /app/cookies \
        /var/lib/social-db \
    && chown -R botuser:botuser \
        /app \
        /var/lib/social-db

# ============================================================
# مستندسازی Volume‌ها
# تمام مسیرهایی که باید persistent باشند یا sensitive data دارند.
# mount واقعی در docker-compose.yml (فاز ۳) انجام می‌شود.
# ============================================================

# دیتابیس SQLite — داده‌های اصلی کاربران و jobها
VOLUME ["/var/lib/social-db"]

# فایل‌های موقت دانلود + فایل session Pyrogram ربات اصلی
# (session: downloads/ytdownloader3_dev2.session)
VOLUME ["/app/downloads"]

# پوشه لاگ‌ها
VOLUME ["/app/logs"]

# پوشه data: pornhub_files.json، adult_content_settings.json، cookies_tmp/
VOLUME ["/app/data"]

# کوکی‌های YouTube (cookie_youtube.txt, cookies/youtube_cookies.txt, ...)
# این فایل‌ها باید bind mount شوند نه named volume
VOLUME ["/app/cookies"]

# ============================================================

# تغییر به کاربر غیر-root
USER botuser

# تست سلامت: بررسی که Python و ffmpeg کار می‌کنند
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import pyrogram; import yt_dlp" && ffmpeg -version > /dev/null 2>&1 || exit 1

# پورت expose نیازی نیست (bot poll-based است، نه webhook)

# نقطه ورود
ENTRYPOINT ["/entrypoint.sh"]

# دستور پیش‌فرض: ربات اصلی
# برای delivery-bot در docker-compose با command: python bot2.py override می‌شود
CMD ["python", "main.py"]
