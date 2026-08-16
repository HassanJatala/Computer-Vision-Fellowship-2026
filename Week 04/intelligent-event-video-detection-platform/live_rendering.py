# import cv2


# class LiveRenderer:
#     def __init__(self, dwell_tracker):
#         self.dwell_tracker = dwell_tracker

#         self.zone_colors = {
#             "zone_1": (0, 0, 255),
#             "zone_2": (0, 255, 255),
#             "zone_3": (255, 0, 0),
#         }
#         self.default_zone_color = (255, 255, 255)
#         self.track_box_color = (0, 255, 0)
#         self.line_color = (0, 140, 255)  # bright orange (BGR)

#     def draw(self, frame, zone_manager, all_track_states, current_time, line_manager=None):
#         annotated = frame.copy()

#         for zone_id, zone in zone_manager.get_all_zones().items():
#             color = self.zone_colors.get(zone_id, self.default_zone_color)
#             cv2.polylines(annotated, [zone.polygon], isClosed=True, color=color, thickness=2)
#             label_position = (int(zone.polygon[0][0]), int(zone.polygon[0][1]) + 35)
#             cv2.putText(annotated, zone.name, label_position,
#                         cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

#         if line_manager is not None:
#             for line_id, line in line_manager.lines.items():
#                 pt_a = tuple(int(c) for c in line.point_a)
#                 pt_b = tuple(int(c) for c in line.point_b)
#                 cv2.line(annotated, pt_a, pt_b, self.line_color, 3)
#                 label_pos = (pt_a[0], pt_a[1] - 15)
#                cv2.putText(annotated, line.name, label_pos,
#                             cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.line_color, 1)

#         for track_id, record in all_track_states.items():
#             x1, y1, x2, y2 = [int(c) for c in record["bbox"]]
#             cv2.rectangle(annotated, (x1, y1), (x2, y2), self.track_box_color, 2)

#             base_label = f"ID: {track_id} | {record['class_name']}"
#             cv2.putText(annotated, base_label, (x1, max(y1 - 12, 20)),
#                         cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.track_box_color, 1)

#             if record["current_zone"] is not None:
#                 zone = zone_manager.get_zone(record["current_zone"])
#                 dwell_time = self.dwell_tracker.get_current_dwell_time(record, current_time)
#                 zone_label = f"Zone: {zone.name} | In zone for: {dwell_time:.1f}s"
#                 cv2.putText(annotated, zone_label, (x1, y2 + 25),
#                             cv2.FONT_HERSHEY_SIMPLEX, 0.3,
#                             self.zone_colors.get(zone.zone_id, self.default_zone_color), 1)

#         return annotated

import cv2


class LiveRenderer:
    def __init__(self, dwell_tracker):
        self.dwell_tracker = dwell_tracker

        self.zone_colors = {
            "zone_1": (0, 0, 255),
            "zone_2": (0, 255, 255),
            "zone_3": (255, 0, 0),
        }
        self.default_zone_color = (255, 255, 255)
        self.track_box_color = (0, 255, 0)
        self.line_color = (0, 140, 255)  # bright orange (BGR)

    def draw(self, frame, zone_manager, all_track_states, current_time, line_manager=None):
        annotated = frame.copy()

        for zone_id, zone in zone_manager.get_all_zones().items():
            color = self.zone_colors.get(zone_id, self.default_zone_color)
            cv2.polylines(annotated, [zone.polygon], isClosed=True, color=color, thickness=2)
            label_position = (int(zone.polygon[0][0]), int(zone.polygon[0][1]) + 35)
            cv2.putText(annotated, zone.name, label_position,
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

        if line_manager is not None:
            for line_id, line in line_manager.lines.items():
                pt_a = tuple(int(c) for c in line.point_a)
                pt_b = tuple(int(c) for c in line.point_b)
                cv2.line(annotated, pt_a, pt_b, self.line_color, 3)
                label_pos = (pt_a[0], pt_a[1] - 15)
                cv2.putText(annotated, line.name, label_pos,
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.line_color, 1)

        for track_id, record in all_track_states.items():
            x1, y1, x2, y2 = [int(c) for c in record["bbox"]]
            cv2.rectangle(annotated, (x1, y1), (x2, y2), self.track_box_color, 2)

            base_label = f"ID: {track_id} | {record['class_name']}"
            cv2.putText(annotated, base_label, (x1, max(y1 - 12, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.track_box_color, 1)

            if record["current_zone"] is not None:
                zone = zone_manager.get_zone(record["current_zone"])
                dwell_time = self.dwell_tracker.get_current_dwell_time(record, current_time)
                zone_label = f"Zone: {zone.name} | In zone for: {dwell_time:.1f}s"
                cv2.putText(annotated, zone_label, (x1, y2 + 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.3,
                            self.zone_colors.get(zone.zone_id, self.default_zone_color), 1)

        return annotated