from rules.base_rule import BaseRule


class OccupancyRule(BaseRule):
    def __init__(self, rule_id, name, zone_id, max_capacity, object_class="person", severity="Critical", enabled=True):
        super().__init__(rule_id, name, event_type="overcrowding", object_class=object_class, zone_id=zone_id, severity=severity, enabled=enabled)
        self.max_capacity = max_capacity

    def check(self, occupancy_tracker=None, all_track_states=None, **kwargs):
        if not self.enabled:
            return False
        return occupancy_tracker.is_over_threshold(self.zone_id, all_track_states, self.max_capacity)