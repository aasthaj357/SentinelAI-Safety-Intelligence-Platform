import json
from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

# Task-specific hazard libraries for automotive maintenance tasks
TASK_HAZARDS = {
    "brake_repair": [
        "jack stands not visible or improperly placed",
        "wheel chocks absent",
        "brake dust inhalation risk (asbestos or non-asbestos)",
        "caliper not supported during pad replacement",
        "rotor heat burn risk",
        "fasteners not torqued to spec",
        "hydraulic brake line under pressure",
        "brake fluid skin/eye contact hazard",
    ],
    "oil_change": [
        "hot oil drain risk (burn hazard)",
        "drain plug not fully secured",
        "oil spill slip hazard on floor",
        "oil filter over- or under-tightened",
        "refill level not verified post-change",
        "used oil disposal not following environmental protocol",
    ],
    "battery": [
        "battery not isolated before work",
        "arc flash risk from short circuit",
        "acid spill (electrolyte) hazard",
        "tools bridging battery terminals (short circuit)",
        "hydrogen gas accumulation in enclosed space",
    ],
    "lifting": [
        "vehicle not on approved lift points",
        "lift stability not confirmed before undercarriage work",
        "pinch hazard during lowering",
        "no secondary support (jack stand) while under vehicle",
    ],
    "wheel_work": [
        "lug nuts not torqued to manufacturer spec",
        "vehicle not restrained during wheel removal",
        "impact tool torque not verified with torque wrench",
        "wheel dropped on foot risk",
    ],
    "general": [
        "PPE (helmet, gloves, safety glasses) not worn",
        "work area not clear of slip/trip hazards",
        "fire extinguisher not accessible",
        "proper lifting technique not used",
    ],
}

TASK_KEYWORDS = {
    "brake_repair": ["brake", "caliper", "rotor", "pad", "drum", "brake fluid", "bleed"],
    "oil_change": ["oil", "drain plug", "filter", "engine oil", "oil change", "lubricant"],
    "battery": ["battery", "terminal", "electrolyte", "acid", "charging", "jump start"],
    "lifting": ["lift", "jack", "stand", "hoist", "raise vehicle", "undercarriage"],
    "wheel_work": ["wheel", "tyre", "tire", "lug", "rim", "hub"],
}


def infer_task(observations: list, transcript: str = "") -> str:
    """Infer the maintenance task from YOLO observations and transcript."""
    combined = " ".join([
        o.get("class_name", "") for o in observations
    ] + [transcript or ""]).lower()

    scores = {}
    for task, keywords in TASK_KEYWORDS.items():
        scores[task] = sum(1 for kw in keywords if kw in combined)

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


REC_MAP = {
    "helmet":   "Provide hard hats and enforce mandatory head protection — retrain workers on TBI risk.",
    "glove":    "Enforce mandatory glove policy before engine/chemical handling — post glove stations at entry.",
    "goggle":   "Require safety goggles/glasses in all tool-use and chemical zones — post eye hazard signage.",
    "vest":     "Enforce hi-vis vest requirement in all vehicle movement areas.",
    "mask":     "Require respirator use in dust/fume/chemical areas — conduct fit testing.",
    "shoes":    "Enforce steel-toed footwear — mark heavy-drop zones.",
    "jack stand": "Enforce secondary support (jack stands) before any undercarriage work — never use jack alone.",
    "fire":     "Hot work permit required — ensure extinguisher within 5 m — conduct fire drill.",
    "lockout":  "Mandatory LOTO before electrical/mechanical maintenance — verify energy isolation.",
    "battery":  "Battery isolation and arc-flash PPE required for all electrical work.",
    "sequence": "Retrain on correct SOP procedure sequence — implement physical checklist.",
    "proximity": "Establish vehicle exclusion zones — enforce safe distance during vehicle operation.",
}


def _generate_recommendations(dedup_violations: list, findings: list) -> list:
    """Auto-generate specific training recommendations from observed violations."""
    seen = set()
    recs = []
    all_labels = (
        [v.get("violation_type", "") for v in dedup_violations]
        + [f.get("rule", "") for f in findings]
    )
    for label in all_labels:
        label_l = (label or "").lower()
        for key, rec in REC_MAP.items():
            if key in label_l and key not in seen:
                recs.append(rec)
                seen.add(key)
    if not recs:
        recs = ["Review all SOP requirements and ensure full PPE compliance before commencing work."]
    return recs


class GroqService:
    def generate_structured_report(
        self,
        risk_data: dict,
        predictions: list,
        findings: list,
        communications: list,
        observations: list = None,
        transcript: str = "",
        timeline: list = None,
        dedup_violations: list = None,
    ) -> dict:
        task = infer_task(observations or [], transcript)
        task_hazards = TASK_HAZARDS.get(task, TASK_HAZARDS["general"])
        timeline = timeline or []
        dedup_violations = dedup_violations or []

        # Auto-generate recommendations from violation types (no static templates)
        auto_recs = _generate_recommendations(dedup_violations, findings)

        prompt = f"""
You are an expert Workplace Safety Analyst.

Detected maintenance task: {task.replace('_', ' ').title()}

=== DETECTED VIOLATIONS (deduplicated, from video analysis) ===
{json.dumps(dedup_violations[:20])}

=== COMPLIANCE FINDINGS ===
{json.dumps(findings[:20])}

=== RISK DATA (score: {risk_data.get('score', 0)}) ===
{json.dumps(risk_data.get('details', {}).get('violation_breakdown', [])[:10])}

=== INCIDENT PREDICTIONS ===
{json.dumps(predictions)}

=== VIOLATION TIMELINE ===
{json.dumps(timeline[:15])}

=== SAFETY COMMUNICATIONS ===
{json.dumps(communications)}

INSTRUCTIONS:
- ALL analysis must be grounded in the violations and timeline above
- Do NOT invent hazards or violations not in the data
- training_recommendations must be specific to each detected violation type
- If no violations exist, state compliance clearly
- ppe_compliance_analysis: name each missing PPE item with worker ID and duration
- incident_prediction_analysis: reference specific evidence (frame, duration, worker)

Return ONLY valid JSON:
{{
    "detected_task": "{task}",
    "executive_summary": "Evidence-based summary of safety status...",
    "task_specific_hazards": ["hazards with actual evidence only"],
    "violation_summary": "Summary naming each violation, worker, duration...",
    "ppe_compliance_analysis": "Which PPE was missing, which worker, for how long...",
    "sop_compliance_analysis": "SOP compliance status based on findings...",
    "risk_assessment_summary": "Score {risk_data.get('score', 0)}/100 with explanation of multipliers...",
    "incident_prediction_analysis": "Predictions grounded in specific violations and durations...",
    "training_recommendations": {json.dumps(auto_recs)}
}}
"""
        try:
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a reporting AI. Output ONLY raw valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.2
            )
            content = response.choices[0].message.content
            content = content.replace("```json", "").replace("```", "").strip()
            report_data = json.loads(content)
            # Always ensure auto_recs are present
            if not report_data.get("training_recommendations"):
                report_data["training_recommendations"] = auto_recs
            return report_data
        except Exception as e:
            print(f"Error generating Groq report: {e}")
            return {
                "detected_task": task,
                "executive_summary": f"Risk score: {risk_data.get('score', 0)}/100. {len(dedup_violations)} violation(s) detected.",
                "task_specific_hazards": task_hazards[:4],
                "violation_summary": f"{len(dedup_violations)} deduplicated violations. {len(findings)} compliance findings.",
                "ppe_compliance_analysis": f"PPE violations: {[v.get('violation_type') for v in dedup_violations[:5]]}",
                "sop_compliance_analysis": f"{len(findings)} findings vs SOP requirements.",
                "risk_assessment_summary": f"Risk score {risk_data.get('score', 0)}/100 ({risk_data.get('level', 'Unknown')}).",
                "incident_prediction_analysis": f"{len(predictions)} incident prediction(s).",
                "training_recommendations": auto_recs,
            }

    def get_chatbot_response(self, prompt: str) -> str:
        """Get response from Safety Officer Chatbot."""
        return "Chatbot response based on Groq"


groq_service = GroqService()


def get_groq_service():
    return groq_service
