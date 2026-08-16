import json
import cv2
import numpy as np


class Zone:
    def __init__(self, zone_id, name, polygon, monitored_classes=None, associated_rules=None):
        self.zone_id = zone_id
        self.name = name
        # Convert to the format cv2.pointPolygonTest expects
        self.polygon = np.array(polygon, dtype=np.int32)
        self.monitored_classes = monitored_classes or ["person"]
        self.associated_rules = associated_rules or []

    def contains_point(self, point):
        """Returns True if the given (x, y) point is inside this zone's polygon."""
        result = cv2.pointPolygonTest(self.polygon, point, False)
        return result >= 0


class ZoneManager:
    def __init__(self, zones_file="user_settings/zones.json"):
        self.zones_file = zones_file
        self.zones = {}  # zone_id -> Zone object
        self.load_zones()

    def load_zones(self):
        try:
            with open(self.zones_file, "r") as f:
                data = json.load(f)
            for zone_data in data.get("zones", []):
                zone = Zone(
                    zone_id=zone_data["zone_id"],
                    name=zone_data["name"],
                    polygon=zone_data["polygon"],
                    monitored_classes=zone_data.get("monitored_classes"),
                    associated_rules=zone_data.get("associated_rules"),
                )
                self.zones[zone.zone_id] = zone
        except FileNotFoundError:
            # No zones configured yet - app should still run, just with zero zones
            self.zones = {}

    def find_zone_for_point(self, point, current_zone_id=None):
        """
        Determines which zone (if any) a point currently belongs to.
        Checks the previously-known zone first as a fast path,
        then falls back to checking all zones.
        Returns zone_id or None.
        """
        if current_zone_id is not None and current_zone_id in self.zones:
            if self.zones[current_zone_id].contains_point(point):
                return current_zone_id

        for zone_id, zone in self.zones.items():
            if zone.contains_point(point):
                return zone_id

        return None

    def get_zone(self, zone_id):
        return self.zones.get(zone_id)

    def get_all_zones(self):
        return self.zones