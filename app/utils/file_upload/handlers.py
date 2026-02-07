"""
File Upload Handlers

Functions for saving and managing uploaded files.
"""
from typing import Tuple, Optional
from werkzeug.datastructures import FileStorage
import os
import uuid

from app.utils.exceptions import FileUploadError


def get_file_size(file: FileStorage) -> int:
    """
    Get file size by seeking to end.
    
    Args:
        file: File to measure
        
    Returns:
        File size in bytes
    """
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)  # Reset to beginning
    return size


def save_uploaded_file(
    file: FileStorage,
    filename: str,
    upload_folder: str,
    upload_id: Optional[str] = None,
    max_size: Optional[int] = None
) -> Tuple[str, int, str]:
    """
    Save uploaded file to disk with validation.
    
    Args:
        file: File to save
        filename: Sanitized filename
        upload_folder: Folder to save in
        upload_id: Optional upload ID (generated if not provided)
        max_size: Maximum file size in bytes
        
    Returns:
        Tuple of (save_path, file_size, upload_id)
        
    Raises:
        FileUploadError: If file too large or save fails
    """
    upload_id = upload_id or str(uuid.uuid4())
    file_size = get_file_size(file)
    
    # Check file size
    if max_size and file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise FileUploadError(f'File too large. Maximum size: {max_mb:.1f} MB')
    
    # Create save path
    save_path = os.path.join(upload_folder, f"{upload_id}_{filename}")
    
    # Save file
    try:
        file.save(save_path)
    except Exception as e:
        raise FileUploadError(f'Failed to save file: {str(e)}')
    
    return save_path, file_size, upload_id
