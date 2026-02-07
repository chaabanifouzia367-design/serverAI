"""
File Upload Helpers

Helper functions for file upload operations.
"""
from typing import Dict, Optional


def extract_form_params(form_data) -> Dict[str, Optional[str]]:
    """
    Extract common form parameters from request.
    
    Args:
        form_data: Flask request.form object
        
    Returns:
        Dictionary with extracted parameters
    """
    return {
        'upload_id': form_data.get('upload_id'),
        'clinic_id': form_data.get('clinic_id'),
        'patient_id': form_data.get('patient_id'),
        'report_type': form_data.get('report_type'),
        'report_id': form_data.get('report_id'),
    }
