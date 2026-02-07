"""
NIfTI Processing with Supabase Upload

Complete NIfTI to Supabase processing pipeline.
"""
from typing import Dict, Optional, Callable
import nibabel as nib
import logging

from ..supabase_uploader import SupabaseSliceUploader

logger = logging.getLogger(__name__)


def process_nifti_to_supabase(
    file_path: str,
    supabase_client,
    clinic_id: str,
    patient_id: str,
    report_id: str,
    report_type: str = '3d',
    progress_callback: Optional[Callable] = None
) -> Dict:
    """
    Process NIfTI file and upload slices directly to Supabase.
    
    Args:
        file_path: Path to NIfTI file (.nii or .nii.gz)
        supabase_client: Supabase client instance
        clinic_id: Clinic identifier
        patient_id: Patient identifier
        report_id: Report identifier
        report_type: Type of report (default '3d')
        progress_callback: Optional callback(view, current, total)
        
    Returns:
        dict: Processing result with:
            - status: 'success'
            - slice_counts: Dict with counts per view
            - uploaded_urls: List of public URLs
            - voxel_sizes: Dict with x/y/z spacing
            - data_shape: List with volume dimensions
            - total_slices: Total number of slices uploaded
            - failed_uploads: Number of failed uploads
            
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is invalid or empty
        Exception: If processing fails
    """
    try:
        logger.info(f"Starting NIfTI processing with Supabase upload: {file_path}")
        
        # 1. Load NIfTI file
        nii_img = nib.load(file_path)
        volume = nii_img.get_fdata()
        
        # 2. Validate data
        if volume.size == 0:
            raise ValueError("Empty NIfTI data")
        
        logger.info(f"Loaded volume shape: {volume.shape}, dtype: {volume.dtype}")
        
        # 3. Extract metadata
        voxel_sizes = nii_img.header.get_zooms()
        metadata = {
            "x_spacing_mm": float(voxel_sizes[0]) if len(voxel_sizes) > 0 else 1.0,
            "y_spacing_mm": float(voxel_sizes[1]) if len(voxel_sizes) > 1 else 1.0,
            "z_spacing_mm": float(voxel_sizes[2]) if len(voxel_sizes) > 2 else 1.0
        }
        
        logger.info(f"Extracted voxel sizes: {metadata}")
        
        # 4. Upload slices to Supabase
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
            "message": "NIfTI file processed and uploaded to Supabase successfully",
            "slice_counts": upload_result['slice_counts'],
            "uploaded_urls": upload_result['uploaded_urls'],
            "voxel_sizes": metadata,
            "data_shape": list(volume.shape),
            "total_slices": upload_result['total_slices'],
            "failed_uploads": upload_result['failed_count']
        }
        
        logger.info(f"✅ NIfTI processing completed: {result['total_slices']} slices uploaded to Supabase")
        return result
        
    except Exception as e:
        logger.error(f"❌ NIfTI processing with Supabase upload failed: {e}")
        raise


__all__ = ['process_nifti_to_supabase']
