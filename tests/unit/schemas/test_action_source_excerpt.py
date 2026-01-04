"""TDD Tests for Action Schema Source Excerpt (DEV-236).

DEV-236: Add source_excerpt field to Action schema for paragraph-level grounding.

Tests written BEFORE implementation following TDD RED-GREEN-REFACTOR methodology.

Coverage Target: 95%+ for schema changes.
"""

import pytest
from pydantic import ValidationError

from app.schemas.proactivity import Action, ActionCategory


class TestActionSourceExcerptField:
    """Test source_excerpt field in Action schema."""

    def test_action_has_source_excerpt_field(self):
        """Action should accept source_excerpt field."""
        action = Action(
            id="action_001",
            label="Calcola aliquota IVA",
            icon="calculator",
            category=ActionCategory.CALCULATE,
            prompt_template="Calcola l'aliquota IVA per {importo}",
            source_excerpt="L'aliquota IVA ordinaria è del 22% per la maggior parte dei beni.",
        )

        assert hasattr(action, "source_excerpt")
        assert action.source_excerpt == "L'aliquota IVA ordinaria è del 22% per la maggior parte dei beni."

    def test_action_source_excerpt_optional(self):
        """source_excerpt should be optional (None by default)."""
        action = Action(
            id="action_002",
            label="Cerca normativa",
            icon="search",
            category=ActionCategory.SEARCH,
            prompt_template="Cerca normativa su {tema}",
        )

        assert action.source_excerpt is None

    def test_action_source_excerpt_can_be_empty_string(self):
        """source_excerpt can be an empty string."""
        action = Action(
            id="action_003",
            label="Verifica scadenza",
            icon="calendar",
            category=ActionCategory.VERIFY,
            prompt_template="Verifica scadenza {data}",
            source_excerpt="",
        )

        assert action.source_excerpt == ""

    def test_action_source_excerpt_is_string(self):
        """source_excerpt must be a string type."""
        action = Action(
            id="action_004",
            label="Esporta dati",
            icon="download",
            category=ActionCategory.EXPORT,
            prompt_template="Esporta {formato}",
            source_excerpt="Estratto dal documento normativo.",
        )

        assert isinstance(action.source_excerpt, str)

    def test_action_serialization_includes_source_excerpt(self):
        """Action.model_dump() should include source_excerpt when set."""
        action = Action(
            id="action_005",
            label="Spiega concetto",
            icon="info",
            category=ActionCategory.EXPLAIN,
            prompt_template="Spiega {concetto}",
            source_excerpt="Definizione tratta dall'Art. 1 del D.Lgs.",
        )

        data = action.model_dump()

        assert "source_excerpt" in data
        assert data["source_excerpt"] == "Definizione tratta dall'Art. 1 del D.Lgs."

    def test_action_serialization_includes_null_source_excerpt(self):
        """Action.model_dump() should include source_excerpt as None when not set."""
        action = Action(
            id="action_006",
            label="Calcola importo",
            icon="calculator",
            category=ActionCategory.CALCULATE,
            prompt_template="Calcola {formula}",
        )

        data = action.model_dump()

        assert "source_excerpt" in data
        assert data["source_excerpt"] is None


class TestActionSourceExcerptValidation:
    """Test validation of source_excerpt field."""

    def test_action_source_excerpt_accepts_long_text(self):
        """source_excerpt should accept text of any length (truncation happens upstream)."""
        long_excerpt = "A" * 250  # Long text

        action = Action(
            id="action_007",
            label="Test",
            icon="test",
            category=ActionCategory.EXPLAIN,
            prompt_template="Test {x}",
            source_excerpt=long_excerpt,
        )

        # Schema accepts the value; truncation happens in extract_paragraph_excerpt
        assert action.source_excerpt == long_excerpt

    def test_action_source_excerpt_preserves_whitespace(self):
        """source_excerpt should preserve content as-is."""
        action = Action(
            id="action_008",
            label="Test",
            icon="test",
            category=ActionCategory.CALCULATE,
            prompt_template="Test {x}",
            source_excerpt="  Testo con spazi   ",
        )

        # Schema preserves the value; stripping happens upstream
        assert action.source_excerpt == "  Testo con spazi   "


class TestActionSourceIdField:
    """Test source_id field in Action schema for linking to kb_sources_metadata."""

    def test_action_has_source_id_field(self):
        """Action should accept source_id field for linking to source."""
        action = Action(
            id="action_009",
            label="Calcola IVA",
            icon="calculator",
            category=ActionCategory.CALCULATE,
            prompt_template="Calcola IVA {importo}",
            source_id="doc_001_p0",
        )

        assert hasattr(action, "source_id")
        assert action.source_id == "doc_001_p0"

    def test_action_source_id_optional(self):
        """source_id should be optional (None by default)."""
        action = Action(
            id="action_010",
            label="Cerca info",
            icon="search",
            category=ActionCategory.SEARCH,
            prompt_template="Cerca {query}",
        )

        assert action.source_id is None

    def test_action_source_id_matches_paragraph_id_format(self):
        """source_id should follow paragraph_id format (doc_id + paragraph index)."""
        action = Action(
            id="action_011",
            label="Verifica",
            icon="check",
            category=ActionCategory.VERIFY,
            prompt_template="Verifica {item}",
            source_id="doc_circolare_2024_p2",
        )

        # source_id should be a string containing doc reference and paragraph
        assert isinstance(action.source_id, str)
        assert "_p" in action.source_id or action.source_id.startswith("doc_")


class TestActionWithFullSourceInfo:
    """Test Action with complete source grounding information."""

    def test_action_with_full_source_grounding(self):
        """Action can have both source_id and source_excerpt for full grounding."""
        action = Action(
            id="action_grounded",
            label="Applica aliquota ridotta",
            icon="percent",
            category=ActionCategory.CALCULATE,
            prompt_template="Calcola IVA ridotta al 10% per {servizio}",
            source_id="doc_001_p1",
            source_excerpt="Aliquote ridotte: 10% per prodotti alimentari, servizi turistici...",
        )

        assert action.source_id == "doc_001_p1"
        assert "10%" in action.source_excerpt

    def test_action_model_dump_includes_all_source_fields(self):
        """model_dump should include all source grounding fields."""
        action = Action(
            id="action_full",
            label="Calcola contributi",
            icon="euro",
            category=ActionCategory.CALCULATE,
            prompt_template="Calcola contributi INPS per {importo}",
            source_id="doc_inps_2024_p0",
            source_excerpt="I contributi INPS per artigiani e commercianti...",
        )

        data = action.model_dump()

        assert "source_id" in data
        assert "source_excerpt" in data
        assert data["source_id"] == "doc_inps_2024_p0"
        assert "INPS" in data["source_excerpt"]
