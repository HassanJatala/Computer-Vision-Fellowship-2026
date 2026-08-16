import time


class DwellTracker:
    """
    Calculates current dwell time for tracked objects, and maintains
    historical dwell records (per zone) to compute average/max dwell time.
    """

    def __init__(self):
        # history[zone_id] = list of completed dwell durations (in seconds)
        self.history = {}

    def get_current_dwell_time(self, track_record, current_time):
        """
        Returns how long this track has currently been in its zone.
        Returns 0 if not currently in any zone.
        """
        if track_record["current_zone"] is None or track_record["zone_entry_time"] is None:
            return 0.0

        return current_time - track_record["zone_entry_time"]

    def record_completed_dwell(self, zone_id, dwell_duration):
        """
        Called when a track exits a zone - logs the completed dwell duration
        into that zone's history for average/max calculations.
        """
        if zone_id not in self.history:
            self.history[zone_id] = []
        self.history[zone_id].append(dwell_duration)

    def get_average_dwell_time(self, zone_id):
        durations = self.history.get(zone_id, [])
        if not durations:
            return 0.0
        return sum(durations) / len(durations)

    def get_max_dwell_time(self, zone_id):
        durations = self.history.get(zone_id, [])
        if not durations:
            return 0.0
        return max(durations)

    def is_over_threshold(self, track_record, current_time, threshold_seconds):
        """
        Checks if current dwell time exceeds a given threshold.
        Used by loitering rule logic later.
        """
        return self.get_current_dwell_time(track_record, current_time) > threshold_seconds