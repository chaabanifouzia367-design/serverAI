
import logging
import os
from app.celery_app import celery
from app.services.job_status import JobStatusManager
from app.services.supabase_manager import update_report_status
from app import create_app
from flask import current_app

logger = logging.getLogger(__name__)

@celery.task(bind=True, name='process_nifti_slices')
def process_nifti_slices_task(self, validation_result):
    """
    Process NIfTI file: slice and upload to Supabase.
    """
    task_id = self.request.id
    try:
        app = create_app()
        with app.app_context():
            file_info = validation_result['file_info']
            file_path = file_info['path']
            clinic_id = validation_result.get('clinic_id')
            patient_id = validation_result.get('patient_id')
            report_id = validation_result.get('report_id')
            report_type = validation_result.get('report_type', 'nifti')
            
            if report_id:
                update_report_status(report_id, "processing_started")
            
            JobStatusManager.create_or_update_status(
                task_id, 'processing', 'Processing NIfTI slices...', 20
            )
            
            supabase = current_app.extensions.get('supabase')
            if not supabase:
                raise Exception("Supabase client not initialized")
            
            def progress_callback(view, current, total):
                if current % 20 == 0:
                    # Map progress roughly to 20-90% range
                    progress = 20 + int((current / total) * 70)
                    JobStatusManager.create_or_update_status(
                        task_id, 'processing', 
                        f'Generating {view} slices ({current}/{total})...', 
                        progress
                    )
            
            # Use existing NIfTI processing logic
            from app.core.processing.nifti.supabase import process_nifti_to_supabase
            
            result = process_nifti_to_supabase(
                file_path,
                supabase,
                clinic_id,
                patient_id,
                report_id,
                report_type,
                progress_callback
            )
            
            if report_id:
                update_report_status(report_id, "slices_uploaded")
            
            final_result = {
                'status': 'success',
                'slice_counts': result['slice_counts'],
                'total_slices': result['total_slices'],
                'voxel_sizes': result['voxel_sizes'],
                'data_shape': result['data_shape'],
                'report_id': report_id
            }
            
            JobStatusManager.create_or_update_status(
                task_id, 'completed', 
                f'Successfully processed {result["total_slices"]} slices', 
                100, final_result
            )
            
            logger.info(f"✅ NIfTI task completed for {report_id}")
            return final_result
            
    except Exception as e:
        error_msg = f"NIfTI processing error: {str(e)}"
        logger.error(error_msg)
        if 'report_id' in locals() and report_id:
            update_report_status(report_id, "failed")
        JobStatusManager.create_or_update_status(task_id, 'failed', error_msg, 0)
        raise

@celery.task(bind=True, name='finalize_nifti_workflow')
def finalize_nifti_workflow_task(self, result):
    """
    Finalize NIfTI workflow.
    """
    task_id = self.request.id
    try:
        app = create_app()
        with app.app_context():
            logger.info(f"Finalizing NIfTI workflow with result: {result}")
            
            # If result comes from a chain, it might be the result of previous task
            report_id = result.get('report_id')
             
            if report_id:
                supabase = current_app.extensions.get('supabase')
                if supabase:
                    try:
                         supabase.table('report_ai').update({'status': 'completed'}).eq('report_id', report_id).execute()
                    except Exception as e:
                        logger.warning(f"Could not update status in DB: {e}")

            JobStatusManager.create_or_update_status(
                task_id, 'completed', 'NIfTI workflow finished', 100, result
            )
            return result
            
    except Exception as e:
        logger.error(f"Finalization error: {e}")
        # Don't fail the whole workflow if just finalization fails, but log it
        raise
