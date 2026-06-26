import os
import uuid
import json
import time
import traceback
import logging
import shutil

logger = logging.getLogger(__name__)

cv2 = None
try:
    import cv2
    _CV2_AVAILABLE = True
except ImportError:
    logger.warning("opencv-python not installed. Video frame processing will be skipped.")
    _CV2_AVAILABLE = False

from app.core.supabase_client import supabase
from app.services.yolov8_service import get_yolo_service
from app.services.roboflow_service import get_roboflow_service
from app.services.sop_service import get_sop_service
from app.services.rag_service import get_rag_service

# Risk configuration
VIOLATION_WEIGHTS = {
    "helmet": (25, "Head injury / traumatic brain injury", "critical"),
    "gloves": (20, "Hand laceration / chemical burn", "high"),
    "goggles": (15, "Eye injury / chemical exposure", "high"),
    "vest": (12, "Struck-by / low visibility collision", "medium"),
    "mask": (10, "Respiratory / chemical exposure", "medium"),
    "shoes": (10, "Foot crush / slip injury", "medium"),
}

# --- IOA helper to associate PPE with worker bounding box ---
def _is_overlapping(w_box, p_box):
    """Calculate if ppe_box overlaps significantly with worker_box (Intersection over PPE Area)."""
    xA = max(w_box[0], p_box[0])
    yA = max(w_box[1], p_box[1])
    xB = min(w_box[2], p_box[2])
    yB = min(w_box[3], p_box[3])
    inter = max(0, xB - xA) * max(0, yB - yA)
    if inter == 0:
        return False
    p_area = (p_box[2] - p_box[0]) * (p_box[3] - p_box[1])
    if p_area == 0:
        return False
    return (inter / float(p_area)) >= 0.3

# --- Helper to calculate duration multiplier ---
def _duration_multiplier(duration_seconds):
    if not duration_seconds:
        return 1.0
    if duration_seconds >= 60:
        return 1.5
    if duration_seconds >= 30:
        return 1.3
    if duration_seconds >= 10:
        return 1.15
    if duration_seconds >= 3:
        return 1.05
    return 1.0

# --- Helper to calculate confidence multiplier ---
def _confidence_multiplier(confidence):
    if confidence >= 0.9:
        return 1.0
    if confidence >= 0.7:
        return 0.95
    if confidence >= 0.5:
        return 0.85
    return 0.75

from app.core.celery_app import celery_app

@celery_app.task(name="process_video_job")
def process_video_job(
    job_id: str,
    video_id: str,
    project_id: str,
    file_url: str,
    user_id: str = None,
    start_frame: int = 1,
    worker_state: dict = None,
    violations_state: list = None
):
    # Temp folders for frame processing
    temp_dir = f"tmp/frames_{video_id}"
    local_video_path = f"tmp/video_{video_id}.mp4"
    
    agents = {
        "frame_extraction": {"status": "waiting", "name": "Frame Extraction Agent", "output": None, "error": None},
        "object_detection": {"status": "waiting", "name": "Object Detection Agent", "output": None, "error": None},
        "person_tracking": {"status": "waiting", "name": "Person Tracking Agent", "output": None, "error": None},
        "ppe_association": {"status": "waiting", "name": "PPE Association Agent", "output": None, "error": None},
        "observation": {"status": "waiting", "name": "Observation Agent", "output": None, "error": None},
        "sop_parsing": {"status": "waiting", "name": "SOP Parsing Agent", "output": None, "error": None},
        "compliance_auditor": {"status": "waiting", "name": "Compliance Auditor Agent", "output": None, "error": None},
        "evidence_builder": {"status": "waiting", "name": "Evidence Builder Agent", "output": None, "error": None},
        "annotation": {"status": "waiting", "name": "Annotation Agent", "output": None, "error": None},
        "risk_assessment": {"status": "waiting", "name": "Risk Assessment Agent", "output": None, "error": None},
        "incident_prediction": {"status": "waiting", "name": "Incident Prediction Agent", "output": None, "error": None},
        "training_recommendation": {"status": "waiting", "name": "Training Recommendation Agent", "output": None, "error": None}
    }

    def update_agent_status(key, status, output=None, error=None):
        agents[key]["status"] = status
        agents[key]["output"] = output
        agents[key]["error"] = error
        agents[key]["updated_at"] = time.time()
        supabase.table("analysis_jobs").update({"result": {"agents": agents}}).eq("id", job_id).execute()
        
        # Log to RAG
        rag = get_rag_service()
        log_content = f"Agent {agents[key]['name']}: {status.upper()}"
        if error:
            log_content += f" - Error: {error}"
        elif output:
            log_content += f" - Output details processed successfully."
        try:
            rag.embed_and_store(
                project_id=project_id,
                user_id=user_id,
                source_type=key.split("_")[0],
                source_id=str(uuid.uuid4()),
                content=log_content
            )
        except Exception as e:
            logger.warning(f"RAG logging failed for agent {key}: {e}")

    is_resume = False
    try:
        job_res = supabase.table("analysis_jobs").select("result").eq("id", job_id).maybe_single().execute()
        job_data = getattr(job_res, "data", None)
        if job_data and job_data.get("result") and "agents" in job_data["result"]:
            existing_agents = job_data["result"]["agents"]
            if existing_agents.get("risk_assessment", {}).get("status") == "completed":
                is_resume = True
                for k, v in existing_agents.items():
                    if k in agents:
                        agents[k] = v
                logger.info(f"Resuming job {job_id} from risk_assessment checkpoint. Skipping steps 2-11.")
    except Exception as e:
        logger.warning(f"Could not load existing agent statuses: {e}")

    try:
        # Mark job as processing
        supabase.table("analysis_jobs").update({"status": "processing"}).eq("id", job_id).execute()
        
        if is_resume:
            logger.info("Running resumed pipeline execution for steps 12 and 13")
            annotated_evidence_list = agents["annotation"].get("output") or []
            
            # -------------------------------------------------------------
            # STEP 12: Incident Prediction Agent
            # -------------------------------------------------------------
            update_agent_status("incident_prediction", "running")
            
            predictions = []
            glove_viols = [ev for ev in annotated_evidence_list if "glove" in ev["violation"]]
            if glove_viols:
                prob = min(0.95, 0.60 + len(glove_viols)*0.08)
                predictions.append({
                    "type": "Hand Laceration or Chemical Burn",
                    "predicted_incident": "Hand Laceration or Chemical Burn",
                    "probability": round(prob, 2),
                    "reasoning": f"Missing gloves detected in {len(glove_viols)} frame(s). Worker hands unprotected.",
                    "evidence": f"Missing gloves detected in {len(glove_viols)} frame(s).",
                    "evidence_ids": [ev["evidence_id"] for ev in glove_viols]
                })
                
            helmet_viols = [ev for ev in annotated_evidence_list if "helmet" in ev["violation"] or "hardhat" in ev["violation"]]
            if helmet_viols:
                prob = min(0.97, 0.65 + len(helmet_viols)*0.08)
                predictions.append({
                    "type": "Traumatic Head Injury (TBI or skull fracture)",
                    "predicted_incident": "Traumatic Head Injury (TBI or skull fracture)",
                    "probability": round(prob, 2),
                    "reasoning": f"Worker head unprotected in {len(helmet_viols)} frame(s) with falling hazard present.",
                    "evidence": f"Unprotected head detected in {len(helmet_viols)} frame(s).",
                    "evidence_ids": [ev["evidence_id"] for ev in helmet_viols]
                })
                
            goggle_viols = [ev for ev in annotated_evidence_list if "goggle" in ev["violation"] or "glass" in ev["violation"]]
            if goggle_viols:
                prob = min(0.90, 0.55 + len(goggle_viols)*0.08)
                predictions.append({
                    "type": "Eye Injury or Chemical Eye Exposure",
                    "predicted_incident": "Eye Injury or Chemical Eye Exposure",
                    "probability": round(prob, 2),
                    "reasoning": f"Worker eyes unprotected in {len(goggle_viols)} frame(s).",
                    "evidence": f"Unprotected eyes detected in {len(goggle_viols)} frame(s).",
                    "evidence_ids": [ev["evidence_id"] for ev in goggle_viols]
                })
                
            for pred in predictions:
                supabase.table("incident_predictions").insert({
                    "project_id": project_id,
                    "prediction_details": pred,
                    "probability": pred["probability"]
                }).execute()
                
            update_agent_status("incident_prediction", "completed", output=predictions)

            # -------------------------------------------------------------
            # STEP 13: Training Recommendation Agent
            # -------------------------------------------------------------
            update_agent_status("training_recommendation", "running")
            
            training_recs = []
            if glove_viols:
                rec_json = {
                    "module_name": "Hand Protection Training",
                    "training_title": "Hand Protection Training",
                    "reasoning": "Conduct gloves selection and safety toolbox talk.",
                    "recommended_action": "Conduct gloves selection and safety toolbox talk.",
                    "priority": "High",
                    "evidence": f"Missing gloves @ {float(glove_viols[0].get('timestamp', 0)):.1f}s",
                    "evidence_ids": [ev["evidence_id"] for ev in glove_viols]
                }
                rec_res = supabase.table("training_recommendations").insert({
                    "project_id": project_id,
                    "user_id": user_id,
                    "priority": "High",
                    "recommendation_json": rec_json,
                    "human_readable_summary": "Hand Protection Training",
                    "explanation": rec_json["recommended_action"],
                    "worker_id": glove_viols[0]["worker_id"],
                    "evidence_id": glove_viols[0]["evidence_id"]
                }).execute()
                if rec_res.data:
                    training_recs.append(rec_res.data[0])
                    
            if helmet_viols:
                rec_json = {
                    "module_name": "Head Protection Training",
                    "training_title": "Head Protection Training",
                    "reasoning": "Conduct head trauma risks and helmet wearing compliance talk.",
                    "recommended_action": "Conduct head trauma risks and helmet wearing compliance talk.",
                    "priority": "Critical",
                    "evidence": f"Missing helmet @ {float(helmet_viols[0].get('timestamp', 0)):.1f}s",
                    "evidence_ids": [ev["evidence_id"] for ev in helmet_viols]
                }
                rec_res = supabase.table("training_recommendations").insert({
                    "project_id": project_id,
                    "user_id": user_id,
                    "priority": "Critical",
                    "recommendation_json": rec_json,
                    "human_readable_summary": "Head Protection Training",
                    "explanation": rec_json["recommended_action"],
                    "worker_id": helmet_viols[0]["worker_id"],
                    "evidence_id": helmet_viols[0]["evidence_id"]
                }).execute()
                if rec_res.data:
                    training_recs.append(rec_res.data[0])
                    
            if goggle_viols:
                rec_json = {
                    "module_name": "Eye Protection Training",
                    "training_title": "Eye Protection Training",
                    "reasoning": "Safety eyewear selection, compliance, and emergency eyewash stations.",
                    "recommended_action": "Safety eyewear selection, compliance, and emergency eyewash stations.",
                    "priority": "High",
                    "evidence": f"Missing goggles @ {float(goggle_viols[0].get('timestamp', 0)):.1f}s",
                    "evidence_ids": [ev["evidence_id"] for ev in goggle_viols]
                }
                rec_res = supabase.table("training_recommendations").insert({
                    "project_id": project_id,
                    "user_id": user_id,
                    "priority": "High",
                    "recommendation_json": rec_json,
                    "human_readable_summary": "Eye Protection Training",
                    "explanation": rec_json["recommended_action"],
                    "worker_id": goggle_viols[0]["worker_id"],
                    "evidence_id": goggle_viols[0]["evidence_id"]
                }).execute()
                if rec_res.data:
                    training_recs.append(rec_res.data[0])
                    
            update_agent_status("training_recommendation", "completed", output=training_recs)

            # Update the overall analysis job status to completed
            supabase.table("analysis_jobs").update({
                "status": "completed",
                "result": {"agents": agents}
            }).eq("id", job_id).execute()

            # Update the video upload status to analyzed
            supabase.table("video_uploads").update({
                "status": "analyzed"
            }).eq("id", video_id).execute()
            
            return

        os.makedirs("tmp", exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)

        # Download raw video
        storage_path = file_url
        if file_url.startswith("http"):
            for marker in ["/object/public/videos/", "/object/sign/videos/", "/videos/"]:
                if marker in file_url:
                    storage_path = file_url.split(marker, 1)[1]
                    break
        res = supabase.storage.from_("videos").download(storage_path)
        with open(local_video_path, "wb") as f:
            f.write(res)

        # -------------------------------------------------------------
        # STEP 2: Frame Extraction Agent
        # -------------------------------------------------------------
        update_agent_status("frame_extraction", "running")
        if not _CV2_AVAILABLE:
            raise ValueError("OpenCV is not available. Cannot extract video frames.")
        
        cap = cv2.VideoCapture(local_video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_interval = max(1, int(fps * 0.5)) # Every 0.5 seconds
        
        extracted_frames = []
        frame_num = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frame_num += 1
            
            if frame_num % frame_interval == 0:
                if frame_num < start_frame:
                    continue
                timestamp = round(frame_num / fps, 2)
                local_frame_path = f"{temp_dir}/frame_{frame_num}.jpg"
                cv2.imwrite(local_frame_path, frame)
                
                # Upload frame image to annotated-videos bucket
                success, buffer = cv2.imencode(".jpg", frame)
                if success:
                    storage_filename = f"{project_id}/{video_id}/frame_{frame_num}.jpg"
                    supabase.storage.from_("annotated-videos").upload(
                        storage_filename, buffer.tobytes(), {"content-type": "image/jpeg", "upsert": "true"}
                    )
                    image_path = supabase.storage.from_("annotated-videos").get_public_url(storage_filename)
                else:
                    image_path = local_frame_path
                
                # Persist to public.frames table
                frame_res = supabase.table("frames").insert({
                    "video_id": video_id,
                    "frame_number": frame_num,
                    "timestamp": timestamp,
                    "image_path": image_path
                }).execute()
                
                if frame_res.data:
                    frame_id = frame_res.data[0]["id"]
                    extracted_frames.append({
                        "frame_id": frame_id,
                        "frame_number": frame_num,
                        "timestamp": timestamp,
                        "image_path": image_path,
                        "local_path": local_frame_path
                    })
        cap.release()
        
        if not extracted_frames:
            raise ValueError("No frames extracted from the video.")
            
        update_agent_status("frame_extraction", "completed", output=extracted_frames)

        # -------------------------------------------------------------
        # STEP 3: Object Detection Agent (YOLO)
        # -------------------------------------------------------------
        update_agent_status("object_detection", "running")
        yolo_service = get_yolo_service()
        roboflow_service = get_roboflow_service()
        
        all_detections = []
        for frm in extracted_frames:
            frame_img = cv2.imread(frm["local_path"])
            if frame_img is None:
                continue
            
            # Run YOLOv8 for COCO classes (e.g., person, car, etc.)
            yolo_res = yolo_service.analyze_frame(frame_img, frm["frame_number"])
            
            # Run Roboflow for PPE classes (helmet, gloves, goggles, mask, vest, shoes)
            robo_res = roboflow_service.detect_ppe(frame_img, frm["frame_number"])
            robo_dets = robo_res.get("detections", [])
            robo_viols = robo_res.get("violations", [])
            
            # Consolidate all detections in this frame
            consolidated_dets = []
            for d in yolo_res:
                consolidated_dets.append({"class_name": d["class_name"], "confidence": d["confidence"], "bbox": d["bbox"]})
            for d in robo_dets:
                # Filter out raw violation labels from detections, keep only actual items
                if not any(d["class_name"].startswith(p) for p in ("no-", "no_")) and "missing" not in d["class_name"]:
                    consolidated_dets.append({"class_name": d["class_name"], "confidence": d["confidence"], "bbox": d["bbox"]})
            for v in robo_viols:
                consolidated_dets.append({"class_name": v["violation_type"], "confidence": v["confidence"], "bbox": v["bbox"]})
            
            # Save detections to public.detections table
            for det in consolidated_dets:
                det_res = supabase.table("detections").insert({
                    "frame_id": frm["frame_id"],
                    "class_name": det["class_name"],
                    "confidence": det["confidence"],
                    "bbox": det["bbox"]
                }).execute()
                
                if det_res.data:
                    all_detections.append({
                        "detection_id": det_res.data[0]["id"],
                        "frame_id": frm["frame_id"],
                        "frame_number": frm["frame_number"],
                        "timestamp": frm["timestamp"],
                        "class_name": det["class_name"],
                        "confidence": det["confidence"],
                        "bbox": det["bbox"],
                        "local_path": frm["local_path"]
                    })
        
        update_agent_status("object_detection", "completed", output=all_detections)

        # -------------------------------------------------------------
        # STEP 4: Person Tracking Agent
        # -------------------------------------------------------------
        update_agent_status("person_tracking", "running")
        
        # IoU-based tracking with max-age pruning and centroid fallback
        worker_ids_map = worker_state or {} # track_id -> worker_uuid
        worker_labels_map = {} # track_id -> worker_label
        next_worker_idx = 1
        
        # Group detections by frame
        detections_by_frame = {}
        for d in all_detections:
            f_num = d["frame_number"]
            if f_num not in detections_by_frame:
                detections_by_frame[f_num] = []
            detections_by_frame[f_num].append(d)
            
        workers_list = []
        last_frame_workers = {} # track_id -> last_bbox
        track_last_seen = {}  # track_id -> last frame_number seen (for max-age pruning)
        TRACK_MAX_AGE = 8  # frames — tracks not seen for >8 frames are removed
        IOU_MATCH_THRESHOLD = 0.4  # raised from 0.3 to reduce false new-identity creation
        CENTROID_FALLBACK_PX = 120  # px — if centroid within range and IoU=0, match anyway
        
        def _centroid(bbox):
            return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)
        
        def _centroid_dist(a, b):
            return ((a[0]-b[0])**2 + (a[1]-b[1])**2) ** 0.5
        
        sorted_frame_nums = sorted(detections_by_frame.keys())
        
        for f_num in sorted_frame_nums:
            # Prune stale tracks before processing this frame
            stale_tids = [tid for tid, last_fn in track_last_seen.items() if (f_num - last_fn) > TRACK_MAX_AGE]
            for stid in stale_tids:
                last_frame_workers.pop(stid, None)
                track_last_seen.pop(stid, None)
            
            frame_dets = detections_by_frame[f_num]
            persons = [d for d in frame_dets if d["class_name"].lower() == "person"]
            
            for p in persons:
                # Find matching track using IoU, then centroid fallback
                best_track_id = None
                best_iou = 0.0
                best_centroid_dist = float('inf')
                p_bbox = p["bbox"]
                p_centroid = _centroid(p_bbox)
                
                for tid, prev_bbox in last_frame_workers.items():
                    # Calculate IoU
                    xA = max(p_bbox[0], prev_bbox[0])
                    yA = max(p_bbox[1], prev_bbox[1])
                    xB = min(p_bbox[2], prev_bbox[2])
                    yB = min(p_bbox[3], prev_bbox[3])
                    inter = max(0, xB - xA) * max(0, yB - yA)
                    areaA = (p_bbox[2] - p_bbox[0]) * (p_bbox[3] - p_bbox[1])
                    areaB = (prev_bbox[2] - prev_bbox[0]) * (prev_bbox[3] - prev_bbox[1])
                    iou = inter / float(areaA + areaB - inter) if (areaA + areaB - inter) > 0 else 0.0
                    
                    if iou > best_iou and iou >= IOU_MATCH_THRESHOLD:
                        best_iou = iou
                        best_track_id = tid
                    elif iou < IOU_MATCH_THRESHOLD:
                        # Centroid fallback: match if close enough even with low IoU
                        prev_centroid = _centroid(prev_bbox)
                        cdist = _centroid_dist(p_centroid, prev_centroid)
                        if cdist < CENTROID_FALLBACK_PX and cdist < best_centroid_dist:
                            best_centroid_dist = cdist
                            if best_iou == 0.0:  # only use centroid if no IoU match found
                                best_track_id = tid
                        
                if best_track_id is not None:
                    # Keep same track ID
                    track_id = best_track_id
                    last_frame_workers[track_id] = p_bbox
                    track_last_seen[track_id] = f_num
                else:
                    # Assign a new track ID
                    track_id = next_worker_idx
                    next_worker_idx += 1
                    last_frame_workers[track_id] = p_bbox
                    track_last_seen[track_id] = f_num
                    
                # Create/Update worker in database
                if track_id not in worker_ids_map:
                    worker_label = f"Worker_{track_id}"
                    worker_res = supabase.table("workers").insert({
                        "video_id": video_id,
                        "worker_label": worker_label,
                        "track_id": track_id,
                        "start_frame": f_num,
                        "end_frame": f_num
                    }).execute()
                    if worker_res.data:
                        worker_ids_map[track_id] = worker_res.data[0]["id"]
                        worker_labels_map[track_id] = worker_label
                        workers_list.append(worker_res.data[0])
                else:
                    # Update end_frame
                    supabase.table("workers").update({"end_frame": f_num}).eq("id", worker_ids_map[track_id]).execute()
                    for wk in workers_list:
                        if wk["id"] == worker_ids_map[track_id]:
                            wk["end_frame"] = f_num
                            
                # Associate the worker_id to this person detection
                worker_uuid = worker_ids_map[track_id]
                p["worker_id"] = worker_uuid
                p["worker_label"] = worker_labels_map[track_id]
                supabase.table("detections").update({"worker_id": worker_uuid, "track_id": track_id}).eq("id", p["detection_id"]).execute()
                
                # Also associate this worker_id with any overlapping non-person detections in the same frame
                for d in frame_dets:
                    if d["class_name"].lower() != "person" and _is_overlapping(p_bbox, d["bbox"]):
                        d["worker_id"] = worker_uuid
                        d["worker_label"] = worker_labels_map[track_id]
                        supabase.table("detections").update({"worker_id": worker_uuid, "track_id": track_id}).eq("id", d["detection_id"]).execute()

        # Handle fallback for frames where no "person" bbox was detected but PPE violations exist
        # Map those violations to a default worker W01 or closest worker
        default_worker_id = workers_list[0]["id"] if workers_list else None
        if not default_worker_id:
            # Create a default worker W01
            w_res = supabase.table("workers").insert({
                "video_id": video_id,
                "worker_label": "Worker_1",
                "track_id": 1,
                "start_frame": 1,
                "end_frame": 300
            }).execute()
            if w_res.data:
                default_worker_id = w_res.data[0]["id"]
                workers_list.append(w_res.data[0])
                worker_ids_map[1] = default_worker_id
                worker_labels_map[1] = "Worker_1"
                
        for d in all_detections:
            if not d.get("worker_id"):
                d["worker_id"] = default_worker_id
                d["worker_label"] = "Worker_1"
                supabase.table("detections").update({"worker_id": default_worker_id, "track_id": 1}).eq("id", d["detection_id"]).execute()

        update_agent_status("person_tracking", "completed", output=workers_list)

        # -------------------------------------------------------------
        # STEP 5: PPE Association Agent
        # -------------------------------------------------------------
        update_agent_status("ppe_association", "running")
        
        from collections import defaultdict
        
        # 1. Map worker to their chronological frame list and dets in each frame
        worker_frames = defaultdict(list)  # wid -> list of frame dicts: {"fid", "frame_number", "timestamp"}
        worker_frame_dets = defaultdict(lambda: defaultdict(list)) # wid -> fid -> list of dets
        
        for d in all_detections:
            wid = d.get("worker_id")
            fid = d.get("frame_id")
            if not wid or not fid:
                continue
            worker_frame_dets[wid][fid].append(d)
            
        for wid, fid_dets in worker_frame_dets.items():
            # Gather unique frames for this worker
            unique_frames = []
            seen_fids = set()
            for fid, dets in fid_dets.items():
                if fid not in seen_fids:
                    unique_frames.append({
                        "fid": fid,
                        "frame_number": dets[0]["frame_number"],
                        "timestamp": dets[0]["timestamp"]
                    })
                    seen_fids.add(fid)
            # Sort chronologically by frame number
            unique_frames.sort(key=lambda x: x["frame_number"])
            worker_frames[wid] = unique_frames
            
        # Define canonical PPE checks with comprehensive Roboflow label variants
        # Uses substring matching (any(keyword in cname)) — do NOT use exact set membership
        PPE_KEYWORDS = {
            "helmet": ["helmet", "hardhat", "hard-hat", "hard_hat", "safety-helmet", "safety helmet"],
            "gloves": ["glove", "gloves", "safety-gloves", "safety gloves", "hand protection"],
            "goggles": [
                "goggle", "goggles", "glasses", "safety-glasses", "safety glasses",
                "safety-goggles", "eye protection", "eye-protection", "eyewear",
                "face shield", "face-shield",
            ],
            "mask": [
                "mask", "face-mask", "face mask", "respirator", "n95",
                "dust mask", "surgical mask", "respiratory",
            ],
            "vest": [
                "vest", "safety-vest", "safety vest", "hi-vis", "high-vis",
                "high visibility", "high-visibility", "reflective", "hivis",
            ],
            "shoes": [
                "shoe", "shoes", "boot", "boots", "safety-shoe", "safety shoe",
                "safety-boot", "safety boot", "safety-boots", "safety boots",
                "steel-toe", "steel toe", "footwear", "foot protection",
            ],
        }
        
        def _ppe_positive_match(cname: str, ppe_type: str) -> bool:
            """Return True if class name positively indicates the PPE is present."""
            keywords = PPE_KEYWORDS.get(ppe_type, [])
            return any(kw in cname for kw in keywords)
        
        def _ppe_negative_match(cname: str, ppe_type: str) -> bool:
            """Return True if class name indicates absence of this PPE type."""
            # Must have a negation prefix
            has_neg = (
                cname.startswith("no-") or cname.startswith("no_") or
                cname.startswith("without-") or cname.startswith("without_") or
                "missing" in cname or "no " in cname or "without " in cname
            )
            if not has_neg:
                return False
            # Strip negation prefixes to get the bare item name
            bare = cname
            for prefix in ("no-", "no_", "without-", "without_", "no ", "without "):
                bare = bare.replace(prefix, " ")
            bare = bare.replace("missing", "").strip()
            keywords = PPE_KEYWORDS.get(ppe_type, [])
            return any(kw in bare for kw in keywords)
        
        # worker_id -> ppe_type -> dict of fid -> bool
        worker_ppe_states = defaultdict(lambda: defaultdict(dict))
        
        for wid, frames_seq in worker_frames.items():
            N = len(frames_seq)
            if N == 0:
                continue
                
            # Run state-carrying temporal tracker for each PPE type
            for ppe_type in PPE_KEYWORDS.keys():
                timeline_states = [None] * N
                
                # Forward Pass
                for t in range(N):
                    fid = frames_seq[t]["fid"]
                    dets = worker_frame_dets[wid][fid]
                    
                    # Find highest confidence positive detection using substring matching
                    max_pos_conf = 0.0
                    for d in dets:
                        cname = d["class_name"].lower().replace("_", "-")
                        conf = d["confidence"]
                        # Only positive: class must NOT start with negation prefix
                        is_neg = (
                            cname.startswith("no-") or cname.startswith("no_") or
                            cname.startswith("without") or "missing" in cname
                        )
                        if not is_neg and _ppe_positive_match(cname, ppe_type):
                            if conf > max_pos_conf:
                                max_pos_conf = conf
                                
                    # Find highest confidence negative detection (violation)
                    max_neg_conf = 0.0
                    for d in dets:
                        cname = d["class_name"].lower().replace("_", "-")
                        conf = d["confidence"]
                        if _ppe_negative_match(cname, ppe_type):
                            if conf > max_neg_conf:
                                max_neg_conf = conf
                                    
                    # Resolve state based on relative confidence
                    pos_valid = max_pos_conf >= 0.45
                    neg_valid = max_neg_conf >= 0.45
                    
                    # Check if they were previously compliant in the sequence
                    was_compliant = any(timeline_states[i] is True for i in range(t))
                    
                    if pos_valid and neg_valid:
                        # Conflict: both detected. Higher confidence wins.
                        if max_pos_conf > max_neg_conf:
                            timeline_states[t] = True
                        else:
                            # If they were previously compliant, require high conf (>=0.80) to override
                            if was_compliant and max_neg_conf < 0.80:
                                timeline_states[t] = True
                            else:
                                timeline_states[t] = False
                    elif pos_valid:
                        timeline_states[t] = True
                    elif neg_valid:
                        # If they were previously compliant, require high conf (>=0.80) to override
                        if was_compliant and max_neg_conf < 0.80:
                            timeline_states[t] = True
                        else:
                            timeline_states[t] = False
                    else:
                        # No detection — carry forward previous state
                        if t > 0:
                            timeline_states[t] = timeline_states[t-1]
                            
                # Backward Pass: fill leading Nones from first known state
                for t in range(N - 1, -1, -1):
                    if timeline_states[t] is None:
                        if t < N - 1 and timeline_states[t+1] is not None:
                            timeline_states[t] = timeline_states[t+1]
                            
                # Compliance smoothing: if a worker is EVER detected compliant (True),
                # treat them as compliant throughout (handles occlusion / brief turn-away).
                # This prevents incorrectly flagging a worker who momentarily leaves
                # frame as non-compliant.
                if any(val is True for val in timeline_states):
                    timeline_states = [True] * N
                            
                # Save finalized states (None -> False = undetected)
                for t in range(N):
                    fid = frames_seq[t]["fid"]
                    val = timeline_states[t]
                    if val is None:
                        val = False
                    worker_ppe_states[wid][ppe_type][fid] = val
                    
        # Save all smoothed associations to the database
        ppe_associations = []
        for wid, frames_seq in worker_frames.items():
            for f_info in frames_seq:
                fid = f_info["fid"]
                ts = f_info["timestamp"]
                
                helmet_val = worker_ppe_states[wid]["helmet"].get(fid, False)
                gloves_val = worker_ppe_states[wid]["gloves"].get(fid, False)
                goggles_val = worker_ppe_states[wid]["goggles"].get(fid, False)
                mask_val = worker_ppe_states[wid]["mask"].get(fid, False)
                vest_val = worker_ppe_states[wid]["vest"].get(fid, False)
                shoes_val = worker_ppe_states[wid]["shoes"].get(fid, False)
                
                assoc_res = supabase.table("ppe_associations").insert({
                    "worker_id": wid,
                    "frame_id": fid,
                    "timestamp": ts,
                    "helmet": helmet_val,
                    "gloves": gloves_val,
                    "goggles": goggles_val,
                    "mask": mask_val,
                    "vest": vest_val,
                    "shoes": shoes_val
                }).execute()
                
                if assoc_res.data:
                    ppe_associations.append(assoc_res.data[0])
                    
        update_agent_status("ppe_association", "completed", output=ppe_associations)

        # -------------------------------------------------------------
        # STEP 6: Observation Agent
        # -------------------------------------------------------------
        update_agent_status("observation", "running")
        
        observations = []
        for assoc in ppe_associations:
            wid = assoc["worker_id"]
            fid = assoc["frame_id"]
            ts = assoc["timestamp"]
            
            worker_lbl = next(w["worker_label"] for w in workers_list if w["id"] == wid)
            
            # Construct factual observations
            missing_items = []
            if not assoc["helmet"]: missing_items.append("helmet")
            if not assoc["gloves"]: missing_items.append("gloves")
            if not assoc["goggles"]: missing_items.append("goggles")
            if not assoc["mask"]: missing_items.append("mask")
            if not assoc["vest"]: missing_items.append("vest")
            if not assoc["shoes"]: missing_items.append("shoes")
            
            content = f"{worker_lbl} detected."
            if missing_items:
                for item in missing_items:
                    content += f" {item.capitalize()} missing."
            else:
                content += " All PPE present."
                
            obs_res = supabase.table("observations").insert({
                "frame_id": fid,
                "worker_id": wid,
                "content": content,
                "timestamp": ts
            }).execute()
            
            if obs_res.data:
                observations.append(obs_res.data[0])
                
        update_agent_status("observation", "completed", output=observations)

        # -------------------------------------------------------------
        # STEP 7: SOP Parsing Agent
        # -------------------------------------------------------------
        update_agent_status("sop_parsing", "running")
        
        sop_service = get_sop_service()
        sop_doc = sop_service.fetch_latest_sop_document(project_id)
        
        if sop_doc and sop_doc.get("sop_structure"):
            sop_rules = sop_doc["sop_structure"]
        else:
            # Use defaults
            sop_rules = {
                "ppe_requirements": ["helmet", "gloves", "goggles", "vest", "shoes"],
                "required_procedures": [],
                "forbidden_actions": []
            }
            
        update_agent_status("sop_parsing", "completed", output=sop_rules)

        # -------------------------------------------------------------
        # STEP 8: Compliance Auditor Agent
        # -------------------------------------------------------------
        update_agent_status("compliance_auditor", "running")
        
        sop_ppe_reqs = [p.lower() for p in sop_rules.get("ppe_requirements", [])]
        violations_list = violations_state or []
        
        for assoc in ppe_associations:
            wid = assoc["worker_id"]
            fid = assoc["frame_id"]
            ts = assoc["timestamp"]
            
            # Find the frame image path to assert existence
            frame_rec = next(f for f in extracted_frames if f["frame_id"] == fid)
            image_path = frame_rec.get("image_path")
            
            # STRICT NULL SAFETY ASSERTIONS
            if not fid or ts is None or not wid or not image_path:
                logger.warning(f"Auditor: Null assertion failed for frame {fid}, worker {wid}, skipping violation.")
                continue
                
            # Compare observed PPE with SOP rules
            for req in sop_ppe_reqs:
                # If PPE is required but observed as False, generate a violation
                # Note: assoc keys are lowercase PPE types (helmet, gloves, goggles, mask, vest, shoes)
                # We only flag a violation if the column explicitly exists AND is False
                # (not just absent from the row) to avoid false positives from DB schema gaps
                if req in assoc and assoc[req] is False:
                    violation_type = f"no-{req}"
                    
                    # Store to violation_tracking
                    viol_res = supabase.table("violation_tracking").insert({
                        "video_id": video_id,
                        "user_id": user_id,
                        "violation_type": violation_type,
                        "timestamp": ts,
                        "confidence": 0.85, # Standard auditor confidence
                        "frame_id": fid,
                        "worker_id": wid,
                        "metadata": {
                            "worker_id": next(w["worker_label"] for w in workers_list if w["id"] == wid),
                            "ppe_type": req,
                            "source": "compliance_auditor",
                            "duration_seconds": 0.5,
                            "frame_start": frame_rec["frame_number"],
                            "frame_end": frame_rec["frame_number"],
                            "frame_number": frame_rec["frame_number"],
                            "timestamp": ts,
                            "bbox": next((d["bbox"] for d in detections_by_frame[frame_rec["frame_number"]] if d["worker_id"] == wid and d["class_name"].lower() == "person"), [0, 0, 100, 100]),
                            "confidence": 0.85,
                            "violation_type": violation_type
                        }
                    }).execute()
                    
                    if viol_res.data:
                        violations_list.append({
                            "violation_id": viol_res.data[0]["id"],
                            "violation": violation_type,
                            "worker_id": wid,
                            "frame_id": fid,
                            "timestamp": ts,
                            "violated_rule": f"SOP mandates {req}",
                            "confidence": 0.85,
                            "bbox": next((d["bbox"] for d in detections_by_frame[frame_rec["frame_number"]] if d["worker_id"] == wid and d["class_name"].lower() == "person"), [0, 0, 100, 100]),
                            "image_path": image_path,
                            "local_path": frame_rec["local_path"],
                            "frame_number": frame_rec["frame_number"]
                        })
                        
                        # Log decision trace to public.decision_traces for explainability page matching
                        try:
                            supabase.table("decision_traces").insert({
                                "project_id": project_id,
                                "agent_id": "ComplianceAgent",
                                "step": "audit_frame_violation",
                                "reasoning": f"Mandatory safety item '{req}' was not detected in frame #{frame_rec['frame_number']} at {ts}s. Verified via SOP requirements.",
                                "context": {
                                    "frame_num": frame_rec["frame_number"],
                                    "timestamp": ts,
                                    "violation": violation_type,
                                    "citation": f"SOP Requirement: Mandatory {req}"
                                }
                            }).execute()
                        except Exception as trace_err:
                            logger.warning(f"Failed to log decision trace for violation: {trace_err}")
                        
        update_agent_status("compliance_auditor", "completed", output=violations_list)

        # -------------------------------------------------------------
        # STEP 9: Evidence Builder Agent
        # -------------------------------------------------------------
        update_agent_status("evidence_builder", "running")
        
        evidence_list = []
        for viol in violations_list:
            fid = viol["frame_id"]
            image_path = viol["image_path"]
            
            # If frame image path is missing, mark INVALID and skip
            if not image_path:
                logger.warning(f"EvidenceBuilder: Missing frame path for violation {viol['violation_id']}. Skipping.")
                continue
                
            # Assert no nulls or placeholders
            if viol["timestamp"] is None or viol["frame_number"] is None or not viol["violation"]:
                logger.warning("EvidenceBuilder: Assertions failed. Skipping.")
                continue
                
            worker_lbl = next(w["worker_label"] for w in workers_list if w["id"] == viol["worker_id"])
            risk_reason = f"Worker {worker_lbl} observed without required safety {viol['violation'].replace('no-', '')}."
            
            evidence_payload = {
                "project_id": project_id,
                "user_id": user_id,
                "video_id": video_id,
                "violation_id": viol["violation_id"],
                "frame_id": fid,
                "worker_id": viol["worker_id"],
                "evidence_type": "video_violation",
                "frame_num": viol["frame_number"],
                "timestamp": viol["timestamp"],
                "detection_label": viol["violation"],
                "confidence": viol["confidence"],
                "screenshot_url": image_path,
                "annotated_screenshot_url": image_path,
                "risk_reason": risk_reason,
                "metadata": {
                    "bbox": viol["bbox"],
                    "worker_id": worker_lbl,
                    "frame_start": viol["frame_number"],
                    "frame_end": viol["frame_number"],
                    "frame_number": viol["frame_number"],
                    "timestamp": viol["timestamp"],
                    "duration_seconds": 0.5,
                    "confidence": viol["confidence"],
                    "violation_type": viol["violation"]
                }
            }
            
            ev_res = supabase.table("evidence_records").insert(evidence_payload).execute()
            if ev_res.data:
                evidence_list.append({
                    "evidence_id": ev_res.data[0]["id"],
                    "frame_id": fid,
                    "violation_id": viol["violation_id"],
                    "worker_id": viol["worker_id"],
                    "worker_label": worker_lbl,
                    "violation": viol["violation"],
                    "frame_number": viol["frame_number"],
                    "timestamp": viol["timestamp"],
                    "bbox": viol["bbox"],
                    "confidence": viol["confidence"],
                    "screenshot_url": image_path,
                    "local_path": viol["local_path"]
                })
                
        update_agent_status("evidence_builder", "completed", output=evidence_list)

        # -------------------------------------------------------------
        # STEP 10: Annotation Agent
        # -------------------------------------------------------------
        update_agent_status("annotation", "running")
        
        annotated_evidence_list = []
        for ev in evidence_list:
            local_path = ev["local_path"]
            frame_img = cv2.imread(local_path)
            
            if frame_img is not None:
                x1, y1, x2, y2 = [int(v) for v in ev["bbox"]]
                # Draw red bounding box
                cv2.rectangle(frame_img, (x1, y1), (x2, y2), (0, 0, 255), 2)
                # Label MISSING HELMET etc.
                label_text = f"MISSING {ev['violation'].replace('no-', '').upper()}"
                cv2.putText(frame_img, label_text, (x1, max(y1-10, 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                
                # Save annotated image locally
                local_annotated_path = f"{temp_dir}/annotated_{ev['evidence_id']}.jpg"
                cv2.imwrite(local_annotated_path, frame_img)
                
                # Upload to Supabase Storage
                success, buffer = cv2.imencode(".jpg", frame_img)
                if success:
                    storage_filename = f"{project_id}/{video_id}/annotated_{ev['evidence_id']}.jpg"
                    supabase.storage.from_("annotated-videos").upload(
                        storage_filename, buffer.tobytes(), {"content-type": "image/jpeg", "upsert": "true"}
                    )
                    annotated_url = supabase.storage.from_("annotated-videos").get_public_url(storage_filename)
                else:
                    annotated_url = ev["screenshot_url"]
                    
                # Update evidence_records with annotated screenshot url
                supabase.table("evidence_records").update({
                    "annotated_screenshot_url": annotated_url
                }).eq("id", ev["evidence_id"]).execute()
                
                ev["annotated_screenshot_url"] = annotated_url
                annotated_evidence_list.append(ev)
                
        update_agent_status("annotation", "completed", output=annotated_evidence_list)

        # -------------------------------------------------------------
        # STEP 11: Risk Assessment Agent
        # -------------------------------------------------------------
        update_agent_status("risk_assessment", "running")
        
        # Group by worker and PPE type to get unique violations instead of summing every frame
        unique_violations = {}
        for ev in annotated_evidence_list:
            ppe_type = ev["violation"].replace("no-", "").replace("no_", "")
            worker_id = ev["worker_label"]
            key = (worker_id, ppe_type)
            
            if key not in unique_violations:
                unique_violations[key] = {
                    "ev": ev,
                    "count": 0,
                    "confidences": []
                }
            unique_violations[key]["count"] += 1
            unique_violations[key]["confidences"].append(ev["confidence"])
            
        total_risk_score = 0.0
        details = []
        for key, info in unique_violations.items():
            worker_id, ppe_type = key
            ev = info["ev"]
            count = info["count"]
            avg_conf = sum(info["confidences"]) / len(info["confidences"])
            
            base_weight, injury, severity = VIOLATION_WEIGHTS.get(ppe_type, (10, "General Injury", "medium"))
            
            # Duration is count * 0.5s per frame
            duration = count * 0.5
            dur_mult = _duration_multiplier(duration)
            conf_mult = _confidence_multiplier(avg_conf)
            
            adjusted_risk = base_weight * dur_mult * conf_mult
            total_risk_score += adjusted_risk
            
            details.append({
                "evidence_id": ev["evidence_id"],
                "worker_id": worker_id,
                "ppe": ppe_type,
                "injury": injury,
                "severity": severity,
                "adjusted_risk": round(adjusted_risk, 2)
            })
            
        final_risk_score = min(100.0, round(total_risk_score, 1))
        
        risk_level = "Low"
        if final_risk_score > 75:
            risk_level = "Critical"
        elif final_risk_score > 50:
            risk_level = "High"
        elif final_risk_score > 25:
            risk_level = "Medium"

        reasoning_lines = [
            f"Risk Score: {final_risk_score:.1f}/100 ({risk_level})",
            f"Formula: Σ(base_weight * dur_mult * conf_mult)",
            f"Total violations analyzed: {len(annotated_evidence_list)}",
        ]
        for entry in details[:12]:
            reasoning_lines.append(f"  • {entry['worker_id']} - {entry['ppe']}: {entry['injury']} [{entry['severity']}] (risk impact: +{entry['adjusted_risk']})")

        risk_details_payload = {
            "risk_breakdown": details,
            "formula": "Σ(base_weight * dur_mult * conf_mult)",
            "reasoning": "\n".join(reasoning_lines),
            "evidence": [f"{e['worker_id']} missing {e['ppe']} (Impact: +{e['adjusted_risk']})" for e in details[:6]],
            "confidence": 0.85,
            "level": risk_level
        }

        # Save to risk_assessments table
        risk_res = supabase.table("risk_assessments").insert({
            "project_id": project_id,
            "video_id": video_id,
            "user_id": user_id,
            "score": final_risk_score,
            "details": risk_details_payload
        }).execute()
        
        risk_id = risk_res.data[0]["id"] if risk_res.data else None
        
        risk_summary = {
            "risk_id": risk_id,
            "score": final_risk_score,
            "details": risk_details_payload
        }
        
        # Link evidence records to this risk assessment (best-effort; column may not exist)
        if risk_id:
            for ev in annotated_evidence_list:
                try:
                    supabase.table("evidence_records").update({
                        "risk_assessment_id": risk_id
                    }).eq("id", ev["evidence_id"]).execute()
                except Exception as _link_err:
                    logger.warning(f"Could not link evidence to risk assessment (column may not exist): {_link_err}")
                
        update_agent_status("risk_assessment", "completed", output=risk_summary)

        # Human-in-the-loop validation checkpoint
        from app.agents.orchestrator_agent import OrchestratorAgent
        orchestrator = OrchestratorAgent()
        checkpoint_payload = {
            "checkpoint_frame": max(f["frame_number"] for f in extracted_frames) if extracted_frames else 1,
            "tracked_workers": worker_ids_map,
            "cumulative_violations": violations_list
        }
        if orchestrator.check_approval_trigger(project_id, job_id, final_risk_score, user_id, checkpoint_payload):
            logger.info("Pipeline execution suspended due to critical incident risk threshold breach. Awaiting human approval.")
            return

        # -------------------------------------------------------------
        # STEP 12: Incident Prediction Agent
        # -------------------------------------------------------------
        update_agent_status("incident_prediction", "running")
        
        predictions = []
        # Hand injury prediction
        glove_viols = [ev for ev in annotated_evidence_list if "glove" in ev["violation"]]
        if glove_viols:
            prob = min(0.95, 0.60 + len(glove_viols)*0.08)
            predictions.append({
                "type": "Hand Laceration or Chemical Burn",
                "predicted_incident": "Hand Laceration or Chemical Burn",
                "probability": round(prob, 2),
                "reasoning": f"Missing gloves detected in {len(glove_viols)} frame(s). Worker hands unprotected.",
                "evidence": f"Missing gloves detected in {len(glove_viols)} frame(s).",
                "evidence_ids": [ev["evidence_id"] for ev in glove_viols]
            })
            
        # Traumatic head injury prediction
        helmet_viols = [ev for ev in annotated_evidence_list if "helmet" in ev["violation"] or "hardhat" in ev["violation"]]
        if helmet_viols:
            prob = min(0.97, 0.65 + len(helmet_viols)*0.08)
            predictions.append({
                "type": "Traumatic Head Injury (TBI or skull fracture)",
                "predicted_incident": "Traumatic Head Injury (TBI or skull fracture)",
                "probability": round(prob, 2),
                "reasoning": f"Worker head unprotected in {len(helmet_viols)} frame(s) with falling hazard present.",
                "evidence": f"Unprotected head detected in {len(helmet_viols)} frame(s).",
                "evidence_ids": [ev["evidence_id"] for ev in helmet_viols]
            })
            
        # Eye injury prediction
        goggle_viols = [ev for ev in annotated_evidence_list if "goggle" in ev["violation"] or "glass" in ev["violation"]]
        if goggle_viols:
            prob = min(0.90, 0.55 + len(goggle_viols)*0.08)
            predictions.append({
                "type": "Eye Injury or Chemical Eye Exposure",
                "predicted_incident": "Eye Injury or Chemical Eye Exposure",
                "probability": round(prob, 2),
                "reasoning": f"Worker eyes unprotected in {len(goggle_viols)} frame(s).",
                "evidence": f"Unprotected eyes detected in {len(goggle_viols)} frame(s).",
                "evidence_ids": [ev["evidence_id"] for ev in goggle_viols]
            })
            
        # Persist predictions to incident_predictions
        for pred in predictions:
            supabase.table("incident_predictions").insert({
                "project_id": project_id,
                "prediction_details": pred,
                "probability": pred["probability"]
            }).execute()
            
        update_agent_status("incident_prediction", "completed", output=predictions)

        # -------------------------------------------------------------
        # STEP 13: Training Recommendation Agent
        # -------------------------------------------------------------
        update_agent_status("training_recommendation", "running")
        
        training_recs = []
        # Missing gloves -> Hand Protection Training
        if glove_viols:
            rec_json = {
                "module_name": "Hand Protection Training",
                "training_title": "Hand Protection Training",
                "reasoning": "Conduct gloves selection and safety toolbox talk.",
                "recommended_action": "Conduct gloves selection and safety toolbox talk.",
                "priority": "High",
                "evidence": f"Missing gloves @ {float(glove_viols[0].get('timestamp', 0)):.1f}s",
                "evidence_ids": [ev["evidence_id"] for ev in glove_viols]
            }
            rec_res = supabase.table("training_recommendations").insert({
                "project_id": project_id,
                "user_id": user_id,
                "priority": "High",
                "recommendation_json": rec_json,
                "human_readable_summary": "Hand Protection Training",
                "explanation": rec_json["recommended_action"],
                "worker_id": glove_viols[0]["worker_id"],
                "evidence_id": glove_viols[0]["evidence_id"]
            }).execute()
            if rec_res.data:
                training_recs.append(rec_res.data[0])
                
        # Missing helmet -> Head Protection Training
        if helmet_viols:
            rec_json = {
                "module_name": "Head Protection Training",
                "training_title": "Head Protection Training",
                "reasoning": "Conduct head trauma risks and helmet wearing compliance talk.",
                "recommended_action": "Conduct head trauma risks and helmet wearing compliance talk.",
                "priority": "Critical",
                "evidence": f"Missing helmet @ {float(helmet_viols[0].get('timestamp', 0)):.1f}s",
                "evidence_ids": [ev["evidence_id"] for ev in helmet_viols]
            }
            rec_res = supabase.table("training_recommendations").insert({
                "project_id": project_id,
                "user_id": user_id,
                "priority": "Critical",
                "recommendation_json": rec_json,
                "human_readable_summary": "Head Protection Training",
                "explanation": rec_json["recommended_action"],
                "worker_id": helmet_viols[0]["worker_id"],
                "evidence_id": helmet_viols[0]["evidence_id"]
            }).execute()
            if rec_res.data:
                training_recs.append(rec_res.data[0])
                
        # Missing goggles -> Eye Protection Training
        if goggle_viols:
            rec_json = {
                "module_name": "Eye Protection Training",
                "training_title": "Eye Protection Training",
                "reasoning": "Safety eyewear selection, compliance, and emergency eyewash stations.",
                "recommended_action": "Safety eyewear selection, compliance, and emergency eyewash stations.",
                "priority": "High",
                "evidence": f"Missing goggles @ {float(goggle_viols[0].get('timestamp', 0)):.1f}s",
                "evidence_ids": [ev["evidence_id"] for ev in goggle_viols]
            }
            rec_res = supabase.table("training_recommendations").insert({
                "project_id": project_id,
                "user_id": user_id,
                "priority": "High",
                "recommendation_json": rec_json,
                "human_readable_summary": "Eye Protection Training",
                "explanation": rec_json["recommended_action"],
                "worker_id": goggle_viols[0]["worker_id"],
                "evidence_id": goggle_viols[0]["evidence_id"]
            }).execute()
            if rec_res.data:
                training_recs.append(rec_res.data[0])
                
        update_agent_status("training_recommendation", "completed", output=training_recs)

        # Update the overall analysis job status to completed
        supabase.table("analysis_jobs").update({
            "status": "completed",
            "result": {"agents": agents}
        }).eq("id", job_id).execute()

        # Update the video upload status to analyzed
        supabase.table("video_uploads").update({
            "status": "analyzed"
        }).eq("id", video_id).execute()
        
        # Clean up temp frame folder and local video file
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
            if os.path.exists(local_video_path):
                os.remove(local_video_path)
        except Exception as e:
            logger.warning(f"Error cleaning up temp files: {e}")

    except Exception as e:
        logger.error(f"Sequential agentic pipeline failed for job {job_id}: {e}")
        traceback.print_exc()
        
        # Mark active running agent as failed
        failed_agent = next((k for k, v in agents.items() if v["status"] == "running"), None)
        if failed_agent:
            update_agent_status(failed_agent, "failed", error=str(e))
            
        supabase.table("analysis_jobs").update({
            "status": "failed",
            "result": {"agents": agents, "error": str(e)}
        }).eq("id", job_id).execute()
        supabase.table("video_uploads").update({"status": "failed"}).eq("id", video_id).execute()
