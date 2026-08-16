import json
from rules.intrusion import IntrusionRule
from rules.loitering import LoiteringRule
from rules.direction import DirectionRule
from rules.occupancy_rule import OccupancyRule


RULE_CLASSES = {
    "intrusion": IntrusionRule,
    "loitering": LoiteringRule,
    "direction": DirectionRule,
    "occupancy": OccupancyRule,
}


class RuleEngine:
    def __init__(self, rules_file="user_settings/rules.json"):
        self.rules_file = rules_file
        self.rules = []
        self.load_rules()

    def load_rules(self):
        try:
            with open(self.rules_file, "r") as f:
                data = json.load(f)
            for rule_data in data.get("rules", []):
                rule_type = rule_data.pop("type")
                rule_class = RULE_CLASSES.get(rule_type)
                if rule_class:
                    self.rules.append(rule_class(**rule_data))
        except FileNotFoundError:
            self.rules = []

    def evaluate(self, **context):
        """
        Runs every enabled rule's check() against the given context.
        Returns a list of rules that fired (True) this frame.
        """
        fired_rules = []
        for rule in self.rules:
            if rule.enabled and rule.check(**context):
                fired_rules.append(rule)
        return fired_rules