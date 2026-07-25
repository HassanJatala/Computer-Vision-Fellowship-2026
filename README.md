# Vision Toolkit — Desktop (PyQt5 + OpenCV)

## Setup
```bash
pip install -r requirements.txt
python vision_toolkit_desktop.py
```

## Features
**Required**
- Upload image (PNG/JPG/JPEG/BMP/TIFF/GIF/WebP) + live webcam capture
- Image info panel: dimensions, current size, file size, channel count
- Grayscale toggle
- Canny edge detection with adjustable low/high thresholds
- Gaussian blur and Median blur with adjustable intensity
- Binary threshold (adjustable value) and Adaptive threshold
- Drawing tools: rectangle, circle, line, text — all click-and-drag on the
  live canvas, correctly mapped from screen to image coordinates
- Save/export to PNG, JPG, or BMP

**Bonus**
- Brightness (-100..100) and Contrast (50%-200%)
- Rotation (0-360°) and Resize (25%-200%)
- Interactive crop tool (drag a region, crops the working image)
- Histogram viewer (per-channel, rendered with OpenCV — no extra deps)
- Webcam capture with "Capture Frame" to freeze and edit a live frame

## Processing pipeline order
Brightness/Contrast → Rotation → Resize → Grayscale → Blur → Canny → Threshold.
Drawings are stored as a separate operation list and re-applied on top of the
filtered image, so changing a filter after drawing never erases your shapes.

## Notes
- Everything runs 100% offline — no internet or backend required.
- Tested end-to-end: pipeline, all filters/toggles, all four drawing tools,
  crop, histogram rendering, and save all verified working on a synthetic
  test image before delivery.
