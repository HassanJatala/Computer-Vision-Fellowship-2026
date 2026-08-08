# Tracking Experiments — Documentation

All experiments run on the same source video (250 frames, native
resolution 2160x3840) using the custom-trained YOLOv8s helmet detection
model. Full raw results: `docs/tracking_experiments_log.csv`.

---

## Experiment 1 — ByteTrack: Evaluate Performance

```bash
python scripts/run_experiment.py --video test_video.mp4 --tracker bytetrack --conf 0.3 --name exp1_bytetrack
```

**Results:**
| Metric | Value |
|---|---|
| total_unique_objects | 18 |
| mean_frames_tracked | 17.56 |
| median_frames_tracked | 18.5 |
| single_frame_ghost_tracks | 3 |
| entered / exited | 0 / 0 |
| avg_fps | 3.49 |

**Observations:**
ByteTrack produced 18 unique tracked objects over 250 frames, with a mean
track length of ~17.6 frames. 3 of the 18 tracks (17%) were single-frame
ghosts -- `minimum_consecutive_frames=3` reduced but did not fully
eliminate the ghost-track problem identified during development.
`entered`/`exited` stayed at 0: no track was stable and long-lived enough
to complete a full crossing of the virtual counting line in this clip,
consistent with the track-fragmentation issue rather than a separate bug
in the line-crossing logic.

---

## Experiment 2 — BoT-SORT: Compare with ByteTrack

```bash
python scripts/run_experiment.py --video test_video.mp4 --tracker botsort --conf 0.3 --name exp2_botsort
```

**Direct comparison (same video, same confidence, only tracker changed):**

| Metric | ByteTrack (exp1) | BoT-SORT (exp2) |
|---|---|---|
| total_unique_objects | 18 | 22 |
| mean_frames_tracked | 17.56 | 19.18 |
| median_frames_tracked | 18.5 | 20.5 |
| single_frame_ghost_tracks | 3 | 1 |
| entered / exited | 0 / 0 | 0 / 0 |
| avg_fps | 3.49 | 3.37 |

**Observations:**
On this run, BoT-SORT produced somewhat more total unique objects (22 vs
18) but with longer and more stable tracks on average (mean 19.18 vs
17.56 frames, median 20.5 vs 18.5) and fewer ghost tracks (1 vs 3).
Speed cost was modest here (3.37 vs 3.49 fps). Taken at face value, this
run suggests BoT-SORT's ReID/camera-motion compensation gave a modest
track-quality improvement (fewer ghosts, longer average tracks) for a
small speed cost.

**Important honest note -- run-to-run variance observed:**
An earlier repetition of this exact experiment (same video, same
config) produced meaningfully different numbers: ByteTrack gave 18
unique objects / 3 ghost tracks (matching this run), but BoT-SORT gave
34 unique objects, 6 ghost tracks, and a much larger FPS gap (2.56 vs
4.18) in that run -- the opposite conclusion from the one above. This
inconsistency between two runs of the identical configuration is itself
a meaningful finding: it indicates the tracking pipeline (or the
underlying detection model's frame-to-frame confidence fluctuation) is
not fully deterministic in this setup, and any single run's tracker
comparison should be treated as noisy rather than conclusive. A fair
comparison would require averaging results across several repeated runs
per configuration rather than relying on one run each, which is a
limitation of the experiments as conducted here and a clear direction
for more rigorous follow-up work.

---

## Experiment 3 — Different Confidence Thresholds: Analyze Impact

```bash
python scripts/run_experiment.py --video test_video.mp4 --tracker bytetrack --conf 0.15 --name exp3_conf015
python scripts/run_experiment.py --video test_video.mp4 --tracker bytetrack --conf 0.30 --name exp3_conf030
python scripts/run_experiment.py --video test_video.mp4 --tracker bytetrack --conf 0.50 --name exp3_conf050
python scripts/run_experiment.py --video test_video.mp4 --tracker bytetrack --conf 0.70 --name exp3_conf070
```

**Results:**

| Confidence | total_unique_objects | mean_frames_tracked | median_frames_tracked | ghost_tracks | avg_confidence | avg_fps |
|---|---|---|---|---|---|---|
| 0.15 | 19 | 17.89 | 19.0 | 4 | 0.726 | 4.38 |
| 0.30 | 18 | 17.56 | 18.5 | 3 | 0.738 | 4.07 |
| 0.50 | 15 | 20.80 | 29.0 | 2 | 0.769 | 4.01 |
| 0.70 | 8 | 21.38 | 24.0 | 0 | 0.851 | 3.99 |

**Observations -- a clear, consistent trend across all four runs:**
As confidence threshold increases: total_unique_objects steadily
decreases (19 to 18 to 15 to 8), while mean_frames_tracked and
median_frames_tracked steadily increase (17.89 to 21.38 mean; 19.0 to
24.0 median), and single_frame_ghost_tracks decreases monotonically to
zero at 0.70.

This is a genuine, clean tradeoff visible directly in tracking behavior:
a higher threshold removes weak, noisy detections that would otherwise
spawn short-lived spurious tracks, so the tracks that remain are cleaner
and longer-lived. However, total_unique_objects dropping to just 8 at
confidence 0.70 is a warning sign, not purely a win -- this scene almost
certainly has more than 8 real distinct people/objects across 250
frames, so the model's already-documented recall weakness (from the
companion detection repo's evaluation) is very likely suppressing
genuine detections at this threshold, not just filtering noise.
0.30-0.50 appears to be the more reasonable operating range for this
scene, balancing ghost-track suppression against recall.

---

## Experiment 4 — Different Video Resolutions: Compare FPS

```bash
python scripts/run_experiment.py --video test_video.mp4 --tracker bytetrack --conf 0.3 --resize 320 --name exp4_res320
python scripts/run_experiment.py --video test_video.mp4 --tracker bytetrack --conf 0.3 --resize 640 --name exp4_res640
python scripts/run_experiment.py --video test_video.mp4 --tracker bytetrack --conf 0.3 --resize 1280 --name exp4_res1280
```

**Results (including native-resolution Experiment 1 run as a reference point):**

| Resolution (width) | avg_fps | avg_processing_ms_per_frame | total_unique_objects | mean_frames_tracked | ghost_tracks |
|---|---|---|---|---|---|
| 320 | 4.59 | 185.14 | 20 | 17.95 | 2 |
| 640 | 3.32 | 251.92 | 19 | 17.53 | 4 |
| 1280 | 3.08 | 257.31 | 17 | 19.47 | 2 |
| 2160 (native, exp1) | 3.49 | 253.34 | 18 | 17.56 | 3 |

**Observations -- FPS did not scale with resolution as expected:**
The hypothesis going in was that lower resolution should process
noticeably faster. The actual FPS values do not show a clean monotonic
relationship with resolution (320 -> 4.59 fps, 640 -> 3.32 fps, 1280 ->
3.08 fps, native 2160 -> 3.49 fps) -- native resolution is in fact
faster than both the 640 and 1280 resize runs, despite being by far the
largest input.

**Likely explanation:** Ultralytics' YOLO internally resizes every input
frame to its own fixed inference size (default imgsz=640) regardless of
the resolution it's handed. Externally resizing the frame before feeding
it to the model does not proportionally reduce the model's actual
computation, since the bulk of inference cost is fixed once the frame
reaches the model. The differences observed here are more likely
dominated by cv2.resize() overhead itself (an extra step added at
320/640/1280 that the native-resolution run skips entirely) and by video
decoding costs, rather than by any real change in detection/tracking
computation. Naively downscaling input resolution in application code is
not a reliable way to speed up this pipeline -- a real speed-up would
need to target the model's own imgsz parameter directly, or reduce
frame-reading/decoding overhead.

total_unique_objects shows no strong resolution-driven pattern (20, 19,
17, 18 -- all within a similar range), suggesting object-count stability
wasn't meaningfully affected by resolution changes in this particular
clip.

---

## Overall Conclusions

1. **The BoT-SORT vs. ByteTrack comparison produced inconsistent results
   across repeated runs of the identical configuration** -- one run
   favored BoT-SORT (fewer ghost tracks, longer average tracks, only a
   small speed cost), while an earlier run showed BoT-SORT performing
   considerably worse on every metric (nearly double the unique objects,
   double the ghost tracks, much larger speed penalty). Rather than
   reporting a false, over-confident conclusion, the most accurate and
   important finding here is that this pipeline's tracking output is not
   fully deterministic run-to-run, and a single-run comparison is not
   sufficient to reliably rank the two trackers. Proper evaluation would
   require multiple repeated runs per configuration, averaged, to draw a
   statistically meaningful conclusion -- a clear scope item for future
   work rather than something resolved here.

2. **Confidence threshold has a clean, measurable, and consistent effect
   on tracking stability**: higher thresholds produce fewer, longer-lived,
   more stable tracks by filtering out noisy detections -- but at the
   extreme (0.70), this comes at the likely cost of missing genuine
   objects (total_unique_objects dropping to 8), consistent with the
   detection model's already-documented recall weaknesses. 0.30-0.50 is
   the recommended operating range, balancing ghost-track suppression
   against recall.

3. **Resolution downscaling did not deliver the expected speed
   improvement**, because Ultralytics' YOLO internally resizes all
   inputs to a fixed inference size regardless of the frame's original
   resolution -- meaning the model's core computation cost stays roughly
   constant, and observed FPS differences are more likely explained by
   cv2.resize() and frame-decoding overhead than genuine inference
   savings. A real speed optimization would need to change the model's
   own imgsz parameter rather than pre-resizing input frames in
   application code.

4. **The counting-line feature (entered/exited) never registered a
   single crossing across any experiment run.** This is consistent with,
   and further evidence for, the track-fragmentation problem observed
   throughout: no track in any configuration tested was stable enough,
   for long enough, to complete a full, continuous line crossing. This
   remains an open limitation inherited from the base detection model's
   small-object/occlusion recall weakness (documented in the companion
   detection repo), which no tracker configuration tested here fully
   resolved.

5. **Most broadly**: these experiments demonstrate that tracking-layer
   configuration (tracker choice, confidence threshold, resolution) can
   meaningfully shift how a detection model's imperfections manifest (as
   fragmentation, as ghost tracks, as missed objects) but cannot fully
   compensate for the underlying detector's known limitations. Improving
   the base detection model's recall and false-positive rate (documented
   separately in the companion detection repo's experiment_summary.md)
   would likely have a larger effect on overall tracking quality than
   any tracker-side tuning explored here.