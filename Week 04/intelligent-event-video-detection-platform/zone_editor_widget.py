from PySide6.QtWidgets import QWidget, QInputDialog
from PySide6.QtGui import QPainter, QPen, QColor, QImage, QPixmap
from PySide6.QtCore import Qt, QPoint
import cv2
import json
import os


class ZoneEditorWidget(QWidget):
    ZONE_COLORS = [
        (0, 0, 255), (0, 255, 255), (255, 0, 0), (0, 255, 0), (255, 0, 255),
    ]
    LINE_COLOR = (0, 140, 255)

    def __init__(self, zones_file="user_settings/zones.json", lines_file="user_settings/lines.json",
                 max_display_width=900, max_display_height=550):
        super().__init__()
        self.zones_file = zones_file
        self.lines_file = lines_file
        self.max_display_width = max_display_width
        self.max_display_height = max_display_height
        self.display_scale = 1.0  # computed dynamically once a frame is loaded

        self.frame = None
        self.qt_pixmap = None

        self.mode = "zone"
        self.current_points = []
        self.zones = []
        self.lines = []

        self.setMinimumSize(400, 300)
        self._load_existing_zones()
        self._load_existing_lines()

    def set_mode(self, mode):
        self.mode = mode
        self.current_points = []
        self.update()

    def _load_existing_zones(self):
        if os.path.exists(self.zones_file):
            with open(self.zones_file, "r") as f:
                data = json.load(f)
            for i, z in enumerate(data.get("zones", [])):
                color = self.ZONE_COLORS[i % len(self.ZONE_COLORS)]
                self.zones.append({
                    "zone_id": z["zone_id"], "name": z["name"], "polygon": z["polygon"],
                    "monitored_classes": z.get("monitored_classes", ["person"]), "color": color,
                })

    def _load_existing_lines(self):
        if os.path.exists(self.lines_file):
            with open(self.lines_file, "r") as f:
                data = json.load(f)
            for l in data.get("lines", []):
                self.lines.append({
                    "line_id": l["line_id"], "name": l["name"],
                    "point_a": l["point_a"], "point_b": l["point_b"],
                    "expected_direction": l.get("expected_direction"),
                })

    def set_frame(self, frame):
        self.frame = frame
        self._refresh_pixmap()

    def _refresh_pixmap(self):
        if self.frame is None:
            return
        rgb = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
        full_pixmap = QPixmap.fromImage(qimg)

        # Compute scale to fit within max_display_width/height, preserving aspect ratio
        scale_w = self.max_display_width / w
        scale_h = self.max_display_height / h
        self.display_scale = min(scale_w, scale_h)

        display_w = int(w * self.display_scale)
        display_h = int(h * self.display_scale)
        self.qt_pixmap = full_pixmap.scaled(display_w, display_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setFixedSize(display_w, display_h)
        self.update()

    def _to_full_res(self, x, y):
        return [int(x / self.display_scale), int(y / self.display_scale)]

    def _to_display(self, x, y):
        return QPoint(int(x * self.display_scale), int(y * self.display_scale))

    def mousePressEvent(self, event):
        if self.frame is None:
            return
        if event.button() == Qt.LeftButton:
            self.current_points.append((event.position().x(), event.position().y()))
            if self.mode == "line" and len(self.current_points) == 2:
                self._finish_current_line()
            self.update()
        elif event.button() == Qt.RightButton:
            if self.mode == "zone":
                self._finish_current_zone()

    def _finish_current_zone(self):
        if len(self.current_points) < 3:
            self.current_points = []
            self.update()
            return
        name, ok = QInputDialog.getText(self, "Zone Name", "Enter a name for this zone:")
        if not ok or not name.strip():
            self.current_points = []
            self.update()
            return
        zone_id = f"zone_{len(self.zones) + 1}"
        color = self.ZONE_COLORS[len(self.zones) % len(self.ZONE_COLORS)]
        full_res_polygon = [self._to_full_res(x, y) for x, y in self.current_points]
        self.zones.append({
            "zone_id": zone_id, "name": name.strip(), "polygon": full_res_polygon,
            "monitored_classes": ["person"], "color": color,
        })
        self.current_points = []
        self.update()

    def _finish_current_line(self):
        name, ok = QInputDialog.getText(self, "Line Name", "Enter a name for this line:")
        if not ok or not name.strip():
            self.current_points = []
            self.update()
            return
        direction, ok = QInputDialog.getItem(
            self, "Expected Direction",
            "Select the allowed crossing direction (or None for no restriction):",
            ["None", "A_to_B", "B_to_A"], 0, False
        )
        expected_direction = None if direction == "None" else direction
        line_id = f"line_{len(self.lines) + 1}"
        point_a = self._to_full_res(*self.current_points[0])
        point_b = self._to_full_res(*self.current_points[1])
        self.lines.append({
            "line_id": line_id, "name": name.strip(),
            "point_a": point_a, "point_b": point_b,
            "expected_direction": expected_direction,
        })
        self.current_points = []
        self.update()

    def delete_zone(self, index):
        if 0 <= index < len(self.zones):
            del self.zones[index]
            self.update()

    def delete_line(self, index):
        if 0 <= index < len(self.lines):
            del self.lines[index]
            self.update()

    def rename_zone(self, index, new_name):
        if 0 <= index < len(self.zones):
            self.zones[index]["name"] = new_name
            self.update()

    def rename_line(self, index, new_name):
        if 0 <= index < len(self.lines):
            self.lines[index]["name"] = new_name
            self.update()

    def set_line_direction(self, index, new_direction):
        if 0 <= index < len(self.lines):
            self.lines[index]["expected_direction"] = None if new_direction == "None" else new_direction

    def save_zones(self):
        data = {"zones": [
            {"zone_id": z["zone_id"], "name": z["name"], "polygon": z["polygon"],
             "monitored_classes": z["monitored_classes"]}
            for z in self.zones
        ]}
        os.makedirs(os.path.dirname(self.zones_file), exist_ok=True)
        with open(self.zones_file, "w") as f:
            json.dump(data, f, indent=2)

    def save_lines(self):
        data = {"lines": [
            {"line_id": l["line_id"], "name": l["name"], "point_a": l["point_a"],
             "point_b": l["point_b"], "expected_direction": l["expected_direction"]}
            for l in self.lines
        ]}
        os.makedirs(os.path.dirname(self.lines_file), exist_ok=True)
        with open(self.lines_file, "w") as f:
            json.dump(data, f, indent=2)

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.qt_pixmap:
            painter.drawPixmap(0, 0, self.qt_pixmap)

        for zone in self.zones:
            color = QColor(zone["color"][2], zone["color"][1], zone["color"][0])
            pen = QPen(color, 3)
            painter.setPen(pen)
            points = [self._to_display(p[0], p[1]) for p in zone["polygon"]]
            for i in range(len(points)):
                painter.drawLine(points[i], points[(i + 1) % len(points)])
            painter.drawText(points[0].x(), points[0].y() - 10, zone["name"])

        for line in self.lines:
            color = QColor(*self.LINE_COLOR[::-1])
            pen = QPen(color, 3)
            painter.setPen(pen)
            pa = self._to_display(*line["point_a"])
            pb = self._to_display(*line["point_b"])
            painter.drawLine(pa, pb)
            painter.drawText(pa.x(), pa.y() - 10, line["name"])

        if self.current_points:
            pen = QPen(QColor(255, 255, 255), 2, Qt.DashLine)
            painter.setPen(pen)
            points = [QPoint(int(p[0]), int(p[1])) for p in self.current_points]
            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i + 1])
            for p in points:
                painter.drawEllipse(p, 4, 4)