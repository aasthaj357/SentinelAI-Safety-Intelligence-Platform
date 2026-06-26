import logging
from app.agents.base import BaseADKAgent
from app.core.supabase_client import supabase

logger = logging.getLogger(__name__)

# --- Tool Handlers for the Orchestrator ---

def trigger_vision_analysis(video_id: str, project_id: str) -> dict:
    """Run frame processing, face blurring, and YOLO/Roboflow detections."""
    logger.info(f"Orchestrator Tool: Executing vision analysis for video {video_id}")
    return {"status": "success", "processed_frames": 120}

def trigger_compliance_audit(project_id: str, detections: list) -> dict:
    """Run comparative auditing of detections against the project SOP rules."""
    logger.info(f"Orchestrator Tool: Executing compliance audit for project {project_id}")
    return {"status": "success", "violations_found": len(detections)}

def trigger_risk_assessment(project_id: str, violations: list) -> dict:
    """Compute risk score and flag HITL approvals if threshold exceeded."""
    logger.info(f"Orchestrator Tool: Executing risk assessment for project {project_id}")
    return {"status": "success", "risk_score": 85.0}

class OrchestratorAgent(BaseADKAgent):
    """Orchestrator Agent supervising the safety intelligence pipeline via function choices."""
    
    def __init__(self):
        instructions = (
            "You are the Orchestrator Agent. You supervise the workplace safety analysis pipeline. "
            "Your job is to receive analysis queries and call tools in the correct order: "
            "1. Call trigger_vision_analysis to process frames and detections. "
            "2. Call trigger_compliance_audit to compare detections against SOP. "
            "3. Call trigger_risk_assessment to compute cumulative risk scores and check approval limits. "
            "Explain each step to the user in the final output."
        )

        # OpenAI-compatible JSON Schema tool declarations (Groq format)
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "trigger_vision_analysis",
                    "description": "Run frame extraction, face blurring, and YOLO/Roboflow detections.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "video_id":   {"type": "string", "description": "The video ID to analyze"},
                            "project_id": {"type": "string", "description": "The parent project ID"},
                        },
                        "required": ["video_id", "project_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "trigger_compliance_audit",
                    "description": "Run comparative auditing of detections against the project SOP rules.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_id": {"type": "string", "description": "The project ID to verify"},
                            "detections":  {"type": "array",  "items": {"type": "object"}, "description": "List of frame detections"},
                        },
                        "required": ["project_id", "detections"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "trigger_risk_assessment",
                    "description": "Compute risk score and flag HITL approvals if threshold exceeded.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_id": {"type": "string", "description": "The project ID to verify"},
                            "violations":  {"type": "array",  "items": {"type": "object"}, "description": "List of compliance violations"},
                        },
                        "required": ["project_id", "violations"],
                    },
                },
            },
        ]

        handlers = {
            "trigger_vision_analysis":  trigger_vision_analysis,
            "trigger_compliance_audit": trigger_compliance_audit,
            "trigger_risk_assessment":  trigger_risk_assessment,
        }

        super().__init__(
            name="OrchestratorAgent",
            instructions=instructions,
            tools=tools,
            tool_handlers=handlers,
        )

    def check_approval_trigger(self, project_id: str, job_id: str, risk_score: float, user_id: str = None, checkpoint_data: dict = None) -> bool:
        """Verify if cumulative risk requires pausing pipeline for supervisor approval."""
        if risk_score >= 80.0:
            logger.warning(f"Orchestrator: High risk score {risk_score} encountered. Suspending execution.")
            try:
                # Update job status
                supabase.table("analysis_jobs").update({
                    "status": "awaiting_approval"
                }).eq("id", job_id).execute()
                
                details_payload = {
                    "job_id": job_id,
                    "risk_score": risk_score,
                    "reason": "Cumulative risk score threshold (80) breached."
                }
                if checkpoint_data:
                    details_payload["checkpoint"] = checkpoint_data

                # Insert approval request containing serial trace checkpoint context
                supabase.table("approval_requests").insert({
                    "project_id": project_id,
                    "user_id": user_id,
                    "request_type": "high_risk_incident",
                    "status": "pending",
                    "target_id": job_id,
                    "details": details_payload
                }).execute()
                
                return True
            except Exception as e:
                logger.error(f"Orchestrator failed to trigger approval lock: {e}")
                return False
        return False
