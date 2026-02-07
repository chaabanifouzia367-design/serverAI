"""
Complete Pano Analysis Workflow

Orchestre le flux complet: AI Analysis → Report Building → Upload
"""
import logging
from typing import Dict
from app.domains.pano.analyzer import get_analyzer
from app.domains.pano.report import build_complete_report
from app.core.uploads import upload_report_json

logger = logging.getLogger(__name__)


def analyze_and_upload(
    image_path: str,
    patient_info: Dict,
    clinic_id: str,
    patient_id: str,
    report_id: str,
    segmentation_config: Dict,
    detection_config: list,
    detection_strategy: str = 'GLOBAL',
    task_id: str = None
) -> Dict:
    """
    Workflow complet: Analyse AI → Rapport → Upload.
    
    TOUJOURS génère un rapport, même si AI échoue!
    
    Args:
        image_path: Chemin vers l'image pano
        patient_info: Infos patient
        clinic_id: ID clinique
        patient_id: ID patient
        report_id: ID rapport
        segmentation_config: Config stage 1
        detection_config: Config stage 2
        task_id: ID tâche Celery
        
    Returns:
        dict: Résultats complets {report, upload_result, status}
    """
    
    # Template vide par défaut
    empty_ai_results = {
        'total_teeth': 0,
        'teeth_data': [],
        'findings': [],
        'summary': {
            'total_findings': 0,
            'by_type': {},
            'by_severity': {},
            'requires_attention': False
        }
    }
    
    ai_results = empty_ai_results
    ai_status = 'no_models'
    ai_error = None
    
    # 1. Essayer de charger et analyser avec AI
    try:
        logger.info(f"🔧 Initializing AI analyzer (Strategy: {detection_strategy})...")
        analyzer = get_analyzer(segmentation_config, detection_config, detection_strategy)
        logger.info("✅ Analyzer ready")
        
        # 2. Analyser l'image
        logger.info(f"🔍 Analyzing image: {image_path}")
        ai_results = analyzer.analyze_pano_image(image_path)
        ai_status = 'success'
        logger.info(f"✅ Analysis complete: {ai_results['total_teeth']} teeth detected, "
                   f"{ai_results['summary']['total_findings']} findings")
        
    except Exception as e:
        logger.warning(f"⚠️ AI analysis failed: {e}")
        logger.info("📝 Will generate empty report template with metadata")
        ai_error = str(e)
        ai_status = 'failed'
        # Continue avec empty_ai_results
    
    # 3. TOUJOURS construire le rapport (avec ou sans AI)
    logger.info("📄 Building report template...")
    try:
        report = build_complete_report(
            ai_results=ai_results,
            patient_info=patient_info,
            report_id=report_id,
            segmentation_config=segmentation_config,
            detection_config=detection_config
        )
        
        # Ajouter statut AI
        report['aiAnalysis']['status'] = ai_status
        if ai_error:
            report['aiAnalysis']['error'] = ai_error
        
        logger.info("✅ Report generated")
        
    except Exception as e:
        logger.error(f"❌ Failed to build report: {e}")
        raise
    
    # 4. TOUJOURS uploader vers Supabase
    logger.info("☁️ Uploading report to Supabase...")
    try:
        upload_result = upload_report_json(
            report=report,
            clinic_id=clinic_id,
            patient_id=patient_id,
            report_id=report_id,
            task_id=task_id
        )
        logger.info(f"✅ Uploaded to: {upload_result.get('public_url')}")
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        raise
    
    logger.info(f"🎉 Workflow completed! AI Status: {ai_status}")
    
    return {
        'status': 'success',
        'ai_status': ai_status,
        'ai_error': ai_error,
        'report': report,
        'upload_result': upload_result,
        'ai_summary': ai_results['summary']
    }
