from fastapi import APIRouter, Query
from app.core.supabase_client import supabase
from app.services.analytics_service import get_analytics_service

router = APIRouter()

@router.get("/analytics")
def get_dashboard_analytics(project_id: str = Query(None), user_id: str = Query(None)):
    """Get full historical analytics for the dashboard."""
    if not project_id or not user_id:
        return {"status": "error", "message": "project_id and user_id required"}
        
    analytics = get_analytics_service()
    
    return {
        "monthly_violations": analytics.get_violation_trend_by_type(user_id, project_id, days=90),
        "risk_trend": analytics.get_risk_score_trend(user_id, project_id, days=90, group_by="month"),
        "ppe_trend": analytics.get_ppe_compliance_trend(user_id, project_id, days=90, group_by="month"),
        "sop_trend": analytics.get_sop_compliance_trend(user_id, project_id, days=90),
        "training_effectiveness": analytics.get_training_effectiveness(user_id, project_id),
        "ppe_by_type": analytics.get_ppe_violations_by_type(user_id, project_id),
        "training_recommendations": analytics.get_training_recommendations_from_violations(user_id, project_id),
    }

@router.get("/stats")
def get_dashboard_stats(project_id: str = Query(None), user_id: str = Query(None)):
    """Get aggregated dashboard statistics from Supabase."""
    if not project_id or not user_id:
        return {
            "total_violations": 0,
            "ppe_compliance_percent": None,
            "high_risk_zones": 0,
            "incident_risk_score": None,
            "evidence_records": 0,
            "recent_reports": [],
            "uploaded_videos": [],
        }

    videos = supabase.table("video_uploads").select("id, title, status, file_url, created_at").eq("project_id", project_id).eq("user_id", user_id).execute()
    video_ids = [v["id"] for v in (videos.data or [])]

    viol_res = supabase.table("violation_tracking").select("id, video_uploads!inner(project_id)").eq("video_uploads.project_id", project_id).eq("user_id", user_id).execute()
    violations = viol_res.data or []

    evidence = supabase.table("evidence_records").select("id").eq("project_id", project_id).eq("user_id", user_id).execute()
    evidence_count = len(evidence.data or [])

    risks = supabase.table("risk_assessments").select("score,details").eq("project_id", project_id).eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
    max_risk = float(risks.data[0]["score"]) if risks.data else 0

    viol_count = len(violations)
    # Never show 100% PPE compliance if there are violations
    if not video_ids:
        ppe = None
    elif viol_count == 0:
        ppe = None  # No data processed yet — don't claim 100%
    else:
        ppe = max(0, 100 - viol_count * 5)

    reports = supabase.table("generated_reports").select("*").eq("project_id", project_id).eq("user_id", user_id).order("created_at", desc=True).limit(5).execute()

    # Fetch latest job result for timeline + worker_summary
    job_result = {}
    if video_ids:
        latest_job_res = supabase.table("analysis_jobs").select("result").in_("target_id", video_ids).eq("user_id", user_id).eq("status", "completed").order("created_at", desc=True).limit(1).execute()
        if latest_job_res.data:
            job_result = latest_job_res.data[0].get("result") or {}

    return {
        "total_violations": viol_count,
        "ppe_compliance_percent": round(ppe, 1) if ppe is not None else None,
        "high_risk_zones": 1 if max_risk > 80 else 0,
        "incident_risk_score": max_risk if risks.data else None,
        "evidence_records": evidence_count,
        "latest_risk_details": risks.data[0]["details"] if risks.data else None,
        "timeline": job_result.get("violation_timeline") or job_result.get("timeline") or [],
        "worker_summary": job_result.get("worker_summary") or {},
        "recent_reports": reports.data or [],
        "uploaded_videos": videos.data or [],
    }
