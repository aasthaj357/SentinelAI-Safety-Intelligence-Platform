import logging
from app.agents.base import BaseADKAgent
from app.mcp.memory_server import store_decision_trace

logger = logging.getLogger(__name__)

class ComplianceAgent(BaseADKAgent):
    """Compliance Agent auditing observations against project safety rules."""
    
    def __init__(self):
        instructions = (
            "You are the Compliance Agent. You analyze workplace activities. "
            "Your job is to compare detected actions against the active SOP rules "
            "and record detailed safety violation logs when requirements are breached."
        )
        super().__init__(name="ComplianceAgent", instructions=instructions)

    async def audit_frame(self, project_id: str, frame_num: int, timestamp: float, detections: list, rules: list) -> list:
        """Compare observed items in a frame against SOP guidelines, flagging missing items."""
        violations = []
        observed_classes = {d["class"].lower() for d in detections}
        
        for rule in rules:
            rule_lower = rule.lower()
            
            # Query the SOP MCP server tool verify_sop_rule
            sop_res = await verify_sop_rule(ppe_type=rule_lower, project_id=project_id)
            is_mandatory = sop_res.get("is_mandatory", False)
            
            if is_mandatory and rule_lower not in observed_classes:
                # Violation detected: a mandatory item was not observed on screen
                viol_type = f"no-{rule_lower}"
                violations.append({
                    "violation_type": viol_type,
                    "timestamp": timestamp,
                    "frame_number": frame_num,
                    "confidence": 0.85
                })
                
                # Log decision trace to Memory MCP Server
                await store_decision_trace(
                    agent_id=self.name,
                    step="audit_frame_violation",
                    reasoning=f"Mandatory safety item '{rule_lower}' was not detected in frame #{frame_num} at {timestamp}s. Verified via SOP MCP Tool.",
                    context={"frame_num": frame_num, "timestamp": timestamp, "violation": viol_type, "citation": sop_res.get("regulatory_citation")},
                    project_id=project_id
                )
                
        return violations
