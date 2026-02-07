"""
AI Analysis Pipeline for Panoramic Images

Stage 1: Tooth Segmentation
Stage 2: Problem Detection per Tooth
"""
import os
# Fix for PyTorch 2.6: Disable weights_only restriction for trusted model files
# Must be set BEFORE importing torch/ultralytics
os.environ["TORCH_SERIALIZATION_WEIGHTS_ONLY"] = "0"

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class PanoAIAnalyzer:
    """Main analyzer that orchestrates the AI pipeline."""
    
    def __init__(self, segmentation_config: Dict = None, detection_config: List[Dict] = None, detection_strategy: str = 'GLOBAL'):
        """
        Initialize analyzer with separate configurations for each stage.
        
        Args:
            segmentation_config: Configuration for Stage 1 (tooth segmentation)
            detection_config: List of detection models for Stage 2
            detection_strategy: 'GLOBAL' (full image) or 'PER_TOOTH' (cropped)
        """
        self.segmentation_model = None
        self.segmentation_config = segmentation_config or {}
        self.problem_detectors = {}
        self.detection_config = detection_config or []
        self.detection_strategy = detection_strategy
        
    def load_models(self):
        """Load all AI models dynamically based on configurations."""
        try:
            logger.info("🔧 Starting model loading...")
            
            # STAGE 1: Load segmentation model
            if self.segmentation_config:
                seg_path = self.segmentation_config.get('path')
                if seg_path:
                    logger.info(f"📦 Stage 1: Loading segmentation model from {seg_path}")
                    
                    # Vérifier si le fichier existe
                    if not os.path.exists(seg_path):
                        raise FileNotFoundError(f"Segmentation model not found: {seg_path}")
                    
                    # Charger le modèle YOLO
                    try:
                        from ultralytics import YOLO
                        
                        model = YOLO(seg_path)
                        logger.info(f"   📊 Model type: {type(model).__name__}")
                        
                        self.segmentation_model = {
                            'model': model,
                            'threshold': self.segmentation_config.get('threshold', 0.2),
                            'path': seg_path
                        }
                        logger.info("✅ Segmentation model loaded")
                        
                    except ImportError as e:
                        logger.warning(f"⚠️ ultralytics not installed - using placeholder. Error: {e}")
                    except Exception as e:
                        logger.warning(f"⚠️ Error loading ultralytics: {e}")
                        self.segmentation_model = {
                            'model': None,
                            'threshold': self.segmentation_config.get('threshold', 0.5),
                            'path': seg_path
                        }
                        logger.info("✅ Segmentation model loaded (placeholder)")
            else:
                raise ValueError("No segmentation config provided - models are required!")
            
            # STAGE 2: Load problem detection models dynamically
            if not self.detection_config:
                logger.warning("⚠️ No detection models configured")
            
            for config in self.detection_config:
                model_name = config['name']
                model_path = config['path']
                
                logger.info(f"📦 Stage 2: Loading detection model '{model_name}' from {model_path}")
                
                # Vérifier si le fichier existe
                if not os.path.exists(model_path):
                    raise FileNotFoundError(f"Detection model '{model_name}' not found: {model_path}")
                
                # Load YOLO model for detection
                try:
                    from ultralytics import YOLO
                    
                    model = YOLO(model_path)
                    logger.info(f"   📊 Detection Model type: {type(model).__name__}")
                    
                    self.problem_detectors[model_name] = {
                        'model': model,
                        'threshold': config.get('threshold', 0.2),
                        'path': model_path
                    }
                    logger.info(f"✅ Detection model '{model_name}' loaded")
                    
                except ImportError as e:
                    logger.warning(f"⚠️ ultralytics not installed - skipping {model_name}. Error: {e}")
                except Exception as e:
                    logger.warning(f"⚠️ Error loading detection model {model_name}: {e}")
            
            logger.info(f"🎉 Successfully loaded segmentation model + {len(self.problem_detectors)} detection models")
            
        except Exception as e:
            logger.error(f"❌ Failed to load AI models: {e}")
            raise
    
    def analyze_pano_image(self, image_path: str) -> Dict[str, Any]:
        """
        Run complete AI analysis pipeline.
        
        Args:
            image_path: Path to panoramic image
            
        Returns:
            Dictionary with analysis results
        """
        try:
            logger.info("🚀 Starting AI analysis pipeline...")
            logger.info(f"📸 Image: {image_path}")
            
            # Stage 1: Segment teeth
            logger.info("🦷 Stage 1: Segmenting teeth...")
            teeth_segments = self._segment_teeth(image_path)
            logger.info(f"✅ Found {len(teeth_segments)} teeth")
            
            # Stage 2: Detect problems on each tooth
            logger.info(f"🔍 Stage 2: Analyzing problems (Strategy: {self.detection_strategy})...")
            findings = self._detect_problems(teeth_segments, image_path)
            logger.info(f"✅ Detection complete: {len(findings)} findings")
            
            # Format results
            results = {
                'total_teeth': len(teeth_segments),
                'teeth_data': teeth_segments,
                'findings': findings,
                'summary': self._generate_summary(findings)
            }
            
            logger.info(f"📊 Summary: {len(teeth_segments)} teeth, {len(findings)} problems detected")
            logger.info("🎉 Analysis pipeline completed successfully!")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ AI analysis failed: {e}")
            raise
    
    def _segment_teeth(self, image_path: str) -> List[Dict]:
        """
        Stage 1: Segment individual teeth from pano image.
        
        Returns:
            List of tooth segments with metadata
        """
        # Run YOLO segmentation model
        if self.segmentation_model and self.segmentation_model['model'] is not None:
            model = self.segmentation_model['model']
            threshold = self.segmentation_model['threshold']
            
            # Run inference
            logger.info(f"🔍 Running YOLO inference with confidence threshold: {threshold}")
            
            # --- DEBUG START ---
            try:
                # 1. Verify Image Loading
                import cv2
                import numpy as np
                path_str = str(image_path)
                
                # Check file existence and size
                if os.path.exists(path_str):
                    size = os.path.getsize(path_str)
                    logger.info(f"📂 DEBUG: File exists. Size: {size} bytes. Path: {path_str}")
                else:
                    logger.error(f"❌ DEBUG: File NOT found at {path_str}")

                # Attempt to read image
                img = cv2.imread(path_str)
                if img is None:
                    logger.error(f"❌ DEBUG: cv2.imread returned None! Image might be corrupted or format unsupported.")
                else:
                    logger.info(f"🔍 DEBUG: Image loaded successfully. Shape: {img.shape}, Type: {img.dtype}")
                    logger.info(f"📊 DEBUG: Pixel stats - Min: {np.min(img)}, Max: {np.max(img)}, Mean: {np.mean(img):.2f}")
                    
                    # 2. Save Debug Input Image
                    # Save to a dedicated debug folder in the same directory as the image
                    image_dir = os.path.dirname(path_str)
                    debug_dir = os.path.join(image_dir, "debug_output")
                    os.makedirs(debug_dir, exist_ok=True)
                    
                    debug_input_path = os.path.join(debug_dir, "debug_input_check.jpg")
                    cv2.imwrite(debug_input_path, img)
                    logger.info(f"💾 DEBUG: Saved input check image to {debug_input_path}")
            except Exception as e:
                logger.error(f"⚠️ DEBUG: Error during image inspection: {e}")
            # --- DEBUG END ---

            # Run prediction with save=True to visualize what the model "sees"
            # We use a temp project dir to avoid cluttering, but accessible enough
            try:
                pred_project = os.path.join(os.path.dirname(str(image_path)), "debug_preds")
                results = model.predict(
                    image_path, 
                    conf=threshold, 
                    verbose=True, # Enable verbose for logs
                    save=True,    # Save annotated image
                    project=pred_project,
                    name='prediction',
                    exist_ok=True
                )
                logger.info(f"💾 DEBUG: Saved model prediction visualization to {pred_project}")
            except Exception as e:
                logger.error(f"⚠️ DEBUG: Prediction failed or save failed: {e}")
                # Fallback to standard prediction if save/project fails
                results = model.predict(image_path, conf=threshold, verbose=False)

            # Parse YOLO results into expected format
            raw_predictions = {"predictions": []}
            for result in results:
                # Log the number of boxes found directly from the result object
                logger.info(f"🔢 DEBUG: Raw result contains {len(result.boxes)} boxes")
                
                boxes = result.boxes
                for i, box in enumerate(boxes):
                    # Extract detection data
                    x, y, w, h = box.xywh[0].tolist()
                    confidence = float(box.conf[0])
                    class_id = int(box.cls[0])
                    class_name = result.names[class_id]
                    
                    raw_predictions["predictions"].append({
                        "detection_id": f"{class_name}_{i}",
                        "x": float(x),
                        "y": float(y),
                        "width": float(w),
                        "height": float(h),
                        "confidence": confidence,
                        "class": class_name,
                        "class_id": class_id
                    })
            
            logger.info(f"📊 YOLO detected {len(raw_predictions['predictions'])} objects")
        else:
            logger.warning("⚠️ Segmentation model not loaded - returning empty results")
            raw_predictions = {
                "predictions": []
            }
        
        # Parse predictions and prepare for stage 2
        teeth_segments = []
        for pred in raw_predictions.get("predictions", []):
            # Extract tooth info
            tooth_class = pred["class"]  # e.g., "d2", "u15", "b"
            
            # Determine tooth type
            if tooth_class.startswith('d'):
                tooth_type = 'lower'  # dent du bas
                tooth_number = tooth_class[1:] if len(tooth_class) > 1 else None
            elif tooth_class.startswith('u'):
                tooth_type = 'upper'  # dent du haut
                tooth_number = tooth_class[1:] if len(tooth_class) > 1 else None
            elif tooth_class == 'b':
                tooth_type = 'bridge'
                tooth_number = None
            elif tooth_class == 'de':
                tooth_type = 'denture'
                tooth_number = None
            else:
                tooth_type = 'unknown'
                tooth_number = None
            
            teeth_segments.append({
                'detection_id': pred['detection_id'],
                'tooth_class': tooth_class,
                'tooth_type': tooth_type,
                'tooth_number': tooth_number,
                'class_id': pred['class_id'],
                'bbox': {
                    'x': pred['x'],
                    'y': pred['y'],
                    'width': pred['width'],
                    'height': pred['height']
                },
                'confidence': pred['confidence'],
                # Store for potential cropping in stage 2
                'raw_prediction': pred
            })
        
        # Filter duplicates: Keep highest confidence for each tooth class
        unique_teeth = {}
        for tooth in teeth_segments:
            cls = tooth['tooth_class']
            # Only filter specific teeth (d1-d32, u1-u32), leave bridges/dentures/unknown alone if needed
            # But the user asked for "same tooth number", so grouping by class is correct per their request.
            if cls not in unique_teeth or tooth['confidence'] > unique_teeth[cls]['confidence']:
                unique_teeth[cls] = tooth
        
        # Apply filtering
        original_count = len(teeth_segments)
        teeth_segments = list(unique_teeth.values())
        filtered_count = len(teeth_segments)
        
        if original_count != filtered_count:
            logger.info(f"🧹 Filtered {original_count - filtered_count} duplicate teeth (kept highest confidence)")

        logger.info(f"✅ Segmentation completed: {len(teeth_segments)} teeth detected")
        if teeth_segments:
            logger.info(f"   📌 Tooth types: {len([t for t in teeth_segments if t['tooth_type']=='upper'])} upper, {len([t for t in teeth_segments if t['tooth_type']=='lower'])} lower")
        return teeth_segments
    
    def _detect_problems(self, teeth_segments: List[Dict], image_path: str = None) -> List[Dict]:
        """
        Stage 2: Run problem detection models.
        
        Strategy depends on self.detection_strategy:
        - 'GLOBAL': Run on full image -> Map to teeth.
        - 'PER_TOOTH': Crop each tooth -> Run on crop -> Assign to tooth.
        """
        if self.detection_strategy == 'PER_TOOTH':
            return self._detect_problems_per_tooth(teeth_segments, image_path)
        else:
            return self._detect_problems_global(teeth_segments, image_path)

    def _detect_problems_global(self, teeth_segments: List[Dict], image_path: str) -> List[Dict]:
        """Run detection on GLOBAL full image and map to teeth."""
        findings = []
        all_detections = []
        
        logger.info("🌍 Strategy: GLOBAL (Full Image Scan)")
        
        # 1. Run all detection models on the full image
        for detector_name, detector_info in self.problem_detectors.items():
            model = detector_info['model']
            threshold = detector_info['threshold']
            
            if model is None:
                continue
                
            logger.info(f"🔍 Running detector '{detector_name}' on full image...")
            
            try:
                # Run inference on full image
                results = model.predict(image_path, conf=threshold, verbose=False)
                
                # Collect all detections
                for result in results:
                    boxes = result.boxes
                    for box in boxes:
                        x, y, w, h = box.xywh[0].tolist()
                        all_detections.append({
                            'bbox': {'x': x, 'y': y, 'width': w, 'height': h},
                            'confidence': float(box.conf[0]),
                            'problem': result.names[int(box.cls[0])],
                            'detector': detector_name
                        })
                        
            except Exception as e:
                logger.error(f"❌ Error running detector {detector_name} on full image: {e}")
        
        logger.info(f"📊 Total raw problems detected: {len(all_detections)}")
        
        # 2. Map findings to teeth
        findings = self._map_problems_to_teeth(all_detections, teeth_segments)
        
        logger.info(f"✅ Problem detection completed: {len(findings)} mapped findings")
        if findings:
            logger.info(f"   📌 Problems by type: {dict((p, len([f for f in findings if f['problem']==p])) for p in set(f['problem'] for f in findings))}")
            
        return findings

    def _detect_problems_per_tooth(self, teeth_segments: List[Dict], image_path: str) -> List[Dict]:
        """Run detection PER TOOTH (Cropped)."""
        findings = []
        
        logger.info("🦷 Strategy: PER_TOOTH (Individual Crops)")
        
        for tooth in teeth_segments:
            detection_id = tooth['detection_id']
            tooth_class = tooth['tooth_class']
            bbox = tooth['bbox']
            
            # Skip non-tooth objects if needed
            if tooth['tooth_type'] in ['bridge', 'denture', 'unknown']:
                continue
            
            # Crop tooth region
            tooth_region_img = self._crop_tooth_image(image_path, bbox)
            
            if tooth_region_img is None:
                # logger.warning(f"⚠️ Failed to crop tooth {tooth_class}")
                continue
            
            # Run each detector on this tooth
            for detector_name, detector_info in self.problem_detectors.items():
                model = detector_info['model']
                threshold = detector_info['threshold']
                
                if model is None: continue
                
                try:
                    # Predict on CROPPED image
                    results = model.predict(tooth_region_img, conf=threshold, verbose=False)
                    
                    for result in results:
                        boxes = result.boxes
                        for box in boxes:
                            confidence = float(box.conf[0])
                            class_id = int(box.cls[0])
                            problem_name = result.names[class_id]
                            
                            findings.append({
                                'tooth_detection_id': detection_id,
                                'tooth_class': tooth_class,
                                'tooth_number': tooth['tooth_number'],
                                'tooth_type': tooth['tooth_type'],
                                'problem': problem_name,
                                'confidence': confidence,
                                'bbox': box.xywh[0].tolist(), # Relative to crop
                                'severity': 'medium', 
                                'description': f"Detected {problem_name}",
                                'detected_by': detector_name
                            })
                            
                except Exception as e:
                    logger.error(f"❌ Error running detector {detector_name} on {tooth_class}: {e}")
        
        logger.info(f"✅ Problem detection completed: {len(findings)} findings")
        if findings:
            logger.info(f"   📌 Problems by type: {dict((p, len([f for f in findings if f['problem']==p])) for p in set(f['problem'] for f in findings))}")
        return findings

    def _map_problems_to_teeth(self, problem_detections: List[Dict], teeth_segments: List[Dict]) -> List[Dict]:
        """
        Helper: Map problem bounding boxes to the best matching tooth.
        """
        mapped_findings = []
        
        for problem in problem_detections:
            p_bbox = problem['bbox']
            p_center_x = p_bbox['x']
            p_center_y = p_bbox['y']
            
            best_tooth = None
            min_dist = float('inf')
            
            import math
            
            for tooth in teeth_segments:
                t_bbox = tooth['bbox']
                
                # Check if problem center is roughly within tooth bounds (with some margin)
                # t_bbox is xywh (center based)
                t_whalf = t_bbox['width'] / 2
                t_hhalf = t_bbox['height'] / 2
                t_min_x = t_bbox['x'] - t_whalf
                t_max_x = t_bbox['x'] + t_whalf
                t_min_y = t_bbox['y'] - t_hhalf
                t_max_y = t_bbox['y'] + t_hhalf
                
                # Check containment
                if (t_min_x <= p_center_x <= t_max_x) and (t_min_y <= p_center_y <= t_max_y):
                    # Found a container tooth. Verify distance to center for tie-breaking
                    dist = math.sqrt((p_center_x - t_bbox['x'])**2 + (p_center_y - t_bbox['y'])**2)
                    
                    if dist < min_dist:
                        min_dist = dist
                        best_tooth = tooth
            
            if best_tooth:
                # Assign to this tooth
                mapped_findings.append({
                    'tooth_detection_id': best_tooth['detection_id'],
                    'tooth_class': best_tooth['tooth_class'],
                    'tooth_number': best_tooth['tooth_number'],
                    'tooth_type': best_tooth['tooth_type'],
                    'problem': problem['problem'],
                    'confidence': problem['confidence'],
                    'bbox': [p_bbox['x'], p_bbox['y'], p_bbox['width'], p_bbox['height']],
                    'severity': 'medium', 
                    'description': f"Detected {problem['problem']} on full scan",
                    'detected_by': problem['detector']
                })
        return mapped_findings
    
    def _generate_summary(self, findings: List[Dict]) -> Dict[str, Any]:
        """Generate a summary of all findings."""
        if not findings:
            return {
                'total_findings': 0,
                'by_type': {},
                'by_severity': {},
                'requires_attention': False
            }
        
        # Count by problem type
        by_type = {}
        by_severity = {}
        
        for finding in findings:
            problem = finding['problem']
            severity = finding.get('severity', 'unknown')
            
            by_type[problem] = by_type.get(problem, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        return {
            'total_findings': len(findings),
            'by_type': by_type,
            'by_severity': by_severity,
            'requires_attention': len(findings) > 0
        }

    def _crop_tooth_image(self, image_path: str, bbox: Dict[str, float]):
        """
        Helper: Crop tooth region from original image.
        bbox format: {'x': center_x, 'y': center_y, 'width': w, 'height': h}
        """
        try:
            import cv2
            import numpy as np
            
            # Load full image if not already kept (optimization: load once per analysis)
            # For now load each time to keep stateless
            img = cv2.imread(str(image_path))
            if img is None:
                return None
            
            img_h, img_w = img.shape[:2]
            
            # Convert xywh center to xyxy top-left/bottom-right
            cx, cy, w, h = bbox['x'], bbox['y'], bbox['width'], bbox['height']
            
            x1 = int(cx - w/2)
            y1 = int(cy - h/2)
            x2 = int(cx + w/2)
            y2 = int(cy + h/2)
            
            # Boundary checks with padding (optional)
            padding = 10
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(img_w, x2 + padding)
            y2 = min(img_h, y2 + padding)
            
            if x1 >= x2 or y1 >= y2:
                return None
                
            crop = img[y1:y2, x1:x2]
            return crop
            
        except Exception as e:
            logger.error(f"❌ Error cropping tooth: {e}")
            return None


# Singleton instance
_analyzer = None

def get_analyzer(segmentation_config: Dict = None, detection_config: List[Dict] = None, detection_strategy: str = 'GLOBAL') -> PanoAIAnalyzer:
    """
    Get or create analyzer instance.
    
    Args:
        segmentation_config: Stage 1 segmentation model config
        detection_config: Stage 2 detection models config list
        detection_strategy: 'GLOBAL' or 'PER_TOOTH'
    """
    global _analyzer
    if _analyzer is None:
        _analyzer = PanoAIAnalyzer(segmentation_config, detection_config, detection_strategy)
        _analyzer.load_models()
    return _analyzer
