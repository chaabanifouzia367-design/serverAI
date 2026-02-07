
import unittest
import os
import sys
import numpy as np
import nibabel as nib
from io import BytesIO

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app

class TestNIfTIUpload(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True
        self.app.config['UPLOAD_FOLDER'] = os.path.abspath('storage/uploads')
        os.makedirs(self.app.config['UPLOAD_FOLDER'], exist_ok=True)
        self.app.config['MAX_FILE_SIZE'] = 10 * 1024 * 1024
        
        # Create dummy NIfTI
        self.dummy_nii = self._create_dummy_nifti()
        
    def _create_dummy_nifti(self):
        # Create small random volume
        data = np.random.rand(10, 10, 10)
        img = nib.Nifti1Image(data, np.eye(4))
        
        import tempfile
        # Create temp file, close it so nibabel can open/write to it
        fd, path = tempfile.mkstemp(suffix='.nii.gz')
        os.close(fd)
        
        nib.save(img, path)
        
        with open(path, 'rb') as f:
            content = f.read()
        
        os.unlink(path)
        return BytesIO(content)

    def test_nifti_upload_endpoint(self):
        print("Testing /nifti-slices endpoint...")
        
        data = {
            'file': (self.dummy_nii, 'test_scan.nii.gz'),
            'patient_id': 'TEST-PAT-001',
            'clinic_id': 'TEST-CLINIC',
            'report_id': 'REP-TEST-NII'
        }
        
        # Mock Supabase (since we don't want real uploads)
        # But for now let's just see if the endpoint validates and returns 202
        # The workflow execution happens asynchronously, so mocking celery isn't strictly needed for the HTTP response test
        
        response = self.client.post(
            '/nifti-slices',
            data=data,
            content_type='multipart/form-data'
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.get_data(as_text=True)}")
        
        self.assertEqual(response.status_code, 202)
        self.assertIn('job_id', response.json)
        self.assertEqual(response.json['message'], 'NIFTI file uploaded and processing workflow started')

if __name__ == '__main__':
    unittest.main()
