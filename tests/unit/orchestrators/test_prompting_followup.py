"""
DEV-251 Part 3: Tests for follow-up grounding rules in prompting.py

Verifies that:
1. Follow-up questions use concise-only grounding rules (no "Estrai TUTTO")
2. New questions use full completeness rules
3. The grounding rules constants are properly defined
"""

import pytest


class TestFollowupGroundingRules:
    """Tests for DEV-251 Part 3: Conditional grounding rules based on is_followup."""

    def test_followup_grounding_rules_exist(self) -> None:
        """DEV-251 Part 3: FOLLOWUP_GROUNDING_RULES constant should exist."""
        from app.orchestrators.prompting import FOLLOWUP_GROUNDING_RULES

        assert FOLLOWUP_GROUNDING_RULES is not None
        assert len(FOLLOWUP_GROUNDING_RULES) > 0

    def test_followup_grounding_rules_no_estrai_tutto(self) -> None:
        """DEV-251 Part 3: Follow-up rules should NOT contain contradicting 'Estrai TUTTO'."""
        from app.orchestrators.prompting import FOLLOWUP_GROUNDING_RULES

        # The key contradiction that caused verbose follow-ups
        assert "Estrai TUTTO" not in FOLLOWUP_GROUNDING_RULES
        assert "Non riassumere" not in FOLLOWUP_GROUNDING_RULES

    def test_followup_grounding_rules_has_concise_instructions(self) -> None:
        """DEV-251 Part 3: Follow-up rules should have concise-mode instructions."""
        from app.orchestrators.prompting import FOLLOWUP_GROUNDING_RULES

        # Key concise-mode markers
        assert "NON RIPETERE" in FOLLOWUP_GROUNDING_RULES
        assert "FOLLOW-UP" in FOLLOWUP_GROUNDING_RULES
        assert "2-5 frasi" in FOLLOWUP_GROUNDING_RULES

    def test_followup_grounding_rules_has_anti_hallucination(self) -> None:
        """DEV-251 Part 3: Follow-up rules should still have anti-hallucination rules."""
        from app.orchestrators.prompting import FOLLOWUP_GROUNDING_RULES

        # Must maintain accuracy even in concise mode
        assert "USA SOLO DATI DAL KB" in FOLLOWUP_GROUNDING_RULES
        assert "informazione non disponibile nel database PratikoAI" in FOLLOWUP_GROUNDING_RULES

    def test_followup_grounding_rules_has_examples(self) -> None:
        """DEV-251 Part 3: Follow-up rules should have good/bad examples."""
        from app.orchestrators.prompting import FOLLOWUP_GROUNDING_RULES

        assert "Risposta CORRETTA" in FOLLOWUP_GROUNDING_RULES
        assert "Risposta SBAGLIATA" in FOLLOWUP_GROUNDING_RULES
        assert "IMU" in FOLLOWUP_GROUNDING_RULES  # Example topic

    def test_concise_mode_prefix_still_exists(self) -> None:
        """DEV-251 Part 3: CONCISE_MODE_PREFIX should still exist for backward compat."""
        from app.orchestrators.prompting import CONCISE_MODE_PREFIX

        # Used by domain prompts (line ~516)
        assert CONCISE_MODE_PREFIX is not None
        assert "NON RIPETERE" in CONCISE_MODE_PREFIX or "RISPONDI DIRETTAMENTE" in CONCISE_MODE_PREFIX


class TestGroundingRulesSelection:
    """Tests for grounding rules selection logic based on is_followup flag."""

    def test_new_question_full_rules_contain_completeness(self) -> None:
        """DEV-251 Part 3: New questions should use rules with 'Estrai TUTTO'."""
        # This tests that the full completeness rules exist in the source
        import inspect

        from app.orchestrators import prompting

        source = inspect.getsource(prompting)
        # The full rules should contain completeness enforcement
        assert "Estrai TUTTO. Non riassumere. Non generalizzare." in source
        assert "INCLUDI TUTTE le informazioni" in source

    def test_followup_rules_and_full_rules_are_different(self) -> None:
        """DEV-251 Part 3: Follow-up rules should be distinct from full rules."""
        from app.orchestrators.prompting import FOLLOWUP_GROUNDING_RULES

        # Follow-up rules should not have the completeness requirements
        # that contradict concise mode
        assert "INCLUDI TUTTE le informazioni" not in FOLLOWUP_GROUNDING_RULES
        assert "Se un dato è nel KB, DEVE essere nella risposta" not in FOLLOWUP_GROUNDING_RULES


class TestFollowupDetectionIntegration:
    """Integration tests for follow-up detection and grounding rules."""

    def test_followup_triggers_exist_in_prompting(self) -> None:
        """DEV-251 Part 3: Follow-up detection triggers should exist."""
        import inspect

        from app.orchestrators import prompting

        source = inspect.getsource(prompting)
        # The follow-up detection log should exist
        assert "DEV251_part3_followup_grounding_rules" in source

    def test_new_question_triggers_exist_in_prompting(self) -> None:
        """DEV-251 Part 3: New question grounding rules log should exist."""
        import inspect

        from app.orchestrators import prompting

        source = inspect.getsource(prompting)
        # The new question detection log should exist
        assert "DEV251_part3_new_question_grounding_rules" in source
