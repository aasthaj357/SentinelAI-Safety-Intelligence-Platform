import logging
from app.mcp.sse_transport import MCPServerSSE
from app.core.supabase_client import supabase
from app.services.rag_service import get_rag_service

logger = logging.getLogger(__name__)
rag = get_rag_service()

sop_server = MCPServerSSE("sop")

# --- Handlers ---

async def get_sop_sections(project_id: str) -> dict:
    """Fetch structured SOP sections for a project."""
    try:
        res = supabase.table("sop_documents").select("id,title,sop_structure").eq("project_id", project_id).order("created_at", desc=True).limit(1).execute()
        if res.data:
            doc = res.data[0]
            struct = doc.get("sop_structure") or {}
            # Standardize output for agents
            return {
                "status": "success",
                "document_id": doc.get("id"),
                "title": doc.get("title"),
                "ppe_requirements": struct.get("ppe_requirements", []),
                "restricted_areas": struct.get("restricted_areas", []),
                "raw_structure": struct
            }
        return {"status": "error", "message": "No SOP document found for this project."}
    except Exception as e:
        logger.error(f"SOP MCP Server: get_sop_sections failed: {e}")
        return {"status": "error", "message": str(e)}

async def query_sop_text(query: str, project_id: str, limit: int = 5) -> dict:
    """Perform RAG search against SOP vectors."""
    try:
        # Search kb for 'sop' source type matches
        hits = rag.similarity_search(project_id, query, top_k=limit)
        results = [
            {
                "id": hit.get("id"),
                "content": hit.get("content"),
                "score": hit.get("similarity", 0.0),
                "source_type": hit.get("source_type")
            }
            for hit in hits if hit.get("source_type") == "sop"
        ]
        return {"status": "success", "results": results}
    except Exception as e:
        logger.error(f"SOP MCP Server: query_sop_text failed: {e}")
        return {"status": "error", "message": str(e)}

async def verify_sop_rule(ppe_type: str, project_id: str) -> dict:
    """Verify if a specific PPE item is mandatory according to latest SOP rules."""
    try:
        res = supabase.table("sop_documents").select("sop_structure").eq("project_id", project_id).order("created_at", desc=True).limit(1).execute()
        if res.data:
            struct = res.data[0].get("sop_structure") or {}
            reqs = [p.lower() for p in struct.get("ppe_requirements", [])]
            is_mandatory = ppe_type.lower() in reqs
            
            # Formulate citation description
            citation = f"SOP requirements section outlines mandatory PPE items: {', '.join(reqs)}"
            return {
                "ppe_type": ppe_type,
                "is_mandatory": is_mandatory,
                "regulatory_citation": citation if is_mandatory else "No active SOP requirement found for this item."
            }
        # Fallback to defaults
        default_reqs = ["helmet", "gloves", "goggles", "vest", "shoes"]
        return {
            "ppe_type": ppe_type,
            "is_mandatory": ppe_type.lower() in default_reqs,
            "regulatory_citation": "Standard OSHA workplace baseline safety fallback."
        }
    except Exception as e:
        logger.error(f"SOP MCP Server: verify_sop_rule failed: {e}")
        return {"status": "error", "message": str(e)}

# --- Register Tools ---

sop_server.register_tool(
    name="get_sop_sections",
    description="Fetch the active safety procedures and PPE lists defined in the latest SOP document.",
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "The target project UUID"}
        },
        "required": ["project_id"]
    },
    handler=get_sop_sections
)

sop_server.register_tool(
    name="query_sop_text",
    description="Perform semantic keyword/sentence similarity search across the chunked SOP policy texts.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search term or safety query sentence"},
            "project_id": {"type": "string", "description": "The target project UUID"},
            "limit": {"type": "integer", "description": "Maximum search result entries", "default": 5}
        },
        "required": ["query", "project_id"]
    },
    handler=query_sop_text
)

sop_server.register_tool(
    name="verify_sop_rule",
    description="Check whether a specific PPE type (helmet, gloves, goggles, vest, mask, shoes) is marked mandatory.",
    input_schema={
        "type": "object",
        "properties": {
            "ppe_type": {"type": "string", "description": "The PPE item label"},
            "project_id": {"type": "string", "description": "The target project UUID"}
        },
        "required": ["ppe_type", "project_id"]
    },
    handler=verify_sop_rule
)

router = sop_server.router
