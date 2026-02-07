"""
DICOM Processing

Complete DICOM to slices processing pipeline.
"""
from typing import Dict, Optional, Callable
import logging

from .loader import DICOMLoader
from .volume import DICOMVolumeCreator
from ..base import SliceGenerator

logger = logging.getLogger(__name__)


def process_dicom(
    directory: str,
    output_dir: str,
    progress_callback: Optional[Callable] = None
) -> Dict:
    """
    Process DICOM directory to generate axial/coronal/sagittal slices.
    
    Args:
        directory: Path to DICOM directory
        output_dir: Path to save slices
        progress_callback: Optional callback(view, current, total)
        
    Returns:
        dict: Processing result with:
            - status: 'success'
            - slice_counts: Dict with counts per view
            - voxel_sizes: Dict with x/y/z spacing
            - data_shape: List with volume dimensions
            - total_slices: Total number of slices generated
            - dicom_files_processed: Number of valid DICOM files
            - failed_files: Number of failed files
            
    Raises:
        ValueError: If no valid DICOM files found
        Exception: If processing fails
    """
    try:
        logger.info(f"Starting DICOM processing: {directory}")
        
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
        
        # 6. Generate slices
        slice_counts = SliceGenerator.generate_all_slices(
            volume, output_dir, progress_callback
        )
        
        result = {
            "status": "success",
            "message": "DICOM files processed successfully",
            "slice_counts": slice_counts,
            "voxel_sizes": metadata,
            "data_shape": list(volume.shape),
            "total_slices": sum(slice_counts.values()),
            "dicom_files_processed": len(sorted_slices),
            "failed_files": len(failed_files)
        }
        
        logger.info(f"✅ DICOM processing completed: {result['total_slices']} slices")
        return result
        
    except Exception as e:
        logger.error(f"❌ DICOM processing failed: {e}")
        raise


__all__ = ['process_dicom']
