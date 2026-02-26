"""DEV-303: Tests for MatchingRule SQLModel."""

from datetime import date

from app.models.matching_rule import MatchingRule, RuleType


class TestMatchingRuleCreation:
    """Test MatchingRule model creation and field defaults."""

    def test_matching_rule_creation(self) -> None:
        """Valid matching rule with all required fields."""
        rule = MatchingRule(
            name="R001 — Rottamazione Quater",
            description="Match clienti con debiti fiscali per rottamazione",
            rule_type=RuleType.NORMATIVA,
            conditions={"operator": "AND", "rules": [{"field": "debiti_fiscali", "op": ">", "value": 0}]},
            priority=90,
            valid_from=date(2025, 1, 1),
            categoria="FISCALE",
            fonte_normativa="Legge 197/2022",
        )

        assert rule.name == "R001 — Rottamazione Quater"
        assert rule.rule_type == RuleType.NORMATIVA
        assert rule.id is not None

    def test_matching_rule_enum_types(self) -> None:
        """All RuleType enum values are valid."""
        assert RuleType.NORMATIVA == "normativa"
        assert RuleType.SCADENZA == "scadenza"
        assert RuleType.OPPORTUNITA == "opportunita"

    def test_matching_rule_jsonb_conditions(self) -> None:
        """JSONB conditions support AND/OR operators."""
        conditions = {
            "operator": "OR",
            "rules": [
                {"field": "regime_fiscale", "op": "==", "value": "forfettario"},
                {
                    "operator": "AND",
                    "rules": [
                        {"field": "n_dipendenti", "op": ">", "value": 5},
                        {"field": "codice_ateco", "op": "starts_with", "value": "62"},
                    ],
                },
            ],
        }
        rule = MatchingRule(
            name="R002 — Bonus Sud",
            description="Match per agevolazioni sud",
            rule_type=RuleType.OPPORTUNITA,
            conditions=conditions,
            priority=80,
            valid_from=date(2025, 1, 1),
            categoria="FISCALE",
            fonte_normativa="DL 91/2017",
        )

        assert rule.conditions["operator"] == "OR"
        assert len(rule.conditions["rules"]) == 2

    def test_matching_rule_priority_ordering(self) -> None:
        """Priority is an int 1-100."""
        rule_high = MatchingRule(
            name="High",
            description="d",
            rule_type=RuleType.NORMATIVA,
            conditions={},
            priority=99,
            valid_from=date(2025, 1, 1),
            categoria="FISCALE",
            fonte_normativa="test",
        )
        rule_low = MatchingRule(
            name="Low",
            description="d",
            rule_type=RuleType.NORMATIVA,
            conditions={},
            priority=1,
            valid_from=date(2025, 1, 1),
            categoria="FISCALE",
            fonte_normativa="test",
        )
        assert rule_high.priority > rule_low.priority

    def test_matching_rule_validity_dates(self) -> None:
        """valid_from is required; valid_to is optional."""
        rule = MatchingRule(
            name="Temporal",
            description="d",
            rule_type=RuleType.SCADENZA,
            conditions={},
            priority=50,
            valid_from=date(2025, 1, 1),
            valid_to=date(2025, 12, 31),
            categoria="SCADENZA",
            fonte_normativa="test",
        )
        assert rule.valid_from == date(2025, 1, 1)
        assert rule.valid_to == date(2025, 12, 31)

    def test_matching_rule_valid_to_default_none(self) -> None:
        """valid_to defaults to None (open-ended rule)."""
        rule = MatchingRule(
            name="OpenEnded",
            description="d",
            rule_type=RuleType.NORMATIVA,
            conditions={},
            priority=50,
            valid_from=date(2025, 1, 1),
            categoria="FISCALE",
            fonte_normativa="test",
        )
        assert rule.valid_to is None

    def test_matching_rule_is_active_default(self) -> None:
        """is_active defaults to True."""
        rule = MatchingRule(
            name="Active",
            description="d",
            rule_type=RuleType.NORMATIVA,
            conditions={},
            priority=50,
            valid_from=date(2025, 1, 1),
            categoria="FISCALE",
            fonte_normativa="test",
        )
        assert rule.is_active is True

    def test_matching_rule_repr(self) -> None:
        """__repr__ includes name and rule_type."""
        rule = MatchingRule(
            name="ReprTest",
            description="d",
            rule_type=RuleType.NORMATIVA,
            conditions={},
            priority=50,
            valid_from=date(2025, 1, 1),
            categoria="FISCALE",
            fonte_normativa="test",
        )
        assert "ReprTest" in repr(rule)
        assert "normativa" in repr(rule)
