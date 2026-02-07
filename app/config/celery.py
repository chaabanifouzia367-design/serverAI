"""
Celery Configuration

Celery setup and configuration.
"""
from celery import Celery
import logging

logger = logging.getLogger(__name__)


def setup_celery(app):
    """
    Initialize Celery with Flask app.
    
    Args:
        app: Flask application instance
        
    Returns:
        Configured Celery instance
    """
    celery = Celery(
        'medical_processor',
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL'],
        include=[
            'app.celery_tasks.ai.analysis',
            'app.celery_tasks.reports.formatter',
            'app.celery_tasks.reports.uploader',
            'app.celery_tasks.slices.uploader',
            'app.celery_tasks.aggregation.finalizer',
        ]
    )
    
    # Enhanced Celery configuration
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=30 * 60,  # 30 minutes
        task_soft_time_limit=25 * 60,  # 25 minutes soft limit
        worker_prefetch_multiplier=1,
        result_expires=3600,  # 1 hour
        broker_connection_retry_on_startup=True,
        broker_transport_options={
            'visibility_timeout': 3600,
            'retry_policy': {'timeout': 5.0}
        }
    )
    
    logger.info("✅ Celery configured successfully")
    return celery
