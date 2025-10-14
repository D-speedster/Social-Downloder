import os
import json
import time
import shutil
import urllib.request
import requests
from plugins import constant

PATH = constant.PATH

async def send_advertisement(client, user_id: int):
    """Send advertisement to user based on database settings (shared utility)."""
    try:
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
            await client.send_message(chat_id=user_id, text=content)
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
                                await client.send_photo(chat_id=user_id, photo=temp_path, caption=caption)
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
                    await client.send_photo(chat_id=user_id, photo=file_id, caption=caption)
            except Exception:
                if caption:
                    await client.send_message(chat_id=user_id, text=f"📢 تبلیغ\n\n{caption}")
        elif content_type == 'video' and file_id:
            await client.send_video(chat_id=user_id, video=file_id, caption=caption)
        elif content_type == 'gif' and file_id:
            await client.send_animation(chat_id=user_id, animation=file_id, caption=caption)
        elif content_type == 'sticker' and file_id:
            await client.send_sticker(chat_id=user_id, sticker=file_id)
    except Exception:
        # Silent fail to avoid interrupting main flow
        pass

async def download_file_simple(url, file_path):
    """Simple file download without progress updates for better performance (shared)."""
    try:
        with urllib.request.urlopen(url) as response:
            total_size = int(response.headers.get('Content-Length', 0))
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(response, f)
        return file_path, total_size
    except Exception as e:
        print(f"Download error: {e}")
        raise e