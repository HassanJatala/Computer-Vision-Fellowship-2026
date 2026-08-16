from ultralytics import YOLO
import config


class PersonDetector:
    def __init__(self, model_path=None, confidence=None):
        # Use config defaults if nothing is explicitly passed in
        self.model_path = model_path or config.MODEL_PATH
        self.confidence = confidence or config.DETECTION_CONFIDENCE
        self.model = YOLO(self.model_path)

        # COCO class 0 = "person" in pretrained YOLOv8 models
        self.target_class_id = 0

    def detect(self, frame):
        """
        Runs detection on a single frame.
        Returns a list of dicts, one per detected person:
        { "bbox": (x1, y1, x2, y2), "confidence": float, "class_id": int, "class_name": str }
        """
        results = self.model.predict(
            source=frame,
            conf=self.confidence,
            classes=[self.target_class_id],
            verbose=False
        )

        detections = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                cls_name = self.model.names[cls_id]

                detections.append({
                    "bbox": (x1, y1, x2, y2),
                    "confidence": conf,
                    "class_id": cls_id,
                    "class_name": cls_name
                })

        return detections