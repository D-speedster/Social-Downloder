import shutil
import requests
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
import json
import os
import re
from pytube import YouTube
from plugins.start import step,join
from pyrogram.types import Message, CallbackQuery
from utils.util import convert_size,thubnail_maker
import random
from plugins import constant
from plugins.db_wrapper import DB
from datetime import datetime, timedelta
from yt_dlp import YoutubeDL
from pyrogram.errors import MessageNotModified
import subprocess
import sys

# Advertisement function
async def send_advertisement(client: Client, user_id: int):
    """Send advertisement to user based on database settings"""
    try:
        # Load advertisement settings from database
        with open('plugins/database.json', 'r', encoding='utf-8') as f:
            db_data = json.load(f)
        
        ad_settings = db_data.get('advertisement', {})
        
        # Check if advertisement is enabled
        if not ad_settings.get('enabled', False):
            return
        
        content_type = ad_settings.get('content_type')
        content = ad_settings.get('content')
        file_id = ad_settings.get('file_id')
        caption = ad_settings.get('caption', '')
        
        if content_type == 'text' and content:
            await client.send_message(user_id, content)
        elif content_type == 'photo' and file_id:
            try:
                await client.send_photo(user_id, file_id, caption=caption)
            except Exception as photo_error:
                print(f"Error sending photo: {photo_error}")
                # Fallback to text message if photo fails
                if caption:
                    await client.send_message(user_id, f"📢 تبلیغ\n\n{caption}")
        elif content_type == 'video' and file_id:
            await client.send_video(user_id, file_id, caption=caption)
        elif content_type == 'gif' and file_id:
            await client.send_animation(user_id, file_id, caption=caption)
        elif content_type == 'sticker' and file_id:
            await client.send_sticker(user_id, file_id)
        elif content_type == 'audio' and file_id:
            await client.send_audio(user_id, file_id, caption=caption)
            
    except Exception as e:
        print(f"Error sending advertisement: {e}")

previousprogress_download = 0
previousprogress_upload = 0


PATH = constant.PATH
txt =constant.TEXT
data = constant.DATA


@Client.on_callback_query(filters.regex(r'^(1|2|3|_file|_link|\d+(vd|vc)|download_video|download_audio)$'))
async def answer(client: Client, callback_query: CallbackQuery):
    # Get video info from step for yt-dlp handlers
    info = step.get('link', {})
    loop = asyncio.get_running_loop()

    # Helper to safely edit message text without raising on same content
    async def safe_edit_text(text: str, reply_markup=None, parse_mode=None):
        try:
            await callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except MessageNotModified:
            # Ignore if content is the same
            pass
        except Exception:
            # Silently ignore transient edit errors to keep workflow running
            pass

    # Small helper to escape URL for HTML attribute
    def _html_escape_url(u: str) -> str:
        try:
            return u.replace('&', '&amp;').replace('"', '&quot;')
        except Exception:
            return u
    
    if callback_query.data == 'download_video':
        # Direct video download with best quality
        if isinstance(info, dict) and 'formats' in info and info.get('title'):
            # Get best video format with audio, prioritizing 720p+ resolutions
            video_formats = [f for f in info['formats'] 
                            if f.get('vcodec', 'none') != 'none' and f.get('acodec', 'none') != 'none']
            
            if video_formats:
                # Prioritize formats with height >= 720, then >= 480, then any available
                hd_formats = [f for f in video_formats if (f.get('height', 0) or 0) >= 720]
                sd_formats = [f for f in video_formats if 480 <= (f.get('height', 0) or 0) < 720]
                
                if hd_formats:
                    # Sort HD formats by height (prefer 720p over higher if available)
                    hd_formats.sort(key=lambda x: abs((x.get('height', 0) or 0) - 720))
                    best_format = hd_formats[0]
                elif sd_formats:
                    # Sort SD formats by height (prefer higher resolution)
                    sd_formats.sort(key=lambda x: (x.get('height', 0) or 0), reverse=True)
                    best_format = sd_formats[0]
                else:
                    # Fallback to any available format
                    video_formats.sort(key=lambda x: (x.get('height', 0) or 0), reverse=True)
                    best_format = video_formats[0]
                
                # Set format info
                step['format_id'] = best_format['format_id']
                step['sort'] = "🎥 ویدیو"
                filesize = best_format.get('filesize') or best_format.get('filesize_approx')
                if not filesize:
                    duration = info.get('duration') or 0
                    kbps = best_format.get('tbr')
                    if duration and kbps:
                        try:
                            filesize = int((kbps * 1000 / 8) * duration)
                        except Exception:
                            filesize = None
                step['filesize'] = f"{(filesize/1024/1024):.2f} MB" if filesize else "نامشخص"
                step['ext'] = best_format.get('ext')
                step['size_bytes'] = int(filesize) if filesize else None
                step['format_url'] = best_format.get('url')
                
                # Show file or link options
                await callback_query.edit_message_caption(
                    caption=txt['file_or_link'].format(name=info.get('title'), sort=step['sort'], size=step['filesize']),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(txt['telegram_file'], callback_data='_file')],
                        [InlineKeyboardButton(txt['download_link'], callback_data='_link')]
                    ])
                )
            else:
                await callback_query.answer("❌ فرمت ویدیویی یافت نشد.", show_alert=True)
        else:
            await callback_query.answer("❌ اطلاعات ویدیو در دسترس نیست.", show_alert=True)
            
    elif callback_query.data == 'download_audio':
        # Direct audio download with best quality
        if isinstance(info, dict) and 'formats' in info and info.get('title'):
            # Get best audio format
            audio_formats = [f for f in info['formats'] 
                           if (f.get('vcodec', 'none') == 'none' and f.get('acodec', 'none') != 'none') or \
                              (f.get('vcodec', 'none') == 'none' and f.get('ext') in ['m4a', 'webm', 'mp3', 'ogg', 'aac', 'flac', 'wav'])]
            
            if audio_formats:
                # Sort by bitrate and get best quality
                audio_formats.sort(key=lambda x: (x.get('abr', 0) or x.get('tbr', 0) or 0), reverse=True)
                best_format = audio_formats[0]
                
                # Set format info
                step['format_id'] = best_format['format_id']
                step['sort'] = "🔊 صدا"
                filesize = best_format.get('filesize') or best_format.get('filesize_approx')
                if not filesize:
                    duration = info.get('duration') or 0
                    kbps = best_format.get('tbr') or best_format.get('abr')
                    if duration and kbps:
                        try:
                            filesize = int((kbps * 1000 / 8) * duration)
                        except Exception:
                            filesize = None
                step['filesize'] = f"{(filesize/1024/1024):.2f} MB" if filesize else "نامشخص"
                step['ext'] = best_format.get('ext')
                step['size_bytes'] = int(filesize) if filesize else None
                step['format_url'] = best_format.get('url')
                
                # Show file or link options
                await callback_query.edit_message_caption(
                    caption=txt['file_or_link'].format(name=info.get('title'), sort=step['sort'], size=step['filesize']),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(txt['telegram_file'], callback_data='_file')],
                        [InlineKeyboardButton(txt['download_link'], callback_data='_link')]
                    ])
                )
            else:
                await callback_query.answer("❌ فرمت صوتی یافت نشد.", show_alert=True)
        else:
            await callback_query.answer("❌ اطلاعات ویدیو در دسترس نیست.", show_alert=True)
            
    elif callback_query.data == '1':
        # Video formats (legacy)
        formats = []
        if isinstance(info, dict) and 'formats' in info and info.get('title'):
            # Using yt-dlp format selection
            video_formats = [f for f in info['formats'] 
                            if f.get('vcodec', 'none') != 'none' and f.get('acodec', 'none') != 'none']
            
            # Prioritize HD formats (720p+), then SD formats (480p+), then others
            hd_formats = [f for f in video_formats if (f.get('height', 0) or 0) >= 720]
            sd_formats = [f for f in video_formats if 480 <= (f.get('height', 0) or 0) < 720]
            low_formats = [f for f in video_formats if (f.get('height', 0) or 0) < 480]
            
            # Sort each category and combine
            hd_formats.sort(key=lambda x: (x.get('height', 0) or 0), reverse=True)
            sd_formats.sort(key=lambda x: (x.get('height', 0) or 0), reverse=True)
            low_formats.sort(key=lambda x: (x.get('height', 0) or 0), reverse=True)
            
            # Combine in priority order: HD first, then SD, then low quality
            prioritized_formats = hd_formats + sd_formats + low_formats
            
            # Get unique resolutions while maintaining priority order
            seen_resolutions = set()
            unique_formats = []
            for fmt in prioritized_formats:
                resolution = fmt.get('height', 0)
                if resolution and resolution not in seen_resolutions:
                    seen_resolutions.add(resolution)
                    unique_formats.append(fmt)
            
            # Create format buttons with proper size fallback (avoid 0B), estimate via tbr*duration when needed
            formats = []
            duration = info.get('duration') or 0
            for fmt in unique_formats:
                size_val = fmt.get('filesize') or fmt.get('filesize_approx')
                if not size_val and duration and (fmt.get('tbr') or 0):
                    try:
                        size_val = int((fmt.get('tbr') * 1000 / 8) * duration)  # tbr in kbps -> bytes
                    except Exception:
                        size_val = None
                size_str = convert_size(2, size_val) if size_val else 'نامشخص'
                btn_text = f"{fmt.get('height', 'N/A')}p - {size_str}"
                formats.append([InlineKeyboardButton(btn_text, callback_data=f"{fmt['format_id']}vd")])
        
        if not formats:
            await callback_query.answer("❌ فرمت ویدیویی یافت نشد. لطفاً دوباره تلاش کنید.", show_alert=True)
            return
            
        await callback_query.edit_message_text(
            txt['file_name'].format(name=info.get('title', 'Unknown')),
            reply_markup=InlineKeyboardMarkup(formats)
        )

    elif callback_query.data == '2':
        # Audio formats
        formats = []
        if isinstance(info, dict) and 'formats' in info and info.get('title'):
            # Using yt-dlp format selection
            audio_formats = [f for f in info['formats'] 
                           if (f.get('vcodec', 'none') == 'none' and f.get('acodec', 'none') != 'none') or \
                              (f.get('vcodec', 'none') == 'none' and f.get('ext') in ['m4a', 'webm', 'mp3', 'ogg', 'aac', 'flac', 'wav'])]
            
            # Sort by audio quality (bitrate)
            audio_formats.sort(key=lambda x: (x.get('abr', 0) or 0), reverse=True)
            
            # Get unique bitrates
            seen_bitrates = set()
            unique_formats = []
            for fmt in audio_formats:
                bitrate = fmt.get('abr', 0) or fmt.get('tbr', 0)
                if bitrate and bitrate not in seen_bitrates:
                    seen_bitrates.add(bitrate)
                    unique_formats.append(fmt)
            
            # Create format buttons with proper size fallback (avoid 0B), estimate via tbr*duration when needed
            formats = []
            duration = info.get('duration') or 0
            for fmt in unique_formats:
                size_val = fmt.get('filesize') or fmt.get('filesize_approx')
                if not size_val and duration and (fmt.get('tbr') or fmt.get('abr')):
                    try:
                        kbps = fmt.get('tbr') or fmt.get('abr')
                        size_val = int((kbps * 1000 / 8) * duration)
                    except Exception:
                        size_val = None
                size_str = convert_size(2, size_val) if size_val else 'نامشخص'
                btn_text = f"{fmt.get('abr', fmt.get('tbr', 'N/A'))}kbps - {size_str}"
                formats.append([InlineKeyboardButton(btn_text, callback_data=f"{fmt['format_id']}vc")])
        
        if not formats:
            await callback_query.answer("❌ فرمت صوتی یافت نشد. لطفاً دوباره تلاش کنید.", show_alert=True)
            return
            
        await callback_query.edit_message_text(
            txt['file_name'].format(name=info.get('title', 'Unknown')),
            reply_markup=InlineKeyboardMarkup(formats)
        )

    elif callback_query.data.endswith("vd") or callback_query.data.endswith("vc"):
        format_id = callback_query.data[:-2]
        is_video = callback_query.data.endswith("vd")
        
        selected_format = next((f for f in info['formats'] if f['format_id'] == format_id), None)
        if not selected_format:
            await callback_query.answer("❌ فرمت انتخاب شده نامعتبر است.", show_alert=True)
            return
        
        # Prevent duplicate message sending by checking if info is valid
        if not info or not info.get('title'):
            await callback_query.answer("❌ اطلاعات ویدیو در دسترس نیست. لطفاً دوباره تلاش کنید.", show_alert=True)
            return

        step['format_id'] = format_id
        step['sort'] = "🎥 ویدیو" if is_video else "🔊 صدا"
        filesize = selected_format.get('filesize') or selected_format.get('filesize_approx')
        if not filesize:
            duration = info.get('duration') or 0
            kbps = selected_format.get('tbr') or selected_format.get('abr')
            if duration and kbps:
                try:
                    filesize = int((kbps * 1000 / 8) * duration)
                except Exception:
                    filesize = None
        # Always display size in MB if known
        step['filesize'] = f"{(filesize/1024/1024):.2f} MB" if filesize else "نامشخص"
        step['ext'] = selected_format.get('ext')
        # Persist numeric size and direct url for dashboard tracking
        step['size_bytes'] = int(filesize) if filesize else None
        step['format_url'] = selected_format.get('url')

        await callback_query.edit_message_text(
            txt['file_or_link'].format(name=info.get('title'), sort=step['sort'], size=step['filesize']),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(txt['telegram_file'], callback_data='_file')],
                [InlineKeyboardButton(txt['download_link'], callback_data='_link')]
            ])
        )

    elif callback_query.data == '_file':
        # Enforce daily blocked_until if set
        try:
            now = datetime.now()
            blocked_until_str = DB().get_blocked_until(callback_query.from_user.id)
            if blocked_until_str:
                bu = None
                try:
                    bu = datetime.fromisoformat(blocked_until_str)
                except Exception:
                    try:
                        bu = datetime.strptime(blocked_until_str, "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        bu = None
                if bu and now < bu:
                    seconds = int((bu - now).total_seconds())
                    await callback_query.message.reply_text(txt['rate_limit'].format(seconds=seconds))
                    return
        except Exception as e:
            print(f"Error checking blocked_until: {e}")

        # نمایش فوری پیام شروع دانلود به کاربر
        await safe_edit_text(
            f"🚀 **شروع دانلود**\n\n"
            f"🏷️ عنوان: {info.get('title', 'نامشخص')}\n"
            f"🎛️ نوع: {step.get('sort', 'نامشخص')}\n"
            f"💾 حجم: {step.get('filesize', 'نامشخص')}\n\n"
            f"⏳ در حال آماده‌سازی دانلود...",
            parse_mode=ParseMode.MARKDOWN
        )

        global previousprogress_download, previousprogress_upload
        previousprogress_download = 0
        previousprogress_upload = 0
        step['random'] = random.randint(0, 500)

        # Create dashboard job as pending
        try:
            job_id = DB().create_job(
                callback_query.from_user.id,
                info.get('title', 'Unknown'),
                status='pending',
                size_bytes=step.get('size_bytes'),
                link=step.get('format_url')
            )
            step['job_id'] = job_id
        except Exception:
            step['job_id'] = 0

        # Helpers for formatted status and safe edits with inline progress button
        def _format_status_text(name: str, sort: str, size_str: str, status: str) -> str:
            return (
                f"🏷️ عنوان:\n{name}\n\n"
                f"🎛️ نوع: {sort}\n"
                f"💾 حجم: {size_str}\n"
                f"⏳ وضعیت: {status}"
            )

        async def _safe_edit_progress(text: str, percent: int):
            try:
                await callback_query.edit_message_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton(f"🚀 پیشرفت: {percent}٪", callback_data='noop')]]
                    )
                )
            except MessageNotModified:
                pass
            except Exception:
                pass
        
        def progress_hook(d):
            global previousprogress_download
            if d['status'] == 'downloading':
                # بهبود محاسبه درصد پیشرفت برای فرگمنت‌ها
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded_bytes = d.get('downloaded_bytes', 0)
                
                # اگر فرگمنت‌ها وجود دارند، از آنها استفاده کن
                fragment_index = d.get('fragment_index')
                fragment_count = d.get('fragment_count')
                
                if fragment_index is not None and fragment_count is not None and fragment_count > 0:
                    # محاسبه درصد بر اساس فرگمنت‌ها
                    percent = int((fragment_index / fragment_count) * 100)
                elif total_bytes and downloaded_bytes:
                    # محاسبه درصد بر اساس بایت‌ها
                    percent = int((downloaded_bytes / total_bytes) * 100)
                else:
                    # اگر هیچ اطلاعاتی نداریم، از درصد قبلی استفاده کن
                    percent = previousprogress_download
                
                # فقط هر 3% به‌روزرسانی کن تا UI spam نشود
                if percent > previousprogress_download and (percent - previousprogress_download) >= 3:
                    previousprogress_download = percent
                    size_str = f"{(total_bytes/1024/1024):.2f} MB" if total_bytes else (step.get('filesize') or 'نامشخص')
                    
                    # نمایش اطلاعات فرگمنت در صورت وجود
                    status_text = "در حال دانلود..."
                    
                    # Update job status occasionally to reduce DB writes
                    try:
                        if step.get('job_id') and percent % 10 == 0:  # Update DB every 10%
                            DB().update_job_status(
                                step['job_id'],
                                'downloading',
                                link=step.get('format_url'),
                                size_bytes=int(total_bytes) if total_bytes else None
                            )
                    except Exception:
                        pass
                    try:
                        asyncio.run_coroutine_threadsafe(
                            _safe_edit_progress(
                                _format_status_text(
                                    info.get('title'), 
                                    step['sort'],
                                    size_str,
                                    status_text
                                ),
                                percent
                            ),
                            loop
                        )
                    except Exception:
                        pass
            elif d['status'] == 'finished':
                total_bytes = d.get('total_bytes')
                size_str = f"{(total_bytes/1024/1024):.2f} MB" if total_bytes else (step.get('filesize') or 'نامشخص')
                # Mark job as ready (download finished, before upload)
                try:
                    if step.get('job_id'):
                        DB().update_job_status(
                            step['job_id'],
                            'ready',
                            link=step.get('format_url'),
                            size_bytes=int(total_bytes) if total_bytes else step.get('size_bytes')
                        )
                except Exception:
                    pass
                asyncio.run_coroutine_threadsafe(
                    _safe_edit_progress(
                        _format_status_text(
                            info.get('title'), 
                            step['sort'],
                            size_str,
                            "دانلود با موفیقت به پایان رسید ✅\nآپلود فایل به‌زودی آغاز می‌گردد"
                        ),
                        100
                    ),
                    loop
                )

        filename = f"video_{step['random']}.{step['ext']}" if step['sort'] == "🎥 ویدیو" else f"audio_{step['random']}.{step['ext']}"
        downloads_dir = os.path.join(os.getcwd(), 'Downloads')
        try:
            os.makedirs(downloads_dir, exist_ok=True)
        except Exception:
            pass
        file_path = os.path.join(downloads_dir, filename)
        
        # Configure yt-dlp with cookies for authentication
        cookies_path = os.path.join(os.getcwd(), 'cookies', 'youtube.txt')
        if not os.path.exists(cookies_path):
            print(f"Warning: YouTube cookies file not found at {cookies_path}")
            
        # Security: Use environment variable for ffmpeg path or auto-detect
        ffmpeg_path = os.environ.get('FFMPEG_PATH')
        try:
            if sys.platform.startswith('linux') and os.path.exists('/usr/bin/ffmpeg'):
                ffmpeg_path = '/usr/bin/ffmpeg'
        except Exception:
            pass
        if not ffmpeg_path:
            common_paths = [
                "C:\\ffmpeg\\bin\\ffmpeg.exe",  # Windows
                "ffmpeg",                      # In PATH
                "/usr/local/bin/ffmpeg"        # macOS or custom
            ]
            for path in common_paths:
                if shutil.which(path) or os.path.exists(path):
                    ffmpeg_path = path
                    break
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': step['format_id'],
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'cookiefile': cookie_path if cookie_path else None,
            'ffmpeg_location': ffmpeg_path,
            'progress_hooks': [progress_hook],
            'noplaylist': True,
            'extract_flat': False,
        }
        
        try:
            # Download the video
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([step['link']['webpage_url']])
            
            # Find the downloaded file
            downloaded_files = [f for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
            if not downloaded_files:
                await bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="❌ خطا در دانلود فایل",
                    reply_markup=None
                )
                return
            
            downloaded_file = os.path.join(temp_dir, downloaded_files[0])
            file_size = os.path.getsize(downloaded_file)
            
            # Update message for upload
            await bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="📤 در حال آپلود...",
                reply_markup=None
            )
            
            # Upload the file
            with open(downloaded_file, 'rb') as video_file:
                if step['format_id'].startswith('audio'):
                    await bot.send_audio(
                        chat_id=call.message.chat.id,
                        audio=video_file,
                        title=step['link'].get('title', 'Audio'),
                        duration=step['link'].get('duration'),
                        reply_to_message_id=call.message.reply_to_message.message_id if call.message.reply_to_message else None
                    )
                else:
                    await bot.send_video(
                        chat_id=call.message.chat.id,
                        video=video_file,
                        duration=step['link'].get('duration'),
                        width=step['link'].get('width'),
                        height=step['link'].get('height'),
                        caption=f"🎬 {step['link'].get('title', 'Video')}",
                        reply_to_message_id=call.message.reply_to_message.message_id if call.message.reply_to_message else None
                    )
            
            # Clean up
            os.remove(downloaded_file)
            
            # Delete the progress message
            await bot.delete_message(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
            
        except Exception as e:
            print(f"Download error: {e}")
            await bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"❌ خطا در دانلود: {str(e)}",
                reply_markup=None
            )