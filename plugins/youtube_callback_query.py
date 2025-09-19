import shutil

import requests
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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
            # Get best video format with audio
            video_formats = [f for f in info['formats'] 
                            if f.get('vcodec', 'none') != 'none' and f.get('acodec', 'none') != 'none']
            
            if video_formats:
                # Sort by height and get best quality
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
            
            # Sort by height (resolution)
            video_formats.sort(key=lambda x: (x.get('height', 0) or 0), reverse=True)
            
            # Get unique resolutions
            seen_resolutions = set()
            unique_formats = []
            for fmt in video_formats:
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
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded_bytes = d.get('downloaded_bytes', 0)
                percent = int(downloaded_bytes / total_bytes * 100) if total_bytes else previousprogress_download
                # Only update every 5% to reduce UI spam and improve performance
                if total_bytes and percent > previousprogress_download and (percent - previousprogress_download) >= 5:
                    previousprogress_download = percent
                    size_str = f"{(total_bytes/1024/1024):.2f} MB" if total_bytes else (step.get('filesize') or 'نامشخص')
                    # Update job status occasionally to reduce DB writes
                    try:
                        if step.get('job_id') and percent % 10 == 0:  # Update DB every 10%
                            DB().update_job_status(
                                step['job_id'],
                                'downloading',
                                link=step.get('format_url'),
                                size_bytes=int(total_bytes)
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
                                    "در حال دانلود در سرور..."
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
        if not ffmpeg_path:
            # Try common locations
            common_paths = [
                "C:\\ffmpeg\\bin\\ffmpeg.exe",
                "ffmpeg",  # If in PATH
                "/usr/bin/ffmpeg",  # Linux
                "/usr/local/bin/ffmpeg"  # macOS
            ]
            for path in common_paths:
                if shutil.which(path) or os.path.exists(path):
                    ffmpeg_path = path
                    break
            
        ydl_opts = {
            'format': step['format_id'],
            'outtmpl': file_path,
            'progress_hooks': [progress_hook],
            'noplaylist': True,
            'extractor_retries': 2,  # Reduced from 3 to 2 for faster processing
            'fragment_retries': 2,   # Reduced from 3 to 2 for faster processing
            'retry_sleep_functions': {'http': lambda n: min(2 ** n, 15)},  # Faster retry with lower max wait
            'http_chunk_size': 10485760,  # 10MB chunks for better stability
            'socket_timeout': 20,    # Reduced from 30 to 20 seconds
            'no_warnings': True,
            'ignoreerrors': False,   # Don't ignore errors during actual download
            'concurrent_fragment_downloads': 4,  # Enable concurrent downloads for faster speed
        }
        
        if ffmpeg_path:
            ydl_opts['ffmpeg_location'] = ffmpeg_path
            
        if os.path.exists(cookies_path):
            ydl_opts['cookiefile'] = cookies_path

        try:
            await asyncio.to_thread(lambda: YoutubeDL(ydl_opts).download([info['webpage_url']]))
        except Exception as e:
            print(f"Download failed with error: {e}")
            # Try fallback with different format options but still using cookies
            try:
                fallback_opts = {
                    'format': step['format_id'],
                    'outtmpl': file_path,
                    'progress_hooks': [progress_hook],
                    'noplaylist': True,
                    'extractor_retries': 1,  # Reduced for faster fallback
                    'fragment_retries': 1,   # Reduced for faster fallback
                    'retry_sleep_functions': {'http': lambda n: min(2 ** n, 10)},  # Even faster retry in fallback
                    'socket_timeout': 15,    # Shorter timeout for fallback
                    'no_warnings': True,
                    'concurrent_fragment_downloads': 2,  # Lower concurrency for fallback
                }
                
                if ffmpeg_path:
                    fallback_opts['ffmpeg_location'] = ffmpeg_path
                    
                if os.path.exists(cookies_path):
                    fallback_opts['cookiefile'] = cookies_path
                await asyncio.to_thread(lambda: YoutubeDL(fallback_opts).download([info['webpage_url']]))
            except Exception as fallback_error:
                # Mark job as failed
                try:
                    if step.get('job_id'):
                        DB().update_job_status(step['job_id'], 'failed')
                except Exception:
                    pass
                await callback_query.message.reply_text(f"❌ دانلود با مشکل مواجه شد: {fallback_error}")
                return

        def on_progress2(current, total, callback_query, client):
            global previousprogress_upload
            total_size = total
            liveprogress = int(current / total_size * 100) if total_size else 0
            # Only update every 5% to reduce UI spam and improve performance
            if liveprogress > previousprogress_upload and (liveprogress - previousprogress_upload) >= 5:
                previousprogress_upload = liveprogress
                try:
                    asyncio.run_coroutine_threadsafe(
                        _safe_edit_progress(
                            _format_status_text(
                                info.get('title'), 
                                step['sort'],
                                f"{(total_size/1024/1024):.2f} MB" if total_size else (step.get('filesize') or 'نامشخص'),
                                "در حال آپلود ..."
                            ),
                            liveprogress
                        ),
                        loop
                    )
                except Exception:
                    pass

        if os.path.exists(file_path):
            try:
                sent_msg = None
                if step['sort'] == "🎥 ویدیو":
                    sent_msg = await callback_query.message.reply_video(
                        file_path,
                        caption=info.get('title'),
                        duration=int(info.get('duration', 0)),
                        progress=on_progress2,
                        progress_args=(callback_query, client)
                    )
                else:
                    sent_msg = await callback_query.message.reply_audio(
                        file_path,
                        caption=info.get('title'),
                        duration=int(info.get('duration', 0)),
                        progress=on_progress2,
                        progress_args=(callback_query, client)
                    )
                
                DB().increment_request(callback_query.from_user.id, datetime.now().isoformat())
                # Mark job as completed after successful upload
                try:
                    if step.get('job_id'):
                        DB().update_job_status(step['job_id'], 'completed')
                except Exception:
                    pass
                # Delete the processing message and sticker after successful upload
                try:
                    await callback_query.message.delete()
                except Exception:
                    pass
                
                # Bot tag under the sent media
                try:
                    if sent_msg:
                        await sent_msg.reply_text("📥 دریافت شده توسط ربات YouTube | Instagram Save Bot")
                except Exception:
                    pass

            except Exception as e:
                await callback_query.message.reply_text(f"❌ آپلود فایل با مشکل مواجه شد: {e}")
            finally:
                # Ensure cleanup of downloaded files
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    part_file = file_path + ".part"
                    if os.path.exists(part_file):
                        os.remove(part_file)
                except Exception as ce:
                    print(f"Cleanup failed: {ce}")
        else:
            await callback_query.message.reply_text("❌ فایل دانلود شده یافت نشد!")

    elif callback_query.data == '_link':
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

        selected_format = next((f for f in info['formats'] if f['format_id'] == step.get('format_id')), None)
        if selected_format and selected_format.get('url'):
            direct_url = selected_format['url']
            btn_markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton("دانلود مستقیم", url=direct_url)]]
            )
            html_link = _html_escape_url(direct_url)
            await safe_edit_text(
                txt['file_or_link2'].format(
                    name=info.get('title'),
                    sort=step['sort'],
                    size=step['filesize'],
                    link=html_link
                ),
                parse_mode='HTML',
                reply_markup=btn_markup
            )
            DB().increment_request(callback_query.from_user.id, datetime.now().isoformat())
            # Create a ready job for direct link
            try:
                size_val = selected_format.get('filesize') or selected_format.get('filesize_approx')
                if not size_val:
                    duration = info.get('duration') or 0
                    kbps = selected_format.get('tbr') or selected_format.get('abr')
                    if duration and kbps:
                        try:
                            size_val = int((kbps * 1000 / 8) * duration)
                        except Exception:
                            size_val = None
                DB().create_job(
                    callback_query.from_user.id,
                    info.get('title', 'Unknown'),
                    status='ready',
                    size_bytes=int(size_val) if size_val else None,
                    link=direct_url
                )
            except Exception:
                pass
        else:
            await callback_query.answer("❌ لینک مستقیم برای این فرمت یافت نشد.", show_alert=True)