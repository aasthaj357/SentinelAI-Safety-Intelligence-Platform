from fastapi import APIRouter, HTTPException
from app.core.supabase_client import supabase

router = APIRouter()

@router.get("/{evidence_id}")
def get_evidence(evidence_id: str, user_id: str):
    result = supabase.table("evidence_records").select("*").eq("id", evidence_id).eq("user_id", user_id).maybe_single().execute()
    evidence = getattr(result, 'data', None)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence record not found")
    return evidence

@router.get("/project/{project_id}")
def list_project_evidence(project_id: str, user_id: str):
    result = supabase.table("evidence_records").select("*").eq("project_id", project_id).eq("user_id", user_id).order("created_at", desc=True).execute()
    return getattr(result, 'data', None) or []
