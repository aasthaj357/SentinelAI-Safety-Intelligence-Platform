from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.supabase_client import supabase
from app.services.rag_service import get_rag_service
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
rag = get_rag_service()


from typing import Optional

class DemoLoadRequest(BaseModel):
    project_id: str
    user_id: Optional[str] = "00000000-0000-4000-a000-000000000001"


class ResetUserRequest(BaseModel):
    user_id: str


class EnsureProjectRequest(BaseModel):
    user_id: str
    project_name: str


def _clear_project_data(project_id: str, user_id: str | None = None):
    try:
        uuid.UUID(project_id)
    except ValueError:
        project_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, project_id))

    # Get video uploads ids for the project to delete related analysis_jobs and violation_tracking records first
    video_query = supabase.table("video_uploads").select("id").eq("project_id", project_id)
    if user_id:
        video_query = video_query.eq("user_id", user_id)
    video_res = video_query.execute()
    video_ids = [v["id"] for v in getattr(video_res, 'data', None) or []]

    if video_ids:
        # Delete analysis_jobs
        job_query = supabase.table("analysis_jobs").delete().in_("target_id", video_ids)
        if user_id:
            job_query = job_query.eq("user_id", user_id)
        job_query.execute()

        # Delete violation_tracking
        viol_query = supabase.table("violation_tracking").delete().in_("video_id", video_ids)
        if user_id:
            viol_query = viol_query.eq("user_id", user_id)
        viol_query.execute()

    # Tables with project_id
    tables = [
        "evidence_records",
        "risk_assessments",
        "incident_predictions",
        "training_recommendations",
        "knowledge_base",
        "generated_reports",
        "sop_documents",
        "chatbot_conversations"
    ]
    
    for table in tables:
        try:
            query = supabase.table(table).delete().eq("project_id", project_id)
            if user_id:
                query = query.eq("user_id", user_id)
            query.execute()
        except Exception as _e:
            logger.warning("Could not clear table %s: %s", table, _e)

    # Special case: video_uploads
    query = supabase.table("video_uploads").delete().eq("project_id", project_id)
    if user_id:
        query = query.eq("user_id", user_id)
    query.execute()


@router.post("/ensure-project")
def ensure_project(request: EnsureProjectRequest):
    """Create or return project for a user."""
    res = supabase.table("projects").select("id").eq("name", request.project_name).eq("user_id", request.user_id).execute()
    if res.data:
        return {"status": "success", "project_id": res.data[0]["id"]}

    new_id = str(uuid.uuid4())
    supabase.table("projects").insert({
        "id": new_id,
        "name": request.project_name,
        "user_id": request.user_id,
    }).execute()
    return {"status": "success", "project_id": new_id}


from datetime import datetime, timedelta
import random

@router.post("/load")
def load_demo_dataset(request: DemoLoadRequest):
    """Loads mock data to demonstrate the platform's capabilities."""
    project_id = request.project_id
    user_id = request.user_id

    try:
        uuid.UUID(project_id)
    except ValueError:
        project_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, project_id))

    res = supabase.table("projects").select("id").eq("id", project_id).execute()
    if not res.data:
         # Project should exist, but create if missing
         supabase.table("projects").insert({
            "id": project_id,
            "name": f"Project-{user_id[:8]}",
            "user_id": user_id,
        }).execute()
    else:
         # Project exists. Update user_id to match current requester
         supabase.table("projects").update({
            "user_id": user_id,
         }).eq("id", project_id).execute()


    try:
        _clear_project_data(project_id, user_id)
    except Exception as e:
        logger.warning("Error clearing old data: %s", e)

    video1_id = str(uuid.uuid4())
    video2_id = str(uuid.uuid4())
    video3_id = str(uuid.uuid4())

    supabase.table("video_uploads").insert([
        {"id": video1_id, "project_id": project_id, "user_id": user_id, "title": "Sector A - Forklift Operation (Compliant)", "file_url": "https://example.com/vid1.mp4", "status": "analyzed"},
        {"id": video2_id, "project_id": project_id, "user_id": user_id, "title": "Sector B - Assembly Line (Medium Risk)", "file_url": "https://example.com/vid2.mp4", "status": "analyzed"},
        {"id": video3_id, "project_id": project_id, "user_id": user_id, "title": "Sector C - Heavy Machinery (Critical Risk)", "file_url": "https://example.com/vid3.mp4", "status": "analyzed"},
    ]).execute()

    # Generate mock frames and workers for the three videos to enable correct FK resolutions
    frames_to_insert = [
        {"video_id": video1_id, "frame_number": 30, "timestamp": 1.0, "image_path": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=800"},
        {"video_id": video1_id, "frame_number": 60, "timestamp": 2.0, "image_path": "https://images.unsplash.com/photo-1581092921461-eab62e97a780?w=800"},
        
        {"video_id": video2_id, "frame_number": 30, "timestamp": 1.0, "image_path": "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=800"},
        {"video_id": video2_id, "frame_number": 60, "timestamp": 2.0, "image_path": "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=800"},
        
        {"video_id": video3_id, "frame_number": 30, "timestamp": 1.0, "image_path": "https://images.unsplash.com/photo-1590069261209-f8e9b8642343?w=800"},
        {"video_id": video3_id, "frame_number": 60, "timestamp": 2.0, "image_path": "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=800"}
    ]
    frames_res = supabase.table("frames").insert(frames_to_insert).execute()
    frames_by_video = {}
    for f in (frames_res.data or []):
        vid = f["video_id"]
        if vid not in frames_by_video:
            frames_by_video[vid] = []
        frames_by_video[vid].append(f)
        
    workers_to_insert = [
        {"video_id": video1_id, "worker_label": "Worker_1", "track_id": 1, "start_frame": 30, "end_frame": 60},
        
        {"video_id": video2_id, "worker_label": "Worker_1", "track_id": 1, "start_frame": 30, "end_frame": 60},
        {"video_id": video2_id, "worker_label": "Worker_2", "track_id": 2, "start_frame": 30, "end_frame": 60},
        
        {"video_id": video3_id, "worker_label": "Worker_1", "track_id": 1, "start_frame": 30, "end_frame": 60},
        {"video_id": video3_id, "worker_label": "Worker_2", "track_id": 2, "start_frame": 30, "end_frame": 60},
        {"video_id": video3_id, "worker_label": "Worker_3", "track_id": 3, "start_frame": 30, "end_frame": 60}
    ]
    workers_res = supabase.table("workers").insert(workers_to_insert).execute()
    workers_by_video = {}
    for w in (workers_res.data or []):
        vid = w["video_id"]
        if vid not in workers_by_video:
            workers_by_video[vid] = []
        workers_by_video[vid].append(w)

    # Generate historical violations over the last 90 days
    now = datetime.now()
    historical_violations = []
    historical_evidence = []
    
    # We want a trend showing improvement over time.
    # Month 1 (oldest): high violations. Month 2: medium. Month 3 (newest): low.
    for days_ago in range(90, -1, -1):
        date_str = (now - timedelta(days=days_ago)).isoformat()
        
        # Decide how many violations today based on how long ago it was
        if days_ago > 60: # Month 1
            num_viols = random.randint(1, 3)
            risk_score = random.randint(70, 95)
        elif days_ago > 30: # Month 2
            num_viols = random.randint(0, 2)
            risk_score = random.randint(50, 75)
        else: # Month 3 (Recent)
            num_viols = random.randint(0, 1)
            # Add occasional spike
            if days_ago == 5:
                num_viols = 3
            risk_score = random.randint(20, 55)
            
        for _ in range(num_viols):
            vtype = random.choice(["No Helmet", "No Vest", "Restricted Zone Entry", "No Helmet", "No Helmet", "No Gloves"])
            v_id = str(uuid.uuid4())
            
            # Select frame and worker for violation
            video_frames = frames_by_video.get(video2_id, [])
            video_workers = workers_by_video.get(video2_id, [])
            
            frame = random.choice(video_frames) if video_frames else None
            worker = random.choice(video_workers) if video_workers else None
            
            frame_id = frame["id"] if frame else None
            worker_id = worker["id"] if worker else None
            frame_num = frame["frame_number"] if frame else 30
            worker_label = worker["worker_label"] if worker else "Worker_1"
            screenshot_url = frame["image_path"] if frame else "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=800"
            
            ts = round(random.uniform(1.0, 60.0), 1)
            conf = round(random.uniform(0.75, 0.99), 2)
            dur_sec = round(random.uniform(5.0, 45.0), 1)
            
            # Detailed metadata payload
            metadata_payload = {
                "worker_id": worker_label,
                "frame_number": frame_num,
                "frame_start": frame_num,
                "frame_end": frame_num + 15,
                "timestamp": ts,
                "duration_seconds": dur_sec,
                "bbox": [100, 150, 250, 400],
                "confidence": conf,
                "violation_type": vtype.lower().replace(" ", "-"),
                "source": "compliance_auditor",
                "ppe_type": vtype.replace("No ", "").lower() if "No" in vtype else "restricted_zone"
            }
            
            historical_violations.append({
                "id": v_id,
                "video_id": video2_id,
                "user_id": user_id,
                "violation_type": vtype,
                "timestamp": ts,
                "confidence": conf,
                "frame_id": frame_id,
                "worker_id": worker_id,
                "metadata": metadata_payload,
                "created_at": date_str
            })
            
            # 50% chance of creating evidence for it
            if random.choice([True, False]):
                historical_evidence.append({
                    "project_id": project_id,
                    "user_id": user_id,
                    "video_id": video2_id,
                    "violation_id": v_id,
                    "frame_id": frame_id,
                    "worker_id": worker_id,
                    "evidence_type": "video_violation",
                    "frame_num": frame_num,
                    "timestamp": ts,
                    "detection_label": vtype,
                    "confidence": conf,
                    "screenshot_url": screenshot_url,
                    "annotated_screenshot_url": screenshot_url,
                    "sop_section": "Standard PPE" if "Helmet" in vtype or "Vest" in vtype else "Restricted Zones",
                    "sop_excerpt": f"Section 2.1: Safety {vtype} mandatory in zone B.",
                    "risk_reason": f"Worker observed without safety {vtype} in active production zone.",
                    "risk_score": int(risk_score),
                    "metadata": metadata_payload,
                    "created_at": date_str
                })
                
        # Generate 1 risk assessment per week roughly
        if days_ago % 7 == 0:
            if days_ago > 60:
                reasoning = "Elevated risk due to frequent PPE violations and restricted zone breaches in early observation period."
                evidence = ["Multiple No Helmet events in Sector B", "Restricted zone entries near active machinery", "Low compliance with SOP-02 and SOP-08"]
                related_sops = ["SOP-02: Head Protection", "SOP-08: Machinery Safety", "SOP-05: Restricted Zones"]
            elif days_ago > 30:
                reasoning = "Moderate risk following initial safety interventions. PPE compliance improving but zone violations persist."
                evidence = ["Reduced helmet violations vs prior month", "2 restricted zone entries in Sector C", "Partial compliance with updated SOP-05"]
                related_sops = ["SOP-05: Restricted Zones", "SOP-02: Head Protection"]
            else:
                reasoning = "Improving safety trajectory. Recent training has reduced violations. Ongoing monitoring recommended."
                evidence = ["Low PPE violations this period", "Zone compliance improved after retraining", "Near-target compliance with SOP-08"]
                related_sops = ["SOP-08: Machinery Safety", "SOP-03: Housekeeping"]
                
            risk_level = "Low"
            if risk_score > 75:
                risk_level = "Critical"
            elif risk_score > 50:
                risk_level = "High"
            elif risk_score > 25:
                risk_level = "Medium"
                
            supabase.table("risk_assessments").insert({
                "project_id": project_id,
                "video_id": video2_id,
                "user_id": user_id,
                "score": risk_score,
                "details": {
                    "reasoning": reasoning,
                    "evidence": evidence,
                    "related_sop_rules": related_sops,
                    "confidence": 0.85,
                    "level": risk_level
                },
                "created_at": date_str
            }).execute()

    if historical_violations:
        # Insert in chunks of 50
        for i in range(0, len(historical_violations), 50):
            supabase.table("violation_tracking").insert(historical_violations[i:i+50]).execute()
            
    inserted_evidence = []
    if historical_evidence:
        for i in range(0, len(historical_evidence), 50):
            res = supabase.table("evidence_records").insert(historical_evidence[i:i+50]).execute()
            if res.data:
                inserted_evidence.extend(res.data)
                
    if not inserted_evidence:
        # Force insert at least one evidence record to avoid empty lists or N/A
        v_id = str(uuid.uuid4())
        f_rec = frames_by_video[video2_id][0]
        w_rec = workers_by_video[video2_id][0]
        
        meta_payload = {
            "worker_id": w_rec["worker_label"],
            "frame_number": f_rec["frame_number"],
            "frame_start": f_rec["frame_number"],
            "frame_end": f_rec["frame_number"] + 15,
            "timestamp": f_rec["timestamp"],
            "duration_seconds": 15.0,
            "bbox": [100, 150, 250, 400],
            "confidence": 0.92,
            "violation_type": "no-helmet",
            "source": "compliance_auditor",
            "ppe_type": "helmet"
        }
        
        supabase.table("violation_tracking").insert({
            "id": v_id,
            "video_id": video2_id,
            "user_id": user_id,
            "violation_type": "No Helmet",
            "timestamp": f_rec["timestamp"],
            "confidence": 0.92,
            "frame_id": f_rec["id"],
            "worker_id": w_rec["id"],
            "metadata": meta_payload,
            "created_at": now.isoformat()
        }).execute()
        
        res = supabase.table("evidence_records").insert({
            "project_id": project_id,
            "user_id": user_id,
            "video_id": video2_id,
            "violation_id": v_id,
            "frame_id": f_rec["id"],
            "worker_id": w_rec["id"],
            "evidence_type": "video_violation",
            "frame_num": f_rec["frame_number"],
            "timestamp": f_rec["timestamp"],
            "detection_label": "No Helmet",
            "confidence": 0.92,
            "screenshot_url": f_rec["image_path"],
            "annotated_screenshot_url": f_rec["image_path"],
            "sop_section": "Standard PPE",
            "sop_excerpt": "Hard hats required in Sector B at all times.",
            "risk_reason": "Unprotected head near active loaders.",
            "risk_score": 85,
            "metadata": meta_payload,
            "created_at": now.isoformat()
        }).execute()
        if res.data:
            inserted_evidence.extend(res.data)

    glove_evidence = [e for e in inserted_evidence if "glove" in e.get("detection_label", "").lower()]
    helmet_evidence = [e for e in inserted_evidence if "helmet" in e.get("detection_label", "").lower()]
    zone_evidence = [e for e in inserted_evidence if "zone" in e.get("detection_label", "").lower() or "restricted" in e.get("detection_label", "").lower()]
    
    glove_ev = glove_evidence[0] if glove_evidence else (inserted_evidence[0] if inserted_evidence else None)
    helmet_ev = helmet_evidence[0] if helmet_evidence else (inserted_evidence[0] if inserted_evidence else None)
    zone_ev = zone_evidence[0] if zone_evidence else (inserted_evidence[0] if inserted_evidence else None)

    recommendations_list = []
    
    # Low Priority - Routine PPE
    rec_json_low = {
        "module_name": "PPE Basics",
        "training_title": "PPE Basics Refresher",
        "reasoning": "Standard yearly review.",
        "recommended_action": "Annual refresher training.",
        "evidence": "No major violations.",
        "related_sop_rules": ["SOP-01"],
        "confidence": 0.99
    }
    recommendations_list.append({
        "project_id": project_id,
        "user_id": user_id,
        "priority": "Low",
        "human_readable_summary": "Routine PPE Refresher",
        "explanation": "Annual requirement.",
        "recommendation_json": rec_json_low,
        "worker_id": helmet_ev["worker_id"] if helmet_ev else None,
        "evidence_id": helmet_ev["id"] if helmet_ev else None
    })
    
    # High Priority - Head Protection
    rec_json_high = {
        "module_name": "Advanced Head Protection",
        "training_title": "Head Protection Compliance",
        "reasoning": "Recent violations in Sector B.",
        "recommended_action": "Targeted training for Sector B workers on hard hat requirements.",
        "evidence": "Multiple No Helmet events.",
        "related_sop_rules": ["SOP-02"],
        "confidence": 0.89
    }
    recommendations_list.append({
        "project_id": project_id,
        "user_id": user_id,
        "priority": "High",
        "human_readable_summary": "Head Protection Compliance",
        "explanation": "Targeted training for Sector B workers on hard hat requirements.",
        "recommendation_json": rec_json_high,
        "worker_id": helmet_ev["worker_id"] if helmet_ev else None,
        "evidence_id": helmet_ev["id"] if helmet_ev else None
    })
    
    # Critical Priority - Restricted Zone
    rec_json_crit = {
        "module_name": "Machinery Safety & Zones",
        "training_title": "Restricted Zone Awareness",
        "reasoning": "Critical safety breach detected near active machinery.",
        "recommended_action": "Immediate retraining required for Sector C personnel.",
        "evidence": "Zone entry at 5.1s.",
        "related_sop_rules": ["SOP-05", "SOP-08"],
        "confidence": 0.98
    }
    recommendations_list.append({
        "project_id": project_id,
        "user_id": user_id,
        "priority": "Critical",
        "human_readable_summary": "Restricted Zone Awareness",
        "explanation": "Immediate retraining required for Sector C personnel.",
        "recommendation_json": rec_json_crit,
        "worker_id": zone_ev["worker_id"] if zone_ev else None,
        "evidence_id": zone_ev["id"] if zone_ev else None
    })
    
    supabase.table("training_recommendations").insert(recommendations_list).execute()

    predictions_list = [
        {
            "project_id": project_id,
            "probability": 0.05,
            "prediction_details": {
                "type": "Minor Trip",
                "predicted_incident": "Minor Trip",
                "reasoning": "Clear walkways, standard operation.",
                "evidence": "No clutter detected.",
                "evidence_ids": [],
                "related_sop_rules": ["SOP-03: Housekeeping"],
                "confidence": 0.90
            }
        },
        {
            "project_id": project_id,
            "probability": 0.40,
            "prediction_details": {
                "type": "Struck by object",
                "predicted_incident": "Struck by object",
                "reasoning": "Missing hard hats in active assembly line increases risk of head injury.",
                "evidence": "PPE violations in Sector B.",
                "evidence_ids": [helmet_ev["id"]] if helmet_ev else [],
                "related_sop_rules": ["SOP-02: Head Protection"],
                "confidence": 0.82
            }
        },
        {
            "project_id": project_id,
            "probability": 0.85,
            "prediction_details": {
                "type": "Severe crush injury",
                "predicted_incident": "Severe crush injury",
                "reasoning": "Worker proximity to heavy machinery without safety barriers active.",
                "evidence": "Restricted zone breach in Sector C.",
                "evidence_ids": [zone_ev["id"]] if zone_ev else [],
                "related_sop_rules": ["SOP-08: Machinery Safety"],
                "confidence": 0.94
            }
        }
    ]
    supabase.table("incident_predictions").insert(predictions_list).execute()

    # Seed knowledge base to support RAG query validation
    try:
        sop_content = (
            "Standard Operating Procedure (SOP) for Workplace Safety:\n\n"
            "SOP-02: Head Protection. Hard hats must be worn by all personnel at all times in active areas of Sector B.\n"
            "SOP-05: Restricted Zones. Unauthorized entry into restricted active machinery zones in Sector C is strictly prohibited.\n"
            "SOP-08: Machinery Safety. Safety barriers must be active when operating heavy machinery in Sector C."
        )
        rag.embed_and_store(
            project_id=project_id,
            user_id=user_id,
            source_type="sop",
            source_id=str(uuid.uuid4()),
            content=sop_content,
            metadata={"title": "Demo SOP Document"}
        )
    except Exception as e:
        logger.error("Error seeding knowledge base: %s", e)

    return {"status": "success", "message": "Demo dataset loaded via backend.", "project_id": project_id}


@router.post("/reset")
def reset_demo_dataset(request: DemoLoadRequest):
    try:
        _clear_project_data(request.project_id, request.user_id)
        return {"status": "success", "message": "Demo data reset for current project."}
    except Exception as e:
        logger.error("Error resetting data: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-all")
def reset_all_user_data(request: ResetUserRequest):
    """Deletes all projects and associated data for a specific user."""
    try:
        # Fetch all project IDs for this user
        res = supabase.table("projects").select("id").eq("user_id", request.user_id).execute()
        project_ids = [p["id"] for p in (res.data or [])]
        
        for pid in project_ids:
            _clear_project_data(pid, request.user_id)
            
        # Finally delete projects themselves
        supabase.table("projects").delete().eq("user_id", request.user_id).execute()
        
        return {"status": "success", "message": f"All data for user {request.user_id} has been deleted."}
    except Exception as e:
        logger.error("Error resetting all user data: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
