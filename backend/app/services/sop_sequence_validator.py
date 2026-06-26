"""
SOP Sequence Validator - checks whether observed actions follow the required procedure sequence.
Generates procedural sequence violations when out-of-order steps are detected.
"""
import logging

logger = logging.getLogger(__name__)


def validate_procedure_sequence(
    required_sequence: list,
    observed_events: list,
    fps: float = 30.0
) -> list:
    """
    Check whether observed events follow the SOP required sequence.
    required_sequence: ordered list of required steps (strings) from SOP
    observed_events: list of dicts with {label, frame_num, timestamp, confidence}
    Returns list of sequence violation dicts.
    """
    if not required_sequence or not observed_events:
        return []

    violations = []
    # Map each observed event to the closest required step by keyword
    step_timestamps = {}  # step_index -> first observed timestamp
    for event in observed_events:
        label = event.get("label", "").lower()
        for i, step in enumerate(required_sequence):
            step_lower = step.lower()
            keywords = [w for w in step_lower.split() if len(w) > 3]
            if any(kw in label for kw in keywords):
                if i not in step_timestamps:
                    step_timestamps[i] = event.get("timestamp", event.get("frame_num", 0) / fps)
                break

    # Check ordering: later steps should not appear before earlier required steps
    observed_steps = sorted(step_timestamps.items(), key=lambda x: x[1])
    for idx, (step_i, ts_i) in enumerate(observed_steps):
        for step_j, ts_j in observed_steps[idx+1:]:
            if step_j < step_i:
                # Out of order
                violations.append({
                    "violation_type": f"Procedure Sequence Violation: Step {step_j+1} before Step {step_i+1}",
                    "description": (
                        f"SOP requires '{required_sequence[step_j]}' (step {step_j+1}) "
                        f"BEFORE '{required_sequence[step_i]}' (step {step_i+1}), "
                        f"but sequence was reversed."
                    ),
                    "step_expected": required_sequence[step_j],
                    "step_observed_early": required_sequence[step_i],
                    "timestamp": ts_j,
                    "confidence": 0.70,
                    "source": "sequence_validation",
                    "sop_clause": f"Required sequence: {' → '.join(required_sequence[:step_j+2])}",
                })

    return violations
