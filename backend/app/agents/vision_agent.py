import logging
import cv2
from app.agents.base import BaseADKAgent
from app.services.pii_service import get_pii_service
from app.services.yolov8_service import get_yolo_service
from app.services.roboflow_service import get_roboflow_service

logger = logging.getLogger(__name__)

class VisionAgent(BaseADKAgent):
    """Vision Agent managing frame extraction, object detection, and face obfuscation."""
    
    def __init__(self):
        instructions = (
            "You are the Vision Agent. You oversee computer vision tasks. "
            "Your job is to extract frames from video files, run YOLOv8 and Roboflow detections, "
            "and run privacy blurring over worker faces using MediaPipe."
        )
        super().__init__(name="VisionAgent", instructions=instructions)
        self.pii = get_pii_service()
        self.yolo = get_yolo_service()
        self.roboflow = get_roboflow_service()

    def process_frame(self, frame_img, frame_num: int) -> dict:
        """Run detections on a frame and apply PII face blurring."""
        logger.info(f"VisionAgent: Processing frame #{frame_num}")
        
        # Apply face blurring first (PII Masking)
        masked_frame = self.pii.blur_faces(frame_img)
        
        # Run detections
        yolo_res = self.yolo.analyze_frame(masked_frame, frame_num)
        robo_res = self.roboflow.detect_ppe(masked_frame, frame_num)
        
        detections = []
        for d in yolo_res:
            detections.append({"class": d["class_name"], "confidence": d["confidence"], "bbox": d["bbox"]})
            
        for d in robo_res.get("detections", []):
            if not any(d["class_name"].startswith(p) for p in ("no-", "no_")) and "missing" not in d["class_name"]:
                detections.append({"class": d["class_name"], "confidence": d["confidence"], "bbox": d["bbox"]})
                
        # Capture raw violation detections
        violations = []
        for v in robo_res.get("violations", []):
            violations.append({"type": v["violation_type"], "confidence": v["confidence"], "bbox": v["bbox"]})
            
        return {
            "frame_number": frame_num,
            "detections": detections,
            "violations": violations,
            "masked_frame": masked_frame
        }
