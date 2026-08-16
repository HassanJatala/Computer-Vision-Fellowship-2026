class BaseRule:
    def __init__(self, rule_id, name, event_type, object_class="person", zone_id=None, severity="Warning", enabled=True):
        self.rule_id = rule_id
        self.name = name
        self.event_type = event_type
        self.object_class = object_class
        self.zone_id = zone_id
        self.severity = severity
        self.enabled = enabled

    def check(self, **kwargs):
        """
        Each subclass must override this - given the current frame's data,
        returns True if this rule's condition is currently met.
        """
        raise NotImplementedError("Subclasses must implement check()")