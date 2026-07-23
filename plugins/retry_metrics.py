"""
Retry Metrics System
سیستم metrics اختصاصی برای smart retry و failed request queue

این ماژول metrics دقیق برای:
- Success rate هر attempt
- Queue size و processing time
- Platform-specific retry statistics
- Admin response time
"""
import time
import logging
from typing import Dict, List, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta

logger = logging.getLogger('retry_metrics')


class RetryMetrics:
    """
    سیستم metrics برای smart retry و queue management
    """
    
    def __init__(self):
        """Initialize retry metrics system"""
        self.start_time = time.time()
        
        # Attempt-level metrics
        self.attempt_stats = {
            1: {'success': 0, 'failure': 0, 'total_time': 0.0},
            2: {'success': 0, 'failure': 0, 'total_time': 0.0},
            3: {'success': 0, 'failure': 0, 'total_time': 0.0}
        }
        
        # Platform-specific retry stats
        self.platform_retry_stats = defaultdict(lambda: {
            'total_requests': 0,
            'success_attempt_1': 0,
            'success_attempt_2': 0,
            'success_attempt_3': 0,
            'final_failures': 0,
            'total_retry_time': 0.0
        })
        
        # Queue metrics
        self.queue_metrics = {
            'total_added': 0,
            'total_processed': 0,
            'total_failed': 0,
            'current_size': 0,
            'processing_times': deque(maxlen=100),  # Last 100 processing times
            'admin_response_times': deque(maxlen=50)  # Last 50 admin response times
        }
        
        # Error categorization
        self.error_categories = defaultdict(int)
        
        # Recent activity tracking (last 1 hour)
        self.recent_retries = deque(maxlen=1000)
        
        logger.info("RetryMetrics system initialized")
    
    def log_attempt(
        self,
        attempt_number: int,
        success: bool,
        platform: str,
        duration: float,
        error_category: Optional[str] = None
    ):
        """
        Log a retry attempt
        
        Args:
            attempt_number: Which attempt (1, 2, or 3)
            success: Whether the attempt succeeded
            platform: Platform name (Instagram, TikTok, etc.)
            duration: Time taken for the attempt in seconds
            error_category: Category of error if failed (transient, permanent, system)
        """
        # Update attempt stats
        if attempt_number in self.attempt_stats:
            if success:
                self.attempt_stats[attempt_number]['success'] += 1
            else:
                self.attempt_stats[attempt_number]['failure'] += 1
            self.attempt_stats[attempt_number]['total_time'] += duration
        
        # Update platform stats
        self.platform_retry_stats[platform]['total_requests'] += 1
        if success:
            if attempt_number == 1:
                self.platform_retry_stats[platform]['success_attempt_1'] += 1
            elif attempt_number == 2:
                self.platform_retry_stats[platform]['success_attempt_2'] += 1
            elif attempt_number == 3:
                self.platform_retry_stats[platform]['success_attempt_3'] += 1
        
        self.platform_retry_stats[platform]['total_retry_time'] += duration
        
        # Track error categories
        if not success and error_category:
            self.error_categories[error_category] += 1
        
        # Add to recent activity
        self.recent_retries.append({
            'timestamp': time.time(),
            'attempt': attempt_number,
            'success': success,
            'platform': platform,
            'duration': duration
        })
        
        logger.debug(
            f"Logged attempt {attempt_number} for {platform}: "
            f"success={success}, duration={duration:.2f}s"
        )
    
    def log_final_failure(self, platform: str):
        """
        Log a final failure (all attempts exhausted)
        
        Args:
            platform: Platform name
        """
        self.platform_retry_stats[platform]['final_failures'] += 1
        logger.info(f"Logged final failure for platform {platform}")
    
    def log_queue_addition(self):
        """Log when a request is added to the queue"""
        self.queue_metrics['total_added'] += 1
        self.queue_metrics['current_size'] += 1
        logger.debug(f"Queue addition logged. Current size: {self.queue_metrics['current_size']}")
    
    def log_queue_processing(self, success: bool, duration: float):
        """
        Log when a request is processed from the queue
        
        Args:
            success: Whether processing succeeded
            duration: Time taken to process in seconds
        """
        if success:
            self.queue_metrics['total_processed'] += 1
        else:
            self.queue_metrics['total_failed'] += 1
        
        self.queue_metrics['current_size'] = max(0, self.queue_metrics['current_size'] - 1)
        self.queue_metrics['processing_times'].append(duration)
        
        logger.info(
            f"Queue processing logged: success={success}, duration={duration:.2f}s, "
            f"current_size={self.queue_metrics['current_size']}"
        )
    
    def log_admin_response(self, response_time: float):
        """
        Log admin response time (time from notification to action)
        
        Args:
            response_time: Time in seconds from notification to admin action
        """
        self.queue_metrics['admin_response_times'].append(response_time)
        logger.info(f"Admin response time logged: {response_time:.2f}s")
    
    def update_queue_size(self, size: int):
        """
        Update current queue size
        
        Args:
            size: Current number of pending requests in queue
        """
        self.queue_metrics['current_size'] = size
    
    def get_attempt_success_rates(self) -> Dict[int, float]:
        """
        Get success rate for each attempt
        
        Returns:
            Dict mapping attempt number to success rate percentage
        """
        rates = {}
        for attempt, stats in self.attempt_stats.items():
            total = stats['success'] + stats['failure']
            if total > 0:
                rates[attempt] = (stats['success'] / total) * 100
            else:
                rates[attempt] = 0.0
        return rates
    
    def get_overall_success_rate(self) -> float:
        """
        Get overall success rate across all attempts
        
        Returns:
            Success rate as percentage
        """
        total_success = sum(stats['success'] for stats in self.attempt_stats.values())
        total_attempts = sum(
            stats['success'] + stats['failure'] 
            for stats in self.attempt_stats.values()
        )
        
        if total_attempts > 0:
            return (total_success / total_attempts) * 100
        return 0.0
    
    def get_platform_stats(self) -> Dict[str, Dict]:
        """
        Get retry statistics per platform
        
        Returns:
            Dict mapping platform name to its statistics
        """
        stats = {}
        for platform, data in self.platform_retry_stats.items():
            total = data['total_requests']
            if total > 0:
                stats[platform] = {
                    'total_requests': total,
                    'success_rate_attempt_1': (data['success_attempt_1'] / total) * 100,
                    'success_rate_attempt_2': (data['success_attempt_2'] / total) * 100,
                    'success_rate_attempt_3': (data['success_attempt_3'] / total) * 100,
                    'final_failure_rate': (data['final_failures'] / total) * 100,
                    'avg_retry_time': data['total_retry_time'] / total
                }
        return stats
    
    def get_queue_stats(self) -> Dict:
        """
        Get queue statistics
        
        Returns:
            Dict with queue metrics
        """
        avg_processing_time = 0.0
        if self.queue_metrics['processing_times']:
            avg_processing_time = sum(self.queue_metrics['processing_times']) / len(
                self.queue_metrics['processing_times']
            )
        
        avg_admin_response = 0.0
        if self.queue_metrics['admin_response_times']:
            avg_admin_response = sum(self.queue_metrics['admin_response_times']) / len(
                self.queue_metrics['admin_response_times']
            )
        
        total_handled = self.queue_metrics['total_processed'] + self.queue_metrics['total_failed']
        queue_success_rate = 0.0
        if total_handled > 0:
            queue_success_rate = (self.queue_metrics['total_processed'] / total_handled) * 100
        
        return {
            'current_size': self.queue_metrics['current_size'],
            'total_added': self.queue_metrics['total_added'],
            'total_processed': self.queue_metrics['total_processed'],
            'total_failed': self.queue_metrics['total_failed'],
            'queue_success_rate': queue_success_rate,
            'avg_processing_time': avg_processing_time,
            'avg_admin_response_time': avg_admin_response,
            'pending_rate': (
                self.queue_metrics['current_size'] / max(1, self.queue_metrics['total_added'])
            ) * 100
        }
    
    def get_error_distribution(self) -> Dict[str, int]:
        """
        Get distribution of error categories
        
        Returns:
            Dict mapping error category to count
        """
        return dict(self.error_categories)
    
    def get_recent_activity_rate(self, minutes: int = 60) -> float:
        """
        Get retry activity rate for recent time period
        
        Args:
            minutes: Time window in minutes (default: 60)
        
        Returns:
            Number of retries per minute
        """
        cutoff_time = time.time() - (minutes * 60)
        recent_count = sum(
            1 for retry in self.recent_retries 
            if retry['timestamp'] > cutoff_time
        )
        return recent_count / minutes if minutes > 0 else 0.0
    
    def get_comprehensive_stats(self) -> Dict:
        """
        Get all statistics in one comprehensive dict
        
        Returns:
            Dict with all metrics
        """
        uptime = time.time() - self.start_time
        
        return {
            'uptime_seconds': uptime,
            'uptime_hours': uptime / 3600,
            'attempt_success_rates': self.get_attempt_success_rates(),
            'overall_success_rate': self.get_overall_success_rate(),
            'platform_stats': self.get_platform_stats(),
            'queue_stats': self.get_queue_stats(),
            'error_distribution': self.get_error_distribution(),
            'recent_activity_rate': self.get_recent_activity_rate(),
            'total_retries': sum(
                stats['success'] + stats['failure'] 
                for stats in self.attempt_stats.values()
            )
        }
    
    def get_formatted_report(self) -> str:
        """
        Get formatted text report for admin
        
        Returns:
            Formatted string with all statistics
        """
        stats = self.get_comprehensive_stats()
        
        report = "📊 **گزارش Smart Retry System**\n\n"
        
        # Uptime
        report += f"⏱️ زمان فعالیت: {stats['uptime_hours']:.1f} ساعت\n"
        report += f"🔄 کل تلاش‌ها: {stats['total_retries']}\n\n"
        
        # Success rates per attempt
        report += "✅ **نرخ موفقیت به تفکیک تلاش:**\n"
        for attempt, rate in stats['attempt_success_rates'].items():
            report += f"  • تلاش {attempt}: {rate:.1f}%\n"
        report += f"  • کلی: {stats['overall_success_rate']:.1f}%\n\n"
        
        # Queue stats
        queue = stats['queue_stats']
        report += "📋 **آمار صف:**\n"
        report += f"  • اندازه فعلی: {queue['current_size']}\n"
        report += f"  • کل افزوده شده: {queue['total_added']}\n"
        report += f"  • پردازش موفق: {queue['total_processed']}\n"
        report += f"  • پردازش ناموفق: {queue['total_failed']}\n"
        report += f"  • نرخ موفقیت صف: {queue['queue_success_rate']:.1f}%\n"
        
        if queue['avg_processing_time'] > 0:
            report += f"  • میانگین زمان پردازش: {queue['avg_processing_time']:.1f}s\n"
        if queue['avg_admin_response_time'] > 0:
            report += f"  • میانگین پاسخ ادمین: {queue['avg_admin_response_time']:.1f}s\n"
        report += "\n"
        
        # Platform stats
        if stats['platform_stats']:
            report += "📱 **آمار پلتفرم‌ها:**\n"
            for platform, pstats in stats['platform_stats'].items():
                report += f"  • {platform}:\n"
                report += f"    - کل: {pstats['total_requests']}\n"
                report += f"    - موفقیت تلاش 1: {pstats['success_rate_attempt_1']:.1f}%\n"
                if pstats['success_rate_attempt_2'] > 0:
                    report += f"    - موفقیت تلاش 2: {pstats['success_rate_attempt_2']:.1f}%\n"
                if pstats['success_rate_attempt_3'] > 0:
                    report += f"    - موفقیت تلاش 3: {pstats['success_rate_attempt_3']:.1f}%\n"
                report += f"    - شکست نهایی: {pstats['final_failure_rate']:.1f}%\n"
            report += "\n"
        
        # Error distribution
        if stats['error_distribution']:
            report += "❌ **توزیع خطاها:**\n"
            for category, count in stats['error_distribution'].items():
                report += f"  • {category}: {count}\n"
            report += "\n"
        
        # Activity rate
        report += f"⚡ فعالیت اخیر: {stats['recent_activity_rate']:.1f} retry/دقیقه\n"
        
        return report
    
    def log_summary(self):
        """Log a summary of current metrics to logger"""
        stats = self.get_comprehensive_stats()
        
        logger.info("="*60)
        logger.info("RETRY METRICS SUMMARY")
        logger.info("="*60)
        logger.info(f"Uptime: {stats['uptime_hours']:.1f} hours")
        logger.info(f"Total retries: {stats['total_retries']}")
        logger.info(f"Overall success rate: {stats['overall_success_rate']:.1f}%")
        
        logger.info("Attempt success rates:")
        for attempt, rate in stats['attempt_success_rates'].items():
            logger.info(f"  Attempt {attempt}: {rate:.1f}%")
        
        queue = stats['queue_stats']
        logger.info(f"Queue size: {queue['current_size']}")
        logger.info(f"Queue success rate: {queue['queue_success_rate']:.1f}%")
        
        logger.info(f"Recent activity: {stats['recent_activity_rate']:.1f} retries/min")
        logger.info("="*60)


# Global metrics instance
retry_metrics = RetryMetrics()

logger.info("RetryMetrics module loaded")
