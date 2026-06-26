"""
Temporal PPE Tracker - implements frame-level consistency and deduplication.
Prevents single-frame flicker from generating violations.
Tracks per-worker PPE state across frames.
Collapses repeated violations into deduplicated records with duration/frame ranges.
"""
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# Minimum consecutive frames a violation must persist to be recorded
VIOLATION_MIN_FRAMES = 3
# Minimum confidence threshold to register a detection
CONFIDENCE_THRESHOLD = 0.45
# IOU threshold for associating detections to same worker across frames
IOU_THRESHOLD = 0.35


def _iou(boxA, boxB):
    """Compute Intersection over Union of two bboxes [x1,y1,x2,y2]."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    inter = max(0, xB - xA) * max(0, yB - yA)
    if inter == 0:
        return 0.0
    areaA = (boxA[2]-boxA[0]) * (boxA[3]-boxA[1])
    areaB = (boxB[2]-boxB[0]) * (boxB[3]-boxB[1])
    return inter / float(areaA + areaB - inter)


class WorkerTracker:
    """
    Assigns persistent worker IDs based on bounding box overlap across frames.
    """
    def __init__(self):
        self.workers = {}   # worker_id -> last_bbox
        self._next_id = 1

    def assign_worker_id(self, bbox: list) -> str:
        best_id = None
        best_iou = 0.0
        for wid, last_bbox in self.workers.items():
            iou = _iou(bbox, last_bbox)
            if iou > best_iou:
                best_iou = iou
                best_id = wid
        if best_iou >= IOU_THRESHOLD and best_id:
            self.workers[best_id] = bbox
            return best_id
        # New worker
        new_id = f"W{self._next_id:02d}"
        self._next_id += 1
        self.workers[new_id] = bbox
        return new_id


class TemporalPPETracker:
    """
    Tracks PPE state per worker across frames.
    Applies temporal smoothing: violation only registered after VIOLATION_MIN_FRAMES.
    Deduplicates: collapses continuous violation runs into single records.
    """
    def __init__(self, fps: float = 30.0, min_frames: int = VIOLATION_MIN_FRAMES):
        self.fps = fps
        self.min_frames = min_frames
        self.worker_tracker = WorkerTracker()
        # worker_id -> ppe_type -> list of (frame_num, confidence, bbox)
        self._ppe_absent: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
        # worker_id -> ppe_type -> list of (frame_num, confidence, bbox)
        self._ppe_present: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
        # Finalized deduplicated violations
        self._violations: list[dict] = []
        # Active violation runs: worker_id -> ppe_type -> start_frame
        self._active_runs: dict[str, dict[str, dict]] = defaultdict(dict)

    def ingest_frame(self, frame_num: int, roboflow_detections: list, roboflow_violations: list, yolo_detections: list):
        """
        Process one frame's detections.
        roboflow_detections: all detections from roboflow (including positive PPE)
        roboflow_violations: explicit absence detections (no-helmet, no-glove, etc.)
        yolo_detections: general YOLO detections (person class used for worker tracking)
        """
        # Assign worker IDs from person detections
        person_detections = [d for d in yolo_detections if d.get("class_name", "").lower() == "person"]
        if not person_detections:
            # Also check roboflow positive PPE detections for person bboxes
            person_detections = [d for d in roboflow_detections if "person" in d.get("class_name", "").lower()]

        # Process explicit PPE absence detections (no-helmet, no-glove, etc.)
        for v in roboflow_violations:
            conf = v.get("confidence", 0.0)
            if conf < CONFIDENCE_THRESHOLD:
                continue
            bbox = v.get("bbox", [0, 0, 100, 100])
            vtype = v.get("violation_type", "").lower()
            # Determine PPE type
            ppe_type = _extract_ppe_type(vtype)
            if not ppe_type:
                continue
            # Find closest worker or create one
            worker_id = self.worker_tracker.assign_worker_id(bbox)
            self._ppe_absent[worker_id][ppe_type].append((frame_num, conf, bbox))

        # Process positive PPE detections to mark presence
        for d in roboflow_detections:
            conf = d.get("confidence", 0.0)
            if conf < CONFIDENCE_THRESHOLD:
                continue
            cname = d.get("class_name", "").lower()
            # Only positive PPE classes (not violations)
            if any(cname.startswith(p) for p in ("no-", "no_")) or "missing" in cname:
                continue
            ppe_type = _extract_ppe_type(cname)
            if not ppe_type:
                continue
            bbox = d.get("bbox", [0, 0, 100, 100])
            worker_id = self.worker_tracker.assign_worker_id(bbox)
            self._ppe_present[worker_id][ppe_type].append((frame_num, conf, bbox))

    def finalize(self, sop_ppe_required: list, video_duration: float = 0.0) -> list:
        """
        After all frames are processed:
        1. Apply temporal smoothing (min_frames threshold)
        2. Deduplicate into continuous runs
        3. For SOP-required PPE never detected at all, generate "undetermined" violations
           even if no worker was tracked (Roboflow returned nothing).
        Returns list of deduplicated violation records.
        """
        violations = []

        # Per-worker, per-PPE temporal analysis
        all_worker_ids = set(self._ppe_absent.keys()) | set(self._ppe_present.keys())

        # Always include a synthetic default worker so SOP-gap violations fire
        # even when Roboflow returned zero detections for the entire video.
        all_worker_ids.add("W00")

        logger.info(
            "TemporalTracker.finalize: workers=%s sop_required=%s absent_keys=%s present_keys=%s",
            all_worker_ids, sop_ppe_required,
            dict(self._ppe_absent), dict(self._ppe_present),
        )

        for worker_id in all_worker_ids:
            absent_map = self._ppe_absent[worker_id]
            present_map = self._ppe_present[worker_id]

            ppe_types_to_check = set(list(absent_map.keys()) + sop_ppe_required)
            for ppe_type in ppe_types_to_check:
                absent_frames = sorted(set(f for f, _, _ in absent_map.get(ppe_type, [])))
                present_frames = sorted(set(f for f, _, _ in present_map.get(ppe_type, [])))

                if not absent_frames and ppe_type in sop_ppe_required and not present_frames:
                    # PPE required by SOP but never detected (positively or negatively) for this worker.
                    # Skip duplicate sop_gap records — only emit once (for W00 if no real workers,
                    # or for the first real worker that has no evidence for this PPE type).
                    already_have_sop_gap = any(
                        v.get("undetermined") and v.get("ppe_type") == ppe_type
                        for v in violations
                    )
                    if already_have_sop_gap:
                        continue
                    logger.info(
                        "SOP-gap violation: worker=%s ppe_type=%s (required but never detected)",
                        worker_id, ppe_type,
                    )
                    violations.append({
                        "worker_id": worker_id,
                        "violation_type": f"missing {ppe_type}",
                        "ppe_type": ppe_type,
                        "source": "sop_gap",
                        "confidence": 0.0,
                        "undetermined": True,
                        "reason": f"SOP requires {ppe_type} but no detection available — unable to determine compliance",
                        "frame_start": 1,
                        "frame_end": int(video_duration * self.fps) if video_duration else 300,
                        "duration_seconds": round(video_duration, 2) if video_duration else 10.0,
                        "frame_count": int(video_duration * self.fps) if video_duration else 300,
                        "bbox": [0, 0, 0, 0],
                        "timestamp": 0.0,
                    })
                    continue

                if not absent_frames:
                    continue

                # Temporal smoothing: remove isolated absent frames surrounded by present frames
                smoothed_absent = _temporal_smooth(absent_frames, present_frames, self.min_frames)

                if not smoothed_absent:
                    continue

                # Collapse into continuous runs
                runs = _collapse_to_runs(smoothed_absent)
                for run_start, run_end in runs:
                    if (run_end - run_start + 1) < self.min_frames:
                        continue
                    run_confs = [conf for f, conf, _ in absent_map.get(ppe_type, []) if run_start <= f <= run_end]
                    avg_conf = sum(run_confs) / len(run_confs) if run_confs else 0.0
                    run_bboxes = [bbox for f, _, bbox in absent_map.get(ppe_type, []) if run_start <= f <= run_end]
                    repr_bbox = run_bboxes[len(run_bboxes)//2] if run_bboxes else [0, 0, 100, 100]

                    duration = (run_end - run_start) / self.fps
                    start_ts = run_start / self.fps
                    violations.append({
                        "worker_id": worker_id,
                        "violation_type": f"no-{ppe_type}",
                        "ppe_type": ppe_type,
                        "source": "temporal_analysis",
                        "confidence": round(avg_conf, 3),
                        "undetermined": False,
                        "frame_start": run_start,
                        "frame_end": run_end,
                        "frame_count": run_end - run_start + 1,
                        "duration_seconds": round(duration, 2),
                        "timestamp": round(start_ts, 2),
                        "bbox": repr_bbox,
                        "reason": (
                            f"Worker {worker_id}: {ppe_type} absent for {run_end - run_start + 1} consecutive frames "
                            f"({duration:.1f}s) with avg confidence {avg_conf:.2f}"
                        ),
                    })

        logger.info("TemporalTracker.finalize: produced %d violations", len(violations))
        return violations


def _extract_ppe_type(label: str) -> str | None:
    """Extract canonical PPE type from a detection label."""
    PPE_MAP = {
        "helmet": ["helmet", "hardhat", "hard-hat", "hard_hat", "safety-helmet", "safety helmet"],
        "gloves": ["glove", "gloves", "safety-gloves", "safety gloves", "hand protection"],
        "goggles": [
            "goggle", "goggles", "glasses", "eye protection", "eye-protection",
            "eyewear", "safety-glasses", "safety glasses", "face-shield", "face shield",
        ],
        "vest": ["vest", "hi-vis", "hivis", "high-vis", "visibility", "reflective", "high visibility"],
        "shoes": ["shoe", "shoes", "boot", "boots", "foot", "footwear", "safety-boot", "steel-toe"],
        "mask": ["mask", "respirator", "face-mask", "face mask", "respiratory", "n95"],
        "person": ["person"],
    }
    for canon, variants in PPE_MAP.items():
        if canon == "person":
            continue
        if any(v in label for v in variants):
            return canon
    return None


def _temporal_smooth(absent_frames: list, present_frames: list, min_frames: int) -> list:
    """
    Remove flicker: an absent-frame isolated between present-frames
    (gap < min_frames) is removed.
    """
    if not absent_frames:
        return []
    present_set = set(present_frames)
    result = []
    n = len(absent_frames)
    for i, f in enumerate(absent_frames):
        # Check if this absent frame is part of a run of >= min_frames
        run_len = 1
        j = i + 1
        while j < n and absent_frames[j] == absent_frames[j-1] + 1:
            run_len += 1
            j += 1
        if run_len >= min_frames:
            result.append(f)
        elif f not in present_set:
            # Isolated absent frame not in a long run — keep only if surrounded by absent frames
            before_present = any(f - k in present_set for k in range(1, min_frames+1))
            after_present = any(f + k in present_set for k in range(1, min_frames+1))
            if not (before_present or after_present):
                result.append(f)
    return result


def _collapse_to_runs(frames: list) -> list:
    """Collapse sorted frame list into (start, end) continuous runs."""
    if not frames:
        return []
    runs = []
    start = frames[0]
    end = frames[0]
    for f in frames[1:]:
        if f <= end + 2:  # Allow 1-frame gap within a run
            end = f
        else:
            runs.append((start, end))
            start = f
            end = f
    runs.append((start, end))
    return runs
