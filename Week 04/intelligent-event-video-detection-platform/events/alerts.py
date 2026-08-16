class AlertEngine:
    def __init__(self):
        self.alert_queue = []  # in-app alerts waiting to be shown in UI

    def send_alert(self, event, source_id="camera_1"):
        alert = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "name": event.name,
            "severity": event.severity,
            "zone_id": event.zone_id,
            "track_id": event.track_id,
            "timestamp": event.detected_time,
            "evidence_path": event.evidence_path,
            "source_id": source_id,
        }
        self.alert_queue.append(alert)
        self._log_to_console(alert)  # simulated secondary channel
        return alert

    def _log_to_console(self, alert):
        print(f"[ALERT] {alert['severity']} | {alert['name']} | Track: {alert['track_id']} | Zone: {alert['zone_id']}")

    def get_pending_alerts(self):
        return self.alert_queue

    def clear_alerts(self):
        self.alert_queue = []