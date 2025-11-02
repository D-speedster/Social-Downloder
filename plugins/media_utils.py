import os
import json
import time
import shutil
import urllib.request
import requests
import aiohttp
import asyncio
from plugins import constant

PATH = constant.PATH
AUTO_DELETE_SECONDS = 120

async def _delete_after_delay(message, delay=120):
    """Deletes a message after a specified delay."""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        # Message might have been deleted already
        pass

def send_advertisement(client, user_id: int):
    """Launches a background task to send an advertisement to the user without blocking."""
    async def _send_ad_task():
        try:
            try:
                from plugins.db_path_manager import db_path_manager
            except Exception:
                from .db_path_manager import db_path_manager
            json_db_path = db_path_manager.get_json_db_path()
            
            with open(json_db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            ad_settings = data.get('advertisement', {})
            if not ad_settings.get('enabled', False):
                return

            content_type = ad_settings.get('content_type', 'text')
            content = ad_settings.get('content', '')
            file_id = ad_settings.get('file_id', '')
            caption = ad_settings.get('caption', '')
            
            # New fields for enhanced advertisement
            button_text = ad_settings.get('button_text', '')
            button_url = ad_settings.get('button_url', '')
            disable_preview = ad_settings.get('disable_preview', True)  # Default: disable preview

            if content_type == 'text' and content:
                # Create inline keyboard if button is configured
                reply_markup = None
                if button_text and button_url:
                    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    reply_markup = InlineKeyboardMarkup([[
                        InlineKeyboardButton(button_text, url=button_url)
                    ]])
                
                msg = await client.send_message(
                    chat_id=user_id, 
                    text=content,
                    reply_markup=reply_markup,
                    disable_web_page_preview=disable_preview
                )
                asyncio.create_task(_delete_after_delay(msg))
            elif content_type == 'photo' and file_id:
                try:
                    if isinstance(file_id, str) and (file_id.startswith('http://') or file_id.startswith('https://')):
                        temp_name = f"ad_photo_{int(time.time())}.jpg"
                        temp_path = os.path.join(PATH, temp_name)
                        try:
                            resp = requests.get(file_id, stream=True, timeout=20)
                            if resp.status_code == 200:
                                with open(temp_path, 'wb') as f:
                                    for chunk in resp.iter_content(8192):
                                        if chunk:
                                            f.write(chunk)
                                if os.path.getsize(temp_path) > 0:
                                    msg = await client.send_photo(chat_id=user_id, photo=temp_path, caption=caption)
                                    asyncio.create_task(_delete_after_delay(msg))
                                else:
                                    raise Exception("Downloaded advertisement photo is empty")
                            else:
                                raise Exception(f"Ad photo download failed: status {resp.status_code}")
                        finally:
                            try:
                                if os.path.exists(temp_path):
                                    os.remove(temp_path)
                            except Exception:
                                pass
                    else:
                        # Create inline keyboard for photo
                        reply_markup = None
                        if button_text and button_url:
                            from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                            reply_markup = InlineKeyboardMarkup([[
                                InlineKeyboardButton(button_text, url=button_url)
                            ]])
                        
                        msg = await client.send_photo(
                            chat_id=user_id, 
                            photo=file_id, 
                            caption=caption,
                            reply_markup=reply_markup
                        )
                        asyncio.create_task(_delete_after_delay(msg))
                except Exception:
                    if caption:
                        # Fallback with button if available
                        reply_markup = None
                        if button_text and button_url:
                            from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                            reply_markup = InlineKeyboardMarkup([[
                                InlineKeyboardButton(button_text, url=button_url)
                            ]])
                        
                        msg = await client.send_message(
                            chat_id=user_id, 
                            text=f"📢 تبلیغ\n\n{caption}",
                            reply_markup=reply_markup,
                            disable_web_page_preview=disable_preview
                        )
                        asyncio.create_task(_delete_after_delay(msg))
            elif content_type == 'video' and file_id:
                # Create inline keyboard for video
                reply_markup = None
                if button_text and button_url:
                    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    reply_markup = InlineKeyboardMarkup([[
                        InlineKeyboardButton(button_text, url=button_url)
                    ]])
                
                msg = await client.send_video(
                    chat_id=user_id, 
                    video=file_id, 
                    caption=caption,
                    reply_markup=reply_markup
                )
                asyncio.create_task(_delete_after_delay(msg))
                
            elif content_type == 'gif' and file_id:
                # Create inline keyboard for gif
                reply_markup = None
                if button_text and button_url:
                    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    reply_markup = InlineKeyboardMarkup([[
                        InlineKeyboardButton(button_text, url=button_url)
                    ]])
                
                msg = await client.send_animation(
                    chat_id=user_id, 
                    animation=file_id, 
                    caption=caption,
                    reply_markup=reply_markup
                )
                asyncio.create_task(_delete_after_delay(msg))
                
            elif content_type == 'sticker' and file_id:
                # Stickers don't support captions or buttons, send separately if needed
                msg = await client.send_sticker(chat_id=user_id, sticker=file_id)
                asyncio.create_task(_delete_after_delay(msg))
                
                # Send caption with button separately if available
                if (caption or (button_text and button_url)):
                    reply_markup = None
                    if button_text and button_url:
                        from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                        reply_markup = InlineKeyboardMarkup([[
                            InlineKeyboardButton(button_text, url=button_url)
                        ]])
                    
                    text_msg = await client.send_message(
                        chat_id=user_id,
                        text=caption or "📢 تبلیغ",
                        reply_markup=reply_markup,
                        disable_web_page_preview=disable_preview
                    )
                    asyncio.create_task(_delete_after_delay(text_msg))
                    
            elif content_type == 'audio' and file_id:
                # Create inline keyboard for audio
                reply_markup = None
                if button_text and button_url:
                    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    reply_markup = InlineKeyboardMarkup([[
                        InlineKeyboardButton(button_text, url=button_url)
                    ]])
                
                msg = await client.send_audio(
                    chat_id=user_id, 
                    audio=file_id, 
                    caption=caption,
                    reply_markup=reply_markup
                )
                asyncio.create_task(_delete_after_delay(msg))
        except Exception:
            # Silent fail to avoid interrupting main flow
            pass

    asyncio.create_task(_send_ad_task())

async def download_file_simple(url, file_path):
    """Simple file download without progress updates for better performance (shared)."""
    try:
        # Create request with Instagram-optimized headers to avoid 403 errors
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'video',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'cross-site',
            'Referer': 'https://www.instagram.com/',
            'Origin': 'https://www.instagram.com'
        })
        
        with urllib.request.urlopen(req) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(response, f)
        return file_path, total_size
    except Exception as e:
        print(f"Download error: {e}")
        raise e

async def download_stream_to_file(url, out_path, chunk_size=64*1024, headers=None):
    """
    Async file download using aiohttp for better performance and non-blocking I/O.
    Returns (file_path, total_size) for compatibility with download_file_simple.
    """
    try:
        # تشخیص platform برای انتخاب headers مناسب
        platform_headers = {
            'spotify': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'audio/mpeg,audio/ogg,audio/wav,audio/*;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'audio',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site'
            },
            'tiktok': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
                'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'video',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site'
            },
            'instagram': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
                'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'video',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site',
                'Referer': 'https://www.instagram.com/',
                'Origin': 'https://www.instagram.com'
            }
        }
        
        # Use custom headers if provided
        if headers is None:
            # تشخیص platform از URL
            if 'spotify' in url.lower() or 'zm.io.vn' in url.lower():
                headers = platform_headers['spotify']
            elif 'tiktok' in url.lower():
                headers = platform_headers['tiktok']
            elif 'instagram' in url.lower() or 'cdninstagram' in url.lower() or 'fbcdn.net' in url.lower():
                headers = platform_headers['instagram']
            else:
                # Default headers برای سایر platformها
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': '*/*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive'
                }
        
        # تنظیمات timeout بهتر برای platformهای مختلف
        if 'spotify' in url.lower() or 'zm.io.vn' in url.lower():
            timeout = aiohttp.ClientTimeout(total=60, connect=15)  # timeout بیشتر برای Spotify
        else:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        # تلاش چندباره برای دانلود در صورت خطاهای سرور
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers=headers, allow_redirects=True) as response:
                        # بررسی دقیق‌تر status code
                        if response.status == 403:
                            raise Exception(f"403 Forbidden: دسترسی به فایل محدود شده است")
                        elif response.status == 404:
                            raise Exception(f"404 Not Found: فایل یافت نشد")
                        elif response.status == 429:
                            raise Exception(f"429 Too Many Requests: تعداد درخواست‌ها زیاد است")
                        elif response.status in [502, 503, 504]:
                            # خطاهای سرور - قابل تلاش مجدد
                            if attempt < max_retries - 1:
                                print(f"Server error {response.status}, retrying in {2 * (attempt + 1)} seconds...")
                                await asyncio.sleep(2 * (attempt + 1))
                                continue
                            else:
                                raise Exception(f"HTTP {response.status}: سرور در دسترس نیست")
                        elif response.status >= 400:
                            raise Exception(f"HTTP {response.status}: خطا در دریافت فایل")
                        
                        response.raise_for_status()
                        
                        # Get content length
                        total_size = int(response.headers.get('Content-Length', 0))
                        
                        # بررسی اینکه آیا فایل خالی است
                        if total_size == 0:
                            # تلاش برای دانلود حتی بدون Content-Length
                            print(f"Warning: No Content-Length header, attempting download anyway")
                        
                        # Stream download to file
                        downloaded_size = 0
                        with open(out_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(chunk_size):
                                if not chunk:
                                    break
                                f.write(chunk)
                                downloaded_size += len(chunk)
                        
                        # بررسی اینکه آیا فایل دانلود شده است
                        if downloaded_size == 0:
                            if attempt < max_retries - 1:
                                print(f"Empty file downloaded, retrying in {2 * (attempt + 1)} seconds...")
                                await asyncio.sleep(2 * (attempt + 1))
                                continue
                            else:
                                raise Exception("فایل دانلود شده خالی است")
                        
                        # اگر total_size صفر بود، از downloaded_size استفاده کن
                        if total_size == 0:
                            total_size = downloaded_size
                        
                        print(f"Download completed: {downloaded_size} bytes")
                        return out_path, total_size
                        
            except aiohttp.ClientError as e:
                if attempt < max_retries - 1:
                    print(f"Network error, retrying in {2 * (attempt + 1)} seconds: {e}")
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                else:
                    raise Exception(f"Network error: {str(e)}")
            except asyncio.TimeoutError as e:
                if attempt < max_retries - 1:
                    print(f"Timeout error, retrying in {2 * (attempt + 1)} seconds...")
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                else:
                    raise Exception("Timeout: درخواست بیش از حد طول کشید")
                
    except aiohttp.ClientError as e:
        error_msg = f"Network error: {str(e)}"
        print(f"Async download error: {error_msg}")
        raise Exception(error_msg)
    except asyncio.TimeoutError as e:
        error_msg = "Timeout: درخواست بیش از حد طول کشید"
        print(f"Async download error: {error_msg}")
        raise Exception(error_msg)
    except Exception as e:
        error_msg = str(e)
        print(f"Async download error: {error_msg}")
        raise Exception(error_msg)