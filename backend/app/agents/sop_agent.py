import logging
from app.agents.base import BaseADKAgent
from app.mcp.sop_server import get_sop_sections, verify_sop_rule

logger = logging.getLogger(__name__)

class SOPAgent(BaseADKAgent):
    """SOP Agent interfacing with the SOP MCP Server to fetch compliance rules."""
    
    def __init__(self):
        instructions = (
            "You are the SOP Agent. You specialize in interpreting regulatory Standard Operating Procedures (SOPs). "
            "Your job is to look up active project files via the SOP MCP Server, "
            "and verify if a target safety rule is mandated."
        )
        super().__init__(name="SOPAgent", instructions=instructions)

    async def get_project_rules(self, project_id: str) -> dict:
        """Fetch the compliance rules for the project."""
        logger.info(f"SOPAgent: Fetching compliance sections for project {project_id}")
        
        # Invoke tool handler
        res = await get_sop_sections(project_id)
        if res.get("status") == "success":
            return {
                "ppe_requirements": res.get("ppe_requirements", []),
                "restricted_areas": res.get("restricted_areas", []),
                "document_title": res.get("title")
            }
            
        # Fallback to base baseline safety rules
        return {
            "ppe_requirements": ["helmet", "gloves", "goggles", "vest", "shoes"],
            "restricted_areas": [],
            "document_title": "Baseline Safety Guidelines"
        }

    async def check_mandatory_ppe(self, ppe_type: str, project_id: str) -> bool:
        """Verify if a specific safety item is flagged as mandatory."""
        res = await verify_sop_rule(ppe_type, project_id)
        return res.get("is_mandatory", False)
