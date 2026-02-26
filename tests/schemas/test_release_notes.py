"""Tests for release notes schemas.

TDD: Tests written FIRST before implementation.
Tests Pydantic validation for release notes request/response schemas.
"""

from datetime import UTC, datetime

import pytest

from app.schemas.release_notes import (
    MarkSeenResponse,
    ReleaseNotePublicResponse,
    ReleaseNoteResponse,
    ReleaseNotesListResponse,
    VersionResponse,
)


class TestVersionResponse:
    """Tests for VersionResponse schema."""

    def test_valid_version_response(self):
        """Should create a valid version response."""
        resp = VersionResponse(version="0.2.0", environment="development")
        assert resp.version == "0.2.0"
        assert resp.environment == "development"

    def test_all_environments(self):
        """Should accept all valid environment strings."""
        for env in ("development", "qa", "production"):
            resp = VersionResponse(version="1.0.0", environment=env)
            assert resp.environment == env


class TestReleaseNotePublicResponse:
    """Tests for ReleaseNotePublicResponse schema (no technical_notes)."""

    def test_valid_public_release_note(self):
        """Should create a valid public release note response."""
        resp = ReleaseNotePublicResponse(
            version="0.2.0",
            released_at=datetime(2026, 2, 26, 10, 0, 0, tzinfo=UTC),
            user_notes="Nuove funzionalità!",
        )
        assert resp.version == "0.2.0"
        assert resp.user_notes == "Nuove funzionalità!"
        assert not hasattr(resp, "technical_notes")

    def test_from_attributes_config(self):
        """Should support from_attributes for SQLModel conversion."""
        assert ReleaseNotePublicResponse.model_config.get("from_attributes") is True


class TestReleaseNoteResponse:
    """Tests for ReleaseNoteResponse schema (full, with technical_notes)."""

    def test_valid_release_note(self):
        """Should create a valid release note response."""
        resp = ReleaseNoteResponse(
            version="0.2.0",
            released_at=datetime(2026, 2, 26, 10, 0, 0, tzinfo=UTC),
            user_notes="Nuove funzionalità!",
            technical_notes="Added versioning.",
        )
        assert resp.version == "0.2.0"
        assert resp.user_notes == "Nuove funzionalità!"
        assert resp.technical_notes == "Added versioning."

    def test_released_at_optional(self):
        """Should allow released_at to be None."""
        resp = ReleaseNoteResponse(
            version="0.1.0",
            user_notes="Note",
            technical_notes="Tech note",
        )
        assert resp.released_at is None

    def test_from_attributes_config(self):
        """Should support from_attributes for SQLModel conversion."""
        assert ReleaseNoteResponse.model_config.get("from_attributes") is True


class TestReleaseNotesListResponse:
    """Tests for ReleaseNotesListResponse schema."""

    def test_empty_list(self):
        """Should handle empty items list."""
        resp = ReleaseNotesListResponse(items=[], total=0, page=1, page_size=10)
        assert resp.items == []
        assert resp.total == 0

    def test_with_items(self):
        """Should handle list with public items (no technical_notes)."""
        item = ReleaseNotePublicResponse(
            version="0.2.0",
            user_notes="Note",
        )
        resp = ReleaseNotesListResponse(items=[item], total=1, page=1, page_size=10)
        assert len(resp.items) == 1
        assert resp.items[0].version == "0.2.0"


class TestMarkSeenResponse:
    """Tests for MarkSeenResponse schema."""

    def test_success_response(self):
        """Should create a success response."""
        resp = MarkSeenResponse(success=True, message_it="Segnato come visto.")
        assert resp.success is True
        assert resp.message_it == "Segnato come visto."

    def test_failure_response(self):
        """Should create a failure response."""
        resp = MarkSeenResponse(success=False, message_it="Versione non trovata.")
        assert resp.success is False

    def test_default_message(self):
        """Should default message_it to empty string."""
        resp = MarkSeenResponse(success=True)
        assert resp.message_it == ""


class TestUpdateUserNotesRequest:
    """Tests for UpdateUserNotesRequest schema."""

    def test_valid_update_request(self):
        """Should create a valid update request with user_notes."""
        from app.schemas.release_notes import UpdateUserNotesRequest

        req = UpdateUserNotesRequest(user_notes="Nuove funzionalità disponibili!")
        assert req.user_notes == "Nuove funzionalità disponibili!"

    def test_empty_user_notes_rejected(self):
        """Should reject empty user_notes."""
        from pydantic import ValidationError

        from app.schemas.release_notes import UpdateUserNotesRequest

        with pytest.raises(ValidationError):
            UpdateUserNotesRequest(user_notes="")

    def test_whitespace_only_rejected(self):
        """Should reject whitespace-only user_notes."""
        from app.schemas.release_notes import UpdateUserNotesRequest

        with pytest.raises(ValueError):
            UpdateUserNotesRequest(user_notes="   ")


class TestReleaseNotesFullListResponse:
    """Tests for ReleaseNotesFullListResponse schema (with technical_notes)."""

    def test_empty_list(self):
        """Should handle empty items list."""
        from app.schemas.release_notes import ReleaseNotesFullListResponse

        resp = ReleaseNotesFullListResponse(items=[], total=0, page=1, page_size=10)
        assert resp.items == []
        assert resp.total == 0

    def test_with_full_items(self):
        """Should contain ReleaseNoteResponse items with technical_notes."""
        from app.schemas.release_notes import ReleaseNotesFullListResponse

        item = ReleaseNoteResponse(
            version="0.2.0",
            user_notes="Note utente",
            technical_notes="Technical details here.",
        )
        resp = ReleaseNotesFullListResponse(items=[item], total=1, page=1, page_size=10)
        assert len(resp.items) == 1
        assert resp.items[0].technical_notes == "Technical details here."
