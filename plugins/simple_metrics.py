"""
سیستم Metrics ساده برای monitoring عملکرد ربات
"""
import time
import asyncio
import psutil
import os
from datetime import datetime
from typing import Dict, List
from collections import deque


class SimpleMetrics:
    """
    کلاس ساده برای جمع‌آوری و نمایش metrics
    """
    def __init__(self):
        self.start_time = time.time()
        
        # Counters
        self.total_requests = 0
        self.total_downloads = 0
        self.total_uploads = 0
        self.total_errors = 0
        
        # Per-platform stats
        self.platform_stats = {}
        
        # Recent requests (برای محاسبه rate)
        self.recent_requests = deque(maxlen=1000)
        
        # Download times (برای محاسبه میانگین)
        self.download_times = deque(maxlen=100)
        self.upload_times = deque(maxlen=100)
        
        # System stats
        self.process = psutil.Process(os.getpid())
        
        print("📊 Metrics system initialized")
    
    def log_request(self, platform: str = "unknown"):
        """ثبت یک درخواست جدید"""
        self.total_requests += 1
        self.recent_requests.append(time.time())
        
        if platform not in self.platform_stats:
            self.platform_stats[platform] = {
                'requests': 0,
                'downloads': 0,
                'errors': 0
            }
        self.platform_stats[platform]['requests'] += 1
        
        # لاگ هر 100 درخواست
        if self.total_requests % 100 == 0:
            self._log_summary()
    
    def log_download(self, platform: str = "unknown", success: bool = True, duration: float = 0):
        """ثبت یک دانلود"""
        if success:
            self.total_downloads += 1
            if duration > 0:
                self.download_times.append(duration)
            
            if platform in self.platform_stats:
                self.platform_stats[platform]['downloads'] += 1
        else:
            self.total_errors += 1
            if platform in self.platform_stats:
                self.platform_stats[platform]['errors'] += 1
        
        # لاگ هر 50 دانلود
        if (self.total_downloads + self.total_errors) % 50 == 0:
            self._log_summary()
    
    def log_upload(self, duration: float = 0):
        """ثبت یک آپلود"""
        self.total_uploads += 1
        if duration > 0:
            self.upload_times.append(duration)
    
    def log_error(self, platform: str = "unknown"):
        """ثبت یک خطا"""
        self.total_errors += 1
        if platform in self.platform_stats:
            self.platform_stats[platform]['errors'] += 1
    
    def get_stats(self) -> Dict:
        """دریافت آمار کامل"""
        uptime = time.time() - self.start_time
        
        # محاسبه request rate (آخرین 1 دقیقه)
        now = time.time()
        recent_count = sum(1 for t in self.recent_requests if t > now - 60)
        requests_per_minute = recent_count
        
        # محاسبه success rate
        total_attempts = self.total_downloads + self.total_errors
        success_rate = (self.total_downloads / total_attempts * 100) if total_attempts > 0 else 0
        
        # محاسبه میانگین زمان‌ها
        avg_download_time = sum(self.download_times) / len(self.download_times) if self.download_times else 0
        avg_upload_time = sum(self.upload_times) / len(self.upload_times) if self.upload_times else 0
        
        # System stats
        cpu_percent = self.process.cpu_percent()
        memory_mb = self.process.memory_info().rss / 1024 / 1024
        
        return {
            'uptime_seconds': uptime,
            'uptime_hours': uptime / 3600,
            'total_requests': self.total_requests,
            'total_downloads': self.total_downloads,
            'total_uploads': self.total_uploads,
            'total_errors': self.total_errors,
            'success_rate': success_rate,
            'requests_per_minute': requests_per_minute,
            'avg_download_time': avg_download_time,
            'avg_upload_time': avg_upload_time,
            'cpu_percent': cpu_percent,
            'memory_mb': memory_mb,
            'platform_stats': self.platform_stats
        }
    
    def _log_summary(self):
        """لاگ خلاصه آمار"""
        stats = self.get_stats()
        
        print("\n" + "="*60)
        print(f"📊 METRICS SUMMARY")
        print("="*60)
        print(f"⏱️  Uptime: {stats['uptime_hours']:.1f} hours")
        print(f"📨 Total Requests: {stats['total_requests']}")
        print(f"📥 Downloads: {stats['total_downloads']} | Uploads: {stats['total_uploads']}")
        print(f"❌ Errors: {stats['total_errors']}")
        print(f"✅ Success Rate: {stats['success_rate']:.1f}%")
        print(f"⚡ Request Rate: {stats['requests_per_minute']:.0f}/min")
        print(f"⏱️  Avg Download: {stats['avg_download_time']:.1f}s")
        print(f"⏱️  Avg Upload: {stats['avg_upload_time']:.1f}s")
        print(f"💻 CPU: {stats['cpu_percent']:.1f}% | RAM: {stats['memory_mb']:.0f} MB")
        print("="*60 + "\n")
    
    def get_formatted_stats(self) -> str:
        """دریافت آمار به صورت متن فرمت شده (برای ادمین)"""
        stats = self.get_stats()
        
        text = "📊 **آمار ربات**\n\n"
        text += f"⏱️ زمان فعالیت: {stats['uptime_hours']:.1f} ساعت\n"
        text += f"📨 کل درخواست‌ها: {stats['total_requests']}\n"
        text += f"📥 دانلودها: {stats['total_downloads']}\n"
        text += f"📤 آپلودها: {stats['total_uploads']}\n"
        text += f"❌ خطاها: {stats['total_errors']}\n"
        text += f"✅ نرخ موفقیت: {stats['success_rate']:.1f}%\n"
        text += f"⚡ سرعت: {stats['requests_per_minute']:.0f} درخواست/دقیقه\n\n"
        
        text += f"⏱️ **زمان‌ها:**\n"
        text += f"• میانگین دانلود: {stats['avg_download_time']:.1f}s\n"
        text += f"• میانگین آپلود: {stats['avg_upload_time']:.1f}s\n\n"
        
        text += f"💻 **منابع سیستم:**\n"
        text += f"• CPU: {stats['cpu_percent']:.1f}%\n"
        text += f"• RAM: {stats['memory_mb']:.0f} MB\n\n"
        
        if stats['platform_stats']:
            text += "📱 **آمار پلتفرم‌ها:**\n"
            for platform, pstats in stats['platform_stats'].items():
                text += f"• {platform}: {pstats['downloads']} دانلود، {pstats['errors']} خطا\n"
        
        return text
    
    async def start_periodic_logging(self, interval: int = 300):
        """
        شروع لاگ‌گیری دوره‌ای (هر 5 دقیقه)
        """
        while True:
            await asyncio.sleep(interval)
            self._log_summary()


# 🔥 Global metrics instance
metrics = SimpleMetrics()

print("✅ Metrics ready")
