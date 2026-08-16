import json
from collections import defaultdict
from database.repository import get_events


def suggest_scenarios():
    all_events = get_events()

    by_type = defaultdict(list)
    for event in all_events:
        by_type[event["event_type"]].append(event)

    scenarios = []
    scenario_counter = 1

    category_map = {
        "intrusion": ("zone_entry", 4),
        "loitering": ("loitering", 3),
        "wrong_direction": ("wrong_direction", 2),
        "overcrowding": ("overcrowding", 2),
    }

    for event_type, (category, needed_count) in category_map.items():
        events_of_type = by_type.get(event_type, [])
        picked = events_of_type[:needed_count]

        for event in picked:
            scenarios.append({
                "scenario_id": f"scenario_{scenario_counter:02d}",
                "category": category,
                "source_event_id": event["event_id"],
                "video_path": "FILL_IN_YOUR_VIDEO_PATH",
                "zone_id": event["zone_id"],
                "track_id": event["track_id"],
                "start_time_reference": event["start_time"],
                "expected_events": [
                    {"event_type": event_type, "expected_count": 1}
                ],
                "notes": f"Auto-suggested from real {event_type} event on track {event['track_id']}"
            })
            scenario_counter += 1

    # Placeholder entries for categories that need manual creation
    manual_categories = [
        ("normal", 4, "No violations expected - pick a calm segment manually"),
        ("line_crossing", 3, "Pick a clear line-crossing segment manually"),
        ("difficult_edge_case", 2, "Pick a heavily occluded/crowded segment manually"),
    ]

    for category, count, note in manual_categories:
        for i in range(count):
            scenarios.append({
                "scenario_id": f"scenario_{scenario_counter:02d}",
                "category": category,
                "source_event_id": None,
                "video_path": "FILL_IN_YOUR_VIDEO_PATH",
                "zone_id": None,
                "track_id": None,
                "start_time_reference": None,
                "expected_events": [],
                "notes": note
            })
            scenario_counter += 1

    output = {"scenarios": scenarios}

    with open("evaluation/scenarios_draft.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"Generated {len(scenarios)} scenario drafts -> evaluation/scenarios_draft.json")
    print("Review and fill in video_path/frame ranges for each, especially the manual ones.")


if __name__ == "__main__":
    suggest_scenarios()