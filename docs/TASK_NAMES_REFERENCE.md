# Task Names Reference

## CBCT Workflow Tasks

| Task Name (in workflow) | Actual Celery Task | File Location |
|------------------------|-------------------|---------------|
| `ai_analysis` | ✅ `ai_analysis` | `app/celery_tasks/ai/analysis.py` |
| `format_report` | ✅ `format_report` | `app/celery_tasks/reports/formatter.py` |
| `upload_report_json` | ✅ `upload_report_json` | `app/celery_tasks/reports/uploader.py` |
| `upload_slices` | ✅ `upload_slices` | `app/celery_tasks/slices/uploader.py` |
| `finalize_report` | ✅ `finalize_report` | `app/celery_tasks/aggregation/finalizer.py` |

### CBCT Workflow Structure:
```python
chain(
    group(
        chain(
            'ai_analysis',      # Step 1: AI analysis via taskes/ai_taskes/pipeline.py
            'format_report',     # Step 2: Format report
            'upload_report_json' # Step 3: Upload to storage
        ),
        'upload_slices'          # Parallel: Upload slices
    ),
    'finalize_report'            # Final: Aggregate
)
```

---

## Pano Workflow Tasks

| Task Name (in workflow) | Actual Celery Task | File Location |
|------------------------|-------------------|---------------|
| `validate_pano_v2` | ✅ `validate_pano_v2` | `app/celery_tasks/pano/tasks.py` |
| `upload_pano_v2` | ✅ `upload_pano_v2` | `app/celery_tasks/pano/tasks.py` |
| `analyze_pano_v2` | ✅ `analyze_pano_v2` | `app/celery_tasks/pano/tasks.py` |
| `aggregate_pano_v2` | ✅ `aggregate_pano_v2` | `app/celery_tasks/pano/tasks.py` |

### Pano Workflow Structure:
```python
chain(
    'validate_pano_v2',  # Step 1: Validate image
    'upload_pano_v2',    # Step 2: Upload to Supabase
    'analyze_pano_v2',   # Step 3: AI analysis (via app/ai/workflow.py)
    'aggregate_pano_v2'  # Step 4: Finalize
)
```

---

## Status: ✅ All Task Names Match!

Both workflows use the correct task names that exist in the Celery tasks.

**CBCT**: Uses generic tasks (`ai_analysis`, `format_report`, etc.)
**Pano**: Uses dedicated v2 tasks (`validate_pano_v2`, `upload_pano_v2`, etc.)
