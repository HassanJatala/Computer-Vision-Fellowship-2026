from analytics.occupancy import OccupancyTracker


def test_occupancy_count():
    tracker = OccupancyTracker()
    all_states = {
        1: {"current_zone": "zone_1"},
        2: {"current_zone": "zone_1"},
        3: {"current_zone": "zone_2"},
    }
    count = tracker.get_current_occupancy("zone_1", all_states)
    assert count == 2


def test_occupancy_threshold():
    tracker = OccupancyTracker()
    all_states = {i: {"current_zone": "zone_1"} for i in range(12)}
    assert tracker.is_over_threshold("zone_1", all_states, max_capacity=10) == True
    assert tracker.is_over_threshold("zone_1", all_states, max_capacity=15) == False