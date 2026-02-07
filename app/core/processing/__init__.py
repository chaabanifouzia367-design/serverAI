"""
Medical File Processing v2

Organized medical image processing for DICOM and NIfTI files.
"""
from .dicom import process_dicom
from .nifti import process_nifti

__all__ = ['process_dicom', 'process_nifti']
