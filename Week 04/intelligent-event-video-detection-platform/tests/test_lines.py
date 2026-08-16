from analytics.lines import Line, LineManager


def test_line_side_detection():
    line = Line("line_1", "Test Line", (500, 0), (500, 1000))
    side_left = line.get_side((400, 500))
    side_right = line.get_side((600, 500))
    assert side_left != side_right


def test_line_crossing_direction():
    line_manager = LineManager(lines_file="nonexistent.json")
    line_manager.lines = {"line_1": Line("line_1", "Test Line", (500, 0), (500, 1000))}
    line_manager.counters = {"line_1": {"A_to_B": 0, "B_to_A": 0}}

    crossings_1 = line_manager.check_crossing(track_id=1, position=(400, 500))
    assert crossings_1 == []

    crossings_2 = line_manager.check_crossing(track_id=1, position=(600, 500))
    assert len(crossings_2) == 1
    assert crossings_2[0]["direction"] in ("A_to_B", "B_to_A")