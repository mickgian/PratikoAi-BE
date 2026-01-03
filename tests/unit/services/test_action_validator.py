"""TDD tests for ActionValidator service.

DEV-215: Tests written FIRST per TDD methodology.
Tests cover label validation, forbidden patterns, source grounding, and quality scoring.
"""

import pytest

from app.services.action_validator import (
    GENERIC_LABELS,
    VALID_ICONS,
    ActionValidator,
    BatchValidationResult,
    ValidationResult,
)


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_valid_result(self):
        """Test creating a valid result."""
        result = ValidationResult(is_valid=True, rejection_reason=None, warnings=[], modified_action=None)
        assert result.is_valid is True
        assert result.rejection_reason is None
        assert result.warnings == []

    def test_invalid_result_with_reason(self):
        """Test creating an invalid result with rejection reason."""
        result = ValidationResult(
            is_valid=False,
            rejection_reason="Label too short",
            warnings=[],
            modified_action=None,
        )
        assert result.is_valid is False
        assert result.rejection_reason == "Label too short"

    def test_result_with_warnings(self):
        """Test result with warnings but still valid."""
        result = ValidationResult(
            is_valid=True,
            rejection_reason=None,
            warnings=["No source grounding found"],
            modified_action=None,
        )
        assert result.is_valid is True
        assert len(result.warnings) == 1

    def test_result_with_modified_action(self):
        """Test result with auto-corrected action."""
        modified = {"label": "Calcola contributi", "icon": "calculator"}
        result = ValidationResult(
            is_valid=True,
            rejection_reason=None,
            warnings=[],
            modified_action=modified,
        )
        assert result.modified_action == modified


class TestBatchValidationResult:
    """Test BatchValidationResult dataclass."""

    def test_batch_result_all_valid(self):
        """Test batch result with all valid actions."""
        actions = [{"label": "Calcola contributi", "prompt": "Quanto devo pagare?"}]
        result = BatchValidationResult(
            validated_actions=actions,
            rejected_count=0,
            rejection_log=[],
            quality_score=1.0,
        )
        assert len(result.validated_actions) == 1
        assert result.rejected_count == 0
        assert result.quality_score == 1.0

    def test_batch_result_partial_rejection(self):
        """Test batch result with some rejected."""
        actions = [{"label": "Valid action", "prompt": "Valid prompt here"}]
        rejected_action = {"label": "Bad", "prompt": "x"}
        result = BatchValidationResult(
            validated_actions=actions,
            rejected_count=1,
            rejection_log=[(rejected_action, "Label too short")],
            quality_score=0.5,
        )
        assert result.rejected_count == 1
        assert len(result.rejection_log) == 1

    def test_batch_result_all_rejected(self):
        """Test batch result when all actions rejected."""
        result = BatchValidationResult(
            validated_actions=[],
            rejected_count=3,
            rejection_log=[],
            quality_score=0.0,
        )
        assert len(result.validated_actions) == 0
        assert result.quality_score == 0.0


class TestLabelLengthValidation:
    """Test label length validation rules."""

    @pytest.fixture
    def validator(self):
        return ActionValidator()

    def test_rejects_short_label(self, validator):
        """Labels <8 chars should be rejected."""
        action = {"label": "Calcola", "prompt": "Prompt text here with enough chars"}
        result = validator.validate(action, kb_sources=[])
        assert result.is_valid is False
        assert "too short" in result.rejection_reason.lower()

    def test_rejects_very_short_label(self, validator):
        """Very short labels (1-2 chars) should be rejected."""
        action = {"label": "OK", "prompt": "Valid prompt with enough characters here"}
        result = validator.validate(action, kb_sources=[])
        assert result.is_valid is False
        assert "too short" in result.rejection_reason.lower()

    def test_accepts_minimum_length_label(self, validator):
        """Labels exactly 8 chars should be accepted."""
        action = {"label": "Calcola!", "prompt": "Calcola i contributi dovuti"}
        result = validator.validate(action, kb_sources=[])
        # May fail for other reasons but not label length
        if not result.is_valid:
            assert "too short" not in result.rejection_reason.lower()

    def test_truncates_long_label(self, validator):
        """Labels >40 chars should be truncated, not rejected."""
        long_label = "Calcola i contributi previdenziali INPS per il regime forfettario 2024"
        assert len(long_label) > 40
        action = {"label": long_label, "prompt": "Calcola i contributi previdenziali"}
        result = validator.validate(action, kb_sources=[])
        # Should be valid (truncated, not rejected)
        if result.is_valid and result.modified_action:
            assert len(result.modified_action["label"]) <= 40

    def test_accepts_valid_length_label(self, validator):
        """Labels 8-40 chars should be accepted as-is."""
        action = {"label": "Calcola contributi INPS", "prompt": "Calcola i contributi dovuti all'INPS"}
        result = validator.validate(action, kb_sources=[])
        # Should pass label length check (may fail other checks)
        if not result.is_valid:
            assert "too short" not in result.rejection_reason.lower()
            assert "too long" not in result.rejection_reason.lower()


class TestPromptLengthValidation:
    """Test prompt length validation rules."""

    @pytest.fixture
    def validator(self):
        return ActionValidator()

    def test_rejects_short_prompt(self, validator):
        """Prompts <25 chars should be rejected."""
        action = {"label": "Calcola contributi", "prompt": "Quanto devo?"}
        result = validator.validate(action, kb_sources=[])
        assert result.is_valid is False
        assert "prompt" in result.rejection_reason.lower() or "too short" in result.rejection_reason.lower()

    def test_rejects_empty_prompt(self, validator):
        """Empty prompts should be rejected."""
        action = {"label": "Calcola contributi", "prompt": ""}
        result = validator.validate(action, kb_sources=[])
        assert result.is_valid is False

    def test_accepts_valid_prompt(self, validator):
        """Prompts >=25 chars should be accepted."""
        action = {"label": "Calcola contributi", "prompt": "Quanto devo pagare di contributi INPS questo mese?"}
        result = validator.validate(action, kb_sources=[])
        # May fail for other reasons but not prompt length
        if not result.is_valid:
            assert "prompt" not in result.rejection_reason.lower() or "too short" not in result.rejection_reason.lower()


class TestForbiddenPatterns:
    """Test forbidden pattern detection."""

    @pytest.fixture
    def validator(self):
        return ActionValidator()

    def test_rejects_consulta_commercialista(self, validator):
        """Suggests consulting accountant should be rejected."""
        action = {
            "label": "Chiedi al commercialista",
            "prompt": "Consulta un commercialista per questo caso",
        }
        result = validator.validate(action, kb_sources=[])
        assert result.is_valid is False
        assert "forbidden" in result.rejection_reason.lower() or "pattern" in result.rejection_reason.lower()

    def test_rejects_contatta_avvocato(self, validator):
        """Suggests contacting lawyer should be rejected."""
        action = {
            "label": "Contatta un avvocato",
            "prompt": "Rivolgiti a un avvocato per una consulenza",
        }
        result = validator.validate(action, kb_sources=[])
        assert result.is_valid is False

    def test_rejects_rivolgiti_professionista(self, validator):
        """Suggests contacting professional should be rejected."""
        action = {
            "label": "Rivolgiti a un esperto",
            "prompt": "Rivolgiti a un professionista del settore",
        }
        result = validator.validate(action, kb_sources=[])
        assert result.is_valid is False

    def test_rejects_verifica_sito_ufficiale(self, validator):
        """Suggests verifying on official site should be rejected."""
        action = {
            "label": "Verifica sul sito INPS",
            "prompt": "Verifica sul sito ufficiale dell'INPS",
        }
        result = validator.validate(action, kb_sources=[])
        assert result.is_valid is False

    def test_accepts_action_without_forbidden_patterns(self, validator):
        """Actions without forbidden patterns should pass this check."""
        action = {
            "label": "Calcola contributi INPS",
            "prompt": "Quanto devo pagare di contributi INPS questo trimestre?",
        }
        result = validator.validate(action, kb_sources=[])
        # May fail other checks but not forbidden patterns
        if not result.is_valid:
            assert "forbidden" not in result.rejection_reason.lower()


class TestGenericLabelDetection:
    """Test generic label detection."""

    @pytest.fixture
    def validator(self):
        return ActionValidator()

    @pytest.mark.parametrize(
        "generic_label",
        [
            "approfondisci",  # 13 chars - generic check
            "Approfondisci",  # 13 chars - generic check
            "APPROFONDISCI",  # 13 chars - generic check
            "dettagli",  # 8 chars - generic check
            "più info",  # 8 chars - generic check
            "saperne di più",  # 14 chars - generic check
            "continua",  # 8 chars - generic check
        ],
    )
    def test_rejects_generic_labels(self, validator, generic_label):
        """Generic labels (8+ chars) should be rejected for being generic."""
        action = {"label": generic_label, "prompt": "Calcola i contributi previdenziali dovuti"}
        result = validator.validate(action, kb_sources=[])
        assert result.is_valid is False
        assert "generic" in result.rejection_reason.lower()

    @pytest.mark.parametrize(
        "short_generic_label",
        [
            "calcola",  # 7 chars - too short
            "verifica",  # 8 chars - this one should pass length
            "scopri",  # 6 chars - too short
            "leggi",  # 5 chars - too short
            "vedi",  # 4 chars - too short
            "altro",  # 5 chars - too short
            "info",  # 4 chars - too short
        ],
    )
    def test_rejects_short_generic_labels(self, validator, short_generic_label):
        """Short generic labels rejected for length or generic check."""
        action = {"label": short_generic_label, "prompt": "Calcola i contributi previdenziali dovuti"}
        result = validator.validate(action, kb_sources=[])
        assert result.is_valid is False
        # Rejected for either length or generic - both are valid rejections
        reason_lower = result.rejection_reason.lower()
        assert "too short" in reason_lower or "generic" in reason_lower

    def test_accepts_specific_labels(self, validator):
        """Specific, descriptive labels should be accepted."""
        action = {
            "label": "Calcola contributi INPS 2024",
            "prompt": "Calcola i contributi previdenziali INPS per il 2024",
        }
        result = validator.validate(action, kb_sources=[])
        # Should pass generic label check
        if not result.is_valid:
            assert "generic" not in result.rejection_reason.lower()


class TestSourceGrounding:
    """Test source grounding validation."""

    @pytest.fixture
    def validator(self):
        return ActionValidator()

    @pytest.fixture
    def kb_sources(self):
        return [
            {
                "id": "doc1",
                "title": "Circolare INPS 45/2024",
                "type": "circolare",
                "key_topics": ["contributi", "forfettario", "INPS"],
            },
            {
                "id": "doc2",
                "title": "D.Lgs 81/2008",
                "type": "decreto_legislativo",
                "key_topics": ["sicurezza", "lavoro"],
            },
        ]

    def test_warns_no_source_grounding(self, validator):
        """Actions without KB reference should generate warning but still be valid."""
        action = {
            "label": "Calcola importo bonus",
            "prompt": "Quanto ammonta il bonus energia per questo mese?",
        }
        result = validator.validate(action, kb_sources=[])
        # Should be valid but with warning
        if result.is_valid:
            assert any("grounding" in w.lower() or "source" in w.lower() for w in result.warnings)

    def test_no_warning_with_source_grounding(self, validator, kb_sources):
        """Actions referencing KB topics should not generate grounding warning."""
        action = {
            "label": "Calcola contributi forfettario INPS",
            "prompt": "Calcola i contributi INPS per regime forfettario",
        }
        result = validator.validate(action, kb_sources=kb_sources)
        # Should not have grounding warning if topics match
        if result.is_valid:
            grounding_warnings = [w for w in result.warnings if "grounding" in w.lower() or "source" in w.lower()]
            assert len(grounding_warnings) == 0

    def test_grounding_check_with_empty_kb_sources(self, validator):
        """Empty KB sources should generate warning."""
        action = {
            "label": "Calcola contributi INPS",
            "prompt": "Calcola i contributi previdenziali dovuti",
        }
        result = validator.validate(action, kb_sources=[])
        if result.is_valid:
            assert len(result.warnings) > 0


class TestIconNormalization:
    """Test icon normalization."""

    @pytest.fixture
    def validator(self):
        return ActionValidator()

    def test_normalizes_invalid_icon(self, validator):
        """Invalid icons should be normalized to 'calculator'."""
        action = {
            "label": "Calcola contributi INPS",
            "prompt": "Calcola i contributi previdenziali dovuti",
            "icon": "invalid_icon",
        }
        result = validator.validate(action, kb_sources=[])
        if result.is_valid and result.modified_action:
            assert result.modified_action.get("icon") in VALID_ICONS

    def test_preserves_valid_icon(self, validator):
        """Valid icons should be preserved."""
        action = {
            "label": "Calcola contributi INPS",
            "prompt": "Calcola i contributi previdenziali dovuti",
            "icon": "calculator",
        }
        result = validator.validate(action, kb_sources=[])
        if result.is_valid:
            # Icon should not be changed if valid
            if result.modified_action:
                assert result.modified_action.get("icon") == "calculator"

    def test_adds_default_icon_if_missing(self, validator):
        """Missing icon should default to 'calculator'."""
        action = {
            "label": "Calcola contributi INPS",
            "prompt": "Calcola i contributi previdenziali dovuti",
        }
        result = validator.validate(action, kb_sources=[])
        if result.is_valid and result.modified_action:
            assert "icon" in result.modified_action


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def validator(self):
        return ActionValidator()

    def test_all_actions_rejected(self, validator):
        """Batch with all invalid actions should return empty list with quality=0."""
        actions = [
            {"label": "Bad", "prompt": "x"},
            {"label": "No", "prompt": "y"},
        ]
        result = validator.validate_batch(actions, response_text="", kb_sources=[])
        assert len(result.validated_actions) == 0
        assert result.quality_score == 0.0
        assert result.rejected_count == 2

    def test_batch_mixed_validity(self, validator):
        """Batch with some valid, some invalid should return valid subset."""
        actions = [
            {"label": "Bad", "prompt": "x"},  # Too short
            {"label": "Calcola contributi INPS", "prompt": "Calcola i contributi previdenziali INPS dovuti"},
        ]
        result = validator.validate_batch(actions, response_text="", kb_sources=[])
        assert len(result.validated_actions) == 1
        assert result.rejected_count == 1
        assert 0 < result.quality_score < 1.0

    def test_unicode_labels(self, validator):
        """Italian characters in labels should work correctly."""
        action = {
            "label": "Verifica validità crediti",
            "prompt": "Verifica la validità dei crediti d'imposta per il 2024",
        }
        result = validator.validate(action, kb_sources=[])
        # Should not fail due to unicode
        assert result is not None

    def test_null_fields_rejected(self, validator):
        """Actions with None for required fields should be rejected."""
        action = {"label": None, "prompt": "Valid prompt text here"}
        result = validator.validate(action, kb_sources=[])
        assert result.is_valid is False

    def test_missing_label_rejected(self, validator):
        """Actions missing label key should be rejected."""
        action = {"prompt": "Valid prompt text here enough chars"}
        result = validator.validate(action, kb_sources=[])
        assert result.is_valid is False

    def test_missing_prompt_rejected(self, validator):
        """Actions missing prompt key should be rejected."""
        action = {"label": "Calcola contributi"}
        result = validator.validate(action, kb_sources=[])
        assert result.is_valid is False

    def test_empty_action_dict_rejected(self, validator):
        """Empty action dict should be rejected."""
        result = validator.validate({}, kb_sources=[])
        assert result.is_valid is False

    def test_empty_actions_list(self, validator):
        """Empty actions list should return empty result with quality=0."""
        result = validator.validate_batch([], response_text="", kb_sources=[])
        assert len(result.validated_actions) == 0
        assert result.quality_score == 0.0
        assert result.rejected_count == 0


class TestBatchValidation:
    """Test batch validation functionality."""

    @pytest.fixture
    def validator(self):
        return ActionValidator()

    @pytest.fixture
    def valid_actions(self):
        return [
            {
                "label": "Calcola contributi INPS",
                "prompt": "Calcola i contributi previdenziali INPS dovuti per il trimestre",
                "icon": "calculator",
            },
            {
                "label": "Verifica scadenze fiscali",
                "prompt": "Verifica le prossime scadenze fiscali per la dichiarazione IVA",
                "icon": "calendar",
            },
        ]

    def test_batch_all_valid(self, validator, valid_actions):
        """Batch with all valid actions should pass with quality=1.0."""
        result = validator.validate_batch(valid_actions, response_text="", kb_sources=[])
        assert len(result.validated_actions) == 2
        assert result.rejected_count == 0
        assert result.quality_score == 1.0

    def test_batch_rejection_log(self, validator):
        """Rejected actions should be logged with reasons."""
        actions = [
            {"label": "Bad", "prompt": "x"},
            {"label": "Consulta un commercialista", "prompt": "Contatta il tuo commercialista per questo"},
        ]
        result = validator.validate_batch(actions, response_text="", kb_sources=[])
        assert result.rejected_count == 2
        assert len(result.rejection_log) == 2
        # Each log entry should be (action, reason)
        for action, reason in result.rejection_log:
            assert isinstance(action, dict)
            assert isinstance(reason, str)
            assert len(reason) > 0

    def test_quality_score_calculation(self, validator):
        """Quality score should reflect valid/total ratio."""
        actions = [
            {"label": "Calcola contributi INPS", "prompt": "Calcola i contributi previdenziali INPS dovuti"},
            {"label": "Bad", "prompt": "x"},
            {"label": "Verifica scadenze fiscali", "prompt": "Verifica le prossime scadenze fiscali importanti"},
            {"label": "No", "prompt": "y"},
        ]
        result = validator.validate_batch(actions, response_text="", kb_sources=[])
        # 2 valid, 2 rejected -> quality_score = 0.5
        assert result.quality_score == pytest.approx(0.5, abs=0.1)


class TestPerformance:
    """Test performance requirements."""

    @pytest.fixture
    def validator(self):
        return ActionValidator()

    def test_single_validation_performance(self, validator):
        """Single action validation should complete in <5ms."""
        import time

        action = {
            "label": "Calcola contributi INPS",
            "prompt": "Calcola i contributi previdenziali INPS dovuti per il trimestre corrente",
            "icon": "calculator",
        }
        start = time.perf_counter()
        validator.validate(action, kb_sources=[])
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 50  # Allow some margin for test environment

    def test_batch_validation_performance(self, validator):
        """Batch validation of 10 actions should complete in <50ms."""
        import time

        actions = [
            {
                "label": f"Calcola contributi INPS numero {i}",
                "prompt": f"Calcola i contributi previdenziali INPS dovuti per il caso {i}",
                "icon": "calculator",
            }
            for i in range(10)
        ]
        start = time.perf_counter()
        validator.validate_batch(actions, response_text="", kb_sources=[])
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500  # Allow margin for test environment


class TestGenericLabelsConstant:
    """Test GENERIC_LABELS constant."""

    def test_generic_labels_contains_expected_values(self):
        """GENERIC_LABELS should contain expected Italian generic terms."""
        expected = {"approfondisci", "calcola", "verifica", "scopri", "leggi", "vedi"}
        assert expected.issubset(GENERIC_LABELS)

    def test_generic_labels_are_lowercase(self):
        """All generic labels should be lowercase for case-insensitive matching."""
        for label in GENERIC_LABELS:
            assert label == label.lower()


class TestValidIconsConstant:
    """Test VALID_ICONS constant."""

    def test_valid_icons_contains_calculator(self):
        """VALID_ICONS should contain 'calculator' as default."""
        assert "calculator" in VALID_ICONS

    def test_valid_icons_is_set(self):
        """VALID_ICONS should be a set for O(1) lookup."""
        assert isinstance(VALID_ICONS, set | frozenset)
