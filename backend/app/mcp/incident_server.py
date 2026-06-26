import logging
from app.mcp.sse_transport import MCPServerSSE
from app.core.supabase_client import supabase

logger = logging.getLogger(__name__)

incident_server = MCPServerSSE("incident")

# --- Handlers ---

async def fetch_historical_incidents(project_id: str, days: int = 30) -> dict:
    """Fetch safety records and past incident statistics."""
    try:
        # Get count of past violation entries within date range
        import datetime
        limit_date = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).isoformat()
        
        video_res = supabase.table("video_uploads").select("id").eq("project_id", project_id).execute()
        video_ids = [r["id"] for r in (video_res.data or [])]
        if not video_ids:
            return {"status": "success", "time_range_days": days, "total_incidents_recorded": 0, "breakdown_by_type": {}}
        res = supabase.table("violation_tracking").select("*").in_("video_id", video_ids).gte("created_at", limit_date).execute()
        violations = res.data or []
        
        # Aggregate by type
        stats = {}
        for v in violations:
            vtype = v.get("violation_type")
            stats[vtype] = stats.get(vtype, 0) + 1
            
        return {
            "status": "success",
            "time_range_days": days,
            "total_incidents_recorded": len(violations),
            "breakdown_by_type": stats
        }
    except Exception as e:
        logger.error(f"Incident MCP Server: fetch_historical_incidents failed: {e}")
        return {"status": "error", "message": str(e)}

async def record_incident_prediction(project_id: str, details: dict, probability: float) -> dict:
    """Log an LLM-reasoned incident prediction profile in the database."""
    try:
        res = supabase.table("incident_predictions").insert({
            "project_id": project_id,
            "prediction_details": details,
            "probability": probability
        }).execute()
        
        if res.data:
            return {
                "status": "success",
                "prediction_id": res.data[0]["id"],
                "message": "Incident prediction successfully recorded."
            }
        return {"status": "error", "message": "Failed to store record."}
    except Exception as e:
        logger.error(f"Incident MCP Server: record_incident_prediction failed: {e}")
        return {"status": "error", "message": str(e)}

async def get_worker_safety_profile(worker_label: str, project_id: str) -> dict:
    """Fetch a worker's cumulative historical safety statistics and metrics."""
    try:
        # Get track records from violation_tracking
        video_res = supabase.table("video_uploads").select("id").eq("project_id", project_id).execute()
        video_ids = [r["id"] for r in (video_res.data or [])]
        if not video_ids:
            all_viols = []
        else:
            res = supabase.table("violation_tracking").select("id,violation_type,created_at,metadata").in_("video_id", video_ids).execute()
            all_viols = res.data or []
        
        # Get matching video/frame records to find matches for this worker label
        worker_viols = []
        for v in all_viols:
            meta = v.get("metadata") or {}
            if meta.get("worker_id") == worker_label or meta.get("worker_label") == worker_label:
                worker_viols.append(v)
                
        # Group and score safety performance
        v_count = len(worker_viols)
        rating = "Excellent" if v_count == 0 else "Good" if v_count < 3 else "Needs Training" if v_count < 8 else "Critical Intervention"
        
        return {
            "worker_label": worker_label,
            "project_id": project_id,
            "safety_rating": rating,
            "total_historical_violations": v_count,
            "violation_types_triggered": list(set(v.get("violation_type") for v in worker_viols))
        }
    except Exception as e:
        logger.error(f"Incident MCP Server: get_worker_safety_profile failed: {e}")
        return {"status": "error", "message": str(e)}

# --- Register Tools ---

incident_server.register_tool(
    name="fetch_historical_incidents",
    description="Query safety records and gather incident data logged within a past day limit.",
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "The target project UUID"},
            "days": {"type": "integer", "description": "Range of review window in days", "default": 30}
        },
        "required": ["project_id"]
    },
    handler=fetch_historical_incidents
)

incident_server.register_tool(
    name="record_incident_prediction",
    description="Save a predicted potential hazard profile (including details and probability) to database.",
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "The target project UUID"},
            "details": {"type": "object", "description": "JSON details describing reasoning and metrics"},
            "probability": {"type": "number", "description": "Prediction probability score (0.0 to 1.0)"}
        },
        "required": ["project_id", "details", "probability"]
    },
    handler=record_incident_prediction
)

incident_server.register_tool(
    name="get_worker_safety_profile",
    description="Check worker track records, safety stats, rating, and recurring safety violations.",
    input_schema={
        "type": "object",
        "properties": {
            "worker_label": {"type": "string", "description": "The worker track label (e.g. Worker_1)"},
            "project_id": {"type": "string", "description": "The target project UUID"}
        },
        "required": ["worker_label", "project_id"]
    },
    handler=get_worker_safety_profile
)

router = incident_server.router
