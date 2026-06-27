from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks
from app.core.supabase_client import supabase
from app.services.video_pipeline import process_video_job
from app.services.rag_service import get_rag_service
from app.services.sop_service import get_sop_service
import uuid
import re
import os
import logging
import urllib.request

router = APIRouter()
logger = logging.getLogger(__name__)


def _fetch_public_url_file_size(public_url: str) -> int | None:
    try:
        request = urllib.request.Request(public_url, method="HEAD")
        with urllib.request.urlopen(request, timeout=10) as response:
            length = response.headers.get("Content-Length") or response.headers.get("content-length")
            if length:
                return int(length)
    except Exception as exc:
        logger.warning("Failed to fetch file metadata from public URL %s: %s", public_url, exc)
    return None


def _safe_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name)


@router.post("/video")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_id: str = Form(...),
    user_id: str = Form(...),
):
    """Upload video via service role."""
    if not project_id or not user_id:
        logger.error("Video upload failed: Missing project_id or user_id.")
        raise HTTPException(status_code=400, detail="project_id and user_id are required")

    logger.info(f"Video upload initiated for project_id={project_id}, user_id={user_id}, filename={file.filename}")
    file_name = f"{uuid.uuid4()}-{_safe_filename(file.filename or 'video.mp4')}"
    storage_path = f"{project_id}/{file_name}"
    content = await file.read()

    try:
        logger.info(f"Uploading file content to Supabase storage bucket 'videos': {storage_path}")
        supabase.storage.from_("videos").upload(
            storage_path,
            content,
            {"content-type": file.content_type or "video/mp4", "upsert": "false"},
        )
        logger.info("Supabase storage upload completed successfully.")
    except Exception as e:
        logger.error(f"Supabase storage upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {e}")

    public_url = supabase.storage.from_("videos").get_public_url(storage_path)

    try:
        logger.info("Creating database record in video_uploads table.")
        video_res = supabase.table("video_uploads").insert({
            "project_id": project_id,
            "user_id": user_id,
            "title": file.filename or file_name,
            "file_url": storage_path,
            "status": "pending",
        }).execute()
    except Exception as db_err:
        logger.error(f"Failed to create video upload record: {db_err}")
        raise HTTPException(status_code=500, detail=f"Database error on video record creation: {db_err}")

    if not video_res.data:
        logger.error("Failed to create video record: Empty response returned from database.")
        raise HTTPException(status_code=500, detail="Failed to create video record")

    video_record = video_res.data[0]
    video_id = video_record["id"]
    logger.info(f"Video record created successfully: video_id={video_id}")

    try:
        logger.info("Creating database record in analysis_jobs table.")
        job_res = supabase.table("analysis_jobs").insert({
            "user_id": user_id,
            "target_id": video_id,
            "job_type": "full_video_pipeline",
            "status": "queued",
        }).execute()
    except Exception as db_err:
        logger.error(f"Failed to create analysis job record: {db_err}")
        raise HTTPException(status_code=500, detail=f"Database error on job creation: {db_err}")

    if not job_res.data:
        logger.error("Failed to create analysis job: Empty response returned from database.")
        raise HTTPException(status_code=500, detail="Failed to create analysis job")

    job_id = job_res.data[0]["id"]
    logger.info(f"Analysis job record created successfully: job_id={job_id}")
    
    logger.info("Queueing background task for process_video_job pipeline.")
    func = getattr(process_video_job, "run", process_video_job)
    background_tasks.add_task(func, job_id, video_id, project_id, storage_path, user_id)

    return {
        "status": "success",
        "video_id": video_id,
        "job_id": job_id,
        "file_url": public_url,
        "storage_path": storage_path,
        "message": "Video uploaded and analysis queued.",
    }


@router.post("/sop")
async def upload_sop(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_id: str = Form(...),
    user_id: str = Form(...),
):
    """Upload SOP document via service role."""
    if not project_id or not user_id:
        logger.error("SOP upload failed: Missing project_id or user_id.")
        raise HTTPException(status_code=400, detail="project_id and user_id are required")

    logger.info(f"SOP upload initiated for project_id={project_id}, user_id={user_id}, filename={file.filename}")
    file_name = f"{uuid.uuid4()}-{_safe_filename(file.filename or 'document.pdf')}"
    storage_path = f"{project_id}/{file_name}"
    content = await file.read()
    file_size = len(content or b"")

    os.makedirs('tmp', exist_ok=True)
    tmp_path = os.path.join('tmp', file_name)
    try:
        logger.info(f"Writing SOP file content to temporary path: {tmp_path}")
        with open(tmp_path, 'wb') as tmpf:
            tmpf.write(content)
        logger.info("Temporary SOP file written successfully.")
    except Exception as e:
        logger.warning(f"Unable to write temporary SOP file for background parsing: {e}")
        tmp_path = None

    try:
        logger.info(f"Uploading file content to Supabase storage bucket 'sop-documents': {storage_path}")
        supabase.storage.from_("sop-documents").upload(
            storage_path,
            content,
            {"content-type": file.content_type or "application/pdf", "upsert": "false"},
        )
        logger.info("Supabase storage upload completed successfully.")
    except Exception as e:
        logger.error(f"Supabase storage upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {e}")

    public_url = supabase.storage.from_("sop-documents").get_public_url(storage_path)

    if not file_size:
        metadata_size = _fetch_public_url_file_size(public_url)
        if metadata_size:
            file_size = metadata_size

    doc_payload = {
        "project_id": project_id,
        "user_id": user_id,
        "title": file.filename or file_name,
        "file_url": storage_path,
    }
    if file_size is not None:
        doc_payload["file_size"] = file_size

    try:
        logger.info("Creating database record in sop_documents table.")
        doc_res = supabase.table("sop_documents").insert(doc_payload).execute()
    except Exception as err:
        if "file_size" in doc_payload:
            logger.warning(
                "Initial SOP insert failed due to unsupported file_size column, retrying without file_size: %s",
                err,
            )
            doc_payload.pop("file_size", None)
            try:
                doc_res = supabase.table("sop_documents").insert(doc_payload).execute()
            except Exception as retry_err:
                logger.error(f"SOP insert retry failed: {retry_err}")
                raise HTTPException(status_code=500, detail=f"Failed to create SOP record on retry: {retry_err}")
        else:
            logger.error(f"Failed to create SOP record: {err}")
            raise HTTPException(status_code=500, detail=f"Failed to create SOP record: {err}")

    if not getattr(doc_res, "data", None):
        logger.error("Failed to create SOP record: Empty response returned from database.")
        raise HTTPException(status_code=500, detail="Failed to create SOP record")

    document_id = str(doc_res.data[0]["id"])
    background_tasks.add_task(
        get_sop_service().process_sop_upload,
        project_id,
        storage_path,
        tmp_path,
        document_id,
        file.filename or file_name,
        user_id,
    )

    return {
        "status": "success",
        "document_id": document_id,
        "file_url": public_url,
        "storage_path": storage_path,
        "file_size": file_size,
        "message": "SOP document uploaded successfully. Parsing and embedding are queued.",
    }
