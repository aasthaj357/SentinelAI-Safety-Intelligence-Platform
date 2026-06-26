import logging

logger = logging.getLogger(__name__)

# Map canonical PPE names to violation label variants
PPE_VIOLATION_VARIANTS = {
    "helmet":  ["no-helmet", "no_helmet", "missing helmet", "without helmet", "no-hardhat", "no_hardhat"],
    "gloves":  ["no-glove", "no_glove", "missing gloves", "without gloves", "no-gloves"],
    "goggles": ["no-goggle", "no_goggle", "missing goggles", "no-glasses", "no_glasses", "missing eye protection"],
    "vest":    ["no-vest", "no_vest", "missing vest", "no-hi-vis", "missing safety vest"],
    "shoes":   ["no-shoes", "no_shoes", "missing safety shoes", "no-boots"],
    "mask":    ["no-mask", "no_mask", "missing mask", "no-respirator"],
}


def _ppe_required(violation_type: str, ppe_reqs: list) -> bool:
    """Check if a detected violation corresponds to a required PPE item from SOP."""
    vt = violation_type.lower()
    if not ppe_reqs:
        # No SOP loaded — accept any explicit PPE violation label
        return (
            vt.startswith("no-") or vt.startswith("no_") or "missing" in vt or "without" in vt
        )
    for req in ppe_reqs:
        req_lower = req.lower()
        # Direct match
        if req_lower in vt:
            return True
        # Check variants
        variants = PPE_VIOLATION_VARIANTS.get(req_lower, [])
        if any(v in vt for v in variants):
            return True
        # Reverse: bare PPE name in violation type
        bare = vt.replace("no-", "").replace("no_", "").replace("missing", "").replace("without", "").strip()
        if req_lower in bare:
            return True
    return False


def _generate_missing_ppe_findings(ppe_reqs: list, observed_ppe: set, frame_num: int = None) -> list:
    """
    Compare SOP-required PPE against detected PPE. Generate findings for every missing item.
    observed_ppe: set of canonical PPE names that were POSITIVELY detected.
    """
    findings = []
    for req in ppe_reqs:
        req_lower = req.lower()
        if req_lower not in observed_ppe:
            findings.append({
                "frame_num": frame_num,
                "rule": f"PPE Requirement: {req} (SOP-required)",
                "observation": f"Worker observed without required {req}",
                "result": "Violation",
                "violation_type": f"Missing {req}",
                "source": "sop_ppe_comparison",
                "sop_clause": f"SOP requires: {req}",
            })
    return findings


POSITIVE_PPE_CLASSES = {
    "helmet", "hardhat", "hard-hat", "safety-helmet",
    "vest", "safety-vest", "hi-vis",
    "gloves", "safety-gloves",
    "goggles", "safety-goggles", "safety-glasses",
    "safety-shoes", "boots",
    "mask", "face-shield",
}

PPE_CANONICAL_MAP = {
    "helmet": ["helmet", "hardhat", "hard-hat", "safety-helmet"],
    "vest": ["vest", "safety-vest", "hi-vis"],
    "gloves": ["gloves", "safety-gloves"],
    "goggles": ["goggles", "safety-goggles", "safety-glasses", "face-shield"],
    "shoes": ["safety-shoes", "boots"],
    "mask": ["mask", "face-mask"],
}


def _normalize_to_canonical(class_name: str) -> str | None:
    """Convert a detected class name to its canonical PPE name."""
    cl = class_name.lower()
    for canon, variants in PPE_CANONICAL_MAP.items():
        if any(v in cl for v in variants):
            return canon
    return None


class ComplianceService:
    def audit(self, observations: list, sop_rules: dict) -> list:
        """
        Compare observations against structured SOP rules.
        Pipeline:
          1. Collect positively-detected PPE from observations
          2. Compare against SOP-required PPE → generate Missing PPE findings
          3. Validate roboflow PPE violation detections against SOP requirements
          4. Pass through procedural violations unchanged
        """
        findings = []
        ppe_reqs = [p.lower() for p in sop_rules.get("ppe_requirements", [])]

        # Collect positively detected PPE classes
        observed_ppe = set()
        for obs in observations:
            if obs.get("type") == "general_object":
                cn = obs.get("class_name", "")
                canon = _normalize_to_canonical(cn)
                if canon:
                    observed_ppe.add(canon)
            elif obs.get("type") == "ppe_violation":
                # A positive PPE detection from roboflow that is NOT a violation class
                vt = obs.get("violation_type", "").lower()
                if not (vt.startswith("no-") or vt.startswith("no_") or "missing" in vt or "without" in vt):
                    canon = _normalize_to_canonical(vt)
                    if canon:
                        observed_ppe.add(canon)

        # Generate findings for SOP-required PPE not detected
        if ppe_reqs:
            first_frame = next(
                (obs.get("frame_num") for obs in observations if obs.get("frame_num")),
                None
            )
            missing_findings = _generate_missing_ppe_findings(ppe_reqs, observed_ppe, first_frame)
            findings.extend(missing_findings)

        # Process explicit PPE violation detections (from Roboflow)
        for obs in observations:
            obs_type = obs.get("type", "")
            if obs_type == "ppe_violation":
                violation_type = obs.get("violation_type", "").lower()
                # Only count if this PPE type is SOP-required, or if SOP is empty
                if _ppe_required(violation_type, ppe_reqs):
                    # Avoid double-counting already added missing PPE
                    duplicate = any(
                        violation_type in f.get("violation_type", "").lower()
                        for f in findings
                    )
                    if not duplicate:
                        findings.append({
                            "frame_num": obs.get("frame_num"),
                            "rule": f"PPE Requirement: {violation_type}",
                            "observation": f"Worker observed with {violation_type}",
                            "result": "Violation",
                            "violation_type": violation_type,
                            "source": "roboflow_detection",
                            "sop_clause": f"SOP requires: {violation_type.replace('no-','').replace('no_','')}",
                        })

            elif obs_type == "procedural_violation":
                vtype = obs.get("violation_type", "Procedural Violation")
                findings.append({
                    "frame_num": obs.get("frame_num"),
                    "rule": f"Procedural Violation: {vtype}",
                    "observation": vtype,
                    "result": "Violation",
                    "source": obs.get("source", "procedural_reasoning"),
                    "why_detected": obs.get("why_detected", ""),
                    "evidence_basis": obs.get("evidence_basis", ""),
                    "sop_clause": obs.get("sop_hint", ""),
                })

            elif obs_type == "unsafe_machinery":
                findings.append({
                    "frame_num": obs.get("frame_num"),
                    "rule": "Machinery Interaction",
                    "observation": obs.get("description"),
                    "result": "Violation",
                    "source": "yolo_detection",
                })

        return findings


compliance_service = ComplianceService()


def get_compliance_service():
    return compliance_service
