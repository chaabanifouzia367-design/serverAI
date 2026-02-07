import logging
import json
import os
from datetime import datetime
from app.celery_app import celery
from app.services.job_status import JobStatusManager
from app.services.supabase_manager import update_report_status
from app import create_app
from flask import current_app

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------------
# 1. AI Analysis
# -------------------------------------------------------------------------

@celery.task(bind=True, name='ai_analysis')
def ai_analysis_task(self, validation_result):
    task_id = self.request.id
    try:
        app = create_app()
        with app.app_context():
            file_info = validation_result['file_info']
            clinic_id = validation_result.get('clinic_id')
            patient_id = validation_result.get('patient_id')
            report_id = validation_result.get('report_id')
            upload_id = validation_result.get('upload_id')
            report_type = validation_result.get('report_type', 'cbct')
            
            # Update status
            if report_id:
                update_report_status(report_id, "ai_started")
            
            JobStatusManager.create_or_update_status(
                task_id, 'processing', 'Running AI analysis...', 40
            )
            
            # Call Model Center
            ai_result = None
            try:
                from app.domains.cbct.pipeline import complete_medical_processing_aiReport_task
                
                # Get supabase client
                supabase = current_app.extensions.get('supabase')
                if not supabase:
                    raise Exception("Supabase client not initialized")
                
                # Call pipeline
                ai_result = complete_medical_processing_aiReport_task(
                    logger,      
                    file_info, 
                    upload_id, 
                    clinic_id, 
                    patient_id, 
                    report_type, 
                    report_id,
                    supabase    
                )
                
                if report_id:
                    update_report_status(report_id, "completed")
                    
                logger.info(f"✅ AI analysis completed for report {report_id}")
                
            except ImportError as e:
                logger.warning(f"AI pipeline not available: {e}")
                ai_result = {'status': 'skipped', 'message': 'AI pipeline not available'}
                if report_id:
                    update_report_status(report_id, "skipped")
            except Exception as e:
                logger.error(f"AI pipeline error: {e}")
                ai_result = {'status': 'failed', 'message': str(e)}
                if report_id:
                    update_report_status(report_id, "failed")
            
            result = {
                'ai_result': ai_result,
                'file_info': file_info,
                'clinic_id': clinic_id,
                'patient_id': patient_id,
                'report_id': report_id,
                'report_type': report_type,
                'upload_id': upload_id
            }
            
            JobStatusManager.create_or_update_status(
                task_id, 'completed', 'AI analysis completed', 100, result
            )
            return result
            
    except Exception as e:
        error_msg = f"AI analysis error: {str(e)}"
        logger.error(error_msg)
        if 'report_id' in locals() and report_id:
            update_report_status(report_id, "failed")
        JobStatusManager.create_or_update_status(task_id, 'failed', error_msg, 0)
        raise


# -------------------------------------------------------------------------
# 2. Format Report
# -------------------------------------------------------------------------

@celery.task(bind=True, name='format_report')
def format_report_task(self, ai_result_dict):
    """Format AI results into report structure."""
    task_id = self.request.id
    try:
        JobStatusManager.create_or_update_status(
            task_id, 'processing', 'Formatting AI report...', 50
        )
        
        ai_result = ai_result_dict.get('ai_result', {})
        report_id = ai_result_dict.get('report_id')
        clinic_id = ai_result_dict.get('clinic_id')
        patient_id = ai_result_dict.get('patient_id')
        report_type = ai_result_dict.get('report_type', 'cbct')
        
        # Format report
        report = {
            'report_id': report_id,
            'clinic_id': clinic_id,
            'patient_id': patient_id,
            'report_type': report_type,
            'ai_analysis': ai_result,
            'timestamp': datetime.utcnow().isoformat(),
            'version': '2.0',
            'generated_by': 'medical_processor_v2'
        }
        
        result = {
            'report': report,
            'report_id': report_id,
            'clinic_id': clinic_id,
            'patient_id': patient_id,
            'report_type': report_type
        }
        
        JobStatusManager.create_or_update_status(
            task_id, 'completed', 'Report formatted', 100, result
        )
        logger.info(f"✅ Report formatted for {report_id}")
        return result
        
    except Exception as e:
        error_msg = f"Report formatting error: {str(e)}"
        logger.error(error_msg)
        JobStatusManager.create_or_update_status(task_id, 'failed', error_msg, 0)
        raise


# -------------------------------------------------------------------------
# 3. Upload Report
# -------------------------------------------------------------------------

@celery.task(bind=True, name='upload_report_json')
def upload_report_json_task(self, report_dict):
    """Upload report JSON to Supabase storage."""
    task_id = self.request.id
    try:
        app = create_app()
        with app.app_context():
            report = report_dict['report']
            report_id = report_dict['report_id']
            clinic_id = report_dict['clinic_id']
            patient_id = report_dict['patient_id']
            report_type = report_dict['report_type']
            
            if report_id:
                update_report_status(report_id, "report_upload_started")
            
            JobStatusManager.create_or_update_status(
                task_id, 'processing', 'Uploading report to Supabase...', 60
            )
            
            # Convert to JSON
            report_json = json.dumps(report, indent=2)
            storage_path = f"{clinic_id}/{patient_id}/{report_type}/{report_id}/report.json"
            
            supabase = current_app.extensions.get('supabase')
            if not supabase:
                raise Exception("Supabase client not initialized")
            
            supabase.storage.from_('reports').upload(
                path=storage_path,
                file=report_json.encode('utf-8'),
                file_options={"content-type": "application/json", "upsert": "true"}
            )
            
            public_url = supabase.storage.from_('reports').get_public_url(storage_path)
            
            if report_id:
                update_report_status(report_id, "report_uploaded")
            
            result = {
                'status': 'report_uploaded',
                'report_url': public_url,
                'report_id': report_id,
                'storage_path': storage_path
            }
            
            JobStatusManager.create_or_update_status(
                task_id, 'completed', 'Report uploaded to Supabase', 100, result
            )
            logger.info(f"✅ Report uploaded: {public_url}")
            return result
            
    except Exception as e:
        error_msg = f"Report upload error: {str(e)}"
        logger.error(error_msg)
        if 'report_id' in locals() and report_id:
            update_report_status(report_id, "report_upload_failed")
        JobStatusManager.create_or_update_status(task_id, 'failed', error_msg, 0)
        raise


# -------------------------------------------------------------------------
# 4. Upload Slices
# -------------------------------------------------------------------------

@celery.task(bind=True, name='upload_slices')
def upload_slices_task(self, validation_result):
    """Process file and upload slices to Supabase."""
    task_id = self.request.id
    try:
        app = create_app()
        with app.app_context():
            file_info = validation_result['file_info']
            file_path = file_info['path']
            clinic_id = validation_result.get('clinic_id')
            patient_id = validation_result.get('patient_id')
            report_id = validation_result.get('report_id')
            report_type = validation_result.get('report_type', 'cbct')
            
            if report_id:
                update_report_status(report_id, "slice_upload_started")
            
            JobStatusManager.create_or_update_status(
                task_id, 'processing', 'Processing and uploading slices...', 30
            )
            
            supabase = current_app.extensions.get('supabase')
            if not supabase:
                raise Exception("Supabase client not initialized")
            
            def progress_callback(view, current, total):
                if current % 50 == 0:
                    progress = 30 + int((current / total) * 50)
                    JobStatusManager.create_or_update_status(
                        task_id, 'processing', 
                        f'Uploading {view} slices ({current}/{total})...', 
                        progress
                    )
            
            # Detect file type and process
            if file_path.endswith(('.nii', '.nii.gz')):
                # NOTE: Updated to app.core.processing
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
            else:  # DICOM
                if os.path.isfile(file_path):
                    dicom_dir = os.path.dirname(file_path)
                else:
                    dicom_dir = file_path
                
                # NOTE: Updated to app.core.processing
                from app.core.processing.dicom.supabase import process_dicom_to_supabase
                result = process_dicom_to_supabase(
                    dicom_dir,
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
                'status': 'slices_uploaded',
                'slice_counts': result['slice_counts'],
                'total_slices': result['total_slices'],
                'voxel_sizes': result['voxel_sizes'],
                'data_shape': result['data_shape'],
                'report_id': report_id
            }
            
            JobStatusManager.create_or_update_status(
                task_id, 'completed', 
                f'{result["total_slices"]} slices uploaded to Supabase', 
                100, final_result
            )
            logger.info(f"✅ Uploaded {result['total_slices']} slices for report {report_id}")
            return final_result
            
    except Exception as e:
        error_msg = f"Slice upload error: {str(e)}"
        logger.error(error_msg)
        if 'report_id' in locals() and report_id:
            update_report_status(report_id, "slice_upload_failed")
        JobStatusManager.create_or_update_status(task_id, 'failed', error_msg, 0)
        raise


# -------------------------------------------------------------------------
# 5. Finalize Report
# -------------------------------------------------------------------------

@celery.task(bind=True, name='finalize_report')
def finalize_report_task(self, results):
    """Aggregate results and update report status to completed."""
    task_id = self.request.id
    try:
        app = create_app()
        with app.app_context():
            JobStatusManager.create_or_update_status(
                task_id, 'processing', 'Finalizing workflow...', 90
            )
            
            # Extract results from group
            if isinstance(results, (list, tuple)) and len(results) == 2:
                report_result = results[0] if isinstance(results[0], dict) else {}
                slices_result = results[1] if isinstance(results[1], dict) else {}
            else:
                report_result = {}
                slices_result = results if isinstance(results, dict) else {}
            
            report_id = (
                report_result.get('report_id') or 
                slices_result.get('report_id')
            )
            
            if not report_id:
                raise ValueError("No report_id found in results")
            
            supabase = current_app.extensions.get('supabase')
            if not supabase:
                raise Exception("Supabase client not initialized")
            
            update_data = {'status': 'completed'}
            
            if report_result.get('report_url'):
                 logger.info(f"Report URL generated: {report_result['report_url']}")
            
            if slices_result.get('slice_counts'):
                 logger.info(f"Slice counts calculated: {slices_result['slice_counts']}")
            
            # Update Supabase
            try:
                supabase.table('report_ai').update(update_data).eq('report_id', report_id).execute()
                logger.info(f"✅ Updated report {report_id} to completed status")
            except Exception as e:
                logger.warning(f"Failed to update Supabase table: {e}")
            
            final_result = {
                'status': 'completed',
                'report_id': report_id,
                'message': 'Workflow completed successfully',
                'report_url': report_result.get('report_url'),
                'slice_counts': slices_result.get('slice_counts'),
                'total_slices': slices_result.get('total_slices'),
                'workflow_completed': True
            }
            
            JobStatusManager.create_or_update_status(
                task_id, 'completed', 'Workflow finalized', 100, final_result
            )
            logger.info(f"🎉 Workflow completed for report {report_id}")
            return final_result
            
    except Exception as e:
        error_msg = f"Finalization error: {str(e)}"
        logger.error(error_msg)
        JobStatusManager.create_or_update_status(task_id, 'failed', error_msg, 0)
        raise
