from rules.base_rule import BaseRule


class LoiteringRule(BaseRule):
    def __init__(self, rule_id, name, zone_id, threshold_seconds, object_class="person", severity="Warning", enabled=True):
        super().__init__(rule_id, name, event_type="loitering", object_class=object_class, zone_id=zone_id, severity=severity, enabled=enabled)
        self.threshold_seconds = threshold_seconds

    def check(self, track_record=None, current_time=None, dwell_tracker=None, **kwargs):
        if not self.enabled:
            return False
        if track_record is None:
            return False
        if track_record["current_zone"] != self.zone_id:
            return False
        return dwell_tracker.is_over_threshold(track_record, current_time, self.threshold_seconds)