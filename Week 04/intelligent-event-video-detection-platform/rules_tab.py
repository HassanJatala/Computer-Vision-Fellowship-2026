import json
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QComboBox, QCheckBox, QMessageBox
)


class RulesTab(QWidget):
    def __init__(self, rules_file="user_settings/rules.json"):
        super().__init__()
        self.rules_file = rules_file
        self.rules_data = []

        layout = QVBoxLayout()

        button_row = QHBoxLayout()
        load_btn = QPushButton("Load Rules")
        load_btn.clicked.connect(self.load_rules)
        button_row.addWidget(load_btn)

        save_btn = QPushButton("Save Rules")
        save_btn.clicked.connect(self.save_rules)
        button_row.addWidget(save_btn)

        layout.addLayout(button_row)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Rule Name", "Type", "Zone/Line", "Severity", "Threshold/Capacity", "Enabled"]
        )
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.load_rules()

    def load_rules(self):
        if not os.path.exists(self.rules_file):
            self.rules_data = []
        else:
            with open(self.rules_file, "r") as f:
                data = json.load(f)
            self.rules_data = data.get("rules", [])

        self.table.setRowCount(len(self.rules_data))

        for row, rule in enumerate(self.rules_data):
            self.table.setItem(row, 0, QTableWidgetItem(rule.get("name", "")))
            self.table.setItem(row, 1, QTableWidgetItem(rule.get("type", "")))

            zone_or_line = rule.get("zone_id") or rule.get("line_id") or "-"
            self.table.setItem(row, 2, QTableWidgetItem(zone_or_line))

            severity_combo = QComboBox()
            severity_combo.addItems(["Warning", "Critical"])
            severity_combo.setCurrentText(rule.get("severity", "Warning"))
            self.table.setCellWidget(row, 3, severity_combo)

            threshold_value = rule.get("threshold_seconds") or rule.get("max_capacity") or ""
            self.table.setItem(row, 4, QTableWidgetItem(str(threshold_value)))

            enabled_checkbox = QCheckBox()
            enabled_checkbox.setChecked(rule.get("enabled", True))
            self.table.setCellWidget(row, 5, enabled_checkbox)

    def save_rules(self):
        for row, rule in enumerate(self.rules_data):
            severity_combo = self.table.cellWidget(row, 3)
            rule["severity"] = severity_combo.currentText()

            threshold_item = self.table.item(row, 4)
            threshold_text = threshold_item.text().strip() if threshold_item else ""
            if threshold_text.isdigit():
                if "threshold_seconds" in rule:
                    rule["threshold_seconds"] = int(threshold_text)
                elif "max_capacity" in rule:
                    rule["max_capacity"] = int(threshold_text)

            enabled_checkbox = self.table.cellWidget(row, 5)
            rule["enabled"] = enabled_checkbox.isChecked()

        os.makedirs(os.path.dirname(self.rules_file), exist_ok=True)
        with open(self.rules_file, "w") as f:
            json.dump({"rules": self.rules_data}, f, indent=2)

        QMessageBox.information(self, "Saved", "Rules saved successfully. Restart the pipeline to apply changes.")