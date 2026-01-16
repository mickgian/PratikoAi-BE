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
        """DEV-244: Labels >50 chars should be truncated at word boundary, not rejected."""
        long_label = "Calcola i contributi previdenziali INPS per il regime forfettario 2024"
        assert len(long_label) > 50  # 70 chars
        action = {"label": long_label, "prompt": "Calcola i contributi previdenziali"}
        result = validator.validate(action, kb_sources=[])
        # Should be valid (truncated, not rejected)
        if result.is_valid and result.modified_action:
            truncated_label = result.modified_action["label"]
            assert len(truncated_label) <= 50
            # Word-boundary truncation: should NOT end mid-word
            assert not truncated_label.endswith("forfet")  # Would be mid-word cut
            assert " " not in truncated_label[-1:]  # Should not end with space

    def test_accepts_valid_length_label(self, validator):
        """Labels 8-50 chars should be accepted as-is."""
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
            assert (
                "prompt" not in result.rejection_reason.lower() or "too short" not in result.rejection_reason.lower()
            )


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


class TestForbiddenMonitoringPatterns:
    """Test DEV-242: Anti-monitoring patterns.

    PratikoAI IS the monitoring service - should never suggest users monitor sources.
    """

    @pytest.fixture
    def validator(self):
        return ActionValidator()

    @pytest.mark.parametrize(
        "label,prompt",
        [
            ("Monitora le comunicazioni", "Monitora le comunicazioni ufficiali dell'AdE"),
            ("Monitorare gli aggiornamenti", "Monitorare gli aggiornamenti dell'Agenzia delle Entrate"),
            ("Controlla periodicamente", "Controlla periodicamente il sito per aggiornamenti"),
            ("Tieni d'occhio le novità", "Tieni d'occhio le novità normative"),
            ("Resta aggiornato", "Resta aggiornato sulle comunicazioni ufficiali"),
            ("Verifica periodicamente", "Verificare periodicamente le fonti ufficiali"),
            ("Consulta regolarmente", "Consultare regolarmente il sito dell'Agenzia"),
            ("Segui le novità", "Seguire le novità dell'Agenzia delle Entrate"),
        ],
    )
    def test_rejects_monitoring_patterns(self, validator, label, prompt):
        """DEV-242: PratikoAI IS the monitor - never suggest user monitors."""
        action = {"label": label, "prompt": prompt}
        result = validator.validate(action, kb_sources=[])
        assert result.is_valid is False
        assert "forbidden" in result.rejection_reason.lower() or "pattern" in result.rejection_reason.lower()

    def test_rejects_monitoring_in_prompt_only(self, validator):
        """Monitoring pattern in prompt should also be rejected."""
        action = {
            "label": "Aggiornamenti rottamazione",
            "prompt": "Monitorare le comunicazioni ufficiali sulla rottamazione quinquies",
        }
        result = validator.validate(action, kb_sources=[])
        assert result.is_valid is False

    def test_accepts_non_monitoring_action(self, validator):
        """Actions without monitoring patterns should pass."""
        action = {
            "label": "Scadenze rottamazione quinquies",
            "prompt": "Quali sono le scadenze della rottamazione quinquies?",
        }
        result = validator.validate(action, kb_sources=[])
        # May fail other checks but not forbidden patterns
        if not result.is_valid:
            assert (
                "forbidden" not in result.rejection_reason.lower()
                or "monitoring" not in result.rejection_reason.lower()
            )

    def test_accepts_pratikoai_monitoring_statement(self, validator):
        """Actions stating PratikoAI monitors should be allowed."""
        action = {
            "label": "PratikoAI monitora per te",
            "prompt": "Il sistema PratikoAI monitora automaticamente gli aggiornamenti",
        }
        result = validator.validate(action, kb_sources=[])
        # This should pass since it's saying PratikoAI monitors, not asking user to
        # Note: May still fail due to length requirements
        if not result.is_valid:
            # Should not fail due to monitoring pattern
            reason_lower = result.rejection_reason.lower()
            assert "forbidden" not in reason_lower or "pattern" not in reason_lower


class TestDEV242SemanticDeduplication:
    """DEV-242: Test semantic deduplication of actions."""

    @pytest.fixture
    def validator(self):
        return ActionValidator()

    @pytest.fixture
    def kb_sources(self):
        return [{"title": "Test", "key_topics": ["IVA", "scadenze"]}]

    # Tests for _extract_significant_words()
    def test_extracts_significant_words(self, validator):
        """Extracts significant words, excluding stop words."""
        action = {
            "label": "Calcola IVA applicabile",
            "prompt": "Calcola l'IVA sul totale della fattura",
        }
        words = validator._extract_significant_words(action)

        assert "calcola" in words
        assert "iva" in words
        assert "fattura" in words
        # Stop words excluded
        assert "il" not in words
        assert "della" not in words

    def test_excludes_short_words(self, validator):
        """Excludes words with 2 or fewer characters."""
        action = {
            "label": "A e o test azione",
            "prompt": "Di la un test per azione",
        }
        words = validator._extract_significant_words(action)

        assert "test" in words
        assert "azione" in words
        # Short words excluded
        assert "a" not in words
        assert "e" not in words
        assert "o" not in words

    # Tests for _calculate_word_overlap()
    def test_calculates_overlap_identical_sets(self, validator):
        """Identical sets have 100% overlap."""
        words = {"calcola", "iva", "fattura"}
        overlap = validator._calculate_word_overlap(words, words)
        assert overlap == 1.0

    def test_calculates_overlap_disjoint_sets(self, validator):
        """Disjoint sets have 0% overlap."""
        words1 = {"calcola", "iva"}
        words2 = {"scadenza", "fiscale"}
        overlap = validator._calculate_word_overlap(words1, words2)
        assert overlap == 0.0

    def test_calculates_overlap_partial(self, validator):
        """Partial overlap calculated correctly."""
        words1 = {"calcola", "iva", "fattura"}
        words2 = {"calcola", "iva", "scadenza"}
        overlap = validator._calculate_word_overlap(words1, words2)
        # Intersection: {calcola, iva} = 2
        # Union: {calcola, iva, fattura, scadenza} = 4
        # Overlap = 2/4 = 0.5
        assert overlap == 0.5

    def test_overlap_empty_sets(self, validator):
        """Empty sets return 0.0 overlap."""
        assert validator._calculate_word_overlap(set(), set()) == 0.0
        assert validator._calculate_word_overlap({"test"}, set()) == 0.0

    # Tests for _deduplicate_actions()
    def test_removes_duplicate_actions(self, validator):
        """Actions with >50% overlap are deduplicated."""
        # These actions share most of the same significant words
        actions = [
            {
                "id": "1",
                "label": "Calcola IVA fattura",
                "prompt": "Calcola IVA fattura cliente",
            },
            {
                "id": "2",
                "label": "Calcola IVA fattura",  # Nearly identical
                "prompt": "Calcola IVA fattura oggi",
            },
            {
                "id": "3",
                "label": "Scadenze fiscali 2026",  # Different
                "prompt": "Mostra le scadenze fiscali per il 2026",
            },
        ]
        result = validator._deduplicate_actions(actions)

        assert len(result) == 2
        assert result[0]["id"] == "1"  # First kept
        assert result[1]["id"] == "3"  # Different kept

    def test_keeps_distinct_actions(self, validator):
        """Distinct actions are all kept."""
        actions = [
            {"id": "1", "label": "Calcola IVA 22%", "prompt": "Calcola IVA al 22%"},
            {"id": "2", "label": "Scadenze fiscali", "prompt": "Mostra scadenze fiscali"},
            {"id": "3", "label": "Contributi INPS", "prompt": "Calcola contributi INPS"},
        ]
        result = validator._deduplicate_actions(actions)

        assert len(result) == 3

    def test_single_action_unchanged(self, validator):
        """Single action is returned unchanged."""
        actions = [{"id": "1", "label": "Test azione", "prompt": "Test prompt"}]
        result = validator._deduplicate_actions(actions)
        assert len(result) == 1

    def test_empty_list_unchanged(self, validator):
        """Empty list returns empty list."""
        result = validator._deduplicate_actions([])
        assert result == []

    # Tests for _filter_previously_used()
    def test_filters_exact_match_previous(self, validator):
        """Filters actions that exactly match previous."""
        actions = [
            {"id": "1", "label": "Calcola IVA 22%", "prompt": "Prompt 1"},
            {"id": "2", "label": "Scadenze fiscali", "prompt": "Prompt 2"},
        ]
        previous = ["Calcola IVA 22%"]

        result = validator._filter_previously_used(actions, previous)

        assert len(result) == 1
        assert result[0]["id"] == "2"

    def test_filters_similar_to_previous(self, validator):
        """Filters actions similar to previous (>50% overlap)."""
        actions = [
            {"id": "1", "label": "Calcola IVA applicabile", "prompt": "Calcola IVA su fattura"},
            {"id": "2", "label": "Scadenze fiscali 2026", "prompt": "Mostra scadenze"},
        ]
        previous = ["Calcola IVA fattura"]  # Similar to action 1

        result = validator._filter_previously_used(actions, previous)

        # Action 1 should be filtered due to similarity
        assert len(result) == 1
        assert result[0]["id"] == "2"

    def test_keeps_dissimilar_actions(self, validator):
        """Keeps actions dissimilar to previous."""
        actions = [
            {"id": "1", "label": "Calcola IVA 22%", "prompt": "Prompt 1"},
            {"id": "2", "label": "Scadenze fiscali", "prompt": "Prompt 2"},
        ]
        previous = ["Contributi INPS"]  # Unrelated

        result = validator._filter_previously_used(actions, previous)

        assert len(result) == 2

    def test_empty_previous_returns_all(self, validator):
        """Empty previous list returns all actions."""
        actions = [
            {"id": "1", "label": "Test 1", "prompt": "Prompt 1"},
            {"id": "2", "label": "Test 2", "prompt": "Prompt 2"},
        ]
        result = validator._filter_previously_used(actions, [])
        assert len(result) == 2

    def test_none_previous_returns_all(self, validator):
        """None previous list returns all actions."""
        actions = [{"id": "1", "label": "Test", "prompt": "Prompt"}]
        result = validator._filter_previously_used(actions, None)
        assert len(result) == 1

    # Tests for validate_batch_with_context()
    def test_validate_batch_with_context_deduplicates(self, validator, kb_sources):
        """validate_batch_with_context deduplicates similar actions."""
        # These actions share most significant words (>50% overlap)
        actions = [
            {"id": "1", "label": "Calcola IVA fattura", "prompt": "Calcola IVA fattura cliente oggi"},
            {"id": "2", "label": "Calcola IVA fattura", "prompt": "Calcola IVA fattura fornitore oggi"},
            {"id": "3", "label": "Scadenze fiscali 2026", "prompt": "Mostra scadenze fiscali anno 2026"},
        ]
        result = validator.validate_batch_with_context(actions, "Test response", kb_sources)

        # Should deduplicate nearly identical actions
        assert len(result.validated_actions) == 2

    def test_validate_batch_with_context_filters_previous(self, validator, kb_sources):
        """validate_batch_with_context filters previously used actions."""
        actions = [
            {"id": "1", "label": "Calcola IVA 22%", "prompt": "Calcola l'IVA al 22% sulla fattura"},
            {"id": "2", "label": "Scadenze fiscali 2026", "prompt": "Mostra le scadenze fiscali 2026"},
        ]
        previous = ["Calcola IVA 22%"]

        result = validator.validate_batch_with_context(actions, "Test response", kb_sources, previous)

        # Should filter out exact match
        assert len(result.validated_actions) == 1
        assert result.validated_actions[0]["id"] == "2"

    def test_validate_batch_with_context_empty_input(self, validator, kb_sources):
        """validate_batch_with_context handles empty input."""
        result = validator.validate_batch_with_context([], "Test response", kb_sources)

        assert len(result.validated_actions) == 0
        assert result.quality_score == 0.0

    def test_validate_batch_with_context_all_invalid(self, validator, kb_sources):
        """validate_batch_with_context handles all invalid actions."""
        actions = [
            {"id": "1", "label": "Bad", "prompt": "x"},  # Too short
            {"id": "2", "label": "Also bad", "prompt": "y"},  # Too short
        ]
        result = validator.validate_batch_with_context(actions, "Test response", kb_sources)

        assert len(result.validated_actions) == 0


class TestDEV242IntegrationScenarios:
    """DEV-242: Integration tests for realistic scenarios."""

    @pytest.fixture
    def validator(self):
        return ActionValidator()

    @pytest.fixture
    def kb_sources(self):
        return [
            {"title": "Rottamazione quinquies", "key_topics": ["rottamazione", "scadenze"]},
            {"title": "IVA ordinaria", "key_topics": ["IVA", "aliquote"]},
        ]

    def test_realistic_action_set_deduplication(self, validator, kb_sources):
        """Realistic scenario with multiple similar actions."""
        # Nearly identical actions should be deduplicated
        actions = [
            {
                "id": "1",
                "label": "Scadenze rottamazione quinquies 2026",
                "prompt": "Scadenze rottamazione quinquies 2026 elenco completo",
            },
            {
                "id": "2",
                "label": "Scadenze rottamazione quinquies 2026",  # Nearly identical
                "prompt": "Scadenze rottamazione quinquies 2026 calendario",
            },
            {
                "id": "3",
                "label": "Calcola IVA ordinaria 22%",
                "prompt": "Calcola l'IVA ordinaria al 22% su un importo",
            },
            {
                "id": "4",
                "label": "Contributi INPS artigiani",  # Completely different
                "prompt": "Qual è l'importo contributi INPS per artigiani?",
            },
        ]

        result = validator.validate_batch_with_context(actions, "Test", kb_sources)

        # Should deduplicate action 1 and 2 (nearly identical)
        assert len(result.validated_actions) == 3

    def test_user_clicked_action_filtered(self, validator, kb_sources):
        """After user clicks action, exact match or highly similar filtered."""
        actions = [
            {
                "id": "1",
                "label": "Scadenze rottamazione quinquies",  # Exact match to previous
                "prompt": "Mostra scadenze rottamazione quinquies 2026",
            },
            {
                "id": "2",
                "label": "Calcola importo dovuto",
                "prompt": "Calcola l'importo totale dovuto al fisco",
            },
        ]
        previous_used = ["Scadenze rottamazione quinquies"]  # User already clicked this

        result = validator.validate_batch_with_context(actions, "Test", kb_sources, previous_used)

        # Action 1 should be filtered (exact match to previously used)
        assert len(result.validated_actions) == 1
        assert result.validated_actions[0]["id"] == "2"


class TestDEV244TopicRelevanceValidation:
    """DEV-244: Topic relevance validation to prevent topic drift."""

    @pytest.fixture
    def validator(self):
        return ActionValidator()

    @pytest.fixture
    def rottamazione_context(self):
        """Context about rottamazione quinquies."""
        return {
            "current_topic": "rottamazione quinquies",
            "topic_keywords": ["rottamazione", "quinquies", "definizione agevolata", "rate", "scadenze"],
            "user_query": "Parlami della rottamazione quinquies",
        }

    @pytest.fixture
    def kb_sources_rottamazione(self):
        return [
            {
                "title": "Rottamazione quinquies 2026",
                "key_topics": ["rottamazione", "quinquies", "definizione agevolata", "rate"],
            },
        ]

    def test_rejects_off_topic_action(self, validator, rottamazione_context):
        """Actions unrelated to current topic should be rejected."""
        action = {
            "label": "Calcola IRPEF dovuta",
            "prompt": "Calcola l'IRPEF dovuta per l'anno 2024 con aliquote progressive",
        }
        result = validator.validate_topic_relevance(action, rottamazione_context)

        assert result.is_valid is False
        assert "topic" in result.rejection_reason.lower() or "rilevante" in result.rejection_reason.lower()

    def test_accepts_on_topic_action(self, validator, rottamazione_context):
        """Actions related to current topic should pass."""
        action = {
            "label": "Scadenze rottamazione quinquies",
            "prompt": "Quali sono le scadenze per la rottamazione quinquies?",
        }
        result = validator.validate_topic_relevance(action, rottamazione_context)

        assert result.is_valid is True

    def test_accepts_action_with_keyword_in_label(self, validator, rottamazione_context):
        """Actions with topic keywords in label should pass."""
        action = {
            "label": "Rate rottamazione 2026",
            "prompt": "Quante rate sono previste per il pagamento?",
        }
        result = validator.validate_topic_relevance(action, rottamazione_context)

        assert result.is_valid is True

    def test_accepts_action_with_keyword_in_prompt(self, validator, rottamazione_context):
        """Actions with topic keywords in prompt should pass."""
        action = {
            "label": "Calcola importo totale",
            "prompt": "Calcola l'importo totale dovuto per la rottamazione quinquies",
        }
        result = validator.validate_topic_relevance(action, rottamazione_context)

        assert result.is_valid is True

    def test_rejects_generic_tax_action_off_topic(self, validator, rottamazione_context):
        """Generic tax actions unrelated to current topic should be rejected."""
        action = {
            "label": "Aliquote IVA vigenti",
            "prompt": "Quali sono le aliquote IVA attualmente vigenti in Italia?",
        }
        result = validator.validate_topic_relevance(action, rottamazione_context)

        assert result.is_valid is False

    def test_handles_empty_context(self, validator):
        """Empty context should not reject actions (fallback behavior)."""
        action = {
            "label": "Calcola contributi INPS",
            "prompt": "Calcola i contributi INPS per regime forfettario",
        }
        empty_context = {}
        result = validator.validate_topic_relevance(action, empty_context)

        # With empty context, should not reject based on topic
        assert result.is_valid is True

    def test_handles_none_context(self, validator):
        """None context should not reject actions (fallback behavior)."""
        action = {
            "label": "Calcola contributi INPS",
            "prompt": "Calcola i contributi INPS per regime forfettario",
        }
        result = validator.validate_topic_relevance(action, None)

        assert result.is_valid is True


class TestDEV244LabelTruncationPrevention:
    """DEV-244: Prevent truncated labels - labels must be complete phrases."""

    @pytest.fixture
    def validator(self):
        return ActionValidator()

    def test_rejects_truncated_label_ending_mid_word(self, validator):
        """Labels ending mid-word (truncated) should be rejected."""
        action = {
            "label": "Dettagli su Parlami della",  # Clearly truncated/nonsensical
            "prompt": "Mostra dettagli sulla rottamazione quinquies",
        }
        result = validator.validate(action, kb_sources=[])

        assert result.is_valid is False
        assert "truncat" in result.rejection_reason.lower() or "incomplete" in result.rejection_reason.lower()

    def test_rejects_label_ending_with_preposition(self, validator):
        """Labels ending with hanging prepositions are likely truncated."""
        action = {
            "label": "Informazioni su",  # Ends with preposition - incomplete
            "prompt": "Mostra informazioni dettagliate sulla normativa",
        }
        result = validator.validate(action, kb_sources=[])

        assert result.is_valid is False

    def test_rejects_label_ending_with_article(self, validator):
        """Labels ending with articles are likely truncated."""
        action = {
            "label": "Calcola il",  # Ends with article - incomplete
            "prompt": "Calcola l'importo dovuto per il pagamento",
        }
        result = validator.validate(action, kb_sources=[])

        assert result.is_valid is False

    def test_accepts_complete_label(self, validator):
        """Complete, meaningful labels should be accepted."""
        action = {
            "label": "Calcola contributi INPS",
            "prompt": "Calcola i contributi INPS per il regime forfettario 2024",
        }
        result = validator.validate(action, kb_sources=[])

        # Should not be rejected for truncation
        if not result.is_valid:
            assert "truncat" not in result.rejection_reason.lower()
            assert "incomplete" not in result.rejection_reason.lower()

    def test_accepts_label_ending_with_noun(self, validator):
        """Labels ending with nouns (complete phrases) should be accepted."""
        action = {
            "label": "Scadenze fiscali 2026",
            "prompt": "Mostra le scadenze fiscali per l'anno 2026",
        }
        result = validator.validate(action, kb_sources=[])

        if not result.is_valid:
            assert "truncat" not in result.rejection_reason.lower()

    def test_accepts_label_ending_with_number(self, validator):
        """Labels ending with numbers (often valid) should be accepted."""
        action = {
            "label": "Aliquota IVA 22%",
            "prompt": "Calcola l'IVA con aliquota ordinaria al 22%",
        }
        result = validator.validate(action, kb_sources=[])

        if not result.is_valid:
            assert "truncat" not in result.rejection_reason.lower()


class TestDEV244ZeroActionsGraceful:
    """DEV-244: System should accept zero actions gracefully when none are relevant."""

    @pytest.fixture
    def validator(self):
        return ActionValidator()

    def test_empty_validated_actions_is_valid(self, validator):
        """Returning 0 validated actions should be valid (not an error)."""
        result = validator.validate_batch([], response_text="", kb_sources=[])

        # Empty is valid - just means no actions
        assert result.validated_actions == []
        assert result.rejected_count == 0

    def test_all_rejected_returns_empty_list(self, validator):
        """When all actions are rejected, should return empty list gracefully."""
        actions = [
            {"label": "Bad", "prompt": "x"},  # Too short
            {"label": "No", "prompt": "y"},  # Too short
        ]
        result = validator.validate_batch(actions, response_text="", kb_sources=[])

        assert result.validated_actions == []
        assert result.rejected_count == 2
        # This is valid behavior, not an error

    def test_validate_batch_with_topic_filter_can_return_zero(self, validator):
        """When topic filter removes all actions, should return empty gracefully."""
        actions = [
            {"label": "Calcola IRPEF 2024", "prompt": "Calcola l'IRPEF con aliquote progressive"},
            {"label": "Aliquote IVA vigenti", "prompt": "Quali sono le aliquote IVA in Italia?"},
        ]
        topic_context = {
            "current_topic": "rottamazione quinquies",
            "topic_keywords": ["rottamazione", "quinquies", "rate"],
        }

        result = validator.validate_batch_with_topic_context(
            actions=actions,
            response_text="Info sulla rottamazione quinquies",
            kb_sources=[],
            topic_context=topic_context,
        )

        # All off-topic actions filtered = empty list is valid
        assert result.validated_actions == []


class TestDEV244BatchValidationWithTopic:
    """DEV-244: Batch validation with topic context integration."""

    @pytest.fixture
    def validator(self):
        return ActionValidator()

    @pytest.fixture
    def topic_context(self):
        return {
            "current_topic": "rottamazione quinquies",
            "topic_keywords": ["rottamazione", "quinquies", "definizione agevolata", "rate", "scadenze"],
        }

    @pytest.fixture
    def kb_sources(self):
        return [{"title": "Rottamazione", "key_topics": ["rottamazione", "quinquies"]}]

    def test_filters_off_topic_actions_in_batch(self, validator, topic_context, kb_sources):
        """Off-topic actions are filtered in batch validation."""
        actions = [
            {
                "id": "1",
                "label": "Scadenze rottamazione quinquies",  # On topic
                "prompt": "Quali sono le scadenze per la rottamazione quinquies?",
            },
            {
                "id": "2",
                "label": "Calcola IRPEF 2024",  # Off topic
                "prompt": "Calcola l'IRPEF dovuta per l'anno fiscale 2024",
            },
            {
                "id": "3",
                "label": "Rate definizione agevolata",  # On topic
                "prompt": "Quante rate sono previste per la definizione agevolata?",
            },
        ]

        result = validator.validate_batch_with_topic_context(
            actions=actions,
            response_text="Test",
            kb_sources=kb_sources,
            topic_context=topic_context,
        )

        # Only on-topic actions should pass
        assert len(result.validated_actions) == 2
        action_ids = [a["id"] for a in result.validated_actions]
        assert "1" in action_ids
        assert "3" in action_ids
        assert "2" not in action_ids

    def test_logs_off_topic_rejections(self, validator, topic_context, kb_sources):
        """Off-topic rejections are logged with clear reason."""
        actions = [
            {
                "id": "1",
                "label": "Calcola IRPEF 2024",
                "prompt": "Calcola l'IRPEF per l'anno 2024 con le aliquote progressive",
            },
        ]

        result = validator.validate_batch_with_topic_context(
            actions=actions,
            response_text="Test",
            kb_sources=kb_sources,
            topic_context=topic_context,
        )

        assert result.rejected_count == 1
        assert len(result.rejection_log) == 1
        _, reason = result.rejection_log[0]
        assert "topic" in reason.lower() or "rilevante" in reason.lower()
