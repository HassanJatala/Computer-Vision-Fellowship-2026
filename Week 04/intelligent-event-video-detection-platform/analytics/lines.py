import json
import cv2


class Line:
    def __init__(self, line_id, name, point_a, point_b, expected_direction=None):
        self.line_id = line_id
        self.name = name
        self.point_a = point_a
        self.point_b = point_b
        self.expected_direction = expected_direction  # "A_to_B", "B_to_A", or None

    def get_side(self, point):
        x1, y1 = self.point_a
        x2, y2 = self.point_b
        px, py = point
        side_value = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
        if side_value > 0:
            return "A"
        elif side_value < 0:
            return "B"
        return "ON_LINE"


class LineManager:
    def __init__(self, lines_file="user_settings/lines.json"):
        self.lines_file = lines_file
        self.lines = {}
        self.track_sides = {}  # (track_id, line_id) -> last known side
        self.counters = {}  # line_id -> {"A_to_B": int, "B_to_A": int}
        self.load_lines()

    def load_lines(self):
        try:
            with open(self.lines_file, "r") as f:
                data = json.load(f)
            for line_data in data.get("lines", []):
                line = Line(
                    line_id=line_data["line_id"],
                    name=line_data["name"],
                    point_a=tuple(line_data["point_a"]),
                    point_b=tuple(line_data["point_b"]),
                    expected_direction=line_data.get("expected_direction"),
                )
                self.lines[line.line_id] = line
                self.counters[line.line_id] = {"A_to_B": 0, "B_to_A": 0}
        except FileNotFoundError:
            self.lines = {}

    def check_crossing(self, track_id, position):
        """
        Checks all lines for this track's position.
        Returns a list of crossing events: [{"line_id", "direction", "is_violation"}]
        """
        crossings = []

        for line_id, line in self.lines.items():
            current_side = line.get_side(position)
            key = (track_id, line_id)
            previous_side = self.track_sides.get(key)

            if previous_side is not None and current_side != previous_side and current_side != "ON_LINE":
                if previous_side == "A" and current_side == "B":
                    direction = "A_to_B"
                elif previous_side == "B" and current_side == "A":
                    direction = "B_to_A"
                else:
                    direction = None

                if direction:
                    self.counters[line_id][direction] += 1
                    is_violation = (
                        line.expected_direction is not None
                        and direction != line.expected_direction
                    )
                    crossings.append({
                        "line_id": line_id,
                        "direction": direction,
                        "is_violation": is_violation
                    })

            if current_side != "ON_LINE":
                self.track_sides[key] = current_side

        return crossings

    def get_counts(self, line_id):
        return self.counters.get(line_id, {"A_to_B": 0, "B_to_A": 0})