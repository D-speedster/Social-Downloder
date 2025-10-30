import asyncio
import http.client
import json
import os
import re
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from plugins.start import (
    SPOTIFY_REGEX, TIKTOK_REGEX, SOUNDCLOUD_REGEX,
    PINTEREST_REGEX, TWITTER_REGEX, THREADS_REGEX, FACEBOOK_REGEX,
    REDDIT_REGEX, IMGUR_REGEX, SNAPCHAT_REGEX, TUMBLR_REGEX,
    RUMBLE_REGEX, IFUNNY_REGEX, DEEZER_REGEX, RADIOJAVAN_REGEX,
    INSTA_REGEX,
)
from plugins.media_utils import send_advertisement, download_file_simple, download_stream_to_file
from plugins.stream_utils import download_to_memory_stream, smart_upload_strategy, optimize_chunk_size
from plugins.db_wrapper import DB
from plugins import constant
from plugins.caption_builder import build_caption
from datetime import datetime as _dt
import logging
import requests
import time
from PIL import Image
import subprocess
from config import BOT_TOKEN, RAPIDAPI_KEY
from plugins.concurrency import acquire_slot, release_slot, get_queue_stats, reserve_user, release_user, get_user_active

# Configure Universal Downloader logger
os.makedirs('./logs', exist_ok=True)
universal_logger = logging.getLogger('universal_downloader')
universal_logger.setLevel(logging.DEBUG)

universal_handler = logging.FileHandler('./logs/universal_downloader.log', encoding='utf-8')
universal_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
universal_handler.setFormatter(universal_formatter)
universal_logger.addHandler(universal_handler)

# Use the same database system as Instagram handler
txt = constant.TEXT

# Simple helper to log to file and console
def _log(msg: str):
    try:
        universal_logger.debug(msg)
    except Exception:
        pass
    try:
        print(msg)
    except Exception:
        pass

def get_user_friendly_error_message(api_response, platform):
    """Convert API error responses to user-friendly Persian messages"""
    try:
        # If it's a string error message
        if isinstance(api_response, str):
            error_lower = api_response.lower()
            
            # 403 Forbidden
            if "403" in error_lower or "forbidden" in error_lower:
                return (
                    "🔒 **دسترسی به محتوا محدود شده**\n\n"
                    "💡 **احتمالات:**\n"
                    "• پست خصوصی است (نیاز به فالو)\n"
                    "• محدودیت موقت API\n"
                    "• IP شما موقتاً مسدود شده\n\n"
                    "🔄 **راه‌حل:**\n"
                    "• چند دقیقه صبر کنید\n"
                    "• دوباره تلاش کنید\n"
                    "• اگر پست خصوصی است، ابتدا فالو کنید"
                )
            
            # 429 Rate Limit
            elif "429" in error_lower or "rate limit" in error_lower or "too many" in error_lower:
                return (
                    "⏰ **محدودیت تعداد درخواست**\n\n"
                    "تعداد درخواست‌ها از حد مجاز گذشته.\n\n"
                    "🔄 لطفاً 5-10 دقیقه صبر کنید و دوباره تلاش کنید."
                )
            
            # 404 Not Found
            elif "404" in error_lower or "not found" in error_lower:
                return (
                    "🔍 **محتوا یافت نشد**\n\n"
                    "💡 **احتمالات:**\n"
                    "• لینک اشتباه است\n"
                    "• پست حذف شده\n"
                    "• لینک منقضی شده\n\n"
                    "🔄 لینک را بررسی کنید"
                )
            
            # Server errors (502, 503, 504)
            elif any(code in error_lower for code in ["502", "503", "504"]) or "سرور در دسترس نیست" in error_lower:
                if platform == "Spotify":
                    return (
                        "🎵 **سرور اسپاتیفای موقتاً در دسترس نیست**\n\n"
                        "💡 **علت:**\n"
                        "• سرور دانلود اسپاتیفای مشکل دارد\n"
                        "• ترافیک زیاد سرور\n\n"
                        "🔄 **راه‌حل:**\n"
                        "• 10-15 دقیقه صبر کنید\n"
                        "• دوباره تلاش کنید\n"
                        "• اگر مشکل ادامه داشت، بعداً امتحان کنید"
                    )
                else:
                    return (
                        f"🔧 **سرور {platform} موقتاً در دسترس نیست**\n\n"
                        "سرور مشکل فنی دارد.\n\n"
                        "🔄 لطفاً چند دقیقه صبر کنید و دوباره تلاش کنید."
                    )
            
            # Timeout
            elif "timeout" in error_lower:
                return (
                    "⏱ **زمان درخواست تمام شد**\n\n"
                    "سرور پاسخ نداد.\n\n"
                    "🔄 لطفاً دوباره تلاش کنید"
                )
            
            # Network errors
            elif any(word in error_lower for word in ["network", "connection", "dns"]):
                return (
                    "🌐 **مشکل در اتصال**\n\n"
                    "خطا در برقراری ارتباط با سرور.\n\n"
                    "🔄 لطفاً دوباره تلاش کنید"
                )
            
            else:
                return f"❌ خطا در دریافت اطلاعات از {platform}"
        
        # If it's a dictionary (API response)
        if isinstance(api_response, dict):
            # Check for specific error patterns
            if api_response.get("error") is True:
                message = api_response.get("message", "")
                data = api_response.get("data", {})
                
                # Handle "No medias found" error
                if "No medias found" in message:
                    if isinstance(data, dict) and "message" in data:
                        data_message = data["message"]
                        
                        # Handle private URL error
                        if "Private Url is not supported" in data_message:
                            return f"🔒 این {platform} خصوصی است و نیاز به ورود دارد.\n\n💡 برای دانلود:\n• ابتدا وارد حساب خود شوید\n• سپس کوکی‌های مرورگر را استخراج کنید\n• یا از لینک عمومی استفاده کنید"
                        
                        # Handle restricted page
                        elif "Restricted personal page" in data_message:
                            return f"⛔ این صفحه محدود شده است.\n\n💡 برای دسترسی:\n• ابتدا این حساب را فالو کنید\n• منتظر تایید بمانید\n• سپس دوباره تلاش کنید"
                        
                        # Handle general private content
                        elif "follow the account" in data_message:
                            return f"👥 برای دسترسی به این محتوا باید حساب را فالو کنید.\n\n💡 مراحل:\n• حساب را فالو کنید\n• منتظر تایید بمانید\n• دوباره لینک را ارسال کنید"
                    
                    return f"📭 هیچ محتوای قابل دانلودی در این لینک {platform} یافت نشد."
                
                # Handle "data not found" error
                elif "data not found" in message.lower() or "not found" in message.lower():
                    return f"🔍 محتوای درخواستی در {platform} یافت نشد.\n\n💡 احتمالات:\n• لینک اشتباه است\n• محتوا حذف شده\n• دسترسی محدود شده"
                
                # Handle rate limiting
                elif "rate limit" in message.lower() or "too many requests" in message.lower():
                    return f"⏳ تعداد درخواست‌ها زیاد است. لطفاً چند دقیقه صبر کنید."
                
                # Handle API quota exceeded
                elif "quota" in message.lower() or "limit exceeded" in message.lower():
                    return f"📊 محدودیت API به پایان رسیده. لطفاً بعداً تلاش کنید."
                
                # Generic error with custom message
                elif message:
                    return f"❌ خطا در {platform}: {message}"
            
            # Handle successful response but no media
            elif api_response.get("medias") is not None and len(api_response.get("medias", [])) == 0:
                return f"📭 هیچ محتوای قابل دانلودی در این لینک {platform} یافت نشد."
        
        # Default fallback
        return f"❌ خطا در دریافت اطلاعات از {platform}. لطفاً لینک را بررسی کنید."
        
    except Exception as e:
        _log(f"Error in get_user_friendly_error_message: {e}")
        return f"❌ خطا در دریافت اطلاعات از {platform}"

# --- Bot API helpers to send media by URL (bypass MTProto upload) ---
def _bot_api_send(method: str, payload: dict, timeout: float = 15.0) -> dict:
    """Synchronous call to Telegram Bot API. Returns response dict or {'ok': False, 'description': ...}."""
    try:
        api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
        resp = requests.post(api_url, json=payload, timeout=timeout)
        return resp.json()
    except Exception as e:
        return {"ok": False, "description": str(e)}

async def _bot_api_send_async(method: str, payload: dict, timeout: float = 15.0) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: _bot_api_send(method, payload, timeout))

# Ensure captions stay within Telegram limits
def _safe_caption(text: str, max_len: int = 950):
    try:
        t = str(text) if text else ""
        if len(t) <= max_len:
            return t
        return t[:max_len-1] + "…"
    except Exception:
        return (str(text) or "")[:max_len-1] + "…"

# Generate Windows-safe filenames from titles
def _safe_filename(name: str, ext: str, max_base_len: int = 80) -> str:
    try:
        base = str(name) if name else "file"
        # Remove control characters (including newlines/tabs)
        base = re.sub(r"[\x00-\x1F]", " ", base)
        # Replace invalid Windows filename chars
        base = re.sub(r"[<>:\"/\\|?*]", "_", base)
        # Collapse whitespace
        base = re.sub(r"\s+", " ", base).strip()
        # Trim trailing spaces/dots
        base = base.rstrip(" .")
        # Limit length and avoid empty
        if not base:
            base = "file"
        base = base[:max_base_len]
        # Avoid reserved device names
        reserved = {"CON","PRN","AUX","NUL","COM1","COM2","COM3","COM4","COM5","COM6","COM7","COM8","COM9","LPT1","LPT2","LPT3","LPT4","LPT5","LPT6","LPT7","LPT8","LPT9"}
        if base.upper() in reserved:
            base = base + "_"
        # Sanitize extension
        ext = (ext or "mp4").strip(" .") or "mp4"
        return f"{base}.{ext}"
    except Exception:
        return f"file.{ext or 'mp4'}"

# Generate Windows-safe filenames with index suffix preserved
def _safe_filename_with_index(name: str, ext: str, idx: int, max_base_len: int = 80) -> str:
    try:
        suffix = f"_{idx}"
        base = str(name) if name else "file"
        base = re.sub(r"[\x00-\x1F]", " ", base)
        base = re.sub(r"[<>:\"/\\|?*]", "_", base)
        base = re.sub(r"\s+", " ", base).strip()
        base = base.rstrip(" .")
        if not base:
            base = "file"
        # Ensure we keep room for suffix
        room = max(1, max_base_len - len(suffix))
        base = base[:room]
        reserved = {"CON","PRN","AUX","NUL","COM1","COM2","COM3","COM4","COM5","COM6","COM7","COM8","COM9","LPT1","LPT2","LPT3","LPT4","LPT5","LPT6","LPT7","LPT8","LPT9"}
        if base.upper() in reserved:
            base = base + "_"
        ext = (ext or "mp4").strip(" .") or "mp4"
        return f"{base}{suffix}.{ext}"
    except Exception:
        return f"file_{idx}.{ext or 'mp4'}"

def get_platform_name(url):
    """Determine the platform based on URL (expanded)"""
    if INSTA_REGEX.search(url):
        return "Instagram"
    if SPOTIFY_REGEX.search(url):
        return "Spotify"
    if TIKTOK_REGEX.search(url):
        return "TikTok"
    if SOUNDCLOUD_REGEX.search(url):
        return "SoundCloud"
    if PINTEREST_REGEX.search(url):
        return "Pinterest"
    if TWITTER_REGEX.search(url):
        return "Twitter"
    if THREADS_REGEX.search(url):
        return "Threads"
    if FACEBOOK_REGEX.search(url):
        return "Facebook"
    if REDDIT_REGEX.search(url):
        return "Reddit"
    if IMGUR_REGEX.search(url):
        return "Imgur"
    if SNAPCHAT_REGEX.search(url):
        return "Snapchat"
    if TUMBLR_REGEX.search(url):
        return "Tumblr"
    if RUMBLE_REGEX.search(url):
        return "Rumble"
    if IFUNNY_REGEX.search(url):
        return "iFunny"
    if DEEZER_REGEX.search(url):
        return "Deezer"
    if RADIOJAVAN_REGEX.search(url):
        return "Radio Javan"
    return "Unknown"

async def get_universal_data_from_api(url):
    """Get media data from the universal API for Spotify, TikTok, and SoundCloud with timeout"""
    try:
        # Use asyncio.wait_for with 6 second timeout (more robust)
        result = await asyncio.wait_for(_api_request_sync(url), timeout=6.0)
        return result
    except asyncio.TimeoutError:
        universal_logger.warning(f"API timeout for URL: {url}")
        return {"error": True, "message": "timeout", "data": {}}
    except Exception as e:
        universal_logger.error(f"API Error for URL {url}: {e}")
        return {"error": True, "message": str(e), "data": {}}

def _api_request_sync(url):
    """Synchronous API request wrapped for async execution"""
    import concurrent.futures
    
    def _make_request():
        try:
            conn = http.client.HTTPSConnection("social-download-all-in-one.p.rapidapi.com", timeout=5.0)
            
            payload = json.dumps({"url": url})
            
            headers = {
                'x-rapidapi-key': RAPIDAPI_KEY,
                'x-rapidapi-host': "social-download-all-in-one.p.rapidapi.com",
                'Content-Type': "application/json"
            }
            
            conn.request("POST", "/v1/social/autolink", payload, headers)
            res = conn.getresponse()
            data = res.read()
            
            conn.close()
            
            response_data = json.loads(data.decode("utf-8"))
            universal_logger.info(f"API Response received for URL: {url}")
            return response_data
        except Exception as e:
            universal_logger.error(f"API request failed for URL {url}: {e}")
            return {"error": True, "message": f"network error: {str(e)}", "data": {}}
    
    # Run in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        return loop.run_in_executor(executor, _make_request)

def _extract_video_metadata(video_path: str):
    """Extract basic metadata and a small thumbnail for Telegram.
    Uses ffprobe/ffmpeg when available; keeps lightweight and skips for large files."""
    import shutil
    try:
        if not video_path or not os.path.exists(video_path):
            return {'width': 0, 'height': 0, 'duration': 0, 'thumbnail': None}
        
        # Proceed to metadata extraction without size-based skipping
        
        # Locate ffprobe/ffmpeg
        ffmpeg_path = os.environ.get('FFMPEG_PATH')
        if not ffmpeg_path:
            try:
                from config import FFMPEG_PATH as CFG_FFMPEG
                ffmpeg_path = CFG_FFMPEG
            except Exception:
                ffmpeg_path = None
        
        ffprobe_path = None
        ffmpeg_exe = None
        if ffmpeg_path and os.path.exists(ffmpeg_path):
            ffmpeg_exe = ffmpeg_path
            base_dir = os.path.dirname(ffmpeg_path)
            if os.name == 'nt':
                cand = os.path.join(base_dir, 'ffprobe.exe')
            else:
                cand = os.path.join(base_dir, 'ffprobe')
            if os.path.exists(cand):
                ffprobe_path = cand
        if not ffprobe_path:
            ffprobe_path = shutil.which('ffprobe') or 'ffprobe'
        if not ffmpeg_exe:
            ffmpeg_exe = shutil.which('ffmpeg') or 'ffmpeg'
        
        width = 0
        height = 0
        duration = 0
        thumb_path = None
        
        # Probe streams and format
        try:
            cmd = [ffprobe_path, '-v', 'error', '-print_format', 'json', '-show_streams', '-show_format', video_path]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if res.returncode == 0 and res.stdout:
                data = json.loads(res.stdout)
                # Duration from format
                fmt = data.get('format') or {}
                try:
                    duration = int(float(fmt.get('duration', 0)))
                except Exception:
                    duration = 0
                # Width/height from first video stream
                for s in data.get('streams', []):
                    if s.get('codec_type') == 'video':
                        width = int(s.get('width') or 0)
                        height = int(s.get('height') or 0)
                        break
        except Exception:
            pass
        
        # Generate small Telegram-friendly thumbnail (بهینه‌سازی شده)
        try:
            # Only if ffmpeg is available
            if ffmpeg_exe and isinstance(ffmpeg_exe, str):
                thumb_path = video_path.rsplit('.', 1)[0] + '_thumb.jpg'
                
                # بررسی اینکه آیا thumbnail قبلاً وجود دارد
                if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0:
                    pass  # از thumbnail موجود استفاده کن
                else:
                    # ساخت thumbnail با timeout کوتاه
                    cmd = [ffmpeg_exe, '-y', '-ss', '1', '-i', video_path, '-vframes', '1', 
                          '-vf', 'scale=320:-2', '-q:v', '5', '-f', 'image2', thumb_path]
                    try:
                        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                                     encoding='utf-8', errors='ignore', timeout=6)
                    except subprocess.TimeoutExpired:
                        thumb_path = None
                    
                    if not os.path.exists(thumb_path) or os.path.getsize(thumb_path) == 0:
                        thumb_path = None
        except Exception:
            thumb_path = None
        
        return {
            'width': width or None,
            'height': height or None,
            'duration': duration or 0,
            'thumbnail': thumb_path
        }
    except Exception:
        return {'width': 0, 'height': 0, 'duration': 0, 'thumbnail': None}

def _progress_callback(current, total):
    """Optimized progress callback for upload tracking"""
    try:
        # Only log at specific thresholds to reduce overhead
        if current == total:  # 100% completion
            univ_logger.info(f"Upload completed: {current} bytes")
        elif current > 0 and (current * 10) % total == 0:  # Every 10% without float division
            percentage = (current * 100) // total
            univ_logger.info(f"Upload progress: {percentage}% ({current}/{total} bytes)")
    except Exception:
        pass

async def _fetch_og_media(url: str):
    """Fallback: fetch media via OpenGraph tags with timeout"""
    try:
        # Use asyncio.wait_for with 4.0 second timeout (more robust)
        return await asyncio.wait_for(_og_request_sync(url), timeout=4.0)
    except asyncio.TimeoutError:
        universal_logger.warning(f"OG fallback timeout for URL: {url}")
        return None
    except Exception as e:
        universal_logger.warning(f"OG fetch fallback failed for {url}: {e}")
        return None

def _og_request_sync(url: str):
    """Synchronous OG request wrapped for async execution"""
    import concurrent.futures
    
    def _make_og_request():
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36',
                'Accept-Language': 'fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7'
            }
            resp = requests.get(url, headers=headers, timeout=3.5, allow_redirects=True)
            html = resp.text
            # Try og:video first
            import re as _re
            vid = _re.search(r'<meta[^>]*property=["\"]og:video["\"][^>]*content=["\"]([^"\"]+)["\"]', html, flags=_re.IGNORECASE)
            if vid:
                vurl = vid.group(1)
                ext = 'mp4' if '.mp4' in vurl else 'mp4'
                return { 'url': vurl, 'extension': ext, 'type': 'video', 'quality': 'unknown', 'title': None, 'author': None, 'duration': 'Unknown' }
            img = _re.search(r'<meta[^>]*property=["\"]og:image["\"][^>]*content=["\"]([^"\"]+)["\"]', html, flags=_re.IGNORECASE)
            if img:
                iurl = img.group(1)
                # Prefer original image if Pinterest provides srcset
                ext = 'jpg'
                if '.png' in iurl:
                    ext = 'png'
                elif '.webp' in iurl:
                    ext = 'webp'
                return { 'url': iurl, 'extension': ext, 'type': 'image', 'quality': 'unknown', 'title': None, 'author': None, 'duration': 'Unknown' }
            return None
        except Exception as e:
            universal_logger.warning(f"OG request failed: {e}")
            return None
    
    # Run in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        return loop.run_in_executor(executor, _make_og_request)

async def handle_universal_link(client: Client, message: Message):
    """Handle downloads for Spotify, TikTok, and SoundCloud links"""
    try:
        t0 = time.perf_counter()
        _log("[UNIV] Start processing message")
        user_id = message.from_user.id
        
        # Check if user is in database
        db = DB()
        if not db.check_user_register(user_id):
            await message.reply_text(txt['first_message'].format(message.from_user.first_name), reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 شروع مجدد", callback_data="start")]
            ]))
            return
        
        # Check if user is blocked (banned/daily limit)
        blocked_until_str = db.get_blocked_until(user_id)
        if blocked_until_str:
            try:
                blocked_until = _dt.fromisoformat(blocked_until_str)
                if blocked_until > _dt.now():
                    await message.reply_text("⛔ شما به دلیل تجاوز از حد مجاز روزانه موقتاً مسدود شده‌اید.\n\n⏰ لطفاً بعداً تلاش کنید.")
                    return
            except Exception:
                pass
        
        url = message.text.strip()
        platform = get_platform_name(url)
        _log(f"[UNIV] Platform detected: {platform}")
        
        # Reserve user for per-user concurrency control
        user_reserved = False
        try:
            if not reserve_user(user_id):
                await message.reply_text("⛔ شما هم‌اکنون به سقف دانلود همزمان خود رسیده‌اید. لطفاً منتظر تکمیل دانلود‌های قبلی بمانید.")
                return
            user_reserved = True
        except Exception:
            pass
        
        # Send initial status message
        status_msg = await message.reply_text(f"🔄 در حال پردازش لینک {platform}...")
        slot_acquired = False
        stats = get_queue_stats()
        if stats.get('active') >= stats.get('capacity'):
            try:
                await status_msg.edit_text("⏳ ظرفیت دانلود مشغول است؛ شما در صف هستید...")
            except Exception:
                pass
        
        # Advertisement will be handled later in the process
        
        # Get data from API with optimized parallel approach using FIRST_COMPLETED
        t_api_start = time.perf_counter()
        await status_msg.edit_text(f"📡 در حال دریافت اطلاعات از {platform}...")
        api_data = None
        fallback_media = None
        last_api_error_message = None
        
        # Layered retry: try API and fallback concurrently, up to N cycles
        # تنظیمات retry بر اساس platform
        retry_config = {
            "Instagram": {"cycles": 5, "timeout": 8},
            "TikTok": {"cycles": 3, "timeout": 6},
            "Pinterest": {"cycles": 3, "timeout": 6},
            "Facebook": {"cycles": 3, "timeout": 6},
        }
        
        config = retry_config.get(platform, {"cycles": 2, "timeout": 5})
        max_cycles = config["cycles"]
        base_timeout = config["timeout"]
        
        api_data = None
        fallback_media = None
        last_api_error_message = None

        for cycle in range(max_cycles):
            # Create tasks for API and fallback (Instagram only)
            tasks = [("api", asyncio.create_task(get_universal_data_from_api(url)))]
            if platform == "Instagram":
                tasks.append(("fallback", asyncio.create_task(_fetch_og_media(url))))

            pending = {t for _, t in tasks}
            wait_timeout = base_timeout + (2 * cycle)  # grow timeout per cycle based on platform

            try:
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED, timeout=wait_timeout)

                # Process completed tasks
                for completed_task in done:
                    for task_name, task in tasks:
                        if task is completed_task:
                            try:
                                result = completed_task.result()
                                _log(f"[UNIV] {task_name} completed (cycle {cycle+1}) with result: {bool(result)}")

                                if task_name == "api" and result:
                                    invalid = (result.get("error", False) or
                                               result.get("data", {}).get("error", False) or
                                               not result.get("medias"))
                                    if not invalid:
                                        api_data = result
                                        _log(f"[UNIV] API success in {time.perf_counter() - t_api_start:.2f}s (cycle {cycle+1})")
                                        print(f"✅ API success for {platform}")
                                    else:
                                        # Store the full API response for better error handling
                                        last_api_error_message = result
                                        _log(f"[UNIV] API returned invalid data (cycle {cycle+1}): {result}")
                                        print(f"⚠️ API invalid data (cycle {cycle+1}): {result.get('message', 'Unknown')}")

                                elif task_name == "fallback" and result:
                                    fallback_media = result
                                    _log(f"[UNIV] Fallback success in {time.perf_counter() - t_api_start:.2f}s (cycle {cycle+1})")
                            except Exception as e:
                                _log(f"[UNIV] {task_name} task failed: {e}")
                                if task_name == "api":
                                    last_api_error_message = str(e)
                            break

                # If we got a valid result, cancel remaining tasks and break
                if api_data or fallback_media:
                    for remaining_task in pending:
                        remaining_task.cancel()
                    break

                # Otherwise, wait for remaining tasks this cycle
                if pending:
                    try:
                        done, pending = await asyncio.wait(pending, timeout=3 + cycle)  # small grace window
                        for completed_task in done:
                            for task_name, task in tasks:
                                if task is completed_task:
                                    try:
                                        result = completed_task.result()
                                        if task_name == "api" and result and not (result.get("error") or result.get("data", {}).get("error") or not result.get("medias")):
                                            api_data = result
                                        elif task_name == "fallback" and result:
                                            fallback_media = result
                                    except Exception as e:
                                        _log(f"[UNIV] {task_name} secondary task failed: {e}")
                                    break
                    finally:
                        for remaining_task in pending:
                            remaining_task.cancel()

            except asyncio.TimeoutError:
                _log(f"[UNIV] Tasks timed out after {wait_timeout} seconds (cycle {cycle+1})")
                last_api_error_message = "Timeout: درخواست بیش از حد طول کشید"
            except Exception as e:
                _log(f"[UNIV] Error in parallel API/fallback (cycle {cycle+1}): {e}")
            finally:
                for _, task in tasks:
                    if not task.done():
                        task.cancel()

            # Prepare for next cycle if not successful
            if not (api_data or fallback_media) and cycle + 1 < max_cycles:
                try:
                    await status_msg.edit_text(f"🔁 تلاش دوباره برای دریافت اطلاعات از {platform}... (تلاش {cycle+2}/{max_cycles})")
                except Exception:
                    pass
                # small backoff jitter
                try:
                    await asyncio.sleep(0.6 * (cycle + 1))
                except Exception:
                    pass
        
        # Check results
        if not api_data and not fallback_media:
            # لاگ تفصیلی برای debug
            _log(f"[UNIV] Both API and fallback failed for {platform}")
            _log(f"[UNIV] Last API error: {last_api_error_message}")
            print(f"❌ Both API and fallback failed for {platform}")
            print(f"   Last error: {last_api_error_message}")
            
            # Use user-friendly error message
            if last_api_error_message:
                error_msg = get_user_friendly_error_message(last_api_error_message, platform)
            else:
                error_msg = f"❌ خطا در دریافت اطلاعات از {platform}"
            
            # اضافه کردن پیشنهاد برای اینستاگرام
            if platform == "Instagram":
                error_msg += "\n\n💡 **نکته:** اگر این لینک روی یک اکانت کار می‌کند اما روی اکانت دیگر نه، احتمالاً API موقتاً محدود شده است. لطفاً 10-15 دقیقه صبر کنید."
            
            await status_msg.edit_text(error_msg)
            try:
                if user_reserved:
                    release_user(user_id)
            except Exception:
                pass
            return

        # Debug logging for API response
        _log(f"[UNIV] API data check: api_data exists={api_data is not None}")
        if api_data:
            _log(f"[UNIV] API data keys: {list(api_data.keys())}")
            _log(f"[UNIV] Has medias key: {'medias' in api_data}")
            if 'medias' in api_data:
                _log(f"[UNIV] Medias count: {len(api_data.get('medias', []))}")
                _log(f"[UNIV] Medias content: {api_data.get('medias', [])}")

        # If API returned nothing after retries, try fallback for supported platforms
        if (not api_data or "medias" not in api_data or not api_data.get("medias")) and platform in ("Pinterest", "Imgur", "Tumblr", "Instagram"):
            _log(f"[UNIV] Entering fallback mode for {platform}")
            await status_msg.edit_text(f"📡 API چیزی برنگرداند؛ تلاش برای استخراج مستقیم {platform}...")
            
            # Try fallback if not already tried
            if not fallback_media:
                try:
                    og = await _fetch_og_media(url)
                    if og:
                        fallback_media = og
                        _log(f"[UNIV] Fallback successful for {platform}")
                    else:
                        _log(f"[UNIV] Fallback failed for {platform}")
                except Exception as e:
                    _log(f"[UNIV] Fallback error for {platform}: {e}")
            
            if not fallback_media:
                # Use user-friendly error message for fallback failure
                if last_api_error_message:
                    err_msg = get_user_friendly_error_message(last_api_error_message, platform)
                else:
                    err_msg = f"❌ خطا در دریافت اطلاعات از {platform}. لطفاً لینک را بررسی کنید."
                
                await status_msg.edit_text(err_msg)
                try:
                    if user_reserved:
                        release_user(user_id)
                except Exception:
                    pass
                return
        
        # Extract media information
        title = api_data.get("title", "Unknown Title") if api_data else "Unknown Title"
        author = api_data.get("author", "Unknown Author") if api_data else "Unknown Author"
        duration_api = api_data.get("duration", 0) if api_data else 0
        thumbnail = api_data.get("thumbnail", "") if api_data else ""
        
        # Find the best quality media
        medias = api_data.get("medias", []) if api_data else []
        is_instagram = (platform == "Instagram")
        
        # For Instagram, check if it's truly an album (multiple different posts) vs single post with multiple formats
        is_album = False
        if is_instagram and len(medias) > 1:
            # Check if we have different media types that suggest it's a single post with video+audio
            video_count = sum(1 for m in medias if m.get("type") == "video")
            audio_count = sum(1 for m in medias if m.get("type") == "audio")
            
            # If we have exactly 1 video and 1 audio, it's likely a single post with separate streams
            if video_count == 1 and audio_count == 1:
                is_album = False
            else:
                # Multiple videos or photos = real album
                is_album = True
        
        _log(f"[UNIV] Medias count: {len(medias)} | album={is_album}")
        _log(f"[UNIV] Medias list: {medias}")
        if not medias:
            _log(f"[UNIV] No medias found, checking fallback_media: {fallback_media}")
            if fallback_media:
                medias = [fallback_media]
                _log(f"[UNIV] Using fallback media: {medias}")
            else:
                _log(f"[UNIV] No fallback media available, returning error")
                await status_msg.edit_text(f"❌ هیچ فایل قابل دانلودی از {platform} یافت نشد.")
                try:
                    if user_reserved:
                        release_user(user_id)
                except Exception:
                    pass
                return
        
        # Prefer video over audio, and highest quality
        selected_media = None
        if not is_album:
            for media in medias:
                if media.get("type") == "video":
                    selected_media = media
                    break
            if not selected_media:
                # If no video found, take the first available media
                selected_media = medias[0]
        
        if not is_album:
            download_url = selected_media.get("url")
            file_extension = selected_media.get("extension", "mp4")
            media_type = selected_media.get("type", "video")
            quality = selected_media.get("quality", "Unknown")
            # Robust duration int
            duration_value = selected_media.get("duration", duration_api)
            try:
                duration_sec = int(duration_value) if duration_value not in (None, "", "Unknown") else 0
            except Exception:
                duration_sec = 0

            if not download_url:
                await status_msg.edit_text(f"❌ لینک دانلود از {platform} یافت نشد.")
                try:
                    if user_reserved:
                        release_user(user_id)
                except Exception:
                    pass
                return

            # Create filename (Windows-safe)
            safe_title_src = title or selected_media.get('title') or platform
            filename = _safe_filename(safe_title_src, file_extension)

            # Download file - single status message, no updates during retry
            if not slot_acquired:
                await acquire_slot()
                slot_acquired = True
            await status_msg.edit_text(f"📥 در حال دانلود از {platform}...")
            t_dl_start = time.perf_counter()
            
            # Try memory streaming for small files first (optimization A)
            use_memory = False
            memory_stream = await download_to_memory_stream(download_url, max_size_mb=10)
            if memory_stream:
                total_size = memory_stream.tell()
                t_dl_end = time.perf_counter()
                _log(f"[UNIV] Memory download took {(t_dl_end - t_dl_start):.2f}s | size={total_size}")
                if total_size and total_size > 0:
                    # Use memory stream for direct upload
                    file_path = filename  # Keep filename for metadata
                    memory_buffer = memory_stream
                    use_memory = True
                else:
                    memory_buffer = None
            if not use_memory:
                # Fallback to file download for larger files with smart retry
                download_result = None
                last_error = None
                
                # تنظیمات retry بر اساس platform
                if platform == "Instagram":
                    max_attempts = 5  # افزایش به 5 برای Instagram
                    base_delay = 2.0  # افزایش به 2 ثانیه
                    max_delay = 30.0
                else:
                    max_attempts = 3
                    base_delay = 1.0
                    max_delay = 10.0
                
                for attempt in range(max_attempts):
                    try:
                        _log(f"[UNIV] Download attempt {attempt+1}/{max_attempts} for {platform}")
                        download_result = await download_stream_to_file(download_url, filename)
                        _log(f"[UNIV] Download success on attempt {attempt+1}")
                        break
                    except Exception as e:
                        last_error = e
                        error_str = str(e).lower()
                        _log(f"[UNIV] Download attempt {attempt+1}/{max_attempts} failed: {e}")
                        
                        if attempt < max_attempts - 1:  # Only sleep if not last attempt
                            # محاسبه delay بر اساس نوع خطا
                            if "403" in error_str or "forbidden" in error_str:
                                # برای 403، delay بیشتر
                                delay = min(base_delay * (3 ** attempt), max_delay)  # 2, 6, 18, 30
                                _log(f"[UNIV] 403 error detected, waiting {delay}s before retry")
                            
                            elif "429" in error_str or "rate limit" in error_str or "too many" in error_str:
                                # برای rate limit، delay خیلی بیشتر
                                delay = min(base_delay * (5 ** attempt), max_delay)  # 2, 10, 30
                                _log(f"[UNIV] Rate limit detected, waiting {delay}s before retry")
                            
                            elif "timeout" in error_str:
                                # برای timeout، delay متوسط
                                delay = min(base_delay * (2 ** attempt), max_delay)  # 2, 4, 8, 16, 30
                                _log(f"[UNIV] Timeout detected, waiting {delay}s before retry")
                            
                            else:
                                # برای سایر خطاها، delay عادی
                                delay = min(base_delay * (2 ** attempt), max_delay)
                                _log(f"[UNIV] Generic error, waiting {delay}s before retry")
                            
                            await asyncio.sleep(delay)
                t_dl_end = time.perf_counter()
                _log(f"[UNIV] Download took {(t_dl_end - t_dl_start):.2f}s | size={os.path.getsize(filename) if os.path.exists(filename) else 'NA'}")

                # Extract file_path from tuple (file_path, total_size)
                if isinstance(download_result, tuple):
                    file_path, total_size = download_result
                else:
                    file_path = download_result

                if not file_path or not os.path.exists(file_path):
                    # استفاده از پیام کاربرپسند به جای خطای فنی
                    if last_error:
                        err_txt = get_user_friendly_error_message(str(last_error), platform)
                        # اضافه کردن پیشنهاد خاص برای مشکلات سرور
                        if any(code in str(last_error).lower() for code in ["502", "503", "504", "سرور در دسترس نیست"]):
                            err_txt += f"\n\n💡 **نکته:** اگر مشکل ادامه داشت، لطفاً 15-30 دقیقه بعد دوباره تلاش کنید."
                    else:
                        err_txt = f"❌ خطا در دانلود فایل از {platform}.\n\n🔄 لطفاً دوباره تلاش کنید."
                    await status_msg.edit_text(err_txt)
                    try:
                        if slot_acquired:
                            release_slot()
                            slot_acquired = False
                    except Exception:
                        pass
                    try:
                        if user_reserved:
                            release_user(user_id)
                    except Exception:
                        pass
                    return
                
                memory_buffer = None  # No memory buffer for file downloads
        else:
            # Album download for Instagram: download all supported medias
            if not slot_acquired:
                await acquire_slot()
                slot_acquired = True
            await status_msg.edit_text(f"📥 در حال دانلود {len(medias)} آیتم از {platform}...")
            album_files = []
            t_dl_all_start = time.perf_counter()
            for idx, media in enumerate(medias, start=1):
                mtype = media.get("type")
                if mtype not in ("image", "photo", "video"):
                    continue
                murl = media.get("url")
                if not murl:
                    continue
                mext = media.get("extension", "mp4" if mtype == "video" else "jpg")
                safe_title_src = title or platform
                mfilename = _safe_filename_with_index(safe_title_src, mext, idx)
                try:
                    t_dl_start_i = time.perf_counter()
                    # Retry per-item download up to 3 times (silent retries)
                    dl_res = None
                    per_item_error = None
                    for attempt in range(3):
                        try:
                            dl_res = await download_stream_to_file(murl, mfilename)
                            break
                        except Exception as e:
                            per_item_error = e
                            _log(f"[UNIV] Item {idx} attempt {attempt+1}/3 failed: {e}")
                            if attempt < 2:  # Only sleep if not last attempt
                                await asyncio.sleep(0.8)
                    t_dl_end_i = time.perf_counter()
                    _log(f"[UNIV] Item {idx} download took {(t_dl_end_i - t_dl_start_i):.2f}s | type={mtype}")
                    if isinstance(dl_res, tuple):
                        mp, _ = dl_res
                    else:
                        mp = dl_res
                    if mp and os.path.exists(mp) and os.path.getsize(mp) > 0:
                        album_files.append((mtype, mp))
                    else:
                        if per_item_error:
                            _log(f"[UNIV] Item {idx} failed after retries: {per_item_error}")
                except Exception as e:
                    _log(f"[UNIV] Failed downloading item {idx}: {e}")
                    continue
            t_dl_all_end = time.perf_counter()
            _log(f"[UNIV] All album downloads took {(t_dl_all_end - t_dl_all_start):.2f}s | files={len(album_files)}")
            if not album_files:
                await status_msg.edit_text(f"❌ هیچ فایل قابل ارسال از {platform} یافت نشد.")
                try:
                    if slot_acquired:
                        release_slot()
                        slot_acquired = False
                except Exception:
                    pass
                try:
                    if user_reserved:
                        release_user(user_id)
                except Exception:
                    pass
                return

            # Ensure caption fields exist for album branch
            media_type = "album"
            quality = "Unknown"
            duration_sec = 0
        
        # ساخت caption اختصاصی برای هر platform
        try:
            caption = build_caption(platform, api_data or {})
            caption = _safe_caption(caption, max_len=950)
        except Exception as e:
            _log(f"[UNIV] Caption builder error: {e}")
            # Fallback به caption ساده
            caption = f"📥 محتوا از {platform}"
            if title:
                caption += f"\n📄 {title[:100]}"
            caption = _safe_caption(caption, max_len=950)
        
        # Check advertisement settings once
        ad_enabled = False
        ad_position = 'after'  # default
        try:
            from .db_path_manager import db_path_manager
            json_db_path = db_path_manager.get_json_db_path()
            
            with open(json_db_path, 'r', encoding='utf-8') as f:
                db_data = json.load(f)
            ad_settings = db_data.get('advertisement', {})
            ad_enabled = ad_settings.get('enabled', False)
            ad_position = ad_settings.get('position', 'after')
        except Exception:
            pass
        
        # Send advertisement before content if enabled and position is 'before'
        if ad_enabled and ad_position == 'before':
            send_advertisement(client, message.chat.id)
            await asyncio.sleep(1)  # Wait 1 second after advertisement
        
        # Upload file(s) based on type
        await status_msg.edit_text(f"📤 در حال ارسال {'آلبوم' if is_album else 'فایل'} {platform}...")
        
        try:
            # Decide upload method based on media type and extension
            image_exts = ["jpg", "jpeg", "png", "webp"]
            video_exts = ["mp4", "avi", "mov", "mkv", "webm"]

            if is_album:
                media_group = []
                # Extract metadata only for first video file to reduce CPU load
                first_video_meta = None
                for idx, (mtype, mp) in enumerate(album_files, start=1):
                    if mtype in ("image", "photo"):
                        if idx == 1:
                            media_group.append(InputMediaPhoto(media=mp, caption=caption))
                        else:
                            media_group.append(InputMediaPhoto(media=mp))
                    elif mtype == "video":
                        # Extract metadata only for first video, reuse for others
                        if first_video_meta is None:
                            first_video_meta = _extract_video_metadata(mp)
                        
                        # Prepare video parameters safely
                        video_params = {
                            'media': mp,
                            'width': first_video_meta.get('width', 0) or None,
                            'height': first_video_meta.get('height', 0) or None,
                            'duration': first_video_meta.get('duration', 0) or None,
                            'thumb': first_video_meta.get('thumbnail')
                        }
                        
                        # Only add caption for first item
                        if idx == 1:
                            video_params['caption'] = caption
                        
                        # Filter out None values to prevent errors
                        video_params = {k: v for k, v in video_params.items() if v is not None}
                        
                        media_group.append(InputMediaVideo(**video_params))
                # Measure only the network upload time
                t_up_start = time.perf_counter()
                last_group_error = None
                for attempt in range(3):
                    try:
                        await client.send_media_group(
                            chat_id=message.chat.id,
                            media=media_group
                        )
                        last_group_error = None
                        break
                    except Exception as e:
                        last_group_error = e
                        _log(f"[UNIV] send_media_group attempt {attempt+1}/3 failed: {e}")
                        await asyncio.sleep(0.8)
                if last_group_error:
                    raise last_group_error
                t_up_end = time.perf_counter()
            else:
                # Use smart upload strategy for optimized I/O
                t_up_start = time.perf_counter()
                
                if media_type in ("image", "photo") or file_extension.lower() in image_exts or platform.lower() in ("pinterest", "imgur"):
                    # Use memory buffer if available, otherwise file path
                    upload_source = memory_buffer if memory_buffer else file_path
                    
                    # Smart upload with retry logic
                    last_upload_error = None
                    for attempt in range(3):
                        try:
                            if memory_buffer:
                                await client.send_photo(
                                    chat_id=message.chat.id,
                                    photo=memory_buffer,
                                    caption=caption
                                )
                            else:
                                success = await smart_upload_strategy(
                                    client, message.chat.id, file_path, "photo", caption=caption
                                )
                                if not success:
                                    raise Exception("Smart upload failed")
                            last_upload_error = None
                            break
                        except Exception as e:
                            last_upload_error = e
                            _log(f"[UNIV] send_photo attempt {attempt+1}/3 failed: {e}")
                            await asyncio.sleep(0.8)
                    if last_upload_error:
                        raise last_upload_error
                    t_up_end = time.perf_counter()
                elif (media_type == "video" or file_extension.lower() in video_exts or platform.lower() == "tiktok"):
                    # Use API metadata if available, otherwise extract from file
                    # Initialize video metadata variables for use in fallback
                    video_width = None
                    video_height = None
                    video_duration = duration_sec
                    video_thumb = None
                    
                    # Check if we have width/height from API response
                    if hasattr(selected_media, 'get') and selected_media.get('width') and selected_media.get('height'):
                        video_width = selected_media.get('width')
                        video_height = selected_media.get('height')
                        _log(f"[UNIV] Using API metadata: {video_width}x{video_height}")
                    else:
                        video_meta = _extract_video_metadata(file_path)
                        video_width = video_meta.get('width', 0) or None
                        video_height = video_meta.get('height', 0) or None
                        video_duration = video_meta.get('duration', 0) or video_duration
                        video_thumb = video_meta.get('thumbnail')
                        _log(f"[UNIV] Using ffprobe metadata: {video_width}x{video_height}, duration={video_duration}")
                    
                    last_upload_error = None
                    upload_done = False
                    
                    # Check file size for optimization
                    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    file_size_mb = file_size / (1024 * 1024)

                    # Try Bot API direct URL send first (bypasses server upload)
                    bot_api_sent = False
                    if isinstance(download_url, str) and download_url.startswith(("http://", "https://")) and file_size_mb <= 50.0:
                        try:
                            _log("[UNIV] Trying Bot API sendVideo by URL")
                            payload = {
                                "chat_id": message.chat.id,
                                "video": download_url,
                                "caption": caption,
                                "supports_streaming": True,
                            }
                            # Optional metadata if available
                            if video_duration is not None and video_duration > 0:
                                payload["duration"] = video_duration
                            if video_width is not None and video_width > 0:
                                payload["width"] = video_width
                            if video_height is not None and video_height > 0:
                                payload["height"] = video_height

                            res = await _bot_api_send_async("sendVideo", payload)
                            if res.get("ok"):
                                bot_api_sent = True
                                last_upload_error = None
                                upload_done = True
                                _log("[UNIV] Bot API URL send succeeded")
                            else:
                                _log(f"[UNIV] Bot API sendVideo failed: {res.get('description')}")
                        except Exception as e:
                            _log(f"[UNIV] Bot API sendVideo exception: {e}")

                    # Use smart upload strategy for video (fallbacks)
                    if (not bot_api_sent) and memory_buffer:
                        # Use memory buffer for small videos
                        max_attempts = 3
                        for attempt in range(max_attempts):
                            try:
                                video_params = {
                                    'chat_id': message.chat.id,
                                    'video': memory_buffer,
                                    'caption': caption,
                                    'supports_streaming': True
                                }
                                
                                # Add metadata if available
                                if video_duration is not None:
                                    video_params['duration'] = video_duration
                                if video_width is not None and video_width > 0:
                                    video_params['width'] = video_width
                                if video_height is not None and video_height > 0:
                                    video_params['height'] = video_height
                                if video_thumb is not None:
                                    video_params['thumb'] = video_thumb
                                
                                await client.send_video(**video_params)
                                last_upload_error = None
                                break
                            except Exception as e:
                                last_upload_error = e
                                _log(f"[UNIV] send_video (memory) attempt {attempt+1}/{max_attempts} failed: {e}")
                                await asyncio.sleep(0.8)
                    elif not bot_api_sent:
                        # Prefer sending as document for faster delivery on larger videos
                        prefer_document_for_large_video = False
                        fast_upload_threshold_mb = 512.0

                        if prefer_document_for_large_video and file_size_mb >= fast_upload_threshold_mb:
                            try:
                                await client.send_document(
                                    chat_id=message.chat.id,
                                    document=file_path,
                                    caption=_safe_caption(caption, max_len=950)
                                )
                                last_upload_error = None
                                _log(f"[UNIV] Sent large video as document for speed ({file_size_mb:.1f}MB)")
                            except Exception as e:
                                last_upload_error = e
                                _log(f"[UNIV] send_document for large video failed: {e}")
                        else:
                            # Use smart upload strategy for file-based upload
                            success = await smart_upload_strategy(
                                client, message.chat.id, file_path, "video",
                                caption=caption, duration=video_duration,
                                width=video_width, height=video_height,
                                thumb=video_thumb, supports_streaming=True
                            )
                            if not success:
                                last_upload_error = Exception("Smart upload strategy failed")

                    if last_upload_error:
                        raise last_upload_error
                    t_up_end = time.perf_counter()
                else:
                    # Audio upload with smart strategy
                    last_upload_error = None
                    
                    if memory_buffer:
                        # Use memory buffer for small audio files
                        for attempt in range(3):
                            try:
                                await client.send_audio(
                                    chat_id=message.chat.id,
                                    audio=memory_buffer,
                                    caption=caption,
                                    duration=duration_sec,
                                    title=title,
                                    performer=author
                                )
                                last_upload_error = None
                                break
                            except Exception as e:
                                last_upload_error = e
                                _log(f"[UNIV] send_audio (memory) attempt {attempt+1}/3 failed: {e}")
                                await asyncio.sleep(0.8)
                    else:
                        # Use smart upload strategy for file-based upload
                        success = await smart_upload_strategy(
                            client, message.chat.id, file_path, "audio",
                            caption=caption, duration=duration_sec,
                            title=title, performer=author
                        )
                        if not success:
                            last_upload_error = Exception("Smart upload strategy failed")
                    
                    if last_upload_error:
                        raise last_upload_error
                    t_up_end = time.perf_counter()
            _log(f"[UNIV] Upload took {(t_up_end - t_up_start):.2f}s")
            try:
                if slot_acquired:
                    release_slot()
                    slot_acquired = False
            except Exception:
                pass
        except Exception as upload_error:
            print(f"Upload error: {upload_error}")
            
            # Check file size before fallback to document
            file_to_check = file_path if not is_album else album_files[0][1]
            file_size = os.path.getsize(file_to_check) if os.path.exists(file_to_check) else 0
            file_size_mb = file_size / (1024 * 1024)
            
            # For video files larger than 50MB, don't fallback to document
            # Instead, try to send as video with streaming support using smart strategy
            if (media_type == "video" or file_extension.lower() in video_exts) and file_size_mb > 50:
                try:
                    # Use smart upload strategy for large video files
                    success = await smart_upload_strategy(
                        client, message.chat.id, file_to_check, "video",
                        caption=_safe_caption(caption, max_len=950),
                        duration=video_duration if 'video_duration' in locals() else None,
                        width=video_width if 'video_width' in locals() else None,
                        height=video_height if 'video_height' in locals() else None,
                        supports_streaming=True
                    )
                    
                    if not success:
                        raise Exception("Smart upload strategy failed for large video")
                        
                except Exception as video_fallback_error:
                    print(f"Video fallback error: {video_fallback_error}")
                    await message.reply_text(f"❌ فایل ویدیو بیش از حد بزرگ است ({file_size_mb:.1f}MB). لطفاً فایل کوچکتری انتخاب کنید.")
                    try:
                        if user_reserved:
                            release_user(user_id)
                    except Exception:
                        pass
                    return
            else:
                # For smaller files or non-video files, use document fallback
                try:
                    await client.send_document(
                        chat_id=message.chat.id,
                        document=file_to_check,
                        caption=_safe_caption(caption, max_len=950)
                    )
                except Exception as fallback_error:
                    print(f"Fallback upload error: {fallback_error}")
                    await message.reply_text(f"❌ خطا در ارسال فایل از {platform}: {str(upload_error)}")
                    try:
                        if user_reserved:
                            release_user(user_id)
                    except Exception:
                        pass
                    return
        
        # Delete status message safely
        try:
            await status_msg.delete()
            status_msg = None  # Mark as deleted
        except Exception:
            pass
        
        # Send advertisement after content if enabled and position is 'after'
        try:
            if slot_acquired:
                release_slot()
                slot_acquired = False
        except Exception:
            pass
        if ad_enabled and ad_position == 'after':
            await asyncio.sleep(1)  # Wait 1 second after upload
            send_advertisement(client, message.chat.id)
        
        # Run cleanup and stats in background to avoid blocking user
        async def cleanup_and_stats():
            try:
                # Increment download count
                now_str = _dt.now().isoformat(timespec='seconds')
                db.increment_request(user_id, now_str)
                
                # Clean up downloaded file(s) and thumbnails
                if not is_album:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    # Clean up thumbnail if exists
                    thumb_path = file_path.rsplit('.', 1)[0] + '_thumb.jpg'
                    if os.path.exists(thumb_path):
                        os.remove(thumb_path)
                else:
                    for _, fp in album_files:
                        try:
                            if os.path.exists(fp):
                                os.remove(fp)
                            # Clean up thumbnail if exists
                            thumb_path = fp.rsplit('.', 1)[0] + '_thumb.jpg'
                            if os.path.exists(thumb_path):
                                os.remove(thumb_path)
                        except Exception:
                            pass
                
                t_end = time.perf_counter()
                _log(f"[UNIV] Total processing time: {(t_end - t0):.2f}s")
            except Exception as cleanup_error:
                _log(f"[UNIV] Cleanup error: {cleanup_error}")
        
        # Start cleanup in background without waiting
        asyncio.create_task(cleanup_and_stats())
        
        # Release per-user reservation
        try:
            if user_reserved:
                release_user(user_id)
        except Exception:
            pass
            
    except Exception as e:
        error_msg = str(e)
        print(f"Universal download error: {error_msg}")
        try:
            if 'slot_acquired' in locals() and slot_acquired:
                release_slot()
                slot_acquired = False
        except Exception:
            pass
        
        # Release per-user reservation on error
        try:
            if 'user_reserved' in locals() and user_reserved:
                release_user(user_id)
                user_reserved = False
        except Exception:
            pass
        
        # Clean up status message if it still exists
        try:
            if 'status_msg' in locals() and status_msg is not None:
                await status_msg.delete()
        except Exception:
            pass
        
        try:
            if "API Error" in error_msg:
                await message.reply_text(f"❌ خطا در ارتباط با سرور {platform}. لطفاً بعداً تلاش کنید.")
            elif "medias" in error_msg:
                await message.reply_text(f"❌ فایل قابل دانلود از {platform} یافت نشد.")
            else:
                await message.reply_text(f"❌ خطا در پردازش لینک {platform}: {error_msg}")
        except:
            pass


# Instagram handler - register with Pyrogram
from pyrogram import filters

@Client.on_message(filters.private & filters.regex(INSTA_REGEX))
async def handle_instagram_link(client: Client, message: Message):
    """Handler for Instagram links - delegates to universal downloader"""
    try:
        universal_logger.info(f"Instagram link detected from user {message.from_user.id}: {message.text}")
        await handle_universal_link(client, message)
    except Exception as e:
        universal_logger.error(f"Instagram handler error: {e}")
        try:
            await message.reply_text(
                "❌ خطا در پردازش لینک اینستاگرام.\n\n"
                "🔄 لطفاً دوباره تلاش کنید."
            )
        except:
            pass
