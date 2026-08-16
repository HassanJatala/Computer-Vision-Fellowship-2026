from analytics.zones import ZoneManager
from rules.rule_engine import RuleEngine


def test_invalid_zone_config_does_not_crash():
    zone_manager = ZoneManager(zones_file="this_file_does_not_exist.json")
    assert zone_manager.get_all_zones() == {}


def test_invalid_rule_config_does_not_crash():
    rule_engine = RuleEngine(rules_file="this_file_does_not_exist.json")
    assert rule_engine.rules == []