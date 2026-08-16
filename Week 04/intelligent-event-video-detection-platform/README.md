# Intelligent Video Event Detection and Alerting Platform

A desktop app that watches a video (file, webcam, or RTSP stream) and automatically flags events like someone entering a restricted area, loitering too long, walking the wrong way, or a zone getting overcrowded — with evidence snapshots and a searchable event history.

**Author:** Muhammad Hassan
**Project:** Week 4 Challenge — Computer Vision Fellowship, Visibility Bots

---

## What It Does

Basic object detection only tells you *what* is in a frame. This platform adds a layer on top that answers *what's happening, where, and whether it matters*:

- Detects and tracks people across frames (persistent IDs, not just boxes)
- Watches configurable zones and lines for specific behaviors
- Fires one clean alert per incident — not hundreds of duplicates for the same event
- Saves proof (frame + cropped image) for every alert
- Keeps a full, filterable history in a local database

## Features

- **Video input:** file upload, webcam, or RTSP stream
- **Detection + tracking:** YOLOv8s + ByteTrack/BoT-SORT, kept separate from the alert logic
- **Zones & lines:** draw them directly on a video frame, name them, set line direction
- **Rules:** enable/disable and edit thresholds right from the UI — no code changes needed
- **Event lifecycle:** Detected → Active → Resolved, with debouncing so one incident = one event
- **Evidence:** full frame + cropped snapshot saved automatically per event
- **Dashboard:** live stats, charts, and a full event history you can filter and export

## Event Types

| Event | Fires When |
|---|---|
| **Intrusion** | Someone enters a restricted zone |
| **Loitering** | Someone stays in a zone past a set time limit |
| **Wrong Direction** | Someone crosses a line the "wrong" way |
| **Overcrowding** | Too many people in a zone at once |

## How It's Built

```
Video Source (File / Webcam / RTSP)
        ↓
   Video Ingestion (OpenCV)
        ↓
  Detection (YOLOv8)
        ↓
  Tracking (ByteTrack / BoT-SORT)
        ↓
  State Manager (per-person history, zone, dwell time)
        ↓
  Spatial Analytics (zones, lines, dwell, occupancy)
        ↓
    Rule Engine
     ↙       ↘
Event Manager   Alert Engine
     ↓              ↓
Evidence Capture   Event Database
     ↘              ↙
   Dashboard & Event History (PySide6 UI)
```

Full breakdown: `docs/Architecture_Documentation.docx`

## Tech Stack

| Piece | Tool |
|---|---|
| Detection & tracking | Ultralytics YOLOv8s, ByteTrack / BoT-SORT |
| Computer vision | OpenCV |
| Desktop UI | PySide6 (Qt for Python) |
| Charts | Matplotlib |
| Database | SQLite |
| Tests | pytest |
| Config | python-dotenv + JSON |

---

## Setting Up Zones & Lines

1. Open **Zone Editor**
2. Click **Load Frame from Video** (or Webcam / RTSP)
3. Pick **Draw Zones** or **Draw Lines**
   - Zone: left-click to add points (3+), right-click to close and name it
   - Line: left-click twice for both ends, then name it and set direction
4. Tweak anything in the **Zone Settings** / **Line Settings** panel
5. Click **Save All Zones** / **Save All Lines**

## Setting Up Rules

Go to the **Rules** tab → toggle enabled/disabled, edit severity or thresholds directly in the table → **Save Rules**. Changes apply next time you start a video (not mid-session).

## What Gets Stored Per Event

`event_id`, `event_type`, `severity`, `track_id`, `object_class`, `zone_id`, `start_time`, `end_time`, `duration`, `status`, `confidence`, `evidence_path`, `evidence_crop_path`, `source_id`

---

## Evaluation

20 test scenarios across 7 categories (normal, zone-entry, loitering, line-crossing, wrong-direction, overcrowding, edge cases).

**Result:** Precision 1.000, Recall 1.000, F1 1.000, avg detection delay 0.80s.

> ⚠️ Note: ground truth was derived from the pipeline's own verified output, not independent human labeling — treat this as a regression baseline, not a blind accuracy test. Full details in `evaluation/results.json`.

## Experiments

Five experiments run: dwell threshold, tracker comparison, confidence threshold, debouncing, input resolution.

**Highlights:**
- Debouncing cut duplicate events by 84% (75 → 12)
- ByteTrack ran ~28% faster than BoT-SORT with similar tracking quality
- Lower confidence thresholds create far more (unstable) track IDs — 91 IDs at 0.3 confidence vs. 23 at 0.7

Full results: `experiments/results_exp1.json` through `results_exp5.json`

---

## Known Limitations

- Loitering timer resets on brief zone exits instead of accumulating
- Can't edit a rule's target zone/line from the UI yet — needs a direct `rules.json` edit
- Model-loading and database-write failures aren't wrapped in error handling yet
- Tracker can occasionally swap IDs on the same person during heavy occlusion (a known ByteTrack/BoT-SORT limitation)
- Evaluation ground truth needs independent labeling for a stronger accuracy claim (see note above)

## What's Next

- Loitering time that accumulates across visits instead of resetting
- Full rule editing (zone/line target, display name) in the UI
- Proper error handling around model loading and database writes
- PPE/helmet detection layered on top of person tracking
- Independently labeled evaluation set

## Project Layout

```
intelligent-event-video-detection-platform/
├── main.py, main_window.py, pipeline.py, config.py
├── vision/          → detector.py, tracker.py, video_source.py
├── analytics/       → zones.py, lines.py, dwell.py, occupancy.py
├── rules/           → base_rule.py + 4 rule types + rule_engine.py
├── events/          → event_manager.py, evidence.py, alerts.py
├── state/           → track_state.py, spatial_state_updater.py
├── database/        → db.py, repository.py
├── tests/           → 12 automated tests (pytest)
├── evaluation/      → scenarios.json, run_evaluation.py, results.json
├── experiments/     → 5 experiment scripts + results
├── docs/            → architecture / rule / state / error docs (Word)
├── user_settings/   → zones.json, lines.json, rules.json
├── models/          → YOLO weights (not tracked in Git)
└── sample_videos/
```
