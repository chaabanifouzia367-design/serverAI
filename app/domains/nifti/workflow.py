
from celery import chain
from app.celery_app import celery
import logging

logger = logging.getLogger(__name__)

def start_nifti_workflow(file_info, upload_id, clinic_id=None, patient_id=None, report_type=None, report_id=None):
    """
    Start workflow to process NIfTI file and generate slices.
    """
    try:
        logger.info(f"Starting NIfTI workflow for report {report_id}")
        
        validation_result = {
            'file_info': file_info,
            'upload_id': upload_id,
            'clinic_id': clinic_id,
            'patient_id': patient_id,
            'report_type': report_type or 'nifti',
            'report_id': report_id
        }
        
        # Simple chain: Process -> Finalize
        workflow = chain(
            celery.signature('process_nifti_slices', args=[validation_result]),
            celery.signature('finalize_nifti_workflow')
        )
        
        result = workflow.apply_async()
        logger.info(f"NIfTI Workflow started with ID: {result.id}")
        
        return {'workflow_id': result.id}
        
    except Exception as e:
        logger.error(f"Failed to start NIfTI workflow: {e}")
        raise

__all__ = ['start_nifti_workflow']
