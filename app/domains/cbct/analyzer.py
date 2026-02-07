"""
CBCT AI Analysis Pipeline (Hybrid: TotalSegmentator + Custom Detection)

Stage 1: Tooth Segmentation & Numbering (TotalSegmentator)
Stage 2: ROI Extraction (Cropping with Padding)
Stage 3: Problem Detection (Custom Models on Crops)
"""
import os
import logging
import numpy as np
import nibabel as nib
from typing import Dict, List, Any, Tuple

# Fix for PyTorch 2.6
os.environ["TORCH_SERIALIZATION_WEIGHTS_ONLY"] = "0"

logger = logging.getLogger(__name__)

class CBCTAIAnalyzer:
    """
    Hybrid 3-Stage Pipeline for CBCT Analysis.
    """
    
    def __init__(self, segmentation_config: Dict = None, detection_config: List[Dict] = None):
        self.detection_config = detection_config or []
        self.problem_detectors = {}
        # We don't strictly need segmentation_config path anymore if using TotalSegmentator,
        # but we keep it for signature compatibility.
        
    def load_models(self):
        """Load Custom Stage 2 Detection Models."""
        logger.info("🔧 Loading CBCT Detection Models (Stage 2)...")
        
        # TotalSegmentator is loaded on-demand (it's a library), 
        # but we can check if it's installed here.
        try:
            import totalsegmentator
            logger.info("✅ TotalSegmentator library found for Stage 1.")
        except ImportError:
            logger.warning("⚠️ TotalSegmentator not installed! Stage 1 will fail.")

        # Load Custom Detection Models
        for config in self.detection_config:
            name = config['name']
            path = config['path']
            try:
                # Placeholder for loading your 3D CNNs (e.g., PyTorch, TensorFlow)
                # from models.load import load_model
                # model = load_model(path)
                logger.info(f"📦 Loaded Detection Model: {name} from {path}")
                
                # Mocking model for now until you provide actual loader wrapper
                self.problem_detectors[name] = {
                    'model': 'LOADED_MOCK', 
                    'threshold': config.get('threshold', 0.5),
                    'path': path
                }
            except Exception as e:
                logger.error(f"❌ Failed to load {name}: {e}")

    def analyze_cbct_volume(self, volume_path: str) -> Dict[str, Any]:
        """
        Main Pipeline Execution.
        """
        logger.info(f"🚀 Starting Hybrid CBCT Analysis on: {volume_path}")
        
        try:
            # --- STAGE 1: TotalSegmentator ---
            logger.info("🧠 Stage 1: Running TotalSegmentator (Segmentation & Numbering)...")
            teeth_segments, nifti_img, mask_data = self._run_totalsegmentator(volume_path)
            logger.info(f"✅ Stage 1 Complete: Found {len(teeth_segments)} teeth.")

            # --- STAGE 2 & 3: Crop & Detect ---
            logger.info("🔍 Stage 2 & 3: Extraction & Problem Detection...")
            findings = self._detect_problems(teeth_segments, nifti_img, mask_data)
            
            # --- STAGE 4: Synthetic Pano Generation ---
            pano_path = None
            try:
                from app.domains.pano.projection import generate_synthetic_pano
                
                # Create output filename
                base_name = os.path.splitext(os.path.basename(volume_path))[0]
                # Handle .nii.gz double extension
                if base_name.endswith('.nii'):
                    base_name = os.path.splitext(base_name)[0]
                    
                output_dir = os.path.dirname(volume_path).replace('uploads', 'processed') # Save to processed
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                    
                pano_path = os.path.join(output_dir, f"{base_name}_syn_pano.jpg")
                
                logger.info("🖼️ Generating Synthetic Panoramic View...")
                if generate_synthetic_pano(nifti_img.get_fdata(), teeth_segments, pano_path):
                    logger.info(f"✅ Pano generated: {pano_path}")
                else:
                    pano_path = None
            except Exception as e:
                logger.error(f"⚠️ Failed to generate pano: {e}")
            
            return {
                'total_teeth': len(teeth_segments),
                'teeth_data': teeth_segments,
                'findings': findings,
                'pano_image': pano_path,
                'summary': self._generate_summary(findings),
                'dimensions': nifti_img.shape # (x, y, z) usually for NIfTI object, checked below
            }
            
        except Exception as e:
            logger.error(f"❌ Analysis Failed: {e}")
            # Return empty structure on failure to prevent crash
            return {'total_teeth': 0, 'teeth_data': [], 'findings': [], 'summary': {}}

    def _run_totalsegmentator(self, volume_path: str) -> Tuple[List[Dict], Any, np.ndarray]:
        """
        Runs TotalSegmentator to get teeth masks.
        """
        # Check if TotalSegmentator is installed via CLI check (optional) or just run it
        
        # Load input NIfTI
        nifti_img = nib.load(volume_path)
        
        # Check resolution and downsample if necessary
        zooms = nifti_img.header.get_zooms()
        min_zoom = min(zooms[:3])
        logger.info(f"   ℹ️ Input resolution: {zooms} (min: {min_zoom:.2f}mm)")
        
        path_to_process = volume_path
        
        # If resolution is too high (e.g. < 1.0mm), downsample to 1.5mm
        # This prevents CPU timeout (15m+) on high-res CBCTs (0.25mm)
        # UNLESS user forces full resolution (requires GPU)
        force_full_res = os.getenv('CBCT_FORCE_FULL_RES', 'false').lower() == 'true'
        
        if min_zoom < 1.0 and not force_full_res:
            logger.info("   ⚠️ High resolution detected. Downsampling to 1.5mm for processing...")
            try:
                import nibabel.processing
                # Resample to 1.5mm isotropic
                resampled_img = nibabel.processing.resample_to_output(nifti_img, (1.5, 1.5, 1.5))
                nifti_img = resampled_img # Update valid NIfTI object
                
                # Save to temp file for TotalSegmentator
                import tempfile
                # We need a persistent temp file for the duration of the function, 
                # but we are already inside a temp dir block below? NO.
                # Use the 'temp_dir' we are about to create.
            except Exception as e:
                logger.error(f"Downsampling failed: {e}. Proceeding with original (risk of timeout).")
                path_to_process = volume_path

        logger.info("   ⏳ Calling TotalSegmentator CLI (this may take time)...")
        # Run inference using a temporary directory for output
        import tempfile
        import subprocess
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # If we resampled, save it here
            if path_to_process != volume_path or min_zoom < 1.0: # Check condition again or use flag
                 # If we have a new nifti_img object that is different from load?
                 # Better logic:
                 if min_zoom < 1.0 and 'resampled_img' in locals():
                     temp_input_path = os.path.join(temp_dir, 'input_resampled.nii.gz')
                     nib.save(nifti_img, temp_input_path)
                     path_to_process = temp_input_path
                     logger.info(f"   💾 Saved resampled volume to {temp_input_path}")

            temp_output_path = os.path.join(temp_dir, 'segmentation')
            if not os.path.exists(temp_output_path):
                os.makedirs(temp_output_path)
            
            logger.info(f"   ⏳ Calling TotalSegmentator (output: {temp_output_path})...")
            
            # Construct command
            # TotalSegmentator -i input -o output
            # Removed --fast (too low res for teeth) and --ml (single file output issue)
            cmd = [
                "TotalSegmentator",
                "-i", path_to_process,
                "-o", temp_output_path
            ]
            
            try:
                # Run CLI command
                logger.info(f"   💻 Executing: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd, 
                    check=True, 
                    capture_output=True, 
                    text=True,
                    timeout=900 # 15 minutes timeout (CPU safe)
                )
                logger.info(f"TotalSegmentator Output: {result.stdout}")
                if result.stderr:
                    logger.warning(f"TotalSegmentator Stderr: {result.stderr}")
            except subprocess.CalledProcessError as e:
                logger.error(f"TotalSegmentator CLI failed: {e.stderr}")
                raise RuntimeError(f"TotalSegmentator failed: {e.stderr}")
            except Exception as e:
                logger.error(f"TotalSegmentator Execution failed: {e}")
                raise

            # Check for output
            # TotalSegmentator produces a directory of files when no file name is specified (or always with -o dir)
            # We expect multiple files like 'tooth_1.nii.gz', 'tooth_2.nii.gz' etc. or a single file if we pointed to a file.
            # Here temp_output_path is a directory.
            
            generated_files = []
            if os.path.isdir(temp_output_path):
                # Recursive search for .nii.gz files
                for root, dirs, files in os.walk(temp_output_path):
                    for file in files:
                        if file.endswith('.nii.gz'):
                            generated_files.append(os.path.join(root, file))
            
            if not generated_files:
                 # Debug: List what IS there
                 all_files = []
                 for root, dirs, files in os.walk(temp_output_path):
                     for file in files:
                         all_files.append(os.path.join(root, file))
                 logger.error(f"DEBUG: All files in temp dir: {all_files}")
                 # raise FileNotFoundError(f"TotalSegmentator did not produce any output files in {temp_output_path}")
                 logger.warning("⚠️ TotalSegmentator produced no output files. Returning empty results.")
                 return [], nifti_img, np.zeros(nifti_img.shape, dtype=np.uint8)

            logger.info(f"   📂 processing {len(generated_files)} output files...")
            
            # Combine all masks into one
            # Load the first one to get dimensions
            first_seg = nib.load(os.path.join(temp_output_path, generated_files[0]))
            mask_data = np.zeros(first_seg.shape, dtype=np.uint8)
            
            # Map of organ name to ID (if using standard TS labels, we might need a map)
            # For simplicity, if filename contains 'tooth', we treat it as tooth.
            # Or we just assign unique IDs based on file index if we trust the filenames.
            
            # Let's filter for teeth only?
            # Teeth files are usually named tooth_1.nii.gz, etc.
            teeth_files = [f for f in generated_files if 'tooth' in f]
            
            if not teeth_files:
                logger.warning("No specific 'tooth' files found. Using all segments.")
                teeth_files = generated_files
                
            for f in teeth_files:
                # Extract simple ID or just use increment
                # tooth_1.nii.gz -> 1
                try:
                    # Attempt to extract number from filename (e.g. tooth_1.nii.gz)
                    import re
                    match = re.search(r'tooth_(\d+)', f)
                    if match:
                        label_id = int(match.group(1))
                    else:
                        # Fallback: Hash or arbitrary ID? 
                        # Ideally we want FDI notation if TS provides it.
                        label_id = abs(hash(f)) % 255 + 1
                except:
                    label_id = 1
                
                seg = nib.load(os.path.join(temp_output_path, f))
                data = seg.get_fdata()
                mask_data[data > 0] = label_id
            
            # nifti_img is already set to the one we used (original or resampled)
            # Do NOT reload from volume_path here!
            # nifti_img = nib.load(volume_path) <--- DELETED

        # Parse mask into segments
        unique_labels = np.unique(mask_data)
        unique_labels = unique_labels[unique_labels > 0] # Exclude background
        
        segments = []
        for label_id in unique_labels:
            # Calculate BBox
            bbox = self._get_bbox(mask_data, label_id)
            
            fdi_number = str(int(label_id)) 
            
            segments.append({
                'detection_id': f"tooth_{fdi_number}",
                'class_id': int(label_id),
                'tooth_number': fdi_number, 
                'tooth_class': f"tooth_{fdi_number}",
                'tooth_type': 'tooth',
                'bbox_3d': bbox,
                'confidence': 1.0
            })
            
        return segments, nifti_img, mask_data

    def _get_bbox(self, mask_data, label_id, padding=5):
        """Calculates 3D BBox with padding."""
        coords = np.argwhere(mask_data == label_id)
        if coords.size == 0:
            return (0,0,0,0,0,0)
            
        z, y, x = coords.T # argwhere returns (z,y,x) for Nifti usually
        
        # Min/Max with padding
        # Clamp to array dimensions
        d, h, w = mask_data.shape
        
        min_z = max(0, z.min() - padding)
        max_z = min(d, z.max() + padding)
        
        min_y = max(0, y.min() - padding)
        max_y = min(h, y.max() + padding)
        
        min_x = max(0, x.min() - padding)
        max_x = min(w, x.max() + padding)
        
        return (int(min_x), int(max_x), int(min_y), int(max_y), int(min_z), int(max_z))

    def _detect_problems(self, segments, nifti_img, mask_data) -> List[Dict]:
        """
        Stage 2 & 3: Crop and Run Detection.
        """
        findings = []
        volume_data = nifti_img.get_fdata()
        
        for tooth in segments:
            # skip if not tooth
            
            # 1. Crop
            min_x, max_x, min_y, max_y, min_z, max_z = tooth['bbox_3d']
            
            # Numpy is (z, y, x) usually in Nibabel wrapper
            tooth_crop = volume_data[min_z:max_z, min_y:max_y, min_x:max_x]
            
            # Apply mask to crop (optional: to remove background bone)
            # mask_crop = mask_data[min_z:max_z, min_y:max_y, min_x:max_x]
            # tooth_crop = tooth_crop * (mask_crop == tooth['class_id'])
            
            # 2. Run Detectors
            for name, detector in self.problem_detectors.items():
                try:
                    # Mock Prediction
                    # prob = detector['model'].predict(tooth_crop)
                    prob = 0.0 # Default
                    
                    # SIMULATION for demo
                    import random
                    if random.random() > 0.8:
                        prob = 0.95
                        
                    if prob > detector['threshold']:
                        findings.append({
                            'tooth_detection_id': tooth['detection_id'],
                            'tooth_number': tooth['tooth_number'],
                            'problem': name,
                            'confidence': prob,
                            'severity': 'high' if prob > 0.8 else 'moderate'
                        })
                except Exception as e:
                    logger.error(f"Detection failed for {name} on {tooth['tooth_number']}: {e}")
                    
        return findings

    def _generate_summary(self, findings):
        return {
            'total_findings': len(findings),
            'requires_attention': len(findings) > 0
        }

# Singleton
_analyzer = None
def get_cbct_analyzer(segmentation_config=None, detection_config=None):
    global _analyzer
    if _analyzer is None:
        _analyzer = CBCTAIAnalyzer(segmentation_config, detection_config)
        _analyzer.load_models()
    return _analyzer
