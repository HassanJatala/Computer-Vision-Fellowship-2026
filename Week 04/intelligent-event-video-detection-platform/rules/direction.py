from rules.base_rule import BaseRule


class DirectionRule(BaseRule):
    def __init__(self, rule_id, name, line_id, object_class="person", severity="Warning", enabled=True):
        super().__init__(rule_id, name, event_type="wrong_direction", object_class=object_class, zone_id=None, severity=severity, enabled=enabled)
        self.line_id = line_id

    def check(self, crossing=None, **kwargs):
        """
        crossing: one dict from LineManager.check_crossing() results
        """
        if not self.enabled:
            return False
        if crossing is None:
            return False
        return crossing["line_id"] == self.line_id and crossing["is_violation"]