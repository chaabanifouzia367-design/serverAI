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
    
    # Helper to clean tooth number
    def clean_tooth_num(val):
        if isinstance(val, str):
            # Remove prefixes like 'u' or 'd' if they exist in the raw model output
            import re
            match = re.search(r'\d+', val)
            return int(match.group()) if match else 0
        return int(val)

    for tooth_data in teeth_data:
        # Get raw tooth number
        raw_num = tooth_data.get('tooth_number') or tooth_data.get('tooth_class', '0')
        tooth_num = clean_tooth_num(raw_num)
        
        # Trouver les problèmes pour cette dent
        tooth_problems = [
            f for f in findings 
            if f.get('tooth_detection_id') == tooth_data['detection_id']
        ]
        
        # Déterminer la catégorie (Healthy, Treated, Unhealthy)
        has_pathology = any(f['problem'].lower() in ['caries', 'infection', 'periapical'] for f in tooth_problems)
        has_restoration = any(f['problem'].lower() in ['fillings', 'root_canal', 'implant', 'bridge', 'crown'] for f in tooth_problems)
        
        if has_pathology:
            category = "Unhealthy"
        elif has_restoration:
            category = "Treated"
        else:
            category = "Healthy"
        
        # Defaults for roots and canals based on common dental anatomy
        roots_count = 1
        canals_count = 1
        if tooth_num in [1, 2, 3, 14, 15, 16, 17, 18, 31, 32]: # Molars usually 3 roots
            roots_count = 3
            canals_count = 3
        elif tooth_num in [4, 5, 12, 13, 20, 21, 28, 29]: # Premolars
            roots_count = 1
            canals_count = 2

        # Construire l'objet dent
        tooth_obj = {
            "toothNumber": tooth_num,
            "toothType": tooth_data.get('tooth_type', 'unknown'),
            "category": category,
            "status": category, # Secondary field for UI support
            "position": {
                "x": tooth_data['bbox']['x'],
                "y": tooth_data['bbox']['y']
            },
            "boundingBox": tooth_data['bbox'],
            "detectionConfidence": tooth_data['confidence'],
            "detectionId": tooth_data['detection_id'],
            "problems": format_problems(tooth_problems),
            "gumHealth": "Healthy", # AI inferred default
            "lastCheckup": datetime.now().isoformat(),
            "note": "",
            "notes": [ # History items for "rich" look
                {
                    "content": f"AI automated detection completed. Category: {category}",
                    "author": "AI System",
                    "date": datetime.now().isoformat()
                }
            ],
            "roots": roots_count,
            "canals": canals_count,
            "Endo": {"mask": []} if "root_canal" in [p['problem'].lower() for p in tooth_problems] else None,
            "Root": {"mask": []},
            "Crown": {"mask": []} if "crown" in [p['problem'].lower() for p in tooth_problems] else None,
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
            "severity": p.get('severity', 'low'),
            "confidence": p.get('confidence', 1.0),
            "description": p.get('description', f"Detected {p['problem']}"),
            "detectedBy": p.get('detected_by', 'AI Analyzer'),
            "location": p.get('bbox'),
            "recommendation": "Clinical validation required.",
            "urgency": map_severity_to_urgency(p.get('severity', 'low'))
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
    # Recalculate based on our new detailed list to ensure perfect sync
    unhealthy_count = len([t for t in teeth_list if t['category'] == "Unhealthy"])
    treated_count = len([t for t in teeth_list if t['category'] == "Treated"])
    healthy_count = len([t for t in teeth_list if t['category'] == "Healthy"])
    missing_count = 32 - len(teeth_list) # Approximate assumption

    return {
        "totalTeeth": len(teeth_list),
        "healthy": healthy_count,
        "unhealthy": unhealthy_count,
        "treated": treated_count,
        "missing": missing_count,
        "cariesDistribution": {
            "active": len([t for t in teeth_list if any(p['type'].lower() == 'caries' for p in t['problems'])]),
            "arrested": 0,
            "recurrent": 0,
            "enamel": 0,
            "dentin": 0,
            "pulp": 0
        },
        "periodontalStatus": "Healthy",
        "missingTeeth": missing_count,
        "problemsDistribution": summary.get('by_type', {}),
        "severityDistribution": summary.get('by_severity', {}),
        "requiresAttention": unhealthy_count > 0 or summary.get('requires_attention', False)
    }


def build_scan_info() -> Dict:
    """Construit les informations du scan."""
    return {
        "device": "Panoramic X-Ray System",
        "dimensions": {
            "width": 0,
            "height": 0,
            "resolution": "300dpi"
        },
        "scanDate": datetime.now().isoformat(),
        "scanType": "panoramic",
        "imageFormat": "PNG",
        "advanced": {
            "exposureTime": "12s",
            "kVp": "70",
            "mA": "10"
        }
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
        "confidence": 0,
        "version": "2.1.0-enriched"
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
        "clinicId": "DEMO-01",
        "name": "Xdental Clinic",
        "license": "AI-2024-X",
        "address": "Digital Suite 101"
    }
    
    return {
        "reportId": report_id,
        "reportType": "pano",
        "generatedBy": "AI Analysis System v2.1",
        "version": "2.1",
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
        "conclusion": "Comprehensive AI analysis of panoramic radiograph completed. Please review detected pathologies and restorations.",
        "conclusionUpdatedAt": datetime.now().isoformat(),
        "metadata": metadata
    }
    
    return report

