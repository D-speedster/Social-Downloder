"""
Periodic Retry Metrics Logger
لاگ‌گیری دوره‌ای از metrics سیستم retry

این ماژول به صورت دوره‌ای metrics را لاگ می‌کند
"""
import asyncio
import logging

logger = logging.getLogger('retry_metrics_logger')


async def start_periodic_metrics_logging(interval_seconds: int = 300):
    """
    شروع لاگ‌گیری دوره‌ای از metrics
    
    Args:
        interval_seconds: فاصله زمانی بین هر لاگ (پیش‌فرض: 300 ثانیه = 5 دقیقه)
    """
    try:
        from plugins.retry_metrics import retry_metrics
        
        logger.info(f"Starting periodic metrics logging (interval: {interval_seconds}s)")
        
        while True:
            await asyncio.sleep(interval_seconds)
            
            try:
                # لاگ خلاصه metrics
                retry_metrics.log_summary()
                
                # دریافت آمار صف و بروزرسانی
                try:
                    from plugins.failed_request_queue import FailedRequestQueue
                    from plugins.db_wrapper import DB
                    
                    db = DB()
                    queue = FailedRequestQueue(db)
                    queue_stats = queue.get_queue_stats()
                    
                    logger.info(
                        f"Queue status: pending={queue_stats.get('pending', 0)}, "
                        f"completed={queue_stats.get('completed', 0)}, "
                        f"failed={queue_stats.get('failed', 0)}"
                    )
                except Exception as queue_error:
                    logger.warning(f"Could not fetch queue stats: {queue_error}")
                
            except Exception as e:
                logger.error(f"Error during periodic metrics logging: {e}")
    
    except ImportError:
        logger.warning("Retry metrics system not available, periodic logging disabled")
    except Exception as e:
        logger.error(f"Error starting periodic metrics logging: {e}")


def init_metrics_logging(interval_seconds: int = 300):
    """
    Initialize periodic metrics logging
    
    Args:
        interval_seconds: Interval between logs in seconds (default: 300 = 5 minutes)
    
    Returns:
        asyncio.Task: The background task
    """
    try:
        task = asyncio.create_task(start_periodic_metrics_logging(interval_seconds))
        logger.info("Periodic metrics logging task created")
        return task
    except Exception as e:
        logger.error(f"Failed to create metrics logging task: {e}")
        return None


logger.info("RetryMetricsLogger module loaded")
