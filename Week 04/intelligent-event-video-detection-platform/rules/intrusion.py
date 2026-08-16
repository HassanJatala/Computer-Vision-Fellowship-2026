from rules.base_rule import BaseRule


class IntrusionRule(BaseRule):
    def __init__(self, rule_id, name, zone_id, object_class="person", severity="Critical", enabled=True):
        super().__init__(rule_id, name, event_type="intrusion", object_class=object_class, zone_id=zone_id, severity=severity, enabled=enabled)

    def check(self, entered_zone=None, **kwargs):
        """
        Fires the instant the monitored zone is entered - no threshold needed.
        """
        if not self.enabled:
            return False
        return entered_zone == self.zone_id