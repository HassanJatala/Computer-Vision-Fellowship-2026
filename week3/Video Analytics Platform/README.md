# Helmet Detection & Tracking Analytics

Real-time multi-object tracking, counting, and analytics built on top of a
**custom-trained YOLOv8 helmet detection model** (see the companion
[helmet-detection-app](../helmet-detection-app) repo for the full dataset
collection, annotation, and training pipeline).

This project extends single-frame detection into a full video analytics
system: persistent object IDs across frames, virtual line-crossing counts,
region-of-interest zone monitoring, movement trails, a live analytics
dashboard, and annotated video/report export.

## Documentation Index

| Deliverable | Location |
|---|---|
| Source Code | `app/`, `scripts/` |
| README | this file |
| Requirements | `requirements.txt` |
| Architecture Diagram | `docs/architecture_diagram.png`, `docs/System_Architecture.docx` |
| Research Report | `docs/research_report.md` |
| Performance Report | `docs/performance_report.md` |
| Tracking Experiments | `docs/tracking_experiments.md` |
| Builder Journal | `docs/Builder_Journal.docx` |
| Demo Video | [Watch on YouTube](PASTE_YOUR_YOUTUBE_LINK_HERE) |

## Why a custom model instead of a pretrained one?

A pretrained COCO-based YOLO model doesn't have `helmet`/`no_helmet`
classes at all — it only recognizes generic categories like `person`.
Using it would abandon the actual task (helmet-compliance tracking) in
favor of generic person-tracking. This project uses the author's own
YOLOv8s model (trained on a self-collected, self-annotated 528-image
dataset — see the companion detection repo), whose precision/recall
characteristics and known limitations (documented in that repo's
`docs/experiment_summary.md`) are fully understood and accounted for here
— for example, the confidence threshold is set higher (0.45 vs. a typical
0.25-0.3) specifically because the base model has a known tendency toward
false positives on cluttered backgrounds, which would otherwise create
unstable, spurious tracks in a video context.

## What's tracked

A tracker ID represents a continuously detected **head region**
(helmet or no_helmet), not a full person — this is the correct
granularity for a helmet-compliance system (e.g. "how many helmeted
heads crossed this checkpoint"), as distinct from general person-tracking
CCTV analytics.

## Features

| # | Feature | Implementation |
|---|---|---|
| 1 | Real-time detection | Custom YOLOv8s model (`model.predict()`) |
| 2 | Object tracking + unique IDs | `supervision.ByteTrack` |
| 3 | Object counter (total / active / entered / exited) | Maintained in `TrackState` |
| 4 | Virtual counting line | `supervision.LineZone` — user-defined via pixel coordinates |
| 5 | ROI zones | `supervision.PolygonZone` |
| 6 | Movement analytics (trajectory / path) | `supervision.TraceAnnotator` + per-ID centroid history |
| 7 | Analytics dashboard | Streamlit live metrics + Plotly charts |
| 8 | Video recording | `cv2.VideoWriter`, annotated frames |
| Bonus | Heatmap | Accumulated centroid density, `cv2.COLORMAP_JET` overlay |

## Required Libraries — Usage Map

| Library | Used for |
|---|---|
| Ultralytics YOLO | Custom-trained detection model + BoT-SORT native tracking |
| OpenCV | Frame I/O, drawing, video writing, heatmap colormap |
| Supervision | ByteTrack, box/label/trace annotators, LineZone, PolygonZone |
| ByteTrack | Selectable tracker option (motion-based) |
| BoT-SORT | Selectable tracker option (motion + camera-motion compensation + appearance) |
| Matplotlib | Static per-class summary bar chart (final report) |
| Plotly | Live object-count-over-time line chart during processing |

## Setup

```bash
pip install -r requirements.txt
```

Copy your trained helmet detection weights into `model/best.pt`:
```bash
copy ..\helmet-detection-app\app\model\best.pt model\best.pt
```

## Running

```bash
streamlit run app/app.py
```

1. Upload a video.
2. Enter pixel coordinates for a virtual counting line (view the displayed
   first frame to estimate coordinates), and optionally an ROI zone.
3. Click **Start Processing**, then **Process Video** to run detection +
   tracking on every frame with a live dashboard.
4. Export the annotated video and a CSV analytics report at the end.

## Comparing trackers (ByteTrack vs. BoT-SORT)

Both trackers are fully wired into the main app — select either one from
the **Tracker** dropdown in the sidebar before processing a video:

- **ByteTrack** (via `supervision.ByteTrack`) — motion-based tracking,
  fast, no appearance model.
- **BoT-SORT** (via Ultralytics' native `model.track(..., tracker="botsort.yaml")`) —
  adds camera-motion compensation and appearance-based re-identification
  on top of ByteTrack's approach, which can be more robust to brief
  occlusion at the cost of slower per-frame processing.

Run the same video with each tracker selected and compare the resulting
entered/exited counts and ID-switch behavior — this is a good basis for
an evaluation write-up (`docs/tracker_comparison.md`).

For a quick command-line comparison outside the Streamlit app:
```bash
python scripts/track_botsort_example.py --source path/to/video.mp4 --tracker botsort
python scripts/track_botsort_example.py --source path/to/video.mp4 --tracker bytetrack
```

## Known Limitations (carried over from the base detection model)

- The base model's documented background false-positive rate (~60%,
  confirmed via confusion matrix in the companion repo) can still produce
  short-lived spurious tracks even with a raised confidence threshold —
  this is a fundamental dataset-scale limitation of the underlying
  detector, not something the tracking layer alone can fully resolve.
- Occlusion or brief head turns can cause ID switches if a detection is
  lost for more than a few frames, since ByteTrack relies on continuity
  of detections to maintain identity.

## Project Structure

```
helmet-tracking-analytics/
├── app/
│   └── app.py                    <- Streamlit UI
├── model/
│   └── best.pt                   <- your trained weights (not included in repo — see Setup)
├── scripts/
│   ├── tracker_core.py           <- detection + tracking + counting + zones + trails engine
│   └── track_botsort_example.py  <- BoT-SORT vs ByteTrack comparison script
├── docs/                          <- analytics reports saved here
└── outputs/                       <- exported annotated videos + CSV reports
```
