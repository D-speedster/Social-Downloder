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
RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY', 'd51a95d960mshb5f65a8e122bb7fp11b675jsn63ff66cbc6cf')
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
        
    async def fetch(self, url: str, user_id: int, message: Message) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        دانلود از Instagram با استراتژی 3 لایه
        
        Returns:
            (success, data, error_message)
        """
        logger.info(f"[INSTA] Starting fetch for user {user_id}: {url}")
        
        # Layer 1: API
        logger.info("[INSTA] Layer 1: Trying API...")
        success, data, error = await self._try_api(url, message)
        if success:
            logger.info("[INSTA] Layer 1 SUCCESS")
            return True, data, None
        
        logger.warning(f"[INSTA] Layer 1 FAILED: {error}")
        
        # Layer 2: yt-dlp (بدون cookie)
        logger.info("[INSTA] Layer 2: Trying yt-dlp...")
        await message.edit_text(
            "⏳ API موفق نبود، در حال تلاش با روش دیگر...\n"
            "🔄 لطفاً صبر کنید..."
        )
        
        success, data, error = await self._try_ytdlp(url, use_cookie=False)
        if success:
            logger.info("[INSTA] Layer 2 SUCCESS")
            return True, data, None
        
        logger.warning(f"[INSTA] Layer 2 FAILED: {error}")
        
        # Layer 3: yt-dlp + cookie
        if os.path.exists(self.cookie_file):
            logger.info("[INSTA] Layer 3: Trying yt-dlp with cookie...")
            await message.edit_text(
                "⏳ در حال تلاش با authentication...\n"
                "🔄 این ممکن است کمی طول بکشد..."
            )
            
            success, data, error = await self._try_ytdlp(url, use_cookie=True)
            if success:
                logger.info("[INSTA] Layer 3 SUCCESS")
                return True, data, None
            
            logger.warning(f"[INSTA] Layer 3 FAILED: {error}")
        else:
            logger.warning("[INSTA] Layer 3 SKIPPED: No cookie file")
        
        # همه layer ها fail شدند
        logger.error("[INSTA] All layers FAILED")
        return False, None, error or "تمام روش‌ها ناموفق بودند"
    
    async def _try_api(self, url: str, message: Message) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Layer 1: تلاش با API"""
        try:
            await message.edit_text(
                "📡 در حال دریافت اطلاعات از Instagram...\n"
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
                return False, None, "API response empty"
            
            # Parse response
            data = json.loads(result)
            
            # بررسی خطاها
            if data.get('error'):
                error_msg = self._parse_api_error(data)
                return False, None, error_msg
            
            # بررسی medias
            medias = data.get('medias', [])
            if not medias:
                return False, None, "No media found"
            
            # موفق!
            return True, data, None
            
        except asyncio.TimeoutError:
            logger.error("[INSTA] API timeout")
            return False, None, "API timeout"
        except Exception as e:
            logger.error(f"[INSTA] API error: {e}")
            return False, None, str(e)
    
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
            else:
                logger.error(f"[INSTA] yt-dlp error: {e}")
                return False, None, str(e)
    
    def _convert_ytdlp_to_api_format(self, info: Dict, url: str) -> Dict:
        """تبدیل خروجی yt-dlp به فرمت API"""
        try:
            # بررسی carousel (چند آیتمی)
            if 'entries' in info and info['entries']:
                # Carousel: فقط اولین آیتم رو بگیر
                first_entry = info['entries'][0]
                return self._convert_single_item(first_entry, url, info)
            else:
                # تک آیتم
                return self._convert_single_item(info, url, info)
            
        except Exception as e:
            logger.error(f"[INSTA] Convert error: {e}")
            raise
    
    def _convert_single_item(self, item: Dict, url: str, parent_info: Dict) -> Dict:
        """تبدیل یک آیتم به فرمت API"""
        try:
            formats = item.get('formats', [])
            
            # فیلتر ویدیوها
            video_formats = [
                f for f in formats
                if f.get('vcodec') != 'none' and f.get('height')
            ]
            
            # اگر ویدیو پیدا شد
            if video_formats:
                # مرتب‌سازی بر اساس کیفیت
                video_formats.sort(key=lambda x: x.get('height', 0), reverse=True)
                best_video = video_formats[0]
                
                data = {
                    'url': url,
                    'source': 'instagram',
                    'title': parent_info.get('title', 'Instagram'),
                    'author': parent_info.get('uploader', 'Unknown'),
                    'thumbnail': item.get('thumbnail', ''),
                    'medias': [{
                        'url': best_video.get('url'),
                        'thumbnail': item.get('thumbnail', ''),
                        'quality': f"{best_video.get('height', 0)}p",
                        'resolution': f"{best_video.get('width', 0)}x{best_video.get('height', 0)}",
                        'type': 'video',
                        'extension': best_video.get('ext', 'mp4'),
                        'is_audio': True
                    }],
                    'type': 'single',
                    'error': False
                }
                return data
            
            # اگر ویدیو نبود، عکس رو بگیر
            else:
                # بررسی URL مستقیم (برای عکس)
                direct_url = item.get('url')
                thumbnail = item.get('thumbnail', '')
                
                if not direct_url:
                    raise Exception("No video or image URL found")
                
                data = {
                    'url': url,
                    'source': 'instagram',
                    'title': parent_info.get('title', 'Instagram'),
                    'author': parent_info.get('uploader', 'Unknown'),
                    'thumbnail': thumbnail,
                    'medias': [{
                        'url': direct_url,
                        'thumbnail': thumbnail,
                        'quality': 'original',
                        'resolution': f"{item.get('width', 0)}x{item.get('height', 0)}",
                        'type': 'image',
                        'extension': item.get('ext', 'jpg'),
                        'is_audio': False
                    }],
                    'type': 'single',
                    'error': False
                }
                return data
                
        except Exception as e:
            logger.error(f"[INSTA] Convert single item error: {e}")
            raise


# ------------------------------------------------------------------- #
# Global instance
insta_fetcher = InstaFetcher()


logger.info("Instagram Fetcher module loaded")



# ------------------------------------------------------------------- #
# Handler
@Client.on_message(
    filters.regex(
        r'(https?://)?(www\.)?(instagram\.com|instagr\.am)/(p|reel|tv)/([a-zA-Z0-9_-]+)'
    )
    & filters.private
    & join
)
async def handle_instagram_link(client: Client, message: Message):
    """Handler اصلی برای لینک‌های Instagram"""
    start_time = time.time()
    user_id = message.from_user.id
    url = message.text.strip()
    
    logger.info(f"[INSTA] User {user_id} sent Instagram link: {url}")
    
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
        await _download_and_send(client, message, status_msg, data, db, request_id, start_time)
        
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
    
    elif "timeout" in error.lower():
        return (
            "⏱️ **زمان انتظار تمام شد**\n\n"
            "سرور Instagram پاسخ نداد.\n\n"
            "💡 **راه‌حل:**\n"
            "• چند لحظه صبر کنید\n"
            "• دوباره تلاش کنید"
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
    start_time: float
):
    """دانلود و ارسال فایل"""
    try:
        medias = data.get('medias', [])
        if not medias:
            raise Exception("No media in data")
        
        # بررسی تعداد medias
        total_medias = len(medias)
        post_type = data.get('type', 'single')
        
        # اگه چند تایی هست، پیام بده
        if total_medias > 1:
            await status_msg.edit_text(
                f"📸 **Instagram Gallery**\n\n"
                f"🖼️ {total_medias} عکس/ویدیو پیدا شد\n"
                f"⏳ در حال دانلود و ارسال...\n\n"
                f"لطفاً صبر کنید..."
            )
        
        # دانلود همه medias
        import aiohttp
        import tempfile
        from pyrogram.types import InputMediaPhoto, InputMediaVideo
        
        downloaded_files = []
        
        for idx, media in enumerate(medias, 1):
            try:
                download_url = media.get('url')
                
                if not download_url:
                    logger.warning(f"[INSTA] No URL for media {idx}/{total_medias}")
                    continue
                
                media_type = media.get('type', 'video')
                file_ext = media.get('extension', 'mp4' if media_type == 'video' else 'jpg')
        
                # Headers برای جلوگیری از 403
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://www.instagram.com/',
                    'Accept': '*/*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                }
                
                # خواندن cookies از فایل
                cookies = {}
                if os.path.exists(COOKIE_FILE):
                    try:
                        with open(COOKIE_FILE, 'r') as f:
                            for line in f:
                                if line.startswith('#') or not line.strip():
                                    continue
                                parts = line.strip().split('\t')
                                if len(parts) >= 7:
                                    cookies[parts[5]] = parts[6]
                    except Exception as e:
                        logger.warning(f"[INSTA] Failed to read cookies: {e}")
                
                # Retry logic برای مقابله با مشکلات شبکه
                max_retries = 2  # کاهش retry برای gallery
                retry_delay = 1
                
                file_path = None
                for attempt in range(max_retries):
                    try:
                        timeout = aiohttp.ClientTimeout(total=30)
                        async with aiohttp.ClientSession(timeout=timeout) as session:
                            async with session.get(download_url, headers=headers, cookies=cookies) as resp:
                                if resp.status == 200:
                                    # موفق!
                                    with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as tmp_file:
                                        tmp_file.write(await resp.read())
                                        file_path = tmp_file.name
                                    break
                                elif resp.status == 403 and attempt < max_retries - 1:
                                    await asyncio.sleep(retry_delay)
                                    continue
                                else:
                                    logger.warning(f"[INSTA] Download failed for media {idx}: {resp.status}")
                                    break
                                    
                    except Exception as e:
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            logger.warning(f"[INSTA] Error downloading media {idx}: {e}")
                            break
                
                if not file_path:
                    logger.warning(f"[INSTA] Skipping media {idx}/{total_medias}")
                    continue
                
                # اضافه کردن به لیست فایل‌های دانلود شده
                downloaded_files.append({
                    'path': file_path,
                    'type': media_type,
                    'idx': idx
                })
                
                logger.info(f"[INSTA] Downloaded media {idx}/{total_medias}")
                    
            except Exception as e:
                logger.error(f"[INSTA] Error processing media {idx}: {e}")
                continue
        
        # ارسال به صورت Media Group (آلبوم)
        if not downloaded_files:
            raise Exception("No media downloaded")
        
        # ساخت caption برای اولین عکس
        caption = (
            f"📸 **Instagram Gallery**\n\n"
            f"👤 {data.get('author', 'Unknown')}\n"
            f"🖼️ {len(downloaded_files)} عکس/ویدیو\n\n"
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
                    await message.reply_photo(
                        photo=file_info['path'],
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN
                    )
                sent_count = 1
            
            # اگه چند تا هست، به صورت Media Group بفرست
            else:
                media_group = []
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
                        media_group.append(
                            InputMediaPhoto(
                                media=file_info['path'],
                                caption=file_caption,
                                parse_mode=ParseMode.MARKDOWN
                            )
                        )
                
                # ارسال Media Group (حداکثر 10 تا)
                await message.reply_media_group(media=media_group[:10])
                sent_count = len(media_group[:10])
            
            logger.info(f"[INSTA] Sent {sent_count} medias as group")
            
        except Exception as e:
            logger.error(f"[INSTA] Failed to send media group: {e}")
            raise
        
        finally:
            # حذف فایل‌های موقت
            for file_info in downloaded_files:
                try:
                    os.unlink(file_info['path'])
                except:
                    pass
        
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
