"""
Configuration pour les modèles AI - Séparé en 2 Stages

Stage 1: Segmentation des dents
Stage 2: Détection de problèmes
"""

# ========================================
# STAGE 1: Configuration du modèle de segmentation
# ========================================

import os

SEGMENTATION_CONFIG = {
    'path': 'models/pano/tooth_segmentation.pt',  # YOLOv8n-seg
    'threshold': float(os.getenv('AI_SEGMENTATION_THRESHOLD', 0.2))  # Seuil de confiance pour détecter les dents
}       


# ========================================
# STAGE 2: Configuration des modèles de détection
# ========================================

# Configuration pour le modèle multi-problèmes
MULTIPROBLEM_DETECTION_CONFIG = [
    {
        'name': 'multiproblem',
        'path': 'models/pano/multiproblem.pt',
        'threshold': 0.2  # Ajuster selon besoin
    }
]

# Stratégie de détection: 'GLOBAL' (image entière) ou 'PER_TOOTH' (découpage par dent)
DETECTION_STRATEGY = 'GLOBAL'  # Modifier ici pour changer le mode

# EXEMPLE 1: Configuration simple (2 modèles) - DEPRECATED
SIMPLE_DETECTION_CONFIG_OLD = [
    {
        'name': 'caries_detector',
        'path': 'models/caries_detector.pt',
        'threshold': 0.6
    },
    {
        'name': 'fracture_detector',
        'path': 'models/fracture_detector.pt',
        'threshold': 0.5
    }
]

# EXEMPLE 2: Un seul modèle général - OLD
SINGLE_DETECTION_CONFIG_OLD = [
    {
        'name': 'all_problems',
        'path': 'models/multi_detector.pt',
        'threshold': 0.5
    }
]


