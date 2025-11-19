#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instagram Fetcher - سیستم دانلود اختصاصی Instagram
استراتژی 3 لایه برای حداکثر نرخ موفقیت
"""

import os
import time
import asyncio
import http.client
import json
import logging
from typing import Optional, Dict, Tuple
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

from plugins.db_wrapper import DB
from plugins.logger_config import get_logger
from plugins.start import join
import yt_dlp

# Import config for admin notifications
try:
    from config import ADMIN_ID, NOTIFY_ADMIN_ON_ERROR
except ImportError:
    ADMIN_ID = None
    NOTIFY_ADMIN_ON_ERROR = False

# ------------------------------------------------------------------- #
# Logger
logger = get_logger('insta_fetch')

# ------------------------------------------------------------------- #
# Configuration
RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY')
if not RAPIDAPI_KEY:
    logger.warning("[INSTA] RAPIDAPI_KEY not set in environment! Instagram API will not work.")
RAPIDAPI_HOST = "social-download-all-in-one.p.rapidapi.com"
COOKIE_FILE = 'instagram_cookies.txt'

# Timeouts
API_TIMEOUT = 10
YTDLP_TIMEOUT = 15
YTDLP_COOKIE_TIMEOUT = 20

# ------------------------------------------------------------------- #
class InstaFetcher:
    """کلاس اصلی برای دانلود از Instagram"""
    
    def __init__(self):
        self.api_key = RAPIDAPI_KEY
        self.cookie_file = COOKIE_FILE
        self.last_api_call = 0  # برای rate limiting
        self.min_api_interval = 1.0  # حداقل 1 ثانیه بین هر request
        
    async def fetch(self, url: str, user_id: int, message: Message) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        دانلود از Instagram با استراتژی بهینه شده
        
        Returns:
            (success, data, error_message)
        """
        # Log فقط domain و post ID، نه query parameters
        safe_url = url.split('?')[0] if '?' in url else url
        logger.info(f"[INSTA] Starting fetch for user {user_id}: {safe_url}")
        
        # بررسی Story: نیاز به login دارد
        if '/stories/' in url:
            if not os.path.exists(self.cookie_file):
                logger.warning("[INSTA] Story requires login but no cookie file")
                return False, None, "story_needs_login"
            
            # برای Story مستقیماً به yt-dlp با cookie برو
            logger.info("[INSTA] Story detected, using yt-dlp with cookie")
            await message.edit_text(
                "📖 **Instagram Story**\n\n"
                "🔄 در حال دانلود...\n"
                "⏳ لطفاً صبر کنید..."
            )
            success, data, error = await self._try_ytdlp(url, use_cookie=True)
            if success:
                logger.info("[INSTA] Story download SUCCESS")
                return True, data, None
            else:
                logger.error(f"[INSTA] Story download FAILED: {error}")
                return False, None, error or "story_download_failed"
        
        # Layer 1: API
        logger.info("[INSTA] Layer 1: Trying API...")
        success, data, error = await self._try_api(url, message)
        if success:
            logger.info("[INSTA] Layer 1 SUCCESS")
            return True, data, None
        
        logger.warning(f"[INSTA] Layer 1 FAILED: {error}")
        
        # استراتژی بهینه: اگر cookie داریم، اول با cookie امتحان کن
        # چون احتمال موفقیت بیشتره (خصوصاً برای پست‌های محدود)
        
        # Layer 2: yt-dlp با cookie (اگر موجود باشه)
        if os.path.exists(self.cookie_file):
            logger.info("[INSTA] Layer 2: Trying yt-dlp with cookie...")
            await message.edit_text(
                "⏳ API موفق نبود، در حال تلاش با authentication...\n"
                "🔄 لطفاً صبر کنید..."
            )
            
            success, data, error = await self._try_ytdlp(url, use_cookie=True)
            if success:
                logger.info("[INSTA] Layer 2 SUCCESS (with cookie)")
                return True, data, None
            
            logger.warning(f"[INSTA] Layer 2 FAILED: {error}")
        else:
            logger.info("[INSTA] Layer 2 SKIPPED: No cookie file")
        
        # Layer 3: yt-dlp بدون cookie (fallback نهایی)
        logger.info("[INSTA] Layer 3: Trying yt-dlp without cookie (fallback)...")
        await message.edit_text(
            "⏳ در حال تلاش نهایی...\n"
            "🔄 لطفاً صبر کنید..."
        )
        
        success, data, error = await self._try_ytdlp(url, use_cookie=False)
        if success:
            logger.info("[INSTA] Layer 3 SUCCESS (without cookie)")
            return True, data, None
        
        logger.warning(f"[INSTA] Layer 3 FAILED: {error}")
        
        # اگر محتوا محدود سنی بود و cookie نداریم، پیام مناسب بده
        if error == "age_restricted_needs_cookie" and not os.path.exists(self.cookie_file):
            logger.error("[INSTA] Age-restricted content needs cookie but no cookie file")
            return False, None, "age_restricted_needs_cookie"
        
        # همه layer ها fail شدند
        logger.error("[INSTA] All layers FAILED")
        return False, None, error or "تمام روش‌ها ناموفق بودند"
    
    async def _try_api(self, url: str, message: Message) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Layer 1: تلاش با API با retry mechanism"""
        
        # تنظیمات retry
        max_retries = 2  # تعداد کل تلاش‌ها (اولی + 1 retry)
        retry_delay = 3.0  # 3 ثانیه delay بین تلاش‌ها
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Rate limiting: حداقل 1 ثانیه بین هر API call
                now = time.time()
                time_since_last = now - self.last_api_call
                if time_since_last < self.min_api_interval:
                    wait_time = self.min_api_interval - time_since_last
                    logger.debug(f"[INSTA] Rate limiting: waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                
                self.last_api_call = time.time()
                
                # پیام مناسب برای هر تلاش
                if attempt == 0:
                    await message.edit_text(
                        "📡 در حال دریافت اطلاعات از Instagram...\n"
                        "⏳ لطفاً صبر کنید..."
                    )
                else:
                    await message.edit_text(
                        f"📡 تلاش مجدد ({attempt + 1}/{max_retries})...\n"
                        "⏳ لطفاً صبر کنید..."
                    )
                
                # کمی delay برای نمایش پیام
                await asyncio.sleep(0.5)
                
                # ساخت payload
                payload = json.dumps({"url": url})
                
                # ارسال request
                loop = asyncio.get_running_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, self._api_request_sync, payload),
                    timeout=API_TIMEOUT
                )
                
                if not result:
                    last_error = "API response empty"
                    logger.warning(f"[INSTA] API attempt {attempt + 1}/{max_retries} failed: empty response")
                    
                    # اگر تلاش آخر نبود، delay بده و retry کن
                    if attempt < max_retries - 1:
                        logger.info(f"[INSTA] Waiting {retry_delay}s before retry...")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        return False, None, last_error
                
                # Parse response
                data = json.loads(result)
                
                # بررسی خطاها
                if data.get('error'):
                    error_msg = self._parse_api_error(data)
                    last_error = error_msg
                    logger.warning(f"[INSTA] API attempt {attempt + 1}/{max_retries} failed: {error_msg}")
                    
                    # برای برخی خطاها retry نکن (مثل private_account)
                    if error_msg in ["private_account", "not_found"]:
                        logger.info(f"[INSTA] Error '{error_msg}' is not retryable, stopping")
                        return False, None, error_msg
                    
                    # اگر تلاش آخر نبود، delay بده و retry کن
                    if attempt < max_retries - 1:
                        logger.info(f"[INSTA] Waiting {retry_delay}s before retry...")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        return False, None, last_error
                
                # بررسی medias
                medias = data.get('medias', [])
                if not medias:
                    last_error = "No media found"
                    logger.warning(f"[INSTA] API attempt {attempt + 1}/{max_retries} failed: no media")
                    
                    # اگر تلاش آخر نبود، delay بده و retry کن
                    if attempt < max_retries - 1:
                        logger.info(f"[INSTA] Waiting {retry_delay}s before retry...")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        return False, None, last_error
                
                # موفق!
                logger.info(f"[INSTA] API attempt {attempt + 1}/{max_retries} SUCCESS")
                return True, data, None
                
            except asyncio.TimeoutError:
                last_error = "API timeout"
                logger.error(f"[INSTA] API attempt {attempt + 1}/{max_retries} timeout")
                
                # اگر تلاش آخر نبود، delay بده و retry کن
                if attempt < max_retries - 1:
                    logger.info(f"[INSTA] Waiting {retry_delay}s before retry...")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    return False, None, last_error
            
            except Exception as e:
                last_error = str(e)
                logger.error(f"[INSTA] API attempt {attempt + 1}/{max_retries} error: {e}")
                
                # اگر تلاش آخر نبود، delay بده و retry کن
                if attempt < max_retries - 1:
                    logger.info(f"[INSTA] Waiting {retry_delay}s before retry...")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    return False, None, last_error
        
        # اگر از loop خارج شدیم بدون return (نباید اتفاق بیفته)
        return False, None, last_error or "API failed after all retries"
    
    def _api_request_sync(self, payload: str) -> Optional[str]:
        """ارسال request به API (sync)"""
        try:
            conn = http.client.HTTPSConnection(RAPIDAPI_HOST, timeout=API_TIMEOUT)
            
            headers = {
                'x-rapidapi-key': self.api_key,
                'x-rapidapi-host': RAPIDAPI_HOST,
                'Content-Type': 'application/json'
            }
            
            conn.request("POST", "/v1/social/autolink", payload, headers)
            res = conn.getresponse()
            data = res.read()
            
            return data.decode("utf-8")
            
        except Exception as e:
            logger.error(f"[INSTA] API request error: {e}")
            return None
        finally:
            try:
                conn.close()
            except:
                pass
    
    def _parse_api_error(self, data: Dict) -> str:
        """Parse کردن خطای API"""
        try:
            data_str = str(data).lower()
            
            # بررسی پیج خصوصی - چند حالت مختلف
            private_keywords = [
                'private',
                'restricted personal page',
                'please follow the account',
                'consent is obtained',
                'transfer your account cookies'
            ]
            
            if any(keyword in data_str for keyword in private_keywords):
                return "private_account"
            
            # بررسی not found
            if 'not found' in data_str or 'no media' in data_str:
                return "not_found"
            
            # خطای عمومی
            return "api_error"
            
        except:
            return "unknown_error"
    
    async def _try_ytdlp(self, url: str, use_cookie: bool = False) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Layer 2/3: تلاش با yt-dlp"""
        try:
            timeout = YTDLP_COOKIE_TIMEOUT if use_cookie else YTDLP_TIMEOUT
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True,
            }
            
            if use_cookie and os.path.exists(self.cookie_file):
                ydl_opts['cookiefile'] = self.cookie_file
                logger.info(f"[INSTA] Using cookie file: {self.cookie_file}")
            
            # استخراج اطلاعات
            loop = asyncio.get_running_loop()
            
            def _extract():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)
            
            info = await asyncio.wait_for(
                loop.run_in_executor(None, _extract),
                timeout=timeout
            )
            
            if not info:
                return False, None, "yt-dlp returned None"
            
            # تبدیل به فرمت مورد نیاز
            data = self._convert_ytdlp_to_api_format(info, url)
            
            return True, data, None
            
        except asyncio.TimeoutError:
            logger.error("[INSTA] yt-dlp timeout")
            return False, None, "yt-dlp timeout"
        except Exception as e:
            error_str = str(e).lower()
            
            # بررسی خطاهای خاص
            if 'private' in error_str or 'login' in error_str:
                return False, None, "private_account"
            elif 'not found' in error_str or '404' in error_str:
                return False, None, "not_found"
            elif 'inappropriate' in error_str or 'unavailable' in error_str or 'certain audiences' in error_str:
                # محتوای محدود سنی: اگر cookie استفاده نشده، بگو که نیاز به cookie داره
                if not use_cookie:
                    logger.warning("[INSTA] Age-restricted content, needs cookie")
                    return False, None, "age_restricted_needs_cookie"
                else:
                    # اگر با cookie هم fail شد، واقعاً محدوده
                    logger.error("[INSTA] Age-restricted even with cookie")
                    return False, None, "age_restricted"
            else:
                logger.error(f"[INSTA] yt-dlp error: {e}")
                return False, None, str(e)
    
    def _convert_ytdlp_to_api_format(self, info: Dict, url: str) -> Dict:
        """تبدیل خروجی yt-dlp به فرمت API"""
        try:
            # بررسی carousel (چند آیتمی)
            if 'entries' in info and info['entries']:
                # Carousel: همه آیتم‌ها رو بگیر
                medias = []
                for entry in info['entries']:
                    media = self._extract_media_from_item(entry)
                    if media:
                        medias.append(media)
                
                return {
                    'url': url,
                    'source': 'instagram',
                    'title': info.get('title', 'Instagram'),
                    'author': info.get('uploader', 'Unknown'),
                    'thumbnail': info['entries'][0].get('thumbnail', '') if info['entries'] else '',
                    'medias': medias,
                    'type': 'multiple',
                    'error': False
                }
            else:
                # تک آیتم
                media = self._extract_media_from_item(info)
                if not media:
                    raise Exception("No media extracted")
                
                return {
                    'url': url,
                    'source': 'instagram',
                    'title': info.get('title', 'Instagram'),
                    'author': info.get('uploader', 'Unknown'),
                    'thumbnail': info.get('thumbnail', ''),
                    'medias': [media],  # فقط یک آیتم
                    'type': 'single',
                    'error': False
                }
            
        except Exception as e:
            logger.error(f"[INSTA] Convert error: {e}")
            raise
    
    def _extract_media_from_item(self, item: Dict) -> Dict:
        """استخراج اطلاعات media از یک آیتم"""
        try:
            formats = item.get('formats', [])
            
            # اگه format نداره، احتمالاً image-only هست
            if not formats:
                logger.info("[INSTA] No formats found, trying direct URL/thumbnail")
                direct_url = item.get('url') or item.get('thumbnail')
                if direct_url:
                    # تشخیص extension از URL
                    ext = 'jpg'
                    if '.png' in direct_url.lower():
                        ext = 'png'
                    elif '.webp' in direct_url.lower():
                        ext = 'webp'
                    
                    return {
                        'url': direct_url,
                        'thumbnail': item.get('thumbnail', ''),
                        'quality': 'original',
                        'resolution': f"{item.get('width', 0)}x{item.get('height', 0)}",
                        'type': 'image',
                        'extension': ext,
                        'is_audio': False
                    }
                return None
            
            # فیلتر ویدیوها
            video_formats = [
                f for f in formats
                if f.get('vcodec') != 'none' and f.get('height')
            ]
            
            if video_formats:
                # ویدیو
                video_formats.sort(key=lambda x: x.get('height', 0), reverse=True)
                best = video_formats[0]
                return {
                    'url': best.get('url'),
                    'thumbnail': item.get('thumbnail', ''),
                    'quality': f"{best.get('height', 0)}p",
                    'resolution': f"{best.get('width', 0)}x{best.get('height', 0)}",
                    'type': 'video',
                    'extension': best.get('ext', 'mp4'),
                    'is_audio': True
                }
            else:
                # عکس
                direct_url = item.get('url')
                if direct_url:
                    # تشخیص extension درست از URL
                    ext = item.get('ext', 'jpg')
                    if '.png' in direct_url.lower():
                        ext = 'png'
                    elif '.webp' in direct_url.lower():
                        ext = 'webp'
                    elif '.jpeg' in direct_url.lower() or '.jpg' in direct_url.lower():
                        ext = 'jpg'
                    
                    return {
                        'url': direct_url,
                        'thumbnail': item.get('thumbnail', ''),
                        'quality': 'original',
                        'resolution': f"{item.get('width', 0)}x{item.get('height', 0)}",
                        'type': 'image',
                        'extension': ext,
                        'is_audio': False
                    }
            return None
        except Exception as e:
            logger.error(f"[INSTA] Extract media error: {e}")
            return None
    



# ------------------------------------------------------------------- #
# Global instance
insta_fetcher = InstaFetcher()


logger.info("Instagram Fetcher module loaded")



# ------------------------------------------------------------------- #
# Handler
@Client.on_message(
    filters.regex(
        r'(https?://)?(www\.|m\.)?(?:dd)?(instagram\.com|instagr\.am)/(p|reel|tv|stories|igtv)/([a-zA-Z0-9_-]+)(\?[^\s]*)?'
    )
    & filters.private
    & join
)
async def handle_instagram_link(client: Client, message: Message):
    """Handler اصلی برای لینک‌های Instagram"""
    start_time = time.time()
    user_id = message.from_user.id
    url = message.text.strip()
    
    # Log فقط domain و post ID، نه query parameters
    safe_url = url.split('?')[0] if '?' in url else url
    logger.info(f"[INSTA] User {user_id} sent Instagram link: {safe_url}")
    
    # بررسی ثبت‌نام کاربر
    db = DB()
    if not db.check_user_register(user_id):
        logger.info(f"[INSTA] User {user_id} not registered")
        await message.reply_text(
            "⚠️ ابتدا باید ربات را استارت کنید.\n\nلطفاً دستور /start را ارسال کنید.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔄 شروع مجدد", callback_data="start")]]
            )
        )
        return
    
    # ثبت درخواست در دیتابیس
    request_id = db.log_request(
        user_id=user_id,
        platform='instagram',
        url=url,
        status='pending'
    )
    logger.info(f"[INSTA] Request logged with ID: {request_id}")
    
    # پیام اولیه
    status_msg = await message.reply_text(
        "📸 **Instagram Downloader**\n\n"
        "🔄 در حال دریافت اطلاعات...\n"
        "⏳ لطفاً صبر کنید..."
    )
    
    try:
        # تلاش برای دانلود
        success, data, error = await insta_fetcher.fetch(url, user_id, status_msg)
        
        if not success:
            # مدیریت خطاها
            processing_time = time.time() - start_time
            db.update_request_status(
                request_id=request_id,
                status='failed',
                processing_time=processing_time,
                error_message=error
            )
            
            # ارسال notification به ادمین
            await _notify_admin_on_error(client, user_id, url, error)
            
            # پیام خطا به کاربر
            error_text = _get_error_message(error)
            await status_msg.edit_text(error_text, parse_mode=ParseMode.MARKDOWN)
            return
        
        # موفق! آماده‌سازی برای ارسال
        await status_msg.edit_text(
            "✅ اطلاعات دریافت شد!\n"
            "📥 در حال دانلود و ارسال...\n"
            "⏳ لطفاً صبر کنید..."
        )
        
        # دانلود و ارسال
        await _download_and_send(client, message, status_msg, data, db, request_id, start_time, insta_fetcher)
        
    except Exception as e:
        logger.error(f"[INSTA] Handler error: {e}")
        
        processing_time = time.time() - start_time
        db.update_request_status(
            request_id=request_id,
            status='failed',
            processing_time=processing_time,
            error_message=str(e)[:500]
        )
        
        await status_msg.edit_text(
            "❌ **خطای غیرمنتظره**\n\n"
            "متأسفانه مشکلی پیش آمد.\n"
            "لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید.",
            parse_mode=ParseMode.MARKDOWN
        )


async def _notify_admin_on_error(client: Client, user_id: int, url: str, error: str):
    """ارسال notification به ادمین در صورت خطا"""
    if not ADMIN_ID or not NOTIFY_ADMIN_ON_ERROR:
        return
    
    try:
        # ساخت پیام برای ادمین
        admin_message = (
            "🚨 **خطای Instagram**\n\n"
            f"👤 **کاربر:** `{user_id}`\n"
            f"🔗 **URL:** `{url[:50]}...`\n"
            f"⚠️ **خطا:** `{error[:100]}`\n\n"
            f"🕐 **زمان:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        await client.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"[INSTA] Admin notified about error for user {user_id}")
    except Exception as e:
        logger.error(f"[INSTA] Failed to notify admin: {e}")


def _get_error_message(error: str) -> str:
    """تبدیل کد خطا به پیام فارسی"""
    
    if error == "private_account":
        return (
            "🔒 **پیج خصوصی**\n\n"
            "این پیج خصوصی است و امکان دانلود وجود ندارد.\n\n"
            "💡 **راه‌حل:**\n"
            "• پیج را عمومی کنید\n"
            "• یا از لینک پست عمومی استفاده کنید"
        )
    
    elif error == "not_found":
        return (
            "❌ **پست پیدا نشد**\n\n"
            "لینک اشتباه است یا پست حذف شده.\n\n"
            "💡 **راه‌حل:**\n"
            "• لینک را بررسی کنید\n"
            "• مطمئن شوید پست هنوز موجود است\n"
            "• لینک کامل را ارسال کنید"
        )
    
    elif error == "story_needs_login":
        return (
            "📖 **Story نیاز به ورود دارد**\n\n"
            "برای دانلود Story باید وارد حساب شوید.\n\n"
            "💡 **راه‌حل:**\n"
            "• از پست‌های عادی استفاده کنید\n"
            "• یا منتظر بمانید تا cookie تنظیم شود"
        )
    
    elif error == "story_download_failed":
        return (
            "📖 **خطا در دانلود Story**\n\n"
            "متأسفانه نتوانستیم Story را دانلود کنیم.\n\n"
            "💡 **دلایل احتمالی:**\n"
            "• Story منقضی شده (24 ساعت)\n"
            "• Story حذف شده\n"
            "• مشکل در authentication"
        )
    
    elif "timeout" in error.lower():
        return (
            "⏱️ **زمان انتظار تمام شد**\n\n"
            "سرور Instagram پاسخ نداد.\n\n"
            "💡 **راه‌حل:**\n"
            "• چند لحظه صبر کنید\n"
            "• دوباره تلاش کنید"
        )
    
    elif error == "age_restricted_needs_cookie":
        return (
            "🔞 **محتوای محدود سنی**\n\n"
            "این پست محدود سنی است و نیاز به ورود دارد.\n\n"
            "💡 **راه‌حل:**\n"
            "• Cookie فایل Instagram را تنظیم کنید\n"
            "• سپس دوباره تلاش کنید\n\n"
            "ℹ️ با cookie می‌توانید این محتوا را دانلود کنید."
        )
    
    elif error == "age_restricted":
        return (
            "🔞 **محتوای محدود**\n\n"
            "این پست محدود شده و حتی با cookie قابل دسترسی نیست.\n\n"
            "💡 **دلایل احتمالی:**\n"
            "• محتوا برای سن شما مناسب نیست\n"
            "• Cookie منقضی شده است\n"
            "• محدودیت منطقه‌ای"
        )
    
    else:
        return (
            "❌ **خطا در دانلود**\n\n"
            "متأسفانه نتوانستیم این پست را دانلود کنیم.\n\n"
            "💡 **راه‌حل:**\n"
            "• لینک را بررسی کنید\n"
            "• دوباره تلاش کنید\n"
            "• از لینک دیگری استفاده کنید"
        )


async def _download_and_send(
    client: Client,
    message: Message,
    status_msg: Message,
    data: Dict,
    db: DB,
    request_id: int,
    start_time: float,
    fetcher: 'InstaFetcher' = None
):
    """دانلود و ارسال فایل"""
    try:
        # اگر fetcher پاس نشده، از global instance استفاده کن
        if fetcher is None:
            fetcher = insta_fetcher
        
        # ذخیره URL اصلی برای استفاده در fallback
        original_url = message.text.strip()
        
        medias = data.get('medias', [])
        if not medias:
            raise Exception("No media in data")
        
        # بررسی تعداد medias واقعی (بدون audio)
        # audio جزء ویدیو حساب میشه، نه media جداگانه
        visual_medias = [m for m in medias if m.get('type') in ['image', 'video']]
        total_medias = len(visual_medias)
        post_type = data.get('type', 'single')
        
        # Logging دقیق برای debug
        logger.info(f"[INSTA] Data structure: type={post_type}, total_medias={len(medias)}, visual_medias={total_medias}")
        logger.debug(f"[INSTA] Media types: {[m.get('type') for m in medias]}")
        logger.info(f"[INSTA] Total visual medias: {total_medias}, Type: {post_type}")
        
        # اگه چند تایی هست، پیام بده
        if total_medias > 1:
            await status_msg.edit_text(
                f"📸 **Instagram Gallery**\n\n"
                f"🖼️ {total_medias} عکس/ویدیو پیدا شد\n"
                f"⏳ در حال دانلود و ارسال...\n\n"
                f"لطفاً صبر کنید..."
            )
        else:
            await status_msg.edit_text(
                f"📸 **Instagram**\n\n"
                f"⏳ در حال دانلود...\n\n"
                f"لطفاً صبر کنید..."
            )
        
        # دانلود همه medias با yt-dlp
        import tempfile
        import aiohttp
        from pyrogram.types import InputMediaPhoto, InputMediaVideo
        
        downloaded_files = []
        
        # دانلود هر media (فقط image و video، نه audio)
        for idx, media in enumerate(visual_medias, 1):
            try:
                download_url = media.get('url')
                if not download_url:
                    logger.warning(f"[INSTA] No URL for media {idx}")
                    continue
                
                media_type = media.get('type', 'video')
                file_ext = media.get('extension', 'mp4' if media_type == 'video' else 'jpg')
                
                # Logging دقیق برای هر media
                logger.info(f"[INSTA] Downloading {idx}/{total_medias}: type={media_type}, ext={file_ext}, url_len={len(download_url)}")
                
                # Headers
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://www.instagram.com/',
                }
                
                # Cookies - استفاده از http.cookiejar برای parse درست
                cookies = {}
                if os.path.exists(COOKIE_FILE):
                    try:
                        import http.cookiejar
                        cookie_jar = http.cookiejar.MozillaCookieJar(COOKIE_FILE)
                        cookie_jar.load(ignore_discard=True, ignore_expires=True)
                        
                        # تبدیل به dict برای aiohttp
                        for cookie in cookie_jar:
                            if 'instagram.com' in cookie.domain:
                                cookies[cookie.name] = cookie.value
                        
                        logger.info(f"[INSTA] Loaded {len(cookies)} cookies from file")
                    except Exception as e:
                        logger.warning(f"[INSTA] Failed to load cookies: {e}")
                        # Fallback به روش قدیمی
                        try:
                            with open(COOKIE_FILE, 'r') as f:
                                for line in f:
                                    if line.startswith('#') or not line.strip():
                                        continue
                                    parts = line.strip().split('\t')
                                    if len(parts) >= 7:
                                        cookies[parts[5]] = parts[6]
                        except:
                            pass
                
                # دانلود با retry برای 403 و chunk-based برای فایل‌های بزرگ
                max_retries = 3
                download_success = False
                
                for retry in range(max_retries):
                    try:
                        # Timeout پویا: ابتدا HEAD request برای گرفتن سایز
                        timeout_seconds = 60  # default
                        try:
                            async with aiohttp.ClientSession() as head_session:
                                async with head_session.head(download_url, headers=headers, cookies=cookies, timeout=aiohttp.ClientTimeout(total=5)) as head_resp:
                                    content_length = head_resp.headers.get('Content-Length')
                                    if content_length:
                                        file_size_mb = int(content_length) / (1024 * 1024)
                                        # 2 ثانیه به ازای هر MB + 30 ثانیه base
                                        timeout_seconds = max(60, int(file_size_mb * 2) + 30)
                                        logger.info(f"[INSTA] Media {idx} size: {file_size_mb:.1f}MB, timeout: {timeout_seconds}s")
                        except Exception as head_error:
                            logger.debug(f"[INSTA] HEAD request failed, using default timeout: {head_error}")
                            timeout_seconds = 120  # fallback برای حالتی که HEAD fail بشه
                        
                        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
                        async with aiohttp.ClientSession(timeout=timeout) as session:
                            async with session.get(download_url, headers=headers, cookies=cookies) as resp:
                                if resp.status == 200:
                                    # دانلود chunk-based برای جلوگیری از OOM
                                    with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as tmp_file:
                                        chunk_size = 1024 * 1024  # 1MB chunks
                                        async for chunk in resp.content.iter_chunked(chunk_size):
                                            tmp_file.write(chunk)
                                        
                                        downloaded_files.append({
                                            'path': tmp_file.name,
                                            'type': media_type
                                        })
                                        logger.info(f"[INSTA] Downloaded media {idx}/{total_medias} ({os.path.getsize(tmp_file.name) / 1024 / 1024:.1f}MB)")
                                        download_success = True
                                        break
                                elif resp.status == 403 and retry < max_retries - 1:
                                    # 403: URL منقضی شده، دوباره fetch کن
                                    logger.error(f"[INSTA] 403 Details: media={idx}, retry={retry+1}/{max_retries}, has_cookies={bool(cookies)}, url_starts={download_url[:50]}")
                                    logger.warning(f"[INSTA] 403 on media {idx}, retry {retry+1}/{max_retries}")
                                    await asyncio.sleep(1.5 * (retry + 1))
                                    
                                    # دوباره fetch کن برای URL تازه
                                    success_refetch, data_refetch, _ = await fetcher.fetch(message.text.strip(), message.from_user.id, status_msg)
                                    if success_refetch and data_refetch:
                                        # فقط visual medias رو بگیر (مثل اول)
                                        medias_refetch = data_refetch.get('medias', [])
                                        visual_medias_refetch = [m for m in medias_refetch if m.get('type') in ['image', 'video']]
                                        if idx <= len(visual_medias_refetch):
                                            download_url = visual_medias_refetch[idx-1].get('url')
                                            logger.info(f"[INSTA] Got fresh URL for media {idx}")
                                else:
                                    logger.warning(f"[INSTA] Download failed {idx}: {resp.status}")
                                    break
                    except Exception as e:
                        logger.error(f"[INSTA] Download error media {idx}, retry {retry+1}: {e}")
                        if retry < max_retries - 1:
                            await asyncio.sleep(1.0 * (retry + 1))
                
                if not download_success:
                    logger.warning(f"[INSTA] Failed to download media {idx} after {max_retries} retries")
                            
            except Exception as e:
                logger.error(f"[INSTA] Error downloading media {idx}: {e}")
                continue
        
        if not downloaded_files:
            # اگر هیچ فایلی دانلود نشد، سعی کن با yt-dlp مستقیم دانلود کنی
            logger.warning("[INSTA] No files downloaded via API, trying yt-dlp direct download")
            
            # Initialize temp_dir برای جلوگیری از NameError در exception handlers
            temp_dir = None
            
            try:
                import yt_dlp
                import glob
                import uuid
                
                # استفاده از UUID برای جلوگیری از conflict
                unique_id = uuid.uuid4().hex[:8]
                temp_dir = f'temp_insta_{unique_id}'
                os.makedirs(temp_dir, exist_ok=True)
                
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'),
                }
                
                if os.path.exists(COOKIE_FILE):
                    ydl_opts['cookiefile'] = COOKIE_FILE
                
                # اجرای async برای جلوگیری از blocking
                def _ytdlp_download():
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        return ydl.extract_info(original_url, download=True)
                
                loop = asyncio.get_event_loop()
                info = await asyncio.wait_for(
                    loop.run_in_executor(None, _ytdlp_download),
                    timeout=30
                )
                
                if info:
                    # پیدا کردن فایل‌های دانلود شده
                    files = glob.glob(os.path.join(temp_dir, '*.*'))
                    if files:
                        for f in files:
                            ext = f.split('.')[-1].lower()
                            media_type = 'video' if ext in ['mp4', 'mov', 'avi', 'mkv', 'webm'] else 'image'
                            downloaded_files.append({
                                'path': f,
                                'type': media_type
                            })
                        logger.info(f"[INSTA] yt-dlp downloaded {len(files)} files")
                    else:
                        # پاک کردن دایرکتوری خالی
                        try:
                            os.rmdir(temp_dir)
                        except:
                            pass
            except asyncio.TimeoutError:
                logger.error("[INSTA] yt-dlp download timeout")
                # پاک کردن فایل‌های ناقص (فقط اگر temp_dir ساخته شده باشه)
                if temp_dir:
                    try:
                        import shutil
                        if os.path.exists(temp_dir):
                            shutil.rmtree(temp_dir)
                    except:
                        pass
            except Exception as e:
                logger.error(f"[INSTA] yt-dlp direct download failed: {e}")
                # پاک کردن فایل‌های ناقص (فقط اگر temp_dir ساخته شده باشه)
                if temp_dir:
                    try:
                        import shutil
                        if os.path.exists(temp_dir):
                            shutil.rmtree(temp_dir)
                    except:
                        pass
            
            if not downloaded_files:
                raise Exception("No files downloaded")
        

        
        # ارسال به صورت Media Group (آلبوم)
        if not downloaded_files:
            raise Exception("No media downloaded")
        
        # ساخت caption مناسب
        if len(downloaded_files) > 1:
            caption = (
                f"📸 **Instagram Gallery**\n\n"
                f"�e {data.get('author', 'Unknown')}\n"
                f"🖼️ {len(downloaded_files)} عکس/ویدیو\n\n"
                f"✅ دانلود شده توسط @DirectTubeBot"
            )
        else:
            caption = (
                f"📸 **Instagram**\n\n"
                f"👤 {data.get('author', 'Unknown')}\n\n"
                f"✅ دانلود شده توسط @DirectTubeBot"
            )
        
        try:
            # اگه فقط یک فایل هست، معمولی بفرست
            if len(downloaded_files) == 1:
                file_info = downloaded_files[0]
                if file_info['type'] == 'video':
                    await message.reply_video(
                        video=file_info['path'],
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    # برای عکس: تبدیل به JPG اگر فرمت مشکل داره یا سایز بزرگه
                    photo_path = file_info['path']
                    try:
                        await message.reply_photo(
                            photo=photo_path,
                            caption=caption,
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except Exception as photo_error:
                        error_str = str(photo_error)
                        if 'PHOTO_EXT_INVALID' in error_str or 'PHOTO_INVALID_DIMENSIONS' in error_str or 'FILE_PARTS_INVALID' in error_str:
                            logger.warning(f"[INSTA] Photo error: {error_str}, converting/resizing")
                            # تبدیل و resize اگر لازم باشه
                            from PIL import Image
                            img = Image.open(photo_path)
                            
                            # تبدیل mode اگر لازم باشه
                            if img.mode in ('RGBA', 'LA', 'P'):
                                img = img.convert('RGB')
                            
                            # بررسی سایز (تلگرام: حداکثر 10MB برای photo)
                            file_size = os.path.getsize(photo_path)
                            max_dimension = 2560  # تلگرام: حداکثر 2560px
                            
                            # Resize اگر خیلی بزرگه
                            if img.width > max_dimension or img.height > max_dimension or file_size > 9 * 1024 * 1024:
                                logger.info(f"[INSTA] Resizing image: {img.width}x{img.height} ({file_size/1024/1024:.1f}MB)")
                                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                            
                            jpg_path = photo_path.rsplit('.', 1)[0] + '_converted.jpg'
                            
                            # تنظیم quality بر اساس سایز
                            quality = 95
                            if file_size > 5 * 1024 * 1024:
                                quality = 85
                            
                            img.save(jpg_path, 'JPEG', quality=quality, optimize=True)
                            logger.info(f"[INSTA] Converted to JPG: {os.path.getsize(jpg_path)/1024/1024:.1f}MB")
                            
                            # ارسال JPG
                            await message.reply_photo(
                                photo=jpg_path,
                                caption=caption,
                                parse_mode=ParseMode.MARKDOWN
                            )
                            
                            # حذف فایل JPG موقت
                            try:
                                os.unlink(jpg_path)
                            except:
                                pass
                        else:
                            raise
                sent_count = 1
            
            # اگه چند تا هست، به صورت Media Group بفرست
            else:
                media_group = []
                converted_files = []  # برای track کردن فایل‌های تبدیل شده
                
                for idx, file_info in enumerate(downloaded_files):
                    # فقط اولین عکس caption داره
                    file_caption = caption if idx == 0 else ""
                    
                    if file_info['type'] == 'video':
                        media_group.append(
                            InputMediaVideo(
                                media=file_info['path'],
                                caption=file_caption,
                                parse_mode=ParseMode.MARKDOWN
                            )
                        )
                    else:
                        # برای عکس: بررسی و تبدیل فرمت اگر لازم باشه
                        photo_path = file_info['path']
                        
                        # اگر فرمت WebP یا PNG با transparency هست، تبدیل کن
                        needs_conversion = photo_path.lower().endswith(('.webp', '.png'))
                        file_size = os.path.getsize(photo_path)
                        
                        # یا اگر سایز بزرگه (>9MB)
                        if needs_conversion or file_size > 9 * 1024 * 1024:
                            try:
                                from PIL import Image
                                img = Image.open(photo_path)
                                
                                # تبدیل mode اگر لازم باشه
                                if img.mode in ('RGBA', 'LA', 'P'):
                                    img = img.convert('RGB')
                                
                                # Resize اگر خیلی بزرگه
                                max_dimension = 2560
                                if img.width > max_dimension or img.height > max_dimension or file_size > 9 * 1024 * 1024:
                                    img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                                
                                jpg_path = photo_path.rsplit('.', 1)[0] + '_converted.jpg'
                                
                                # تنظیم quality
                                quality = 85 if file_size > 5 * 1024 * 1024 else 95
                                img.save(jpg_path, 'JPEG', quality=quality, optimize=True)
                                
                                photo_path = jpg_path
                                converted_files.append(jpg_path)
                                logger.info(f"[INSTA] Converted {file_info['path']} to JPG ({os.path.getsize(jpg_path)/1024/1024:.1f}MB)")
                            except Exception as e:
                                logger.warning(f"[INSTA] Failed to convert image: {e}")
                        
                        media_group.append(
                            InputMediaPhoto(
                                media=photo_path,
                                caption=file_caption,
                                parse_mode=ParseMode.MARKDOWN
                            )
                        )
                
                # ارسال Media Group (حداکثر 10 تا)
                try:
                    await message.reply_media_group(media=media_group[:10])
                    sent_count = len(media_group[:10])
                except Exception as e:
                    logger.error(f"[INSTA] Media group send failed: {e}")
                    # حذف فایل‌های تبدیل شده
                    for cf in converted_files:
                        try:
                            os.unlink(cf)
                        except:
                            pass
                    raise
                
                # حذف فایل‌های تبدیل شده بعد از ارسال موفق
                for cf in converted_files:
                    try:
                        os.unlink(cf)
                    except:
                        pass
            
            logger.info(f"[INSTA] Sent {sent_count} medias as group")
            
        except Exception as e:
            logger.error(f"[INSTA] Failed to send media group: {e}")
            raise
        
        # حذف پیام وضعیت
        try:
            await status_msg.delete()
        except:
            pass
        
        # به‌روزرسانی دیتابیس
        processing_time = time.time() - start_time
        db.update_request_status(
            request_id=request_id,
            status='success',
            processing_time=processing_time
        )
        logger.info(f"[INSTA] Success! Sent {sent_count}/{len(downloaded_files)} medias in {processing_time:.2f}s")
        
    except Exception as e:
        logger.error(f"[INSTA] Download/Send error: {e}")
        raise
    
    finally:
        # کمی صبر کن تا upload کامل بشه (جلوگیری از race condition)
        await asyncio.sleep(1.5)
        
        # Cleanup: حذف فایل‌های موقت در هر صورت
        for file_info in downloaded_files:
            try:
                if os.path.exists(file_info['path']):
                    os.unlink(file_info['path'])
                    logger.debug(f"[INSTA] Cleaned up: {file_info['path']}")
            except Exception as cleanup_error:
                logger.warning(f"[INSTA] Cleanup failed for {file_info['path']}: {cleanup_error}")
        
        # حذف دایرکتوری‌های موقت yt-dlp
        try:
            import glob
            temp_dirs = glob.glob('temp_insta_*')
            for temp_dir in temp_dirs:
                if os.path.isdir(temp_dir):
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    logger.debug(f"[INSTA] Cleaned up temp dir: {temp_dir}")
        except:
            pass
