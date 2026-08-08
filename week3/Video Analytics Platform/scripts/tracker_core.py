"""
tracker_core.py

Core video analytics engine: detection + tracking + counting + line
crossing + zones + trails + heatmap + CSV report generation.

This module is UI-agnostic (no Streamlit here) so it can be reused from
the Streamlit app, a plain script, or tested standalone.
"""
import tempfile
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# --- Compat shim: NumPy 2.x removed 2D-vector support from np.cross,
# but supervision's PolygonZone (get_polygon_center) still relies on it. ---
_original_cross = np.cross


def _cross_2d_compat(a, b, *args, **kwargs):
    a = np.asarray(a)
    b = np.asarray(b)
    if a.shape[-1] == 2 and b.shape[-1] == 2:
        return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]
    return _original_cross(a, b, *args, **kwargs)


np.cross = _cross_2d_compat

import cv2
import pandas as pd
import supervision as sv
from ultralytics import YOLO


@dataclass
class TrackState:
    """Keeps running state across frames: which IDs we've seen, their
    trails, zone dwell times, etc. One instance per processing session."""
    seen_ids: set = field(default_factory=set)          # every ID ever seen (Total Objects)
    active_ids: set = field(default_factory=set)         # IDs present in the CURRENT frame
    trails: dict = field(default_factory=lambda: defaultdict(lambda: deque(maxlen=30)))
    class_names: dict = field(default_factory=dict)      # tracker_id -> class name (for reports)
    confidences: dict = field(default_factory=dict)      # tracker_id -> last known confidence
    entered_count: int = 0
    exited_count: int = 0
    zone_dwell_frames: dict = field(default_factory=lambda: defaultdict(int))  # (zone_idx, tracker_id) -> frame count
    heatmap: np.ndarray = None
    frame_count: int = 0
    all_confidences: list = field(default_factory=list)
    checkpoint_status: dict = field(default_factory=dict)  # tracker_id -> "outside" | "inside" | "passed"
    # botsort only -- see the confirmation-gate block in process_frame().
    # Ultralytics' native model.track() has no equivalent to ByteTrack's
    # minimum_consecutive_frames, so it's replicated manually here. Both
    # fields stay empty and untouched for the bytetrack path.
    pending_confirmation: dict = field(default_factory=lambda: defaultdict(int))  # tid -> frames seen so far
    confirmed_ids: set = field(default_factory=set)  # tids that have cleared minimum_consecutive_frames

    def register(self, tracker_id, class_name, conf):
        self.seen_ids.add(tracker_id)
        self.active_ids.add(tracker_id)
        self.class_names[tracker_id] = class_name
        self.confidences[tracker_id] = conf
        self.all_confidences.append(conf)


class VideoAnalyticsEngine:
    def __init__(self, model_path: str, tracker: str = "bytetrack",
                 conf_threshold: float = 0.3, track_buffer: int = 60,
                 minimum_consecutive_frames: int = 5):
        """
        tracker: "bytetrack" or "botsort".

        conf_threshold: confidence threshold for detections.

        track_buffer: number of frames a track is kept alive while
        unmatched (e.g. during occlusion) before being deleted and a new
        ID being issued on reappearance.

        minimum_consecutive_frames: how many consecutive frames a
        detection must appear in before a track is confirmed as real and
        stable (rather than instantly assigning an ID to any single
        detection, which is supervision's default of 1). This directly
        targets "ghost tracks" -- high-confidence detections that appear
        for exactly one frame and vanish, inflating Total Objects without
        representing a real, persistent object.

        For "bytetrack", this is passed straight into sv.ByteTrack(),
        which has native support for it. For "botsort", Ultralytics'
        native model.track() has NO equivalent parameter -- new_track_thresh
        only gates confidence, not multi-frame persistence -- so the same
        confirmation requirement is replicated manually in process_frame()
        via TrackState.pending_confirmation / confirmed_ids. Both paths are
        meant to enforce the same standard; the mechanism just differs
        because Ultralytics doesn't expose the hook ByteTrack does.
        """
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        # Detection floor: what we actually feed the detector/tracker.
        # This must stay BELOW track_low_thresh in the tracker configs
        # below, otherwise every detection the tracker relies on to
        # survive brief confidence dips (occlusion, motion blur, angle)
        # gets deleted before the tracker ever sees it -- which was the
        # root cause of the ID-churn problem. conf_threshold is kept
        # separately and used only for reporting/display filtering, not
        # for the actual model.track()/model.predict() call.
        self.detection_floor = min(0.1, conf_threshold)
        self.tracker_name = tracker
        self.track_buffer = track_buffer
        self.minimum_consecutive_frames = minimum_consecutive_frames
        self._botsort_config_path = None

        if tracker == "bytetrack":
            self.byte_tracker = sv.ByteTrack(
                track_activation_threshold=conf_threshold,
                lost_track_buffer=track_buffer,
                minimum_matching_threshold=0.8,
                minimum_consecutive_frames=minimum_consecutive_frames,
            )
        elif tracker == "botsort":
            self.byte_tracker = None  # ultralytics handles tracking natively for this mode
            # FIX: conf_threshold is now passed through so BoT-SORT's
            # track-start/track-high/track-low thresholds are tied to the
            # same value ByteTrack uses -- see docstring below for why.
            self._botsort_config_path = self._write_botsort_config(track_buffer, conf_threshold)
        else:
            raise ValueError(f"Unknown tracker '{tracker}', expected 'bytetrack' or 'botsort'")

        self.box_annotator = sv.BoxAnnotator()
        self.label_annotator = sv.LabelAnnotator()
        self.trace_annotator = sv.TraceAnnotator(trace_length=30)

        self.state = TrackState()
        self.checkpoint_rect = None    # (x1, y1, x2, y2) -- the checkpoint rectangle
        self.polygon_zones = []       # list of sv.PolygonZone
        self.polygon_annotators = []  # list of sv.PolygonZoneAnnotator

    @staticmethod
    def _write_botsort_config(track_buffer: int, conf_threshold: float) -> str:
        """Writes a BoT-SORT tracker config to a temp file with the ACTUAL
        requested track_buffer and conf_threshold, rather than relying on a
        static yaml with hardcoded values that ignore whatever the user set
        in the UI.

        FIX #1 -- thresholds tied to conf_threshold:
        track_high_thresh, track_low_thresh, and (most importantly)
        new_track_thresh were previously hardcoded independently of
        conf_threshold, with new_track_thresh fixed at 0.5. The
        conf_threshold slider's own help text in app.py documents that
        real helmet detections on this footage commonly sit at
        0.46-0.59 confidence -- so a fixed 0.5 new-track gate was
        silently discarding a meaningful slice of genuine detections
        (anything 0.46-0.49) before BoT-SORT ever got a chance to track
        them, while ByteTrack (activation threshold tied directly to
        conf_threshold) tracked those same detections fine. All three
        thresholds are now tied to conf_threshold, matching ByteTrack's
        activation threshold, so both trackers start from the same
        detection floor. track_low_thresh mirrors detection_floor's
        min(0.1, conf_threshold) logic above for consistency.

        FIX #2 -- with_reid now OFF by default:
        Ultralytics' default Re-ID backbone (model: auto) is trained for
        person re-identification -- full-body crops, clothing texture,
        gait -- not the small head/helmet crops this project tracks. On
        this footage it was fusing appearance cost from a mismatched
        embedding space into the match decision rather than providing a
        genuine occlusion-recovery signal. Re-enable only after
        validating (or fine-tuning) a Re-ID model on helmet crops
        specifically -- proximity_thresh/appearance_thresh below are
        left in place but are inactive while with_reid is False, so
        re-enabling is a one-line change.

        FIX #3 -- gmc_method now "none":
        Camera-motion compensation estimates a frame-to-frame homography
        to correct for camera movement. This project's checkpoint-based
        design (a fixed rectangle objects walk through) implies a static
        camera, so sparseOptFlow had nothing real to correct for and was
        only injecting optical-flow estimation noise into every track's
        motion prediction. Switch this back to "sparseOptFlow" only for
        footage where the camera itself moves (handheld, drone, PTZ).

        FIX #4 -- match_thresh now 0.8, matching ByteTrack:
        Previously loosened to 0.7 while ByteTrack's
        minimum_matching_threshold stayed at 0.8 -- an asymmetric
        comparison where BoT-SORT accepted weaker IoU matches than
        ByteTrack, independent of either tracker's actual matching
        strategy. Aligned to 0.8 so a tracker-vs-tracker comparison
        isn't confounded by differing acceptance bars. (Loosening this
        deliberately, as its own controlled experiment, is still worth
        trying later -- just not as a silent default.)
        """
        track_low_thresh = min(0.1, conf_threshold)
        config_text = f"""tracker_type: botsort
track_high_thresh: {conf_threshold}
track_low_thresh: {track_low_thresh}
new_track_thresh: {conf_threshold}
track_buffer: {track_buffer}
match_thresh: 0.8
fuse_score: True
gmc_method: none
proximity_thresh: 0.5
appearance_thresh: 0.25
with_reid: False
model: auto
"""
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        tmp.write(config_text)
        tmp.close()
        return tmp.name

    def get_active_config(self) -> dict:
        """Returns the ACTUAL settings currently in effect -- use this to
        confirm a config change really landed, rather than assuming it did."""
        cfg = {
            "tracker": self.tracker_name,
            "conf_threshold": self.conf_threshold,
            "track_buffer": self.track_buffer,
            "minimum_consecutive_frames": self.minimum_consecutive_frames,
        }
        if self.tracker_name == "botsort":
            cfg["config_file"] = self._botsort_config_path
            cfg["config_contents"] = Path(self._botsort_config_path).read_text()
        return cfg

    # ------------------------------------------------------------------
    # Setup: checkpoint rectangle and zones (call once, before processing)
    # ------------------------------------------------------------------
    def set_checkpoint(self, top_left, bottom_right):
        """top_left, bottom_right: (x, y) tuples defining the checkpoint
        rectangle in pixel coordinates.

        Logic (whole-bounding-box based, not a single anchor point):
        - A tracker_id is marked ENTERED the first time its FULL bounding
          box is completely contained inside this rectangle (not just
          touching/overlapping -- the whole box must be inside).
        - The same tracker_id is marked EXITED the first time its full
          bounding box is completely OUTSIDE the rectangle again, after
          having previously been marked entered. This models the
          rectangle as a checkpoint "tunnel": you must fully enter, then
          fully leave, to register a complete pass-through.
        - Each tracker_id can only trigger each event once, so a single
          real vehicle/object is never double-counted even if it lingers
          or jitters at the rectangle's edge.

        This is more forgiving for messy/multi-lane traffic than a thin
        line + single anchor point, since it doesn't require an exact
        pixel-perfect crossing moment -- just full containment, then full
        departure.
        """
        (x1, y1), (x2, y2) = top_left, bottom_right
        self.checkpoint_rect = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))

    @staticmethod
    def _fully_inside(box, rect):
        """box: (x1, y1, x2, y2) detection box. rect: (x1, y1, x2, y2)
        checkpoint. Returns True only if the ENTIRE box is inside rect."""
        bx1, by1, bx2, by2 = box
        rx1, ry1, rx2, ry2 = rect
        return bx1 >= rx1 and by1 >= ry1 and bx2 <= rx2 and by2 <= ry2

    def add_roi_zone(self, polygon_points, frame_shape):
        """polygon_points: list of (x, y) tuples. frame_shape: (h, w)."""
        polygon = np.array(polygon_points, dtype=np.int32)
        zone = sv.PolygonZone(polygon=polygon)
        annotator = sv.PolygonZoneAnnotator(zone=zone, color=sv.Color.YELLOW, thickness=2)
        self.polygon_zones.append(zone)
        self.polygon_annotators.append(annotator)

    def init_heatmap(self, frame_shape):
        h, w = frame_shape[:2]
        self.state.heatmap = np.zeros((h, w), dtype=np.float32)

    # ------------------------------------------------------------------
    # Per-frame processing
    # ------------------------------------------------------------------
    def process_frame(self, frame: np.ndarray):
        start = time.time()
        self.state.frame_count += 1
        self.state.active_ids = set()

        if self.tracker_name == "botsort":
            # Uses the dynamically-generated config from __init__ (see
            # _write_botsort_config), which reflects the ACTUAL requested
            # track_buffer and conf_threshold -- not static hardcoded values.
            results = self.model.track(
                frame, conf=self.detection_floor, tracker=self._botsort_config_path,
                persist=True, verbose=False,
            )[0]
            detections = sv.Detections.from_ultralytics(results)
            # tracker_id is already populated by ultralytics in this mode
        else:
            results = self.model.predict(frame, conf=self.detection_floor, verbose=False)[0]
            detections = sv.Detections.from_ultralytics(results)
            detections = self.byte_tracker.update_with_detections(detections)
        print(f"[DEBUG] frame#{self.state.frame_count} shape={frame.shape} raw_detections={len(detections)}")
        annotated = frame.copy()

        # Display/report mask: the tracker sees every detection down to
        # detection_floor so it can survive confidence dips, but we only
        # want to draw boxes/labels and register into reports for
        # detections that clear the user-facing conf_threshold. This
        # keeps low-confidence "recovery" detections useful to the
        # tracker's matching logic without cluttering the visible output.
        report_mask = detections.confidence >= self.conf_threshold if len(detections) else np.array([], dtype=bool)

        if detections.tracker_id is not None:
            for i in range(len(detections)):
                tid = int(detections.tracker_id[i])

                # BoT-SORT-only: replicate ByteTrack's minimum_consecutive_frames
                # confirmation gate, which Ultralytics' native track() has no
                # equivalent for. Guarded so this NEVER executes for ByteTrack --
                # self.tracker_name is set once in __init__ and never changes,
                # so this branch is structurally unreachable on the bytetrack path.
                if self.tracker_name == "botsort" and tid not in self.state.confirmed_ids:
                    self.state.pending_confirmation[tid] += 1
                    if self.state.pending_confirmation[tid] < self.minimum_consecutive_frames:
                        continue  # not yet confirmed -- skip registering/drawing/counting this one
                    self.state.confirmed_ids.add(tid)

                cls_id = int(detections.class_id[i])
                conf = float(detections.confidence[i])
                cls_name = self.model.names.get(cls_id, str(cls_id))

                # Checkpoint state machine runs on EVERY (confirmed) detection
                # so a track that dips below conf_threshold for a frame or two
                # doesn't miss its entered/exited transition. Uses FULL
                # bounding-box containment, not a single anchor point -- see
                # set_checkpoint() docstring for the entered/exited rules.
                if self.checkpoint_rect is not None:
                    box = tuple(detections.xyxy[i])
                    status = self.state.checkpoint_status.get(tid, "outside")
                    fully_in = self._fully_inside(box, self.checkpoint_rect)

                    if status == "outside" and fully_in:
                        self.state.checkpoint_status[tid] = "inside"
                        self.state.entered_count += 1
                    elif status == "inside" and not fully_in:
                        self.state.checkpoint_status[tid] = "passed"
                        self.state.exited_count += 1

                if not report_mask[i]:
                    continue
                self.state.register(tid, cls_name, conf)

                x1, y1, x2, y2 = detections.xyxy[i]
                cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
                self.state.trails[tid].append((cx, cy))

                if self.state.heatmap is not None:
                    cv2.circle(self.state.heatmap, (cx, cy), 15, 1.0, -1)

                for zi, zone in enumerate(self.polygon_zones):
                    if zone.trigger(detections=detections[i:i + 1]).any():
                        self.state.zone_dwell_frames[(zi, tid)] += 1

            display_detections = detections[report_mask]
            annotated = self.box_annotator.annotate(annotated, display_detections)
            labels = [
                f"#{tid} {self.model.names.get(cid, cid)} {conf:.2f}"
                for tid, cid, conf in zip(
                    display_detections.tracker_id, display_detections.class_id, display_detections.confidence
                )
            ]
            annotated = self.label_annotator.annotate(annotated, display_detections, labels=labels)
            annotated = self.trace_annotator.annotate(annotated, display_detections)

        # Draw the checkpoint rectangle for visual reference on the output
        # video (entered/exited counting happens above, per detection).
        if self.checkpoint_rect is not None:
            rx1, ry1, rx2, ry2 = self.checkpoint_rect
            cv2.rectangle(annotated, (int(rx1), int(ry1)), (int(rx2), int(ry2)), (0, 255, 255), 2)
            cv2.putText(annotated, f"IN: {self.state.entered_count}  OUT: {self.state.exited_count}",
                        (int(rx1), max(0, int(ry1) - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        for annotator, zone in zip(self.polygon_annotators, self.polygon_zones):
            annotated = annotator.annotate(annotated)

        proc_time = time.time() - start
        stats = {
            "active_objects": len(self.state.active_ids),
            "total_objects": len(self.state.seen_ids),
            "entered": self.state.entered_count,
            "exited": self.state.exited_count,
            "avg_confidence": float(np.mean(self.state.all_confidences)) if self.state.all_confidences else 0.0,
            "processing_time_ms": proc_time * 1000,
            "fps": 1.0 / proc_time if proc_time > 0 else 0.0,
        }
        return annotated, stats

    # ------------------------------------------------------------------
    # Post-processing: heatmap image + CSV report
    # ------------------------------------------------------------------
    def get_heatmap_overlay(self, base_frame):
        if self.state.heatmap is None:
            return base_frame
        norm = cv2.normalize(self.state.heatmap, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        colored = cv2.applyColorMap(norm, cv2.COLORMAP_JET)
        return cv2.addWeighted(base_frame, 0.6, colored, 0.4, 0)

    def generate_report(self, out_path: str):
        rows = []
        for tid in self.state.seen_ids:
            rows.append({
                "tracker_id": tid,
                "class": self.state.class_names.get(tid, "unknown"),
                "last_confidence": self.state.confidences.get(tid, 0.0),
                "frames_tracked": len(self.state.trails.get(tid, [])),
            })
        df = pd.DataFrame(rows)
        df.to_csv(out_path, index=False)
        return df