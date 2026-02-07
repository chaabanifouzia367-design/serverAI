
from celery import chain, group
from app.celery_app import celery
import logging

logger = logging.getLogger(__name__)


def start_cbct_workflow(file_info, upload_id, clinic_id=None, patient_id=None, report_type=None, report_id=None):

    try:
        logger.info(f"Starting CBCT workflow for report {report_id}")
        
        validation_result = {
            'file_info': file_info,
            'upload_id': upload_id,
            'clinic_id': clinic_id,
            'patient_id': patient_id,
            'report_type': report_type,
            'report_id': report_id
        }
        
        workflow = chain(
            group(
       
                chain(
                    celery.signature('ai_analysis', args=[validation_result]),
                    celery.signature('format_report'),
                    celery.signature('upload_report_json')
                ),
                celery.signature('upload_slices', args=[validation_result])
            ),
            celery.signature('finalize_report')
        )
        
        result = workflow.apply_async()
        logger.info(f"Workflow started with ID: {result.id}")
        
        return {'workflow_id': result.id}
        
    except Exception as e:
        logger.error(f"Failed to start workflow: {e}")
        raise


__all__ = ['start_cbct_workflow']
