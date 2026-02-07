"""
DICOM Processing with Supabase Upload

Complete DICOM to Supabase processing pipeline.
"""
from typing import Dict, Optional, Callable
import logging

from .loader import DICOMLoader
from .volume import DICOMVolumeCreator
from ..supabase_uploader import SupabaseSliceUploader

logger = logging.getLogger(__name__)


def process_dicom_to_supabase(
    directory: str,
    supabase_client,
    clinic_id: str,
    patient_id: str,
    report_id: str,
    report_type: str = 'cbct',
    progress_callback: Optional[Callable] = None
) -> Dict:
    """
    Process DICOM directory and upload slices directly to Supabase.
    
    Args:
        directory: Path to DICOM directory
        supabase_client: Supabase client instance
        clinic_id: Clinic identifier
        patient_id: Patient identifier
        report_id: Report identifier
        report_type: Type of report (default 'cbct')
        progress_callback: Optional callback(view, current, total)
        
    Returns:
        dict: Processing result with:
            - status: 'success'
            - slice_counts: Dict with counts per view
            - uploaded_urls: List of public URLs
            - voxel_sizes: Dict with x/y/z spacing
            - data_shape: List with volume dimensions
            - total_slices: Total number of slices uploaded
            - dicom_files_processed: Number of valid DICOM files
            - failed_files: Number of failed files
            - failed_uploads: Number of failed uploads
            
    Raises:
        ValueError: If no valid DICOM files found
        Exception: If processing fails
    """
    try:
        logger.info(f"Starting DICOM processing with Supabase upload: {directory}")
        
        # 1. Find DICOM files
        dicom_files = DICOMLoader.find_dicom_files(directory)
        if not dicom_files:
            raise ValueError("No DICOM files found in directory")
        
        # 2. Load and validate
        valid_slices, failed_files = DICOMLoader.load_and_validate(dicom_files)
        if not valid_slices:
            raise ValueError("No valid DICOM slices could be loaded")
        
        # 3. Sort slices
        sorted_slices = DICOMLoader.sort_slices(valid_slices)
        
        # 4. Create 3D volume
        volume = DICOMVolumeCreator.create_volume(sorted_slices)
        
        # 5. Extract metadata
        metadata = DICOMVolumeCreator.extract_metadata(sorted_slices[0][0])
        
        # 6. Upload slices to Supabase
        uploader = SupabaseSliceUploader(supabase_client)
        upload_result = uploader.upload_all_slices(
            volume,
            clinic_id,
            patient_id,
            report_id,
            report_type,
            progress_callback
        )
        
        result = {
            "status": "success",
            "message": "DICOM files processed and uploaded to Supabase successfully",
            "slice_counts": upload_result['slice_counts'],
            "uploaded_urls": upload_result['uploaded_urls'],
            "voxel_sizes": metadata,
            "data_shape": list(volume.shape),
            "total_slices": upload_result['total_slices'],
            "dicom_files_processed": len(sorted_slices),
            "failed_files": len(failed_files),
            "failed_uploads": upload_result['failed_count']
        }
        
        logger.info(f"✅ DICOM processing completed: {result['total_slices']} slices uploaded to Supabase")
        return result
        
    except Exception as e:
        logger.error(f"❌ DICOM processing with Supabase upload failed: {e}")
        raise


__all__ = ['process_dicom_to_supabase']
