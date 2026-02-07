"""
Base Processing Classes

Shared logic for medical file processing.
"""
from typing import Dict, Optional, Callable
import numpy as np
from PIL import Image
import os
import logging

logger = logging.getLogger(__name__)


class SliceGenerator:
    """Base class for generating 2D slices from 3D volume."""
    
    VIEWS = ['axial', 'coronal', 'sagittal']
    AXES = {'axial': 2, 'coronal': 1, 'sagittal': 0}
    
    @staticmethod
    def normalize_volume(volume: np.ndarray) -> np.ndarray:
        """
        Normalize volume to 0-255 range.
        
        Args:
            volume: 3D numpy array
            
        Returns:
            Normalized volume as uint8
        """
        volume_min, volume_max = volume.min(), volume.max()
        
        if volume_max == volume_min:
            logger.warning("Constant intensity volume detected")
            return np.zeros_like(volume, dtype=np.uint8)
        
        normalized = (volume - volume_min) / (volume_max - volume_min) * 255
        return normalized.astype(np.uint8)
    
    @staticmethod
    def extract_slice(volume: np.ndarray, axis: int, index: int) -> np.ndarray:
        """
        Extract 2D slice from volume along specified axis.
        
        Args:
            volume: 3D numpy array
            axis: 0=sagittal, 1=coronal, 2=axial
            index: Slice index
            
        Returns:
            2D slice array
        """
        if axis == 0:
            return volume[index, :, :]
        elif axis == 1:
            return volume[:, index, :]
        else:  # axis == 2
            return volume[:, :, index]
    
    @staticmethod
    def is_valid_slice(slice_data: np.ndarray) -> bool:
        """
        Check if slice has meaningful content.
        
        Args:
            slice_data: 2D slice array
            
        Returns:
            True if slice has content
        """
        return np.any(slice_data) and np.std(slice_data) > 1
    
    @staticmethod
    def save_slice(
        slice_data: np.ndarray,
        output_dir: str,
        view: str,
        index: int,
        quality: int = 85
    ) -> Optional[str]:
        """
        Save 2D slice as JPEG image.
        
        Args:
            slice_data: 2D slice array
            output_dir: Base output directory
            view: View name (axial/coronal/sagittal)
            index: Slice index for filename
            quality: JPEG quality (1-100)
            
        Returns:
            Path to saved file or None if invalid
        """
        # Validate slice
        if not SliceGenerator.is_valid_slice(slice_data):
            return None
        
        # Create view directory
        view_dir = os.path.join(output_dir, view)
        os.makedirs(view_dir, exist_ok=True)
        
        # Save image
        img = Image.fromarray(slice_data, mode='L')
        slice_path = os.path.join(view_dir, f"{index}.jpg")
        img.save(slice_path, quality=quality, optimize=True)
        
        return slice_path
    
    @staticmethod
    def generate_all_slices(
        volume: np.ndarray,
        output_dir: str,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, int]:
        """
        Generate slices for all views (axial, coronal, sagittal).
        
        Args:
            volume: 3D numpy array
            output_dir: Base output directory
            progress_callback: Optional callback(view, current, total)
            
        Returns:
            Dictionary with slice counts per view
        """
        volume_normalized = SliceGenerator.normalize_volume(volume)
        slice_counts = {}
        
        for view in SliceGenerator.VIEWS:
            axis = SliceGenerator.AXES[view]
            slice_count = volume_normalized.shape[axis]
            saved_count = 0
            
            logger.info(f"Generating {slice_count} {view} slices...")
            
            for i in range(slice_count):
                slice_data = SliceGenerator.extract_slice(volume_normalized, axis, i)
                
                if SliceGenerator.save_slice(slice_data, output_dir, view, saved_count):
                    saved_count += 1
                
                # Progress callback
                if progress_callback and i % 20 == 0:
                    progress_callback(view, i, slice_count)
            
            slice_counts[view] = saved_count
            logger.info(f"✅ Created {saved_count} {view} slices")
        
        return slice_counts
