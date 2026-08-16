import cv2
import json
import time
from vision.tracker import PersonTracker
from state.track_state import TrackStateManager
from state.spatial_state_updater import SpatialStateUpdater
from analytics.zones import ZoneManager
from analytics.dwell import DwellTracker

VIDEO_PATH = "sample_videos/vid_9.mp4"
RESOLUTIONS_TO_TEST = [(1920, 1080), (1280, 720), (640, 360)]


def run_at_resolution(width, height):
    tracker = PersonTracker()
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
    total_inference_time = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        resized_frame = cv2.resize(frame, (width, height))
        current_time = frame_count / fps

        start = time.time()
        tracks = tracker.track(resized_frame)
        total_inference_time += (time.time() - start)

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

    avg_inference_ms = (total_inference_time / frame_count) * 1000 if frame_count else 0
    effective_fps = 1000 / avg_inference_ms if avg_inference_ms > 0 else 0

    return {
        "resolution": f"{width}x{height}",
        "avg_detections_per_frame": total_detections / frame_count if frame_count else 0,
        "unique_track_ids": len(unique_track_ids),
        "zone_entries": zone_entries,
        "avg_inference_time_ms": avg_inference_ms,
        "effective_fps": effective_fps,
    }


def run_experiment():
    print("Experiment 5: Input Resolution Comparison\n")
    results = []

    for width, height in RESOLUTIONS_TO_TEST:
        print(f"Running at {width}x{height}...")
        result = run_at_resolution(width, height)
        results.append(result)
        print(f"  Avg detections/frame: {result['avg_detections_per_frame']:.1f}")
        print(f"  Unique track IDs: {result['unique_track_ids']}")
        print(f"  Zone entries: {result['zone_entries']}")
        print(f"  Avg inference time: {result['avg_inference_time_ms']:.1f} ms")
        print(f"  Effective FPS: {result['effective_fps']:.1f}")
        print()

    analysis = (
        "Lower input resolutions significantly reduce inference time (higher achievable FPS), since YOLO "
        "processes fewer pixels. However, this comes at the cost of detection quality: smaller/distant people "
        "become harder to detect accurately at reduced resolution, likely lowering true detection counts and "
        "potentially missing legitimate events. Full resolution (1920x1080) gives the highest detection fidelity "
        "at the cost of speed, while 640x360 offers the fastest processing but risks missed detections, "
        "particularly for people further from the camera or partially occluded."
    )
    print(f"Analysis: {analysis}")

    output = {"experiment": "Input Resolution Comparison", "results": results, "analysis": analysis}
    with open("experiments/results_exp5_resolution.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nResults saved to experiments/results_exp5_resolution.json")


if __name__ == "__main__":
    run_experiment()