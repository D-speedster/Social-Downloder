import subprocess
import json
import os

# 🔥 تابع جدید برای استخراج metadata
def extract_video_metadata(file_path: str) -> dict:
    """
    استخراج metadata کامل از ویدیو با ffprobe
    """
    try:
        # پیدا کردن ffprobe
        ffprobe_path = os.environ.get('FFMPEG_PATH', 'ffmpeg').replace('ffmpeg', 'ffprobe')
        if not os.path.exists(ffprobe_path):
            ffprobe_path = shutil.which('ffprobe') or 'ffprobe'
        
        # اجرای ffprobe
        cmd = [
            ffprobe_path, '-v', 'error',
            '-show_entries', 'format=duration:stream=width,height,codec_type,duration',
            '-of', 'json',
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=10)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            
            # استخراج اطلاعات
            metadata = {
                'duration': 0,
                'width': 0,
                'height': 0,
                'has_video': False,
                'has_audio': False
            }
            
            # مدت زمان از format
            format_data = data.get('format', {})
            if 'duration' in format_data:
                try:
                    metadata['duration'] = int(float(format_data['duration']))
                except:
                    pass
            
            # ابعاد و codec از streams
            streams = data.get('streams', [])
            for stream in streams:
                codec_type = stream.get('codec_type', '')
                
                if codec_type == 'video':
                    metadata['has_video'] = True
                    if 'width' in stream and not metadata['width']:
                        metadata['width'] = int(stream['width'])
                    if 'height' in stream and not metadata['height']:
                        metadata['height'] = int(stream['height'])
                    # مدت زمان از stream اگر در format نبود
                    if not metadata['duration'] and 'duration' in stream:
                        try:
                            metadata['duration'] = int(float(stream['duration']))
                        except:
                            pass
                
                elif codec_type == 'audio':
                    metadata['has_audio'] = True
            
            print(f"📊 Metadata extracted: {metadata}")
            return metadata
        else:
            print(f"❌ ffprobe failed: {result.stderr}")
            return {}
            
    except Exception as e:
        print(f"❌ Metadata extraction error: {e}")
        return {}


# 🔥 تابع جدید برای ساخت thumbnail
def generate_thumbnail(file_path: str) -> str:
    """
    ساخت thumbnail از ویدیو
    """
    try:
        ffmpeg_path = os.environ.get('FFMPEG_PATH', 'ffmpeg')
        if not os.path.exists(ffmpeg_path):
            ffmpeg_path = shutil.which('ffmpeg') or 'ffmpeg'
        
        # مسیر thumbnail
        thumb_path = file_path.rsplit('.', 1)[0] + '_thumb.jpg'
        
        # ساخت thumbnail از ثانیه 2
        cmd = [
            ffmpeg_path, '-y',
            '-ss', '2',  # ثانیه 2
            '-i', file_path,
            '-vframes', '1',
            '-vf', 'scale=320:-1',
            '-q:v', '2',
            thumb_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=15)
        
        if result.returncode == 0 and os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0:
            print(f"✅ Thumbnail created: {thumb_path}")
            return thumb_path
        else:
            print(f"❌ Thumbnail generation failed")
            return None
            
    except Exception as e:
        print(f"❌ Thumbnail error: {e}")
        return None


# 🔥 تابع smart_upload_strategy اصلاح شده
async def smart_upload_strategy(client, chat_id: int, file_path: str, media_type: str, **kwargs) -> bool:
    """
    Smart upload strategy with COMPLETE metadata support
    Returns True if upload was successful, False otherwise
    """
    file_size = os.path.getsize(file_path)
    file_size_mb = file_size / (1024 * 1024)
    
    # استخراج progress callback از kwargs
    progress_callback = kwargs.pop('progress', None)
    
    # Calculate optimal delay for throttling
    upload_delay = calculate_upload_delay(file_size_mb, 1)
    
    # 🔥 استخراج metadata برای ویدیو
    metadata = {}
    thumb_path = None
    
    if media_type == "video":
        print("📊 استخراج metadata از ویدیو...")
        metadata = extract_video_metadata(file_path)
        
        # ساخت thumbnail
        print("🖼️ ساخت thumbnail...")
        thumb_path = generate_thumbnail(file_path)
    
    # Define upload function for throttled retry
    async def perform_upload():
        # For small files (< 10MB), try memory streaming first
        if file_size_mb < 10:
            try:
                with open(file_path, 'rb') as f:
                    buffer = StreamBuffer(os.path.basename(file_path))
                    buffer.write(f.read())
                    buffer.seek(0)
                    
                    # اضافه کردن progress callback اگر موجود باشد
                    upload_kwargs = kwargs.copy()
                    if progress_callback:
                        upload_kwargs['progress'] = progress_callback
                    
                    # 🔥 اضافه کردن metadata
                    if media_type == "video":
                        upload_kwargs['supports_streaming'] = True
                        if metadata.get('duration'):
                            upload_kwargs['duration'] = metadata['duration']
                        if metadata.get('width'):
                            upload_kwargs['width'] = metadata['width']
                        if metadata.get('height'):
                            upload_kwargs['height'] = metadata['height']
                        if thumb_path:
                            upload_kwargs['thumb'] = thumb_path
                    
                    if media_type == "video":
                        result = await client.send_video(chat_id=chat_id, video=buffer, **upload_kwargs)
                    elif media_type == "photo":
                        result = await client.send_photo(chat_id=chat_id, photo=buffer, **upload_kwargs)
                    elif media_type == "audio":
                        result = await client.send_audio(chat_id=chat_id, audio=buffer, **upload_kwargs)
                    else:
                        result = await client.send_document(chat_id=chat_id, document=buffer, **upload_kwargs)
                    
                    buffer.close()
                    return result
            except Exception as e:
                print(f"Memory upload failed, falling back to file upload: {e}")
        
        # File-based upload with progress callback
        upload_kwargs = kwargs.copy()
        if progress_callback:
            upload_kwargs['progress'] = progress_callback
        
        # 🔥 اضافه کردن metadata برای file-based upload
        if media_type == "video":
            upload_kwargs['supports_streaming'] = True
            if metadata.get('duration'):
                upload_kwargs['duration'] = metadata['duration']
                print(f"✅ Duration set: {metadata['duration']}s")
            if metadata.get('width'):
                upload_kwargs['width'] = metadata['width']
                print(f"✅ Width set: {metadata['width']}px")
            if metadata.get('height'):
                upload_kwargs['height'] = metadata['height']
                print(f"✅ Height set: {metadata['height']}px")
            if thumb_path:
                upload_kwargs['thumb'] = thumb_path
                print(f"✅ Thumbnail set: {thumb_path}")
        
        # Add throttling delay before upload
        if upload_delay > 0:
            await asyncio.sleep(upload_delay)
        
        # تنظیمات بهینه برای آپلود فایل
        if media_type == "video":
            return await client.send_video(chat_id=chat_id, video=file_path, **upload_kwargs)
        elif media_type == "photo":
            return await client.send_photo(chat_id=chat_id, photo=file_path, **upload_kwargs)
        elif media_type == "audio":
            return await client.send_audio(chat_id=chat_id, audio=file_path, **upload_kwargs)
        else:
            return await client.send_document(chat_id=chat_id, document=file_path, **upload_kwargs)
    
    # Use throttled upload with retry
    try:
        await throttled_upload_with_retry(perform_upload, max_retries=3, base_delay=upload_delay)
        
        # 🔥 حذف thumbnail بعد از آپلود
        if thumb_path and os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
                print("🗑️ Thumbnail cleaned up")
            except:
                pass
        
        return True
    except Exception as e:
        print(f"Smart upload failed after all retries: {e}")
        
        # حذف thumbnail در صورت خطا
        if thumb_path and os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except:
                pass
        
        return False