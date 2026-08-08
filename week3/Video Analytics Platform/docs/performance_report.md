# Performance Report — Helmet Detection & Tracking Analytics

Formal summary of speed and resource benchmarks measured during
development and experimentation. For methodology and per-experiment
analysis, see `tracking_experiments.md`. For detection-model accuracy
(precision/recall/mAP), see the companion detection repo's
`experiment_summary.md` — this report covers the *tracking pipeline's*
runtime performance specifically.

## Test Environment

- CPU: Intel Core i5-8365U @ 1.60GHz (no GPU acceleration used)
- Source video: 250 frames, native resolution 2160x3840
- Model: custom-trained YOLOv8s (helmet / no_helmet, 2 classes)

## Throughput by Tracker

| Tracker | avg FPS | avg ms/frame |
|---|---|---|
| ByteTrack | 3.49 - 4.18 | 204 - 253 |
| BoT-SORT | 2.56 - 3.37 | 258 - 360 |

BoT-SORT consistently ran slower than ByteTrack across repeated runs, by
roughly 20-40%, attributable to its added camera-motion compensation and
appearance (ReID) computation performed every frame. On CPU-only
hardware, this gap is significant enough to matter for any
near-real-time deployment target.

## Throughput by Input Resolution

| Resolution (width) | avg FPS | avg ms/frame |
|---|---|---|
| 320 | 4.59 | 185.14 |
| 640 | 3.32 | 251.92 |
| 1280 | 3.08 | 257.31 |
| 2160 (native) | 3.49 | 253.34 |

**Finding:** FPS did not scale monotonically with resolution as
expected — native resolution (2160) outperformed both the 640 and 1280
resize configurations. Root cause: Ultralytics' YOLO internally resizes
every input frame to its own fixed inference size (`imgsz`, default 640)
regardless of the frame's original resolution, so the model's core
computation cost is roughly constant across all tested resolutions. The
differences observed are more likely explained by `cv2.resize()` overhead
and frame-decoding cost than genuine inference savings. **Practical
implication: pre-resizing frames in application code is not a reliable
speed-optimization strategy for this pipeline** — a real speed
improvement would need to change the model's own `imgsz` parameter.

## Throughput by Confidence Threshold

| Confidence | avg FPS |
|---|---|
| 0.15 | 4.38 |
| 0.30 | 4.07 |
| 0.50 | 4.01 |
| 0.70 | 3.99 |

Confidence threshold had only a marginal effect on FPS (within ~10%
across the full range tested) — as expected, since threshold filtering
happens after the (fixed-cost) inference pass, not before it. Threshold
choice should therefore be driven by tracking-quality tradeoffs (see
`tracking_experiments.md`, Experiment 3), not by performance
considerations.

## Training Performance Anomaly (Detection Model, Historical)

During the companion detection model's third training run (yolov8s, 50
epochs), total training time was 46.3 hours against an expected ~3.5
hours (based on the first two runs on identical hardware). Per-epoch
logs showed several epochs spiking from a normal ~30 seconds/iteration to
over 1,000 seconds/iteration. This is attributed to the training machine
sleeping or thermal throttling mid-run rather than any change in
workload, and is not representative of yolov8s's normal training speed
on this hardware. Documented here as a practical operational lesson:
long unattended jobs require explicit power/sleep-setting precautions.

## Summary

| Bottleneck | Cause | Mitigation applied |
|---|---|---|
| BoT-SORT ~20-40% slower than ByteTrack | ReID + camera-motion compensation compute cost | Selectable per-use-case; ByteTrack recommended as default for this dataset (see tracking_experiments.md) |
| Resolution downscaling did not improve FPS | YOLO's fixed internal `imgsz` dominates compute cost | Documented as a known limitation; true speed-up would require changing model `imgsz`, not pre-resizing |
| 46-hour anomalous training run | Machine sleep/thermal throttling | Operational precaution for future long runs (keep device awake and cool) |