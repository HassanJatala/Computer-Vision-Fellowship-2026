import cv2
import os
from datetime import datetime


class EvidenceCapture:
    def __init__(self, evidence_dir="evidence"):
        self.evidence_dir = evidence_dir
        os.makedirs(self.evidence_dir, exist_ok=True)

        self.zone_colors = {
            "zone_1": (0, 0, 255),      # Restricted Area - Red
            "zone_2": (0, 255, 255),    # Entrance - Yellow
            "zone_3": (255, 0, 0),      # Waiting Area - Blue
        }
        self.person_box_color = (0, 255, 0)  # Green
        self.default_zone_color = (255, 255, 255)

    def capture(self, event_id, frame, bbox, detected_time, zone=None):
        """
        Saves the full frame (with zone outline + person bbox drawn on it)
        and a plain cropped image of the detected object.
        Filenames are timestamped with real-world detected_time for easy
        chronological browsing.
        """
        timestamp_str = datetime.fromtimestamp(detected_time).strftime("%Y-%m-%d_%H-%M-%S")
        base_name = f"{timestamp_str}_{event_id}"

        full_path = os.path.join(self.evidence_dir, f"{base_name}_full.jpg")
        crop_path = os.path.join(self.evidence_dir, f"{base_name}_crop.jpg")

        annotated_frame = frame.copy()

        if zone is not None:
            color = self.zone_colors.get(zone.zone_id, self.default_zone_color)
            cv2.polylines(annotated_frame, [zone.polygon], isClosed=True, color=color, thickness=3)
            label_position = tuple(zone.polygon[0])
            cv2.putText(annotated_frame, zone.name, label_position,
                        cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        x1, y1, x2, y2 = [int(coord) for coord in bbox]
        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), self.person_box_color, 2)

        cv2.imwrite(full_path, annotated_frame)

        cropped = frame[y1:y2, x1:x2]
        if cropped.size > 0:
            cv2.imwrite(crop_path, cropped)
        else:
            crop_path = None

        return full_path, crop_path