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

def get_universal_data_from_api(url):
    """Get media data from the universal API for Spotify, TikTok, and SoundCloud"""
    try:
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
        
        response_data = json.loads(data.decode("utf-8"))
        universal_logger.info(f"API Response received for URL: {url}")
        universal_logger.debug(f"API Response data: {response_data}")
        return response_data
    except Exception as e:
        universal_logger.error(f"API Error for URL {url}: {e}")
        return None

def _extract_video_metadata(video_path: str):
    """Extract video metadata including dimensions and conditionally generate thumbnail"""
    try:
        # Try to get video info using ffprobe (if available)
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                video_stream = None
                for stream in data.get('streams', []):
                    if stream.get('codec_type') == 'video':
                        video_stream = stream
                        break
                
                if video_stream:
                    width = int(video_stream.get('width', 0))
                    height = int(video_stream.get('height', 0))
                    duration = float(video_stream.get('duration', 0))
                    
                    # Only generate thumbnail for larger files (>10MB) to improve performance
                    file_size = os.path.getsize(video_path) if os.path.exists(video_path) else 0
                    thumbnail_path = None
                    
                    if file_size > 10 * 1024 * 1024:  # 10MB threshold
                        thumbnail_path = video_path.rsplit('.', 1)[0] + '_thumb.jpg'
                        thumb_cmd = [
                            'ffmpeg', '-i', video_path, '-ss', '00:00:01', '-vframes', '1', 
                            '-y', thumbnail_path
                        ]
                        thumb_result = subprocess.run(thumb_cmd, capture_output=True, timeout=10)
                        
                        if thumb_result.returncode != 0 or not os.path.exists(thumbnail_path):
                            thumbnail_path = None
                    
                    return {
                        'width': width,
                        'height': height,
                        'duration': int(duration),
                        'thumbnail': thumbnail_path
                    }
        except Exception:
            pass
        
        # Fallback: try to get basic info from file
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

def _fetch_og_media(url: str):
    """Fallback: fetch media via OpenGraph tags for image/video-centric sites (Pinterest/Imgur/Tumblr)."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=12)
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
        universal_logger.warning(f"OG fetch fallback failed for {url}: {e}")
        return None

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
        
        # Get data from API
        await status_msg.edit_text(f"📡 در حال دریافت اطلاعات از {platform}...")
        t_api_start = time.perf_counter()
        api_data = get_universal_data_from_api(url)
        t_api_end = time.perf_counter()
        _log(f"[UNIV] API fetch took {(t_api_end - t_api_start):.2f}s")

        # Fallback holder
        fallback_media = None

        # If API errors, try OG fallback for Instagram before failing
        if api_data and (api_data.get("error", False) or api_data.get("data", {}).get("error", False)):
            error_message = api_data.get("message", "خطای نامشخص")
            if platform == "Instagram":
                await status_msg.edit_text("📡 API خطا داد؛ تلاش برای استخراج مستقیم Instagram...")
                og = _fetch_og_media(url)
                if og:
                    fallback_media = og
                else:
                    await status_msg.edit_text(f"❌ خطا در دریافت اطلاعات از {platform}: {error_message}")
                    return
            else:
                await status_msg.edit_text(f"❌ خطا در دریافت اطلاعات از {platform}: {error_message}")
                return

        # Debug logging for API response
        _log(f"[UNIV] API data check: api_data exists={api_data is not None}")
        if api_data:
            _log(f"[UNIV] API data keys: {list(api_data.keys())}")
            _log(f"[UNIV] Has medias key: {'medias' in api_data}")
            if 'medias' in api_data:
                _log(f"[UNIV] Medias count: {len(api_data.get('medias', []))}")
                _log(f"[UNIV] Medias content: {api_data.get('medias', [])}")

        # If API returned nothing, expand fallback to include Instagram
        if (not api_data or "medias" not in api_data or not api_data.get("medias")) and platform in ("Pinterest", "Imgur", "Tumblr", "Instagram"):
            _log(f"[UNIV] Entering fallback mode for {platform}")
            await status_msg.edit_text(f"📡 API چیزی برنگرداند؛ تلاش برای استخراج مستقیم {platform}...")
            og = _fetch_og_media(url)
            if og:
                fallback_media = og
            else:
                await status_msg.edit_text(f"❌ خطا در دریافت اطلاعات از {platform}. لطفاً لینک را بررسی کنید.")
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

            # Create filename
            safe_title_src = title or selected_media.get('title') or platform
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', str(safe_title_src)[:50])
            filename = f"{safe_title}.{file_extension}"

            # Download file
            await status_msg.edit_text(f"⬇️ در حال دانلود از {platform}...")
            t_dl_start = time.perf_counter()
            download_result = await download_file_simple(download_url, filename)
            t_dl_end = time.perf_counter()
            _log(f"[UNIV] Download took {(t_dl_end - t_dl_start):.2f}s | size={os.path.getsize(filename) if os.path.exists(filename) else 'NA'}")

            # Extract file_path from tuple (file_path, total_size)
            if isinstance(download_result, tuple):
                file_path, total_size = download_result
            else:
                file_path = download_result

            if not file_path or not os.path.exists(file_path):
                await status_msg.edit_text(f"❌ خطا در دانلود فایل از {platform}.")
                return
        else:
            # Album download for Instagram: download all supported medias
            await status_msg.edit_text(f"⬇️ در حال دانلود {len(medias)} آیتم از {platform}...")
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
                safe_title = re.sub(r'[<>:"/\\|?*]', '_', str(safe_title_src)[:40])
                mfilename = f"{safe_title}_{idx}.{mext}"
                try:
                    t_dl_start_i = time.perf_counter()
                    dl_res = await download_file_simple(murl, mfilename)
                    t_dl_end_i = time.perf_counter()
                    _log(f"[UNIV] Item {idx} download took {(t_dl_end_i - t_dl_start_i):.2f}s | type={mtype}")
                    if isinstance(dl_res, tuple):
                        mp, _ = dl_res
                    else:
                        mp = dl_res
                    if mp and os.path.exists(mp) and os.path.getsize(mp) > 0:
                        album_files.append((mtype, mp))
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
        
        # Prepare caption (trim to safe length)
        caption = f"🎵 **{title}**\n"
        caption += f"👤 **نویسنده:** {author}\n"
        caption += f"⏱️ **مدت زمان:** {duration_sec} ثانیه\n"
        caption += f"🔗 **پلتفرم:** {platform}\n"
        caption += f"📊 **کیفیت:** {quality}\n"
        caption += f"📁 **نوع:** {media_type.title()}"
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
            t_up_start = time.perf_counter()
            # Decide upload method based on media type and extension
            image_exts = ["jpg", "jpeg", "png", "webp"]
            video_exts = ["mp4", "avi", "mov", "mkv", "webm"]

            if is_album:
                media_group = []
                for idx, (mtype, mp) in enumerate(album_files, start=1):
                    if mtype in ("image", "photo"):
                        if idx == 1:
                            media_group.append(InputMediaPhoto(media=mp, caption=caption))
                        else:
                            media_group.append(InputMediaPhoto(media=mp))
                    elif mtype == "video":
                        # Extract video metadata for better upload performance
                        video_meta = _extract_video_metadata(mp)
                        if idx == 1:
                            media_group.append(InputMediaVideo(
                                media=mp, 
                                caption=caption,
                                width=video_meta.get('width', 0) or None,
                                height=video_meta.get('height', 0) or None,
                                duration=video_meta.get('duration', 0) or None,
                                thumb=video_meta.get('thumbnail')
                            ))
                        else:
                            media_group.append(InputMediaVideo(
                                media=mp,
                                width=video_meta.get('width', 0) or None,
                                height=video_meta.get('height', 0) or None,
                                duration=video_meta.get('duration', 0) or None,
                                thumb=video_meta.get('thumbnail')
                            ))
                await client.send_media_group(
                    chat_id=message.chat.id, 
                    media=media_group,
                    progress=_progress_callback
                )
            else:
                if media_type in ("image", "photo") or file_extension.lower() in image_exts or platform.lower() in ("pinterest", "imgur"):
                    await client.send_photo(
                        chat_id=message.chat.id,
                        photo=file_path,
                        caption=caption,
                        progress=_progress_callback
                    )
                elif (media_type == "video" or file_extension.lower() in video_exts or platform.lower() == "tiktok"):
                    # Extract video metadata for better upload performance
                    video_meta = _extract_video_metadata(file_path)
                    await client.send_video(
                        chat_id=message.chat.id,
                        video=file_path,
                        caption=caption,
                        duration=video_meta.get('duration', duration_sec) or duration_sec,
                        width=video_meta.get('width', 0) or None,
                        height=video_meta.get('height', 0) or None,
                        thumb=video_meta.get('thumbnail'),
                        supports_streaming=True,
                        progress=_progress_callback
                    )
                else:
                    await client.send_audio(
                        chat_id=message.chat.id,
                        audio=file_path,
                        caption=caption,
                        duration=duration_sec,
                        title=title,
                        performer=author,
                        progress=_progress_callback
                    )
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
        
        # Increment download count
        now_str = _dt.now().isoformat(timespec='seconds')
        db.increment_request(user_id, now_str)
        
        # Clean up downloaded file(s) and thumbnails
        try:
            if not is_album:
                os.remove(file_path)
                # Clean up thumbnail if exists
                thumb_path = file_path.rsplit('.', 1)[0] + '_thumb.jpg'
                if os.path.exists(thumb_path):
                    os.remove(thumb_path)
            else:
                for _, fp in album_files:
                    try:
                        os.remove(fp)
                        # Clean up thumbnail if exists
                        thumb_path = fp.rsplit('.', 1)[0] + '_thumb.jpg'
                        if os.path.exists(thumb_path):
                            os.remove(thumb_path)
                    except Exception:
                        pass
        except Exception:
            pass

        t_end = time.perf_counter()
        _log(f"[UNIV] Total processing time: {(t_end - t0):.2f}s")
            
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