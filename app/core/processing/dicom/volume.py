"""
DICOM Volume Creator

Create 3D volume from DICOM slices.
"""
import numpy as np
from typing import List, Tuple, Dict
import logging

logger = logging.getLogger(__name__)


class DICOMVolumeCreator:
    """Create 3D volume from DICOM slices."""
    
    @staticmethod
    def create_volume(slices: List[Tuple]) -> np.ndarray:
        """
        Create 3D volume from sorted DICOM slices.
        
        Args:
            slices: List of (dataset, file_path, pixel_array)
            
        Returns:
            3D numpy array (stacked along axis 2)
        """
        pixel_data_list = []
        
        for ds, file_path, pixel_array in slices:
            try:
                # Apply rescaling if available
                if hasattr(ds, 'RescaleSlope') and hasattr(ds, 'RescaleIntercept'):
                    slope = float(ds.RescaleSlope) if ds.RescaleSlope else 1.0
                    intercept = float(ds.RescaleIntercept) if ds.RescaleIntercept else 0.0
                    pixel_array = pixel_array.astype(np.float64) * slope + intercept
                
                # Ensure consistent data type
                pixel_array = pixel_array.astype(np.float64)
                pixel_data_list.append(pixel_array)
                
            except Exception as e:
                logger.warning(f"Error processing slice {file_path}: {e}")
                continue
        
        if not pixel_data_list:
            raise ValueError("No valid pixel data to create volume")
        
        # Stack into 3D volume
        volume = np.stack(pixel_data_list, axis=2)
        logger.info(f"Created volume shape: {volume.shape}, dtype: {volume.dtype}")
        
        return volume
    
    @staticmethod
    def extract_metadata(first_slice) -> Dict[str, float]:
        """
        Extract voxel spacing metadata from first slice.
        
        Args:
            first_slice: First DICOM dataset
            
        Returns:
            Dictionary with x/y/z spacing in mm
        """
        try:
            pixel_spacing = getattr(first_slice, 'PixelSpacing', [1.0, 1.0])
            slice_thickness = getattr(first_slice, 'SliceThickness', 1.0)
            
            # Parse pixel spacing
            if isinstance(pixel_spacing, (list, tuple)) and len(pixel_spacing) >= 2:
                x_spacing = float(pixel_spacing[0])
                y_spacing = float(pixel_spacing[1])
            else:
                x_spacing = y_spacing = 1.0
            
            # Parse slice thickness
            z_spacing = float(slice_thickness) if slice_thickness else 1.0
            
            metadata = {
                "x_spacing_mm": x_spacing,
                "y_spacing_mm": y_spacing,
                "z_spacing_mm": z_spacing
            }
            
            logger.info(f"Extracted voxel sizes: {metadata}")
            return metadata
            
        except Exception as e:
            logger.warning(f"Failed to extract metadata: {e}, using defaults")
            return {
                "x_spacing_mm": 1.0,
                "y_spacing_mm": 1.0,
                "z_spacing_mm": 1.0
            }
