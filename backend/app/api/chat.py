from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import json
from groq import Groq
from app.core.config import settings
from app.core.supabase_client import supabase
from app.services.rag_service import get_rag_service
from app.services.analytics_service import get_analytics_service

router = APIRouter()
rag = get_rag_service()
analytics = get_analytics_service()
client = Groq(api_key=settings.GROQ_API_KEY)


class ChatRequest(BaseModel):
    project_id: str
    user_id: str = "00000000-0000-4000-a000-000000000001"
    message: str
    history: List[dict] = []


def _video_ids(project_id, user_id):
    rows = supabase.table("video_uploads").select("id").eq("project_id", project_id).eq("user_id", user_id).execute()
    return [r["id"] for r in (rows.data or [])]


def _fetch_project_context(project_id, user_id):
    evidence = supabase.table("evidence_records").select("*").eq("project_id", project_id).eq("user_id", user_id).order("created_at", desc=True).limit(15).execute()
    risks = supabase.table("risk_assessments").select("*").eq("project_id", project_id).eq("user_id", user_id).order("created_at", desc=True).limit(5).execute()
    sops = supabase.table("sop_documents").select("id,title,sop_structure").eq("project_id", project_id).eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()

    predictions = supabase.table("incident_predictions").select("*").eq("project_id", project_id).order("created_at", desc=True).limit(10).execute()

    violations = []
    ids = _video_ids(project_id, user_id)
    if ids:
        vres = supabase.table("violation_tracking").select("*").in_("video_id", ids).eq("user_id", user_id).order("created_at", desc=True).limit(30).execute()
        violations = vres.data or []

    return {
        "evidence": evidence.data or [],
        "risks": risks.data or [],
        "sops": sops.data or [],
        "violations": violations,
        "predictions": predictions.data or [],
    }


def _rag_search(project_id, user_id, query):
    """Retrieve top KB matches for the query, including full evidence metadata."""
    kb_hits = rag.similarity_search(project_id, query, user_id=user_id, top_k=6)
    sources = []
    seen_ids = set()
    for hit in kb_hits:
        meta = hit.get("metadata") or {}
        eid = meta.get("evidence_id")
        if eid and eid not in seen_ids:
            rec = supabase.table("evidence_records").select("*").eq("id", eid).eq("user_id", user_id).maybe_single().execute()
            if getattr(rec, "data", None):
                sources.append(_format_source(len(sources)+1, rec.data, hit.get("score", 0.0)))
                seen_ids.add(eid)
        elif not eid:
            sources.append({
                "id": len(sources)+1,
                "type": "knowledge_base",
                "content": hit.get("content", ""),
                "metadata": meta,
                "relevance_score": hit.get("score", 0.0),
            })
    return sources


def _filter_evidence(evidence, query):
    words = [w for w in query.lower().split() if len(w) > 2]
    matched = [e for e in evidence if any(
        w in (str(e.get("detection_label","")) + str(e.get("sop_section","")) + str(e.get("sop_excerpt",""))).lower()
        for w in words
    )]
    return matched or evidence


def _format_source(idx, record, relevance=0.0):
    ts = float(record.get("timestamp") or 0)
    worker = (record.get("metadata") or {}).get("worker_id", "")
    dur = (record.get("metadata") or {}).get("duration_seconds")
    dur_str = f" Duration: {dur:.1f}s." if dur else ""
    conf = record.get("confidence")
    conf_str = f" Confidence: {conf:.0%}." if conf else ""
    return {
        "id": idx,
        "type": "evidence",
        "evidence_id": record.get("id"),
        "content": (
            f"[Frame {record.get('frame_num')} | {ts:.2f}s{dur_str}] "
            f"Violation: '{record.get('detection_label')}'{conf_str} "
            f"Worker: {worker or 'unknown'}. "
            f"SOP: {record.get('sop_section')} — {str(record.get('sop_excerpt',''))[:120]}. "
            f"Risk: {record.get('risk_reason','')}"
        ),
        "relevance_score": round(relevance, 3),
        "metadata": {
            "video_id": record.get("video_id"),
            "frame_num": record.get("frame_num"),
            "frame_start": (record.get("metadata") or {}).get("frame_start"),
            "frame_end": (record.get("metadata") or {}).get("frame_end"),
            "timestamp": record.get("timestamp"),
            "detection_label": record.get("detection_label"),
            "confidence": record.get("confidence"),
            "worker_id": worker,
            "duration_seconds": dur,
            "screenshot_url": record.get("screenshot_url"),
            "cropped_url": (record.get("metadata") or {}).get("cropped_url"),
            "sop_section": record.get("sop_section"),
            "sop_excerpt": record.get("sop_excerpt"),
            "risk_score": record.get("risk_score"),
            "risk_reason": record.get("risk_reason"),
            "bbox": (record.get("metadata") or {}).get("bbox"),
            "why_detected": (record.get("metadata") or {}).get("why_detected"),
            "how_detected": (record.get("metadata") or {}).get("how_detected"),
            "mitigation": (record.get("metadata") or {}).get("mitigation"),
            "undetermined": (record.get("metadata") or {}).get("undetermined") or False,
            "source": (record.get("metadata") or {}).get("source"),
        },
    }


def _build_reply(message, context, sources, kb_sources):
    report_requested = any(kw in message.lower() for kw in [
        "full report", "detailed report", "generate report", "complete analysis",
        "executive summary", "show all findings", "show everything"
    ])

    violations = context.get("violations", [])
    evidence = context.get("evidence", [])
    risks = context.get("risks", [])

    # Build citation block for grounding
    citation_lines = []
    all_sources = sources + [s for s in kb_sources if s not in sources]
    for s in all_sources[:8]:
        citation_lines.append(f"[{s['id']}] {s['content']}")

    citations_block = "\n".join(citation_lines) if citation_lines else "No retrieved evidence."

    safe_violations = [
        {
            "type": v.get("violation_type"),
            "timestamp": v.get("timestamp"),
            "confidence": v.get("confidence"),
            "worker_id": (v.get("metadata") or {}).get("worker_id"),
            "duration": (v.get("metadata") or {}).get("duration_seconds"),
            "frame_start": (v.get("metadata") or {}).get("frame_start"),
        }
        for v in violations[:15]
    ]

    if report_requested:
        system_prompt = (
            "You are an Executive Safety Manager Copilot. "
            "Generate a comprehensive Markdown report with sections: "
            "### Executive Summary, ### Key Findings, ### Violation Details, "
            "### Risk Assessment, ### Recommended Actions. "
            "Cite evidence by [id] where applicable. Never invent data."
        )
    else:
        system_prompt = (
            "You are a Safety Officer Copilot. Answer the specific question in 3-8 sentences. "
            "RULES: "
            "1. ALWAYS cite evidence by [id] when referencing specific violations. "
            "2. NEVER claim 'no violations' if violations or evidence exist in the context. "
            "3. Ground every claim in the provided evidence/violations. "
            "4. If asked about a specific violation type, search violations list and report accurately. "
            "5. Never fabricate violations; never deny violations that exist. "
            "6. If data is genuinely empty, say so explicitly."
        )

    user_prompt = f"""Question: {message}

RETRIEVED EVIDENCE (cite by [id]):
{citations_block}

VIOLATIONS DATABASE ({len(violations)} total):
{json.dumps(safe_violations)}

RISK ASSESSMENTS:
{json.dumps([{"score": r.get("score"), "level": (r.get("details") or {}).get("level", "unknown")} for r in risks[:3]])}

SOP STRUCTURE:
{json.dumps([(s.get("title"), (s.get("sop_structure") or {}).get("ppe_requirements", [])) for s in context.get("sops", [])])}

INCIDENT PREDICTIONS:
{json.dumps([{"incident": (p.get("prediction_details") or {}).get("predicted_incident"), "probability": p.get("probability")} for p in context.get("predictions", [])[:5]])}
"""

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model="llama-3.1-8b-instant",
            temperature=0.15,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error connecting to AI: {e}"


@router.post("", include_in_schema=False)
@router.post("/")
def chat_with_copilot(request: ChatRequest):
    if not request.project_id or not request.user_id:
        return {"status": "error", "reply": "No project or user found.", "sources": []}

    context = _fetch_project_context(request.project_id, request.user_id)

    # Direct DB evidence filtered by query
    filtered_evidence = _filter_evidence(context["evidence"], request.message)
    direct_sources = [_format_source(i+1, e) for i, e in enumerate(filtered_evidence[:5])]

    # RAG vector retrieval
    kb_sources = _rag_search(request.project_id, request.user_id, request.message)

    # Merge, deduplicate by evidence_id
    seen = set()
    all_sources = []
    for s in direct_sources + kb_sources:
        eid = s.get("evidence_id") or s.get("id")
        if eid not in seen:
            all_sources.append(s)
            seen.add(eid)

    reply = _build_reply(request.message, context, direct_sources, kb_sources)

    return {
        "status": "success",
        "reply": reply,
        "sources": all_sources[:8],
    }
