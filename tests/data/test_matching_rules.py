"""DEV-321: Tests for pre-configured matching rules JSON data."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def matching_rules() -> list[dict]:
    rules_path = Path(__file__).resolve().parent.parent.parent / "app" / "data" / "matching_rules.json"
    return json.loads(rules_path.read_text(encoding="utf-8"))


class TestMatchingRulesData:
    """Test matching_rules.json structure and completeness."""

    def test_total_rules_count(self, matching_rules: list[dict]) -> None:
        """Happy path: 15 total rules (10 MVP + 5 extended)."""
        assert len(matching_rules) == 15

    def test_mvp_rules_present(self, matching_rules: list[dict]) -> None:
        """Happy path: R001 through R010 MVP rules exist."""
        names = [r["name"] for r in matching_rules]
        for i in range(1, 11):
            prefix = f"R{i:03d}"
            assert any(prefix in n for n in names), f"Missing MVP rule {prefix}"

    def test_extended_rules_present(self, matching_rules: list[dict]) -> None:
        """Happy path: R011 through R015 extended rules exist."""
        names = [r["name"] for r in matching_rules]
        for i in range(11, 16):
            prefix = f"R{i:03d}"
            assert any(prefix in n for n in names), f"Missing extended rule {prefix}"

    def test_rule_required_fields(self, matching_rules: list[dict]) -> None:
        """All rules have required fields."""
        required = [
            "name",
            "description",
            "rule_type",
            "conditions",
            "priority",
            "valid_from",
            "categoria",
            "fonte_normativa",
        ]
        for rule in matching_rules:
            for field in required:
                assert field in rule, f"Rule '{rule.get('name', '?')}' missing field '{field}'"

    def test_rule_types_valid(self, matching_rules: list[dict]) -> None:
        """All rule_type values are valid."""
        valid_types = {"normativa", "scadenza", "opportunita"}
        for rule in matching_rules:
            assert rule["rule_type"] in valid_types, (
                f"Invalid rule_type '{rule['rule_type']}' in rule '{rule['name']}'"
            )

    def test_priority_ranges(self, matching_rules: list[dict]) -> None:
        """Edge case: all priorities are between 1 and 100."""
        for rule in matching_rules:
            assert 1 <= rule["priority"] <= 100, f"Priority {rule['priority']} out of range in '{rule['name']}'"

    def test_conditions_structure(self, matching_rules: list[dict]) -> None:
        """All conditions use AND/OR operator structure."""
        for rule in matching_rules:
            conditions = rule["conditions"]
            assert isinstance(conditions, dict), f"conditions must be dict in '{rule['name']}'"
            assert any(k in conditions for k in ("AND", "OR")), f"conditions must have AND or OR in '{rule['name']}'"

    def test_unique_names(self, matching_rules: list[dict]) -> None:
        """Error case: no duplicate rule names."""
        names = [r["name"] for r in matching_rules]
        assert len(names) == len(set(names)), "Duplicate rule names found"
