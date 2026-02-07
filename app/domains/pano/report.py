"""
Report Builder for Pano Analysis

Fonctions modulaires pour construire le rapport à partir des résultats AI
"""
from datetime import datetime
from typing import Dict, List, Any


def build_teeth_list(teeth_data: List[Dict], findings: List[Dict]) -> List[Dict]:
    """
    Construit la liste des dents pour le rapport.
    
    Args:
        teeth_data: Données de segmentation des dents
        findings: Problèmes détectés par AI
        
    Returns:
        List[Dict]: Liste des dents formatées pour le rapport
    """
    teeth_list = []
    
    for tooth_data in teeth_data:
        # Trouver les problèmes pour cette dent
        tooth_problems = [
            f for f in findings 
            if f['tooth_detection_id'] == tooth_data['detection_id']
        ]
        
        # Déterminer la catégorie
        if tooth_problems:
            category = "Unhealthy"
        else:
            category = "Healthy"
        
        # Construire l'objet dent
        tooth_obj = {
            "toothNumber": tooth_data['tooth_class'],
            "toothType": tooth_data['tooth_type'],
            "category": category,
            "position": {
                "x": tooth_data['bbox']['x'],
                "y": tooth_data['bbox']['y']
            },
            "boundingBox": tooth_data['bbox'],
            "detectionConfidence": tooth_data['confidence'],
            "detectionId": tooth_data['detection_id'],
            "problems": format_problems(tooth_problems),
            "gumHealth": "Unknown",
            "lastCheckup": datetime.now().isoformat(),
            "note": "",
            "approved": False
        }
        
        teeth_list.append(tooth_obj)
    
    return teeth_list


def format_problems(problems: List[Dict]) -> List[Dict]:
    """
    Formate les problèmes détectés pour le rapport.
    
    Args:
        problems: Liste des problèmes bruts de l'AI
        
    Returns:
        List[Dict]: Problèmes formatés
    """
    formatted = []
    
    for p in problems:
        formatted.append({
            "type": p['problem'],
            "severity": p['severity'],
            "confidence": p['confidence'],
            "description": p.get('description', ''),
            "detectedBy": p['detected_by'],
            "location": p.get('bbox'),
            "recommendation": "",
            "urgency": map_severity_to_urgency(p['severity'])
        })
    
    return formatted


def map_severity_to_urgency(severity: str) -> str:
    """Convertit severity en urgency."""
    mapping = {
        'low': 'low',
        'medium': 'medium',
        'high': 'urgent'
    }
    return mapping.get(severity, 'medium')


def build_statistics(teeth_list: List[Dict], summary: Dict) -> Dict:
    """
    Construit les statistiques du rapport.
    
    Args:
        teeth_list: Liste des dents
        summary: Résumé de l'AI
        
    Returns:
        Dict: Statistiques formatées
    """
    return {
        "totalTeeth": len(teeth_list),
        "healthy": len([t for t in teeth_list if t['category'] == 'Healthy']),
        "unhealthy": len([t for t in teeth_list if t['category'] == 'Unhealthy']),
        "treated": 0,
        "missing": 0,
        "problemsDistribution": summary.get('by_type', {}),
        "severityDistribution": summary.get('by_severity', {}),
        "requiresAttention": summary.get('requires_attention', False)
    }


def build_scan_info() -> Dict:
    """Construit les informations du scan."""
    return {
        "device": "Panoramic X-Ray",
        "dimensions": {
            "width": 0,
            "height": 0,
            "resolution": "300dpi"
        },
        "scanDate": datetime.now().isoformat(),
        "scanType": "panoramic",
        "imageFormat": "PNG"
    }


def build_ai_analysis_info(segmentation_config: Dict, detection_config: List[Dict]) -> Dict:
    """
    Construit les informations d'analyse AI.
    
    Args:
        segmentation_config: Config du modèle de segmentation
        detection_config: Config des modèles de détection
        
    Returns:
        Dict: Info d'analyse AI
    """
    return {
        "segmentationModel": segmentation_config.get('path', 'unknown'),
        "detectionModels": [m['name'] for m in detection_config],
        "analysisDate": datetime.now().isoformat(),
        "processingTime": 0,
        "confidence": 0
    }


def build_metadata(report_id: str, clinic_info: Dict = None) -> Dict:
    """
    Construit les métadonnées du rapport.
    
    Args:
        report_id: ID du rapport
        clinic_info: Informations de la clinique (optionnel)
        
    Returns:
        Dict: Métadonnées
    """
    clinic_data = clinic_info or {
        "clinicId": "",
        "name": "",
        "license": "",
        "address": ""
    }
    
    return {
        "reportId": report_id,
        "reportType": "pano",
        "generatedBy": "AI Analysis System v2",
        "version": "2.0",
        "lastUpdated": datetime.now().isoformat(),
        "clinicInfo": clinic_data
    }


def build_complete_report(
    ai_results: Dict,
    patient_info: Dict,
    report_id: str,
    segmentation_config: Dict,
    detection_config: List[Dict],
    clinic_info: Dict = None
) -> Dict:
    """
    Construit le rapport complet à partir des résultats AI.
    
    Args:
        ai_results: Résultats de l'analyzer AI
        patient_info: Informations du patient
        report_id: ID du rapport
        segmentation_config: Config stage 1
        detection_config: Config stage 2
        clinic_info: Info clinique (optionnel)
        
    Returns:
        Dict: Rapport complet prêt pour upload
    """
    # Extraire les données AI
    teeth_data = ai_results.get('teeth_data', [])
    findings = ai_results.get('findings', [])
    summary = ai_results.get('summary', {})
    
    # Construire chaque section
    teeth_list = build_teeth_list(teeth_data, findings)
    statistics = build_statistics(teeth_list, summary)
    scan_info = build_scan_info()
    ai_analysis = build_ai_analysis_info(segmentation_config, detection_config)
    metadata = build_metadata(report_id, clinic_info)
    
    # Assembler le rapport final
    report = {
        "patientInfo": patient_info,
        "teeth": teeth_list,
        "statistics": statistics,
        "scanInfo": scan_info,
        "aiAnalysis": ai_analysis,
        "conclusion": "",
        "conclusionUpdatedAt": None,
        "metadata": metadata
    }
    
    return report
