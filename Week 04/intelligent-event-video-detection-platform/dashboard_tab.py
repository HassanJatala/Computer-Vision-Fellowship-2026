from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from collections import Counter

from database.repository import get_events


class DashboardTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        refresh_btn = QPushButton("Refresh Dashboard")
        refresh_btn.clicked.connect(self.refresh_dashboard)
        layout.addWidget(refresh_btn)

        # --- Stat cards row ---
        cards_row = QHBoxLayout()
        self.total_events_label = self._make_stat_card("Total Events", "0")
        self.critical_label = self._make_stat_card("Critical Events", "0")
        self.warning_label = self._make_stat_card("Warning Events", "0")
        self.active_label = self._make_stat_card("Currently Active", "0")

        cards_row.addWidget(self.total_events_label)
        cards_row.addWidget(self.critical_label)
        cards_row.addWidget(self.warning_label)
        cards_row.addWidget(self.active_label)
        layout.addLayout(cards_row)

        # --- Charts row ---
        charts_row = QHBoxLayout()

        self.type_chart_figure = Figure(figsize=(5, 4), facecolor="#1e1e2e")
        self.type_chart_canvas = FigureCanvas(self.type_chart_figure)
        charts_row.addWidget(self.type_chart_canvas)

        self.severity_chart_figure = Figure(figsize=(5, 4), facecolor="#1e1e2e")
        self.severity_chart_canvas = FigureCanvas(self.severity_chart_figure)
        charts_row.addWidget(self.severity_chart_canvas)

        layout.addLayout(charts_row)

        self.setLayout(layout)
        self.refresh_dashboard()

    def _make_stat_card(self, title, value):
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet("background-color: #2a2a3c; border-radius: 6px; padding: 10px;")
        card_layout = QVBoxLayout()
        title_label = QLabel(f"<b>{title}</b>")
        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 24px; color: #4a9eff;")
        card_layout.addWidget(title_label)
        card_layout.addWidget(value_label)
        frame.setLayout(card_layout)
        frame.value_label = value_label  # store reference so we can update it later
        return frame

    def refresh_dashboard(self):
        all_events = get_events()

        total = len(all_events)
        critical_count = sum(1 for e in all_events if e["severity"] == "Critical")
        warning_count = sum(1 for e in all_events if e["severity"] == "Warning")
        active_count = sum(1 for e in all_events if e["status"] == "Active")

        self.total_events_label.value_label.setText(str(total))
        self.critical_label.value_label.setText(str(critical_count))
        self.warning_label.value_label.setText(str(warning_count))
        self.active_label.value_label.setText(str(active_count))

        self._draw_type_chart(all_events)
        self._draw_severity_chart(all_events)

    def _draw_type_chart(self, events):
        self.type_chart_figure.clear()
        ax = self.type_chart_figure.add_subplot(111)
        ax.set_facecolor("#1e1e2e")

        type_counts = Counter(e["event_type"] for e in events)
        if type_counts:
            ax.bar(type_counts.keys(), type_counts.values(), color="#4a9eff")
        ax.set_title("Events by Type", color="white")
        ax.tick_params(colors="white", rotation=20)
        for spine in ax.spines.values():
            spine.set_color("white")

        self.type_chart_figure.tight_layout()
        self.type_chart_canvas.draw()

    def _draw_severity_chart(self, events):
        self.severity_chart_figure.clear()
        ax = self.severity_chart_figure.add_subplot(111)

        severity_counts = Counter(e["severity"] for e in events)
        colors = {"Critical": "#ff4d4d", "Warning": "#ffb84d"}
        if severity_counts:
            ax.pie(
                severity_counts.values(),
                labels=severity_counts.keys(),
                colors=[colors.get(k, "#4a9eff") for k in severity_counts.keys()],
                autopct="%1.0f%%",
                textprops={"color": "white"},
            )
        ax.set_title("Events by Severity", color="white")

        self.severity_chart_canvas.draw()