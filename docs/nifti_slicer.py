
import os
import sys
import argparse
import numpy as np
import nibabel as nib
from PIL import Image

class SliceGenerator:
    """
    Generator class to extract 2D slices from 3D NIfTI volumes.
    Supports Axial, Coronal, and Sagittal views.
    """
    
    VIEWS = ['axial', 'coronal', 'sagittal']
    # Axis mapping for common NIfTI orientation (RAS)
    # This might need adjustment based on specific file orientation
    AXES = {'axial': 2, 'coronal': 1, 'sagittal': 0}
    
    @staticmethod
    def normalize_volume(volume: np.ndarray) -> np.ndarray:
        """
        Normalize volume intensity to 0-255 range for image saving.
        """
        volume_min, volume_max = volume.min(), volume.max()
        
        if volume_max == volume_min:
            print("Warning: Constant intensity volume detected.")
            return np.zeros_like(volume, dtype=np.uint8)
        
        # Linear normalization
        normalized = (volume - volume_min) / (volume_max - volume_min) * 255
        return normalized.astype(np.uint8)
    
    @staticmethod
    def extract_slice(volume: np.ndarray, axis: int, index: int) -> np.ndarray:
        """
        Extract 2D slice from 3D volume along specified axis.
        """
        if axis == 0:
            # Sagittal: Slice along X axis
            slice_data = volume[index, :, :]
            # Rotate for display if needed (often needed for NIfTI)
            return np.rot90(slice_data)
        elif axis == 1:
            # Coronal: Slice along Y axis
            slice_data = volume[:, index, :]
            return np.rot90(slice_data)
        else:  # axis == 2
            # Axial: Slice along Z axis
            slice_data = volume[:, :, index]
            return np.rot90(slice_data)

    @staticmethod
    def save_slice(slice_data: np.ndarray, output_dir: str, view: str, index: int):
        """
        Save slice as JPEG image.
        """
        # Skip empty slices (optional, based on variance or sum)
        if np.std(slice_data) < 1:
            return False

        # Create view directory
        view_dir = os.path.join(output_dir, view)
        os.makedirs(view_dir, exist_ok=True)
        
        # Save image
        img = Image.fromarray(slice_data, mode='L')
        img.save(os.path.join(view_dir, f"{index:04d}.jpg"), quality=90)
        return True

    @classmethod
    def process_file(cls, input_file: str, output_dir: str):
        print(f"Processing: {input_file}")
        
        try:
            # Load NIfTI file
            nii = nib.load(input_file)
            volume = nii.get_fdata()
            print(f"Volume shape: {volume.shape}")
            
            # Normalize once
            print("Normalizing volume...")
            vol_norm = cls.normalize_volume(volume)
            
            total_saved = 0
            
            # Generate slices for each view
            for view in cls.VIEWS:
                axis = cls.AXES[view]
                num_slices = vol_norm.shape[axis]
                print(f"Generating {view} slices ({num_slices})...")
                
                view_saved = 0
                for i in range(num_slices):
                    slice_data = cls.extract_slice(vol_norm, axis, i)
                    if cls.save_slice(slice_data, output_dir, view, i):
                        view_saved += 1
                
                print(f"  - Saved {view_saved} {view} slices")
                total_saved += view_saved
                
            print(f"Done! Total slices saved: {total_saved}")
            print(f"Output directory: {output_dir}")
            
        except Exception as e:
            print(f"Error processing file: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract slices from NIfTI file.")
    parser.add_argument("input_file", help="Path to input .nii or .nii.gz file")
    parser.add_argument("--output", "-o", default="output/slices", help="Directory to save slices")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}")
        sys.exit(1)
        
    SliceGenerator.process_file(args.input_file, args.output)
