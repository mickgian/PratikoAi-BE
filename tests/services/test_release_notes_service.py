"""Tests for release notes service layer.

TDD: Tests written FIRST before implementation.
Tests business logic for release notes CRUD and seen tracking.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import ProgrammingError

from app.models.release_note import ReleaseNote, UserReleaseNoteSeen


@pytest.fixture
def service():
    """Create a ReleaseNotesService instance lazily to avoid DB import."""
    with patch("app.services.release_notes_service.AsyncSessionLocal"):
        from app.services.release_notes_service import ReleaseNotesService

        return ReleaseNotesService()


@pytest.fixture
def sample_db_release_note():
    """Sample ReleaseNote model instance."""
    return ReleaseNote(
        id=1,
        version="0.2.0",
        user_notes="Nuove funzionalità disponibili!",
        technical_notes="Added versioning system with release notes API.",
        released_at=datetime(2026, 2, 26, 10, 0, 0, tzinfo=UTC),
    )


class TestListReleaseNotes:
    """Tests for list_release_notes()."""

    @pytest.mark.asyncio
    async def test_returns_paginated_results(self, service, sample_db_release_note):
        """Should return release notes with pagination."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_db_release_note]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_result])

        with patch("app.services.release_notes_service.AsyncSessionLocal") as mock_session_cls:
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            items, total = await service.list_release_notes(page=1, page_size=10)

        assert total == 1
        assert len(items) == 1
        assert items[0].version == "0.2.0"

    @pytest.mark.asyncio
    async def test_empty_database(self, service):
        """Should return empty list when no release notes exist."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_result])

        with patch("app.services.release_notes_service.AsyncSessionLocal") as mock_session_cls:
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            items, total = await service.list_release_notes(page=1, page_size=10)

        assert total == 0
        assert items == []


class TestGetLatest:
    """Tests for get_latest()."""

    @pytest.mark.asyncio
    async def test_returns_most_recent(self, service, sample_db_release_note):
        """Should return the most recently released note."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_db_release_note

        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.release_notes_service.AsyncSessionLocal") as mock_session_cls:
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await service.get_latest()

        assert result is not None
        assert result.version == "0.2.0"

    @pytest.mark.asyncio
    async def test_returns_none_when_empty(self, service):
        """Should return None when no release notes exist."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.release_notes_service.AsyncSessionLocal") as mock_session_cls:
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await service.get_latest()

        assert result is None


class TestGetUnseenForUser:
    """Tests for get_unseen_for_user()."""

    @pytest.mark.asyncio
    async def test_returns_unseen_note(self, service, sample_db_release_note):
        """Should return latest release note that user hasn't seen."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_db_release_note

        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.release_notes_service.AsyncSessionLocal") as mock_session_cls:
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await service.get_unseen_for_user(user_id=1)

        assert result is not None
        assert result.version == "0.2.0"

    @pytest.mark.asyncio
    async def test_returns_none_when_all_seen(self, service):
        """Should return None when user has seen all notes."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.release_notes_service.AsyncSessionLocal") as mock_session_cls:
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await service.get_unseen_for_user(user_id=1)

        assert result is None


class TestMarkSeen:
    """Tests for mark_seen()."""

    @pytest.mark.asyncio
    async def test_marks_existing_version(self, service, sample_db_release_note):
        """Should mark a release note as seen and return True."""
        mock_db = AsyncMock()

        # First query: find release note by version
        mock_note_result = MagicMock()
        mock_note_result.scalar_one_or_none.return_value = sample_db_release_note

        # Second query: check if already seen
        mock_seen_result = MagicMock()
        mock_seen_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[mock_note_result, mock_seen_result])
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        with patch("app.services.release_notes_service.AsyncSessionLocal") as mock_session_cls:
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await service.mark_seen(user_id=1, version="0.2.0")

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_for_nonexistent_version(self, service):
        """Should return False when version doesn't exist."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.release_notes_service.AsyncSessionLocal") as mock_session_cls:
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await service.mark_seen(user_id=1, version="99.99.99")

        assert result is False

    @pytest.mark.asyncio
    async def test_idempotent_when_already_seen(self, service, sample_db_release_note):
        """Should return True without duplicating when already marked."""
        mock_db = AsyncMock()

        mock_note_result = MagicMock()
        mock_note_result.scalar_one_or_none.return_value = sample_db_release_note

        existing_seen = MagicMock()
        mock_seen_result = MagicMock()
        mock_seen_result.scalar_one_or_none.return_value = existing_seen

        mock_db.execute = AsyncMock(side_effect=[mock_note_result, mock_seen_result])

        with patch("app.services.release_notes_service.AsyncSessionLocal") as mock_session_cls:
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await service.mark_seen(user_id=1, version="0.2.0")

        assert result is True
        mock_db.add.assert_not_called()


class TestUpdateUserNotes:
    """Tests for update_user_notes()."""

    @pytest.mark.asyncio
    async def test_updates_existing_version(self, service, sample_db_release_note):
        """Should update user_notes and return True."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_db_release_note

        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        with patch("app.services.release_notes_service.AsyncSessionLocal") as mock_session_cls:
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await service.update_user_notes("0.2.0", "Note aggiornate!")

        assert result is True
        assert sample_db_release_note.user_notes == "Note aggiornate!"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_for_nonexistent_version(self, service):
        """Should return False when version doesn't exist."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.release_notes_service.AsyncSessionLocal") as mock_session_cls:
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await service.update_user_notes("99.99.99", "Non esiste")

        assert result is False

    @pytest.mark.asyncio
    async def test_strips_whitespace_from_notes(self, service, sample_db_release_note):
        """Should strip leading/trailing whitespace from user_notes."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_db_release_note

        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        with patch("app.services.release_notes_service.AsyncSessionLocal") as mock_session_cls:
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await service.update_user_notes("0.2.0", "  Note con spazi  ")

        assert result is True
        assert sample_db_release_note.user_notes == "Note con spazi"


class TestListReleaseNotesFull:
    """Tests for list_release_notes_full()."""

    @pytest.mark.asyncio
    async def test_returns_full_notes_with_technical(self, service, sample_db_release_note):
        """Should return release notes including technical_notes."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_db_release_note]

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_result])

        with patch("app.services.release_notes_service.AsyncSessionLocal") as mock_session_cls:
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            items, total = await service.list_release_notes_full(page=1, page_size=10)

        assert total == 1
        assert len(items) == 1
        assert items[0].version == "0.2.0"
        assert items[0].technical_notes == "Added versioning system with release notes API."

    @pytest.mark.asyncio
    async def test_empty_database(self, service):
        """Should return empty list when no release notes exist."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_result])

        with patch("app.services.release_notes_service.AsyncSessionLocal") as mock_session_cls:
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            items, total = await service.list_release_notes_full(page=1, page_size=10)

        assert total == 0
        assert items == []


class TestMissingTableGracefulDegradation:
    """Tests that service returns safe defaults when release_notes table is missing."""

    @pytest.fixture
    def _programming_error(self):
        """Create a ProgrammingError simulating a missing table."""
        return ProgrammingError(
            statement="SELECT ...",
            params={},
            orig=Exception('relation "release_notes" does not exist'),
        )

    @pytest.mark.asyncio
    async def test_list_release_notes_returns_empty_on_missing_table(self, service, _programming_error):
        """list_release_notes should return ([], 0) when table is missing."""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=_programming_error)

        with patch("app.services.release_notes_service.AsyncSessionLocal") as mock_session_cls:
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            items, total = await service.list_release_notes()

        assert items == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_latest_returns_none_on_missing_table(self, service, _programming_error):
        """get_latest should return None when table is missing."""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=_programming_error)

        with patch("app.services.release_notes_service.AsyncSessionLocal") as mock_session_cls:
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await service.get_latest()

        assert result is None

    @pytest.mark.asyncio
    async def test_get_unseen_returns_none_on_missing_table(self, service, _programming_error):
        """get_unseen_for_user should return None when table is missing."""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=_programming_error)

        with patch("app.services.release_notes_service.AsyncSessionLocal") as mock_session_cls:
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await service.get_unseen_for_user(user_id=1)

        assert result is None

    @pytest.mark.asyncio
    async def test_list_full_returns_empty_on_missing_table(self, service, _programming_error):
        """list_release_notes_full should return ([], 0) when table is missing."""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=_programming_error)

        with patch("app.services.release_notes_service.AsyncSessionLocal") as mock_session_cls:
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            items, total = await service.list_release_notes_full()

        assert items == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_mark_seen_returns_false_on_missing_table(self, service, _programming_error):
        """mark_seen should return False when table is missing."""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=_programming_error)

        with patch("app.services.release_notes_service.AsyncSessionLocal") as mock_session_cls:
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await service.mark_seen(user_id=1, version="0.2.0")

        assert result is False
