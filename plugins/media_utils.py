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

            if content_type == 'text' and content:
                msg = await client.send_message(chat_id=user_id, text=content)
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
                        msg = await client.send_photo(chat_id=user_id, photo=file_id, caption=caption)
                        asyncio.create_task(_delete_after_delay(msg))
                except Exception:
                    if caption:
                        msg = await client.send_message(chat_id=user_id, text=f"📢 تبلیغ\n\n{caption}")
                        asyncio.create_task(_delete_after_delay(msg))
            elif content_type == 'video' and file_id:
                msg = await client.send_video(chat_id=user_id, video=file_id, caption=caption)
                asyncio.create_task(_delete_after_delay(msg))
            elif content_type == 'gif' and file_id:
                msg = await client.send_animation(chat_id=user_id, animation=file_id, caption=caption)
                asyncio.create_task(_delete_after_delay(msg))
            elif content_type == 'sticker' and file_id:
                msg = await client.send_sticker(chat_id=user_id, sticker=file_id)
                asyncio.create_task(_delete_after_delay(msg))
            elif content_type == 'audio' and file_id:
                msg = await client.send_audio(chat_id=user_id, audio=file_id, caption=caption)
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
        # Use custom headers if provided, otherwise use Instagram-optimized headers
        if headers is None:
            headers = {
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
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                
                # Get content length
                total_size = int(response.headers.get('Content-Length', 0))
                
                # Stream download to file
                with open(out_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        f.write(chunk)
                
                return out_path, total_size
                
    except Exception as e:
        print(f"Async download error: {e}")
        raise e