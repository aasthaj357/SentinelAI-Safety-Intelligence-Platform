import logging
from app.agents.base import BaseADKAgent
from app.core.supabase_client import supabase

logger = logging.getLogger(__name__)

class ExplainabilityAgent(BaseADKAgent):
    """Explainability Agent explaining system decisions and safety logic."""
    
    def __init__(self):
        instructions = (
            "You are the Explainability Agent. You help users understand the system's reasoning. "
            "Your job is to read trace records and compile detailed summaries. "
            "Explain exactly why a violation was flagged, citing specific SOP sections and visual evidence frames."
        )
        super().__init__(name="ExplainabilityAgent", instructions=instructions)

    def explain_violation(self, violation_id: str) -> dict:
        """Fetch a violation and compile its explainability summary card."""
        logger.info(f"ExplainabilityAgent: Resolving context for violation {violation_id}")
        
        try:
            # Query violation and matching project/evidence data
            viol_res = supabase.table("violation_tracking").select("*").eq("id", violation_id).maybe_single().execute()
            viol = getattr(viol_res, "data", None)
            if not viol:
                return {"status": "error", "explanation": "Violation record not found."}
                
            # Get trace logs
            trace_res = supabase.table("decision_traces").select("*").eq("step", "audit_frame_violation").execute()
            traces = trace_res.data or []
            
            # Match trace with violation timestamp
            matching_trace = "No direct trace record found."
            for t in traces:
                ctx = t.get("context") or {}
                if ctx.get("violation") == viol.get("violation_type") and ctx.get("timestamp") == viol.get("timestamp"):
                    matching_trace = t.get("reasoning")
                    break
                    
            explanation = (
                f"Violation '{viol.get('violation_type')}' was registered at {viol.get('timestamp')}s. "
                f"Reasoning trace: {matching_trace}"
            )
            
            return {
                "status": "success",
                "violation_id": violation_id,
                "type": viol.get("violation_type"),
                "timestamp": viol.get("timestamp"),
                "reasoning_summary": explanation,
                "confidence_score": viol.get("confidence", 0.85)
            }
        except Exception as e:
            logger.error(f"ExplainabilityAgent failed: {e}")
            return {"status": "error", "explanation": str(e)}
