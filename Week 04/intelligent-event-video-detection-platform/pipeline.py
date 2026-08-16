import cv2
import time
import config
from vision.tracker import PersonTracker
from state.track_state import TrackStateManager
from state.spatial_state_updater import SpatialStateUpdater
from analytics.zones import ZoneManager
from analytics.dwell import DwellTracker
from analytics.lines import LineManager
from analytics.occupancy import OccupancyTracker
from rules.rule_engine import RuleEngine
from events.event_manager import EventManager
from events.evidence import EvidenceCapture
from events.alerts import AlertEngine
from live_rendering import LiveRenderer
from database.db import init_db
from database.repository import save_event


class Pipeline:
    def __init__(self, video_path=None, is_live_stream=False):
        init_db()

        self.tracker = PersonTracker()
        self.state_manager = TrackStateManager()
        self.zone_manager = ZoneManager()
        self.dwell_tracker = DwellTracker()
        self.line_manager = LineManager()
        self.occupancy_tracker = OccupancyTracker()
        self.spatial_updater = SpatialStateUpdater(self.zone_manager, self.dwell_tracker)
        self.rule_engine = RuleEngine()
        self.event_manager = EventManager(grace_period_seconds=3)
        self.evidence_capture = EvidenceCapture()
        self.alert_engine = AlertEngine()
        self.renderer = LiveRenderer(self.dwell_tracker)

        self.video_path = video_path
        self.is_live_stream = is_live_stream
        self.cap = None
        self.fps = 30
        self.frame_count = 0
        self.running = False

        # Performance tracking (Requirement 20)
        self.last_frame_time_ms = 0

    def start(self, source):
        self.cap = cv2.VideoCapture(source)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.running = True

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()

    def process_frame(self):
        """
        Processes exactly one frame. Returns (annotated_frame, active_alerts)
        or (None, []) if the video ended / read failed.
        """
        start_time = time.time()

        ret, frame = self.cap.read()
        if not ret:
            self.running = False
            return None, []

        current_time = (
            self.frame_count / self.fps if not self.is_live_stream else time.time()
        )

        tracks = self.tracker.track(frame)
        self.state_manager.update(tracks, current_time)
        all_states = self.state_manager.get_all_states()
        print(f"Frame {self.frame_count} | Active tracks: {len(all_states)}")

        new_alerts = []

        for track_id, record in all_states.items():
            spatial_result = self.spatial_updater.update(record, current_time)

            context = {
                "entered_zone": spatial_result["entered_zone"],
                "track_record": record,
                "current_time": current_time,
                "dwell_tracker": self.dwell_tracker,
                "crossing": None,
                "occupancy_tracker": self.occupancy_tracker,
                "all_track_states": all_states,
            }

            for rule in self.rule_engine.rules:
                if rule.event_type in ("intrusion", "loitering") and rule.enabled:
                    is_firing = rule.check(**context)
                    new_event = self.event_manager.process_rule_result(rule, is_firing, current_time, track_id)
                    if new_event is not None:
                        zone = self.zone_manager.get_zone(rule.zone_id) if rule.zone_id else None
                        full_path, crop_path = self.evidence_capture.capture(
                            new_event.event_id, frame, record["bbox"], new_event.detected_time, zone=zone
                        )
                        new_event.evidence_path = full_path
                        new_event.evidence_crop_path = crop_path
                        self.alert_engine.send_alert(new_event)
                        save_event(new_event, confidence=record["confidence"])
                        new_alerts.append(new_event)

            crossings = self.line_manager.check_crossing(track_id, record["position"])
            for crossing in crossings:
                for rule in self.rule_engine.rules:
                    if rule.event_type == "wrong_direction" and rule.enabled:
                        crossing_context = dict(context)
                        crossing_context["crossing"] = crossing
                        is_firing = rule.check(**crossing_context)
                        new_event = self.event_manager.process_rule_result(rule, is_firing, current_time, track_id)
                        if new_event is not None:
                            full_path, crop_path = self.evidence_capture.capture(
                                new_event.event_id, frame, record["bbox"], new_event.detected_time, zone=None
                            )
                            new_event.evidence_path = full_path
                            new_event.evidence_crop_path = crop_path
                            self.alert_engine.send_alert(new_event)
                            save_event(new_event, confidence=record["confidence"])
                            new_alerts.append(new_event)

        for zone_id in self.zone_manager.get_all_zones():
            count = self.occupancy_tracker.get_current_occupancy(zone_id, all_states)
            self.occupancy_tracker.record_sample(zone_id, count)

            occupancy_context = {
                "entered_zone": None, "track_record": None, "current_time": current_time,
                "dwell_tracker": self.dwell_tracker, "crossing": None,
                "occupancy_tracker": self.occupancy_tracker, "all_track_states": all_states,
            }
            for rule in self.rule_engine.rules:
                if rule.event_type == "overcrowding" and rule.zone_id == zone_id and rule.enabled:
                    is_firing = rule.check(**occupancy_context)
                    new_event = self.event_manager.process_rule_result(rule, is_firing, current_time)
                    if new_event is not None:
                        self.alert_engine.send_alert(new_event)
                        save_event(new_event)
                        new_alerts.append(new_event)

        self.state_manager.remove_stale_tracks(current_time, max_age_seconds=5)

        annotated_frame = self.renderer.draw(frame, self.zone_manager, all_states, current_time, line_manager=self.line_manager)

        self.frame_count += 1
        self.last_frame_time_ms = (time.time() - start_time) * 1000

        return annotated_frame, new_alerts