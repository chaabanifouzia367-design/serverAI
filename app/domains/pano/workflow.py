
from app.celery_app import celery, REDIS_AVAILABLE
from celery import chain
from app.services.job_status import JobStatusManager
from app.services.supabase_manager import update_report_status
import logging

logger = logging.getLogger(__name__)


def start_pano_workflow(file_info, upload_id, clinic_id=None, patient_id=None, report_type=None, report_id=None):

    if not REDIS_AVAILABLE or not celery:
        logger.error("Redis/Celery not available")
        return {'workflow_id': None}
    
    try:
        logger.info(f"Starting pano workflow for report {report_id}")
        
        workflow = chain(
            celery.signature('validate_pano_v2', args=[file_info, report_id]),
            
            celery.signature('upload_pano_v2', args=[clinic_id, patient_id, report_id]),
            
            celery.signature('analyze_pano_v2', args=[report_id]),
            
            celery.signature('aggregate_pano_v2', args=[file_info, upload_id, clinic_id, patient_id, report_id]),
        )
        
        workflow_result = workflow.apply_async()
        logger.info(f"Pano workflow started with ID: {workflow_result.id}")
        
        return {'workflow_id': workflow_result.id}
        
    except Exception as e:
        logger.error(f"Failed to start pano workflow: {e}")
        return {'workflow_id': None}


__all__ = ['start_pano_workflow']
