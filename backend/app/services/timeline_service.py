"""
Timeline Service - generates chronological violation timeline from deduplicated violations.
Each entry has timestamp, worker_id, ppe_type, duration, confidence.
"""
from typing import List, Dict


def build_violation_timeline(deduplicated_violations: list, fps: float = 30.0) -> list:
    """
    Build a sorted chronological timeline from deduplicated violation records.
    Returns list of timeline events with formatted timestamps.
    """
    events = []
    for v in deduplicated_violations:
        if v.get("undetermined"):
            continue
        ts = v.get("timestamp") or (v.get("frame_start", 0) / fps if v.get("frame_start") else 0)
        end_ts = None
        if v.get("frame_end") and fps:
            end_ts = v["frame_end"] / fps
        elif v.get("duration_seconds") and ts is not None:
            end_ts = ts + v["duration_seconds"]

        events.append({
            "timestamp": round(ts, 2),
            "timestamp_fmt": _fmt_ts(ts),
            "end_timestamp": round(end_ts, 2) if end_ts else None,
            "end_timestamp_fmt": _fmt_ts(end_ts) if end_ts else None,
            "worker_id": v.get("worker_id", "W01"),
            "violation_type": v.get("violation_type", ""),
            "ppe_type": v.get("ppe_type", ""),
            "frame_start": v.get("frame_start"),
            "frame_end": v.get("frame_end"),
            "duration_seconds": v.get("duration_seconds"),
            "confidence": v.get("confidence", 0.0),
            "source": v.get("source", ""),
            "description": _describe(v),
            "bbox": v.get("bbox", [0, 0, 0, 0]),
        })

    # Sort by timestamp
    events.sort(key=lambda x: x["timestamp"])
    return events


def _fmt_ts(seconds: float) -> str:
    if seconds is None:
        return "--:--"
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02d}:{s:02d}"


def _describe(v: dict) -> str:
    ppe = v.get("ppe_type", v.get("violation_type", "PPE")).title()
    worker = v.get("worker_id", "Worker")
    dur = v.get("duration_seconds")
    conf = v.get("confidence", 0.0)
    if v.get("undetermined"):
        return f"{ppe} — unable to determine (SOP required, no detection)"
    if dur:
        return f"{worker}: {ppe} missing for {dur:.1f}s (confidence {conf:.0%})"
    return f"{worker}: {ppe} missing (confidence {conf:.0%})"
