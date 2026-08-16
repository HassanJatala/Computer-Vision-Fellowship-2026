from collections import deque


class TrackStateManager:
    """
    Maintains persistent state for every tracked object across frames.
    This is the shared 'memory' that analytics, rules, and events all read from.
    """

    def __init__(self, trajectory_length=100):
        self.tracks = {}  # track_id -> state dict
        self.trajectory_length = trajectory_length

    def _bottom_center(self, bbox):
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2, y2)

    def update(self, tracked_objects, current_time):
        """
        Called once per frame with the tracker's output
        (list of dicts: track_id, bbox, confidence, class_id, class_name).
        Creates new state entries for new track_ids, updates existing ones.
        """
        seen_ids = set()

        for obj in tracked_objects:
            track_id = obj["track_id"]
            seen_ids.add(track_id)
            position = self._bottom_center(obj["bbox"])

            if track_id not in self.tracks:
                self.tracks[track_id] = {
                    "track_id": track_id,
                    "class_name": obj["class_name"],
                    "bbox": obj["bbox"],
                    "confidence": obj["confidence"],
                    "position": position,
                    "first_seen": current_time,
                    "last_seen": current_time,
                    "current_zone": None,
                    "previous_zone": None,
                    "zone_entry_time": None,
                    "trajectory": deque(maxlen=self.trajectory_length),
                }
                self.tracks[track_id]["trajectory"].append(position)
            else:
                record = self.tracks[track_id]
                record["bbox"] = obj["bbox"]
                record["confidence"] = obj["confidence"]
                record["position"] = position
                record["last_seen"] = current_time
                record["trajectory"].append(position)

        return seen_ids

    def get_state(self, track_id):
        return self.tracks.get(track_id)

    def get_all_states(self):
        return self.tracks

    def remove_stale_tracks(self, current_time, max_age_seconds=5):
        """
        Removes tracks that haven't been seen in a while
        (e.g., person left the frame permanently).
        Uses the same clock (video-time or wall-clock) as everything
        else in the pipeline, passed in by the caller.
        """
        stale_ids = [
            tid for tid, record in self.tracks.items()
            if current_time - record["last_seen"] > max_age_seconds
        ]
        for tid in stale_ids:
            del self.tracks[tid]
        return stale_ids