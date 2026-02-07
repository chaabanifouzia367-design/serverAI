"""
File Download from URL

Utility to download files from URLs for remote upload.
"""
import requests
import os
import logging
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def download_file_from_url(url: str, upload_folder: str, timeout: int = 60) -> dict:
    """
    Download file from URL to upload folder.
    
    Args:
        url: URL to download file from
        upload_folder: Folder to save downloaded file
        timeout: Download timeout in seconds (default: 60)
        
    Returns:
        dict: File information with filepath, filename, and size
        
    Raises:
        ValueError: If URL is invalid or download fails
        requests.RequestException: If network error
    """
    try:
        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme in ['http', 'https']:
            raise ValueError(f"Invalid URL scheme: {parsed.scheme}. Only http/https allowed.")
        
        logger.info(f"Downloading file from URL: {url}")
        
        # Download with streaming
        response = requests.get(url, stream=True, timeout=timeout)
        response.raise_for_status()
        
        # Extract filename from URL or Content-Disposition header
        filename = None
        if 'Content-Disposition' in response.headers:
            content_disp = response.headers['Content-Disposition']
            if 'filename=' in content_disp:
                filename = content_disp.split('filename=')[-1].strip('"')
        
        if not filename:
            filename = os.path.basename(parsed.path) or 'downloaded_file.nii'
        
        # Ensure upload folder exists
        os.makedirs(upload_folder, exist_ok=True)
        
        # Save file
        filepath = os.path.join(upload_folder, filename)
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        file_size = os.path.getsize(filepath)
        
        logger.info(f"File downloaded successfully: {filename} ({file_size} bytes)")
        
        return {
            'filepath': filepath,
            'filename': filename,
            'size': file_size
        }
        
    except requests.exceptions.Timeout:
        raise ValueError(f"Download timeout after {timeout} seconds")
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Download failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error downloading file: {e}")
        raise ValueError(f"Failed to download file: {str(e)}")


__all__ = ['download_file_from_url']
