"""
Supabase Uploader for Reports

Fonctions pour uploader les rapports vers Supabase Storage
"""
import json
import logging
from typing import Dict
from app.services.uploads import SupabaseUploadManager

logger = logging.getLogger(__name__)


def upload_report_json(
    report: Dict,
    clinic_id: str,
    patient_id: str,
    report_id: str,
    report_type: str = 'pano',  # ← Added parameter
    task_id: str = None
) -> Dict:
    """
    Upload le rapport JSON vers Supabase storage.
    
    Args:
        report: Dict du rapport
        clinic_id: ID clinique
        patient_id: ID patient
        report_id: ID rapport
        report_type: Type de rapport (pano, cbct, etc.)
        task_id: ID de la tâche Celery (optionnel)
        
    Returns:
        dict: Résultat de l'upload avec public_url
    """
    try:
        # Convertir en JSON
        report_json = json.dumps(report, indent=2, ensure_ascii=False)
        report_bytes = report_json.encode('utf-8')
        
        # Uploader
        uploader = SupabaseUploadManager(task_id=task_id)
        
        # Path: reports/{clinic_id}/{patient_id}/{report_type}/{report_id}/report.json
        storage_path = f"{clinic_id}/{patient_id}/{report_type}/{report_id}/report.json"  # ← Dynamic
        
        logger.info(f"Uploading report.json to {storage_path}")
        
        # Upload directement via Supabase
        if not uploader.supabase:
            raise Exception("Supabase client not available")
        
        # Upload le fichier
        result = uploader.supabase.storage.from_("reports").upload(
            path=storage_path,
            file=report_bytes,
            file_options={"content-type": "application/json", "upsert": "true"}
        )
        
        # Obtenir l'URL publique
        public_url = uploader.supabase.storage.from_("reports").get_public_url(storage_path)
        
        upload_result = {
            'success': True,
            'storage_path': storage_path,
            'public_url': public_url,
            'file_size': len(report_bytes)
        }
        
        logger.info(f"Report uploaded successfully: {public_url}")
        return upload_result
        
    except Exception as e:
        logger.error(f"Failed to upload report: {e}")
        raise


def upload_annotated_image(
    image_bytes: bytes,
    clinic_id: str,
    patient_id: str,
    report_id: str,
    filename: str = 'annotated.png',
    task_id: str = None
) -> Dict:
    """
    Upload une image annotée (avec les détections dessinées).
    
    Args:
        image_bytes: Bytes de l'image
        clinic_id: ID clinique
        patient_id: ID patient
        report_id: ID rapport
        filename: Nom du fichier (défaut: annotated.png)
        task_id: ID tâche Celery
        
    Returns:
        dict: Résultat de l'upload
    """
    try:
        uploader = SupabaseUploadManager(task_id=task_id)
        
        storage_path = f"{clinic_id}/{patient_id}/pano/{report_id}/{filename}"
        
        logger.info(f"Uploading annotated image to {storage_path}")
        
        # Upload directement via Supabase
        if not uploader.supabase:
            raise Exception("Supabase client not available")
        
        result = uploader.supabase.storage.from_("reports").upload(
            path=storage_path,
            file=image_bytes,
            file_options={"content-type": "image/png", "upsert": "true"}
        )
        
        public_url = uploader.supabase.storage.from_("reports").get_public_url(storage_path)
        
        return {
            'success': True,
            'storage_path': storage_path,
            'public_url': public_url,
            'file_size': len(image_bytes)
        }
        
    except Exception as e:
        logger.error(f"Failed to upload annotated image: {e}")
        raise
