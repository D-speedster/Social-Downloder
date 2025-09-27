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
        self.ffmpeg_path = self._find_ffmpeg()
        self.cookies_file = os.path.join(os.getcwd(), 'cookies', 'youtube.txt')
        advanced_logger.info("YouTubeAdvancedDownloader initialized")
    
    def _find_ffmpeg(self) -> Optional[str]:
        """پیدا کردن مسیر ffmpeg"""
        # Check environment variable first
        ffmpeg_path = os.environ.get('FFMPEG_PATH')
        if ffmpeg_path and os.path.exists(ffmpeg_path):
            return ffmpeg_path
        
        # Common paths to check
        common_paths = [
            "C:\\ffmpeg\\bin\\ffmpeg.exe",
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
    
    async def get_video_info(self, url: str, cookie_content: Optional[str] = None) -> Optional[Dict]:
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
        }
        
        temp_cookie_file = None
        try:
            # Setup cookies if provided
            if cookie_content:
                temp_cookie_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                temp_cookie_file.write(cookie_content)
                temp_cookie_file.close()
                ydl_opts['cookiefile'] = temp_cookie_file.name
                advanced_logger.debug("Cookie file created for extraction")
            
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
            # Cleanup cookie file
            if temp_cookie_file and os.path.exists(temp_cookie_file.name):
                try:
                    os.unlink(temp_cookie_file.name)
                except:
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
    
    async def download_and_merge(self, url: str, quality_info: Dict, callback=None) -> Dict:
        """دانلود و merge ویدئو با کیفیت انتخابی"""
        try:
            format_id = quality_info['format_id']
            file_type = quality_info.get('type', 'video')
            
            # تعیین نام فایل خروجی
            if file_type == 'audio_only':
                output_filename = f"audio_{int(time.time())}.mp3"
            else:
                output_filename = f"video_{int(time.time())}.mp4"
            
            output_path = os.path.join(self.download_dir, output_filename)
            
            # تنظیمات yt-dlp برای merge واقعی
            ydl_opts = {
                'format': format_id,
                'outtmpl': output_path,
                'merge_output_format': 'mp4' if file_type != 'audio_only' else 'mp3',
                'writeinfojson': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'ignoreerrors': False,
                'no_warnings': False,
                'extractflat': False,
                'writethumbnail': True,  # دانلود thumbnail
                'embedthumbnail': True,  # اضافه کردن thumbnail به فایل
            }
            
            # اضافه کردن ffmpeg برای merge واقعی
            if self.ffmpeg_path:
                ydl_opts['ffmpeg_location'] = os.path.dirname(self.ffmpeg_path)
            
            # تنظیمات خاص برای ویدئو
            if file_type != 'audio_only':
                ydl_opts.update({
                    'format': f"{format_id}+bestaudio/best",  # اطمینان از merge video+audio
                    'postprocessors': [{
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    }, {
                        'key': 'EmbedThumbnail',
                        'already_have_thumbnail': False,
                    }],
                    'prefer_ffmpeg': True,
                    'keepvideo': False,
                })
            else:
                ydl_opts.update({
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }, {
                        'key': 'EmbedThumbnail',
                        'already_have_thumbnail': False,
                    }],
                })
            
            # Progress hook
            def progress_hook(d):
                if callback and d['status'] == 'downloading':
                    try:
                        percent = d.get('_percent_str', '0%').replace('%', '')
                        speed = d.get('_speed_str', 'N/A')
                        asyncio.create_task(callback(f"دانلود: {percent}% - سرعت: {speed}"))
                    except:
                        pass
                elif callback and d['status'] == 'finished':
                    asyncio.create_task(callback("در حال merge کردن فایل‌ها..."))
            
            ydl_opts['progress_hooks'] = [progress_hook]
            
            # دانلود با yt-dlp
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, self._download_with_ytdlp, url, ydl_opts)
            
            if not success:
                return {'success': False, 'error': 'دانلود ناموفق'}
            
            # پیدا کردن فایل نهایی
            final_file = None
            expected_extensions = ['.mp4', '.mp3', '.mkv', '.webm']
            
            for ext in expected_extensions:
                test_path = output_path.replace('.mp4', ext).replace('.mp3', ext)
                if os.path.exists(test_path):
                    final_file = test_path
                    break
            
            if not final_file:
                # جستجو در پوشه دانلود
                base_name = os.path.splitext(output_filename)[0]
                for file in os.listdir(self.download_dir):
                    if file.startswith(base_name) and any(file.endswith(ext) for ext in expected_extensions):
                        final_file = os.path.join(self.download_dir, file)
                        break
            
            if not final_file or not os.path.exists(final_file):
                return {'success': False, 'error': 'فایل نهایی پیدا نشد'}
            
            # تأیید یکپارچگی فایل
            is_valid = await self._verify_file_integrity(final_file, file_type)
            if not is_valid:
                advanced_logger.error(f"File integrity check failed: {final_file}")
                if os.path.exists(final_file):
                    os.remove(final_file)
                return {'success': False, 'error': 'فایل دانلود شده معتبر نیست'}
            
            # تغییر نام به mp4 برای ویدئو
            if file_type != 'audio_only' and not final_file.endswith('.mp4'):
                new_path = final_file.rsplit('.', 1)[0] + '.mp4'
                try:
                    os.rename(final_file, new_path)
                    final_file = new_path
                except:
                    pass
            
            advanced_logger.info(f"Download completed successfully: {final_file}")
            
            return {
                'success': True,
                'file_path': final_file,
                'file_size': os.path.getsize(final_file)
            }
            
        except Exception as e:
            advanced_logger.error(f"Download error: {e}")
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
            return False
    
    async def _download_combined(self, url: str, quality_info: Dict, output_path: str, 
                               cookie_content: Optional[str], progress_callback) -> Optional[str]:
        """دانلود فرمت combined"""
        format_id = quality_info['format_id']
        
        ydl_opts = {
            'format': format_id,
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
        }
        
        if self.ffmpeg_path:
            ydl_opts['ffmpeg_location'] = self.ffmpeg_path
        
        # Add progress hook
        if progress_callback:
            ydl_opts['progress_hooks'] = [progress_callback]
        
        temp_cookie_file = None
        try:
            # Setup cookies
            if cookie_content:
                temp_cookie_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                temp_cookie_file.write(cookie_content)
                temp_cookie_file.close()
                ydl_opts['cookiefile'] = temp_cookie_file.name
            
            # Download in thread pool
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, self._download_with_ydl, url, ydl_opts)
            
            if success and os.path.exists(output_path):
                advanced_logger.info("Combined format downloaded successfully")
                return output_path
            else:
                advanced_logger.error("Combined format download failed")
                return None
                
        finally:
            if temp_cookie_file and os.path.exists(temp_cookie_file.name):
                try:
                    os.unlink(temp_cookie_file.name)
                except:
                    pass
    
    async def _download_and_merge_separate(self, url: str, quality_info: Dict, output_path: str,
                                         cookie_content: Optional[str], progress_callback) -> Optional[str]:
        """دانلود و merge فرمت‌های جداگانه"""
        video_format = quality_info['video_format']
        audio_format = quality_info['audio_format']
        
        video_path = os.path.join(self.temp_dir, f"video.{video_format.get('ext', 'mp4')}")
        audio_path = os.path.join(self.temp_dir, f"audio.{audio_format.get('ext', 'm4a')}")
        
        # Download video
        advanced_logger.info("Downloading video stream...")
        video_success = await self._download_single_format(url, video_format['format_id'], 
                                                          video_path, cookie_content, progress_callback)
        
        if not video_success:
            advanced_logger.error("Video download failed")
            return None
        
        # Download audio
        advanced_logger.info("Downloading audio stream...")
        audio_success = await self._download_single_format(url, audio_format['format_id'],
                                                          audio_path, cookie_content, progress_callback)
        
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
                                    cookie_content: Optional[str], progress_callback) -> bool:
        """دانلود یک فرمت خاص"""
        ydl_opts = {
            'format': format_id,
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
        }
        
        if progress_callback:
            ydl_opts['progress_hooks'] = [progress_callback]
        
        temp_cookie_file = None
        try:
            if cookie_content:
                temp_cookie_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                temp_cookie_file.write(cookie_content)
                temp_cookie_file.close()
                ydl_opts['cookiefile'] = temp_cookie_file.name
            
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, self._download_with_ydl, url, ydl_opts)
            
            return success and os.path.exists(output_path)
            
        finally:
            if temp_cookie_file and os.path.exists(temp_cookie_file.name):
                try:
                    os.unlink(temp_cookie_file.name)
                except:
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
    
    async def _merge_with_ffmpeg(self, video_path: str, audio_path: str, output_path: str) -> bool:
        """merge ویدئو و صدا با ffmpeg"""
        if not self.ffmpeg_path:
            advanced_logger.error("FFmpeg not available for merging")
            return False
        
        # FFmpeg command for merging
        cmd = [
            self.ffmpeg_path,
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'copy',  # Copy video stream (no re-encoding)
            '-c:a', 'aac',   # Encode audio to AAC
            '-strict', 'experimental',
            '-y',  # Overwrite output file
            output_path
        ]
        
        try:
            advanced_logger.debug(f"FFmpeg command: {' '.join(cmd)}")
            
            # Run ffmpeg in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._run_ffmpeg, cmd)
            
            if result and os.path.exists(output_path):
                advanced_logger.info("FFmpeg merge successful")
                return True
            else:
                advanced_logger.error("FFmpeg merge failed")
                return False
                
        except Exception as e:
            advanced_logger.error(f"FFmpeg merge error: {e}")
            return False
    
    def _run_ffmpeg(self, cmd: List[str]) -> bool:
        """اجرای ffmpeg در thread جداگانه"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                return True
            else:
                advanced_logger.error(f"FFmpeg stderr: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            advanced_logger.error("FFmpeg timeout")
            return False
        except Exception as e:
            advanced_logger.error(f"FFmpeg execution error: {e}")
            return False
    
    def _verify_file_integrity(self, file_path: str, tool_type: str = 'ffprobe') -> bool:
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
            streams = self._probe_file_streams(file_path, tool_type)
            if not streams:
                advanced_logger.error("No streams found in file")
                return False
            
            # Check if file has expected streams
            has_video = streams.get('has_video', False)
            has_audio = streams.get('has_audio', False)
            
            if not has_video and not has_audio:
                advanced_logger.error("File has no valid video or audio streams")
                return False
            
            advanced_logger.info(f"File integrity verified: video={has_video}, audio={has_audio}")
            return True
            
        except Exception as e:
            advanced_logger.error(f"File integrity check failed: {e}")
            return False
            
        except Exception as e:
            advanced_logger.error(f"File integrity check error: {e}")
            return False
    
    async def _download_audio_only(self, url: str, quality_info: Dict, output_path: str,
                                 cookie_content: Optional[str], progress_callback) -> Optional[str]:
        """دانلود فقط صدا"""
        format_id = quality_info['format_id']
        
        ydl_opts = {
            'format': format_id,
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
        }
        
        if progress_callback:
            ydl_opts['progress_hooks'] = [progress_callback]
        
        temp_cookie_file = None
        try:
            if cookie_content:
                temp_cookie_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
                temp_cookie_file.write(cookie_content)
                temp_cookie_file.close()
                ydl_opts['cookiefile'] = temp_cookie_file.name
            
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, self._download_with_ydl, url, ydl_opts)
            
            if success and os.path.exists(output_path):
                advanced_logger.info("Audio download completed successfully")
                return output_path
            else:
                advanced_logger.error("Audio download failed")
                return None
                
        finally:
            if temp_cookie_file and os.path.exists(temp_cookie_file.name):
                try:
                    os.unlink(temp_cookie_file.name)
                except:
                    pass
    
    async def extract_final_metadata(self, file_path: str) -> Dict:
        """استخراج metadata نهایی از فایل"""
        return await self.get_file_metadata(file_path)

    def _probe_file_streams(self, file_path: str, ffprobe_path: str) -> Dict:
        """بررسی streams فایل با ffprobe"""
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
                        return {}
            
            cmd = [
                probe_cmd,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_streams',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                
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

# Global instance
youtube_downloader = YouTubeAdvancedDownloader()