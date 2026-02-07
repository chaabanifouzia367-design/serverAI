"""
Supabase Slice Uploader

Upload slices directly to Supabase storage without saving locally.
"""
from typing import Dict, Optional, Callable, List
import numpy as np
from PIL import Image
import io
import logging
from flask import current_app

logger = logging.getLogger(__name__)


class SupabaseSliceUploader:
    
    VIEWS = ['axial', 'coronal', 'sagittal']
    AXES = {'axial': 2, 'coronal': 1, 'sagittal': 0}
    
    def __init__(self, supabase_client):
        """
        Initialize uploader.
        
        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
    
    @staticmethod
    def normalize_volume(volume: np.ndarray) -> np.ndarray:
        """Normalize volume to 0-255 range."""
        volume_min, volume_max = volume.min(), volume.max()
        
        if volume_max == volume_min:
            logger.warning("Constant intensity volume detected")
            return np.zeros_like(volume, dtype=np.uint8)
        
        normalized = (volume - volume_min) / (volume_max - volume_min) * 255
        return normalized.astype(np.uint8)
    
    @staticmethod
    def extract_slice(volume: np.ndarray, axis: int, index: int) -> np.ndarray:
        """Extract 2D slice from volume along specified axis."""
        if axis == 0:
            return volume[index, :, :]
        elif axis == 1:
            return volume[:, index, :]
        else:  # axis == 2
            return volume[:, :, index]
    
    @staticmethod
    def is_valid_slice(slice_data: np.ndarray) -> bool:
        """Check if slice has meaningful content."""
        return np.any(slice_data) and np.std(slice_data) > 1
    
    @staticmethod
    def slice_to_bytes(slice_data: np.ndarray, quality: int = 85) -> bytes:

        img = Image.fromarray(slice_data, mode='L')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=quality, optimize=True)
        return buffer.getvalue()
    
    def upload_slice(
        self,
        slice_bytes: bytes,
        clinic_id: str,
        patient_id: str,
        report_id: str,
        report_type: str,
        view: str,
        index: int
    ) -> Optional[str]:

        try:
            # Build storage path
            storage_path = f"{clinic_id}/{patient_id}/{report_type}/{report_id}/{view}/{index}.jpg"
            
            # Upload to Supabase
            response = self.supabase.storage.from_('reports').upload(
                path=storage_path,
                file=slice_bytes,
                file_options={"content-type": "image/jpeg"}
            )
            
            # Get public URL
            public_url = self.supabase.storage.from_('reports').get_public_url(storage_path)
            
            return public_url
            
        except Exception as e:
            logger.error(f"Failed to upload slice {view}/{index}: {e}")
            return None
    
    def upload_all_slices(
        self,
        volume: np.ndarray,
        clinic_id: str,
        patient_id: str,
        report_id: str,
        report_type: str,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        volume_normalized = self.normalize_volume(volume)
        slice_counts = {}
        uploaded_urls = []
        failed_count = 0
        
        for view in self.VIEWS:
            axis = self.AXES[view]
            slice_count = volume_normalized.shape[axis]
            saved_count = 0
            
            logger.info(f"Uploading {slice_count} {view} slices to Supabase...")
            
            for i in range(slice_count):
                # Extract slice
                slice_data = self.extract_slice(volume_normalized, axis, i)
                
                # Validate
                if not self.is_valid_slice(slice_data):
                    continue
                
                # Convert to JPEG bytes
                slice_bytes = self.slice_to_bytes(slice_data)
                
                # Upload to Supabase
                url = self.upload_slice(
                    slice_bytes,
                    clinic_id,
                    patient_id,
                    report_id,
                    report_type,
                    view,
                    saved_count
                )
                
                if url:
                    uploaded_urls.append(url)
                    saved_count += 1
                    
                    # [DEBUG] Limit to 5 slices per view as requested
                    if saved_count >= 5:
                        logger.info(f"🛑 Reached limit of 5 slices for {view} (Debug Mode)")
                        break
                else:
                    failed_count += 1
                
                # Progress callback
                if progress_callback and i % 20 == 0:
                    progress_callback(view, i, slice_count)
            
            slice_counts[view] = saved_count
            logger.info(f"✅ Uploaded {saved_count} {view} slices to Supabase")
        
        result = {
            'slice_counts': slice_counts,
            'uploaded_urls': uploaded_urls,
            'total_slices': sum(slice_counts.values()),
            'failed_count': failed_count
        }
        
        logger.info(f"Upload summary: {result['total_slices']} slices uploaded, {failed_count} failed")
        return result
