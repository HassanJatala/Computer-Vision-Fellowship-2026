import cv2
import json
from vision.tracker import PersonTracker
from state.track_state import TrackStateManager
from state.spatial_state_updater import SpatialStateUpdater
from analytics.zones import ZoneManager
from analytics.dwell import DwellTracker
from rules.rule_engine import RuleEngine
from events.event_manager import EventManager

VIDEO_PATH = "sample_videos/vid_9.mp4"


def run_without_debouncing():
    tracker = PersonTracker()
    state_manager = TrackStateManager()
    zone_manager = ZoneManager()
    dwell_tracker = DwellTracker()
    spatial_updater = SpatialStateUpdater(zone_manager, dwell_tracker)
    rule_engine = RuleEngine()

    cap = cv2.VideoCapture(VIDEO_PATH)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30

    frame_count = 0
    raw_fire_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        current_time = frame_count / fps
        tracks = tracker.track(frame)
        state_manager.update(tracks, current_time)
        all_states = state_manager.get_all_states()

        for track_id, record in all_states.items():
            spatial_result = spatial_updater.update(record, current_time)
            context = {
                "entered_zone": spatial_result["entered_zone"], "track_record": record,
                "current_time": current_time, "dwell_tracker": dwell_tracker,
                "crossing": None, "occupancy_tracker": None, "all_track_states": all_states,
            }
            for rule in rule_engine.rules:
                if rule.event_type in ("intrusion", "loitering") and rule.enabled:
                    if rule.check(**context):
                        raw_fire_count += 1

        frame_count += 1

    cap.release()
    return raw_fire_count


def run_with_debouncing():
    tracker = PersonTracker()
    state_manager = TrackStateManager()
    zone_manager = ZoneManager()
    dwell_tracker = DwellTracker()
    spatial_updater = SpatialStateUpdater(zone_manager, dwell_tracker)
    rule_engine = RuleEngine()
    event_manager = EventManager(grace_period_seconds=3)

    cap = cv2.VideoCapture(VIDEO_PATH)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30

    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        current_time = frame_count / fps
        tracks = tracker.track(frame)
        state_manager.update(tracks, current_time)
        all_states = state_manager.get_all_states()

        for track_id, record in all_states.items():
            spatial_result = spatial_updater.update(record, current_time)
            context = {
                "entered_zone": spatial_result["entered_zone"], "track_record": record,
                "current_time": current_time, "dwell_tracker": dwell_tracker,
                "crossing": None, "occupancy_tracker": None, "all_track_states": all_states,
            }
            for rule in rule_engine.rules:
                if rule.event_type in ("intrusion", "loitering") and rule.enabled:
                    is_firing = rule.check(**context)
                    event_manager.process_rule_result(rule, is_firing, current_time, track_id)

        frame_count += 1

    cap.release()
    return len(event_manager.get_all_events())


def run_experiment():
    print("Experiment 4: Event Debouncing Comparison\n")

    raw_fires = run_without_debouncing()
    debounced_events = run_with_debouncing()

    duplicate_rate = (raw_fires - debounced_events) / raw_fires if raw_fires > 0 else 0

    print(f"Without debouncing (raw rule fires): {raw_fires}")
    print(f"With debouncing (distinct events): {debounced_events}")
    print(f"Duplicate event rate reduced: {duplicate_rate * 100:.1f}%")

    analysis = (
        f"Without debouncing, the rule engine fired {raw_fires} times total across the video, since a "
        f"continuously-true condition (e.g., ongoing loitering) re-fires every single frame. With debouncing "
        f"via EventManager's Detected->Active->Resolved lifecycle, only {debounced_events} distinct events were "
        f"created, since ongoing conditions correctly update an existing Active event rather than creating a new "
        f"one. This represents a {duplicate_rate*100:.1f}% reduction in duplicate alerts, directly validating "
        f"Requirement 13's debouncing objective."
    )
    print(f"\nAnalysis: {analysis}")

    output = {
        "experiment": "Event Debouncing Comparison",
        "raw_fires_without_debouncing": raw_fires,
        "distinct_events_with_debouncing": debounced_events,
        "duplicate_rate_reduced_percent": duplicate_rate * 100,
        "analysis": analysis,
    }
    with open("experiments/results_exp4_debouncing.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nResults saved to experiments/results_exp4_debouncing.json")


if __name__ == "__main__":
    run_experiment()