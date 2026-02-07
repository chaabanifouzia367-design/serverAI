"""
Panoramic Image Processing Tasks (V2)

All pano workflow tasks consolidated in one file for simplicity.
"""
from app.celery_app import celery
from app.services.job_status import JobStatusManager
from app.services.supabase_manager import update_report_status
from app.services.uploads import SupabaseUploadManager
from app import create_app
import os
import logging

logger = logging.getLogger(__name__)


import time

@celery.task(bind=True, name='test_sleep_task')
def test_sleep_task(self, duration=10):
    """Simulate a long running task."""
    task_id = self.request.id
    try:
        JobStatusManager.create_or_update_status(
            task_id, 'processing', f'Sleeping for {duration} seconds...', 0
        )
       
        for i in range(duration):
            time.sleep(1)
            JobStatusManager.create_or_update_status(
                task_id, 'processing', f'Sleeping for {duration} seconds...', i * 100 / duration
            )
        JobStatusManager.create_or_update_status(
            task_id, 'completed', 'Sleep completed', 100, {'duration': duration}
        )
        return {'status': 'completed', 'duration': duration}
    except Exception as e:
        JobStatusManager.create_or_update_status(task_id, 'failed', str(e), 0)
        raise e

@celery.task(bind=True, name='validate_pano_v2')
def validate_pano_task(self, file_info, report_id):
    """Validate panoramic image file."""
    task_id = self.request.id
    try:
        app = create_app()
        with app.app_context():
            JobStatusManager.create_or_update_status(
                task_id, 'processing', 'Validating pano image...', 10
            )
            
            # Simple validation - check file exists
            file_path = file_info.get('path')
            if not file_path or not os.path.exists(file_path):
                raise FileNotFoundError(f'Pano file not found: {file_path}')
            
            result = {
                'status': 'validated',
                'message': 'Pano image validated successfully',
                'file_info': file_info,
                'report_id': report_id
            }
            
            JobStatusManager.create_or_update_status(
                task_id, 'completed', 'Validation completed', 20, result
            )
            return result
            
    except Exception as e:
        error_msg = f"Pano validation error: {str(e)}"
        JobStatusManager.create_or_update_status(task_id, 'failed', error_msg, 0)
        raise


@celery.task(bind=True, name='upload_pano_v2')
def upload_pano_task(self, validation_result, clinic_id, patient_id, report_id):
    """Upload panoramic image to Supabase storage."""
    task_id = self.request.id
    try:
        app = create_app()
        with app.app_context():
            JobStatusManager.create_or_update_status(
                task_id, 'processing', 'Uploading pano image...', 30
            )
            
            file_info = validation_result.get('file_info', {})
            image_path = file_info.get('path')
            
            if not image_path or not os.path.exists(image_path):
                raise FileNotFoundError(f'Pano image not found: {image_path}')
            
            # Read image bytes
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            
            # Upload to Supabase
            uploader = SupabaseUploadManager(task_id=task_id)
            upload_result = uploader.upload_pano_image_bytes(
                image_bytes=image_bytes,
                filename='original.png',  # Always use original.png
                clinic_id=clinic_id,
                patient_id=patient_id,
                report_id=report_id
            )
            
            result = {
                'status': 'uploaded',
                'message': 'Pano image uploaded successfully',
                'file_info': file_info,
                'upload_result': upload_result,
                'clinic_id': clinic_id,
                'patient_id': patient_id,
                'report_id': report_id
            }
            
            JobStatusManager.create_or_update_status(
                task_id, 'completed', 'Upload completed', 50, result
            )
            return result
            
    except Exception as e:
        error_msg = f"Pano upload error: {str(e)}"
        JobStatusManager.create_or_update_status(task_id, 'failed', error_msg, 0)
        raise


@celery.task(bind=True, name='analyze_pano_v2')
def analyze_pano_task(self, upload_result, report_id):
    """
    Analyze panoramic image with AI (placeholder for now).
    
    When ready to use AI:
    1. Uncomment the AI integration code below
    2. Configure your models in app/ai/config.py
    3. Implement model.predict() in pano_analyzer.py
    """
    task_id = self.request.id
    try:
        app = create_app()
        with app.app_context():
            JobStatusManager.create_or_update_status(
                task_id, 'processing', ' 👌👌 Analyzing pano image...', 60
            )
            
            # Extract data
            file_info = upload_result.get('file_info', {})
            image_path = file_info.get('path')
            clinic_id = upload_result.get('clinic_id')
            patient_id = upload_result.get('patient_id')

            from app.domains.pano.logic import analyze_and_upload
            from app.domains.pano.config import SEGMENTATION_CONFIG, MULTIPROBLEM_DETECTION_CONFIG, DETECTION_STRATEGY
            from app.services.model_manager import ModelManager

            active_models = ModelManager.get_active_model() # Returns dict now
            
            detection_config_to_use = MULTIPROBLEM_DETECTION_CONFIG
            if active_models and 'pano_detection' in active_models:
                m = active_models['pano_detection']
                logger.info(f"🚀 Using Dynamic Pano Detection: {m['name']}")
                detection_config_to_use = [{
                    'name': m['name'],
                    'path': m['path'],
                    'threshold': m.get('threshold', 0.5)
                }]
                
            # 2. Pano Segmentation
            segmentation_config_to_use = SEGMENTATION_CONFIG
            if active_models and 'pano_segmentation' in active_models:
                m = active_models['pano_segmentation']
                logger.info(f"🚀 Using Dynamic Pano Segmentation: {m['name']}")
                segmentation_config_to_use = {
                    'path': m['path'],
                    'threshold': m.get('threshold', 0.5)
                }
            
            # Patient info (fetch from DB or construct)
            patient_info = {
                "patientId": patient_id,
                "info": {
                    "fullName": "",
                    "dateOfBirth": "",
                    "age": 0,
                    "lastScanDate": "",
                    "gender": "",
                    "bloodType": "",
                    "allergies": [],
                    "medicalHistory": []
                }
            }
            
            # Execute complete workflow: AI → Report → Upload
            logger.info(f"🔬 Starting AI analysis for pano report {report_id} (Strategy: {DETECTION_STRATEGY})")
            workflow_result = analyze_and_upload(
                image_path=image_path,
                patient_info=patient_info,
                clinic_id=clinic_id,
                patient_id=patient_id,
                report_id=report_id,
                segmentation_config=segmentation_config_to_use, # Uses dynamic config if set
                detection_config=detection_config_to_use,  # Uses dynamic config if set
                detection_strategy=DETECTION_STRATEGY,
                task_id=task_id
            )
            
            result = {
                'status': 'analyzed',
                'message': f'Pano AI analysis completed (status: {workflow_result["ai_status"]})',
                'report_id': report_id,
                'ai_status': workflow_result['ai_status'],
                'report': workflow_result.get('report'),
                'upload_result': workflow_result.get('upload_result'),
                'ai_summary': workflow_result.get('ai_summary')
            }
            
            JobStatusManager.create_or_update_status(
                task_id, 'completed', ' 👌👌 Analysis completed', 80, result
            )
            return result
            
    except Exception as e:
        error_msg = f"Pano analysis error: {str(e)}"
        JobStatusManager.create_or_update_status(task_id, 'failed', error_msg, 0)
        raise


@celery.task(bind=True, name='aggregate_pano_v2')
def aggregate_pano_task(self, analysis_result, file_info, upload_id, clinic_id, patient_id, report_id):
    """Aggregate pano workflow results."""
    task_id = self.request.id
    try:
        app = create_app()
        with app.app_context():
            if report_id:
                update_report_status(report_id, "completed")
            
            JobStatusManager.create_or_update_status(
                task_id, 'processing', ' 👌👌 Finalizing pano workflow...', 90
            )
            
            final_result = {
                'status': 'completed',
                'message': ' 👌👌 Pano workflow completed successfully',
                'file_info': file_info,
                'clinic_id': clinic_id,
                'patient_id': patient_id,
                'report_type': 'pano',
                'upload_id': upload_id,
                'report_id': report_id,
                'analysis_result': analysis_result,
                'workflow_completed': True
            }
            
            JobStatusManager.create_or_update_status(
                task_id, 'completed', ' 👌👌 Workflow completed', 100, final_result
            )
            return final_result
            
    except Exception as e:
        error_msg = f"Pano aggregation error: {str(e)}"
        if report_id:
            update_report_status(report_id, "failed")
        JobStatusManager.create_or_update_status(task_id, 'failed', error_msg, 0)
        raise
