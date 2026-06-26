import logging
from app.mcp.sse_transport import MCPServerSSE
from app.core.supabase_client import supabase

logger = logging.getLogger(__name__)

evidence_server = MCPServerSSE("evidence")

# --- Handlers ---

async def register_evidence(project_id: str, video_id: str, detection_label: str, timestamp: float, screenshot_url: str, metadata: dict) -> dict:
    """Insert a formal evidence record linking the violation coordinates and assets."""
    try:
        # Resolve potential null values
        ev_payload = {
            "project_id": project_id,
            "video_id": video_id,
            "evidence_type": "video_violation",
            "timestamp": timestamp,
            "detection_label": detection_label,
            "confidence": metadata.get("confidence", 0.85),
            "screenshot_url": screenshot_url,
            "annotated_screenshot_url": screenshot_url,
            "risk_reason": f"Observed safety exception: missing {detection_label.replace('no-', '')}",
            "metadata": metadata
        }
        
        res = supabase.table("evidence_records").insert(ev_payload).execute()
        if res.data:
            return {
                "status": "success",
                "evidence_id": res.data[0]["id"],
                "message": "Evidence record registered successfully."
            }
        return {"status": "error", "message": "Failed to create evidence log."}
    except Exception as e:
        logger.error(f"Evidence MCP Server: register_evidence failed: {e}")
        return {"status": "error", "message": str(e)}

async def update_annotated_status(evidence_id: str, annotated_screenshot_url: str) -> dict:
    """Modify the target evidence record with the blurred/annotated visual asset path."""
    try:
        res = supabase.table("evidence_records").update({
            "annotated_screenshot_url": annotated_screenshot_url
        }).eq("id", evidence_id).execute()
        
        if res.data:
            return {
                "status": "success",
                "evidence_id": evidence_id,
                "message": "Annotated screenshot URL updated."
            }
        return {"status": "error", "message": "No evidence record updated."}
    except Exception as e:
        logger.error(f"Evidence MCP Server: update_annotated_status failed: {e}")
        return {"status": "error", "message": str(e)}

# --- Register Tools ---

evidence_server.register_tool(
    name="register_evidence",
    description="Save a new safety violation evidence file linking screenshot image and metadata.",
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "The target project UUID"},
            "video_id": {"type": "string", "description": "The target video UUID"},
            "detection_label": {"type": "string", "description": "Type of violation detected (e.g. no-helmet)"},
            "timestamp": {"type": "number", "description": "Video playback timestamp in seconds"},
            "screenshot_url": {"type": "string", "description": "Public URL link to raw frame screenshot"},
            "metadata": {"type": "object", "description": "Visual tracking details including bounding box and confidence"}
        },
        "required": ["project_id", "video_id", "detection_label", "timestamp", "screenshot_url"]
    },
    handler=register_evidence
)

evidence_server.register_tool(
    name="update_annotated_status",
    description="Update the visual evidence record with the blurred or labeled screenshot URL.",
    input_schema={
        "type": "object",
        "properties": {
            "evidence_id": {"type": "string", "description": "The target evidence record UUID"},
            "annotated_screenshot_url": {"type": "string", "description": "Public URL of labeled or masked screenshot"}
        },
        "required": ["evidence_id", "annotated_screenshot_url"]
    },
    handler=update_annotated_status
)

router = evidence_server.router
