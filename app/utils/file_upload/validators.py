"""
File Upload Validators

Validation functions for file uploads.
"""
from typing import Tuple, Optional
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
import os

from app.utils.exceptions import FileUploadError


def validate_file_request(
    file: Optional[FileStorage],
    allowed_extensions: set
) -> Tuple[str, str]:
    """
    Validate file from request.
    
    Args:
        file: File from request.files
        allowed_extensions: Set of allowed extensions (e.g., {'.jpg', '.png'})
        
    Returns:
        Tuple of (original_filename, sanitized_filename)
        
    Raises:
        FileUploadError: If validation fails
    """
    if not file or file.filename == '':
        raise FileUploadError('No file provided')
    
    filename = file.filename
    file_ext = os.path.splitext(filename.lower())[1]
    
    if file_ext not in allowed_extensions:
        allowed_list = ', '.join(sorted(allowed_extensions))
        raise FileUploadError(
            f'File type not allowed. Allowed extensions: {allowed_list}'
        )
    
    sanitized_filename = secure_filename(filename)
    return filename, sanitized_filename
