from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFileDialog, QListWidget,
    QFrame, QListWidgetItem, QMessageBox, QComboBox
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
import cv2

from pipeline import Pipeline
from zone_editor_widget import ZoneEditorWidget
from rules_tab import RulesTab
from event_history_tab import EventHistoryTab
from dashboard_tab import DashboardTab
from settings_tab import SettingsTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Intelligent Video Event Detection and Alerting Platform")
        self.resize(1400, 900)

        self._load_stylesheet()

        self.pipeline = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self._build_live_view_tab()
        self._build_zone_editor_tab()
        self._build_rules_tab()
        self._build_dashboard_tab()
        self._build_event_history_tab()
        self._build_settings_tab()

    def _load_stylesheet(self):
        try:
            with open("styles.qss", "r") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            pass

    def _build_placeholder_tab(self, name):
        tab = QWidget()
        layout = QVBoxLayout()
        label = QLabel(f"{name} - coming soon")
        layout.addWidget(label)
        tab.setLayout(layout)
        self.tabs.addTab(tab, name)

    # ---------------- Live View ----------------

    def _build_live_view_tab(self):
        tab = QWidget()
        main_layout = QHBoxLayout()

        video_column = QVBoxLayout()

        self.video_label = QLabel("No video loaded")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(800, 500)
        self.video_label.setStyleSheet("background-color: #000000; border: 1px solid #3a3a4c;")
        video_column.addWidget(self.video_label)

        control_row = QHBoxLayout()

        open_btn = QPushButton("Open Video File")
        open_btn.clicked.connect(self.open_video_file)
        control_row.addWidget(open_btn)

        webcam_btn = QPushButton("Use Webcam")
        webcam_btn.clicked.connect(self.open_webcam)
        control_row.addWidget(webcam_btn)

        self.rtsp_input = QLineEdit()
        self.rtsp_input.setPlaceholderText("rtsp://...")
        control_row.addWidget(self.rtsp_input)

        rtsp_btn = QPushButton("Connect RTSP")
        rtsp_btn.clicked.connect(self.open_rtsp)
        control_row.addWidget(rtsp_btn)

        stop_btn = QPushButton("Stop")
        stop_btn.clicked.connect(self.stop_video)
        control_row.addWidget(stop_btn)

        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self.reset_live_view)
        control_row.addWidget(reset_btn)

        video_column.addLayout(control_row)
        main_layout.addLayout(video_column, stretch=3)

        sidebar = QVBoxLayout()
        sidebar_frame = QFrame()
        sidebar_frame.setFrameShape(QFrame.StyledPanel)

        sidebar.addWidget(QLabel("<b>Live Stats</b>"))
        self.fps_label = QLabel("FPS: --")
        sidebar.addWidget(self.fps_label)
        self.frame_time_label = QLabel("Frame time: -- ms")
        sidebar.addWidget(self.frame_time_label)
        self.active_tracks_label = QLabel("Active tracks: 0")
        sidebar.addWidget(self.active_tracks_label)

        sidebar.addWidget(QLabel("<b>Recent Alerts</b>"))
        self.alerts_list = QListWidget()
        sidebar.addWidget(self.alerts_list)

        sidebar_frame.setLayout(sidebar)
        main_layout.addWidget(sidebar_frame, stretch=1)

        tab.setLayout(main_layout)
        self.tabs.addTab(tab, "Live View")

    def open_video_file(self):
        # file_path, _ = QFileDialog.getOpenFileName(self, "Select Video", "", "Video Files (*.mp4 *.avi)")
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Video", "", "Video Files (*.mp4 *.avi *.mpg *.mov *.mkv)")
        if file_path:
            self.start_pipeline(file_path, is_live_stream=False)

    def open_webcam(self):
        self.start_pipeline(0, is_live_stream=True)

    def open_rtsp(self):
        url = self.rtsp_input.text().strip()
        if url:
            self.start_pipeline(url, is_live_stream=True)

    def start_pipeline(self, source, is_live_stream):
        if self.pipeline:
            self.pipeline.stop()
        self.pipeline = Pipeline(is_live_stream=is_live_stream)
        self.pipeline.start(source)
        self.video_label.setText("")
        self.timer.start(250)

    def stop_video(self):
        self.timer.stop()
        if self.pipeline:
            self.pipeline.stop()
        self.video_label.setText("Stopped")

    def reset_live_view(self):
        self.timer.stop()
        if self.pipeline:
            self.pipeline.stop()
            self.pipeline = None
        self.video_label.clear()
        self.video_label.setText("No video loaded")
        self.fps_label.setText("FPS: --")
        self.frame_time_label.setText("Frame time: -- ms")
        self.active_tracks_label.setText("Active tracks: 0")
        self.alerts_list.clear()

    def update_frame(self):
        if not self.pipeline or not self.pipeline.running:
            self.timer.stop()
            return

        annotated_frame, new_alerts = self.pipeline.process_frame()

        if annotated_frame is None:
            self.timer.stop()
            self.video_label.setText("Video ended")
            return

        rgb_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        qt_image = QImage(rgb_frame.data, w, h, ch * w, QImage.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(qt_image).scaled(
            self.video_label.width(), self.video_label.height(), Qt.KeepAspectRatio
        )
        self.video_label.setPixmap(pixmap)

        self.frame_time_label.setText(f"Frame time: {self.pipeline.last_frame_time_ms:.1f} ms")
        self.active_tracks_label.setText(f"Active tracks: {len(self.pipeline.state_manager.get_all_states())}")

        for event in new_alerts:
            self.alerts_list.insertItem(0, f"[{event.severity}] {event.name} (Track {event.track_id})")

    # ---------------- Zone Editor ----------------

    def _build_zone_editor_tab(self):
        tab = QWidget()
        main_layout = QHBoxLayout()

        left_column = QVBoxLayout()

        instructions = QLabel(
            "Zones: Left-click to add points, right-click to close and name the polygon (3+ points). | "
            "Lines: Left-click twice to place both endpoints, then name it and set direction."
        )
        left_column.addWidget(instructions)

        top_row = QHBoxLayout()

        load_btn = QPushButton("Load Frame from Video")
        load_btn.clicked.connect(self.load_frame_for_zone_editing)
        top_row.addWidget(load_btn)
        load_webcam_btn = QPushButton("Load Frame from Webcam")
        load_webcam_btn.clicked.connect(self.load_frame_from_webcam_for_zone_editing)
        top_row.addWidget(load_webcam_btn)
        load_rtsp_btn = QPushButton("Load Frame from RTSP")
        load_rtsp_btn.clicked.connect(self.load_frame_from_rtsp_for_zone_editing)
        top_row.addWidget(load_rtsp_btn)

        zone_mode_btn = QPushButton("Draw Zones")
        zone_mode_btn.clicked.connect(lambda: self.set_editor_mode("zone"))
        top_row.addWidget(zone_mode_btn)

        line_mode_btn = QPushButton("Draw Lines")
        line_mode_btn.clicked.connect(lambda: self.set_editor_mode("line"))
        top_row.addWidget(line_mode_btn)

        reset_editor_btn = QPushButton("Reset Editor (clears everything)")
        reset_editor_btn.clicked.connect(self.reset_zone_editor)
        top_row.addWidget(reset_editor_btn)

        self.mode_label = QLabel("Current mode: Zone")
        top_row.addWidget(self.mode_label)

        left_column.addLayout(top_row)

        self.zone_editor = ZoneEditorWidget()
        canvas_row = QHBoxLayout()
        canvas_row.addStretch()
        canvas_row.addWidget(self.zone_editor)
        canvas_row.addStretch()
        left_column.addLayout(canvas_row)
        left_column.addStretch()

        main_layout.addLayout(left_column, stretch=3)

        self.zone_line_settings_tabs = QTabWidget()
        self.zone_line_settings_tabs.setMaximumWidth(350)

        self._build_zone_settings_panel()
        self._build_line_settings_panel()

        main_layout.addWidget(self.zone_line_settings_tabs, stretch=1)

        tab.setLayout(main_layout)
        self.tabs.addTab(tab, "Zone Editor")

    def _build_zone_settings_panel(self):
        panel = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("<b>Zones</b>"))

        self.zone_list_widget = QListWidget()
        self.zone_list_widget.currentRowChanged.connect(self.on_zone_selected)
        layout.addWidget(self.zone_list_widget)

        layout.addWidget(QLabel("Name:"))
        self.zone_name_input = QLineEdit()
        layout.addWidget(self.zone_name_input)

        rename_zone_btn = QPushButton("Rename Zone")
        rename_zone_btn.clicked.connect(self.rename_selected_zone)
        layout.addWidget(rename_zone_btn)

        delete_zone_btn = QPushButton("Delete This Zone")
        delete_zone_btn.clicked.connect(self.delete_selected_zone)
        layout.addWidget(delete_zone_btn)

        save_zones_btn = QPushButton("Save All Zones")
        save_zones_btn.clicked.connect(self.save_zones)
        layout.addWidget(save_zones_btn)

        layout.addStretch()
        panel.setLayout(layout)
        self.zone_line_settings_tabs.addTab(panel, "Zone Settings")

    def _build_line_settings_panel(self):
        panel = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("<b>Lines</b>"))

        self.line_list_widget = QListWidget()
        self.line_list_widget.currentRowChanged.connect(self.on_line_selected)
        layout.addWidget(self.line_list_widget)

        layout.addWidget(QLabel("Name:"))
        self.line_name_input = QLineEdit()
        layout.addWidget(self.line_name_input)

        layout.addWidget(QLabel("Expected Direction:"))
        self.line_direction_input = QComboBox()
        self.line_direction_input.addItems(["None", "A_to_B", "B_to_A"])
        layout.addWidget(self.line_direction_input)

        update_line_btn = QPushButton("Update This Line")
        update_line_btn.clicked.connect(self.update_selected_line)
        layout.addWidget(update_line_btn)

        delete_line_btn = QPushButton("Delete This Line")
        delete_line_btn.clicked.connect(self.delete_selected_line)
        layout.addWidget(delete_line_btn)

        save_lines_btn = QPushButton("Save All Lines")
        save_lines_btn.clicked.connect(self.save_lines)
        layout.addWidget(save_lines_btn)

        layout.addStretch()
        panel.setLayout(layout)
        self.zone_line_settings_tabs.addTab(panel, "Line Settings")

    # ---------------- Rules ----------------

    def _build_rules_tab(self):
        self.rules_tab = RulesTab()
        self.tabs.addTab(self.rules_tab, "Rules")

    # ---------------- Dashboard ----------------

    def _build_dashboard_tab(self):
        self.dashboard_tab = DashboardTab()
        self.tabs.addTab(self.dashboard_tab, "Dashboard")

    # ---------------- Event History ----------------

    def _build_event_history_tab(self):
        self.event_history_tab = EventHistoryTab()
        self.tabs.addTab(self.event_history_tab, "Event History")

    # ---------------- Settings ----------------

    def _build_settings_tab(self):
        self.settings_tab = SettingsTab()
        self.tabs.addTab(self.settings_tab, "Settings")

    # ---------------- Zone Editor helper methods ----------------

    def load_frame_for_zone_editing(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Video for Zone Editing", "", "Video Files (*.mp4 *.avi *.mpg *.mov *.mkv)")
        if not file_path:
            return
        cap = cv2.VideoCapture(file_path)
        ret, frame = cap.read()
        cap.release()
        if ret:
            self.zone_editor.set_frame(frame)
            self.refresh_zone_list()
            self.refresh_line_list()
        else:
            QMessageBox.warning(self, "Error", "Could not read a frame from that video.")

    def load_frame_from_webcam_for_zone_editing(self):
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        if ret:
            self.zone_editor.set_frame(frame)
            self.refresh_zone_list()
            self.refresh_line_list()
        else:
            QMessageBox.warning(self, "Error", "Could not read a frame from the webcam.")

    def load_frame_from_rtsp_for_zone_editing(self):
        url = self.rtsp_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Enter an RTSP URL in the Live View tab first.")
            return
        cap = cv2.VideoCapture(url)
        ret, frame = cap.read()
        cap.release()
        if ret:
            self.zone_editor.set_frame(frame)
            self.refresh_zone_list()
            self.refresh_line_list()
        else:
            QMessageBox.warning(self, "Error", "Could not read a frame from the RTSP stream. Check the URL and connection.")

    def set_editor_mode(self, mode):
        self.zone_editor.set_mode(mode)
        self.mode_label.setText(f"Current mode: {'Zone' if mode == 'zone' else 'Line'}")

    def reset_zone_editor(self):
        self.zone_editor.frame = None
        self.zone_editor.qt_pixmap = None
        self.zone_editor.current_points = []
        self.zone_editor.zones = []
        self.zone_editor.lines = []
        self.zone_editor.setMinimumSize(960, 540)
        self.zone_editor.update()
        self.refresh_zone_list()
        self.refresh_line_list()
        self.zone_name_input.clear()
        self.line_name_input.clear()

    def refresh_zone_list(self):
        self.zone_list_widget.clear()
        for zone in self.zone_editor.zones:
            self.zone_list_widget.addItem(QListWidgetItem(f"{zone['zone_id']}: {zone['name']}"))

    def on_zone_selected(self, row):
        if 0 <= row < len(self.zone_editor.zones):
            self.zone_name_input.setText(self.zone_editor.zones[row]["name"])

    def rename_selected_zone(self):
        row = self.zone_list_widget.currentRow()
        new_name = self.zone_name_input.text().strip()
        if row >= 0 and new_name:
            self.zone_editor.rename_zone(row, new_name)
            self.refresh_zone_list()
            self.zone_list_widget.setCurrentRow(row)

    def delete_selected_zone(self):
        row = self.zone_list_widget.currentRow()
        if row >= 0:
            self.zone_editor.delete_zone(row)
            self.refresh_zone_list()
            self.zone_name_input.clear()

    def save_zones(self):
        self.zone_editor.save_zones()
        QMessageBox.information(self, "Saved", "Zones saved successfully to user_settings/zones.json")

    def refresh_line_list(self):
        self.line_list_widget.clear()
        for line in self.zone_editor.lines:
            direction = line["expected_direction"] or "No restriction"
            self.line_list_widget.addItem(QListWidgetItem(f"{line['line_id']}: {line['name']} ({direction})"))

    def on_line_selected(self, row):
        if 0 <= row < len(self.zone_editor.lines):
            line = self.zone_editor.lines[row]
            self.line_name_input.setText(line["name"])
            self.line_direction_input.setCurrentText(line["expected_direction"] or "None")

    def update_selected_line(self):
        row = self.line_list_widget.currentRow()
        new_name = self.line_name_input.text().strip()
        if row >= 0 and new_name:
            self.zone_editor.rename_line(row, new_name)
            self.zone_editor.set_line_direction(row, self.line_direction_input.currentText())
            self.refresh_line_list()
            self.line_list_widget.setCurrentRow(row)

    def delete_selected_line(self):
        row = self.line_list_widget.currentRow()
        if row >= 0:
            self.zone_editor.delete_line(row)
            self.refresh_line_list()
            self.line_name_input.clear()

    def save_lines(self):
        self.zone_editor.save_lines()
        QMessageBox.information(self, "Saved", "Lines saved successfully to user_settings/lines.json")