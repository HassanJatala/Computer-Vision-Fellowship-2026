import uuid
import time


class Event:
    def __init__(self, rule, current_time, track_id=None):
        self.event_id = str(uuid.uuid4())
        self.rule_id = rule.rule_id
        self.event_type = rule.event_type
        self.name = rule.name
        self.severity = rule.severity
        self.zone_id = rule.zone_id
        self.track_id = track_id
        self.status = "Active"
        self.detected_time = time.time()
        self.last_true_time = current_time
        self.resolved_time = None
        self.evidence_path = None
        self.evidence_crop_path = None

    def resolve(self):
        self.status = "Resolved"
        self.resolved_time = time.time()


class EventManager:
    def __init__(self, grace_period_seconds=3):
        self.active_events = {}
        self.all_events = []
        self.grace_period_seconds = grace_period_seconds

    def process_rule_result(self, rule, is_firing, current_time, track_id=None):
        key = (track_id, rule.rule_id) if track_id is not None else rule.rule_id

        if is_firing:
            if key not in self.active_events:
                event = Event(rule, current_time, track_id)
                self.active_events[key] = event
                self.all_events.append(event)
                return event
            else:
                self.active_events[key].last_true_time = current_time
        else:
            if key in self.active_events:
                event = self.active_events[key]
                if current_time - event.last_true_time > self.grace_period_seconds:
                    event.resolve()
                    del self.active_events[key]

        return None

    def get_active_events(self):
        return list(self.active_events.values())

    def get_all_events(self):
        return self.all_events