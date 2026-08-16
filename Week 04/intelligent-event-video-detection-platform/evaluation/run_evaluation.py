import json
import cv2
from collections import defaultdict

from vision.tracker import PersonTracker
from state.track_state import TrackStateManager
from state.spatial_state_updater import SpatialStateUpdater
from analytics.zones import ZoneManager
from analytics.dwell import DwellTracker
from analytics.lines import LineManager
from analytics.occupancy import OccupancyTracker
from rules.rule_engine import RuleEngine
from events.event_manager import EventManager


def run_scenario(scenario):
    tracker = PersonTracker()
    state_manager = TrackStateManager()
    zone_manager = ZoneManager()
    dwell_tracker = DwellTracker()
    line_manager = LineManager()
    occupancy_tracker = OccupancyTracker()
    spatial_updater = SpatialStateUpdater(zone_manager, dwell_tracker)
    rule_engine = RuleEngine()
    event_manager = EventManager(grace_period_seconds=3)

    cap = cv2.VideoCapture(scenario["video_path"])
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    cap.set(cv2.CAP_PROP_POS_FRAMES, scenario["start_frame"])

    frame_count = scenario["start_frame"]
    actual_event_counts = defaultdict(int)
    detection_delays = []

    while frame_count < scenario["end_frame"]:
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
                "entered_zone": spatial_result["entered_zone"],
                "track_record": record,
                "current_time": current_time,
                "dwell_tracker": dwell_tracker,
                "crossing": None,
                "occupancy_tracker": occupancy_tracker,
                "all_track_states": all_states,
            }

            for rule in rule_engine.rules:
                if rule.event_type in ("intrusion", "loitering") and rule.enabled:
                    is_firing = rule.check(**context)
                    new_event = event_manager.process_rule_result(rule, is_firing, current_time, track_id)
                    if new_event is not None:
                        actual_event_counts[rule.event_type] += 1
                        detection_delays.append(current_time - scenario["start_frame"] / fps)

            crossings = line_manager.check_crossing(track_id, record["position"])
            for crossing in crossings:
                actual_event_counts["line_crossing"] += 1
                for rule in rule_engine.rules:
                    if rule.event_type == "wrong_direction" and rule.enabled:
                        crossing_context = dict(context)
                        crossing_context["crossing"] = crossing
                        is_firing = rule.check(**crossing_context)
                        new_event = event_manager.process_rule_result(rule, is_firing, current_time, track_id)
                        if new_event is not None:
                            actual_event_counts["wrong_direction"] += 1
                            detection_delays.append(current_time - scenario["start_frame"] / fps)

        for zone_id in zone_manager.get_all_zones():
            count = occupancy_tracker.get_current_occupancy(zone_id, all_states)
            occupancy_tracker.record_sample(zone_id, count)
            occupancy_context = {
                "entered_zone": None, "track_record": None, "current_time": current_time,
                "dwell_tracker": dwell_tracker, "crossing": None,
                "occupancy_tracker": occupancy_tracker, "all_track_states": all_states,
            }
            for rule in rule_engine.rules:
                if rule.event_type == "overcrowding" and rule.zone_id == zone_id and rule.enabled:
                    is_firing = rule.check(**occupancy_context)
                    new_event = event_manager.process_rule_result(rule, is_firing, current_time)
                    if new_event is not None:
                        actual_event_counts["overcrowding"] += 1
                        detection_delays.append(current_time - scenario["start_frame"] / fps)

        frame_count += 1

    cap.release()
    return actual_event_counts, detection_delays


def evaluate_all():
    with open("evaluation/scenarios.json", "r") as f:
        data = json.load(f)

    total_tp = 0
    total_fp = 0
    total_fn = 0
    all_delays = []
    per_scenario_results = []

    for scenario in data["scenarios"]:
        actual_counts, delays = run_scenario(scenario)
        all_delays.extend(delays)

        expected_counts = defaultdict(int)
        for exp in scenario["expected_events"]:
            expected_counts[exp["event_type"]] += exp["expected_count"]

        scenario_tp = 0
        scenario_fp = 0
        scenario_fn = 0

        all_types = set(list(expected_counts.keys()) + list(actual_counts.keys()))
        for event_type in all_types:
            expected = expected_counts.get(event_type, 0)
            actual = actual_counts.get(event_type, 0)
            tp = min(expected, actual)
            fp = max(0, actual - expected)
            fn = max(0, expected - actual)
            scenario_tp += tp
            scenario_fp += fp
            scenario_fn += fn

        total_tp += scenario_tp
        total_fp += scenario_fp
        total_fn += scenario_fn

        per_scenario_results.append({
            "scenario_id": scenario["scenario_id"],
            "category": scenario["category"],
            "expected": dict(expected_counts),
            "actual": dict(actual_counts),
            "true_positives": scenario_tp,
            "false_positives": scenario_fp,
            "false_negatives": scenario_fn,
        })

        print(f"{scenario['scenario_id']} ({scenario['category']}): "
              f"expected={dict(expected_counts)} actual={dict(actual_counts)} "
              f"TP={scenario_tp} FP={scenario_fp} FN={scenario_fn}")

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    avg_delay = sum(all_delays) / len(all_delays) if all_delays else 0

    print("\n--- Aggregate Metrics ---")
    print(f"Total TP: {total_tp}, FP: {total_fp}, FN: {total_fn}")
    print(f"Precision: {precision:.3f}")
    print(f"Recall: {recall:.3f}")
    print(f"F1 Score: {f1:.3f}")
    print(f"Average Detection Delay: {avg_delay:.2f}s")

    results = {
        "per_scenario": per_scenario_results,
        "aggregate": {
            "total_tp": total_tp, "total_fp": total_fp, "total_fn": total_fn,
            "precision": precision, "recall": recall, "f1_score": f1,
            "average_detection_delay_seconds": avg_delay,
        }
    }
    with open("evaluation/results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\nFull results saved to evaluation/results.json")


if __name__ == "__main__":
    evaluate_all()