from analytics.zones import Zone, ZoneManager


def test_point_inside_zone():
    zone = Zone("zone_1", "Test Zone", [[0, 0], [100, 0], [100, 100], [0, 100]])
    assert zone.contains_point((50, 50)) == True


def test_point_outside_zone():
    zone = Zone("zone_1", "Test Zone", [[0, 0], [100, 0], [100, 100], [0, 100]])
    assert zone.contains_point((200, 200)) == False


def test_zone_entry_detection():
    zone_manager = ZoneManager(zones_file="nonexistent.json")
    zone_manager.zones = {
        "zone_1": Zone("zone_1", "Test Zone", [[0, 0], [100, 0], [100, 100], [0, 100]])
    }
    result = zone_manager.find_zone_for_point((50, 50), current_zone_id=None)
    assert result == "zone_1"


def test_zone_exit_detection():
    zone_manager = ZoneManager(zones_file="nonexistent.json")
    zone_manager.zones = {
        "zone_1": Zone("zone_1", "Test Zone", [[0, 0], [100, 0], [100, 100], [0, 100]])
    }
    result = zone_manager.find_zone_for_point((200, 200), current_zone_id="zone_1")
    assert result is None