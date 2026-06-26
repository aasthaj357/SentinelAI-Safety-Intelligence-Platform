import logging

logger = logging.getLogger(__name__)

# Deterministic per-violation-type risk weights
# (base_weight, injury_type, severity_label)
VIOLATION_WEIGHTS = {
    "no-helmet":        (25, "Head injury / traumatic brain injury", "critical"),
    "no_helmet":        (25, "Head injury / traumatic brain injury", "critical"),
    "missing helmet":   (25, "Head injury / traumatic brain injury", "critical"),
    "no-hardhat":       (25, "Head injury / traumatic brain injury", "critical"),
    "no-glove":         (20, "Hand laceration / chemical burn", "high"),
    "no_glove":         (20, "Hand laceration / chemical burn", "high"),
    "missing gloves":   (20, "Hand laceration / chemical burn", "high"),
    "no-goggle":        (15, "Eye injury / chemical exposure", "high"),
    "no_goggle":        (15, "Eye injury / chemical exposure", "high"),
    "missing goggles":  (15, "Eye injury / chemical exposure", "high"),
    "no-glasses":       (15, "Eye injury", "high"),
    "no-vest":          (12, "Struck-by / low visibility collision", "medium"),
    "no_vest":          (12, "Struck-by / low visibility collision", "medium"),
    "missing vest":     (12, "Struck-by / low visibility collision", "medium"),
    "no-mask":          (10, "Respiratory / chemical exposure", "medium"),
    "no_mask":          (10, "Respiratory / chemical exposure", "medium"),
    "no-shoes":         (10, "Foot crush / slip injury", "medium"),
    "no_shoes":         (10, "Foot crush / slip injury", "medium"),
    "jack stand":       (20, "Fatal crush injury from vehicle drop", "critical"),
    "vehicle lift":     (20, "Fatal crush injury from vehicle drop", "critical"),
    "proximity hazard": (15, "Worker-vehicle crush / struck-by", "critical"),
    "fire hazard":      (30, "Burns / fire injury", "critical"),
    "battery":          (15, "Arc flash / electrocution / acid burn", "high"),
    "posture":          (10, "Musculoskeletal injury", "medium"),
    "lockout":          (20, "Electrocution / unexpected machine movement", "critical"),
    "tagout":           (20, "Electrocution / unexpected machine movement", "critical"),
    "restricted area":  (25, "Exposure to hazardous operation", "critical"),
    "machinery":        (20, "Entanglement / crush injury", "high"),
    "sequence":         (15, "Procedural accident from incorrect step order", "high"),
}

CATEGORY_WEIGHTS = {
    "ppe": 10,
    "procedural": 15,
    "machinery": 20,
    "restricted": 25,
    "communication": 15,
}

MITIGATION_MAP = {
    "helmet": "Enforce mandatory helmet/hard hat wearing at all times in the work zone.",
    "glove":  "Enforce mandatory glove policy before any engine/chemical handling.",
    "goggle": "Enforce mandatory eye protection in all tool-use and chemical areas.",
    "vest":   "Require hi-vis vests in all vehicle movement areas.",
    "mask":   "Require respirator use in areas with dust, fumes, or chemical exposure.",
    "shoes":  "Enforce steel-toed footwear policy; mark heavy-drop zones.",
    "jack stand": "Secondary support (jack stands) mandatory before undercarriage work; never use jack alone.",
    "fire":   "Hot work permit required; fire extinguisher within reach; evacuate on detection.",
    "lockout": "LOTO procedure mandatory before any electrical or mechanical maintenance.",
    "battery": "Battery isolation and arc-flash PPE required for electrical work.",
    "sequence": "Retrain workers on correct SOP procedure sequence; use checklist.",
    "proximity": "Establish vehicle exclusion zones; enforce safe distance during vehicle operation.",
}


def _match_violation_weight(violation_type: str) -> tuple:
    vt = violation_type.lower() if violation_type else ""
    for key, (weight, injury, severity) in VIOLATION_WEIGHTS.items():
        if key in vt:
            return weight, injury, severity
    if any(k in vt for k in ("helmet", "glove", "goggle", "vest", "ppe", "mask", "shoe", "boot")):
        return CATEGORY_WEIGHTS["ppe"], "PPE-related injury", "medium"
    if any(k in vt for k in ("procedural", "sequence", "step", "procedure")):
        return CATEGORY_WEIGHTS["procedural"], "Procedural accident", "medium"
    if any(k in vt for k in ("machine", "equipment", "tool")):
        return CATEGORY_WEIGHTS["machinery"], "Equipment injury", "high"
    if any(k in vt for k in ("restricted", "zone", "area")):
        return CATEGORY_WEIGHTS["restricted"], "Exposure to hazardous area", "critical"
    return 5, "General safety violation", "low"


def _duration_multiplier(duration_seconds: float | None) -> float:
    """Scale risk by how long the violation persisted."""
    if not duration_seconds:
        return 1.0
    if duration_seconds >= 60:
        return 1.5
    if duration_seconds >= 30:
        return 1.3
    if duration_seconds >= 10:
        return 1.15
    if duration_seconds >= 3:
        return 1.05
    return 1.0


def _confidence_multiplier(confidence: float) -> float:
    """Scale risk by detection confidence."""
    if confidence <= 0:
        return 0.5   # Undetermined — halved
    if confidence >= 0.9:
        return 1.0
    if confidence >= 0.7:
        return 0.95
    if confidence >= 0.5:
        return 0.85
    return 0.75


class RiskService:
    def calculate_risk(
        self,
        project_id: str,
        findings: list,
        communications: list,
        sop_rules: dict = None,
        dedup_violations: list = None
    ) -> dict:
        """
        Deterministic risk scoring:
        score = Σ (base_weight × duration_multiplier × confidence_multiplier)
        capped at 100. Full breakdown per violation.
        """
        sop_rules = sop_rules or {}
        dedup_violations = dedup_violations or []
        score = 0.0
        violation_breakdown = []
        ppe_violations = []
        procedural_violations = []
        communication_violations = []

        # Build a lookup from violation_type → dedup violation for duration/confidence
        dedup_by_type: dict[str, dict] = {}
        for dv in dedup_violations:
            key = (dv.get("violation_type") or "").lower()
            if key not in dedup_by_type:
                dedup_by_type[key] = dv

        for f in findings:
            rule = f.get("rule", "") or ""
            observation = f.get("observation", "") or ""
            source = f.get("source", "")
            full_text = f"{rule} {observation}".lower()

            base_weight, injury_type, severity = _match_violation_weight(full_text)

            # Look up duration + confidence from dedup_violations
            vtype_key = full_text.strip()
            matched_dv = None
            for k, dv in dedup_by_type.items():
                if k in vtype_key or vtype_key in k:
                    matched_dv = dv
                    break

            duration = matched_dv.get("duration_seconds") if matched_dv else None
            confidence = matched_dv.get("confidence", 0.0) if matched_dv else (f.get("confidence") or 0.0)
            worker_id = matched_dv.get("worker_id") if matched_dv else f.get("worker_id")

            dur_mult = _duration_multiplier(duration)
            conf_mult = _confidence_multiplier(confidence)
            adjusted = base_weight * dur_mult * conf_mult

            score += adjusted

            entry = {
                "rule": rule,
                "observation": observation,
                "base_weight": base_weight,
                "duration_seconds": duration,
                "duration_multiplier": round(dur_mult, 3),
                "confidence": round(confidence, 3),
                "confidence_multiplier": round(conf_mult, 3),
                "adjusted_weight": round(adjusted, 2),
                "injury_type": injury_type,
                "severity": severity,
                "source": source,
                "worker_id": worker_id,
                "explanation": (
                    f"+{base_weight} × {dur_mult:.2f}(dur) × {conf_mult:.2f}(conf) = "
                    f"+{adjusted:.1f} pts — {rule} — risk: {injury_type} [{severity}]"
                    + (f" — Worker {worker_id}" if worker_id else "")
                    + (f" — duration {duration:.1f}s" if duration else "")
                ),
            }
            violation_breakdown.append(entry)

            if any(k in full_text for k in ("helmet", "glove", "goggle", "vest", "mask", "shoe", "ppe")):
                ppe_violations.append(entry)
            elif source in ("sop_procedural_reasoning", "procedural_reasoning", "sequence_validation") or "procedural" in rule.lower():
                procedural_violations.append(entry)

        for c in communications:
            if c.get("type") == "warning" and c.get("severity") == "high":
                w = CATEGORY_WEIGHTS["communication"]
                score += w
                entry = {
                    "rule": "Ignored Safety Warning",
                    "observation": c.get("content", "High-severity warning"),
                    "base_weight": w,
                    "duration_seconds": None,
                    "duration_multiplier": 1.0,
                    "confidence": 0.8,
                    "confidence_multiplier": 0.95,
                    "adjusted_weight": w * 0.95,
                    "injury_type": "General workplace accident",
                    "severity": "high",
                    "explanation": f"+{w} pts: High-severity safety warning in audio",
                }
                violation_breakdown.append(entry)
                communication_violations.append(entry)

        score = min(score, 100.0)

        level = "Low"
        if score > 75:
            level = "Critical"
        elif score > 50:
            level = "High"
        elif score > 25:
            level = "Medium"

        reasoning_lines = [
            f"Risk Score: {score:.1f}/100 ({level})",
            f"Formula: Σ(base_weight × duration_multiplier × confidence_multiplier)",
            f"Total findings: {len(findings)}",
        ]
        for entry in violation_breakdown[:12]:
            reasoning_lines.append(f"  • {entry['explanation']}")
        if len(violation_breakdown) > 12:
            reasoning_lines.append(f"  ... and {len(violation_breakdown) - 12} more")

        details = {
            "ppe_violations_count": len(ppe_violations),
            "procedural_violations_count": len(procedural_violations),
            "ignored_warnings_count": len(communication_violations),
            "violation_breakdown": violation_breakdown,
            "detailed_violations": violation_breakdown,
            "reasoning": "\n".join(reasoning_lines),
            "score_formula": "Σ(base_weight × duration_mult × confidence_mult), capped at 100",
            "evidence": [e["explanation"] for e in violation_breakdown[:6]],
            "confidence": 0.90,
        }

        return {"score": round(score, 1), "level": level, "details": details}

    def predict_incidents(self, project_id: str, risk_data: dict, sop_rules: dict = None) -> list:
        sop_rules = sop_rules or {}
        predictions = []
        detailed_violations = risk_data.get("details", {}).get("detailed_violations", [])

        def _viols_of(*keywords):
            return [v for v in detailed_violations
                    if any(k in (v.get("rule") or "").lower() for k in keywords)]

        def _max_duration(viols):
            durs = [v.get("duration_seconds") for v in viols if v.get("duration_seconds")]
            return max(durs) if durs else None

        def _avg_conf(viols):
            confs = [v.get("confidence") for v in viols if v.get("confidence")]
            return sum(confs) / len(confs) if confs else 0.0

        # Helmet
        hv = _viols_of("helmet", "hardhat")
        if hv:
            dur = _max_duration(hv)
            conf = _avg_conf(hv)
            dur_str = f" for {dur:.0f}s" if dur else ""
            # Probability increases with duration
            prob = min(0.97, 0.65 + len(hv)*0.05 + (dur or 0)*0.002)
            predictions.append({
                "predicted_incident": "Traumatic Head Injury (TBI or skull fracture)",
                "confidence": round(prob, 2),
                "reasoning": f"{len(hv)} helmet violation(s){dur_str}. Worker head unprotected against falling objects/impacts.",
                "detected_violation": hv[0]["rule"],
                "evidence_frame": hv[0].get("worker_id"),
                "sop_clause": "PPE Requirements: Safety helmet mandatory",
                "mitigation": self.get_mitigation("helmet"),
                "duration_seconds": dur,
            })

        # Gloves
        gv = _viols_of("glove")
        if gv:
            dur = _max_duration(gv)
            prob = min(0.92, 0.55 + len(gv)*0.05 + (dur or 0)*0.001)
            predictions.append({
                "predicted_incident": "Hand Laceration or Chemical Burn",
                "confidence": round(prob, 2),
                "reasoning": f"{len(gv)} glove violation(s). Worker hands unprotected.",
                "detected_violation": gv[0]["rule"],
                "sop_clause": "PPE Requirements: Safety gloves mandatory",
                "mitigation": self.get_mitigation("glove"),
                "duration_seconds": _max_duration(gv),
            })

        # Goggles
        ev = _viols_of("goggle", "glass", "eye")
        if ev:
            dur = _max_duration(ev)
            prob = min(0.90, 0.55 + len(ev)*0.05 + (dur or 0)*0.001)
            predictions.append({
                "predicted_incident": "Eye Injury or Chemical Eye Exposure",
                "confidence": round(prob, 2),
                "reasoning": f"{len(ev)} eye protection violation(s). Eyes exposed to debris/chemicals.",
                "detected_violation": ev[0]["rule"],
                "sop_clause": "PPE Requirements: Safety goggles mandatory",
                "mitigation": self.get_mitigation("goggle"),
                "duration_seconds": _max_duration(ev),
            })

        # Vehicle/crush
        vv = _viols_of("jack stand", "vehicle lift", "proximity", "crush")
        if vv:
            predictions.append({
                "predicted_incident": "Vehicle Crush Injury (potentially fatal)",
                "confidence": 0.90,
                "reasoning": f"{len(vv)} vehicle safety violation(s). Inadequate support or unsafe proximity.",
                "detected_violation": vv[0]["rule"],
                "sop_clause": "Required Procedures: Vehicle must be secured before undercarriage work",
                "mitigation": self.get_mitigation("jack stand"),
                "duration_seconds": _max_duration(vv),
            })

        # Fire
        fv = _viols_of("fire")
        if fv:
            predictions.append({
                "predicted_incident": "Fire Injury / Burns",
                "confidence": 0.92,
                "reasoning": "Fire hazard visually detected.",
                "detected_violation": fv[0]["rule"],
                "sop_clause": "Hazards: Open flame is a critical hazard",
                "mitigation": self.get_mitigation("fire"),
                "duration_seconds": None,
            })

        # Sequence
        sv = _viols_of("sequence")
        if sv:
            predictions.append({
                "predicted_incident": "Procedural Accident from Incorrect Step Order",
                "confidence": 0.72,
                "reasoning": f"SOP procedure sequence violated in {len(sv)} instance(s).",
                "detected_violation": sv[0]["rule"],
                "sop_clause": "Required sequence (SOP)",
                "mitigation": self.get_mitigation("sequence"),
                "duration_seconds": None,
            })

        return predictions

    def explain_violation(self, violation_type: str) -> str:
        vt = violation_type.lower() if violation_type else ""
        weight, injury_type, severity = _match_violation_weight(vt)
        return (
            f"Violation: '{violation_type}' — Severity: {severity}. "
            f"Potential injury: {injury_type}. "
            f"Base risk contribution: +{weight} pts (scaled by duration and confidence). "
            f"Immediate corrective action required."
        )

    def get_mitigation(self, violation_type: str) -> str:
        vt = (violation_type or "").lower()
        for key, mit in MITIGATION_MAP.items():
            if key in vt:
                return mit
        return "Review SOP and ensure all required PPE is worn and procedures are followed."

    def calculate_ppe_compliance(self, sop_rules: dict, dedup_violations: list) -> dict:
        required_ppe = [p.lower() for p in sop_rules.get("ppe_requirements", [])]
        if not required_ppe:
            required_ppe = ["helmet", "vest"]
        violated_types = set()
        for v in dedup_violations:
            if v.get("undetermined"):
                continue
            ppe = v.get("ppe_type", "")
            if ppe in required_ppe:
                violated_types.add(ppe)
        total = len(required_ppe)
        violated_count = len(violated_types)
        pct = max(0.0, round(100.0 * (total - violated_count) / total, 1)) if total > 0 else None
        return {
            "required_ppe": required_ppe,
            "violated_ppe": list(violated_types),
            "compliance_pct": pct,
            "compliant": violated_count == 0,
        }


risk_service = RiskService()

def get_risk_service():
    return risk_service
