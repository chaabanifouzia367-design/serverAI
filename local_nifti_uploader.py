import os
import sys
import argparse
import numpy as np
import nibabel as nib
from PIL import Image
import io
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables if available
load_dotenv()

# --- CONFIGURATION (FILL THESE IN OR USE ENV VARS) ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "YOUR_SUPABASE_URL_HERE")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "YOUR_SUPABASE_KEY_HERE")

# Default Test IDs (You can override these via command line args)
DEFAULT_CLINIC_ID = "5bb43ddc-7d5b-48f4-aa95-a21e5f41aa78"
DEFAULT_PATIENT_ID = "50af57f3-909a-402a-9a46-f69845c7f3b6"
DEFAULT_REPORT_ID = "fe8c3422-7bf4-48ab-968a-19433961efb0"
DEFAULT_FILE_PATH = r"C:\Users\jihad\Desktop\264_cbct.nii\264_cbct.nii"

class NiftiUploader:
    """
    Handles NIfTI processing and Supabase uploading.
    """
    VIEWS = ['axial', 'coronal', 'sagittal']
    AXES = {'axial': 2, 'coronal': 1, 'sagittal': 0}

    def __init__(self, supabase_url: str, supabase_key: str):
        if not supabase_url or "YOUR_SUPABASE" in supabase_url:
             raise ValueError("Please provide a valid SUPABASE_URL")
        if not supabase_key or "YOUR_SUPABASE" in supabase_key:
             raise ValueError("Please provide a valid SUPABASE_KEY")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        print("✅ Supabase client initialized.")

    @staticmethod
    def normalize_volume(volume: np.ndarray) -> np.ndarray:
        """Normalize volume to 0-255 range."""
        volume_min, volume_max = volume.min(), volume.max()
        
        if volume_max == volume_min:
            print("⚠️ Constant intensity volume.")
            return np.zeros_like(volume, dtype=np.uint8)
        
        normalized = (volume - volume_min) / (volume_max - volume_min) * 255
        return normalized.astype(np.uint8)

    @staticmethod
    def extract_slice(volume: np.ndarray, axis: int, index: int) -> np.ndarray:
        """
        Extract 2D slice from volume along specified axis.
        Rotates 90 degrees for correct orientation.
        """
        if axis == 0:
            slice_data = volume[index, :, :]
        elif axis == 1:
            slice_data = volume[:, index, :]
        else:  # axis == 2
            slice_data = volume[:, :, index]
            
        return np.rot90(slice_data)

    def upload_slice(self, slice_data: np.ndarray, path: str) -> bool:
        """Upload a single slice to Supabase Storage."""
        try:
            # Convert to JPEG
            img = Image.fromarray(slice_data, mode='L')
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85, optimize=True)
            file_bytes = buffer.getvalue()

            # Upload
            self.supabase.storage.from_('reports').upload(
                path=path,
                file=file_bytes,
                file_options={"content-type": "image/jpeg", "x-upsert": "true"}
            )
            return True
        except Exception as e:
            print(f"❌ Failed to upload {path}: {e}")
            return False

    def process_and_upload(self, file_path: str, clinic_id: str, patient_id: str, report_id: str):
        """
        Main workflow: Load -> Normalize -> Slice -> Upload
        """
        print(f"\n🚀 Starting processing for:")
        print(f"   File: {file_path}")
        print(f"   Clinic: {clinic_id}")
        print(f"   Patient: {patient_id}")
        print(f"   Report: {report_id}")

        if not os.path.exists(file_path):
             print(f"❌ Error: File not found at {file_path}")
             return

        # 1. Load NIfTI
        try:
            nii = nib.load(file_path)
            volume = nii.get_fdata()
            print(f"📦 Volume loaded. Shape: {volume.shape}")
        except Exception as e:
            print(f"❌ Error loading NIfTI file: {e}")
            return

        # 2. Normalize
        print("🔄 Normalizing volume...")
        vol_norm = self.normalize_volume(volume)

        # 3. Process each view
        total_uploaded = 0
        
        for view in self.VIEWS:
            axis = self.AXES[view]
            num_slices = vol_norm.shape[axis]
            print(f"\n📸 Processing {view} ({num_slices} slices)...")
            
            view_uploaded = 0
            # Iterate through all slices
            for i in range(num_slices):
                # Extract
                slice_data = self.extract_slice(vol_norm, axis, i)
                
                # Check if empty (optional optimization)
                if np.std(slice_data) < 1:
                    continue

                # Construct Path: {clinic_id}/{patient_id}/cbct/{report_id}/{view}/{index}.jpg
                # Note: Using 'cbct' as report_type hardcoded for this script
                storage_path = f"{clinic_id}/{patient_id}/cbct/{report_id}/{view}/{i}.jpg"
                
                # Upload
                if self.upload_slice(slice_data, storage_path):
                    view_uploaded += 1
                    # Progress indicator every 10 slices
                    if view_uploaded % 10 == 0:
                        print(f"   Uploaded {view_uploaded}...", end='\r')

            print(f"✅ Uploaded {view_uploaded} {view} slices.")
            total_uploaded += view_uploaded

        print(f"\n🎉 DONE! Total slices uploaded: {total_uploaded}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local NIfTI to Supabase Uploader")
    
    parser.add_argument("--file", "-f", default=DEFAULT_FILE_PATH, help="Path to .nii file")
    parser.add_argument("--clinic", "-c", default=DEFAULT_CLINIC_ID, help="Clinic ID")
    parser.add_argument("--patient", "-p", default=DEFAULT_PATIENT_ID, help="Patient ID")
    parser.add_argument("--report", "-r", default=DEFAULT_REPORT_ID, help="Report ID")
    
    args = parser.parse_args()

    try:
        uploader = NiftiUploader(SUPABASE_URL, SUPABASE_KEY)
        uploader.process_and_upload(
            file_path=args.file,
            clinic_id=args.clinic,
            patient_id=args.patient,
            report_id=args.report
        )
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("Please set SUPABASE_URL and SUPABASE_KEY in the script or .env file.")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
