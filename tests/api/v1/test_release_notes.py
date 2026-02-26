"""Tests for release notes API endpoints.

TDD: Tests written FIRST before implementation.
Tests all release notes endpoints with mocked services.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.release_notes import (
    ReleaseNotePublicResponse,
    ReleaseNoteResponse,
    ReleaseNotesListResponse,
    UpdateUserNotesRequest,
    VersionResponse,
)


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    user = MagicMock()
    user.id = 1
    user.email = "test@example.com"
    return user


@pytest.fixture
def sample_public_release_note():
    """Sample public release note response (no technical_notes)."""
    return ReleaseNotePublicResponse(
        version="0.2.0",
        released_at=datetime(2026, 2, 26, 10, 0, 0, tzinfo=UTC),
        user_notes="Nuove funzionalità disponibili!",
    )


@pytest.fixture
def sample_release_note():
    """Sample full release note response (with technical_notes)."""
    return ReleaseNoteResponse(
        version="0.2.0",
        released_at=datetime(2026, 2, 26, 10, 0, 0, tzinfo=UTC),
        user_notes="Nuove funzionalità disponibili!",
        technical_notes="Added versioning system with release notes API.",
    )


class TestGetVersion:
    """Tests for GET /release-notes/version."""

    @pytest.mark.asyncio
    async def test_returns_current_version(self):
        """Should return the current version and environment."""
        from app.api.v1.release_notes import get_version

        with (
            patch("app.api.v1.release_notes.app_get_version", return_value="0.2.0"),
            patch("app.api.v1.release_notes.get_environment", return_value="development"),
        ):
            result = await get_version()

        assert result.version == "0.2.0"
        assert result.environment == "development"

    @pytest.mark.asyncio
    async def test_returns_qa_environment(self):
        """Should correctly report QA environment."""
        from app.api.v1.release_notes import get_version

        with (
            patch("app.api.v1.release_notes.app_get_version", return_value="0.2.0"),
            patch("app.api.v1.release_notes.get_environment", return_value="qa"),
        ):
            result = await get_version()

        assert result.environment == "qa"


class TestGetReleaseNotes:
    """Tests for GET /release-notes."""

    @pytest.mark.asyncio
    async def test_returns_paginated_list(self, sample_public_release_note):
        """Should return paginated release notes list (public, no technical_notes)."""
        from app.api.v1.release_notes import get_release_notes

        mock_svc = AsyncMock()
        mock_svc.list_release_notes.return_value = ([sample_public_release_note], 1)

        with patch("app.api.v1.release_notes.release_notes_service", mock_svc):
            result = await get_release_notes(page=1, page_size=10)

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].version == "0.2.0"

    @pytest.mark.asyncio
    async def test_returns_empty_list(self):
        """Should return empty list when no release notes exist."""
        from app.api.v1.release_notes import get_release_notes

        mock_svc = AsyncMock()
        mock_svc.list_release_notes.return_value = ([], 0)

        with patch("app.api.v1.release_notes.release_notes_service", mock_svc):
            result = await get_release_notes(page=1, page_size=10)

        assert result.total == 0
        assert result.items == []


class TestGetLatestReleaseNote:
    """Tests for GET /release-notes/latest."""

    @pytest.mark.asyncio
    async def test_returns_latest(self, sample_public_release_note):
        """Should return the most recent release note (public, no technical_notes)."""
        from app.api.v1.release_notes import get_latest_release_note

        mock_svc = AsyncMock()
        mock_svc.get_latest.return_value = sample_public_release_note

        with patch("app.api.v1.release_notes.release_notes_service", mock_svc):
            result = await get_latest_release_note()

        assert result is not None
        assert result.version == "0.2.0"

    @pytest.mark.asyncio
    async def test_returns_none_when_empty(self):
        """Should return None when no release notes exist."""
        from app.api.v1.release_notes import get_latest_release_note

        mock_svc = AsyncMock()
        mock_svc.get_latest.return_value = None

        with patch("app.api.v1.release_notes.release_notes_service", mock_svc):
            result = await get_latest_release_note()

        assert result is None


class TestGetUnseenReleaseNote:
    """Tests for GET /release-notes/unseen."""

    @pytest.mark.asyncio
    async def test_returns_unseen_for_user(self, mock_user, sample_release_note):
        """Should return the latest unseen release note for authenticated user."""
        from app.api.v1.release_notes import get_unseen_release_note

        mock_svc = AsyncMock()
        mock_svc.get_unseen_for_user.return_value = sample_release_note

        with patch("app.api.v1.release_notes.release_notes_service", mock_svc):
            result = await get_unseen_release_note(current_user=mock_user)

        assert result is not None
        assert result.version == "0.2.0"
        mock_svc.get_unseen_for_user.assert_called_once_with(user_id=mock_user.id)

    @pytest.mark.asyncio
    async def test_returns_none_when_all_seen(self, mock_user):
        """Should return None when user has seen all release notes."""
        from app.api.v1.release_notes import get_unseen_release_note

        mock_svc = AsyncMock()
        mock_svc.get_unseen_for_user.return_value = None

        with patch("app.api.v1.release_notes.release_notes_service", mock_svc):
            result = await get_unseen_release_note(current_user=mock_user)

        assert result is None


class TestMarkReleaseNoteSeen:
    """Tests for POST /release-notes/{version}/seen."""

    @pytest.mark.asyncio
    async def test_marks_as_seen(self, mock_user):
        """Should mark a release note as seen for the user."""
        from app.api.v1.release_notes import mark_release_note_seen

        mock_svc = AsyncMock()
        mock_svc.mark_seen.return_value = True

        with patch("app.api.v1.release_notes.release_notes_service", mock_svc):
            result = await mark_release_note_seen(version="0.2.0", current_user=mock_user)

        assert result.success is True
        mock_svc.mark_seen.assert_called_once_with(user_id=mock_user.id, version="0.2.0")

    @pytest.mark.asyncio
    async def test_mark_nonexistent_version(self, mock_user):
        """Should handle marking a non-existent version gracefully."""
        from app.api.v1.release_notes import mark_release_note_seen

        mock_svc = AsyncMock()
        mock_svc.mark_seen.return_value = False

        with patch("app.api.v1.release_notes.release_notes_service", mock_svc):
            result = await mark_release_note_seen(version="99.99.99", current_user=mock_user)

        assert result.success is False

    @pytest.mark.asyncio
    async def test_idempotent_mark_seen(self, mock_user):
        """Should be idempotent - marking already-seen note should succeed."""
        from app.api.v1.release_notes import mark_release_note_seen

        mock_svc = AsyncMock()
        mock_svc.mark_seen.return_value = True

        with patch("app.api.v1.release_notes.release_notes_service", mock_svc):
            result = await mark_release_note_seen(version="0.2.0", current_user=mock_user)

        assert result.success is True


class TestUpdateUserNotes:
    """Tests for PATCH /release-notes/{version}/user-notes."""

    @pytest.mark.asyncio
    async def test_updates_user_notes(self, mock_user):
        """Should update user_notes for a given version."""
        from app.api.v1.release_notes import update_user_notes

        mock_svc = AsyncMock()
        mock_svc.update_user_notes.return_value = True

        body = UpdateUserNotesRequest(user_notes="Note aggiornate!")

        with patch("app.api.v1.release_notes.release_notes_service", mock_svc):
            result = await update_user_notes(body=body, version="0.2.0", current_user=mock_user)

        assert result.success is True
        mock_svc.update_user_notes.assert_called_once_with("0.2.0", "Note aggiornate!")

    @pytest.mark.asyncio
    async def test_returns_failure_for_nonexistent_version(self, mock_user):
        """Should return failure when version doesn't exist."""
        from app.api.v1.release_notes import update_user_notes

        mock_svc = AsyncMock()
        mock_svc.update_user_notes.return_value = False

        body = UpdateUserNotesRequest(user_notes="Note")

        with patch("app.api.v1.release_notes.release_notes_service", mock_svc):
            result = await update_user_notes(body=body, version="99.99.99", current_user=mock_user)

        assert result.success is False


class TestGetReleaseNotesFull:
    """Tests for GET /release-notes/full (authenticated, with technical_notes)."""

    @pytest.mark.asyncio
    async def test_returns_full_notes(self, mock_user, sample_release_note):
        """Should return full release notes including technical_notes."""
        from app.api.v1.release_notes import get_release_notes_full

        mock_svc = AsyncMock()
        mock_svc.list_release_notes_full.return_value = ([sample_release_note], 1)

        with patch("app.api.v1.release_notes.release_notes_service", mock_svc):
            result = await get_release_notes_full(page=1, page_size=10, current_user=mock_user)

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].technical_notes == "Added versioning system with release notes API."

    @pytest.mark.asyncio
    async def test_returns_empty_full_list(self, mock_user):
        """Should return empty list when no release notes exist."""
        from app.api.v1.release_notes import get_release_notes_full

        mock_svc = AsyncMock()
        mock_svc.list_release_notes_full.return_value = ([], 0)

        with patch("app.api.v1.release_notes.release_notes_service", mock_svc):
            result = await get_release_notes_full(page=1, page_size=10, current_user=mock_user)

        assert result.total == 0
        assert result.items == []
