import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QMessageBox, QDoubleSpinBox, QSpinBox
)


class SettingsTab(QWidget):
    def __init__(self, env_path=".env"):
        super().__init__()
        self.env_path = env_path

        layout = QVBoxLayout()
        form = QFormLayout()

        self.model_path_input = QLineEdit()
        form.addRow("Model Path:", self.model_path_input)

        self.confidence_input = QDoubleSpinBox()
        self.confidence_input.setRange(0.0, 1.0)
        self.confidence_input.setSingleStep(0.05)
        form.addRow("Detection Confidence:", self.confidence_input)

        self.tracker_input = QComboBox()
        self.tracker_input.addItems(["bytetrack", "botsort"])
        form.addRow("Tracker:", self.tracker_input)

        self.dwell_threshold_input = QSpinBox()
        self.dwell_threshold_input.setRange(1, 3600)
        form.addRow("Default Dwell Threshold (sec):", self.dwell_threshold_input)

        self.occupancy_threshold_input = QSpinBox()
        self.occupancy_threshold_input.setRange(1, 500)
        form.addRow("Default Occupancy Threshold:", self.occupancy_threshold_input)

        self.log_level_input = QComboBox()
        self.log_level_input.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        form.addRow("Log Level:", self.log_level_input)

        layout.addLayout(form)

        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)

        self.setLayout(layout)

        self.load_settings()

    def load_settings(self):
        values = {}
        if os.path.exists(self.env_path):
            with open(self.env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        values[key.strip()] = value.strip()

        self.model_path_input.setText(values.get("MODEL_PATH", "models/yolov8s.pt"))
        self.confidence_input.setValue(float(values.get("DETECTION_CONFIDENCE", 0.5)))
        self.tracker_input.setCurrentText(values.get("TRACKER", "bytetrack"))
        self.dwell_threshold_input.setValue(int(values.get("DWELL_THRESHOLD_SECONDS", 60)))
        self.occupancy_threshold_input.setValue(int(values.get("OCCUPANCY_THRESHOLD", 10)))
        self.log_level_input.setCurrentText(values.get("LOG_LEVEL", "INFO"))

    def save_settings(self):
        lines = [
            "# Path to the trained/pretrained YOLO model weights",
            f"MODEL_PATH={self.model_path_input.text()}",
            "",
            "# Path to the SQLite database file",
            "DATABASE_PATH=database/events.db",
            "",
            "# Default detection confidence threshold (0.0 to 1.0)",
            f"DETECTION_CONFIDENCE={self.confidence_input.value()}",
            "",
            "# Tracker choice: bytetrack or botsort",
            f"TRACKER={self.tracker_input.currentText()}",
            "",
            "# Default dwell-time threshold in seconds (used for loitering detection)",
            f"DWELL_THRESHOLD_SECONDS={self.dwell_threshold_input.value()}",
            "",
            "# Default occupancy threshold (max people before \"overcrowding\")",
            f"OCCUPANCY_THRESHOLD={self.occupancy_threshold_input.value()}",
            "",
            "# Logging level: DEBUG, INFO, WARNING, ERROR",
            f"LOG_LEVEL={self.log_level_input.currentText()}",
        ]

        with open(self.env_path, "w") as f:
            f.write("\n".join(lines))

        QMessageBox.information(
            self, "Saved",
            "Settings saved to .env. Restart the video/pipeline for changes to take effect."
        )