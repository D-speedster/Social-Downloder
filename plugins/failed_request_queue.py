"""
Failed Request Queue System
سیستم صف درخواست‌های ناموفق برای پردازش دستی توسط ادمین
"""
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from pyrogram import Client
from pyrogram.types import Message
import logging
import time

logger = logging.getLogger('failed_request_queue')

# Import metrics system
try:
    from plugins.retry_metrics import retry_metrics
    METRICS_ENABLED = True
    logger.info("Retry metrics system enabled for queue")
except ImportError:
    METRICS_ENABLED = False
    logger.warning("Retry metrics system not available for queue")


class FailedRequestQueue:
    """
    مدیریت صف درخواست‌های ناموفق
    Manages the queue of failed download requests for admin processing
    """
    
    def __init__(self, db):
        """
        Initialize the failed request queue
        
        Args:
            db: Database instance (DB class from db_wrapper)
        """
        self.db = db
        logger.info("FailedRequestQueue initialized")
    
    def add_request(
        self,
        user_id: int,
        url: str,
        platform: str,
        error_message: str,
        original_message_id: int
    ) -> int:
        """
        Add a failed request to the queue
        افزودن درخواست ناموفق به صف
        
        Args:
            user_id: User's Telegram ID
            url: Download URL that failed
            platform: Platform name (Instagram, TikTok, etc.)
            error_message: Error message from the failure
            original_message_id: Message ID of the original user request
        
        Returns:
            int: Request ID in database, or 0 if failed
        """
        try:
            request_id = self.db.add_failed_request(
                user_id=user_id,
                url=url,
                platform=platform,
                error_message=error_message,
                original_message_id=original_message_id
            )
            
            if request_id > 0:
                logger.info(
                    f"Added failed request to queue: id={request_id}, "
                    f"user={user_id}, platform={platform}"
                )
            else:
                logger.error(f"Failed to add request to queue for user {user_id}")
            
            return request_id
        except Exception as e:
            logger.error(f"Error adding request to queue: {e}")
            return 0
    
    def get_pending_requests(self, limit: int = 100) -> List[Dict]:
        """
        Get all pending requests from the queue
        دریافت لیست درخواست‌های در انتظار از صف
        
        Args:
            limit: Maximum number of requests to return
        
        Returns:
            List of request dictionaries with keys:
            - id, user_id, url, platform, error_message, original_message_id,
              status, created_at, processed_at, retry_count, admin_notified
        """
        try:
            requests = self.db.get_pending_failed_requests(limit=limit)
            logger.info(f"Retrieved {len(requests)} pending requests from queue")
            return requests
        except Exception as e:
            logger.error(f"Error getting pending requests: {e}")
            return []
    
    def mark_as_processed(self, request_id: int) -> bool:
        """
        Mark a request as successfully processed
        علامت‌گذاری درخواست به عنوان پردازش شده موفق
        
        Args:
            request_id: ID of the request in database
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            success = self.db.mark_failed_request_as_processed(request_id)
            
            if success:
                logger.info(f"Marked request {request_id} as processed")
            else:
                logger.error(f"Failed to mark request {request_id} as processed")
            
            return success
        except Exception as e:
            logger.error(f"Error marking request as processed: {e}")
            return False
    
    def mark_as_failed(self, request_id: int, error: str) -> bool:
        """
        Mark a request as permanently failed
        علامت‌گذاری درخواست به عنوان شکست دائمی
        
        Args:
            request_id: ID of the request in database
            error: Error message describing the permanent failure
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            success = self.db.mark_failed_request_as_failed(request_id, error)
            
            if success:
                logger.info(f"Marked request {request_id} as permanently failed")
            else:
                logger.error(f"Failed to mark request {request_id} as failed")
            
            return success
        except Exception as e:
            logger.error(f"Error marking request as failed: {e}")
            return False
    
    def get_request_by_id(self, request_id: int) -> Dict:
        """
        Get a specific request by ID
        دریافت یک درخواست خاص با شناسه
        
        Args:
            request_id: ID of the request
        
        Returns:
            Dict with request data, or empty dict if not found
        """
        try:
            request = self.db.get_failed_request_by_id(request_id)
            return request
        except Exception as e:
            logger.error(f"Error getting request by id: {e}")
            return {}
    
    def increment_retry_count(self, request_id: int) -> bool:
        """
        Increment the retry count for a request
        افزایش شمارنده تلاش مجدد
        
        Args:
            request_id: ID of the request
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            success = self.db.increment_failed_request_retry(request_id)
            
            if success:
                logger.info(f"Incremented retry count for request {request_id}")
            
            return success
        except Exception as e:
            logger.error(f"Error incrementing retry count: {e}")
            return False
    
    def mark_admin_notified(self, request_id: int) -> bool:
        """
        Mark that admin has been notified about this request
        علامت‌گذاری اینکه ادمین از این درخواست مطلع شده
        
        Args:
            request_id: ID of the request
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            success = self.db.mark_failed_request_admin_notified(request_id)
            
            if success:
                logger.info(f"Marked admin notified for request {request_id}")
            
            return success
        except Exception as e:
            logger.error(f"Error marking admin notified: {e}")
            return False
    
    def get_queue_stats(self) -> Dict:
        """
        Get statistics about the queue
        دریافت آمار صف
        
        Returns:
            Dict with keys: total, pending, processing, completed, failed
        """
        try:
            stats = self.db.get_failed_requests_stats()
            logger.info(f"Queue stats: {stats}")
            
            # Update metrics with current queue size
            if METRICS_ENABLED:
                retry_metrics.update_queue_size(stats.get('pending', 0))
            
            return stats
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            return {
                'total': 0,
                'pending': 0,
                'processing': 0,
                'completed': 0,
                'failed': 0
            }
    
    def cleanup_old_requests(self, days: int = 7) -> int:
        """
        Delete old completed/failed requests
        پاک کردن درخواست‌های قدیمی
        
        Args:
            days: Delete requests older than this many days
        
        Returns:
            int: Number of deleted requests
        """
        try:
            deleted_count = self.db.cleanup_old_failed_requests(days=days)
            logger.info(f"Cleaned up {deleted_count} old requests (older than {days} days)")
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up old requests: {e}")
            return 0
    
    async def retry_request(
        self,
        client: Client,
        request_id: int
    ) -> Tuple[bool, str]:
        """
        Retry a failed request from the queue
        تلاش مجدد برای یک درخواست ناموفق از صف
        
        Args:
            client: Pyrogram client instance
            request_id: ID of the request to retry
        
        Returns:
            Tuple[bool, str]: (success, message)
                - success: True if download succeeded, False otherwise
                - message: Status message describing the result
        """
        try:
            # Get request from database
            request = self.get_request_by_id(request_id)
            
            if not request:
                error_msg = f"Request {request_id} not found in database"
                logger.error(error_msg)
                return False, error_msg
            
            # Check if request is still pending
            if request['status'] != 'pending':
                error_msg = f"Request {request_id} is not pending (status: {request['status']})"
                logger.warning(error_msg)
                return False, error_msg
            
            # Update status to processing
            try:
                # We don't have a direct method for this, so we'll use increment_retry_count
                # to track that we're processing it
                self.increment_retry_count(request_id)
                logger.info(f"Starting retry for request {request_id}")
            except Exception as e:
                logger.error(f"Failed to update status to processing: {e}")
            
            # Extract request details
            user_id = request['user_id']
            url = request['url']
            platform = request['platform']
            original_message_id = request['original_message_id']
            
            logger.info(
                f"Retrying request {request_id}: user={user_id}, "
                f"platform={platform}, url={url[:50]}..."
            )
            
            # Create a fake message object for the handler
            class FakeMessage:
                def __init__(self, text, user_id, chat_id, message_id):
                    self.text = text
                    self.from_user = type('obj', (object,), {'id': user_id})()
                    self.chat = type('obj', (object,), {'id': chat_id})()
                    self.message_id = message_id
                    self.reply_to_message = None
                
                async def reply_text(self, text, **kwargs):
                    """Send message to user"""
                    return await client.send_message(self.chat.id, text, **kwargs)
            
            # Create fake message
            fake_msg = FakeMessage(url, user_id, user_id, original_message_id)
            
            # Import the handler
            from plugins.universal_downloader import handle_universal_link
            
            # Track processing time
            processing_start = time.time()
            
            # Try to process the request
            try:
                # Call the handler with is_retry=True to avoid infinite loops
                await handle_universal_link(client, fake_msg, is_retry=True)
                
                processing_duration = time.time() - processing_start
                
                # If we got here without exception, assume success
                self.mark_as_processed(request_id)
                
                # Log metrics
                if METRICS_ENABLED:
                    retry_metrics.log_queue_processing(success=True, duration=processing_duration)
                
                success_msg = f"Successfully processed request {request_id} for user {user_id}"
                logger.info(success_msg)
                
                # Send success notification to user
                try:
                    await client.send_message(
                        chat_id=user_id,
                        text="✅ **درخواست شما پردازش شد!**\n\n"
                             f"فایل {platform} شما با موفقیت دریافت شد 🎉\n\n"
                             "از صبر و شکیبایی شما متشکریم! 🙏"
                    )
                except Exception as e:
                    logger.warning(f"Failed to send success notification to user: {e}")
                
                return True, success_msg
                
            except Exception as e:
                # Download failed
                error_msg = str(e)
                processing_duration = time.time() - processing_start
                
                logger.error(f"Retry failed for request {request_id}: {error_msg}")
                
                # Mark as failed
                self.mark_as_failed(request_id, error_msg)
                
                # Log metrics
                if METRICS_ENABLED:
                    retry_metrics.log_queue_processing(success=False, duration=processing_duration)
                
                # Send failure notification to user
                try:
                    await client.send_message(
                        chat_id=user_id,
                        text="😔 **متأسفیم!**\n\n"
                             f"متأسفانه نتوانستیم فایل {platform} شما را دریافت کنیم.\n\n"
                             "💡 **لطفاً:**\n"
                             "• چند دقیقه صبر کنید و دوباره تلاش کنید\n"
                             "• یا از پلتفرم دیگری استفاده کنید\n\n"
                             "🙏 از صبر و شکیبایی شما متشکریم!"
                    )
                except Exception as notify_err:
                    logger.warning(f"Failed to send failure notification to user: {notify_err}")
                
                return False, f"Retry failed: {error_msg}"
        
        except Exception as e:
            error_msg = f"Error in retry_request: {e}"
            logger.error(error_msg)
            return False, error_msg


logger.info("FailedRequestQueue module loaded")
