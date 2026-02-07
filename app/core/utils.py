"""
Core Utilities (Shared)

Helper functions for various tasks.
"""
import logging
from app.core.uploads import upload_report_json

logger = logging.getLogger(__name__)

def upload_report_to_storage(
    report_data, 
    clinic_id, 
    patient_id, 
    report_type, 
    report_id, 
    logger_param=None,
    supabase=None
):
    """
    Wrapper to upload report JSON using core uploads.
    Maintains compatibility with legacy signature.
    """
    try:
        # Call the uploader
        result = upload_report_json(
            report=report_data,
            clinic_id=clinic_id,
            patient_id=patient_id,
            report_id=report_id,
            report_type=report_type,
            task_id=None
        )
        
        logger.info(f"✅ Report uploaded successfully: {result.get('public_url')}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to upload report: {e}")
        return {
            'success': False,
            'error': str(e)
        }
