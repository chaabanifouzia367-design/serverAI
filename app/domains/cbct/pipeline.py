"""
CBCT AI Analysis and Report Generation Pipeline

Real AI workflow with error handling:
- Load AI models
- Analyze CBCT image
- Generate report with results
- On error: return empty template with metadata
"""
from app.core.utils import upload_report_to_storage
import logging
import datetime
import os

logger = logging.getLogger(__name__)


def complete_medical_processing_aiReport_task(
    logger_param, file_info, upload_id, clinic_id, patient_id, report_type, report_id, supabase
):
    """
    CBCT AI Analysis Pipeline.
    
    Flow:
    1. Load AI models
    2. Run analysis on CBCT image
    3. Generate report with findings
    4. Upload report to storage
    
    On Error: Return empty template with metadata only
    """
    logger.info("🔬 Starting CBCT AI analysis pipeline...")
    logger.info(f"📁 File: {file_info.get('path')}")
    logger.info(f"📋 Report ID: {report_id}")
    
    # Initialize variables
    ai_results = None
    ai_status = 'no_analysis'
    report_data = None
    
    try:
        # Step 1: Initialize AI analyzer
        logger.info("🔧 Initializing CBCT AI analyzer...")
        
        from app.domains.cbct.analyzer import get_cbct_analyzer
        from app.domains.cbct.config import CBCT_SEGMENTATION_CONFIG, CBCT_DETECTION_CONFIG
        from app.domains.cbct.report_template import generate_cbct_report_template
        from app.services.model_manager import ModelManager

        # [NEW] Check for active dynamic models
        active_models = ModelManager.get_active_model()
        
        # 1. CBCT Detection
        detection_config_to_use = CBCT_DETECTION_CONFIG
        if active_models and 'cbct_detection' in active_models:
            m = active_models['cbct_detection']
            logger.info(f"🚀 Using Dynamic CBCT Detection: {m['name']} ({m['id']})")
            detection_config_to_use = [{
                'name': m['name'],
                'path': m['path'],
                'threshold': m.get('threshold', 0.5)
            }]
            
        # 2. CBCT Segmentation
        segmentation_config_to_use = CBCT_SEGMENTATION_CONFIG
        if active_models and 'cbct_segmentation' in active_models:
            m = active_models['cbct_segmentation']
            logger.info(f"🚀 Using Dynamic CBCT Segmentation: {m['name']} ({m['id']})")
            segmentation_config_to_use = {
                'path': m['path'],
                'threshold': m.get('threshold', 0.1)
            }
        
        # Get analyzer instance (2-stage: segmentation + detection)
        try:
            analyzer = get_cbct_analyzer(
                segmentation_config=segmentation_config_to_use, # Uses dynamic config if set
                detection_config=detection_config_to_use  # Use dynamic config if set
            )
            logger.info("✅ Analyzer ready")
        except Exception as e:
            logger.error(f"❌ Failed to load AI models: {e}")
            raise
        
        # Step 2: Run AI analysis on 3D volume
        volume_path = file_info.get('path')
        if not volume_path:
            raise ValueError("No volume path provided in file_info")
        
        logger.info(f"🔍 Analyzing CBCT 3D volume: {volume_path}")
        
        try:
            ai_results = analyzer.analyze_cbct_volume(volume_path)  # ⭐ 3D volume
            ai_status = 'success'
            logger.info(f"✅ Analysis complete: {len(ai_results.get('teeth_data', []))} teeth, {len(ai_results.get('findings', []))} findings")
        except Exception as e:
            logger.error(f"❌ AI analysis failed: {e}")
            ai_results = None
            ai_status = 'failed'
        
        # [NEW] Upload Pano Image if generated
        pano_url = None
        if ai_results and ai_results.get('pano_image'):
            try:
                pano_path = ai_results['pano_image']
                if os.path.exists(pano_path):
                    logger.info(f"📤 Uploading Pano Image: {pano_path}")
                    with open(pano_path, 'rb') as f:
                        file_content = f.read()
                        
                    storage_path = f"{clinic_id}/{patient_id}/{report_type}/{report_id}/original.png"
                    
                    supabase.storage.from_('reports').upload(
                        path=storage_path,
                        file=file_content,
                        file_options={"content-type": "image/png", "upsert": "true"}
                    )
                    
                    pano_url = supabase.storage.from_('reports').get_public_url(storage_path)
                    logger.info(f"✅ Pano uploaded: {pano_url}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to upload pano image: {e}")
                raise Exception(f"Failed to upload pano image to storage: {str(e)}")
                    # [DEBUG] Upload Debug Axial View if exists
                    debug_path = pano_path.replace('.jpg', '_debug.jpg')
                    if os.path.exists(debug_path):
                        logger.info(f"📤 Uploading Debug Pano Image: {debug_path}")
                        with open(debug_path, 'rb') as f:
                            debug_content = f.read()
                        
                        debug_storage_path = f"{clinic_id}/{patient_id}/{report_type}/{report_id}/pano_debug.jpg"
                        
                        supabase.storage.from_('reports').upload(
                            path=debug_storage_path,
                            file=debug_content,
                            file_options={"content-type": "image/jpeg", "upsert": "true"}
                        )
                        debug_url = supabase.storage.from_('reports').get_public_url(debug_storage_path)
                        logger.info(f"✅ Pano Debug uploaded: {debug_url}")
                        # Optionally add to report_data if you want frontend to see it
                        # report_data['aiAnalysis']['pano_debug_url'] = debug_url
                    
            except Exception as e:
                logger.error(f"⚠️ Failed to upload pano image: {e}")
        
        # Step 3: Generate report (with or without AI results)
        logger.info("📄 Building CBCT report...")
        
        # Patient info (fetch from DB or construct empty)
        patient_info = {
            "patientId": patient_id,
            "info": {
                "fullName": "",
                "dateOfBirth": "",
                "age": 0,
                "lastScanDate": "",
                "gender": "",
                "bloodType": "",
                "allergies": [],
                "medicalHistory": []
            }
        }
        
        report_data = generate_cbct_report_template(
            patient_info=patient_info,
            clinic_id=clinic_id,
            patient_id=patient_id,
            report_id=report_id,
            ai_results=ai_results
        )
        
        # Update AI analysis metadata
        if CBCT_SEGMENTATION_CONFIG:
            report_data['aiAnalysis']['segmentationModel'] = CBCT_SEGMENTATION_CONFIG.get('path', '')
        
        if CBCT_DETECTION_CONFIG:
            report_data['aiAnalysis']['detectionModels'] = [
                cfg['name'] for cfg in CBCT_DETECTION_CONFIG
            ]
            
        # [NEW] Add Pano URL to report
        if pano_url:
            report_data['aiAnalysis']['pano_url'] = pano_url
        
        logger.info("✅ Report generated")
        
    except Exception as e:
        # On any error: Generate empty template with metadata only
        logger.error(f"❌ Pipeline error: {e}")
        logger.info("📄 Generating empty report template...")
        
        from app.domains.cbct.report_template import generate_cbct_report_template
        
        patient_info = {
            "patientId": patient_id,
            "info": {}
        }
        
        report_data = generate_cbct_report_template(
            patient_info=patient_info,
            clinic_id=clinic_id,
            patient_id=patient_id,
            report_id=report_id,
            ai_results=None
        )
        
        report_data['aiAnalysis']['status'] = 'error'
        report_data['aiAnalysis']['error'] = str(e)
        ai_status = 'error'
        
        logger.info("✅ Empty template generated with error info")
    
    # Report data is ready - workflow will handle upload via chain
    logger.info("📦 CBCT pipeline complete - returning report data for workflow")
    
    # Return results (workflow chain will upload)
    return {
        "status": ai_status,
        "message": f"CBCT pipeline completed with status: {ai_status}",
        "findings_count": len(report_data.get('teeth', [])) if report_data else 0,
        "report_data": report_data
    }
