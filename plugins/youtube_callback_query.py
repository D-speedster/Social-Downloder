import os
import sys
import json
import time
import shutil
import asyncio
import yt_dlp
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.enums import ParseMode
from pyrogram.errors import MessageNotModified
from plugins.start import step
from plugins.sqlite_db_wrapper import DB
from plugins.logger_config import get_logger
from plugins.youtube_helpers import download_youtube_file, get_direct_download_url, safe_edit_text
from plugins.job_queue import enqueue_download_job
from plugins import constant
from utils.util import convert_size
from plugins.stream_utils import smart_upload_strategy, direct_youtube_upload
import random
import subprocess

# Initialize logger
youtube_callback_logger = get_logger('youtube_callback')

previousprogress_download = 0
previousprogress_upload = 0

PATH = constant.PATH
txt = constant.TEXT
data = constant.DATA


@Client.on_callback_query(filters.regex(r'^(1|2|3|_file|_link|\d+(vd|vc)|download_video|download_audio)$'))
async def answer(client: Client, callback_query: CallbackQuery):
    youtube_callback_logger.info(f"شروع پردازش callback query از کاربر {callback_query.from_user.id}")
    youtube_callback_logger.debug(f"Callback data: {callback_query.data}")
    
    # Get video info from step for yt-dlp handlers
    info = step.get('link', {})
    youtube_callback_logger.debug(f"اطلاعات ویدیو: title={info.get('title', 'نامشخص')}, duration={info.get('duration', 'نامشخص')}")
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
            # First try to get combined formats (video + audio)
            combined_formats = [f for f in info['formats'] 
                               if f.get('vcodec', 'none') != 'none' and f.get('acodec', 'none') != 'none']
            
            # If no combined formats, use best video + best audio approach
            if not combined_formats:
                # Get best video-only format
                video_only_formats = [f for f in info['formats'] 
                                     if f.get('vcodec', 'none') != 'none' and f.get('acodec', 'none') == 'none']
                
                if video_only_formats:
                    # Prioritize formats with height >= 720, then >= 480, then any available
                    hd_formats = [f for f in video_only_formats if (f.get('height', 0) or 0) >= 720]
                    sd_formats = [f for f in video_only_formats if 480 <= (f.get('height', 0) or 0) < 720]
                    
                    if hd_formats:
                        # Sort HD formats by height (prefer 720p over higher if available)
                        hd_formats.sort(key=lambda x: abs((x.get('height', 0) or 0) - 720))
                        best_video = hd_formats[0]
                    elif sd_formats:
                        # Sort SD formats by height (prefer higher resolution)
                        sd_formats.sort(key=lambda x: (x.get('height', 0) or 0), reverse=True)
                        best_video = sd_formats[0]
                    else:
                        # Fallback to any available format
                        video_only_formats.sort(key=lambda x: (x.get('height', 0) or 0), reverse=True)
                        best_video = video_only_formats[0]
                    
                    # Get best audio format
                    audio_formats = [f for f in info['formats'] 
                                   if f.get('acodec', 'none') != 'none' and f.get('vcodec', 'none') == 'none']
                    
                    if audio_formats:
                        # Sort by audio bitrate (prefer higher quality)
                        audio_formats.sort(key=lambda x: x.get('abr', 0) or x.get('tbr', 0), reverse=True)
                        best_audio = audio_formats[0]
                        
                        # Use format combination (video+audio)
                        step['format_id'] = f"{best_video['format_id']}+{best_audio['format_id']}"
                        best_format = best_video  # Use video format for size calculation
                    else:
                        # Fallback to video-only
                        step['format_id'] = best_video['format_id']
                        best_format = best_video
                else:
                    await callback_query.answer("❌ فرمت ویدیویی یافت نشد.", show_alert=True)
                    return
            else:
                # Use combined format
                # Prioritize formats with height >= 720, then >= 480, then any available
                hd_formats = [f for f in combined_formats if (f.get('height', 0) or 0) >= 720]
                sd_formats = [f for f in combined_formats if 480 <= (f.get('height', 0) or 0) < 720]
                
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
                    combined_formats.sort(key=lambda x: (x.get('height', 0) or 0), reverse=True)
                    best_format = combined_formats[0]
                
                step['format_id'] = best_format['format_id']
            
            # Set format info
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
        youtube_callback_logger.info(f"کاربر {callback_query.from_user.id} انتخاب کرد: دریافت فایل")
        youtube_callback_logger.debug(f"فرمت انتخابی: {step.get('sort', 'نامشخص')}, حجم: {step.get('filesize', 'نامشخص')}")
        
        # بررسی وجود اطلاعات ویدیو
        if not info or not info.get('title'):
            youtube_callback_logger.error("اطلاعات ویدیو در step موجود نیست")
            await callback_query.answer("❌ اطلاعات ویدیو در دسترس نیست. لطفاً دوباره تلاش کنید.", show_alert=True)
            return
            
        # بررسی وجود format_id
        if not step.get('format_id'):
            youtube_callback_logger.error("format_id در step موجود نیست")
            await callback_query.answer("❌ فرمت انتخاب نشده. لطفاً ابتدا فرمت مورد نظر را انتخاب کنید.", show_alert=True)
            return
        
        youtube_callback_logger.info(f"شروع دانلود روی سرور برای کاربر {callback_query.from_user.id}")
        # نمایش فوری پیام شروع دانلود روی سرور به کاربر
        await safe_edit_text(
            f"🚀 **شروع دانلود روی سرور**\n\n"
            f"🏷️ عنوان: {info.get('title', 'نامشخص')}\n"
            f"🎛️ نوع: {step.get('sort', 'نامشخص')}\n"
            f"💾 حجم: {step.get('filesize', 'نامشخص')}\n\n"
            f"⏳ در حال آماده‌سازی دانلود...",
            parse_mode=ParseMode.MARKDOWN
        )

        # Enqueue job into the worker queue and show position
        media_type = 'audio' if step.get('sort') == '🔊 صدا' else 'video'
        caption = f"🎬 {info.get('title', 'نامشخص')}" if media_type == 'video' else f"🔊 {info.get('title', 'نامشخص')}"
        pos = await enqueue_download_job(
            client,
            callback_query.message,
            callback_query.from_user.id,
            info.get('webpage_url', ''),
            info.get('title', ''),
            step.get('format_id', ''),
            media_type,
            caption
        )
        await safe_edit_text(
            f"🕒 **در صف دانلود هستید** (نفر {pos})\n\n"
            f"🏷️ عنوان: {info.get('title', 'نامشخص')}\n"
            f"🎛️ نوع: {step.get('sort', 'نامشخص')}\n"
            f"💾 حجم: {step.get('filesize', 'نامشخص')}\n\n"
            f"🔔 به‌محض شروع دانلود، وضعیت و پیشرفت نمایش داده می‌شود",
            parse_mode=ParseMode.MARKDOWN
        )
        return
        # Initialize progress variables
        progress = 0
        start_time = time.time()
        
        # Create job in database
        job_id = DB().create_job(
            user_id=callback_query.from_user.id,
            url=info.get('webpage_url', ''),
            title=info.get('title', ''),
            format_id=step.get('format_id', ''),
            status='downloading'
        )
        youtube_callback_logger.info(f"ایجاد job با ID: {job_id}")

        def status_hook(d):
            nonlocal progress, start_time
            if d['status'] == 'downloading':
                try:
                    if 'total_bytes' in d:
                        progress = int((d['downloaded_bytes'] / d['total_bytes']) * 100)
                    elif 'total_bytes_estimate' in d:
                        progress = int((d['downloaded_bytes'] / d['total_bytes_estimate']) * 100)
                    else:
                        progress = 0
                    
                    # Update job status
                    DB().update_job_progress(job_id, progress)
                    youtube_callback_logger.debug(f"پیشرفت دانلود: {progress}%")
                except Exception as e:
                    youtube_callback_logger.error(f"خطا در محاسبه پیشرفت: {e}")

        async def progress_display():
            while progress < 100:
                try:
                    elapsed = time.time() - start_time
                    await safe_edit_text(
                        f"📥 **دانلود روی سرور در حال انجام**\n\n"
                        f"🏷️ عنوان: {info.get('title', 'نامشخص')}\n"
                        f"📊 پیشرفت: {progress}%\n"
                        f"⏱️ زمان سپری شده: {int(elapsed)}s\n"
                        f"🎛️ نوع: {step.get('sort', 'نامشخص')}\n"
                        f"💾 حجم: {step.get('filesize', 'نامشخص')}\n\n"
                        f"💡 پس از پایان دانلود، فایل به تلگرام آپلود می‌شود",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    await asyncio.sleep(2)
                except Exception as e:
                    youtube_callback_logger.error(f"خطا در نمایش پیشرفت: {e}")
                    break

        # Start progress display task
        progress_task = asyncio.create_task(progress_display())

        downloaded_file = None
        try:
            # دانلود به پوشه downloads روی سرور
            downloads_dir = os.path.join(os.getcwd(), 'downloads')
            
            # زمان‌سنج دانلود
            t_dl_start = time.perf_counter()
            downloaded_file = await download_youtube_file(
                info.get('webpage_url', ''),
                step.get('format_id', ''),
                status_hook,
                out_dir=downloads_dir
            )
            t_dl_end = time.perf_counter()
            youtube_callback_logger.info(f"⏱️ زمان دانلود: {t_dl_end - t_dl_start:.2f}s")
            
            # توقف نمایش پیشرفت
            try:
                progress_task.cancel()
            except Exception:
                pass
            
            if not downloaded_file or not os.path.exists(downloaded_file):
                raise Exception("دانلود ناموفق بود")
            
            # اطلاع‌رسانی شروع آپلود
            await safe_edit_text(
                f"📤 **در حال آپلود به تلگرام**\n\n"
                f"🏷️ عنوان: {info.get('title', 'نامشخص')}\n"
                f"🎛️ نوع: {step.get('sort', 'نامشخص')}\n"
                f"💾 حجم: {step.get('filesize', 'نامشخص')}\n\n"
                f"⏳ لطفاً چند لحظه صبر کنید...",
                parse_mode=ParseMode.MARKDOWN
            )
            DB().update_job_status(job_id, 'uploading')
            
            # نوع مدیا برای آپلود
            media_type = 'audio' if step.get('sort') == '🔊 صدا' else 'video'
            caption = f"🎬 {info.get('title', 'نامشخص')}" if media_type == 'video' else f"🔊 {info.get('title', 'نامشخص')}"
            
            # انتخاب روش آپلود: برای فایل‌های بزرگ، به صورت Document (chunked)
            file_size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)
            LARGE_MB = 50
            t_ul_start = time.perf_counter()
            upload_ok = False
            if file_size_mb >= LARGE_MB:
                try:
                    await client.send_document(
                        chat_id=callback_query.message.chat.id,
                        document=downloaded_file,
                        caption=caption,
                        reply_to_message_id=callback_query.message.reply_to_message.message_id if callback_query.message.reply_to_message else None
                    )
                    upload_ok = True
                except Exception as e:
                    youtube_callback_logger.error(f"آپلود Document ناموفق بود: {e}")
                    upload_ok = False
            else:
                upload_ok = await smart_upload_strategy(
                    client=client,
                    chat_id=callback_query.message.chat.id,
                    file_path=downloaded_file,
                    media_type=media_type,
                    caption=caption,
                    duration=info.get('duration'),
                    reply_to_message_id=callback_query.message.reply_to_message.message_id if callback_query.message.reply_to_message else None
                )
            t_ul_end = time.perf_counter()
            youtube_callback_logger.info(f"⏱️ زمان آپلود: {t_ul_end - t_ul_start:.2f}s")
            
            if not upload_ok:
                raise Exception("آپلود ناموفق بود")
            
            # آپلود موفق
            DB().update_job_status(job_id, 'completed')
            youtube_callback_logger.info("دانلود و آپلود با موفقیت انجام شد")
            
            # حذف پیام پیشرفت
            try:
                await callback_query.message.delete()
            except Exception:
                pass  # Ignore if message is already deleted
            
        except Exception as e:
            youtube_callback_logger.error(f"خطا در دانلود/آپلود سنتی: {e}")
            try:
                progress_task.cancel()
            except Exception:
                pass
            await client.edit_message_text(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                text=f"❌ خطا: {str(e)}",
                reply_markup=None
            )
            # Update job as failed
            DB().update_job_status(job_id, 'failed')
        finally:
            # حذف فایل دانلودشده از سرور
            try:
                if downloaded_file and os.path.exists(downloaded_file):
                    os.unlink(downloaded_file)
            except Exception:
                pass

    elif callback_query.data == '_link':
        youtube_callback_logger.info(f"کاربر {callback_query.from_user.id} انتخاب کرد: دریافت لینک")
        youtube_callback_logger.debug(f"فرمت انتخابی: {step.get('sort', 'نامشخص')}, حجم: {step.get('filesize', 'نامشخص')}")
        
        # بررسی وجود اطلاعات ویدیو
        if not info or not info.get('title'):
            youtube_callback_logger.error("اطلاعات ویدیو در step موجود نیست")
            await callback_query.answer("❌ اطلاعات ویدیو در دسترس نیست. لطفاً دوباره تلاش کنید.", show_alert=True)
            return
            
        # بررسی وجود format_id
        if not step.get('format_id'):
            youtube_callback_logger.error("format_id در step موجود نیست")
            await callback_query.answer("❌ فرمت انتخاب نشده. لطفاً ابتدا فرمت مورد نظر را انتخاب کنید.", show_alert=True)
            return

        try:
            # Get direct download URL
            youtube_callback_logger.info("دریافت لینک مستقیم دانلود")
            direct_url = await get_direct_download_url(
                info.get('webpage_url', ''),
                step.get('format_id', '')
            )
            
            if direct_url:
                await safe_edit_text(
                    f"🔗 **لینک دانلود مستقیم**\n\n"
                    f"🏷️ عنوان: {info.get('title', 'نامشخص')}\n"
                    f"🎛️ نوع: {step.get('sort', 'نامشخص')}\n"
                    f"💾 حجم: {step.get('filesize', 'نامشخص')}\n\n"
                    f"🔗 لینک: {direct_url}\n\n"
                    f"⚠️ توجه: این لینک موقت است و ممکن است پس از مدتی منقضی شود.",
                    parse_mode=ParseMode.MARKDOWN
                )
                youtube_callback_logger.info("لینک مستقیم با موفقیت ارسال شد")
            else:
                await safe_edit_text(
                    f"❌ **خطا در دریافت لینک**\n\n"
                    f"متأسفانه نتوانستیم لینک مستقیم دانلود را دریافت کنیم.\n"
                    f"لطفاً گزینه 'دریافت فایل' را انتخاب کنید.",
                    parse_mode=ParseMode.MARKDOWN
                )
                youtube_callback_logger.error("نتوانست لینک مستقیم دریافت کند")
                
        except Exception as e:
            youtube_callback_logger.error(f"خطا در دریافت لینک مستقیم: {e}")
            await safe_edit_text(
                f"❌ **خطا در دریافت لینک**\n\n"
                f"خطا: {str(e)}\n"
                f"لطفاً گزینه 'دریافت فایل' را انتخاب کنید.",
                parse_mode=ParseMode.MARKDOWN
            )

    else:
        youtube_callback_logger.warning(f"callback_query.data ناشناخته: {callback_query.data}")
        await callback_query.answer("❌ گزینه نامعتبر", show_alert=True)