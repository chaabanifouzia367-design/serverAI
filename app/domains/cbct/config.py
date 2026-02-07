"""
Configuration for CBCT AI Models

2-Stage Architecture (same as Pano, but for 3D volumes):
- Stage 1: Tooth Segmentation from 3D volume
- Stage 2: Problem Detection per tooth
"""

# ========================================
# STAGE 1: Tooth Segmentation (3D)
# ========================================

CBCT_SEGMENTATION_CONFIG = {
    'path': 'models/cbct/cbct_tooth_segmentation.pt',  # Model for 3D tooth detection
    'threshold': 0.1  # Confidence threshold
}


# ========================================
# STAGE 2: Problem Detection Models
# ========================================

CBCT_DETECTION_CONFIG = [
    # Example: Caries detector for 3D tooth regions
    # {
    #     'name': 'caries_detector',
    #     'path': 'models/cbct_caries_detector.pt',
    #     'threshold': 0.6
    # },
    
    # Example: Fracture detector
    # {
    #     'name': 'fracture_detector',
    #     'path': 'models/cbct_fracture.pt',
    #     'threshold': 0.5
    # },
]


# ========================================
# Expected Model Input/Output:
# ========================================
"""
STAGE 1 (Segmentation):
Input: 3D volume (NIfTI/DICOM)
Output: Same format as Pano
{
    "predictions": [
        {
            "x": 100, "y": 200, "width": 50, "height": 60,
            "confidence": 0.92,
            "class": "d2",  # tooth class
            "class_id": 10,
            "detection_id": "..."
        },
        ...
    ]
}

STAGE 2 (Detection):
Input: 3D tooth region (cropped from volume)
Output: List of problems (same as Pano)
[
    {
        'problem': 'caries',
        'confidence': 0.92,
        'bbox': [x, y, z, w, h, d],  # 3D bbox
        'severity': 'high',
        'description': '...'
    },
    ...
]

If nothing found → []
"""

