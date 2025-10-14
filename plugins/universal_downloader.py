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
from plugins.media_utils import send_advertisement, download_file_simple
from plugins.db_wrapper import DB
from plugins import constant
from datetime import datetime as _dt
import logging
import requests
import time
from PIL import Image
import subprocess

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
        # Use asyncio.wait_for with 3 second timeout
        return await asyncio.wait_for(_api_request_sync(url), timeout=3.0)
    except asyncio.TimeoutError:
        universal_logger.warning(f"API timeout for URL: {url}")
        return None
    except Exception as e:
        universal_logger.error(f"API Error for URL {url}: {e}")
        return None

def _api_request_sync(url):
    """Synchronous API request wrapped for async execution"""
    import concurrent.futures
    
    def _make_request():
        try:
            conn = http.client.HTTPSConnection("social-download-all-in-one.p.rapidapi.com", timeout=2.5)
            
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
            
            response_data = json.loads(data.decode("utf-8"))
            universal_logger.info(f"API Response received for URL: {url}")
            return response_data
        except Exception as e:
            universal_logger.error(f"API request failed for URL {url}: {e}")
            return None
    
    # Run in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        return loop.run_in_executor(executor, _make_request)

def _extract_video_metadata(video_path: str):
    """Fast stub: avoid ffmpeg/ffprobe calls and thumbnail generation.
    Returns placeholder metadata to minimize pre-upload overhead."""
    try:
        return {
            'width': 0,
            'height': 0,
            'duration': 0,
            'thumbnail': None
        }
    except Exception:
        return {
            'width': 0,
            'height': 0,
            'duration': 0,
            'thumbnail': None
        }

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
        # Use asyncio.wait_for with 2.5 second timeout
        return await asyncio.wait_for(_og_request_sync(url), timeout=2.5)
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
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36'
            }
            resp = requests.get(url, headers=headers, timeout=2.0)
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
        
        # Send initial status message
        status_msg = await message.reply_text(f"🔄 در حال پردازش لینک {platform}...")
        
        # Advertisement will be handled later in the process
        
        # Get data from API with optimized parallel approach
        await status_msg.edit_text(f"📡 در حال دریافت اطلاعات از {platform}...")
        api_data = None
        fallback_media = None
        
        # Create tasks for API and fallback (if Instagram)
        tasks = []
        api_task = asyncio.create_task(get_universal_data_from_api(url))
        tasks.append(("api", api_task))
        
        # Only add fallback for Instagram
        if platform == "Instagram":
            fallback_task = asyncio.create_task(_fetch_og_media(url))
            tasks.append(("fallback", fallback_task))
        
        # Wait for first successful result
        completed_tasks = []
        try:
            for task_name, task in tasks:
                try:
                    result = await task
                    completed_tasks.append((task_name, result))
                    
                    # Check if API result is valid
                    if task_name == "api" and result:
                        invalid = (result.get("error", False) or 
                                 result.get("data", {}).get("error", False) or 
                                 not result.get("medias"))
                        if not invalid:
                            api_data = result
                            # Cancel remaining tasks
                            for remaining_name, remaining_task in tasks:
                                if remaining_name != task_name and not remaining_task.done():
                                    remaining_task.cancel()
                            break
                    
                    # Check if fallback result is valid
                    elif task_name == "fallback" and result:
                        fallback_media = result
                        # If API hasn't succeeded yet, use fallback
                        if not api_data:
                            # Cancel API task if still running
                            for remaining_name, remaining_task in tasks:
                                if remaining_name == "api" and not remaining_task.done():
                                    remaining_task.cancel()
                            break
                            
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    _log(f"[UNIV] {task_name} task failed: {e}")
                    
        except Exception as e:
            _log(f"[UNIV] Error in parallel API/fallback: {e}")
        
        # Check results
        if not api_data and not fallback_media:
            error_msg = "خطا در دریافت اطلاعات"
            if completed_tasks:
                for task_name, result in completed_tasks:
                    if result and isinstance(result, dict):
                        error_msg = result.get("message", error_msg)
                        break
            await status_msg.edit_text(f"❌ {error_msg} از {platform}")
            return

        # Debug logging for API response
        _log(f"[UNIV] API data check: api_data exists={api_data is not None}")
        if api_data:
            _log(f"[UNIV] API data keys: {list(api_data.keys())}")
            _log(f"[UNIV] Has medias key: {'medias' in api_data}")
            if 'medias' in api_data:
                _log(f"[UNIV] Medias count: {len(api_data.get('medias', []))}")
                _log(f"[UNIV] Medias content: {api_data.get('medias', [])}")

        # If API returned nothing after retries, expand fallback to include Instagram
        if (not api_data or "medias" not in api_data or not api_data.get("medias")) and platform in ("Pinterest", "Imgur", "Tumblr", "Instagram"):
            _log(f"[UNIV] Entering fallback mode for {platform}")
            await status_msg.edit_text(f"📡 API چیزی برنگرداند؛ تلاش برای استخراج مستقیم {platform}...")
            og = _fetch_og_media(url)
            if og:
                fallback_media = og
            else:
                err_msg = last_api_error_message or "لطفاً لینک را بررسی کنید."
                await status_msg.edit_text(f"❌ خطا در دریافت اطلاعات از {platform}: {err_msg}")
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
                return

            # Create filename (Windows-safe)
            safe_title_src = title or selected_media.get('title') or platform
            filename = _safe_filename(safe_title_src, file_extension)

            # Download file - single status message, no updates during retry
            await status_msg.edit_text(f"📥 در حال دانلود از {platform}...")
            t_dl_start = time.perf_counter()
            # Retry download up to 3 times (silent retries)
            download_result = None
            last_error = None
            for attempt in range(3):
                try:
                    download_result = await download_file_simple(download_url, filename)
                    break
                except Exception as e:
                    last_error = e
                    _log(f"[UNIV] Download attempt {attempt+1}/3 failed: {e}")
                    if attempt < 2:  # Only sleep if not last attempt
                        await asyncio.sleep(1.0)
            t_dl_end = time.perf_counter()
            _log(f"[UNIV] Download took {(t_dl_end - t_dl_start):.2f}s | size={os.path.getsize(filename) if os.path.exists(filename) else 'NA'}")

            # Extract file_path from tuple (file_path, total_size)
            if isinstance(download_result, tuple):
                file_path, total_size = download_result
            else:
                file_path = download_result

            if not file_path or not os.path.exists(file_path):
                err_txt = f"❌ خطا در دانلود فایل از {platform}."
                if last_error:
                    err_txt += f"\nجزئیات: {last_error}"
                await status_msg.edit_text(err_txt)
                return
        else:
            # Album download for Instagram: download all supported medias
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
                            dl_res = await download_file_simple(murl, mfilename)
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
                return

            # Ensure caption fields exist for album branch
            media_type = "album"
            quality = "Unknown"
            duration_sec = 0
        
        # Prepare simplified caption (only 3 essential lines)
        caption = f"📸 پیج دانلود شده: {author}\n"
        caption += f"⏱ زمان ویدیو: {duration_sec} ثانیه\n"
        caption += f"🎞 کیفیت: {quality}"
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
            await send_advertisement(client, message.chat.id)
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
                        
                        if idx == 1:
                            media_group.append(InputMediaVideo(
                                media=mp, 
                                caption=caption,
                                width=first_video_meta.get('width', 0) or None,
                                height=first_video_meta.get('height', 0) or None,
                                duration=first_video_meta.get('duration', 0) or None,
                                thumb=first_video_meta.get('thumbnail')
                            ))
                        else:
                            # Reuse metadata from first video for performance
                            media_group.append(InputMediaVideo(
                                media=mp,
                                width=first_video_meta.get('width', 0) or None,
                                height=first_video_meta.get('height', 0) or None,
                                duration=first_video_meta.get('duration', 0) or None,
                                thumb=first_video_meta.get('thumbnail')
                            ))
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
                if media_type in ("image", "photo") or file_extension.lower() in image_exts or platform.lower() in ("pinterest", "imgur"):
                    # Retry photo upload up to 3 times
                    t_up_start = time.perf_counter()
                    last_upload_error = None
                    for attempt in range(3):
                        try:
                            await client.send_photo(
                                chat_id=message.chat.id,
                                photo=file_path,
                                caption=caption
                            )
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
                    video_width = None
                    video_height = None
                    video_duration = duration_sec
                    video_thumb = None
                    
                    # Check if we have width/height from API response
                    if hasattr(data, 'get') and data.get('width') and data.get('height'):
                        video_width = data.get('width')
                        video_height = data.get('height')
                        _log(f"[UNIV] Using API metadata: {video_width}x{video_height}")
                    else:
                        # Fallback to ffprobe only if API doesn't provide dimensions
                        video_meta = _extract_video_metadata(file_path)
                        video_width = video_meta.get('width', 0) or None
                        video_height = video_meta.get('height', 0) or None
                        video_thumb = video_meta.get('thumbnail')
                        _log(f"[UNIV] Using ffprobe metadata: {video_width}x{video_height}")
                    
                    t_up_start = time.perf_counter()
                    last_upload_error = None
                    for attempt in range(3):
                        try:
                            await client.send_video(
                                chat_id=message.chat.id,
                                video=file_path,
                                caption=caption,
                                duration=video_duration,
                                width=video_width,
                                height=video_height,
                                thumb=video_thumb,
                                supports_streaming=True
                            )
                            last_upload_error = None
                            break
                        except Exception as e:
                            last_upload_error = e
                            _log(f"[UNIV] send_video attempt {attempt+1}/3 failed: {e}")
                            await asyncio.sleep(0.8)
                    if last_upload_error:
                        raise last_upload_error
                    t_up_end = time.perf_counter()
                else:
                    t_up_start = time.perf_counter()
                    last_upload_error = None
                    for attempt in range(3):
                        try:
                            await client.send_audio(
                                chat_id=message.chat.id,
                                audio=file_path,
                                caption=caption,
                                duration=duration_sec,
                                title=title,
                                performer=author
                            )
                            last_upload_error = None
                            break
                        except Exception as e:
                            last_upload_error = e
                            _log(f"[UNIV] send_audio attempt {attempt+1}/3 failed: {e}")
                            await asyncio.sleep(0.8)
                    if last_upload_error:
                        raise last_upload_error
                    t_up_end = time.perf_counter()
            _log(f"[UNIV] Upload took {(t_up_end - t_up_start):.2f}s")
        except Exception as upload_error:
            print(f"Upload error: {upload_error}")
            try:
                await client.send_document(
                    chat_id=message.chat.id,
                    document=file_path if not is_album else album_files[0][1],
                    caption=_safe_caption(caption, max_len=950)
                )
            except Exception as fallback_error:
                print(f"Fallback upload error: {fallback_error}")
                await message.reply_text(f"❌ خطا در ارسال فایل از {platform}: {str(upload_error)}")
                return
        
        # Delete status message safely
        try:
            await status_msg.delete()
            status_msg = None  # Mark as deleted
        except Exception:
            pass
        
        # Send advertisement after content if enabled and position is 'after'
        if ad_enabled and ad_position == 'after':
            await asyncio.sleep(1)  # Wait 1 second after upload
            await send_advertisement(client, message.chat.id)
        
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
            
    except Exception as e:
        error_msg = str(e)
        print(f"Universal download error: {error_msg}")
        
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