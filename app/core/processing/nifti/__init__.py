"""
NIfTI Processing

Complete NIfTI to slices processing pipeline.
"""
from typing import Dict, Optional, Callable
import nibabel as nib
import numpy as np
import logging

from ..base import SliceGenerator

logger = logging.getLogger(__name__)


def process_nifti(
    file_path: str,
    output_dir: str,
    progress_callback: Optional[Callable] = None
) -> Dict:
    """
    Process NIfTI file to generate axial/coronal/sagittal slices.
    
    Args:
        file_path: Path to NIfTI file (.nii or .nii.gz)
        output_dir: Path to save slices
        progress_callback: Optional callback(view, current, total)
        
    Returns:
        dict: Processing result with:
            - status: 'success'
            - slice_counts: Dict with counts per view
            - voxel_sizes: Dict with x/y/z spacing
            - data_shape: List with volume dimensions
            - total_slices: Total number of slices generated
            
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is invalid or empty
        Exception: If processing fails
    """
    try:
        logger.info(f"Starting NIfTI processing: {file_path}")
        
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
        
        # 4. Generate slices
        slice_counts = SliceGenerator.generate_all_slices(
            volume, output_dir, progress_callback
        )
        
        result = {
            "status": "success",
            "message": "NIfTI file processed successfully",
            "slice_counts": slice_counts,
            "voxel_sizes": metadata,
            "data_shape": list(volume.shape),
            "total_slices": sum(slice_counts.values())
        }
        
        logger.info(f"✅ NIfTI processing completed: {result['total_slices']} slices")
        return result
        
    except Exception as e:
        logger.error(f"❌ NIfTI processing failed: {e}")
        raise


__all__ = ['process_nifti']
