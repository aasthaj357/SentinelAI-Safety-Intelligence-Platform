from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from app.core.supabase_client import supabase

router = APIRouter()

class ApprovalAction(BaseModel):
    action: str  # 'approved' or 'rejected'
    user_id: str

@router.get("/")
def list_approvals(project_id: str, status: str = "pending"):
    """List all approval requests for a project."""
    res = supabase.table("approval_requests").select("*").eq("project_id", project_id).eq("status", status).order("created_at", desc=True).execute()
    return res.data or []

@router.get("/{request_id}")
def get_approval(request_id: str):
    """Retrieve details of a specific approval request."""
    res = supabase.table("approval_requests").select("*").eq("id", request_id).maybe_single().execute()
    req = getattr(res, "data", None)
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return req

@router.post("/{request_id}/action")
def take_approval_action(request_id: str, request: ApprovalAction, background_tasks: BackgroundTasks):
    """Approve or reject a pending request, updating execution states."""
    if request.action not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid action. Must be 'approved' or 'rejected'")
        
    # Fetch request
    res = supabase.table("approval_requests").select("*").eq("id", request_id).maybe_single().execute()
    ticket = getattr(res, "data", None)
    if not ticket:
        raise HTTPException(status_code=404, detail="Approval request not found")
        
    # Update ticket status
    supabase.table("approval_requests").update({
        "status": request.action,
        "updated_at": "now()"
    }).eq("id", request_id).execute()
    
    # Cascade status to target record (e.g. analysis job or report)
    target_id = ticket.get("target_id")
    req_type = ticket.get("request_type")
    
    if req_type == "high_risk_incident":
        if request.action == "approved":
            # Resume video pipeline from checkpoint
            details = ticket.get("details") or {}
            checkpoint = details.get("checkpoint") or {}
            
            # Query job target video
            job_res = supabase.table("analysis_jobs").select("*").eq("id", target_id).maybe_single().execute()
            job_data = getattr(job_res, "data", None)
            
            if job_data:
                video_res = supabase.table("video_uploads").select("*").eq("id", job_data["target_id"]).maybe_single().execute()
                video_data = getattr(video_res, "data", None)
                
                if video_data:
                    from app.services.video_pipeline import process_video_job
                    
                    supabase.table("analysis_jobs").update({"status": "processing"}).eq("id", target_id).execute()
                    
                    background_tasks.add_task(
                        process_video_job,
                        job_id=target_id,
                        video_id=job_data["target_id"],
                        project_id=video_data["project_id"],
                        file_url=video_data["file_url"],
                        user_id=ticket.get("user_id"),
                        start_frame=checkpoint.get("checkpoint_frame", 1),
                        worker_state=checkpoint.get("tracked_workers"),
                        violations_state=checkpoint.get("cumulative_violations")
                    )
        else:
            supabase.table("analysis_jobs").update({"status": "failed"}).eq("id", target_id).execute()
            
    elif req_type == "report_generation":
        report_status = "safety_analysis_html" if request.action == "approved" else "rejected"
        supabase.table("generated_reports").update({"type": report_status}).eq("id", target_id).execute()
        
    # Log to audit trail
    supabase.table("audit_logs").insert({
        "user_id": request.user_id,
        "action": f"supervisor_{request.action}",
        "details": {"request_id": request_id, "type": req_type, "target_id": target_id}
    }).execute()
    
    return {"status": "success", "request_id": request_id, "action": request.action}
