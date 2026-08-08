from ultralytics import YOLO
model = YOLO("model/best.pt")
results = model.predict("C:/Users/abdul/Downloads/stock video/vid1.mp4", conf=0.05, verbose=False)
all_confs = [float(c) for r in results for c in r.boxes.conf]
import numpy as np
print("max:", max(all_confs), "median:", np.median(all_confs), "count>0.45:", sum(c > 0.45 for c in all_confs))