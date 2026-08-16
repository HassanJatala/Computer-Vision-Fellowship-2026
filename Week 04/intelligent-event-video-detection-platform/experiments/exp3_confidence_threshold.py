import cv2
import json
from vision.tracker import PersonTracker
from state.track_state import TrackStateManager
from state.spatial_state_updater import SpatialStateUpdater
from analytics.zones import ZoneManager
from analytics.dwell import DwellTracker

VIDEO_PATH = "sample_videos/vid_9.mp4"
CONFIDENCE_THRESHOLDS = [0.3, 0.5, 0.7]


def run_with_confidence(confidence):
    tracker = PersonTracker(confidence=confidence)
    state_manager = TrackStateManager()
    zone_manager = ZoneManager()
    dwell_tracker = DwellTracker()
    spatial_updater = SpatialStateUpdater(zone_manager, dwell_tracker)

    cap = cv2.VideoCapture(VIDEO_PATH)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30

    frame_count = 0
    total_detections = 0
    unique_track_ids = set()
    zone_entries = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = frame_count / fps
        tracks = tracker.track(frame)
        total_detections += len(tracks)

        state_manager.update(tracks, current_time)
        all_states = state_manager.get_all_states()

        for track_id, record in all_states.items():
            unique_track_ids.add(track_id)
            result = spatial_updater.update(record, current_time)
            if result["entered_zone"]:
                zone_entries += 1

        frame_count += 1

    cap.release()
    avg_detections_per_frame = total_detections / frame_count if frame_count else 0

    return {
        "confidence": confidence,
        "avg_detections_per_frame": avg_detections_per_frame,
        "unique_track_ids": len(unique_track_ids),
        "zone_entries": zone_entries,
    }


def run_experiment():
    print("Experiment 3: Confidence Threshold Comparison\n")
    results = []

    for confidence in CONFIDENCE_THRESHOLDS:
        print(f"Running with confidence={confidence}...")
        result = run_with_confidence(confidence)
        results.append(result)
        print(f"  Avg detections per frame: {result['avg_detections_per_frame']:.1f}")
        print(f"  Unique track IDs: {result['unique_track_ids']}")
        print(f"  Zone entry events: {result['zone_entries']}")
        print()

    analysis = (
        "Lower confidence thresholds detect more objects per frame (fewer missed detections) but "
        "risk including false-positive detections (background clutter misidentified as a person), which can "
        "inflate track counts and trigger spurious events. Higher thresholds reduce false positives but risk "
        "missing genuine but lower-confidence detections (e.g., partially occluded people), potentially "
        "causing missed events."
    )
    print(f"Analysis: {analysis}")

    output = {"experiment": "Confidence Threshold Comparison", "results": results, "analysis": analysis}
    with open("experiments/results_exp3_confidence_threshold.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nResults saved to experiments/results_exp3_confidence_threshold.json")


if __name__ == "__main__":
    run_experiment()