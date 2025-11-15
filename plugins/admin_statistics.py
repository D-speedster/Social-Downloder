"""
Admin Statistics Module
ماژول آمار حرفه‌ای برای پنل ادمین
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
from plugins.db_wrapper import DB

logger = logging.getLogger('admin_statistics')

# Cache برای بهبود عملکرد
STATS_CACHE = {}
CACHE_DURATION = 300  # 5 minutes


class StatisticsCalculator:
    """کلاس محاسبه آمار"""
    
    def __init__(self, db: DB):
        self.db = db
    
    def calculate_users_stats(self) -> Dict:
        """
        محاسبه آمار کاربران
        
        Returns:
            dict: {
                'total': int,
                'today': int,
                'week': int,
                'month': int,
                'active_today': int,
                'active_week': int,
                'active_month': int
            }
        """
        try:
            # محاسبه تاریخ‌ها
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = today_start - timedelta(days=now.weekday())
            month_start = today_start.replace(day=1)
            
            # کل کاربران
            total = self.db.get_total_users()
            
            # کاربران جدید
            today = self.db.get_users_since(today_start)
            week = self.db.get_users_since(week_start)
            month = self.db.get_users_since(month_start)
            
            # کاربران فعال
            active_today = self.db.get_active_users_since(today_start)
            active_week = self.db.get_active_users_since(week_start)
            active_month = self.db.get_active_users_since(month_start)
            
            return {
                'total': total,
                'today': today,
                'week': week,
                'month': month,
                'active_today': active_today,
                'active_week': active_week,
                'active_month': active_month
            }
        
        except Exception as e:
            logger.error(f"Error calculating users stats: {e}")
            return {
                'total': 0,
                'today': 0,
                'week': 0,
                'month': 0,
                'active_today': 0,
                'active_week': 0,
                'active_month': 0
            }
    
    def calculate_requests_stats(self) -> Dict:
        """
        محاسبه آمار درخواست‌ها
        
        Returns:
            dict: {
                'total': int,
                'youtube': int,
                'aparat': int,
                'adult': int,
                'universal': int,
                'percentages': {...}
            }
        """
        try:
            # مجموع درخواست‌ها
            total = self.db.get_total_requests()
            
            # درخواست‌ها به تفکیک پلتفرم
            youtube = self.db.get_requests_by_platform('youtube')
            aparat = self.db.get_requests_by_platform('aparat')
            adult = self.db.get_requests_by_platform('adult')
            universal = self.db.get_requests_by_platform('universal')
            
            # محاسبه درصدها
            percentages = {}
            if total > 0:
                percentages['youtube'] = (youtube / total) * 100
                percentages['aparat'] = (aparat / total) * 100
                percentages['adult'] = (adult / total) * 100
                percentages['universal'] = (universal / total) * 100
            else:
                percentages = {'youtube': 0, 'aparat': 0, 'adult': 0, 'universal': 0}
            
            return {
                'total': total,
                'youtube': youtube,
                'aparat': aparat,
                'adult': adult,
                'universal': universal,
                'percentages': percentages
            }
        
        except Exception as e:
            logger.error(f"Error calculating requests stats: {e}")
            return {
                'total': 0,
                'youtube': 0,
                'aparat': 0,
                'adult': 0,
                'universal': 0,
                'percentages': {'youtube': 0, 'aparat': 0, 'adult': 0, 'universal': 0}
            }
    
    def calculate_performance_stats(self) -> Dict:
        """
        محاسبه آمار عملکرد
        
        Returns:
            dict: {
                'successful': int,
                'failed': int,
                'success_rate': float,
                'avg_processing_time': float
            }
        """
        try:
            # درخواست‌های موفق و ناموفق
            successful = self.db.get_successful_requests()
            failed = self.db.get_failed_requests()
            total = successful + failed
            
            # نرخ موفقیت
            if total > 0:
                success_rate = (successful / total) * 100
            else:
                success_rate = 0.0
            
            # میانگین زمان پردازش
            avg_time = self.db.get_avg_processing_time()
            
            return {
                'successful': successful,
                'failed': failed,
                'success_rate': success_rate,
                'avg_processing_time': avg_time
            }
        
        except Exception as e:
            logger.error(f"Error calculating performance stats: {e}")
            return {
                'successful': 0,
                'failed': 0,
                'success_rate': 0.0,
                'avg_processing_time': 0.0
            }
    
    def calculate_overview_stats(self) -> Dict:
        """
        محاسبه آمار خلاصه برای صفحه Overview
        
        Returns:
            dict: {
                'total_users': int,
                'total_requests': int,
                'active_today': int,
                'success_rate': float,
                'avg_time': float
            }
        """
        try:
            # دریافت آمار کاربران
            users_stats = self.calculate_users_stats()
            total_users = users_stats.get('total', 0)
            active_today = users_stats.get('active_today', 0)
            
            # دریافت آمار درخواست‌ها
            requests_stats = self.calculate_requests_stats()
            total_requests = requests_stats.get('total', 0)
            
            # دریافت آمار عملکرد
            performance_stats = self.calculate_performance_stats()
            success_rate = performance_stats.get('success_rate', 0.0)
            avg_time = performance_stats.get('avg_processing_time', 0.0)
            
            # ترکیب آمارها در یک dictionary
            return {
                'total_users': total_users,
                'total_requests': total_requests,
                'active_today': active_today,
                'success_rate': success_rate,
                'avg_time': avg_time
            }
        
        except Exception as e:
            logger.error(f"Error calculating overview stats: {e}")
            # برگرداندن مقادیر پیش‌فرض در صورت خطا
            return {
                'total_users': 0,
                'total_requests': 0,
                'active_today': 0,
                'success_rate': 0.0,
                'avg_time': 0.0
            }


class StatisticsFormatter:
    """کلاس فرمت کردن آمار"""
    
    @staticmethod
    def format_number(num: int) -> str:
        """
        فرمت کردن اعداد با جداکننده هزارگان
        
        Args:
            num: عدد
        
        Returns:
            str: عدد فرمت شده مثل 1,234,567
        """
        return f"{num:,}"
    
    @staticmethod
    def create_progress_bar(percentage: float, length: int = 10) -> str:
        """
        ساخت نمودار نواری
        
        Args:
            percentage: درصد (0-100)
            length: طول نوار
        
        Returns:
            str: نمودار نواری مثل ████████░░ 80%
        """
        filled = int((percentage / 100) * length)
        empty = length - filled
        bar = '█' * filled + '░' * empty
        return f"{bar} {percentage:.1f}%"
    
    @staticmethod
    def format_users_stats(stats: Dict) -> str:
        """
        فرمت کردن آمار کاربران
        
        Args:
            stats: دیکشنری آمار کاربران
        
        Returns:
            str: متن فرمت شده
        """
        # محاسبه نرخ فعالیت
        activity_rate_today = 0
        activity_rate_week = 0
        activity_rate_month = 0
        
        if stats['today'] > 0:
            activity_rate_today = (stats['active_today'] / stats['today']) * 100
        if stats['week'] > 0:
            activity_rate_week = (stats['active_week'] / stats['week']) * 100
        if stats['month'] > 0:
            activity_rate_month = (stats['active_month'] / stats['month']) * 100
        
        text = (
            "👥 **آمار کاربران**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📊 **مجموع کاربران**\n\n"
            f"• کل کاربران: **{StatisticsFormatter.format_number(stats['total'])}**\n"
            f"• کاربران این ماه: **{StatisticsFormatter.format_number(stats['month'])}**\n"
            f"• کاربران این هفته: **{StatisticsFormatter.format_number(stats['week'])}**\n"
            f"• کاربران امروز: **{StatisticsFormatter.format_number(stats['today'])}**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ **کاربران فعال**\n\n"
            f"• فعال امروز: **{StatisticsFormatter.format_number(stats['active_today'])}**\n"
            f"• فعال این هفته: **{StatisticsFormatter.format_number(stats['active_week'])}**\n"
            f"• فعال این ماه: **{StatisticsFormatter.format_number(stats['active_month'])}**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📈 **نرخ فعالیت**\n\n"
            f"امروز: {StatisticsFormatter.create_progress_bar(activity_rate_today)}\n"
            f"هفته: {StatisticsFormatter.create_progress_bar(activity_rate_week)}\n"
            f"ماه: {StatisticsFormatter.create_progress_bar(activity_rate_month)}"
        )
        
        return text
    
    @staticmethod
    def format_requests_stats(stats: Dict) -> str:
        """
        فرمت کردن آمار درخواست‌ها
        
        Args:
            stats: دیکشنری آمار درخواست‌ها
        
        Returns:
            str: متن فرمت شده
        """
        text = (
            "📈 **آمار درخواست‌ها**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 **مجموع:** {StatisticsFormatter.format_number(stats['total'])} درخواست\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎬 **YouTube**\n"
            f"{StatisticsFormatter.create_progress_bar(stats['percentages']['youtube'], 18)}\n"
            f"{StatisticsFormatter.format_number(stats['youtube'])} درخواست\n\n"
            f"📺 **Aparat**\n"
            f"{StatisticsFormatter.create_progress_bar(stats['percentages']['aparat'], 18)}\n"
            f"{StatisticsFormatter.format_number(stats['aparat'])} درخواست\n\n"
            f"🔞 **محتوای بزرگسال**\n"
            f"{StatisticsFormatter.create_progress_bar(stats['percentages']['adult'], 18)}\n"
            f"{StatisticsFormatter.format_number(stats['adult'])} درخواست\n\n"
            f"🌐 **Universal**\n"
            f"{StatisticsFormatter.create_progress_bar(stats['percentages']['universal'], 18)}\n"
            f"{StatisticsFormatter.format_number(stats['universal'])} درخواست"
        )
        
        return text
    
    @staticmethod
    def format_performance_stats(stats: Dict) -> str:
        """
        فرمت کردن آمار عملکرد
        
        Args:
            stats: دیکشنری آمار عملکرد
        
        Returns:
            str: متن فرمت شده
        """
        total = stats['successful'] + stats['failed']
        
        text = (
            "⚡ **آمار عملکرد**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📊 **وضعیت درخواست‌ها**\n\n"
            f"✅ موفق: **{StatisticsFormatter.format_number(stats['successful'])}**\n"
            f"❌ ناموفق: **{StatisticsFormatter.format_number(stats['failed'])}**\n"
            f"📊 مجموع: **{StatisticsFormatter.format_number(total)}**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📈 **نرخ موفقیت**\n\n"
            f"{StatisticsFormatter.create_progress_bar(stats['success_rate'], 18)}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⏱️ **عملکرد**\n\n"
            f"میانگین زمان پردازش: **{stats['avg_processing_time']:.1f}** ثانیه"
        )
        
        return text
    
    @staticmethod
    def format_overview_stats(stats: Dict) -> str:
        """
        فرمت کردن صفحه Overview
        
        Args:
            stats: دیکشنری آمار شامل:
                - total_users: تعداد کل کاربران
                - total_requests: تعداد کل درخواست‌ها
                - active_today: کاربران فعال امروز
                - success_rate: نرخ موفقیت (درصد)
                - avg_time: میانگین زمان پردازش (ثانیه)
        
        Returns:
            str: متن فرمت شده
        """
        text = (
            "📊 **نمای کلی آمار**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "👥 **کاربران**\n\n"
            f"• کل کاربران: **{StatisticsFormatter.format_number(stats['total_users'])}**\n"
            f"• فعال امروز: **{StatisticsFormatter.format_number(stats['active_today'])}**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📈 **درخواست‌ها**\n\n"
            f"• کل درخواست‌ها: **{StatisticsFormatter.format_number(stats['total_requests'])}**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ **عملکرد**\n\n"
            f"• نرخ موفقیت: **{stats['success_rate']:.1f}%**\n"
            f"• میانگین زمان: **{stats['avg_time']:.1f}** ثانیه\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "💡 برای مشاهده جزئیات بیشتر، از دکمه‌های زیر استفاده کنید."
        )
        
        return text


def get_cached_stats(stats_type: str) -> Optional[Dict]:
    """
    دریافت آمار از cache
    
    Args:
        stats_type: نوع آمار (users, requests, performance)
    
    Returns:
        dict یا None
    """
    if stats_type in STATS_CACHE:
        cached_time, data = STATS_CACHE[stats_type]
        if time.time() - cached_time < CACHE_DURATION:
            logger.info(f"Using cached stats for {stats_type}")
            return data
    return None


def set_cached_stats(stats_type: str, data: Dict):
    """
    ذخیره آمار در cache
    
    Args:
        stats_type: نوع آمار
        data: داده آمار
    """
    STATS_CACHE[stats_type] = (time.time(), data)
    logger.info(f"Cached stats for {stats_type}")


def clear_stats_cache():
    """پاک کردن cache آمار"""
    global STATS_CACHE
    STATS_CACHE = {}
    logger.info("Stats cache cleared")


logger.info("Admin Statistics module loaded")
