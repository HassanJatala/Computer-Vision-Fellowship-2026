"""
run_experiment.py

Headless experiment runner -- processes a video once with a given
tracker/confidence/resolution config and appends the results as one row
to docs/tracking_experiments_log.csv. Much more reliable for running a
clean, comparable set of experiments than clicking through the Streamlit
UI multiple times.

Usage examples:

    # Experiment 1: ByteTrack baseline
    python scripts/run_experiment.py --video test.mp4 --tracker bytetrack --conf 0.3 --name exp1_bytetrack

    # Experiment 2: BoT-SORT, same settings, for direct comparison
    python scripts/run_experiment.py --video test.mp4 --tracker botsort --conf 0.3 --name exp2_botsort

    # Experiment 3: confidence threshold sweep (run several times)
    python scripts/run_experiment.py --video test.mp4 --tracker bytetrack --conf 0.15 --name exp3_conf015
    python scripts/run_experiment.py --video test.mp4 --tracker bytetrack --conf 0.30 --name exp3_conf030
    python scripts/run_experiment.py --video test.mp4 --tracker bytetrack --conf 0.50 --name exp3_conf050
    python scripts/run_experiment.py --video test.mp4 --tracker bytetrack --conf 0.70 --name exp3_conf070

    # Experiment 4: resolution sweep (resize the same source video)
    python scripts/run_experiment.py --video test.mp4 --tracker bytetrack --conf 0.3 --resize 320 --name exp4_res320
    python scripts/run_experiment.py --video test.mp4 --tracker bytetrack --conf 0.3 --resize 640 --name exp4_res640
    python scripts/run_experiment.py --video test.mp4 --tracker bytetrack --conf 0.3 --resize 1280 --name exp4_res1280
"""
import argparse
import time
from pathlib import Path
import sys

import cv2
import pandas as pd

sys.path.append(str(Path(__file__).parent))
from tracker_core import VideoAnalyticsEngine


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", type=str, required=True)
    ap.add_argument("--model", type=str, default="model/best.pt")
    ap.add_argument("--tracker", type=str, default="bytetrack", choices=["bytetrack", "botsort"])
    ap.add_argument("--conf", type=float, default=0.3)
    ap.add_argument("--track-buffer", type=int, default=60)
    ap.add_argument("--min-consecutive-frames", type=int, default=3)
    ap.add_argument("--resize", type=int, default=None,
                     help="resize frame width to this value (height scales proportionally); "
                          "omit to use the source video's native resolution")
    ap.add_argument("--name", type=str, required=True, help="experiment identifier for the log")
    ap.add_argument("--max-frames", type=int, default=None,
                     help="stop after this many frames (useful for quick tests); omit for full video")
    ap.add_argument("--log", type=str, default="docs/tracking_experiments_log.csv")
    args = ap.parse_args()

    engine = VideoAnalyticsEngine(
        args.model,
        tracker=args.tracker,
        conf_threshold=args.conf,
        track_buffer=args.track_buffer,
        minimum_consecutive_frames=args.min_consecutive_frames,
    )

    cap = cv2.VideoCapture(args.video)
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    frame_idx = 0
    frame_times = []
    start_all = time.time()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if args.max_frames and frame_idx >= args.max_frames:
            break

        if args.resize:
            scale = args.resize / orig_w
            frame = cv2.resize(frame, (args.resize, int(orig_h * scale)))

        t0 = time.time()
        _, stats = engine.process_frame(frame)
        frame_times.append(time.time() - t0)
        frame_idx += 1

        if frame_idx % 25 == 0:
            print(f"  frame {frame_idx}: active={stats['active_objects']} "
                  f"total={stats['total_objects']} entered={stats['entered']} "
                  f"exited={stats['exited']}")

    cap.release()
    total_wall_time = time.time() - start_all

    report_df = engine.generate_report(f"docs/{args.name}_report.csv")
    frames_tracked = report_df["frames_tracked"] if not report_df.empty else pd.Series([], dtype=int)

    result_row = {
        "experiment_name": args.name,
        "tracker": args.tracker,
        "conf_threshold": args.conf,
        "track_buffer": args.track_buffer,
        "min_consecutive_frames": args.min_consecutive_frames,
        "resolution_width": args.resize or orig_w,
        "frames_processed": frame_idx,
        "total_unique_objects": stats["total_objects"],
        "final_active_objects": stats["active_objects"],
        "entered": stats["entered"],
        "exited": stats["exited"],
        "avg_confidence": round(stats["avg_confidence"], 4),
        "avg_fps": round(frame_idx / total_wall_time, 2) if total_wall_time > 0 else 0,
        "avg_processing_ms_per_frame": round((sum(frame_times) / len(frame_times)) * 1000, 2) if frame_times else 0,
        "mean_frames_tracked": round(frames_tracked.mean(), 2) if len(frames_tracked) else 0,
        "median_frames_tracked": round(frames_tracked.median(), 2) if len(frames_tracked) else 0,
        "single_frame_ghost_tracks": int((frames_tracked == 1).sum()) if len(frames_tracked) else 0,
        "total_wall_time_sec": round(total_wall_time, 2),
    }

    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.exists():
        log_df = pd.read_csv(log_path)
        log_df = pd.concat([log_df, pd.DataFrame([result_row])], ignore_index=True)
    else:
        log_df = pd.DataFrame([result_row])
    log_df.to_csv(log_path, index=False)

    print("\n--- Result ---")
    for k, v in result_row.items():
        print(f"  {k}: {v}")
    print(f"\nAppended to {log_path}")
    print(f"Per-track detail saved to docs/{args.name}_report.csv")


if __name__ == "__main__":
    main()