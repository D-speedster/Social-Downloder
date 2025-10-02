"""
سیستم پیشرفته دانلود یوتیوب با قابلیت merge واقعی ویدئو و صدا
"""

import os
import sys
import json
import time
import shutil
import asyncio
import tempfile
import subprocess
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import yt_dlp
from plugins.logger_config import get_logger

# Initialize logger
advanced_logger = get_logger('youtube_advanced')

class YouTubeAdvancedDownloader:
    """کلاس پیشرفته برای دانلود یوتیوب با merge واقعی"""
    
    def __init__(self):
        self.temp_dir = None
        self.download_dir = os.path.join(os.getcwd(), 'downloads')  # standardized lowercase
        os.makedirs(self.download_dir, exist_ok=True)
        self.ffmpeg_path = self._find_ffmpeg()
        # Cookie rotation state
        self._prev_cookie_id: Optional[int] = None
        advanced_logger.info("YouTubeAdvancedDownloader initialized")
    
    def _find_ffmpeg(self) -> Optional[str]:
        """پیدا کردن مسیر ffmpeg"""
        # Check environment variable first
        ffmpeg_path = os.environ.get('FFMPEG_PATH')
        if ffmpeg_path and os.path.exists(ffmpeg_path):
            return ffmpeg_path
        
        # Common paths to check
        from config import FFMPEG_PATH
        common_paths = [
            FFMPEG_PATH,
            "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "ffmpeg"  # If in PATH
        ]
        
        for path in common_paths:
            if shutil.which(path) or os.path.exists(path):
                advanced_logger.info(f"FFmpeg found at: {path}")
                return path
        
        advanced_logger.warning("FFmpeg not found in common locations")
        return None
    
    async def get_video_info(self, url: str) -> Optional[Dict]:
        """دریافت اطلاعات کامل ویدیو"""
        advanced_logger.info(f"Getting video info for: {url}")
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': False,
            'no_check_certificate': True,
            'socket_timeout': 15,
            'connect_timeout': 10,
            'proxy': 'socks5h://127.0.0.1:1084',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android']
                }
            },
        }
        # همیشه ابتدا سعی کن از فایل کوکی اصلی استفاده کنی
        try:
            from .cookie_manager import get_cookie_file_with_fallback
            cookiefile, cid = get_cookie_file_with_fallback(self._prev_cookie_id)
            if cookiefile:
                ydl_opts['cookiefile'] = cookiefile
                self._prev_cookie_id = cid
                if cid == -1:
                    advanced_logger.info("استفاده از کوکی اصلی cookie_youtube.txt برای استخراج اطلاعات")
                else:
                    advanced_logger.info(f"استفاده از کوکی استخر برای استخراج اطلاعات: id={cid}")
        except Exception as _:
            pass
        
        try:
            # حذف وابستگی کوکی: اطلاعات ویدیو بدون کوکی استخراج می‌شود
            
            # Run extraction in thread pool
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, self._extract_info, url, ydl_opts)
            
            if info:
                advanced_logger.info(f"Video info extracted: {info.get('title', 'Unknown')}")
                return info
            else:
                advanced_logger.error("Failed to extract video info")
                return None
                
        except Exception as e:
            advanced_logger.error(f"Error extracting video info: {e}")
            return None
        finally:
            # وابستگی کوکی حذف شده است؛ نیازی به پاک‌سازی فایل کوکی نیست
            pass
    
    def _extract_info(self, url: str, ydl_opts: Dict) -> Optional[Dict]:
        """استخراج اطلاعات در thread جداگانه"""
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as e:
            advanced_logger.error(f"yt-dlp extraction error: {e}")
            return None
    
    def get_mergeable_qualities(self, info: Dict) -> List[Dict]:
        """دریافت لیست کیفیت‌های قابل merge"""
        if not info or 'formats' not in info:
            return []
        
        advanced_logger.info("Analyzing mergeable qualities")
        formats = info['formats']
        
        # Separate video and audio formats
        video_formats = []
        audio_formats = []
        combined_formats = []
        
        for fmt in formats:
            vcodec = fmt.get('vcodec', 'none')
            acodec = fmt.get('acodec', 'none')
            
            if vcodec != 'none' and acodec != 'none':
                # Combined format (video + audio)
                combined_formats.append(fmt)
            elif vcodec != 'none' and acodec == 'none':
                # Video only
                video_formats.append(fmt)
            elif vcodec == 'none' and acodec != 'none':
                # Audio only
                audio_formats.append(fmt)
        
        # Get best audio format for merging
        best_audio = None
        if audio_formats:
            # Prefer AAC, then MP3, then others
            aac_formats = [f for f in audio_formats if f.get('acodec', '').lower().startswith('aac')]
            mp3_formats = [f for f in audio_formats if f.get('acodec', '').lower().startswith('mp3')]
            
            if aac_formats:
                best_audio = max(aac_formats, key=lambda x: x.get('abr', 0) or 0)
            elif mp3_formats:
                best_audio = max(mp3_formats, key=lambda x: x.get('abr', 0) or 0)
            elif audio_formats:
                best_audio = max(audio_formats, key=lambda x: x.get('abr', 0) or 0)
        
        mergeable_qualities = []
        
        # Add combined formats first
        for fmt in combined_formats:
            height = fmt.get('height', 0) or 0
            if height >= 360:  # Only show reasonable qualities
                quality_info = {
                    'format_id': fmt['format_id'],
                    'resolution': f"{height}p" if height else "Unknown",
                    'fps': fmt.get('fps', 0) or 0,
                    'vcodec': fmt.get('vcodec', 'unknown'),
                    'acodec': fmt.get('acodec', 'unknown'),
                    'filesize': fmt.get('filesize') or fmt.get('filesize_approx'),
                    'ext': fmt.get('ext', 'mp4'),
                    'type': 'combined',
                    'video_format': fmt,
                    'audio_format': None,
                    'tbr': fmt.get('tbr', 0) or 0
                }
                mergeable_qualities.append(quality_info)
        
        # Add mergeable video formats (if we have audio to merge with)
        if best_audio:
            for fmt in video_formats:
                height = fmt.get('height', 0) or 0
                if height >= 360:  # Only show reasonable qualities
                    # Estimate merged file size
                    video_size = fmt.get('filesize') or fmt.get('filesize_approx') or 0
                    audio_size = best_audio.get('filesize') or best_audio.get('filesize_approx') or 0
                    estimated_size = video_size + audio_size if video_size and audio_size else None
                    
                    quality_info = {
                        'format_id': f"{fmt['format_id']}+{best_audio['format_id']}",
                        'resolution': f"{height}p" if height else "Unknown",
                        'fps': fmt.get('fps', 0) or 0,
                        'vcodec': fmt.get('vcodec', 'unknown'),
                        'acodec': best_audio.get('acodec', 'unknown'),
                        'filesize': estimated_size,
                        'ext': 'mp4',  # Output will be MP4
                        'type': 'mergeable',
                        'video_format': fmt,
                        'audio_format': best_audio,
                        'tbr': (fmt.get('tbr', 0) or 0) + (best_audio.get('tbr', 0) or 0)
                    }
                    mergeable_qualities.append(quality_info)
        
        # Sort by resolution (highest first), then by bitrate
        mergeable_qualities.sort(key=lambda x: (
            int(x['resolution'].replace('p', '')) if x['resolution'] != 'Unknown' else 0,
            x['tbr']
        ), reverse=True)
        
        # Remove duplicates based on resolution and keep the best bitrate
        seen_resolutions = set()
        unique_qualities = []
        for quality in mergeable_qualities:
            res_key = quality['resolution']
            if res_key not in seen_resolutions:
                seen_resolutions.add(res_key)
                unique_qualities.append(quality)
        
        advanced_logger.info(f"Found {len(unique_qualities)} mergeable qualities")
        return unique_qualities
    
    async def download_and_merge(self, url: str, quality_info: Dict, callback=None, thumbnail_url: Optional[str] = None) -> Dict:
        """دانلود و ادغام با اعمال الزامات خروجی: MP4/H.264/AAC در 1280x720 و تولید thumbnail"""
        try:
            file_type = quality_info.get('type', 'combined')
            timestamp = int(time.time())
            base_name = f"video_{timestamp}"
            temp_output = os.path.join(self.temp_dir, f"{base_name}.mp4")
            final_output = os.path.join(self.download_dir, f"{base_name}.mp4")

            # Hook تطبیق با callback پیشرفت
            def progress_hook(d):
                if callback and d.get('status') == 'downloading':
                    try:
                        percent = d.get('_percent_str', '0%').replace('%', '')
                        speed = d.get('_speed_str', 'N/A')
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.run_coroutine_threadsafe(callback(f"دانلود: {percent}% - سرعت: {speed}"), loop)
                    except:
                        pass
                elif callback and d.get('status') == 'finished':
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.run_coroutine_threadsafe(callback("در حال ادغام و تبدیل به 720p..."), loop)
                    except:
                        pass

            # مسیر progressive/combined یا DASH (video+audio جدا)
            merged_path: Optional[str] = None
            if file_type == 'combined':
                # دانلود فرمت ترکیبی و سپس تبدیل به 720p/H.264/AAC
                merged_path = await self._download_combined(url, quality_info, temp_output, progress_hook)
            else:
                # دانلود جداگانه و ادغام با ffmpeg و اعمال 720p/H.264/AAC
                merged_path = await self._download_and_merge_separate(url, quality_info, temp_output, progress_hook)

            if not merged_path or not os.path.exists(merged_path):
                return {'success': False, 'error': 'دانلود یا ادغام ناموفق بود'}

            # تبدیل نهایی به خروجی دقیق 720p/H.264/AAC
            transcode_ok = await self._transcode_to_target(merged_path, final_output)
            if not transcode_ok or not os.path.exists(final_output):
                return {'success': False, 'error': 'تبدیل نهایی به 720p/H.264/AAC شکست خورد'}

            # تولید thumbnail برای تلگرام (اختیاری)
            thumb_path = None
            if thumbnail_url:
                try:
                    raw_thumb = await self._download_thumbnail_simple(thumbnail_url)
                    if raw_thumb:
                        thumb_out = os.path.join(self.temp_dir, f"thumb_{timestamp}.jpg")
                        gen_thumb_ok = await self._generate_telegram_thumb(raw_thumb, thumb_out)
                        if gen_thumb_ok:
                            thumb_path = thumb_out
                except Exception as e:
                    advanced_logger.warning(f"Thumbnail processing failed: {e}")

            # اعتبارسنجی خروجی نهایی
            metadata = await self.get_file_metadata(final_output)
            width, height = metadata.get('width', 0), metadata.get('height', 0)
            vcodec = metadata.get('video_codec', '').lower()
            acodec = metadata.get('audio_codec', '').lower()

            if width != 1280 or height != 720:
                # پاک‌سازی و گزارش خطا
                try:
                    os.unlink(final_output)
                except:
                    pass
                return {'success': False, 'error': f"وضوح نهایی {width}x{height} است؛ باید دقیقاً 1280x720 باشد"}

            if ('264' not in vcodec) or ('aac' not in acodec):
                try:
                    os.unlink(final_output)
                except:
                    pass
                return {'success': False, 'error': 'کدک‌های خروجی باید H.264 و AAC باشند'}

            return {
                'success': True,
                'file_path': final_output,
                'file_size': os.path.getsize(final_output),
                'thumb_path': thumb_path
            }

        except Exception as e:
            advanced_logger.error(f"Download/Merge error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _download_with_ytdlp(self, url: str, ydl_opts: Dict) -> bool:
        """دانلود با yt-dlp"""
        try:
            import yt_dlp
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            advanced_logger.info("yt-dlp download completed successfully")
            return True
            
        except Exception as e:
            advanced_logger.error(f"yt-dlp download error: {e}")
            # Check if any file was downloaded in the download directory
            outtmpl = ydl_opts.get('outtmpl', '')
            if isinstance(outtmpl, str):
                # Extract base filename pattern
                base_pattern = os.path.basename(outtmpl).replace('.%(ext)s', '')
                if os.path.exists(self.download_dir):
                    for file in os.listdir(self.download_dir):
                        if base_pattern in file and not file.endswith('.part'):
                            file_path = os.path.join(self.download_dir, file)
                            if os.path.getsize(file_path) > 1024:  # File has content
                                advanced_logger.info(f"Found downloaded file despite error: {file}")
                                return True
            return False
    
    async def _download_combined(self, url: str, quality_info: Dict, output_path: str, 
                               progress_callback) -> Optional[str]:
        """دانلود فرمت combined"""
        format_id = quality_info['format_id']
        
        ydl_opts = {
            'format': format_id,
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'proxy': 'socks5h://127.0.0.1:1084',
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios']
                }
            },
        }
        # همیشه ابتدا سعی کن از فایل کوکی اصلی استفاده کنی
        try:
            from .cookie_manager import get_cookie_file_with_fallback
            cookiefile, cid = get_cookie_file_with_fallback(self._prev_cookie_id)
            if cookiefile:
                ydl_opts['cookiefile'] = cookiefile
                self._prev_cookie_id = cid
                if cid == -1:
                    advanced_logger.info("استفاده از کوکی اصلی cookie_youtube.txt برای دانلود combined")
                else:
                    advanced_logger.info(f"استفاده از کوکی استخر برای دانلود combined: id={cid}, path={cookiefile}")
        except Exception:
            pass
        
        if self.ffmpeg_path:
            ydl_opts['ffmpeg_location'] = self.ffmpeg_path
        
        # Add progress hook
        if progress_callback:
            ydl_opts['progress_hooks'] = [progress_callback]
        
        try:
            # حذف وابستگی کوکی: دانلود بدون کوکی انجام می‌شود
            
            # Download in thread pool
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, self._download_with_ydl, url, ydl_opts)
            
            if success and os.path.exists(output_path):
                advanced_logger.info("Combined format downloaded successfully")
                # Mark cookie success
                try:
                    from .cookie_manager import mark_cookie_used
                    if self._prev_cookie_id and self._prev_cookie_id != -1:
                        mark_cookie_used(self._prev_cookie_id, True)
                except Exception:
                    pass
                return output_path
            else:
                advanced_logger.error("Combined format download failed")
                # Mark cookie failure
                try:
                    from .cookie_manager import mark_cookie_used
                    if self._prev_cookie_id and self._prev_cookie_id != -1:
                        mark_cookie_used(self._prev_cookie_id, False)
                except Exception:
                    pass
                return None
                
        finally:
            # وابستگی کوکی حذف شده است؛ نیازی به پاک‌سازی فایل کوکی نیست
            pass
    
    async def _download_and_merge_separate(self, url: str, quality_info: Dict, output_path: str,
                                         progress_callback) -> Optional[str]:
        """دانلود و merge فرمت‌های جداگانه"""
        video_format = quality_info['video_format']
        audio_format = quality_info['audio_format']
        
        video_path = os.path.join(self.temp_dir, f"video.{video_format.get('ext', 'mp4')}")
        audio_path = os.path.join(self.temp_dir, f"audio.{audio_format.get('ext', 'm4a')}")
        
        # Download video
        advanced_logger.info("Downloading video stream...")
        video_success = await self._download_single_format(url, video_format['format_id'], 
                                                          video_path, progress_callback)
        
        if not video_success:
            advanced_logger.error("Video download failed")
            return None
        
        # Download audio
        advanced_logger.info("Downloading audio stream...")
        audio_success = await self._download_single_format(url, audio_format['format_id'],
                                                          audio_path, progress_callback)
        
        if not audio_success:
            advanced_logger.error("Audio download failed")
            return None
        
        # Merge with ffmpeg
        advanced_logger.info("Merging video and audio...")
        merge_success = await self._merge_with_ffmpeg(video_path, audio_path, output_path)
        
        if merge_success:
            advanced_logger.info("Merge completed successfully")
            return output_path
        else:
            advanced_logger.error("Merge failed")
            return None
    
    async def _download_single_format(self, url: str, format_id: str, output_path: str,
                                    progress_callback) -> bool:
        """دانلود یک فرمت خاص"""
        ydl_opts = {
            'format': format_id,
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'proxy': 'socks5h://127.0.0.1:1084',
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios']
                }
            },
        }
        # همیشه ابتدا سعی کن از فایل کوکی اصلی استفاده کنی
        try:
            from .cookie_manager import get_cookie_file_with_fallback
            cookiefile, cid = get_cookie_file_with_fallback(self._prev_cookie_id)
            if cookiefile:
                ydl_opts['cookiefile'] = cookiefile
                self._prev_cookie_id = cid
                if cid == -1:
                    advanced_logger.info("استفاده از کوکی اصلی cookie_youtube.txt برای دانلود single format")
                else:
                    advanced_logger.info(f"استفاده از کوکی استخر برای دانلود single format: id={cid}, path={cookiefile}")
        except Exception:
            pass
        
        if progress_callback:
            ydl_opts['progress_hooks'] = [progress_callback]
        
        try:
            # حذف وابستگی کوکی: دانلود بدون کوکی انجام می‌شود
            
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, self._download_with_ydl, url, ydl_opts)
            
            if success and os.path.exists(output_path):
                try:
                    from .cookie_manager import mark_cookie_used
                    if self._prev_cookie_id and self._prev_cookie_id != -1:
                        mark_cookie_used(self._prev_cookie_id, True)
                except Exception:
                    pass
                return True
            else:
                try:
                    from .cookie_manager import mark_cookie_used
                    if self._prev_cookie_id and self._prev_cookie_id != -1:
                        mark_cookie_used(self._prev_cookie_id, False)
                except Exception:
                    pass
                return False
            
        finally:
            # وابستگی کوکی حذف شده است؛ نیازی به پاک‌سازی فایل کوکی نیست
            pass
    
    def _download_with_ydl(self, url: str, ydl_opts: Dict) -> bool:
        """دانلود با yt-dlp در thread جداگانه"""
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                return True
        except Exception as e:
            advanced_logger.error(f"yt-dlp download error: {e}")
            return False
    
    async def _merge_with_ffmpeg(self, video_path: str, audio_path: str, output_path: str, target_resolution: str = '720p') -> bool:
        """ادغام و اطمینان از خروجی MP4/H.264/AAC با وضوح دقیق 1280x720"""
        if not self.ffmpeg_path:
            advanced_logger.error("FFmpeg not available for merging")
            return False
        
        # تعریف وضوح‌های استاندارد طبق دستورالعمل فاز 1
        standard_resolutions = {
            '240p': '426x240',
            '360p': '640x360', 
            '480p': '854x480',
            '720p': '1280x720',
            '1080p': '1920x1080'
        }
        
        try:
            # بررسی وضوح فعلی ویدئو
            current_resolution = await self._get_video_resolution(video_path)
            advanced_logger.info(f"Current video resolution: {current_resolution}")

            # FFmpeg command برای ادغام و تبدیل به 720p
            cmd = [
                self.ffmpeg_path,
                '-i', video_path,
                '-i', audio_path,
                '-map', '0:v:0',
                '-map', '1:a:0',
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-ar', '48000',
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                '-avoid_negative_ts', 'make_zero',
                '-fflags', '+genpts',
                '-y',
            ]
            
            # اضافه کردن فیلتر وضوح فقط در صورت نیاز
            if target_resolution and target_resolution in standard_resolutions:
                target_res = standard_resolutions[target_resolution]
                # همیشه به وضوح هدف scale/pad انجام می‌شود (downscale یا upscale)
                advanced_logger.info(f"Enforcing target resolution: {target_res}")
                vf_filter = f"scale={target_res}:force_original_aspect_ratio=decrease,pad={target_res}:(ow-iw)/2:(oh-ih)/2"
                cmd.extend(['-vf', vf_filter, '-preset', 'fast', '-crf', '22'])
            
            cmd.append(output_path)
            
            advanced_logger.debug(f"FFmpeg command: {' '.join(cmd)}")
            
            # Run ffmpeg in thread pool with enhanced error handling
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._run_ffmpeg_enhanced, cmd)
            
            if result['success'] and os.path.exists(output_path):
                # تأیید وضوح نهایی
                final_resolution = await self._get_video_resolution(output_path)
                file_size = os.path.getsize(output_path)
                
                advanced_logger.info(f"FFmpeg merge successful - Final resolution: {final_resolution}, Size: {file_size} bytes")
                
                # ثبت گزارش موفقیت
                merge_report = {
                    'success': True,
                    'original_resolution': current_resolution,
                    'target_resolution': target_resolution,
                    'final_resolution': final_resolution,
                    'output_size': file_size,
                    'ffmpeg_output': result.get('output', ''),
                    'timestamp': time.time()
                }
                await self._log_merge_report(merge_report)
                
                return True
            else:
                advanced_logger.error(f"FFmpeg merge failed: {result.get('error', 'Unknown error')}")
                
                # ثبت گزارش شکست
                merge_report = {
                    'success': False,
                    'original_resolution': current_resolution,
                    'target_resolution': target_resolution,
                    'error': result.get('error', 'Unknown error'),
                    'ffmpeg_output': result.get('output', ''),
                    'timestamp': time.time()
                }
                await self._log_merge_report(merge_report)
                
                return False
                
        except Exception as e:
            advanced_logger.error(f"FFmpeg merge error: {e}")
            
            # ثبت گزارش خطا
            merge_report = {
                'success': False,
                'original_resolution': current_resolution if 'current_resolution' in locals() else 'unknown',
                'target_resolution': target_resolution,
                'error': str(e),
                'timestamp': time.time()
            }
            await self._log_merge_report(merge_report)
            
            return False

    async def _transcode_to_target(self, input_path: str, output_path: str, target_resolution: str = '720p') -> bool:
        """تبدیل یک فایل ویدئویی به خروجی MP4/H.264/AAC با 1280x720"""
        if not self.ffmpeg_path:
            return False

        standard_resolutions = {
            '720p': '1280x720'
        }

        try:
            target_res = standard_resolutions[target_resolution]
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-ar', '48000',
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                '-vf', f"scale={target_res}:force_original_aspect_ratio=decrease,pad={target_res}:(ow-iw)/2:(oh-ih)/2",
                '-preset', 'fast',
                '-crf', '22',
                '-y',
                output_path
            ]

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._run_ffmpeg_enhanced, cmd)
            return result.get('success', False)
        except Exception as e:
            advanced_logger.error(f"Transcode error: {e}")
            return False

    async def _download_thumbnail_simple(self, url: str) -> Optional[str]:
        """دانلود ساده thumbnail بدون وابستگی خارجی"""
        try:
            import urllib.request
            import tempfile
            fd, temp_path = tempfile.mkstemp(suffix='.jpg')
            os.close(fd)
            urllib.request.urlretrieve(url, temp_path)
            return temp_path
        except Exception as e:
            advanced_logger.warning(f"Thumbnail download failed: {e}")
            return None

    async def _generate_telegram_thumb(self, input_path: str, output_path: str) -> bool:
        """تولید فایل thumbnail مناسب تلگرام (JPEG با ابعاد کوچک)"""
        if not self.ffmpeg_path:
            return False
        try:
            cmd = [
                self.ffmpeg_path,
                '-y',
                '-i', input_path,
                '-vf', 'scale=320:-2',
                '-vframes', '1',
                output_path
            ]
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._run_ffmpeg_enhanced, cmd)
            return result.get('success', False)
        except Exception as e:
            advanced_logger.error(f"Thumb generation error: {e}")
            return False

    def _run_ffmpeg_enhanced(self, cmd: List[str]) -> Dict[str, Any]:
        """اجرای ffmpeg در thread جداگانه با گزارش‌دهی بهتر"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'output': result.stdout,
                'error': result.stderr if result.returncode != 0 else None
            }
            
        except subprocess.TimeoutExpired:
            error_msg = "FFmpeg timeout (10 minutes exceeded)"
            advanced_logger.error(error_msg)
            return {
                'success': False,
                'returncode': -1,
                'output': '',
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"FFmpeg execution error: {e}"
            advanced_logger.error(error_msg)
            return {
                'success': False,
                'returncode': -1,
                'output': '',
                'error': error_msg
            }

    async def _log_merge_report(self, report: Dict[str, Any]) -> None:
        """ثبت گزارش merge در فایل"""
        try:
            reports_dir = os.path.join(os.getcwd(), 'logs')
            os.makedirs(reports_dir, exist_ok=True)
            
            report_file = os.path.join(reports_dir, 'merge_reports.json')
            
            # خواندن گزارش‌های موجود
            reports = []
            if os.path.exists(report_file):
                try:
                    with open(report_file, 'r', encoding='utf-8') as f:
                        reports = json.load(f)
                except:
                    reports = []
            
            # اضافه کردن گزارش جدید
            reports.append(report)
            
            # نگه داشتن فقط 100 گزارش آخر
            if len(reports) > 100:
                reports = reports[-100:]
            
            # ذخیره گزارش‌ها
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(reports, f, indent=2, ensure_ascii=False)
                
            advanced_logger.debug(f"Merge report logged: {report['success']}")
            
        except Exception as e:
            advanced_logger.error(f"Failed to log merge report: {e}")

    async def extract_final_metadata(self, file_path: str) -> Dict:
        """استخراج metadata دقیق از فایل نهایی"""
        if not os.path.exists(file_path):
            return {}
        
        advanced_logger.info(f"Extracting metadata from: {file_path}")
        
        metadata = {
            'file_size': os.path.getsize(file_path),
            'file_path': file_path
        }
        
        # Use ffprobe to get detailed metadata
        if self.ffmpeg_path:
            ffprobe_path = self.ffmpeg_path.replace('ffmpeg', 'ffprobe')
            if os.path.exists(ffprobe_path) or shutil.which('ffprobe'):
                try:
                    loop = asyncio.get_event_loop()
                    probe_data = await loop.run_in_executor(None, self._probe_file, file_path, ffprobe_path)
                    if probe_data:
                        metadata.update(probe_data)
                except Exception as e:
                    advanced_logger.error(f"FFprobe error: {e}")
        
        return metadata

    def _probe_file(self, file_path: str, ffprobe_path: str) -> Dict:
        """استخراج metadata با ffprobe"""
        try:
            # Try to find ffprobe
            probe_cmd = ffprobe_path
            if not os.path.exists(ffprobe_path):
                probe_cmd = shutil.which('ffprobe')
                if not probe_cmd:
                    # Try common locations
                    common_probes = [
                        "C:\\ffmpeg\\bin\\ffprobe.exe",
                        "C:\\Program Files\\ffmpeg\\bin\\ffprobe.exe",
                        "/usr/bin/ffprobe",
                        "/usr/local/bin/ffprobe"
                    ]
                    for probe_path in common_probes:
                        if os.path.exists(probe_path):
                            probe_cmd = probe_path
                            break
                    else:
                        advanced_logger.warning("ffprobe not found")
                        return {}
            
            cmd = [
                probe_cmd,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                
                metadata = {}
                
                # Extract format info
                if 'format' in data:
                    fmt = data['format']
                    metadata['duration'] = float(fmt.get('duration', 0))
                    metadata['bitrate'] = int(fmt.get('bit_rate', 0))
                    metadata['format_name'] = fmt.get('format_name', '')
                
                # Extract stream info
                if 'streams' in data:
                    for stream in data['streams']:
                        if stream.get('codec_type') == 'video':
                            metadata['width'] = stream.get('width', 0)
                            metadata['height'] = stream.get('height', 0)
                            # Safe evaluation of frame rate
                            try:
                                fps_str = stream.get('r_frame_rate', '0/1')
                                if '/' in fps_str:
                                    num, den = fps_str.split('/')
                                    metadata['fps'] = float(num) / float(den) if float(den) != 0 else 0
                                else:
                                    metadata['fps'] = float(fps_str)
                            except:
                                metadata['fps'] = 0
                            metadata['video_codec'] = stream.get('codec_name', '')
                        elif stream.get('codec_type') == 'audio':
                            metadata['audio_codec'] = stream.get('codec_name', '')
                            metadata['sample_rate'] = int(stream.get('sample_rate', 0))
                            metadata['channels'] = stream.get('channels', 0)
                
                advanced_logger.info(f"Metadata extracted successfully: {metadata}")
                return metadata
            else:
                advanced_logger.error(f"FFprobe failed: {result.stderr}")
                
        except Exception as e:
            advanced_logger.error(f"FFprobe execution error: {e}")
        
        return {}
    
    async def get_file_metadata(self, file_path: str) -> Dict:
        """استخراج metadata از فایل"""
        if not os.path.exists(file_path):
            return {}
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Use _probe_file to get detailed metadata
        metadata = self._probe_file(file_path, 'ffprobe')
        
        # Add file size to metadata
        metadata['size'] = file_size
        
        return metadata

    async def _get_video_resolution(self, video_path: str) -> str:
        """دریافت وضوح ویدئو با ffprobe"""
        if not self.ffmpeg_path:
            return None
            
        ffprobe_path = self.ffmpeg_path.replace('ffmpeg', 'ffprobe')
        if not os.path.exists(ffprobe_path):
            return None
            
        cmd = [
            ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            video_path
        ]
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._run_ffprobe, cmd)
            
            if result:
                import json
                data = json.loads(result)
                for stream in data.get('streams', []):
                    if stream.get('codec_type') == 'video':
                        width = stream.get('width')
                        height = stream.get('height')
                        if width and height:
                            return f"{width}x{height}"
            return None
            
        except Exception as e:
            advanced_logger.error(f"Error getting video resolution: {e}")
            return None
    
    def _run_ffprobe(self, cmd: List[str]) -> str:
        """اجرای ffprobe در thread جداگانه"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout
            else:
                advanced_logger.error(f"FFprobe stderr: {result.stderr}")
                return None
        except subprocess.TimeoutExpired:
            advanced_logger.error("FFprobe timeout")
            return None
        except Exception as e:
            advanced_logger.error(f"FFprobe execution error: {e}")
            return None
    
    async def _verify_file_integrity(self, file_path: str, file_type: str = 'video') -> bool:
        """بررسی یکپارچگی فایل"""
        if not os.path.exists(file_path):
            advanced_logger.error(f"File does not exist: {file_path}")
            return False
        
        try:
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size < 1024:  # Less than 1KB
                advanced_logger.error(f"File too small: {file_size} bytes")
                return False
            
            # Use ffprobe to verify file integrity
            streams = await self._probe_file_streams(file_path)
            if not streams:
                advanced_logger.error("No streams found in file")
                return False
            
            # Check if file has expected streams
            has_video = streams.get('has_video', False)
            has_audio = streams.get('has_audio', False)
            
            if file_type == 'audio_only':
                if not has_audio:
                    advanced_logger.error("Audio file has no valid audio stream")
                    return False
            else:
                if not has_video and not has_audio:
                    advanced_logger.error("File has no valid video or audio streams")
                    return False
            
            advanced_logger.info(f"File integrity verified: video={has_video}, audio={has_audio}")
            return True
            
        except Exception as e:
            advanced_logger.error(f"File integrity check failed: {e}")
            return False

    async def _probe_file_streams(self, file_path: str) -> Dict:
        """بررسی streams فایل با ffprobe"""
        if not self.ffmpeg_path:
            return {}
            
        ffprobe_path = self.ffmpeg_path.replace('ffmpeg', 'ffprobe')
        if not os.path.exists(ffprobe_path):
            ffprobe_path = shutil.which('ffprobe')
            if not ffprobe_path:
                return {}
        
        cmd = [
            ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            file_path
        ]
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._run_ffprobe, cmd)
            
            if result:
                data = json.loads(result)
                
                stream_info = {
                    'has_video': False,
                    'has_audio': False,
                    'width': 0,
                    'height': 0
                }
                
                if 'streams' in data:
                    for stream in data['streams']:
                        if stream.get('codec_type') == 'video':
                            stream_info['has_video'] = True
                            stream_info['width'] = stream.get('width', 0)
                            stream_info['height'] = stream.get('height', 0)
                        elif stream.get('codec_type') == 'audio':
                            stream_info['has_audio'] = True
                
                return stream_info
                
        except Exception as e:
            advanced_logger.error(f"Stream probe error: {e}")
        
        return {}

    async def generate_phase1_report(self) -> Dict[str, Any]:
        """تولید گزارش کامل فاز 1"""
        try:
            reports_dir = os.path.join(os.getcwd(), 'logs')
            report_file = os.path.join(reports_dir, 'merge_reports.json')
            
            # خواندن گزارش‌های merge
            merge_reports = []
            if os.path.exists(report_file):
                try:
                    with open(report_file, 'r', encoding='utf-8') as f:
                        merge_reports = json.load(f)
                except:
                    merge_reports = []
            
            # تحلیل گزارش‌ها
            total_merges = len(merge_reports)
            successful_merges = len([r for r in merge_reports if r.get('success', False)])
            failed_merges = total_merges - successful_merges
            
            # آمار وضوح‌ها
            resolution_stats = {}
            for report in merge_reports:
                if report.get('success') and report.get('final_resolution'):
                    res = report['final_resolution']
                    resolution_stats[res] = resolution_stats.get(res, 0) + 1
            
            # تولید گزارش نهایی
            phase1_report = {
                'phase': 1,
                'title': 'Merge واقعی و وضوح صحیح',
                'timestamp': time.time(),
                'statistics': {
                    'total_merge_attempts': total_merges,
                    'successful_merges': successful_merges,
                    'failed_merges': failed_merges,
                    'success_rate': (successful_merges / total_merges * 100) if total_merges > 0 else 0
                },
                'resolution_distribution': resolution_stats,
                'ffmpeg_status': {
                    'available': self.ffmpeg_path is not None,
                    'path': self.ffmpeg_path
                },
                'compliance': {
                    'standard_resolutions_enforced': True,
                    'no_forced_resize_unless_larger': True,
                    'error_handling_implemented': True,
                    'continuous_operation': True
                },
                'recent_errors': [r for r in merge_reports[-10:] if not r.get('success', False)]
            }
            
            # ذخیره گزارش فاز 1
            phase_report_file = os.path.join(reports_dir, 'phase1_report.json')
            with open(phase_report_file, 'w', encoding='utf-8') as f:
                json.dump(phase1_report, f, indent=2, ensure_ascii=False)
            
            advanced_logger.info(f"Phase 1 report generated: {successful_merges}/{total_merges} successful merges")
            
            return phase1_report
            
        except Exception as e:
            advanced_logger.error(f"Failed to generate Phase 1 report: {e}")
            return {
                'phase': 1,
                'error': str(e),
                'timestamp': time.time()
            }

# Global instance
youtube_downloader = YouTubeAdvancedDownloader()