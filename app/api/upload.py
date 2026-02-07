"""
Upload Routes

Handles file uploads for CBCT, Panoramic, and 3D medical reports.
"""
from flask import Blueprint, request, jsonify, current_app
from typing import Tuple, Callable
import os
import logging

from app.utils.exceptions import FileUploadError
from app.utils.file_upload import (
    validate_file_request,
    save_uploaded_file,
    extract_form_params,
    download_file_from_url
)
from app.utils.validators import validate_file_content
from app.services.supabase_manager import update_report_status
from app.domains.cbct.workflow import start_cbct_workflow
from app.domains.pano.workflow import start_pano_workflow
from app.domains.nifti.workflow import start_nifti_workflow



upload_bp = Blueprint('upload', __name__)
logger = logging.getLogger(__name__)

# Constants
MEDICAL_FILE_EXTENSIONS = {'.nii', '.nii.gz', '.dcm', '.dicom', '.ima'}
IMAGE_FILE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp'}
MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50 MB


from app.utils.queue_utils import is_queue_full # [NEW]

def _handle_file_upload(
    allowed_extensions: set,
    max_size: int,
    report_type: str,
    workflow_starter: Callable,
    validate_content: bool = False
) -> Tuple[dict, int]:

    # [NEW] Check queue size first
    if is_queue_full():
        return {'error': 'Server is busy. Too many requests. Please try again later.'}, 503

    try:
        # 1. Extract parameters first
        params = extract_form_params(request.form)
        report_id = params['report_id']
        
        # 2. Check if URL or direct file
        file_url = request.form.get('file_url')
        
        if file_url:
            # Download from URL
            logger.info(f"Downloading file from URL for {report_type} processing")
            try:
                download_info = download_file_from_url(
                    file_url,
                    current_app.config['UPLOAD_FOLDER']
                )
                save_path = download_info['filepath']
                sanitized_filename = download_info['filename']
                original_filename = download_info['filename']
                file_size = download_info['size']
                upload_id = params.get('upload_id', f"upload-{os.urandom(8).hex()}")
                
            except ValueError as e:
                if report_id:
                    update_report_status(report_id, "download_failed")
                return {'error': f'URL download failed: {str(e)}'}, 400
        else:
            # Direct file upload (existing logic)
            file = request.files.get('file')
            if not file:
                return {'error': 'No file or file_url provided'}, 400
            
            try:
                original_filename, sanitized_filename = validate_file_request(
                    file, allowed_extensions
                )
            except FileUploadError as e:
                return {'error': str(e)}, 400
        
        # 3. Update status
        if report_id:
            update_report_status(report_id, "file_uploaded")
        
        # 4. Save file (if not already downloaded from URL)
        if not file_url:
            try:
                save_path, file_size, upload_id = save_uploaded_file(
                    file,
                    sanitized_filename,
                    current_app.config['UPLOAD_FOLDER'],
                    params['upload_id'],
                    max_size
                )
            except FileUploadError as e:
                if report_id:
                    update_report_status(report_id, "file_too_large")
                return {'error': str(e)}, 400
        
        # 5. Validate file content (for medical files only)
        if validate_content:
            is_valid, validation_msg = validate_file_content(save_path, sanitized_filename)
            if not is_valid:
                os.remove(save_path)
                if report_id:
                    update_report_status(report_id, "invalid_file")
                return {'error': validation_msg}, 400
        
        # 6. Prepare file info
        file_info = {
            'path': save_path,
            'filename': sanitized_filename,
            'original_name': original_filename,
            'file_size': file_size
        }
        
        # 7. Start workflow
        task_info = workflow_starter(
            file_info,
            upload_id,
            params['clinic_id'],
            params['patient_id'],
            params['report_type'] or report_type,
            report_id
        )
        
        # 8. Return response
        return {
            'job_id': task_info['workflow_id'],
            'status': 'queued',
            'upload_id': upload_id,
            'report_id': report_id,
            'message': f'{report_type.upper()} file uploaded and processing workflow started',
            'file_info': {
                'filename': sanitized_filename,
                'file_size': file_size
            }
        }, 202
        
    except FileUploadError as e:
        logger.warning(f"File upload error: {e}")
        return {'error': str(e)}, 400
    except Exception as e:
        logger.error(f"Upload error in {report_type}: {e}", exc_info=True)
        return {'error': 'Internal server error'}, 500


@upload_bp.route('/cbct-report-generated', methods=['POST'])
def upload_cbct_report():
    response, status = _handle_file_upload(
        allowed_extensions=MEDICAL_FILE_EXTENSIONS,
        max_size=current_app.config['MAX_FILE_SIZE'],
        report_type='cbct',
        workflow_starter=start_cbct_workflow,
        validate_content=True
    )
    return jsonify(response), status


@upload_bp.route('/pano-report-generated', methods=['POST'])
def upload_pano_report():
    response, status = _handle_file_upload(
        allowed_extensions=IMAGE_FILE_EXTENSIONS,
        max_size=MAX_IMAGE_SIZE,
        report_type='pano',
        workflow_starter=start_pano_workflow,
        validate_content=False
    )
    return jsonify(response), status


@upload_bp.route('/nifti-slices', methods=['POST'])
def upload_nifti_slices():
    response, status = _handle_file_upload(
        allowed_extensions=MEDICAL_FILE_EXTENSIONS,
        max_size=current_app.config['MAX_FILE_SIZE'],
        report_type='nifti',
        workflow_starter=start_nifti_workflow,
        validate_content=True
    )
    return jsonify(response), status





@upload_bp.route('/', methods=['GET'])
def index():
    """API information endpoint."""
    return jsonify({
        'service': 'Medical File Processor',
        'version': '2.1',
        'status': 'running',
        'endpoints': {
            'cbct_upload': '/cbct-report-generated',
            'pano_upload': '/pano-report-generated',
            'nifti_upload': '/nifti-slices',

            'status': '/job-status/<job_id>',
            'health': '/health',
            'cleanup': '/cleanup'
        }
    })
