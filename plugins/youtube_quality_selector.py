"""
سیستم انتخاب کیفیت پیشرفته برای یوتیوب
"""

import asyncio
from typing import Dict, List, Optional
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from plugins.logger_config import get_logger
from plugins.youtube_advanced_downloader import youtube_downloader
from utils.util import convert_size

# Initialize logger
quality_selector_logger = get_logger('quality_selector')

class YouTubeQualitySelector:
    """کلاس انتخاب کیفیت یوتیوب"""
    
    def __init__(self):
        self.downloader = youtube_downloader
        quality_selector_logger.info("YouTubeQualitySelector initialized")
    
    async def get_available_qualities(self, url: str) -> Optional[List[Dict]]:
        """دریافت لیست کیفیت‌های موجود"""
        quality_selector_logger.info(f"Getting available qualities for: {url}")
        
        try:
            # Get video info
            info = await self.downloader.get_video_info(url)
            if not info:
                quality_selector_logger.error("Failed to get video info")
                return None
            
            # Get mergeable qualities
            qualities = self.downloader.get_mergeable_qualities(info)
            if not qualities:
                quality_selector_logger.error("No mergeable qualities found")
                return None
            
            quality_selector_logger.info(f"Found {len(qualities)} available qualities")
            return qualities
            
        except Exception as e:
            quality_selector_logger.error(f"Error getting available qualities: {e}")
            return None

    def format_quality_info(self, quality: Dict) -> str:
        """فرمت کردن اطلاعات کیفیت برای نمایش"""
        resolution = quality.get('resolution', 'Unknown')
        fps = quality.get('fps', 0)
        vcodec = quality.get('vcodec', 'unknown')
        acodec = quality.get('acodec', 'unknown')
        filesize = quality.get('filesize', 0)
        
        fps_text = f"@{fps}fps" if fps > 0 else ""
        # اعمال ضریب تصحیح 0.5 برای نمایش حجم واقعی (نصف حجم تخمینی اولیه)
        if filesize:
            correction_factor = 0.5
            corrected_filesize = int(filesize * correction_factor)
            size_text = convert_size(2, corrected_filesize)
        else:
            size_text = "Unknown size"
        codec_text = f"{vcodec}/{acodec}" if vcodec != 'unknown' and acodec != 'unknown' else ""
        
        info_text = f"{resolution}{fps_text}"
        if size_text:
            info_text += f" • {size_text}"
        if codec_text:
            info_text += f" • {codec_text}"
        
        return info_text

    async def get_quality_options(self, url: str) -> Optional[Dict]:
        """دریافت گزینه‌های کیفیت برای نمایش به کاربر"""
        quality_selector_logger.info(f"Getting quality options for: {url}")
        
        try:
            # Get video info
            info = await self.downloader.get_video_info(url)
            if not info:
                quality_selector_logger.error("Failed to get video info")
                return None
            
            # Get mergeable qualities
            qualities = self.downloader.get_mergeable_qualities(info)
            if not qualities:
                quality_selector_logger.error("No mergeable qualities found")
                return None
            
            # Prepare response
            result = {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Unknown'),
                'view_count': info.get('view_count', 0),
                'upload_date': info.get('upload_date', ''),
                'description': info.get('description', ''),
                'thumbnail': info.get('thumbnail', ''),
                'qualities': qualities,
                'raw_info': info  # Keep for later use
            }
            
            quality_selector_logger.info(f"Found {len(qualities)} quality options")
            return result
            
        except Exception as e:
            quality_selector_logger.error(f"Error getting quality options: {e}")
            return None
    
    def create_quality_keyboard(self, qualities: List[Dict], page: int = 0, per_page: int = 8) -> InlineKeyboardMarkup:
        """ایجاد کیبورد انتخاب کیفیت"""
        quality_selector_logger.debug(f"Creating quality keyboard - page {page}, per_page {per_page}")
        
        # Calculate pagination
        start_idx = page * per_page
        end_idx = start_idx + per_page
        page_qualities = qualities[start_idx:end_idx]
        
        buttons = []
        
        # Quality buttons
        for i, quality in enumerate(page_qualities):
            # Format quality info for display
            resolution = quality['resolution']
            fps_text = f"@{quality['fps']}fps" if quality['fps'] > 0 else ""
            
            # File size info
            if quality['filesize']:
                # اعمال ضریب تصحیح 0.5 برای نمایش حجم واقعی (نصف حجم تخمینی اولیه)
                correction_factor = 0.5
                corrected_filesize = int(quality['filesize'] * correction_factor)
                size_text = convert_size(2, corrected_filesize)
            else:
                size_text = "~حجم"
            
            # Format type indicator
            type_indicator = "🔗" if quality['type'] == 'combined' else "🔀"
            
            # Codec info (shortened)
            vcodec = quality['vcodec'][:4] if quality['vcodec'] != 'unknown' else ""
            acodec = quality['acodec'][:4] if quality['acodec'] != 'unknown' else ""
            codec_text = f"{vcodec}/{acodec}" if vcodec and acodec else ""
            
            button_text = f"{type_indicator} {resolution}{fps_text} • {size_text}"
            if codec_text:
                button_text += f" • {codec_text}"
            
            callback_data = f"dl_quality_{start_idx + i}"
            buttons.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        # Navigation buttons
        nav_buttons = []
        total_pages = (len(qualities) + per_page - 1) // per_page
        
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"quality_page_{page-1}"))
        
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"quality_page_{page+1}"))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        # Additional options
        additional_buttons = [
            [InlineKeyboardButton("🎵 فقط صدا (بهترین کیفیت)", callback_data="dl_audio_best")],
            [InlineKeyboardButton("❌ لغو", callback_data="cancel_download")]
        ]
        
        buttons.extend(additional_buttons)
        
        quality_selector_logger.debug(f"Created keyboard with {len(buttons)} button rows")
        return InlineKeyboardMarkup(buttons)
    
    def format_video_info_text(self, video_info: Dict) -> str:
        """فرمت کردن متن اطلاعات ویدیو"""
        title = video_info.get('title', 'نامشخص')
        duration = video_info.get('duration', 0)
        uploader = video_info.get('uploader', 'نامشخص')
        view_count = video_info.get('view_count', 0)
        
        # Format duration
        if duration:
            minutes, seconds = divmod(int(duration), 60)
            hours, minutes = divmod(minutes, 60)
            if hours:
                duration_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                duration_text = f"{minutes:02d}:{seconds:02d}"
        else:
            duration_text = "نامشخص"
        
        # Format view count
        if view_count:
            if view_count >= 1000000:
                view_text = f"{view_count/1000000:.1f}M"
            elif view_count >= 1000:
                view_text = f"{view_count/1000:.1f}K"
            else:
                view_text = str(view_count)
        else:
            view_text = "نامشخص"
        
        text = f"🎬 <b>{title}</b>\n\n"
        text += f"👤 <b>کانال:</b> {uploader}\n"
        text += f"⏱ <b>مدت زمان:</b> {duration_text}\n"
        text += f"👁 <b>بازدید:</b> {view_text}\n\n"
        text += "📋 <b>کیفیت‌های موجود:</b>\n"
        text += "🔗 = فرمت ترکیبی (ویدیو+صدا)\n"
        text += "🔀 = نیاز به ترکیب (ویدیو جداگانه + صدا)\n\n"
        text += "لطفاً کیفیت مورد نظر خود را انتخاب کنید:"
        
        return text
    
    def get_quality_by_index(self, qualities: List[Dict], index: int) -> Optional[Dict]:
        """دریافت کیفیت بر اساس ایندکس"""
        if 0 <= index < len(qualities):
            return qualities[index]
        return None
    
    async def get_audio_only_info(self, info: Dict) -> Optional[Dict]:
        """دریافت اطلاعات فرمت صوتی بهترین کیفیت"""
        if not info or 'formats' not in info:
            return None
        
        formats = info['formats']
        audio_formats = [f for f in formats if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
        
        if not audio_formats:
            return None
        
        # Find best audio format
        # Prefer AAC, then MP3, then others
        aac_formats = [f for f in audio_formats if f.get('acodec', '').lower().startswith('aac')]
        mp3_formats = [f for f in audio_formats if f.get('acodec', '').lower().startswith('mp3')]
        
        if aac_formats:
            best_audio = max(aac_formats, key=lambda x: x.get('abr', 0) or 0)
        elif mp3_formats:
            best_audio = max(mp3_formats, key=lambda x: x.get('abr', 0) or 0)
        else:
            best_audio = max(audio_formats, key=lambda x: x.get('abr', 0) or 0)
        
        return {
            'format_id': best_audio['format_id'],
            'resolution': 'Audio Only',
            'fps': 0,
            'vcodec': 'none',
            'acodec': best_audio.get('acodec', 'unknown'),
            'filesize': best_audio.get('filesize') or best_audio.get('filesize_approx'),
            'ext': best_audio.get('ext', 'm4a'),
            'type': 'audio_only',
            'video_format': None,
            'audio_format': best_audio,
            'tbr': best_audio.get('abr', 0) or 0,
            'abr': best_audio.get('abr', 0) or 0
        }

# Global instance
quality_selector = YouTubeQualitySelector()