# Research Report — Multi-Object Tracking for Helmet Compliance Analytics

## 1. Problem Context

Detecting a helmet in a single image tells you whether one person, in one
frame, is compliant. It says nothing about *how many distinct people*
passed through a scene, whether they crossed a checkpoint, or how long
they stayed in a zone. Answering those questions requires tracking:
assigning a persistent identity to each detected object across
consecutive frames, so that the same physical person is counted once,
not once per frame they appear in.

## 2. Tracking Algorithms Researched

### ByteTrack
ByteTrack is a motion-based, detection-associated tracker. Its key
insight is using *low-confidence* detections (which most trackers
discard) as secondary evidence for continuing an existing track, rather
than only matching high-confidence boxes. It associates detections
across frames primarily using Intersection-over-Union (IoU) and a Kalman
filter motion model — no appearance/visual features are used. This makes
it fast and simple, but purely motion-based, so it can struggle when
objects move erratically or overlap heavily during occlusion.

### BoT-SORT
BoT-SORT extends the same core association approach with two additions:
**camera motion compensation** (correcting for camera movement/shake so
motion prediction stays accurate) and **appearance-based re-identification
(ReID)** — a learned visual embedding used to re-match an object to its
previous identity after it's lost for a few frames (e.g. due to
occlusion). This theoretically makes it more robust in exactly the
scenarios ByteTrack struggles with, at the cost of extra computation per
frame.

### Other trackers considered but not used
- **SORT** (the predecessor to both algorithms above) — pure Kalman
  filter + Hungarian matching, no low-confidence detection recovery.
  Simpler and faster than either option used, but generally less
  accurate under occlusion than ByteTrack.
- **DeepSORT** — adds a ReID embedding on top of SORT, similar in spirit
  to BoT-SORT but with an older, separately-trained appearance model
  rather than BoT-SORT's integrated approach. Not used here since
  BoT-SORT (available natively through Ultralytics) offered equivalent
  capability with less integration overhead.

## 3. Why `supervision` + Ultralytics Native Tracking

The `supervision` library was chosen for ByteTrack because it provides a
clean, well-maintained Python API (`sv.ByteTrack`) plus ready-made
annotators for boxes, labels, traces, line zones, and polygon zones —
covering most of the required application features (virtual counting
line, ROI zones, movement trails) without writing custom geometry code.
BoT-SORT was used via Ultralytics' own native `model.track()` method,
since Ultralytics ships and maintains the tracker directly and it
integrates without requiring a second detection pass.

## 4. Application to This Project

This project's detector produces two classes (`helmet`, `no_helmet`)
representing head regions, not full people. Tracking at this level of
granularity is appropriate for the compliance use case ("how many
helmeted heads crossed this checkpoint") but is more fragile than
person-level tracking would be, since a head region is smaller, more
easily occluded, and more prone to detection confidence fluctuating near
threshold — all factors that surfaced directly during the tracking
experiments documented in `tracking_experiments.md`.

## 5. Key Takeaway

The choice of tracker is not purely theoretical: BoT-SORT's ReID
advantage assumes objects are visually distinguishable from one another.
In a dense, visually homogeneous crowd — common in real helmet-compliance
scenes (construction sites, traffic) — that assumption weakens, which is
exactly what this project's own experiments observed (see
`tracking_experiments.md`, Experiment 2). Research alone does not
guarantee which tracker performs best for a specific dataset and scene;
empirical testing on the actual target domain remains necessary.