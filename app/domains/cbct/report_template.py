"""
CBCT Report Template

Template structure for CBCT analysis reports.
Matches Pano structure but for 3D CBCT scans.
"""
import datetime


def generate_cbct_report_template(
    patient_info: dict,
    clinic_id: str,
    patient_id: str,
    report_id: str,
    ai_results: dict = None
) -> dict:
    """
    Generate CBCT report template (same structure as Pano).
    
    Args:
        patient_info: Patient information dict
        clinic_id: Clinic identifier
        patient_id: Patient identifier  
        report_id: Report identifier
        ai_results: AI analysis results (optional, can be None on error)
        
    Returns:
        Report dictionary with teeth array
    """
    
    # Extract AI results if available
    teeth_data = []
    findings_list = []
    ai_status = 'no_analysis'
    total_teeth = 0
    
    if ai_results:
        teeth_data = ai_results.get('teeth_data', [])
        findings_list = ai_results.get('findings', [])
        ai_status = 'success' if teeth_data else 'no_detections'
        total_teeth = len(teeth_data)
        
        # Get dimensions (default to 0 if missing)
        dims = ai_results.get('dimensions', (0, 0, 0))
        # NIfTI shape is usually (x, y, z)
        # x = sagittal, y = coronal, z = axial
        slice_counts = {
            "sagittal": dims[0] if len(dims) > 0 else 0,
            "coronal": dims[1] if len(dims) > 1 else 0,
            "axial": dims[2] if len(dims) > 2 else 0
        }
    
    else:
        # Default empty counts if no results
        slice_counts = {"axial": 0, "coronal": 0, "sagittal": 0}

    # Build teeth array with their problems (same as Pano)
    teeth = []
    for tooth in teeth_data:
        # Get problems for this tooth
        tooth_problems = [
            f for f in findings_list 
            if f.get('tooth_detection_id') == tooth.get('detection_id')
        ]
        
        teeth.append({
            'toothId': tooth.get('tooth_class'),
            'toothNumber': tooth.get('tooth_number'),
            'toothType': tooth.get('tooth_type'),
            'bbox': tooth.get('bbox'),
            'confidence': tooth.get('confidence'),
            'problems': tooth_problems  # Problems attached to this tooth
        })
    
    # Calculate statistics
    healthy_count = len([t for t in teeth if not t['problems']])
    unhealthy_count = len([t for t in teeth if t['problems']])
    
    problems_distribution = {}
    severity_distribution = {}
    for finding in findings_list:
        problem = finding.get('problem', 'unknown')
        severity = finding.get('severity', 'unknown')
        problems_distribution[problem] = problems_distribution.get(problem, 0) + 1
        severity_distribution[severity] = severity_distribution.get(severity, 0) + 1

    # Build report (same structure as Pano)
    report = {
        "patientInfo": {
            "patientId": patient_id,
            "info": patient_info.get('info', {})
        },
        
        "teeth": teeth,  # ⭐ Same as Pano - hierarchical
        
        "statistics": {
            "totalTeeth": total_teeth,
            "healthy": healthy_count,
            "unhealthy": unhealthy_count,
            "treated": 0,  # TODO: Calculate from findings
            "missing": 0,  # TODO: Calculate from segmentation
            "problemsDistribution": problems_distribution,
            "severityDistribution": severity_distribution,
            "requiresAttention": unhealthy_count > 0
        },
        
        "scanInfo": {
            "device": "CBCT Scanner",
            "scanDate": datetime.datetime.now().isoformat(),
            "scanType": "cbct",
            "imageFormat": "DICOM",  # 3D format
            "dimensions": {
                "x": slice_counts['sagittal'],
                "y": slice_counts['coronal'],
                "z": slice_counts['axial']
            }
        },
        
        "aiAnalysis": {
            "segmentationModel": "",  # Will be populated during analysis
            "detectionModels": [],  # Will be populated during analysis
            "analysisDate": datetime.datetime.now().isoformat(),
            "processingTime": 0,
            "confidence": 0,
            "status": ai_status
        },
        
        "conclusion": "",
        "conclusionUpdatedAt": None,
        
        "metadata": {
            "reportId": report_id,
            "reportType": "cbct",
            "clinicId": clinic_id,
            "generatedBy": "CBCT AI Analysis System v2",
            "version": "2.0",
            "lastUpdated": datetime.datetime.now().isoformat(),
            "slice_count": slice_counts  # [NEW] Added as requested
        }
    }
    
    return report

