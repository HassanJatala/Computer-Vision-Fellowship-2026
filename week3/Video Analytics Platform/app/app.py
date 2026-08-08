"""
app.py — Intelligent Video Analytics Platform

Run with:
    streamlit run app/app.py
"""
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from PIL import Image
from streamlit_image_coordinates import streamlit_image_coordinates

sys.path.append(str(Path(__file__).parent.parent / "scripts"))
from tracker_core import VideoAnalyticsEngine

st.set_page_config(page_title="Helmet Tracking Analytics", page_icon="⛑️", layout="wide")

MODEL_PATH = Path(__file__).parent.parent / "model" / "best.pt"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

st.title("⛑️ Helmet Detection & Tracking Analytics")
st.caption("Real-time helmet/no_helmet detection with multi-object tracking, "
           "counting, virtual line crossing, and zone analytics — built on a "
           "custom-trained YOLOv8 model.")
st.info("**Note on what's tracked**: this system tracks *detected helmet/"
        "no_helmet regions* (heads), not full people. A tracker ID "
        "represents a continuously detected head across frames, which is "
        "the right granularity for helmet-compliance analytics (e.g. "
        "\"how many helmeted heads crossed this checkpoint\").")

# ---------------------------------------------------------------------------
# Sidebar configuration
# ---------------------------------------------------------------------------
st.sidebar.header("Configuration")

if not MODEL_PATH.exists():
    st.sidebar.error(f"No model found at {MODEL_PATH}. Copy your trained "
                      f"helmet-detection weights (best.pt) there.")
    st.stop()

st.sidebar.caption("Choose which tracking algorithm to use — both are fully wired.")
tracker_choice = st.sidebar.selectbox(
    "Tracker",
    ["bytetrack", "botsort"],
    help="ByteTrack: motion-based, fast, supervision library. "
         "BoT-SORT: adds camera-motion compensation + appearance features "
         "on top of ByteTrack's approach — can be more robust to occlusion "
         "when the camera moves and a domain-matched Re-ID model is used, "
         "at the cost of slower per-frame processing. Runs via Ultralytics' "
         "native tracking. NOTE: for this fixed-camera / helmet-crop setup, "
         "camera-motion compensation and Re-ID are disabled by default in "
         "tracker_core.py (gmc_method: none, with_reid: False) since this "
         "footage has a static camera and no helmet-specific Re-ID model has "
         "been trained — BoT-SORT here is effectively 'ByteTrack-style "
         "matching with BoT-SORT's Kalman refinements' unless you "
         "re-enable those options for footage where they'd help."
)
conf_threshold = st.sidebar.slider(
    "Confidence Threshold", 0.05, 0.95, 0.30, 0.05,
    help="Lowered from an earlier default of 0.45. Diagnosis on real "
         "footage showed detections sitting at 0.46-0.59 confidence, "
         "right at a 0.45 cutoff, causing them to flicker in/out of "
         "existence frame-to-frame and fragment track identity. A lower "
         "threshold keeps marginal-but-real detections consistently "
         "present, which matters more for tracking stability than "
         "filtering out some extra noise. This value now also drives "
         "BoT-SORT's track_high_thresh/new_track_thresh directly (see "
         "tracker_core.py), so both trackers start from the same "
         "detection floor."
)
min_consecutive_frames = st.sidebar.slider(
    "Track Confirmation Frames", 1, 5, 2, 1,
    help="How many consecutive matched frames before a detection becomes "
         "a confirmed track. Higher values suppress ghost/flicker tracks "
         "but can suppress real objects on footage with lower or "
         "inconsistent detection confidence. Lower values catch more real "
         "objects but let noise through as phantom tracks. Tune per video."
)
track_buffer = st.sidebar.slider(
    "Track Buffer (frames)", 15, 120, 60, 5,
    help="How many frames a track is kept alive while unmatched (e.g. "
         "during occlusion) before it's deleted and a new ID is issued "
         "on reappearance. Raise this for dense/occluded scenes where "
         "people briefly disappear behind others; lower it if IDs are "
         "sticking around too long after an object has genuinely left."
)
enable_heatmap = st.sidebar.checkbox("Enable Heatmap (bonus)", value=False)

uploaded_video = st.file_uploader("Upload a video", type=["mp4", "avi", "mov"])

if "engine" not in st.session_state:
    st.session_state.engine = None
if "line_points" not in st.session_state:
    st.session_state.line_points = []
if "zone_points" not in st.session_state:
    st.session_state.zone_points = []
if "stats_history" not in st.session_state:
    st.session_state.stats_history = []

# ---------------------------------------------------------------------------
# Step 1: draw line / zone on first frame
# ---------------------------------------------------------------------------
if uploaded_video and st.session_state.engine is None:
    tmp_path = Path("temp_input_video.mp4")
    tmp_path.write_bytes(uploaded_video.read())

    cap = cv2.VideoCapture(str(tmp_path))
    ret, first_frame = cap.read()
    cap.release()

    if ret:
        st.subheader("Step 1 — Define counting line and ROI zone")
        st.caption("Enter pixel coordinates for the virtual counting line (a straight "
                   "line objects will cross) and an optional ROI zone polygon. "
                   "Tip: view the frame below to estimate coordinates.")

        h, w = first_frame.shape[:2]
        st.image(cv2.cvtColor(first_frame, cv2.COLOR_BGR2RGB),
                  caption=f"First frame ({w}x{h}) — use this to pick coordinates",
                  use_container_width=True)

        st.markdown("**Click two corners to draw the checkpoint** — click once for the "
                    "top-left corner, then click again for the bottom-right corner, "
                    "directly on the frame below.")

        # Display is capped for usability; scale click coordinates back to
        # the real frame size (w, h) afterward.
        display_w = min(w, 900)
        scale = display_w / w
        display_h = int(h * scale)
        pil_frame = Image.fromarray(cv2.cvtColor(first_frame, cv2.COLOR_BGR2RGB)).resize((display_w, display_h))

        if "checkpoint_clicks" not in st.session_state:
            st.session_state.checkpoint_clicks = []
        if "checkpoint_last_raw" not in st.session_state:
            st.session_state.checkpoint_last_raw = None

        # Draw whatever's been clicked so far onto the preview image before
        # showing it, so the person sees their progress.
        preview_img = np.array(pil_frame).copy()
        for (px, py) in st.session_state.checkpoint_clicks:
            cv2.circle(preview_img, (px, py), 6, (255, 255, 0), -1)
        if len(st.session_state.checkpoint_clicks) == 2:
            (ax, ay), (bx, by) = st.session_state.checkpoint_clicks
            cv2.rectangle(preview_img, (ax, ay), (bx, by), (255, 255, 0), 3)
        preview_pil = Image.fromarray(preview_img)

        click_value = streamlit_image_coordinates(preview_pil, key="checkpoint_img")

        if click_value is not None and click_value != st.session_state.checkpoint_last_raw:
            st.session_state.checkpoint_last_raw = click_value
            if len(st.session_state.checkpoint_clicks) >= 2:
                # A 3rd click starts a fresh rectangle rather than accumulating.
                st.session_state.checkpoint_clicks = []
            st.session_state.checkpoint_clicks.append((click_value["x"], click_value["y"]))
            st.rerun()

        cx1 = cy1 = cx2 = cy2 = None
        if len(st.session_state.checkpoint_clicks) == 2:
            (ax, ay), (bx, by) = st.session_state.checkpoint_clicks
            # Scale click coordinates (in display space) back to the real
            # frame's pixel coordinates, and normalize so top-left/bottom-
            # right are correct regardless of click order.
            rx1, ry1 = min(ax, bx) / scale, min(ay, by) / scale
            rx2, ry2 = max(ax, bx) / scale, max(ay, by) / scale
            cx1, cy1, cx2, cy2 = int(rx1), int(ry1), int(rx2), int(ry2)
            st.success(f"Checkpoint set: top-left ({cx1}, {cy1}) → bottom-right ({cx2}, {cy2})")
            if st.button("Clear checkpoint and redraw"):
                st.session_state.checkpoint_clicks = []
                st.rerun()
        elif len(st.session_state.checkpoint_clicks) == 1:
            st.info("First corner placed — click the opposite corner to complete the rectangle.")
        else:
            st.info("Click a corner on the frame above to start drawing the checkpoint.")

        use_zone = st.checkbox("Also draw an optional ROI zone (dwell-time tracking)")
        zx1 = zy1 = zx2 = zy2 = None
        if use_zone:
            st.markdown("**Click two corners to draw the ROI zone.**")
            if "zone_clicks" not in st.session_state:
                st.session_state.zone_clicks = []
            if "zone_last_raw" not in st.session_state:
                st.session_state.zone_last_raw = None

            zone_preview_img = np.array(pil_frame).copy()
            for (px, py) in st.session_state.zone_clicks:
                cv2.circle(zone_preview_img, (px, py), 6, (255, 165, 0), -1)
            if len(st.session_state.zone_clicks) == 2:
                (ax, ay), (bx, by) = st.session_state.zone_clicks
                cv2.rectangle(zone_preview_img, (ax, ay), (bx, by), (255, 165, 0), 3)
            zone_preview_pil = Image.fromarray(zone_preview_img)

            zone_click_value = streamlit_image_coordinates(zone_preview_pil, key="zone_img")

            if zone_click_value is not None and zone_click_value != st.session_state.zone_last_raw:
                st.session_state.zone_last_raw = zone_click_value
                if len(st.session_state.zone_clicks) >= 2:
                    st.session_state.zone_clicks = []
                st.session_state.zone_clicks.append((zone_click_value["x"], zone_click_value["y"]))
                st.rerun()

            if len(st.session_state.zone_clicks) == 2:
                (ax, ay), (bx, by) = st.session_state.zone_clicks
                rzx1, rzy1 = min(ax, bx) / scale, min(ay, by) / scale
                rzx2, rzy2 = max(ax, bx) / scale, max(ay, by) / scale
                zx1, zy1, zx2, zy2 = int(rzx1), int(rzy1), int(rzx2), int(rzy2)
                st.success(f"ROI zone set: top-left ({zx1}, {zy1}) → bottom-right ({zx2}, {zy2})")
                if st.button("Clear zone and redraw"):
                    st.session_state.zone_clicks = []
                    st.rerun()
            elif len(st.session_state.zone_clicks) == 1:
                st.info("First corner placed — click the opposite corner to complete the rectangle.")
            else:
                st.info("Click a corner on the frame above to start drawing the ROI zone.")

        if st.button("Start Processing", disabled=cx1 is None):
            engine = VideoAnalyticsEngine(
                str(MODEL_PATH),
                tracker=tracker_choice,
                conf_threshold=conf_threshold,
                track_buffer=track_buffer,
                minimum_consecutive_frames=min_consecutive_frames, 
            )
            engine.set_checkpoint((cx1, cy1), (cx2, cy2))
            if use_zone and zx1 is not None:
                zone_poly = [(zx1, zy1), (zx2, zy1), (zx2, zy2), (zx1, zy2)]
                engine.add_roi_zone(zone_poly, first_frame.shape)
            if enable_heatmap:
                engine.init_heatmap(first_frame.shape)

            st.session_state.engine = engine
            st.session_state.video_path = str(tmp_path)
            st.rerun()

# ---------------------------------------------------------------------------
# Step 2: process video with live dashboard
# ---------------------------------------------------------------------------
if st.session_state.engine is not None:
    st.subheader("Step 2 — Live Processing & Analytics Dashboard")

    engine = st.session_state.engine
    cap = cv2.VideoCapture(st.session_state.video_path)
    fps_in = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out_path = OUTPUT_DIR / "annotated_output.mp4"
    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps_in, (w, h))

    frame_placeholder = st.empty()
    dashboard_placeholder = st.empty()
    progress = st.progress(0)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    run = st.button("Process Video")

    if run:
        frame_idx = 0
        last_annotated = None
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            print(f"[DEBUG] frame_idx={frame_idx} shape={frame.shape} mean={frame.mean():.2f}")  # <-- new line
            annotated, stats = engine.process_frame(frame)
            print(f"[DEBUG] stats={stats}")  # <-- new line
            last_annotated = annotated
            writer.write(annotated)
            st.session_state.stats_history.append(stats)

            frame_idx += 1
            if frame_idx % 3 == 0:  # throttle UI updates for speed
                frame_placeholder.image(
                    cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB),
                    caption=f"Frame {frame_idx}/{total_frames}",
                    use_container_width=True,
                )
                with dashboard_placeholder.container():
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("Active Objects", stats["active_objects"])
                    c2.metric("Total Objects", stats["total_objects"])
                    c3.metric("Entered (IN)", stats["entered"])
                    c4.metric("Exited (OUT)", stats["exited"])
                    c5.metric("FPS", f"{stats['fps']:.1f}")
                progress.progress(min(frame_idx / max(total_frames, 1), 1.0))

        cap.release()
        writer.release()

        st.success(f"Processing complete! (Tracker used: **{engine.tracker_name}**)")
        final_stats = st.session_state.stats_history[-1]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Unique Objects", final_stats["total_objects"])
        c2.metric("Entered (IN)", final_stats["entered"])
        c3.metric("Exited (OUT)", final_stats["exited"])
        c4.metric("Avg Confidence", f"{final_stats['avg_confidence']:.2%}")

        df = pd.DataFrame(st.session_state.stats_history)
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=df["active_objects"], mode="lines", name="Active Objects"))
        fig.add_trace(go.Scatter(y=df["total_objects"], mode="lines", name="Total Objects"))
        fig.update_layout(title="Object Count Over Time", xaxis_title="Frame", yaxis_title="Count")
        st.plotly_chart(fig, use_container_width=True)

        if enable_heatmap and last_annotated is not None:
            heatmap_overlay = engine.get_heatmap_overlay(last_annotated)
            st.subheader("Movement Heatmap (bonus)")
            st.image(cv2.cvtColor(heatmap_overlay, cv2.COLOR_BGR2RGB), use_container_width=True)

        with open(out_path, "rb") as f:
            st.download_button("Export annotated video", data=f.read(),
                                file_name="annotated_output.mp4", mime="video/mp4")

        report_path = OUTPUT_DIR / "analytics_report.csv"
        report_df = engine.generate_report(str(report_path))
        st.dataframe(report_df, use_container_width=True)
        with open(report_path, "rb") as f:
            st.download_button("Export analytics report (CSV)", data=f.read(),
                                file_name="analytics_report.csv", mime="text/csv")

        # Static per-class summary chart (Matplotlib) -- a final-report-style
        # complement to the live Plotly time-series above: total unique
        # objects tracked per class over the whole video.
        if not report_df.empty:
            st.subheader("Per-Class Object Summary")
            class_counts = report_df["class"].value_counts()
            fig_mpl, ax = plt.subplots(figsize=(6, 4))
            ax.bar(class_counts.index, class_counts.values,
                   color=["#4ade80" if c == "helmet" else "#f87171" for c in class_counts.index])
            ax.set_ylabel("Unique Tracked Objects")
            ax.set_title("Total Unique Objects Tracked per Class")
            for i, v in enumerate(class_counts.values):
                ax.text(i, v + 0.1, str(v), ha="center")
            st.pyplot(fig_mpl)

    if st.button("Reset / Load New Video"):
        st.session_state.engine = None
        st.session_state.stats_history = []
        st.session_state.checkpoint_clicks = []
        st.session_state.zone_clicks = []
        st.session_state.checkpoint_last_raw = None
        st.session_state.zone_last_raw = None
        st.rerun()