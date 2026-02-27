"""Tests for Matching API endpoints (DEV-326).

TDD: Tests written FIRST before implementation.
Tests the matching suggestions management and trigger endpoints.

Endpoints tested:
- GET  /matching/suggestions                    (list suggestions)
- GET  /matching/suggestions?unread_only=true   (list unread only)
- POST /matching/trigger                        (trigger matching job)
- PUT  /matching/suggestions/{id}/read          (mark as read)
- PUT  /matching/suggestions/{id}/dismiss       (mark as dismissed)
- 404  on suggestion not found
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def studio_id() -> UUID:
    """Fixed studio UUID for tenant isolation."""
    return uuid4()


@pytest.fixture
def mock_db() -> AsyncMock:
    """Mock async database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def suggestion_id() -> UUID:
    """Fixed suggestion UUID."""
    return uuid4()


@pytest.fixture
def sample_suggestion(studio_id: UUID, suggestion_id: UUID) -> MagicMock:
    """Return a mock ProactiveSuggestion."""
    suggestion = MagicMock()
    suggestion.id = suggestion_id
    suggestion.studio_id = studio_id
    suggestion.knowledge_item_id = 42
    suggestion.matched_client_ids = [1, 2, 3]
    suggestion.match_score = 0.85
    suggestion.suggestion_text = "Nuova normativa rilevante per 3 clienti."
    suggestion.is_read = False
    suggestion.is_dismissed = False
    suggestion.created_at = datetime.now(UTC)
    return suggestion


@pytest.fixture
def sample_read_suggestion(studio_id: UUID, suggestion_id: UUID) -> MagicMock:
    """Return a mock ProactiveSuggestion marked as read."""
    suggestion = MagicMock()
    suggestion.id = suggestion_id
    suggestion.studio_id = studio_id
    suggestion.knowledge_item_id = 42
    suggestion.matched_client_ids = [1, 2, 3]
    suggestion.match_score = 0.85
    suggestion.suggestion_text = "Nuova normativa rilevante per 3 clienti."
    suggestion.is_read = True
    suggestion.is_dismissed = False
    suggestion.created_at = datetime.now(UTC)
    return suggestion


@pytest.fixture
def sample_dismissed_suggestion(studio_id: UUID, suggestion_id: UUID) -> MagicMock:
    """Return a mock ProactiveSuggestion marked as dismissed."""
    suggestion = MagicMock()
    suggestion.id = suggestion_id
    suggestion.studio_id = studio_id
    suggestion.knowledge_item_id = 42
    suggestion.matched_client_ids = [1, 2, 3]
    suggestion.match_score = 0.85
    suggestion.suggestion_text = "Nuova normativa rilevante per 3 clienti."
    suggestion.is_read = False
    suggestion.is_dismissed = True
    suggestion.created_at = datetime.now(UTC)
    return suggestion


# ---------------------------------------------------------------------------
# GET /matching/suggestions — List suggestions
# ---------------------------------------------------------------------------


class TestListSuggestions:
    """Tests for GET /matching/suggestions endpoint."""

    @pytest.mark.asyncio
    async def test_list_suggestions_success(
        self, mock_db: AsyncMock, studio_id: UUID, sample_suggestion: MagicMock
    ) -> None:
        """Happy path: returns list of suggestions for studio."""
        from app.api.v1.matching import list_suggestions

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_suggestion]

        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await list_suggestions(
            x_studio_id=studio_id,
            unread_only=False,
            offset=0,
            limit=50,
            db=mock_db,
        )

        assert len(result) == 1
        assert result[0].knowledge_item_id == 42
        assert result[0].match_score == 0.85

    @pytest.mark.asyncio
    async def test_list_suggestions_unread_only_filter(
        self, mock_db: AsyncMock, studio_id: UUID, sample_suggestion: MagicMock
    ) -> None:
        """Happy path: returns only unread suggestions when filter is applied."""
        from app.api.v1.matching import list_suggestions

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_suggestion]

        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await list_suggestions(
            x_studio_id=studio_id,
            unread_only=True,
            offset=0,
            limit=50,
            db=mock_db,
        )

        assert len(result) == 1
        # All returned suggestions should be unread
        assert result[0].is_read is False

    @pytest.mark.asyncio
    async def test_list_suggestions_empty(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Edge case: no suggestions returns empty list."""
        from app.api.v1.matching import list_suggestions

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await list_suggestions(
            x_studio_id=studio_id,
            unread_only=False,
            offset=0,
            limit=50,
            db=mock_db,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_list_suggestions_pagination(
        self, mock_db: AsyncMock, studio_id: UUID, sample_suggestion: MagicMock
    ) -> None:
        """Edge case: pagination with offset and limit."""
        from app.api.v1.matching import list_suggestions

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_suggestion]

        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await list_suggestions(
            x_studio_id=studio_id,
            unread_only=False,
            offset=10,
            limit=5,
            db=mock_db,
        )

        assert len(result) == 1
        mock_db.execute.assert_awaited_once()


# ---------------------------------------------------------------------------
# POST /matching/trigger — Trigger matching job
# ---------------------------------------------------------------------------


class TestTriggerMatching:
    """Tests for POST /matching/trigger endpoint."""

    @pytest.mark.asyncio
    async def test_trigger_matching_success(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Happy path: triggers matching job in background."""
        from app.api.v1.matching import trigger_matching
        from app.schemas.matching import TriggerMatchingRequest

        body = TriggerMatchingRequest(knowledge_item_id=42, trigger="manual")
        mock_background_tasks = MagicMock()

        result = await trigger_matching(
            body=body,
            x_studio_id=studio_id,
            background_tasks=mock_background_tasks,
            db=mock_db,
        )

        assert result.status == "accepted"
        assert result.studio_id == studio_id
        mock_background_tasks.add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_matching_without_knowledge_item(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Happy path: triggers full matching (no specific knowledge_item_id)."""
        from app.api.v1.matching import trigger_matching
        from app.schemas.matching import TriggerMatchingRequest

        body = TriggerMatchingRequest()
        mock_background_tasks = MagicMock()

        result = await trigger_matching(
            body=body,
            x_studio_id=studio_id,
            background_tasks=mock_background_tasks,
            db=mock_db,
        )

        assert result.status == "accepted"
        assert result.knowledge_item_id is None
        mock_background_tasks.add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_matching_custom_trigger_type(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Edge case: custom trigger type is forwarded correctly."""
        from app.api.v1.matching import trigger_matching
        from app.schemas.matching import TriggerMatchingRequest

        body = TriggerMatchingRequest(trigger="scheduled")
        mock_background_tasks = MagicMock()

        result = await trigger_matching(
            body=body,
            x_studio_id=studio_id,
            background_tasks=mock_background_tasks,
            db=mock_db,
        )

        assert result.status == "accepted"
        assert result.trigger == "scheduled"


# ---------------------------------------------------------------------------
# PUT /matching/suggestions/{id}/read — Mark as read
# ---------------------------------------------------------------------------


class TestMarkSuggestionRead:
    """Tests for PUT /matching/suggestions/{suggestion_id}/read endpoint."""

    @pytest.mark.asyncio
    async def test_mark_read_success(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        suggestion_id: UUID,
        sample_suggestion: MagicMock,
    ) -> None:
        """Happy path: marks suggestion as read."""
        from app.api.v1.matching import mark_suggestion_read

        # After marking as read
        sample_suggestion.is_read = True

        mock_db.get = AsyncMock(return_value=sample_suggestion)

        result = await mark_suggestion_read(
            suggestion_id=suggestion_id,
            x_studio_id=studio_id,
            db=mock_db,
        )

        assert result.is_read is True
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_mark_read_not_found_returns_404(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Error case: nonexistent suggestion raises 404."""
        from app.api.v1.matching import mark_suggestion_read

        fake_id = uuid4()
        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await mark_suggestion_read(
                suggestion_id=fake_id,
                x_studio_id=studio_id,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404
        assert "non trovat" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_mark_read_wrong_studio_returns_404(
        self, mock_db: AsyncMock, suggestion_id: UUID, sample_suggestion: MagicMock
    ) -> None:
        """Error case: suggestion belongs to different studio raises 404."""
        from app.api.v1.matching import mark_suggestion_read

        wrong_studio_id = uuid4()
        # sample_suggestion.studio_id is a different UUID
        mock_db.get = AsyncMock(return_value=sample_suggestion)

        with pytest.raises(HTTPException) as exc_info:
            await mark_suggestion_read(
                suggestion_id=suggestion_id,
                x_studio_id=wrong_studio_id,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404
        assert "non trovat" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# PUT /matching/suggestions/{id}/dismiss — Mark as dismissed
# ---------------------------------------------------------------------------


class TestMarkSuggestionDismissed:
    """Tests for PUT /matching/suggestions/{suggestion_id}/dismiss endpoint."""

    @pytest.mark.asyncio
    async def test_mark_dismissed_success(
        self,
        mock_db: AsyncMock,
        studio_id: UUID,
        suggestion_id: UUID,
        sample_suggestion: MagicMock,
    ) -> None:
        """Happy path: marks suggestion as dismissed."""
        from app.api.v1.matching import mark_suggestion_dismissed

        # After marking as dismissed
        sample_suggestion.is_dismissed = True

        mock_db.get = AsyncMock(return_value=sample_suggestion)

        result = await mark_suggestion_dismissed(
            suggestion_id=suggestion_id,
            x_studio_id=studio_id,
            db=mock_db,
        )

        assert result.is_dismissed is True
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_mark_dismissed_not_found_returns_404(self, mock_db: AsyncMock, studio_id: UUID) -> None:
        """Error case: nonexistent suggestion raises 404."""
        from app.api.v1.matching import mark_suggestion_dismissed

        fake_id = uuid4()
        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await mark_suggestion_dismissed(
                suggestion_id=fake_id,
                x_studio_id=studio_id,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404
        assert "non trovat" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_mark_dismissed_wrong_studio_returns_404(
        self, mock_db: AsyncMock, suggestion_id: UUID, sample_suggestion: MagicMock
    ) -> None:
        """Error case: suggestion belongs to different studio raises 404."""
        from app.api.v1.matching import mark_suggestion_dismissed

        wrong_studio_id = uuid4()
        mock_db.get = AsyncMock(return_value=sample_suggestion)

        with pytest.raises(HTTPException) as exc_info:
            await mark_suggestion_dismissed(
                suggestion_id=suggestion_id,
                x_studio_id=wrong_studio_id,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404
        assert "non trovat" in exc_info.value.detail.lower()
