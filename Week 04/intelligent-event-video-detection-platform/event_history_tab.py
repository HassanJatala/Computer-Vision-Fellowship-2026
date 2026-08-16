import csv
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QLabel, QDialog, QFileDialog, QMessageBox
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from datetime import datetime
from database.repository import get_events, update_event_status


class EvidenceViewerDialog(QDialog):
    def __init__(self, full_path, crop_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Evidence")
        layout = QVBoxLayout()

        if full_path:
            full_label = QLabel("Full Frame:")
            layout.addWidget(full_label)
            full_pixmap = QPixmap(full_path)
            if not full_pixmap.isNull():
                img_label = QLabel()
                img_label.setPixmap(full_pixmap.scaledToWidth(700, Qt.SmoothTransformation))
                layout.addWidget(img_label)

        if crop_path:
            crop_label = QLabel("Cropped Detection:")
            layout.addWidget(crop_label)
            crop_pixmap = QPixmap(crop_path)
            if not crop_pixmap.isNull():
                img_label2 = QLabel()
                img_label2.setPixmap(crop_pixmap.scaledToWidth(300, Qt.SmoothTransformation))
                layout.addWidget(img_label2)

        if not full_path and not crop_path:
            layout.addWidget(QLabel("No evidence available for this event."))

        self.setLayout(layout)


class EventHistoryTab(QWidget):
    def __init__(self):
        super().__init__()
        self.current_events = []

        layout = QVBoxLayout()

        filter_row = QHBoxLayout()

        self.type_filter = QComboBox()
        self.type_filter.addItems(["All Types", "intrusion", "loitering", "wrong_direction", "overcrowding"])
        filter_row.addWidget(self.type_filter)

        self.severity_filter = QComboBox()
        self.severity_filter.addItems(["All Severities", "Warning", "Critical"])
        filter_row.addWidget(self.severity_filter)

        self.zone_filter = QComboBox()
        self.zone_filter.addItems(["All Zones", "zone_1", "zone_2", "zone_3"])
        filter_row.addWidget(self.zone_filter)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_events)
        filter_row.addWidget(refresh_btn)

        export_btn = QPushButton("Export to CSV")
        export_btn.clicked.connect(self.export_csv)
        filter_row.addWidget(export_btn)

        layout.addLayout(filter_row)

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(
            ["Event ID", "Type", "Severity", "Zone", "Track", "Status", "Start Time", "Evidence", "Action"]
        )
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.refresh_events()

    def refresh_events(self):
        event_type = self.type_filter.currentText()
        severity = self.severity_filter.currentText()
        zone = self.zone_filter.currentText()

        self.current_events = get_events(
            event_type=None if event_type == "All Types" else event_type,
            severity=None if severity == "All Severities" else severity,
            zone_id=None if zone == "All Zones" else zone,
        )

        self.table.setRowCount(len(self.current_events))

        for row, event in enumerate(self.current_events):
            self.table.setItem(row, 0, QTableWidgetItem(str(event["event_id"])[:8]))
            self.table.setItem(row, 1, QTableWidgetItem(str(event["event_type"])))
            self.table.setItem(row, 2, QTableWidgetItem(str(event["severity"])))
            self.table.setItem(row, 3, QTableWidgetItem(str(event["zone_id"])))
            self.table.setItem(row, 4, QTableWidgetItem(str(event["track_id"])))
            self.table.setItem(row, 5, QTableWidgetItem(str(event["status"])))
            readable_time = datetime.fromtimestamp(event["start_time"]).strftime("%Y-%m-%d %H:%M:%S") if event["start_time"] else "N/A"
            self.table.setItem(row, 6, QTableWidgetItem(readable_time))

            evidence_btn = QPushButton("View")
            evidence_btn.clicked.connect(lambda checked, r=row: self.view_evidence(r))
            self.table.setCellWidget(row, 7, evidence_btn)

            action_btn = QPushButton("Resolve")
            action_btn.clicked.connect(lambda checked, r=row: self.resolve_event(r))
            self.table.setCellWidget(row, 8, action_btn)

    def view_evidence(self, row):
        event = self.current_events[row]
        dialog = EvidenceViewerDialog(event.get("evidence_path"), event.get("evidence_crop_path"), self)
        dialog.exec()

    def resolve_event(self, row):
        event = self.current_events[row]
        update_event_status(event["event_id"], "Resolved")
        QMessageBox.information(self, "Updated", "Event marked as Resolved.")
        self.refresh_events()

    def export_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Event History", "event_history.csv", "CSV Files (*.csv)")
        if not file_path:
            return

        with open(file_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Event ID", "Type", "Severity", "Zone", "Track", "Status", "Start Time"])
            for event in self.current_events:
                writer.writerow([
                    event["event_id"], event["event_type"], event["severity"],
                    event["zone_id"], event["track_id"], event["status"], event["start_time"]
                ])

        QMessageBox.information(self, "Exported", f"Event history exported to {file_path}")