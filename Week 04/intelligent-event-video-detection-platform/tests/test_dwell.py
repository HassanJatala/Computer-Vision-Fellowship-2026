from analytics.dwell import DwellTracker


def test_dwell_time_calculation():
    tracker = DwellTracker()
    record = {"current_zone": "zone_1", "zone_entry_time": 10.0}
    dwell = tracker.get_current_dwell_time(record, current_time=25.0)
    assert dwell == 15.0


def test_loitering_trigger():
    tracker = DwellTracker()
    record = {"current_zone": "zone_1", "zone_entry_time": 0.0}
    assert tracker.is_over_threshold(record, current_time=70.0, threshold_seconds=60) == True
    assert tracker.is_over_threshold(record, current_time=30.0, threshold_seconds=60) == False