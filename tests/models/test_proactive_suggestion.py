"""DEV-324: Tests for ProactiveSuggestion SQLModel."""

import sys
from datetime import datetime
from types import ModuleType
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

if "app.services.database" not in sys.modules:
    _db_stub = ModuleType("app.services.database")
    _db_stub.database_service = MagicMock()  # type: ignore[attr-defined]
    sys.modules["app.services.database"] = _db_stub

from app.models.proactive_suggestion import ProactiveSuggestion


class TestProactiveSuggestionCreation:
    """Test ProactiveSuggestion model creation."""

    def test_suggestion_creation_valid(self) -> None:
        """Valid suggestion with required fields."""
        studio_id = uuid4()
        suggestion = ProactiveSuggestion(
            studio_id=studio_id,
            knowledge_item_id=10,
            matched_client_ids=[1, 2, 3],
            match_score=0.87,
            suggestion_text="Nuova normativa IVA riguarda questi clienti",
        )

        assert suggestion.studio_id == studio_id
        assert suggestion.knowledge_item_id == 10
        assert suggestion.match_score == 0.87
        assert suggestion.id is not None  # uuid4 auto-generated

    def test_suggestion_fk_constraints(self) -> None:
        """Required FKs: studio_id, knowledge_item_id."""
        studio_id = uuid4()
        suggestion = ProactiveSuggestion(
            studio_id=studio_id,
            knowledge_item_id=5,
            matched_client_ids=[1],
            match_score=0.5,
            suggestion_text="Test",
        )
        assert suggestion.studio_id == studio_id
        assert suggestion.knowledge_item_id == 5


class TestProactiveSuggestionJSONB:
    """Test JSONB client IDs field."""

    def test_matched_client_ids_single(self) -> None:
        """Single client ID in array."""
        suggestion = ProactiveSuggestion(
            studio_id=uuid4(),
            knowledge_item_id=1,
            matched_client_ids=[42],
            match_score=0.9,
            suggestion_text="Test",
        )
        assert suggestion.matched_client_ids == [42]

    def test_matched_client_ids_multiple(self) -> None:
        """Multiple client IDs in array."""
        suggestion = ProactiveSuggestion(
            studio_id=uuid4(),
            knowledge_item_id=1,
            matched_client_ids=[1, 2, 3, 4, 5],
            match_score=0.75,
            suggestion_text="Test",
        )
        assert len(suggestion.matched_client_ids) == 5

    def test_matched_client_ids_empty(self) -> None:
        """Empty client IDs array."""
        suggestion = ProactiveSuggestion(
            studio_id=uuid4(),
            knowledge_item_id=1,
            matched_client_ids=[],
            match_score=0.5,
            suggestion_text="Test",
        )
        assert suggestion.matched_client_ids == []


class TestProactiveSuggestionStatus:
    """Test read/dismissed status fields."""

    def test_is_read_default_false(self) -> None:
        """is_read defaults to False."""
        suggestion = ProactiveSuggestion(
            studio_id=uuid4(),
            knowledge_item_id=1,
            matched_client_ids=[1],
            match_score=0.5,
            suggestion_text="Test",
        )
        assert suggestion.is_read is False

    def test_is_dismissed_default_false(self) -> None:
        """is_dismissed defaults to False."""
        suggestion = ProactiveSuggestion(
            studio_id=uuid4(),
            knowledge_item_id=1,
            matched_client_ids=[1],
            match_score=0.5,
            suggestion_text="Test",
        )
        assert suggestion.is_dismissed is False

    def test_is_read_toggle(self) -> None:
        """is_read can be toggled to True."""
        suggestion = ProactiveSuggestion(
            studio_id=uuid4(),
            knowledge_item_id=1,
            matched_client_ids=[1],
            match_score=0.5,
            suggestion_text="Test",
        )
        suggestion.is_read = True
        assert suggestion.is_read is True

    def test_is_dismissed_toggle(self) -> None:
        """is_dismissed can be toggled to True."""
        suggestion = ProactiveSuggestion(
            studio_id=uuid4(),
            knowledge_item_id=1,
            matched_client_ids=[1],
            match_score=0.5,
            suggestion_text="Test",
        )
        suggestion.is_dismissed = True
        assert suggestion.is_dismissed is True


class TestProactiveSuggestionMatchScore:
    """Test match score boundaries."""

    def test_match_score_high(self) -> None:
        """High match score (close to 1.0)."""
        suggestion = ProactiveSuggestion(
            studio_id=uuid4(),
            knowledge_item_id=1,
            matched_client_ids=[1],
            match_score=0.99,
            suggestion_text="Test",
        )
        assert suggestion.match_score == 0.99

    def test_match_score_low(self) -> None:
        """Low match score (close to 0.0)."""
        suggestion = ProactiveSuggestion(
            studio_id=uuid4(),
            knowledge_item_id=1,
            matched_client_ids=[1],
            match_score=0.01,
            suggestion_text="Test",
        )
        assert suggestion.match_score == 0.01

    def test_match_score_zero(self) -> None:
        """Match score can be zero."""
        suggestion = ProactiveSuggestion(
            studio_id=uuid4(),
            knowledge_item_id=1,
            matched_client_ids=[1],
            match_score=0.0,
            suggestion_text="Test",
        )
        assert suggestion.match_score == 0.0


class TestProactiveSuggestionRepr:
    """Test __repr__ output."""

    def test_repr(self) -> None:
        """__repr__ includes knowledge_item_id and match_score."""
        suggestion = ProactiveSuggestion(
            studio_id=uuid4(),
            knowledge_item_id=42,
            matched_client_ids=[1, 2],
            match_score=0.85,
            suggestion_text="Test normativa",
        )
        r = repr(suggestion)
        assert "42" in r
        assert "0.85" in r
