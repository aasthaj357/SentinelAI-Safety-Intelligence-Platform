import logging
from app.mcp.sse_transport import MCPServerSSE
from app.core.supabase_client import supabase
from app.api.reports import _generate_report_html, _html_to_pdf_bytes, _fetch_project_data

logger = logging.getLogger(__name__)

reporting_server = MCPServerSSE("reporting")

# --- Handlers ---

async def generate_draft_report(project_id: str, user_id: str) -> dict:
    """Dynamically generate draft HTML report for review."""
    try:
        data = _fetch_project_data(project_id, user_id)
        html_content = _generate_report_html(data)
        
        # Save placeholder record as draft
        report_res = supabase.table("generated_reports").insert({
            "project_id": project_id,
            "user_id": user_id,
            "report_url": f"/reports/draft-{project_id}.html",
            "type": "draft_html",
        }).execute()
        
        report_id = report_res.data[0]["id"] if report_res.data else None
        
        return {
            "status": "success",
            "report_id": report_id,
            "draft_html": html_content
        }
    except Exception as e:
        logger.error(f"Reporting MCP Server: generate_draft_report failed: {e}")
        return {"status": "error", "message": str(e)}

async def submit_for_approval(report_id: str, user_id: str) -> dict:
    """Submit a draft report to the human approval queue."""
    try:
        # Create approval ticket
        ticket_res = supabase.table("approval_requests").insert({
            "project_id": None, # Resolve cascade later if needed
            "user_id": user_id,
            "request_type": "report_generation",
            "status": "pending",
            "target_id": report_id,
            "details": {"report_id": report_id, "notes": "Automated multi-agent audit compilation."}
        }).execute()
        
        if ticket_res.data:
            # Update report status
            supabase.table("generated_reports").update({"type": "pending_approval"}).eq("id", report_id).execute()
            return {
                "status": "success",
                "approval_id": ticket_res.data[0]["id"],
                "message": "Report submitted for human supervisor review."
            }
        return {"status": "error", "message": "Failed to create approval ticket."}
    except Exception as e:
        logger.error(f"Reporting MCP Server: submit_for_approval failed: {e}")
        return {"status": "error", "message": str(e)}

async def export_pdf_document(report_id: str) -> dict:
    """Convert approved draft HTML to a finalized PDF document and upload."""
    try:
        # Fetch report details
        rep_res = supabase.table("generated_reports").select("*").eq("id", report_id).maybe_single().execute()
        report = getattr(rep_res, "data", None)
        if not report:
            return {"status": "error", "message": "Report record not found."}
            
        # Compile content and export
        data = _fetch_project_data(report["project_id"], report["user_id"])
        html_content = _generate_report_html(data)
        pdf_bytes = _html_to_pdf_bytes(html_content)
        
        # Upload PDF to storage
        import uuid
        filename = f"{report['project_id']}/report_{uuid.uuid4()}.pdf"
        
        supabase.storage.from_("annotated-videos").upload(
            filename, pdf_bytes, {"content-type": "application/pdf"}
        )
        pdf_url = supabase.storage.from_("annotated-videos").get_public_url(filename)
        
        # Update record URL
        supabase.table("generated_reports").update({
            "report_url": pdf_url,
            "type": "safety_analysis_pdf"
        }).eq("id", report_id).execute()
        
        return {
            "status": "success",
            "report_id": report_id,
            "pdf_url": pdf_url,
            "message": "PDF exported and uploaded successfully."
        }
    except Exception as e:
        logger.error(f"Reporting MCP Server: export_pdf_document failed: {e}")
        return {"status": "error", "message": str(e)}

# --- Register Tools ---

reporting_server.register_tool(
    name="generate_draft_report",
    description="Generate a draft HTML safety report summarizing violations, evidence, and risk profiles.",
    input_schema={
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "The target project UUID"},
            "user_id": {"type": "string", "description": "The requesting user UUID"}
        },
        "required": ["project_id", "user_id"]
    },
    handler=generate_draft_report
)

reporting_server.register_tool(
    name="submit_for_approval",
    description="Queue an HTML draft report in the database, requiring manual supervisor approval before compilation.",
    input_schema={
        "type": "object",
        "properties": {
            "report_id": {"type": "string", "description": "The target report UUID"},
            "user_id": {"type": "string", "description": "The requesting user UUID"}
        },
        "required": ["report_id", "user_id"]
    },
    handler=submit_for_approval
)

reporting_server.register_tool(
    name="export_pdf_document",
    description="Convert an approved HTML draft report to a PDF document, saving it to Supabase Storage.",
    input_schema={
        "type": "object",
        "properties": {
            "report_id": {"type": "string", "description": "The target report UUID"}
        },
        "required": ["report_id"]
    },
    handler=export_pdf_document
)

router = reporting_server.router
