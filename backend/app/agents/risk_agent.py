import logging
from app.agents.base import BaseADKAgent
from app.core.supabase_client import supabase
from app.mcp.memory_server import store_decision_trace

logger = logging.getLogger(__name__)

VIOLATION_WEIGHTS = {
    "helmet": (25, "Head injury / traumatic brain injury", "critical"),
    "gloves": (20, "Hand laceration / chemical burn", "high"),
    "goggles": (15, "Eye injury / chemical exposure", "high"),
    "vest": (12, "Struck-by / low visibility collision", "medium"),
    "mask": (10, "Respiratory / chemical exposure", "medium"),
    "shoes": (10, "Foot crush / slip injury", "medium"),
}

class RiskAgent(BaseADKAgent):
    """Risk Agent evaluating cumulative safety danger ratings."""
    
    def __init__(self):
        instructions = (
            "You are the Risk Agent. You analyze safety violations. "
            "Your job is to assess cumulative workplace danger levels, "
            "apply risk weights based on violation severity, and log risk profiles."
        )
        super().__init__(name="RiskAgent", instructions=instructions)

    async def evaluate_project_risk(self, project_id: str, violations: list, user_id: str = None) -> float:
        """Calculate weighted hazard score and insert a risk assessment profile."""
        total_risk = 0.0
        details = []
        
        for v in violations:
            vtype = v.get("violation_type", "").replace("no-", "").replace("no_", "")
            weight, injury, severity = VIOLATION_WEIGHTS.get(vtype, (10, "General hazard", "medium"))
            
            # Apply standard baseline weights
            adjusted_risk = weight * 1.05  # Default duration multiplier
            total_risk += adjusted_risk
            
            details.append({
                "violation_type": v.get("violation_type"),
                "timestamp": v.get("timestamp"),
                "injury_hazard": injury,
                "adjusted_risk": round(adjusted_risk, 2)
            })
            
        final_score = min(100.0, round(total_risk, 1))
        
        # Save to database
        try:
            supabase.table("risk_assessments").insert({
                "project_id": project_id,
                "user_id": user_id,
                "score": final_score,
                "details": {
                    "level": "Critical" if final_score >= 80 else "High" if final_score >= 50 else "Medium" if final_score >= 20 else "Low",
                    "reasoning": f"Calculated total score of {final_score} across {len(violations)} recorded safety breaches.",
                    "evidence_breakdown": details
                }
            }).execute()
            
            # Log trace
            await store_decision_trace(
                agent_id=self.name,
                step="evaluate_project_risk",
                reasoning=f"Calculated project safety score of {final_score}/100. Logged entry in database.",
                context={"violations_count": len(violations), "final_score": final_score},
                project_id=project_id
            )
        except Exception as e:
            logger.error(f"RiskAgent: Failed to insert safety assessment: {e}")
            
        return final_score
