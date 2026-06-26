import logging
from app.mcp.sse_transport import MCPServerSSE
from app.core.supabase_client import supabase
from app.services.rag_service import get_rag_service

logger = logging.getLogger(__name__)
rag = get_rag_service()

memory_server = MCPServerSSE("memory")

# --- Handlers ---

async def save_agent_memory(agent_id: str, key: str, value: dict) -> dict:
    """Store short-term or episodic memory parameters for a specific agent."""
    try:
        # We can store in knowledge_base with metadata containing target fields
        rag.embed_and_store(
            project_id="00000000-0000-0000-0000-000000000000", # System fallback ID
            source_type=f"memory_{agent_id}",
            source_id="00000000-0000-0000-0000-000000000000",
            content=f"Agent {agent_id} memory: {key} is {str(value)}",
            metadata={"agent_id": agent_id, "key": key, "value": value}
        )
        return {"status": "success", "message": f"Episodic memory recorded for agent {agent_id}."}
    except Exception as e:
        logger.error(f"Memory MCP Server: save_agent_memory failed: {e}")
        return {"status": "error", "message": str(e)}

async def retrieve_agent_memory(agent_id: str, key: str) -> dict:
    """Retrieve custom episodic memory logs for a specific agent."""
    try:
        # Search the knowledge_base system index
        hits = rag.similarity_search(
            project_id="00000000-0000-0000-0000-000000000000",
            query=f"Agent {agent_id} memory {key}",
            top_k=3
        )
        # Parse matches
        records = []
        for hit in hits:
            meta = hit.get("metadata") or {}
            if meta.get("agent_id") == agent_id and meta.get("key") == key:
                records.append(meta.get("value"))
                
        return {
            "status": "success",
            "agent_id": agent_id,
            "key": key,
            "values": records
        }
    except Exception as e:
        logger.error(f"Memory MCP Server: retrieve_agent_memory failed: {e}")
        return {"status": "error", "message": str(e)}

async def get_worker_history(worker_label: str, project_id: str) -> dict:
    """Fetch safety ratings and previous violations associated with a specific worker label."""
    try:
        # Retrieve worker profile
        from app.mcp.incident_server import get_worker_safety_profile
        res = await get_worker_safety_profile(worker_label, project_id)
        return res
    except Exception as e:
        logger.error(f"Memory MCP Server: get_worker_history failed: {e}")
        return {"status": "error", "message": str(e)}

async def store_decision_trace(agent_id: str, step: str, reasoning: str, context: dict, project_id: str = None) -> dict:
    """Register an agent reasoning step in the system audit trail table."""
    try:
        # Safe default project ID resolving
        target_pid = project_id or "00000000-0000-0000-0000-000000000000"
        
        res = supabase.table("decision_traces").insert({
            "project_id": target_pid if target_pid != "00000000-0000-0000-0000-000000000000" else None,
            "agent_id": agent_id,
            "step": step,
            "reasoning": reasoning,
            "context": context
        }).execute()
        
        if res.data:
            return {
                "status": "success",
                "trace_id": res.data[0]["id"],
                "message": "Reasoning trace captured in transaction memory."
            }
        return {"status": "error", "message": "Failed to log decision trace."}
    except Exception as e:
        logger.error(f"Memory MCP Server: store_decision_trace failed: {e}")
        return {"status": "error", "message": str(e)}

async def get_project_context(project_id: str) -> dict:
    """Aggregate safety scores, violation totals, and general audit metadata for RAG chats."""
    try:
        from app.api.chat import _fetch_project_context
        # Run internal database helper
        res = _fetch_project_context(project_id, "00000000-0000-0000-0000-000000000000")  # Guest or default ID
        return {
            "status": "success",
            "project_id": project_id,
            "total_violations_registered": len(res.get("violations", [])),
            "evidence_count": len(res.get("evidence", [])),
            "latest_risk_score": res.get("risks")[0].get("score") if res.get("risks") else 0
        }
    except Exception as e:
        logger.error(f"Memory MCP Server: get_project_context failed: {e}")
        return {"status": "error", "message": str(e)}

# --- Register Tools ---

memory_server.register_tool(
    name="save_agent_memory",
    description="Record short-term agent memory key-value properties inside system vector logs.",
    input_schema={
        "type": "object",
        "properties": {
            "agent_id": {"type": "string", "description": "The target agent name identifier"},
            "key": {"type": "string", "description": "The search keyword category"},
            "value": {"type": "object", "description": "JSON details to store"}
        },
        "required": ["agent_id", "key", "value"]
    },
    handler=save_agent_memory
)

memory_server.register_tool(
    name="retrieve_agent_memory",
    description="Retrieve dynamic episodic memory records based on agent identifier and keyword parameters.",
    input_schema={
        "type": "object",
        "properties": {
            "agent_id": {"type": "string", "description": "The target agent name identifier"},
            "key": {"type": "string", "description": "The search keyword category"}
        },
        "required": ["agent_id", "key"]
    },
    handler=retrieve_agent_memory
)

memory_server.register_tool(
    name="get_worker_history",
    description="Check safety ratings, past violations, and compliance levels for a worker.",
    input_schema={
        "type": "object",
        "properties": {
            "worker_label": {"type": "string", "description": "The worker track label (e.g. Worker_1)"},
            "project_id": {"type": "string", "description": "The target project UUID"}
        },
        "required": ["worker_label", "project_id"]
    },
    handler=get_worker_history
)

memory_server.register_tool(
    name="store_decision_trace",
    description="Log chronological agent actions, decision traces, and reasoning explanations for audit compliance.",
    input_schema={
        "type": "object",
        "properties": {
            "agent_id": {"type": "string", "description": "The sending agent identifier"},
            "step": {"type": "string", "description": "The execution phase or milestone"},
            "reasoning": {"type": "string", "description": "Explainable text detailing agent decisions"},
            "context": {"type": "object", "description": "Execution metadata properties"},
            "project_id": {"type": "string", "description": "The target project UUID"}
        },
        "required": ["agent_id", "step", "reasoning", "context"]
    },
    handler=store_decision_trace
)

memory_server.register_tool(
    name="get_project_context",
    description="Aggregate project statistics, historical incident counts, and safety performance metadata.",
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "The target project UUID"}
        },
        "required": ["project_id"]
    },
    handler=get_project_context
)

router = memory_server.router
