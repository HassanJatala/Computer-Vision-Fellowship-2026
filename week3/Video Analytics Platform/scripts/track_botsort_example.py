"""
track_botsort_example.py

Ultralytics YOLO has native tracking support built in (no supervision
needed) using either ByteTrack or BoT-SORT, selected via a config file.
This is a simpler alternative to tracker_core.py's supervision-based
approach -- useful for comparing the two trackers side by side, which
your Week 3 brief explicitly calls for.

Usage:
    python scripts/track_botsort_example.py --source path/to/video.mp4 --tracker botsort
    python scripts/track_botsort_example.py --source path/to/video.mp4 --tracker bytetrack
"""
import argparse
import cv2
from ultralytics import YOLO


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=str, required=True, help="video path or 0 for webcam")
    ap.add_argument("--model", type=str, default="model/best.pt")
    ap.add_argument("--tracker", type=str, default="botsort", choices=["botsort", "bytetrack"])
    ap.add_argument("--conf", type=float, default=0.3)
    args = ap.parse_args()

    model = YOLO(args.model)
    source = 0 if args.source == "0" else args.source

    # model.track() handles detection + tracking + ID assignment internally
    results_generator = model.track(
        source=source,
        conf=args.conf,
        tracker=f"{args.tracker}.yaml",  # ultralytics ships both configs built-in
        stream=True,
        persist=True,
    )

    for result in results_generator:
        annotated = result.plot()  # draws boxes + track IDs automatically
        cv2.imshow(f"Tracking ({args.tracker})", annotated)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
