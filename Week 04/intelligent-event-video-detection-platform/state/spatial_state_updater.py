import time


class SpatialStateUpdater:
    """
    Coordinates zone membership detection and dwell tracking.
    Reads/writes TrackStateManager records using ZoneManager and DwellTracker.
    """

    def __init__(self, zone_manager, dwell_tracker):
        self.zone_manager = zone_manager
        self.dwell_tracker = dwell_tracker

    def update(self, track_record, current_time):
        """
        Given a single track's state record, checks for zone transitions,
        updates the record in place, and returns what changed this frame.

        Returns: {"entered_zone": zone_id or None, "exited_zone": zone_id or None}
        """
        position = track_record["position"]
        old_zone = track_record["current_zone"]

        new_zone = self.zone_manager.find_zone_for_point(position, old_zone)

        result = {"entered_zone": None, "exited_zone": None}

        if new_zone != old_zone:
            # Something changed - handle exit from old zone, if any
            if old_zone is not None:
                completed_dwell = current_time - track_record["zone_entry_time"]
                self.dwell_tracker.record_completed_dwell(old_zone, completed_dwell)
                result["exited_zone"] = old_zone

            # Handle entry into new zone, if any
            if new_zone is not None:
                track_record["zone_entry_time"] = current_time
                result["entered_zone"] = new_zone
            else:
                track_record["zone_entry_time"] = None

            track_record["previous_zone"] = old_zone
            track_record["current_zone"] = new_zone

        return result