# Helmet Detection — YOLOv8s Training, Evaluation & Deployment

A custom object detection system that trains a **YOLOv8s** model to classify motorcycle riders as
**With Helmet** or **Without Helmet**, evaluates it, and deploys it as an interactive **Gradio** app
supporting image upload, video upload, and real-time webcam detection.

Built and intended to run in **Google Colab** (GPU runtime recommended), though it also works locally
with a GPU-enabled machine.

---

## What's in the notebook

| Section | Contents |
|---|---|
| **1. Setup** | Install Ultralytics, upload/extract the dataset, fix Roboflow's known `data.yaml` path issue, sanity-check the train/valid/test splits |
| **2. Model Training** | Trains 5 YOLOv8s experiments varying epochs, image size, batch size, and learning rate; compares results visually and picks the best run by mAP50-95 |
| **3. Evaluation** | Loads the best run, saves it to Google Drive, and reports precision, recall, mAP50, mAP50-95, a confusion matrix, and sample predictions on the test set |
| **4. Analysis** | Strengths/weaknesses write-up, plus a shortcut to reload the saved model from Drive without retraining |
| **5. Deployment** | A Gradio app with three tabs — Image Upload, Video Upload, and Webcam Detection — each with a confidence threshold slider, detection statistics (object count, processing time, confidence scores), and exportable annotated results |

---

## Dataset

This notebook expects the **Bike Helmet Detection** dataset (Roboflow, YOLOv8 export format),
containing 2 classes: `With Helmet`, `Without Helmet`.

Extract it into a folder named `dataset` next to the notebook:

```
your_project/
├── Helmet_Detection_Training_and_Evaluation.ipynb
└── dataset/
    ├── train/images, train/labels
    ├── valid/images, valid/labels
    ├── test/images,  test/labels
    └── data.yaml
```

- **In Google Colab:** run the "1.0 Upload Dataset" cell to upload the zip directly — it extracts automatically into `dataset/`.
- **Running locally:** skip that cell and just make sure `dataset/` already exists in the structure above.

The notebook automatically patches `data.yaml`'s `train`/`val`/`test`/`path` fields to match this
structure (a known Roboflow export quirk), then verifies every split has matching image/label counts
before training starts.

---

## Setup

```bash
pip install -r requirements.txt
```

Then open and run `Helmet_Detection_Training_and_Evaluation.ipynb` top to bottom.

> **Note:** `google.colab` (used for file upload and Google Drive mounting) is a Colab-only built-in
> module — it isn't a pip package and isn't in `requirements.txt`. If you're running locally instead of
> in Colab, skip the "Upload Dataset," "Save to Google Drive," and "Load from Google Drive" cells; place
> your dataset in `dataset/` manually, and load your trained weights directly with
> `YOLO("path/to/best.pt")`.

---

## Usage

### First time (training)
Run the notebook top to bottom through **Section 3.0 "Save Trained Model to Google Drive"**. This
trains 5 experiments, evaluates the best one, and persists `best.pt` to
`/content/drive/MyDrive/helmet_detection_model/best.pt` so you don't have to retrain next session.

### Every time after that (skip retraining)
1. Run the Section 1 setup/import cells (no dataset upload needed)
2. Jump to **Section 4.1 "Load Trained Model from Google Drive"**
3. Jump to **Section 5** to launch the app

### Launching the app
Running the last cell in Section 5 starts a Gradio app (`demo.launch(share=True)`), giving you a
public link with three tabs:
- **Image Upload** — detect on a single image, view stats, download the annotated PNG
- **Video Upload** — detect frame-by-frame on an uploaded video, view stats, download the annotated MP4
- **Webcam Detection** — live detection streamed from your browser's webcam, with stats updating per frame

---

## Known limitations

- The model is trained on road/dashcam-style imagery of motorcyclists. It does **not** generalize to
  unrelated contexts (e.g. portraits, construction sites) — expect unreliable results outside its
  training domain.
- All training experiments in Section 2 start from fresh pretrained `yolov8s.pt` weights (COCO), not
  from each other — they are independent runs, not a continued fine-tuning chain.
- `demo.launch(share=True)` public links expire after about a week (Gradio's free tunnel limit).

---

## Requirements

See `requirements.txt`. Key dependencies: `ultralytics`, `gradio`, `opencv-python`, `pandas`,
`matplotlib`, `pyyaml`, `numpy`, `Pillow`.
