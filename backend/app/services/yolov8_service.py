import os
import logging

logger = logging.getLogger(__name__)

MODEL_PATH = "yolov8n.pt"

# Workshop/automotive-relevant COCO classes that indicate task context
TASK_INDICATOR_CLASSES = {
    "car", "truck", "bus", "motorcycle", "bicycle",
    "bottle", "cup", "bowl",
    "scissors", "knife",
    "fire", "person",
}

# PPE-related YOLO class names (when using a PPE-specific model)
PPE_POSITIVE_CLASSES = {
    "helmet", "hardhat", "hard-hat", "safety-helmet",
    "vest", "safety-vest", "hi-vis",
    "gloves", "safety-gloves",
    "goggles", "safety-goggles", "safety-glasses",
    "safety-shoes", "boots",
    "mask", "face-shield",
}

PPE_VIOLATION_PREFIXES = ("no-", "no_", "without-", "missing-", "missing_")


class YOLOv8Service:
    def __init__(self):
        self._model = None  # Lazy-load

    def _get_model(self):
        if self._model is None:
            try:
                from ultralytics import YOLO
                self._model = YOLO(MODEL_PATH)
                logger.info("YOLOv8 model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load YOLOv8 model: {e}")
                self._model = None
        return self._model

    def analyze_frame(self, frame, frame_num: int):
        """
        Analyze a single frame using YOLOv8.
        Returns a list of detections: { class_name, confidence, bbox: [x1, y1, x2, y2] }
        """
        model = self._get_model()
        if model is None:
            return []

        try:
            results = model(frame, verbose=False)
        except Exception as e:
            logger.error(f"YOLOv8 inference error at frame {frame_num}: {e}")
            return []

        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                class_name = model.names.get(cls_id, "unknown")
                if conf > 0.4:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    detections.append({
                        "frame_num": frame_num,
                        "class_name": class_name,
                        "confidence": conf,
                        "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    })

        return detections

    def infer_procedural_violations(self, all_detections: list, fps: float = 30.0, sop_rules: dict = None) -> list:
        """
        Analyze YOLO detections to infer procedural violations grounded in SOP rules.
        Only raises violations when there is clear evidence AND the SOP requires it.
        Never hallucinates generic violations (no jack stand, worker near vehicle, etc.)
        unless those specific checks appear in the SOP's required_procedures or forbidden_actions.
        """
        if not all_detections:
            return []

        if sop_rules is None:
            sop_rules = {}

        # Group detections by frame
        frames = {}
        for det in all_detections:
            fn = det.get("frame_num", 0)
            if fn not in frames:
                frames[fn] = []
            frames[fn].append(det.get("class_name", "").lower())

        all_classes_seen = set()
        for class_list in frames.values():
            all_classes_seen.update(class_list)

        violations = []
        triggered = set()

        # ── Fire hazard: always flag if fire is visually detected ──
        if "fire" in all_classes_seen and "fire_hazard" not in triggered:
            first_frame = next(
                (fn for fn in sorted(frames.keys()) if "fire" in frames[fn]), None
            )
            if first_frame is not None:
                ts = first_frame / fps if fps > 0 else float(first_frame)
                violations.append({
                    "violation_type": "Fire Hazard Detected",
                    "confidence": 0.92,
                    "frame_num": first_frame,
                    "timestamp": round(ts, 2),
                    "bbox": [0, 0, 100, 100],
                    "source": "visual_evidence",
                    "sop_hint": "fire",
                    "why_detected": "Fire class detected by object detection model",
                    "evidence_basis": "Direct visual detection of fire",
                })
                triggered.add("fire_hazard")

        # ── SOP-grounded procedural checks ──
        # Only raise vehicle/proximity hazards if the SOP explicitly requires procedures
        # around vehicle lifting, jack stands, or worker proximity.
        forbidden_actions = [str(f).lower() for f in sop_rules.get("forbidden_actions", [])]
        required_procedures = [str(p).lower() for p in sop_rules.get("required_procedures", [])]
        hazards_list = [str(h).lower() for h in sop_rules.get("hazards", [])]
        all_sop_text = " ".join(forbidden_actions + required_procedures + hazards_list)

        # Jack stand check: only if SOP mentions jack stands AND vehicle + person are co-present
        if ("jack stand" in all_sop_text or "vehicle lift" in all_sop_text):
            vehicle_classes = {"car", "truck", "bus", "motorcycle"}
            vehicle_frames = {fn for fn, cls in frames.items() if any(c in cls for c in vehicle_classes)}
            person_frames = {fn for fn, cls in frames.items() if "person" in cls}
            colocated = vehicle_frames & person_frames
            if colocated and "jack_stand_check" not in triggered:
                first_frame = min(colocated)
                ts = first_frame / fps if fps > 0 else float(first_frame)
                violations.append({
                    "violation_type": "Unsafe Vehicle Lift - Jack Stand Required",
                    "confidence": 0.70,
                    "frame_num": first_frame,
                    "timestamp": round(ts, 2),
                    "bbox": [0, 0, 100, 100],
                    "source": "sop_procedural_reasoning",
                    "sop_hint": "jack stand",
                    "why_detected": "SOP requires jack stand during vehicle lift; person and vehicle co-detected in frame",
                    "evidence_basis": "Vehicle + person co-occurrence; SOP mandates secondary support",
                })
                triggered.add("jack_stand_check")

        # Proximity hazard: only if SOP forbids it or mandates safe distance
        if ("safe distance" in all_sop_text or "proximity" in all_sop_text or "crush hazard" in all_sop_text):
            vehicle_classes = {"car", "truck", "bus", "motorcycle"}
            vehicle_frames_set = {fn for fn, cls in frames.items() if any(c in cls for c in vehicle_classes)}
            person_frames_set = {fn for fn, cls in frames.items() if "person" in cls}
            for pf in sorted(person_frames_set)[:3]:
                for vf in sorted(vehicle_frames_set)[:3]:
                    if abs(pf - vf) <= 3 and "proximity_hazard" not in triggered:
                        ts = pf / fps if fps > 0 else float(pf)
                        violations.append({
                            "violation_type": "Worker-Vehicle Proximity Hazard",
                            "confidence": 0.68,
                            "frame_num": pf,
                            "timestamp": round(ts, 2),
                            "bbox": [0, 0, 100, 100],
                            "source": "sop_procedural_reasoning",
                            "sop_hint": "proximity",
                            "why_detected": "SOP mandates safe distance from vehicles; worker and vehicle co-detected",
                            "evidence_basis": "Person+vehicle within 3 frames; SOP prohibits unsafe proximity",
                        })
                        triggered.add("proximity_hazard")
                        break
                if "proximity_hazard" in triggered:
                    break

        return violations


# Singleton instance — model loads lazily on first call, not at import time
yolo_service = YOLOv8Service()

def get_yolo_service():
    return yolo_service
