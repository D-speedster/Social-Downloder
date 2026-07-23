"""
🏥 Health Monitor - سیستم نظارت و هشدار
"""
import os
import asyncio
import psutil
import time
from datetime import datetime
from typing import Dict, List
import logging

logger = logging.getLogger('health_monitor')


class HealthMonitor:
    """
    سیستم نظارت بر سلامت ربات
    """
    def __init__(self, admin_ids: List[int]):
        self.admin_ids = admin_ids
        self.running = False
        self.alerts_sent = {}  # برای جلوگیری از spam
        self.alert_cooldown = 3600  # 🔥 1 ساعت (بود 5 دقیقه)
        
        # Thresholds
        self.thresholds = {
            'disk_space_percent': 10,  # کمتر از 10% آزاد
            'memory_percent': 85,       # بیشتر از 85% استفاده
            'cpu_percent': 90,          # بیشتر از 90% استفاده
            'downloads_dir_size_gb': 50,  # بیشتر از 50GB
        }
        
        logger.info("Health Monitor initialized (alert cooldown: 1 hour)")
    
    async def start(self, client):
        """شروع monitoring"""
        self.running = True
        logger.info("Health Monitor started")
        
        while self.running:
            try:
                await asyncio.sleep(60)  # هر 1 دقیقه چک کن
                
                # بررسی سلامت
                health_status = self.check_health()
                
                # ارسال هشدار در صورت مشکل
                if health_status['alerts']:
                    await self.send_alerts(client, health_status)
                
                # لاگ وضعیت
                if health_status['status'] != 'healthy':
                    logger.warning(f"Health check: {health_status['status']}")
                
            except Exception as e:
                logger.error(f"Error in health monitor: {e}")
    
    def check_health(self) -> Dict:
        """بررسی سلامت سیستم"""
        status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'metrics': {},
            'alerts': []
        }
        
        try:
            # 1. Disk Space
            disk = psutil.disk_usage('/')
            disk_free_percent = (disk.free / disk.total) * 100
            status['metrics']['disk_free_percent'] = round(disk_free_percent, 2)
            status['metrics']['disk_free_gb'] = round(disk.free / (1024**3), 2)
            
            if disk_free_percent < self.thresholds['disk_space_percent']:
                status['status'] = 'critical'
                status['alerts'].append({
                    'level': 'critical',
                    'type': 'disk_space',
                    'message': f"🔴 فضای دیسک کم است: {disk_free_percent:.1f}% آزاد"
                })
            
            # 2. Memory Usage
            memory = psutil.virtual_memory()
            status['metrics']['memory_percent'] = memory.percent
            status['metrics']['memory_available_gb'] = round(memory.available / (1024**3), 2)
            
            if memory.percent > self.thresholds['memory_percent']:
                status['status'] = 'warning' if status['status'] == 'healthy' else status['status']
                status['alerts'].append({
                    'level': 'warning',
                    'type': 'memory',
                    'message': f"⚠️ استفاده بالای حافظه: {memory.percent:.1f}%"
                })
            
            # 3. CPU Usage
            cpu_percent = psutil.cpu_percent(interval=1)
            status['metrics']['cpu_percent'] = cpu_percent
            
            if cpu_percent > self.thresholds['cpu_percent']:
                status['status'] = 'warning' if status['status'] == 'healthy' else status['status']
                status['alerts'].append({
                    'level': 'warning',
                    'type': 'cpu',
                    'message': f"⚠️ استفاده بالای CPU: {cpu_percent:.1f}%"
                })
            
            # 4. Downloads Directory Size
            downloads_dir = './downloads'
            if os.path.exists(downloads_dir):
                dir_size = self._get_dir_size(downloads_dir)
                dir_size_gb = dir_size / (1024**3)
                status['metrics']['downloads_dir_gb'] = round(dir_size_gb, 2)
                
                if dir_size_gb > self.thresholds['downloads_dir_size_gb']:
                    status['status'] = 'warning' if status['status'] == 'healthy' else status['status']
                    status['alerts'].append({
                        'level': 'warning',
                        'type': 'downloads_dir',
                        'message': f"⚠️ حجم پوشه downloads زیاد است: {dir_size_gb:.1f}GB"
                    })
            
            # 5. Database Size
            db_files = [f for f in os.listdir('.') if f.endswith('.db')]
            if db_files:
                db_size = sum(os.path.getsize(f) for f in db_files if os.path.exists(f))
                db_size_mb = db_size / (1024**2)
                status['metrics']['database_size_mb'] = round(db_size_mb, 2)
            
            # 6. Process Info
            process = psutil.Process()
            status['metrics']['process_memory_mb'] = round(process.memory_info().rss / (1024**2), 2)
            status['metrics']['process_threads'] = process.num_threads()
            status['metrics']['process_open_files'] = len(process.open_files())
            
        except Exception as e:
            logger.error(f"Error checking health: {e}")
            status['status'] = 'error'
            status['alerts'].append({
                'level': 'error',
                'type': 'monitor_error',
                'message': f"❌ خطا در بررسی سلامت: {str(e)[:100]}"
            })
        
        return status
    
    def _get_dir_size(self, path: str) -> int:
        """محاسبه حجم یک دایرکتوری"""
        total = 0
        try:
            for entry in os.scandir(path):
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat().st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += self._get_dir_size(entry.path)
        except Exception as e:
            logger.error(f"Error calculating dir size for {path}: {e}")
        return total
    
    async def send_alerts(self, client, health_status: Dict):
        """ارسال هشدارها به ادمین"""
        try:
            now = time.time()
            
            for alert in health_status['alerts']:
                alert_key = f"{alert['type']}_{alert['level']}"
                
                # بررسی cooldown
                if alert_key in self.alerts_sent:
                    time_since_last = now - self.alerts_sent[alert_key]
                    if time_since_last < self.alert_cooldown:
                        # لاگ کن که skip شد
                        remaining = int(self.alert_cooldown - time_since_last)
                        logger.debug(f"Alert {alert_key} skipped (cooldown: {remaining}s remaining)")
                        continue  # هنوز در cooldown است
                
                # ساخت پیام هشدار
                message = self._build_alert_message(alert, health_status)
                
                # ارسال به تمام ادمین‌ها
                sent_count = 0
                for admin_id in self.admin_ids:
                    try:
                        await client.send_message(admin_id, message)
                        logger.info(f"Alert sent to admin {admin_id}: {alert['type']}")
                        sent_count += 1
                    except Exception as e:
                        logger.error(f"Failed to send alert to admin {admin_id}: {e}")
                
                # ثبت زمان ارسال (فقط اگر حداقل به یک نفر فرستاده شد)
                if sent_count > 0:
                    self.alerts_sent[alert_key] = now
                    logger.info(f"Alert cooldown set for {alert_key} (next alert in {self.alert_cooldown}s)")
        
        except Exception as e:
            logger.error(f"Error sending alerts: {e}")
    
    def _build_alert_message(self, alert: Dict, health_status: Dict) -> str:
        """ساخت پیام هشدار"""
        emoji_map = {
            'critical': '🔴',
            'warning': '⚠️',
            'error': '❌'
        }
        
        emoji = emoji_map.get(alert['level'], '⚠️')
        
        message = f"{emoji} **هشدار سیستم**\n\n"
        message += f"{alert['message']}\n\n"
        message += "📊 **وضعیت فعلی:**\n"
        
        metrics = health_status['metrics']
        message += f"💾 فضای آزاد: {metrics.get('disk_free_gb', 0):.1f}GB ({metrics.get('disk_free_percent', 0):.1f}%)\n"
        message += f"🧠 حافظه: {metrics.get('memory_percent', 0):.1f}%\n"
        message += f"⚙️ CPU: {metrics.get('cpu_percent', 0):.1f}%\n"
        message += f"📁 Downloads: {metrics.get('downloads_dir_gb', 0):.1f}GB\n"
        message += f"🗄️ Database: {metrics.get('database_size_mb', 0):.1f}MB\n\n"
        message += f"⏰ زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # توصیه‌های اقدام
        if alert['type'] == 'disk_space':
            message += "💡 **اقدام پیشنهادی:**\n"
            message += "• پاک‌سازی فایل‌های قدیمی در downloads/\n"
            message += "• بررسی logs/ برای فایل‌های بزرگ\n"
            message += "• افزایش فضای دیسک"
        elif alert['type'] == 'memory':
            message += "💡 **اقدام پیشنهادی:**\n"
            message += "• Restart ربات\n"
            message += "• بررسی memory leaks\n"
            message += "• کاهش MAX_CONCURRENT_DOWNLOADS"
        elif alert['type'] == 'downloads_dir':
            message += "💡 **اقدام پیشنهادی:**\n"
            message += "• اجرای auto-cleanup\n"
            message += "• پاک‌سازی دستی فایل‌ها"
        
        return message
    
    def stop(self):
        """توقف monitoring"""
        self.running = False
        logger.info("Health Monitor stopped")
    
    def get_status_report(self) -> str:
        """گزارش وضعیت برای ادمین"""
        health = self.check_health()
        
        report = "🏥 **گزارش سلامت سیستم**\n\n"
        
        status_emoji = {
            'healthy': '✅',
            'warning': '⚠️',
            'critical': '🔴',
            'error': '❌'
        }
        
        report += f"وضعیت: {status_emoji.get(health['status'], '❓')} {health['status'].upper()}\n\n"
        
        metrics = health['metrics']
        report += "📊 **معیارها:**\n"
        report += f"💾 فضای آزاد: {metrics.get('disk_free_gb', 0):.1f}GB ({metrics.get('disk_free_percent', 0):.1f}%)\n"
        report += f"🧠 حافظه: {metrics.get('memory_percent', 0):.1f}% (آزاد: {metrics.get('memory_available_gb', 0):.1f}GB)\n"
        report += f"⚙️ CPU: {metrics.get('cpu_percent', 0):.1f}%\n"
        report += f"📁 Downloads: {metrics.get('downloads_dir_gb', 0):.1f}GB\n"
        report += f"🗄️ Database: {metrics.get('database_size_mb', 0):.1f}MB\n\n"
        
        report += "🔧 **پروسه:**\n"
        report += f"💾 حافظه پروسه: {metrics.get('process_memory_mb', 0):.1f}MB\n"
        report += f"🧵 Threads: {metrics.get('process_threads', 0)}\n"
        report += f"📂 فایل‌های باز: {metrics.get('process_open_files', 0)}\n\n"
        
        if health['alerts']:
            report += "⚠️ **هشدارها:**\n"
            for alert in health['alerts']:
                report += f"• {alert['message']}\n"
        else:
            report += "✅ هیچ هشداری وجود ندارد\n"
        
        report += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return report


# 🔥 Global instance
_health_monitor = None


def get_health_monitor(admin_ids: List[int] = None):
    """دریافت instance health monitor"""
    global _health_monitor
    if _health_monitor is None and admin_ids:
        _health_monitor = HealthMonitor(admin_ids)
    return _health_monitor


async def start_health_monitor(client, admin_ids: List[int]):
    """شروع health monitoring"""
    monitor = get_health_monitor(admin_ids)
    if monitor:
        await monitor.start(client)


def stop_health_monitor():
    """توقف health monitoring"""
    if _health_monitor:
        _health_monitor.stop()


print("✅ Health Monitor system ready")
print("   - Disk space monitoring")
print("   - Memory monitoring")
print("   - CPU monitoring")
print("   - Auto alerts to admins")
