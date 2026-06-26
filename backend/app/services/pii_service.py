import cv2
import logging
import numpy as np

logger = logging.getLogger(__name__)

# Lazy-load mediapipe to prevent startup blocking
_mp_face = None

def _get_mp_face():
    global _mp_face
    if _mp_face is None:
        try:
            import mediapipe as mp
            _mp_face = mp.solutions.face_detection
        except Exception as e:
            logger.error(f"Failed to load mediapipe: {e}")
            _mp_face = False
    return _mp_face

class PIIService:
    """PII Obfuscation service utilizing MediaPipe face detection."""
    
    def __init__(self):
        self.face_detector = None

    def _init_detector(self):
        mp_face = _get_mp_face()
        if mp_face and self.face_detector is None:
            try:
                self.face_detector = mp_face.FaceDetection(min_detection_confidence=0.45)
            except Exception as e:
                logger.error(f"Failed to initialize MediaPipe Face Detection: {e}")
                self.face_detector = False

    def blur_faces(self, frame: np.ndarray) -> np.ndarray:
        """Locates faces in a frame and applies a Gaussian blur to protect user privacy."""
        self._init_detector()
        if not self.face_detector:
            # Fallback: if MediaPipe failed to load, return unchanged frame
            return frame
            
        try:
            h, w, _ = frame.shape
            # MediaPipe expects RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_detector.process(rgb_frame)
            
            if results.detections:
                for detection in results.detections:
                    bbox = detection.location_data.relative_bounding_box
                    # Convert relative coordinates to pixels
                    xmin = max(0, int(bbox.xmin * w))
                    ymin = max(0, int(bbox.ymin * h))
                    width = int(bbox.width * w)
                    height = int(bbox.height * h)
                    
                    xmax = min(w, xmin + width)
                    ymax = min(h, ymin + height)
                    
                    if width > 0 and height > 0:
                        # Extract face region
                        face_roi = frame[ymin:ymax, xmin:xmax]
                        # Apply Gaussian Blur (kernel must be odd)
                        ksize = max(15, int(width / 3) | 1)
                        blurred_roi = cv2.GaussianBlur(face_roi, (ksize, ksize), 30)
                        # Replace original face area with blurred one
                        frame[ymin:ymax, xmin:xmax] = blurred_roi
                        
            return frame
        except Exception as e:
            logger.error(f"Error executing MediaPipe face blur: {e}")
            return frame

pii_service = PIIService()

def get_pii_service():
    return pii_service
