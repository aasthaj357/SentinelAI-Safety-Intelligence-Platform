from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.core.supabase_client import supabase
from app.services.video_pipeline import process_video_job
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class AnalyzeRequest(BaseModel):
    video_id: str
    project_id: str
    user_id: str
    file_url: str

def _extract_storage_path(file_url: str) -> str:
    if not file_url:
        return file_url

    if file_url.startswith("http"):
        markers = [
            "/object/public/videos/",
            "/object/sign/videos/",
            "/storage/v1/object/public/videos/",
            "/storage/v1/object/sign/videos/",
            "/videos/"
        ]
        for marker in markers:
            if marker in file_url:
                return file_url.split(marker, 1)[1]
    return file_url


@router.post("/video")
def analyze_video(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """Trigger background video analysis pipeline."""
    file_url = _extract_storage_path(request.file_url)
    # Create analysis job
    res = supabase.table("analysis_jobs").insert({
        "target_id": request.video_id,
        "user_id": request.user_id,
        "job_type": "full_video_pipeline",
        "status": "queued"
    }).execute()
    
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create analysis job")
        
    job_id = res.data[0]["id"]
    
    # Run via background tasks to avoid celery queue hang when no workers are running
    background_tasks.add_task(process_video_job, job_id, request.video_id, request.project_id, file_url, request.user_id)
    
    return {"status": "success", "job_id": job_id, "message": "Analysis queued"}

import logging
logger = logging.getLogger(__name__)

@router.get("/{job_id}/status")
def get_analysis_status(job_id: str):
    """Get the AI analysis status for a job."""
    res = supabase.table("analysis_jobs").select("*").eq("id", job_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return res.data[0]

@router.get("/video/{video_id}")
def get_video_analysis_details(video_id: str, project_id: str, user_id: str):
    # Fetch video record
    video_res = supabase.table("video_uploads").select("*").eq("id", video_id).eq("project_id", project_id).eq("user_id", user_id).maybe_single().execute()
    video = getattr(video_res, 'data', None)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    # Get signed url or fallback public url
    video_url = video.get("file_url")
    try:
        storage_path = video.get("file_url")
        if storage_path.startswith("http"):
            # extract path
            for marker in ["/object/public/videos/", "/object/sign/videos/"]:
                if marker in storage_path:
                    storage_path = storage_path.split(marker, 1)[1]
                    break
        url_data = supabase.storage.from_("videos").create_signed_url(storage_path, 3600)
        # Try both casing styles
        if url_data and isinstance(url_data, dict):
            if "signedURL" in url_data:
                video_url = url_data["signedURL"]
            elif "signedUrl" in url_data:
                video_url = url_data["signedUrl"]
        elif hasattr(url_data, 'data') and url_data.data:
            # handle cases where supabase-py returns wrapper object
            if isinstance(url_data.data, dict):
                video_url = url_data.data.get("signedUrl") or url_data.data.get("signedURL") or video_url
            elif isinstance(url_data.data, str):
                video_url = url_data.data
    except Exception as e:
        logger.warning(f"Failed to generate signed url: {e}")
        
    # Fetch transcript
    transcript_res = supabase.table("video_transcripts").select("*").eq("video_id", video_id).maybe_single().execute()
    transcript = getattr(transcript_res, 'data', None)
    
    # Fetch violations
    violations_res = supabase.table("violation_tracking").select("*").eq("video_id", video_id).eq("user_id", user_id).order("timestamp", desc=False).execute()
    violations = getattr(violations_res, 'data', None) or []
    
    # Fetch evidence records
    evidence_res = supabase.table("evidence_records").select("*").eq("video_id", video_id).eq("project_id", project_id).eq("user_id", user_id).order("timestamp", desc=False).execute()
    evidence = getattr(evidence_res, 'data', None) or []
    
    # Fetch analysis job status
    job_res = supabase.table("analysis_jobs").select("*").eq("target_id", video_id).eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
    job = getattr(job_res, 'data', None)
    job_status = job[0].get("status") if job else None
    
    return {
        "video": video,
        "video_url": video_url,
        "transcript": transcript,
        "violations": violations,
        "evidence": evidence,
        "job_status": job_status
    }


@router.get("/project/{project_id}/latest")
def get_latest_project_job(project_id: str, user_id: str):
    """Get the latest analysis job for the active project and user."""
    # Fetch latest job by getting project videos first
    videos_res = supabase.table("video_uploads").select("id").eq("project_id", project_id).eq("user_id", user_id).execute()
    video_ids = [v["id"] for v in getattr(videos_res, 'data', None) or []]
    if not video_ids:
        return None
    res = supabase.table("analysis_jobs").select("*").in_("target_id", video_ids).eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
    if not res.data:
        return None
    return res.data[0]


@router.post("/evidence/{evidence_id}/annotate")
def annotate_evidence_on_demand(evidence_id: str, user_id: str):
    """Generate annotated frame on demand if missing."""
    import cv2
    import requests
    import numpy as np

    # 1. Fetch evidence record
    ev_res = supabase.table("evidence_records").select("*").eq("id", evidence_id).eq("user_id", user_id).maybe_single().execute()
    evidence = getattr(ev_res, 'data', None)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence record not found")
        
    if evidence.get("annotated_screenshot_url"):
        return {"status": "success", "url": evidence["annotated_screenshot_url"]}
        
    # 2. Get frame record
    frame_id = evidence.get("frame_id")
    if not frame_id:
        raise HTTPException(status_code=400, detail="No frame ID associated with evidence")
        
    frame_res = supabase.table("frames").select("*").eq("id", frame_id).maybe_single().execute()
    frame_rec = getattr(frame_res, 'data', None)
    if not frame_rec or not frame_rec.get("image_path"):
        raise HTTPException(status_code=404, detail="Source frame not found")
        
    # 3. Download source frame image
    image_url = frame_rec["image_path"]
    try:
        resp = requests.get(image_url)
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch source frame image")
        arr = np.frombuffer(resp.content, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading frame image: {str(e)}")
        
    # 4. Annotate
    meta = evidence.get("metadata") or {}
    bbox = meta.get("bbox") or [0, 0, 100, 100]
    violation_type = evidence.get("detection_label", "violation")
    
    x1, y1, x2, y2 = [int(v) for v in bbox]
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
    label_text = f"MISSING {violation_type.replace('no-', '').upper()}"
    cv2.putText(img, label_text, (x1, max(y1-10, 10)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                
    # 5. Upload annotated frame
    success, buffer = cv2.imencode(".jpg", img)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to encode annotated image")
        
    project_id = evidence.get("project_id")
    video_id = evidence.get("video_id")
    storage_filename = f"{project_id}/{video_id}/annotated_{evidence_id}.jpg"
    
    try:
        supabase.storage.from_("annotated-videos").upload(
            storage_filename, buffer.tobytes(), {"content-type": "image/jpeg"}
        )
        annotated_url = supabase.storage.from_("annotated-videos").get_public_url(storage_filename)
        
        # 6. Update evidence record
        supabase.table("evidence_records").update({
            "annotated_screenshot_url": annotated_url
        }).eq("id", evidence_id).execute()
        
        return {"status": "success", "url": annotated_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload or save annotation: {str(e)}")

