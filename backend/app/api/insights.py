from fastapi import APIRouter
from app.core.supabase_client import supabase

router = APIRouter()

@router.get("/violations")
def get_violations(project_id: str, user_id: str, video_id: str = None):
    if video_id:
        query = supabase.table("violation_tracking").select("*").eq("video_id", video_id).eq("user_id", user_id)
    else:
        # Join via video_uploads to scope by project
        query = supabase.table("violation_tracking").select("*, video_uploads!inner(project_id)").eq("video_uploads.project_id", project_id).eq("user_id", user_id)
    return query.execute().data

@router.get("/transcripts")
def get_transcripts(video_id: str, user_id: str):
    # Verify the video belongs to the requesting user before returning transcript
    video = supabase.table("video_uploads").select("id").eq("id", video_id).eq("user_id", user_id).maybe_single().execute()
    if not getattr(video, 'data', None):
        return []
    return supabase.table("video_transcripts").select("*").eq("video_id", video_id).execute().data

@router.get("/risk")
def get_risk(project_id: str, user_id: str, limit: int = 3):
    return supabase.table("risk_assessments").select("*").eq("project_id", project_id).eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute().data

@router.get("/predictions")
def get_predictions(project_id: str, user_id: str, limit: int = 3):
    return supabase.table("incident_predictions").select("*").eq("project_id", project_id).eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute().data

@router.get("/trainings")
def get_trainings(project_id: str, user_id: str, limit: int = 3):
    return supabase.table("training_recommendations").select("*").eq("project_id", project_id).eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute().data

@router.get("/logs")
def get_logs(project_id: str, user_id: str, limit: int = 3):
    return supabase.table("knowledge_base").select("*").eq("project_id", project_id).eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute().data

