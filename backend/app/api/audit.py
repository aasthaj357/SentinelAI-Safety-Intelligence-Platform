from fastapi import APIRouter, HTTPException
from app.core.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/logs")
def list_audit_logs(user_id: str = None, limit: int = 50):
    """Retrieve system security audit logs."""
    query = supabase.table("audit_logs").select("*").order("created_at", desc=True)
    if user_id:
        query = query.eq("user_id", user_id)
    res = query.limit(limit).execute()
    return res.data or []

@router.get("/traces")
def list_decision_traces(project_id: str, limit: int = 100):
    """Retrieve explainability decision reasoning traces for agents."""
    res = supabase.table("decision_traces").select("*").eq("project_id", project_id).order("created_at", desc=True).limit(limit).execute()
    return res.data or []


@router.get("/explain/{evidence_id}")
def explain_evidence(evidence_id: str):
    """
    Generate a rich, dynamic explanation for a specific evidence record.
    Pulls from evidence_records, violation_tracking, decision_traces,
    risk_assessments, and training_recommendations to build a complete
    explanation grounded in actual analysis results.
    """
    # 1. Fetch evidence record
    ev_res = supabase.table("evidence_records").select("*").eq("id", evidence_id).maybe_single().execute()
    evidence = getattr(ev_res, "data", None)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence record not found")

    project_id = evidence.get("project_id")
    worker_id_val = evidence.get("worker_id")
    violation_label = evidence.get("detection_label") or evidence.get("detection_label") or "unknown violation"
    timestamp_val = evidence.get("timestamp", 0.0)
    frame_num = evidence.get("frame_num")
    confidence = evidence.get("confidence", 0.0)
    sop_section = evidence.get("sop_section") or "Standard PPE Requirements"
    sop_excerpt = evidence.get("sop_excerpt") or "PPE compliance is mandatory in all active work zones."
    risk_reason = evidence.get("risk_reason") or f"Worker observed without required {violation_label}."
    metadata = evidence.get("metadata") or {}

    # 2. Resolve worker label
    worker_label = metadata.get("worker_id", "Unknown Worker")
    if not worker_label or worker_label == "Unknown Worker":
        if worker_id_val:
            w_res = supabase.table("workers").select("worker_label").eq("id", worker_id_val).maybe_single().execute()
            w_data = getattr(w_res, "data", None)
            if w_data:
                worker_label = w_data.get("worker_label", "Unknown Worker")

    # 3. Fetch matching decision trace for extra reasoning
    trace_reasoning = None
    if project_id:
        traces_res = supabase.table("decision_traces").select("*").eq("project_id", project_id).eq("step", "audit_frame_violation").order("created_at", desc=True).limit(200).execute()
        traces = traces_res.data or []
        for t in traces:
            ctx = t.get("context") or {}
            if (ctx.get("violation") == violation_label or ctx.get("violation", "").replace("no-", "") == violation_label.replace("no-", "")):
                # Check timestamp proximity
                t_ts = ctx.get("timestamp")
                if t_ts is not None and abs(float(t_ts) - float(timestamp_val)) < 2.0:
                    trace_reasoning = t.get("reasoning")
                    break
                elif t_ts is None:
                    trace_reasoning = t.get("reasoning")
                    break

    # 4. Fetch latest risk assessment for context
    risk_score = None
    risk_level = None
    risk_reasoning_text = None
    if project_id:
        risk_res = supabase.table("risk_assessments").select("score, details").eq("project_id", project_id).order("created_at", desc=True).limit(1).execute()
        if risk_res.data:
            risk_score = risk_res.data[0].get("score")
            risk_details = risk_res.data[0].get("details") or {}
            risk_level = risk_details.get("level")
            risk_reasoning_text = risk_details.get("reasoning", "")

    # 5. Fetch training recommendations triggered by this violation type
    training_recs = []
    if project_id:
        tr_res = supabase.table("training_recommendations").select("human_readable_summary, priority, explanation, recommendation_json").eq("project_id", project_id).order("created_at", desc=True).limit(10).execute()
        for tr in (tr_res.data or []):
            rec_json = tr.get("recommendation_json") or {}
            rec_title = rec_json.get("training_title") or tr.get("human_readable_summary") or "Safety Training"
            viol_clean = violation_label.lower().replace("no-", "").replace("no_", "").strip()
            # Check if this training is relevant to this violation type
            if (viol_clean in rec_title.lower() or
                any(kw in rec_title.lower() for kw in viol_clean.split())):
                training_recs.append({
                    "title": rec_title,
                    "priority": tr.get("priority", "Medium"),
                    "action": tr.get("explanation") or rec_json.get("recommended_action", "")
                })

    # 6. Build structured explanation
    ppe_type = violation_label.replace("no-", "").replace("no_", "").replace("missing ", "").replace("No ", "").strip()
    ppe_type_capitalized = ppe_type.replace("-", " ").title()

    # Build decision reasoning text
    if trace_reasoning:
        decision_context = trace_reasoning
    else:
        decision_context = (
            f"The AI compliance auditor detected that {worker_label} was observed without required "
            f"{ppe_type_capitalized} at timestamp {float(timestamp_val):.2f}s (Frame #{frame_num}). "
            f"Detection confidence: {float(confidence)*100:.0f}%. "
            f"This violates the safety requirement: '{sop_excerpt}'. "
            f"Risk assessment: {risk_reason}"
        )

    # Build citations
    citations = [
        f"SOP Reference: {sop_section}",
        f"SOP Requirement: {sop_excerpt}",
        f"Evidence: Frame #{frame_num} captured at {float(timestamp_val):.2f}s",
        f"Detection Confidence: {float(confidence)*100:.0f}%",
        f"Worker Identified: {worker_label}",
        f"Violation Type: {ppe_type_capitalized} Missing",
    ]
    if risk_score is not None:
        citations.append(f"Project Risk Score: {risk_score}/100 ({risk_level or 'N/A'})")
    if metadata.get("bbox"):
        bbox = metadata["bbox"]
        citations.append(f"Bounding Box: [{', '.join(str(int(v)) for v in bbox)}]")

    # Build AI analysis summary
    ai_summary_parts = [
        f"**Violation Detected**: {ppe_type_capitalized} not present on {worker_label}.",
        f"**When**: At {float(timestamp_val):.2f}s (Frame #{frame_num}) during video analysis.",
        f"**Confidence**: {float(confidence)*100:.0f}% — classified as a genuine violation after temporal consistency analysis.",
        f"**Risk Impact**: This violation contributes to the project's risk score of {risk_score}/100 ({risk_level or 'N/A'})." if risk_score else f"**Risk Impact**: {risk_reason}",
    ]

    if risk_reasoning_text:
        # Extract first 2 relevant lines from risk reasoning
        risk_lines = [l.strip() for l in risk_reasoning_text.split("\n") if ppe_type.lower() in l.lower()]
        if risk_lines:
            ai_summary_parts.append(f"**Risk Breakdown**: {risk_lines[0]}")

    if training_recs:
        tr = training_recs[0]
        ai_summary_parts.append(
            f"**Recommended Action** ({tr['priority']} Priority): {tr['action']}"
        )

    return {
        "evidence_id": evidence_id,
        "violation_type": violation_label,
        "ppe_type": ppe_type,
        "worker_label": worker_label,
        "timestamp": timestamp_val,
        "frame_num": frame_num,
        "confidence": confidence,
        "sop_section": sop_section,
        "sop_excerpt": sop_excerpt,
        "decision_context": decision_context,
        "ai_summary": "\n\n".join(ai_summary_parts),
        "citations": citations,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "training_recommendations": training_recs,
        "screenshot_url": evidence.get("annotated_screenshot_url") or evidence.get("screenshot_url"),
        "metadata": metadata,
    }
