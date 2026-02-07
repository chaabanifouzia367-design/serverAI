from app.celery_app import redis_client
from app.config import Config
import logging

logger = logging.getLogger(__name__)

def is_queue_full() -> bool:
    """
    Check if the main Celery queue has reached its maximum capacity.
    
    Returns:
        bool: True if queue is full, False otherwise.
    """
    if not redis_client:
        # Fallback if Redis is down (fail open or closed based on preference)
        # Here we log error and allow, assuming Celery might handle connection issues
        logger.warning("Redis client not available for queue check")
        return False
        
    try:
        # 'celery' is the default queue name in Celery
        queue_len = redis_client.llen('celery')
        logger.debug(f"Current queue length: {queue_len}")
        
        if queue_len >= Config.MAX_QUEUE_SIZE:
            logger.warning(f"Queue full! Current: {queue_len}, Max: {Config.MAX_QUEUE_SIZE}")
            return True
            
        return False
    except Exception as e:
        logger.error(f"Error checking queue size: {e}")
        return False
