from events.event_manager import EventManager


class FakeRule:
    def __init__(self):
        self.rule_id = "rule_1"
        self.event_type = "loitering"
        self.name = "Test Loitering Rule"
        self.severity = "Warning"
        self.zone_id = "zone_1"


def test_event_debouncing():
    manager = EventManager(grace_period_seconds=3)
    rule = FakeRule()

    event1 = manager.process_rule_result(rule, is_firing=True, current_time=10.0, track_id=1)
    event2 = manager.process_rule_result(rule, is_firing=True, current_time=11.0, track_id=1)

    assert event1 is not None
    assert event2 is None  # should NOT create a duplicate event


def test_event_state_transitions():
    manager = EventManager(grace_period_seconds=3)
    rule = FakeRule()

    manager.process_rule_result(rule, is_firing=True, current_time=10.0, track_id=1)
    assert manager.get_active_events()[0].status == "Active"

    manager.process_rule_result(rule, is_firing=False, current_time=15.0, track_id=1)
    assert len(manager.get_active_events()) == 0
    assert manager.get_all_events()[0].status == "Resolved"