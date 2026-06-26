import os
import io
import re
import uuid
import logging

logger = logging.getLogger(__name__)


class ReportService:
    def generate_pdf_report(self, structured_report: dict, project_id: str) -> str:
        """
        Generate a downloadable PDF report from the structured Groq data.
        Saves locally to a temporary file, returns the file path.
        Uses reportlab (always available) instead of fpdf2.
        """
        os.makedirs("tmp", exist_ok=True)
        file_path = f"tmp/report_{uuid.uuid4().hex}.pdf"
        temp_files = []
        
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.units import inch
            from reportlab.lib import colors
            
            doc = SimpleDocTemplate(
                file_path,
                pagesize=letter,
                rightMargin=0.75*inch,
                leftMargin=0.75*inch,
                topMargin=0.75*inch,
                bottomMargin=0.75*inch,
            )
            
            styles = getSampleStyleSheet()
            h1_style = ParagraphStyle('h1', parent=styles['Heading1'], fontSize=16, spaceAfter=12, textColor=colors.HexColor('#1f2937'))
            h2_style = ParagraphStyle('h2', parent=styles['Heading2'], fontSize=13, spaceAfter=8, textColor=colors.HexColor('#374151'))
            body_style = ParagraphStyle('body', parent=styles['Normal'], fontSize=10, spaceAfter=4)
            bullet_style = ParagraphStyle('bullet', parent=styles['Normal'], fontSize=10, spaceAfter=4, leftIndent=20)
            
            story = []

            def safe_para(text, style):
                t = str(text).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
                try:
                    return Paragraph(t, style)
                except Exception:
                    return Paragraph(t.encode('ascii','replace').decode(), style)

            # Title
            story.append(Paragraph("Workplace Safety Intelligence Report", h1_style))
            story.append(Spacer(1, 12))

            # Executive summary section
            sections = [
                ("Executive Summary", "executive_summary"),
                ("Detected Task", "detected_task"),
                ("Violation Summary", "violation_summary"),
                ("PPE Compliance Analysis", "ppe_compliance_analysis"),
                ("SOP Compliance Analysis", "sop_compliance_analysis"),
                ("Risk Assessment Summary", "risk_assessment_summary"),
                ("Incident Prediction Analysis", "incident_prediction_analysis"),
            ]
            for title, key in sections:
                content = structured_report.get(key)
                if not content:
                    continue
                story.append(Paragraph(title, h2_style))
                story.append(safe_para(content, body_style))
                story.append(Spacer(1, 8))

            # Hazards
            hazards = structured_report.get("task_specific_hazards", [])
            if hazards:
                story.append(Paragraph("Task-Specific Hazards", h2_style))
                for h in hazards:
                    story.append(safe_para(f"• {h}", bullet_style))
                story.append(Spacer(1, 8))

            # Risk Score Breakdown
            risk_breakdown = structured_report.get("risk_breakdown") or []
            if not risk_breakdown:
                # Try nested path
                rb = structured_report.get("details", {})
                risk_breakdown = rb.get("violation_breakdown", []) if isinstance(rb, dict) else []
            if risk_breakdown:
                story.append(Paragraph("Risk Score Breakdown", h2_style))
                story.append(safe_para(f"Formula: base_weight × duration_multiplier × confidence_multiplier (capped at 100)", body_style))
                for entry in risk_breakdown[:15]:
                    expl = entry.get("explanation") or (
                        f"+{entry.get('base_weight',0)} × {entry.get('duration_multiplier',1):.2f} × {entry.get('confidence_multiplier',1):.2f} = "
                        f"+{entry.get('adjusted_weight',0):.1f} pts — {entry.get('rule','')} [{entry.get('severity','')}]"
                    )
                    story.append(safe_para(f"  • {expl}", bullet_style))
                story.append(Spacer(1, 8))

            # Violation Timeline
            timeline = structured_report.get("violation_timeline", [])
            if timeline:
                story.append(Paragraph("Violation Timeline", h2_style))
                for ev in timeline[:30]:
                    ts_fmt = ev.get("timestamp_fmt", "--:--")
                    desc = ev.get("description", "")
                    worker = ev.get("worker_id", "")
                    frame = ev.get("frame_start")
                    dur = ev.get("duration_seconds")
                    
                    frame_str = f" | Frame #{frame}" if frame is not None else ""
                    dur_str = f" | Duration: {dur:.1f}s" if dur is not None else ""
                    
                    conf = ev.get("confidence", 0)
                    conf_str = f" ({conf:.0%} conf)" if conf else ""
                    story.append(safe_para(f"  [{ts_fmt}{frame_str}{dur_str}] {desc}{conf_str}", bullet_style))
                story.append(Spacer(1, 8))

            # Worker Summary
            worker_summary = structured_report.get("worker_summary", {})
            if worker_summary:
                story.append(Paragraph("Worker PPE Summary", h2_style))
                for wid, data in worker_summary.items():
                    missing = ', '.join(data.get("ppe_types_missing", [])) or "none"
                    dur = data.get("total_duration", 0)
                    count = len(data.get("violations", []))
                    story.append(safe_para(f"  Worker {wid}: {count} violation(s), missing PPE: {missing}, total exposure: {dur:.1f}s", bullet_style))
                story.append(Spacer(1, 8))

            # Training Recommendations
            recs = structured_report.get("training_recommendations", [])
            if recs:
                story.append(Paragraph("Training Recommendations", h2_style))
                for r in (recs if isinstance(recs, list) else [recs]):
                    if isinstance(r, dict):
                        title = r.get('training_title') or r.get('module_name') or 'Safety Training'
                        action = r.get('recommended_action') or r.get('reasoning') or ''
                        priority = r.get('priority') or 'Medium'
                        story.append(safe_para(f"• [{priority.upper()}] {title} — {action}", bullet_style))
                    else:
                        story.append(safe_para(f"• {r}", bullet_style))
                story.append(Spacer(1, 8))

            # Visual Evidence / screenshots section removed per request
            pass
            
            doc.build(story)
            
            # Cleanup temp files
            for path in temp_files:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass
                        
            return file_path
            
        except Exception as e:
            logger.error(f"PDF generation with reportlab failed: {e}")
            # Create minimal valid PDF
            minimal_pdf = (
                b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
                b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
                b"/Contents 4 0 R/Resources<</Font<</F1<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>>>>>>>endobj\n"
                b"4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 100 700 Td (Safety Report) Tj ET\nendstream\nendobj\n"
                b"xref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n"
                b"0000000115 00000 n\n0000000274 00000 n\n\ntrailer<</Size 5/Root 1 0 R>>\nstartxref\n366\n%%EOF"
            )
            with open(file_path, "wb") as f:
                f.write(minimal_pdf)
            return file_path


report_service = ReportService()

def get_report_service():
    return report_service
