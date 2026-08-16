class OccupancyTracker:
    """
    Tracks current, maximum, and average occupancy per zone.
    """

    def __init__(self):
        self.max_occupancy = {}  # zone_id -> highest count ever seen
        self.occupancy_samples = {}  # zone_id -> list of occupancy counts recorded over time

    def get_current_occupancy(self, zone_id, all_track_states):
        """
        Counts how many currently-tracked objects have current_zone == zone_id.
        """
        count = sum(
            1 for record in all_track_states.values()
            if record["current_zone"] == zone_id
        )
        return count

    def record_sample(self, zone_id, count):
        """
        Called once per frame to log the occupancy count for averaging/max tracking.
        """
        if zone_id not in self.occupancy_samples:
            self.occupancy_samples[zone_id] = []
        self.occupancy_samples[zone_id].append(count)

        if zone_id not in self.max_occupancy or count > self.max_occupancy[zone_id]:
            self.max_occupancy[zone_id] = count

    def get_max_occupancy(self, zone_id):
        return self.max_occupancy.get(zone_id, 0)

    def get_average_occupancy(self, zone_id):
        samples = self.occupancy_samples.get(zone_id, [])
        if not samples:
            return 0.0
        return sum(samples) / len(samples)

    def is_over_threshold(self, zone_id, all_track_states, max_capacity):
        return self.get_current_occupancy(zone_id, all_track_states) > max_capacity