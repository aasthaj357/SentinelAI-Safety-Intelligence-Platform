from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
from app.core.supabase_client import supabase
from app.services.analytics_service import get_analytics_service
import json
from datetime import datetime, timedelta
import io
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class ReportRequest(BaseModel):
    project_id: str
    user_id: str


def _fetch_project_data(project_id: str, user_id: str) -> dict:
    """Fetch all project data for report generation."""
    
    analytics = get_analytics_service()
    
    project = supabase.table("projects").select("*").eq("id", project_id).eq("user_id", user_id).maybe_single().execute()
    
    videos = supabase.table("video_uploads").select("*").eq("project_id", project_id).eq("user_id", user_id).execute()
    video_ids = [v["id"] for v in (videos.data or [])]
    
    violations = []
    if video_ids:
        viol_res = supabase.table("violation_tracking").select("*, video_uploads!inner(project_id)").eq("video_uploads.project_id", project_id).eq("user_id", user_id).execute()
        violations = viol_res.data or []
    
    evidence = supabase.table("evidence_records").select("*").eq("project_id", project_id).eq("user_id", user_id).execute()
    
    risks = supabase.table("risk_assessments").select("*").eq("project_id", project_id).eq("user_id", user_id).order("created_at", desc=True).limit(5).execute()
    
    predictions = supabase.table("incident_predictions").select("*").eq("project_id", project_id).execute()
    
    trainings = supabase.table("training_recommendations").select("*").eq("project_id", project_id).eq("user_id", user_id).execute()
    
    sops = supabase.table("sop_documents").select("*").eq("project_id", project_id).eq("user_id", user_id).execute()
    
    analytics_data = {
        "monthly_violations": analytics.get_violation_trend_by_type(user_id, project_id, 90),
        "risk_trend": analytics.get_risk_score_trend(user_id, project_id, 90, "month"),
        "ppe_trend": analytics.get_ppe_compliance_trend(user_id, project_id, 90, "month"),
        "sop_trend": analytics.get_sop_compliance_trend(user_id, project_id, 90, "month"),
        "training_effectiveness": analytics.get_training_effectiveness(user_id, project_id),
    }

    return {
        "project": project.data if (project and project.data) else {},
        "videos": videos.data or [],
        "violations": violations,
        "evidence": evidence.data or [],
        "risks": risks.data or [],
        "predictions": predictions.data or [],
        "trainings": trainings.data or [],
        "sops": sops.data or [],
        "analytics": analytics_data,
    }


def _coerce_evidence_val(val):
    """Coerce evidence field to a display string."""
    if val is None:
        return "N/A"
    if isinstance(val, list):
        return "; ".join(str(e) for e in val)
    return str(val)


def _generate_report_html(data: dict) -> str:
    """Generate HTML report content."""
    from datetime import datetime, timedelta
    
    project = data.get("project", {})
    videos = data.get("videos", [])
    evidence = data.get("evidence", [])
    risks = data.get("risks", [])
    predictions = data.get("predictions", [])
    trainings = data.get("trainings", [])
    analytics = data.get("analytics", {})
    violations = data.get("violations", [])

    # Classify videos
    def is_demo_video(v):
        title = (v.get("title") or "").lower()
        file_url = (v.get("file_url") or "").lower()
        return (
            "sector a" in title or
            "sector b" in title or
            "sector c" in title or
            "example.com" in file_url or
            file_url.startswith("http")
        )

    user_videos = [v for v in videos if not is_demo_video(v)]
    has_user_videos = len(user_videos) > 0
    
    if has_user_videos:
        target_video_ids = [v["id"] for v in user_videos]
        is_demo_only = False
    else:
        target_video_ids = [v["id"] for v in videos]
        is_demo_only = True

    # Filter violations, evidence, risks by video_id
    filtered_violations = [v for v in violations if v.get("video_id") in target_video_ids]
    filtered_evidence = [e for e in evidence if e.get("video_id") in target_video_ids]
    filtered_risks = [r for r in risks if r.get("video_id") in target_video_ids or r.get("video_id") is None]

    if is_demo_only:
        # Filter to last 7 days for demo data to avoid subtraction-overflow to 0
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        def is_recent(created_at_str):
            if not created_at_str:
                return True
            try:
                # Remove timezone offset suffix like +00:00 or Z
                clean_str = created_at_str.replace("Z", "")
                if "+" in clean_str:
                    clean_str = clean_str.split("+")[0]
                dt = datetime.fromisoformat(clean_str)
                return dt >= seven_days_ago
            except Exception:
                return True

        filtered_violations = [v for v in filtered_violations if is_recent(v.get("created_at"))]
        filtered_evidence = [e for e in filtered_evidence if is_recent(e.get("created_at"))]
        filtered_risks = [r for r in filtered_risks if is_recent(r.get("created_at"))]

    violations = filtered_violations
    evidence = filtered_evidence
    risks = filtered_risks
    videos = user_videos if has_user_videos else videos

    max_risk = float(risks[0].get("score") or 0) if risks else 0
    violation_count = len(violations)
    evidence_count = len(evidence)
    
    html_parts = []
    
    html_parts.append("""
    <html>
    <head>
        <meta charset="UTF-8"/>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; color: #333; }
            h1 { color: #1f2937; border-bottom: 3px solid #4f46e5; padding-bottom: 10px; }
            h2 { color: #374151; margin-top: 30px; }
            h3 { color: #4b5563; margin-top: 20px; }
            .section { margin: 20px 0; padding: 15px; background: #f9fafb; border-left: 4px solid #4f46e5; }
            .critical { border-left-color: #dc2626; background: #fef2f2; }
            .high { border-left-color: #f59e0b; background: #fffbeb; }
            .medium { border-left-color: #10b981; background: #f0fdf4; }
            table { width: 100%; border-collapse: collapse; margin: 10px 0; }
            th { background: #4f46e5; color: white; padding: 10px; text-align: left; }
            td { padding: 8px; border-bottom: 1px solid #e5e7eb; }
            .metric { font-size: 24px; font-weight: bold; color: #4f46e5; }
            .timestamp { color: #6b7280; font-size: 12px; }
            .scorecard { display: flex; gap: 20px; flex-wrap: wrap; margin: 20px 0; }
            .score-box { background: #f3f4f6; border-radius: 8px; padding: 15px; min-width: 120px; text-align: center; }
            .score-label { font-size: 12px; color: #6b7280; }
            .score-val { font-size: 28px; font-weight: bold; color: #4f46e5; }
        </style>
    </head>
    <body>
    """)
    
    html_parts.append(f"<h1>Safety Analysis Report</h1>")
    html_parts.append(f"<p><strong>Project:</strong> {project.get('name', 'Safety Analysis Project')}</p>")
    html_parts.append(f"<p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")
    html_parts.append(f"<p><strong>Videos Analyzed:</strong> {len(user_videos) if has_user_videos else len(videos)} | <strong>Violations Detected:</strong> {violation_count} | <strong>Evidence Records:</strong> {evidence_count}</p>")
    # Calculate unique categories violated
    violated_categories = set()
    violated_ppe = set()
    for v in violations:
        t = (v.get("violation_type") or "").lower()
        if "helmet" in t or "hardhat" in t or "hard-hat" in t:
            violated_categories.add("helmet")
            violated_ppe.add("helmet")
        elif "glove" in t:
            violated_categories.add("gloves")
            violated_ppe.add("gloves")
        elif "goggle" in t or "eye" in t:
            violated_categories.add("goggles")
            violated_ppe.add("goggles")
        elif "vest" in t or "vis" in t:
            violated_categories.add("vest")
            violated_ppe.add("vest")
        elif "shoes" in t or "boots" in t or "foot" in t:
            violated_categories.add("shoes")
            violated_ppe.add("shoes")
        elif "mask" in t or "respirator" in t:
            violated_categories.add("mask")
            violated_ppe.add("mask")
        else:
            violated_categories.add("other")

    if violation_count == 0:
        ppe_pct = 100.0
        sop_score = 100.0
        overall = 100.0
    else:
        ppe_pct = max(0.0, 100.0 - len(violated_ppe) * 15.0)
        sop_score = max(0.0, 100.0 - len(violated_categories) * 10.0)
        overall = max(0.0, round(100.0 - len(violated_categories) * 8.0 - max_risk * 0.4, 1))

    html_parts.append(f"<div class='score-box'><div class='score-label'>Overall Safety</div><div class='score-val'>{overall}</div></div>")
    html_parts.append(f"<div class='score-box'><div class='score-label'>PPE Compliance</div><div class='score-val'>{ppe_pct}%</div></div>")
    html_parts.append(f"<div class='score-box'><div class='score-label'>SOP Compliance</div><div class='score-val'>{sop_score}</div></div>")
    html_parts.append(f"<div class='score-box'><div class='score-label'>Incident Risk</div><div class='score-val'>{max_risk:.0f}</div></div>")
    html_parts.append("</div>")
    
    # Executive Summary
    html_parts.append("<h2>Executive Summary</h2>")
    html_parts.append("<div class='section'>")
    if max_risk > 80:
        html_parts.append(f"<p><strong style='color: #dc2626;'>[CRITICAL RISK]:</strong> Risk score is {max_risk:.0f}/100, indicating severe safety concerns requiring immediate action.</p>")
    elif max_risk > 50:
        html_parts.append(f"<p><strong style='color: #f59e0b;'>[HIGH RISK]:</strong> Risk score is {max_risk:.0f}/100, indicating significant safety issues.</p>")
    else:
        html_parts.append(f"<p><strong style='color: #10b981;'>[MANAGEABLE RISK]:</strong> Risk score is {max_risk:.0f}/100.</p>")
    html_parts.append(f"<p>Analyzed {len(videos)} video(s), detected {violation_count} safety violation(s) and {evidence_count} evidence record(s).</p>")
    html_parts.append("</div>")
    
    # Risk Analysis
    html_parts.append("<h2>Risk Analysis</h2>")
    if risks:
        for risk in risks[:3]:
            risk_score = float(risk.get("score") or 0)
            severity_class = "critical" if risk_score > 80 else "high" if risk_score > 50 else "medium"
            details = risk.get("details") or {}
            html_parts.append(f"<div class='section {severity_class}'>")
            html_parts.append(f"<p><strong>Risk Score: {risk_score:.0f}/100</strong></p>")
            html_parts.append(f"<p><strong>Reasoning:</strong> {details.get('reasoning', 'N/A')}</p>")
            evidence_val = _coerce_evidence_val(details.get('evidence'))
            html_parts.append(f"<p><strong>Evidence:</strong> {evidence_val}</p>")
            related = details.get('related_sop_rules') or details.get('related_sops', [])
            if isinstance(related, list):
                related_str = ', '.join(str(r) for r in related)
            else:
                related_str = str(related)
            if related_str:
                html_parts.append(f"<p><strong>Related SOPs:</strong> {related_str}</p>")
            conf = details.get('confidence') or 0
            html_parts.append(f"<p><strong>Confidence:</strong> {float(conf) * 100:.0f}%</p>")
            html_parts.append("</div>")
    else:
        html_parts.append("<p>No risk assessments available.</p>")
    
    # Violations table
    html_parts.append("<h2>Safety Violations</h2>")
    filtered_viols = []
    for v in violations:
        v_meta = v.get("metadata") or {}
        if isinstance(v_meta, str):
            try:
                v_meta = json.loads(v_meta)
            except Exception:
                v_meta = {}
        is_gap = v_meta.get("undetermined") or v_meta.get("source") == "sop_gap"
        if not is_gap:
            filtered_viols.append((v, v_meta))

    if filtered_viols:
        html_parts.append("<table>")
        html_parts.append("<tr><th>Type</th><th>Timestamp</th><th>Frame</th><th>Duration</th><th>Confidence</th></tr>")
        for v, v_meta in filtered_viols[:20]:
            ts_display = f"{float(v.get('timestamp') or 0):.2f}s"
            conf_display = f"{float(v.get('confidence') or 0) * 100:.0f}%"
            frame_display = str(v_meta.get("frame_start") or "")
            dur_display = f"{float(v_meta.get('duration_seconds')):.1f}s" if v_meta.get("duration_seconds") is not None else "N/A"
            
            html_parts.append(f"""
            <tr>
                <td>{v.get('violation_type', 'Unknown')}</td>
                <td>{ts_display}</td>
                <td>{frame_display}</td>
                <td>{dur_display}</td>
                <td>{conf_display}</td>
            </tr>
            """)
        if len(filtered_viols) > 20:
            html_parts.append(f"<tr><td colspan='5'><em>... and {len(filtered_viols)-20} more violations</em></td></tr>")
        html_parts.append("</table>")
    else:
        html_parts.append("<p>No violations recorded.</p>")
    
    # Visual Evidence
    html_parts.append("<h2>Visual Evidence</h2>")
    evidence_with_images = [e for e in evidence if e.get("annotated_screenshot_url") or e.get("screenshot_url")]
    if evidence_with_images:
        html_parts.append("<table>")
        html_parts.append("<tr><th>Frame</th><th>Timestamp</th><th>Violation</th><th>Screenshot</th></tr>")
        for ev in evidence_with_images[:10]:
            img_url = ev.get("annotated_screenshot_url") or ev.get("screenshot_url")
            ts_display = f"{float(ev.get('timestamp') or 0):.2f}s"
            html_parts.append(f"""
            <tr>
                <td>Frame #{ev.get('frame_num', 'N/A')}</td>
                <td>{ts_display}</td>
                <td>{ev.get('detection_label', 'Unknown')}</td>
                <td><img src='{img_url}' style='max-width: 240px; border: 1px solid #ccc; border-radius: 4px;' /></td>
            </tr>
            """)
        html_parts.append("</table>")
    else:
        html_parts.append("<p>No visual evidence available with screenshots</p>")
    
    # SOP Compliance
    html_parts.append("<h2>SOP Compliance</h2>")
    sop_sections = {}
    for ev in evidence:
        s = ev.get('sop_section')
        if s:
            sop_sections[s] = sop_sections.get(s, 0) + 1
    if sop_sections:
        for section, count in sorted(sop_sections.items(), key=lambda x: -x[1]):
            html_parts.append(f"<div class='section'>")
            html_parts.append(f"<p><strong>{section}:</strong> {count} violation(s)</p>")
            html_parts.append("</div>")
    else:
        html_parts.append("<p>No SOP violations recorded.</p>")
    
    # Historical Trends
    html_parts.append("<h2>Historical Trend Analysis</h2>")
    
    if analytics.get("monthly_violations"):
        html_parts.append("<h3>Violation Trends by Type</h3>")
        for v in analytics["monthly_violations"][:5]:
            html_parts.append(f"<h4>{v.get('violation_type')}</h4><ul>")
            for m in v.get("monthly_trend", []):
                html_parts.append(f"<li>{m.get('month')}: {m.get('count')} incident(s)</li>")
            html_parts.append("</ul>")

    if analytics.get("risk_trend"):
        html_parts.append("<h3>Risk Score Trend</h3><ul>")
        for r in analytics["risk_trend"]:
            html_parts.append(f"<li>{r.get('period')}: {r.get('avg_risk_score')}/100 (from {r.get('assessments',1)} assessment(s))</li>")
        html_parts.append("</ul>")

    if analytics.get("ppe_trend"):
        html_parts.append("<h3>PPE Compliance Trend</h3><ul>")
        for p in analytics["ppe_trend"]:
            html_parts.append(f"<li>{p.get('period')}: {p.get('ppe_compliance_pct')}% compliant ({p.get('ppe_violations',0)} violations / {p.get('total_violations',0)} total)</li>")
        html_parts.append("</ul>")

    sop_trend = analytics.get("sop_trend")
    if sop_trend and isinstance(sop_trend, dict) and sop_trend:
        html_parts.append("<h3>SOP Violation Trend</h3>")
        for sop, trend in list(sop_trend.items())[:5]:
            html_parts.append(f"<h4>{sop}</h4><ul>")
            for m in trend:
                html_parts.append(f"<li>{m.get('period')}: {m.get('violation_count')} violation(s)</li>")
            html_parts.append("</ul>")

    te = analytics.get("training_effectiveness")
    if te and isinstance(te, dict) and not te.get("status"):
        html_parts.append("<h3>Training Effectiveness</h3><ul>")
        for module, eff in te.items():
            html_parts.append(f"<li><strong>{module}:</strong> {eff.get('reduction_percent')}% reduction (Before: {eff.get('violations_before')}, After: {eff.get('violations_after')})</li>")
        html_parts.append("</ul>")
    
    # Incident Predictions
    html_parts.append("<h2>Incident Predictions</h2>")
    if predictions:
        for pred in predictions[:3]:
            prob = float(pred.get("probability") or 0) * 100
            details = pred.get("prediction_details") or {}
            severity_class = "critical" if prob > 70 else "high" if prob > 40 else "medium"
            html_parts.append(f"<div class='section {severity_class}'>")
            html_parts.append(f"<p><strong>{details.get('type', 'Unknown Incident')}</strong> — {prob:.0f}% Probability</p>")
            html_parts.append(f"<p><strong>Reasoning:</strong> {details.get('reasoning', 'N/A')}</p>")
            ev_val = _coerce_evidence_val(details.get('evidence'))
            html_parts.append(f"<p><strong>Evidence:</strong> {ev_val}</p>")
            html_parts.append("</div>")
    else:
        html_parts.append("<p>No incident predictions available.</p>")
    
    # Training Recommendations
    html_parts.append("<h2>Training Recommendations</h2>")
    if trainings:
        for training in trainings:
            priority_class = "critical" if training.get("priority") == "Critical" else "high" if training.get("priority") == "High" else "medium"
            rec = training.get("recommendation_json") or {}
            if isinstance(rec, str):
                try:
                    rec = json.loads(rec)
                except Exception:
                    rec = {"training_title": rec}
            module_val = rec.get("module_name") or rec.get("training_title") or training.get("human_readable_summary") or "N/A"
            reasoning_val = rec.get("reasoning") or rec.get("recommended_action") or training.get("explanation") or "N/A"
            
            html_parts.append(f"<div class='section {priority_class}'>")
            html_parts.append(f"<p><strong>[{training.get('priority')}]</strong> {training.get('human_readable_summary', 'Training Module')}</p>")
            html_parts.append(f"<p><strong>Module:</strong> {module_val}</p>")
            html_parts.append(f"<p><strong>Reasoning:</strong> {reasoning_val}</p>")
            related_sops = rec.get('related_sop_rules') or rec.get('related_sops', [])
            if isinstance(related_sops, list) and related_sops:
                html_parts.append(f"<p><strong>Related SOPs:</strong> {', '.join(str(s) for s in related_sops)}</p>")
            elif rec.get('violation_trigger'):
                html_parts.append(f"<p><strong>Related SOPs:</strong> {rec.get('violation_trigger')}</p>")
            html_parts.append("</div>")
    else:
        html_parts.append("<p>No training recommendations at this time.</p>")
    
    # Evidence Gallery removed per request
    pass
    
    html_parts.append("""
    </body>
    </html>
    """)
    
    return "".join(html_parts)


def _html_to_pdf_bytes(html_content: str) -> bytes:
    """Convert HTML to PDF bytes using reportlab fallback or weasyprint."""
    # Try weasyprint first (best quality)
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes
    except Exception:
        pass
    
    # Try pdfkit
    try:
        import pdfkit
        pdf_bytes = pdfkit.from_string(html_content, False)
        return pdf_bytes
    except Exception:
        pass
    
    # Fallback: generate a simple PDF with reportlab
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        import re
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                                rightMargin=0.75*inch, leftMargin=0.75*inch,
                                topMargin=0.75*inch, bottomMargin=0.75*inch)
        
        styles = getSampleStyleSheet()
        story = []
        
        # Strip HTML tags for reportlab
        text = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL)
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        # Convert some tags
        text = re.sub(r'<h1[^>]*>(.*?)</h1>', r'\n### \1 ###\n', text, flags=re.DOTALL)
        text = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1 ##\n', text, flags=re.DOTALL)
        text = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n# \1 #\n', text, flags=re.DOTALL)
        text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'\1', text, flags=re.DOTALL)
        text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n', text, flags=re.DOTALL)
        text = re.sub(r'<li[^>]*>(.*?)</li>', r'• \1\n', text, flags=re.DOTALL)
        text = re.sub(r'<td[^>]*>(.*?)</td>', r'\1 | ', text, flags=re.DOTALL)
        text = re.sub(r'<tr[^>]*>', '\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&nbsp;', ' ', text)
        
        # Ensure all characters are ASCII-compatible to prevent ReportLab font encoding crashes on Windows
        text = text.encode('ascii', 'ignore').decode('ascii')
        
        h1_style = ParagraphStyle('h1', parent=styles['Heading1'], fontSize=16, spaceAfter=12)
        h2_style = ParagraphStyle('h2', parent=styles['Heading2'], fontSize=13, spaceAfter=8)
        body_style = ParagraphStyle('body', parent=styles['Normal'], fontSize=10, spaceAfter=4)
        
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                story.append(Spacer(1, 4))
                continue
            if line.startswith('### ') and line.endswith(' ###'):
                story.append(Paragraph(line[4:-4], h1_style))
            elif line.startswith('## ') and line.endswith(' ##'):
                story.append(Paragraph(line[3:-3], h2_style))
            elif line.startswith('# ') and line.endswith(' #'):
                story.append(Paragraph(line[2:-2], h2_style))
            else:
                try:
                    story.append(Paragraph(line, body_style))
                except Exception:
                    story.append(Paragraph(line.encode('ascii', 'replace').decode(), body_style))
        
        doc.build(story)
        return buffer.getvalue()
    except Exception as e:
        logger.error(f"All PDF generation methods failed: {e}")
        # Last resort: return a minimal PDF
        minimal_pdf = (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
            b"/Contents 4 0 R/Resources<</Font<</F1<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>>>>>>>endobj\n"
            b"4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 100 700 Td (Safety Report) Tj ET\nendstream\nendobj\n"
            b"xref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n"
            b"0000000115 00000 n\n0000000274 00000 n\n\ntrailer<</Size 5/Root 1 0 R>>\nstartxref\n366\n%%EOF"
        )
        return minimal_pdf


@router.get("/")
def get_reports(project_id: str, user_id: str):
    """Retrieve all reports for a project."""
    reports = supabase.table("generated_reports").select("*").eq("project_id", project_id).eq("user_id", user_id).order("created_at", desc=True).execute()
    return {
        "status": "success",
        "reports": reports.data or [],
    }


@router.post("/generate")
def generate_report(request: ReportRequest):
    """Generate a comprehensive safety report for a project and return HTML + PDF bytes."""
    try:
        data = _fetch_project_data(request.project_id, request.user_id)
        html_content = _generate_report_html(data)
        
        # Also generate PDF bytes
        pdf_bytes = None
        try:
            pdf_bytes = _html_to_pdf_bytes(html_content)
        except Exception as pdf_err:
            logger.warning(f"PDF byte generation failed: {pdf_err}")
        
        report_name = f"Safety-Report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
        
        try:
            report_res = supabase.table("generated_reports").insert({
                "project_id": request.project_id,
                "user_id": request.user_id,
                "report_url": f"/reports/{report_name}",
                "type": "safety_analysis_html",
            }).execute()
            report_id = report_res.data[0]["id"] if report_res.data else None
        except Exception as db_err:
            logger.warning(f"Failed to save report record: {db_err}")
            report_id = None
        
        import base64
        pdf_b64 = base64.b64encode(pdf_bytes).decode() if pdf_bytes else None
        
        return {
            "status": "success",
            "message": "Report generated successfully",
            "report_html": html_content,
            "report_pdf_b64": pdf_b64,
            "report_id": report_id,
        }
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return {
            "status": "error",
            "message": f"Report generation failed: {str(e)}",
        }
