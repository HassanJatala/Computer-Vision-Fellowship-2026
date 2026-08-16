from ultralytics import YOLO
import config


class PersonTracker:
    def __init__(self, model_path=None, confidence=None, tracker_type=None):
        self.model_path = model_path or config.MODEL_PATH
        self.confidence = confidence or config.DETECTION_CONFIDENCE
        self.tracker_type = tracker_type or config.TRACKER  # "bytetrack" or "botsort"
        self.model = YOLO(self.model_path)

        self.target_class_id = 0  # person

        # ultralytics expects a .yaml filename for tracker config
        self.tracker_config = f"{self.tracker_type}.yaml"

    def track(self, frame):
        """
        Runs detection + tracking on a single frame.
        Returns a list of dicts, one per tracked person:
        { "track_id": int, "bbox": (x1, y1, x2, y2), "confidence": float,
          "class_id": int, "class_name": str }
        """
        results = self.model.track(
            source=frame,
            conf=self.confidence,
            classes=[self.target_class_id],
            tracker=self.tracker_config,
            persist=True,
            verbose=False
        )

        tracks = []
        for result in results:
            if result.boxes.id is None:
                continue  # no tracks confirmed yet this frame

            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                cls_name = self.model.names[cls_id]
                track_id = int(box.id[0])

                tracks.append({
                    "track_id": track_id,
                    "bbox": (x1, y1, x2, y2),
                    "confidence": conf,
                    "class_id": cls_id,
                    "class_name": cls_name
                })

        return tracks