
import json
import random

def generate_full_report():
    teeth = []
    
    # FDI Notation:
    # 18-11 (Upper Right)
    # 21-28 (Upper Left)
    # 48-41 (Lower Right)
    # 31-38 (Lower Left)
    
    # Standard mapping for types
    tooth_types = {
        1: "Central Incisor",
        2: "Lateral Incisor",
        3: "Canine",
        4: "First Premolar",
        5: "Second Premolar",
        6: "First Molar",
        7: "Second Molar",
        8: "Third Molar"
    }

    quadrants = [1, 2, 3, 4]
    
    for quad in quadrants:
        # 1 and 2 go 1-8 (Center to Back) or 8-1? 
        # FDI is usually enumerated 11..18, 21..28 etc.
        # Let's just loop 1 to 8.
        for i in range(1, 9):
            tooth_num = quad * 10 + i
            tooth_type = tooth_types[i]
            
            # Add some logic for bounding boxes (just simulated)
            # This is just dummy data for visualization
            bbox = [
                100 + (i * 20) + (0 if quad in [1,4] else 200), # x
                100 + (100 if quad in [3,4] else 0),           # y
                30, # w
                40  # h
            ]
            
            # Problems
            problems = []
            
            # Add a specific problem to Tooth 13 as requested previously
            if tooth_num == 13:
                problems.append({
                    "id": f"prob_{tooth_num}_1",
                    "tooth_detection_id": f"det_{tooth_num}",
                    "problem": "caries",
                    "severity": "medium",
                    "location": "distal",
                    "confidence": 0.88,
                    "details": "Example caries on Tooth 13"
                })
            
            # Add some random problems to other teeth
            elif random.random() > 0.8:
                 problems.append({
                    "id": f"prob_{tooth_num}_1",
                    "tooth_detection_id": f"det_{tooth_num}",
                    "problem": "calculus" if random.random() > 0.5 else "bone_loss",
                    "severity": "low",
                    "confidence": 0.90
                })

            teeth.append({
                "toothId": str(tooth_num),
                "toothNumber": tooth_num,
                "toothType": tooth_type,
                "bbox": bbox,
                "confidence": 0.95 + (random.random() * 0.04),
                "problems": problems
            })
            
    report = {
        "patientInfo": {
            "patientId": "PAT-FULL-001",
            "info": {
                "name": "Full Dentition Sample",
                "age": 28,
                "gender": "Female"
            }
        },
        "teeth": teeth,
        "statistics": {
            "totalTeeth": 32,
            "healthy": len([t for t in teeth if not t['problems']]),
            "unhealthy": len([t for t in teeth if t['problems']]),
            "requiresAttention": True
        },
        "metadata": {
            "reportType": "cbct",
            "version": "2.0",
            "note": "Generated full dentition sample"
        }
    }
    
    return report

if __name__ == "__main__":
    report = generate_full_report()
    print(json.dumps(report, indent=2))
