"""
DICOM File Loader

Load and validate DICOM files from directory.
"""
import os
import pydicom
import numpy as np
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class DICOMLoader:
    """Load DICOM files from directory."""
    
    SUPPORTED_EXTENSIONS = {'.dcm', '.dicom', '.ima', ''}
    
    @staticmethod
    def is_dicom_file(file_path: str) -> bool:
        """
        Check if file is valid DICOM by magic number.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if valid DICOM file
        """
        try:
            with open(file_path, 'rb') as f:
                f.seek(128)
                return f.read(4) == b'DICM'
        except Exception:
            return False
    
    @staticmethod
    def find_dicom_files(directory: str) -> List[str]:
        """
        Find all DICOM files in directory recursively.
        
        Args:
            directory: Root directory to search
            
        Returns:
            List of DICOM file paths
        """
        dicom_files = []
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1].lower()
                
                # Check extension
                if file_ext in DICOMLoader.SUPPORTED_EXTENSIONS:
                    # Validate DICOM magic number
                    if DICOMLoader.is_dicom_file(file_path):
                        dicom_files.append(file_path)
                    elif file_ext in {'.dcm', '.dicom', '.ima'}:
                        # Try anyway if extension suggests DICOM
                        dicom_files.append(file_path)
        
        logger.info(f"Found {len(dicom_files)} potential DICOM files")
        return dicom_files
    
    @staticmethod
    def load_and_validate(file_paths: List[str]) -> Tuple[List[Tuple], List[Tuple]]:
        """
        Load DICOM files and return valid slices.
        
        Args:
            file_paths: List of DICOM file paths
            
        Returns:
            Tuple of (valid_slices, failed_files)
            valid_slices: List of (dataset, file_path, pixel_array)
            failed_files: List of (file_path, error_message)
        """
        valid_slices = []
        failed_files = []
        
        for file_path in file_paths:
            try:
                ds = pydicom.dcmread(file_path, force=True)
                
                # Validate has pixel data
                if not hasattr(ds, 'pixel_array'):
                    failed_files.append((file_path, "No pixel data"))
                    continue
                
                pixel_array = ds.pixel_array
                
                # Validate not empty
                if pixel_array.size == 0:
                    failed_files.append((file_path, "Empty pixel array"))
                    continue
                
                valid_slices.append((ds, file_path, pixel_array))
                
            except Exception as e:
                failed_files.append((file_path, str(e)))
                continue
        
        logger.info(f"Loaded {len(valid_slices)} valid DICOM slices")
        if failed_files:
            logger.warning(f"Failed to load {len(failed_files)} files")
        
        return valid_slices, failed_files
    
    @staticmethod
    def sort_slices(slices: List[Tuple]) -> List[Tuple]:
        """
        Sort DICOM slices by location/position.
        
        Args:
            slices: List of (dataset, file_path, pixel_array)
            
        Returns:
            Sorted list of slices
        """
        def sort_key(slice_data):
            ds, _, _ = slice_data
            
            # Try multiple sorting criteria
            if hasattr(ds, 'SliceLocation') and ds.SliceLocation is not None:
                return float(ds.SliceLocation)
            elif hasattr(ds, 'ImagePositionPatient') and ds.ImagePositionPatient:
                return float(ds.ImagePositionPatient[2])  # Z-coordinate
            elif hasattr(ds, 'InstanceNumber') and ds.InstanceNumber is not None:
                return int(ds.InstanceNumber)
            return 0
        
        try:
            return sorted(slices, key=sort_key)
        except Exception as e:
            logger.warning(f"Could not sort by metadata: {e}, using filename")
            # Fallback to filename sorting
            return sorted(slices, key=lambda x: x[1])
