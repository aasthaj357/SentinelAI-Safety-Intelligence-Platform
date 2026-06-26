import logging
from app.core.config import settings

logger = logging.getLogger(__name__)
MODEL_ID = "ppe-detection-with-gloves/9"


class RoboflowService:
    def __init__(self):
        self._client = None  # Lazy-load

    def _get_client(self):
        if self._client is None:
            try:
                from inference_sdk import InferenceHTTPClient
                self._client = InferenceHTTPClient(
                    api_url="https://serverless.roboflow.com",
                    api_key=settings.ROBOFLOW_API_KEY,
                )
            except Exception as e:
                logger.error(f"Failed to initialize Roboflow client: {e}")
                self._client = None
        return self._client

    def detect_ppe(self, frame, frame_num: int) -> dict:
        """
        Run PPE detection on a single frame.
        Returns a dict with detections and violations lists.
        """
        client = self._get_client()
        if client is None:
            return {"detections": [], "violations": []}

        try:
            result = client.infer(frame, model_id=MODEL_ID)
        except Exception as e:
            logger.warning(f"Roboflow inference error at frame {frame_num}: {e}")
            return {"detections": [], "violations": []}

        predictions = result.get("predictions", [])
        detections = []
        violations = []

        for p in predictions:
            class_name = p.get("class", "").lower()
            conf = p.get("confidence", 0.0)

            if conf < 0.45:
                continue

            bbox = [
                int(p["x"] - p["width"] / 2),
                int(p["y"] - p["height"] / 2),
                int(p["x"] + p["width"] / 2),
                int(p["y"] + p["height"] / 2),
            ]

            detections.append({
                "frame_num": frame_num,
                "class_name": class_name,
                "confidence": conf,
                "bbox": bbox,
            })

            # Only raise a PPE violation if the model explicitly labels the absence of PPE.
            # Require confidence >= 0.5 and a genuine "missing" class name.
            # Positive PPE detections ("helmet", "vest", etc.) must NOT create violations.
            is_violation = False
            if conf >= 0.5:
                if class_name.startswith("no-") or class_name.startswith("no_"):
                    is_violation = True
                elif "missing" in class_name or "without" in class_name:
                    is_violation = True
                # Explicitly exclude positive detections that may contain the word "no" in a brand/label
                # e.g. "safety-helmet" should NOT match

            if is_violation:
                violations.append({
                    "frame_num": frame_num,
                    "violation_type": class_name,
                    "confidence": conf,
                    "bbox": bbox,
                })

        return {"detections": detections, "violations": violations}


roboflow_service = RoboflowService()

def get_roboflow_service():
    return roboflow_service
