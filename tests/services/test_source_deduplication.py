"""Tests for KB source deduplication across conversation turns (DEV-245 Phase 4.2).

Tests that follow-up responses don't repeat sources already shown in prior turns.
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.chat_history_service import ChatHistoryService


@pytest.fixture
def chat_history_service():
    """Fixture for ChatHistoryService instance."""
    return ChatHistoryService()


@pytest.fixture
def sample_user_id():
    """Fixture for sample user ID."""
    return 12345


@pytest.fixture
def sample_session_id():
    """Fixture for sample session ID."""
    return str(uuid.uuid4())


class TestGetPriorKbSourceUrls:
    """Test suite for get_prior_kb_source_urls method (DEV-245 Phase 4.2)."""

    @pytest.mark.asyncio
    async def test_returns_empty_set_for_new_session(
        self,
        chat_history_service,
        sample_user_id,
        sample_session_id,
    ):
        """New session should have no prior sources."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        prior_urls = await chat_history_service.get_prior_kb_source_urls(
            user_id=sample_user_id,
            session_id=sample_session_id,
            db=mock_db,
        )

        assert prior_urls == set()

    @pytest.mark.asyncio
    async def test_returns_urls_from_single_prior_turn(
        self,
        chat_history_service,
        sample_user_id,
        sample_session_id,
    ):
        """Should return URLs from one prior response."""
        prior_kb_metadata = [
            {"title": "Legge 199/2025", "url": "https://example.com/legge-199"},
            {"title": "Circolare AdE", "url": "https://example.com/circolare-ade"},
        ]

        mock_rows = [(json.dumps(prior_kb_metadata),)]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        prior_urls = await chat_history_service.get_prior_kb_source_urls(
            user_id=sample_user_id,
            session_id=sample_session_id,
            db=mock_db,
        )

        assert prior_urls == {
            "https://example.com/legge-199",
            "https://example.com/circolare-ade",
        }

    @pytest.mark.asyncio
    async def test_returns_urls_from_multiple_prior_turns(
        self,
        chat_history_service,
        sample_user_id,
        sample_session_id,
    ):
        """Should aggregate URLs from all prior responses."""
        turn1_metadata = [{"title": "Source 1", "url": "https://example.com/1"}]
        turn2_metadata = [{"title": "Source 2", "url": "https://example.com/2"}]

        mock_rows = [
            (json.dumps(turn1_metadata),),
            (json.dumps(turn2_metadata),),
        ]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        prior_urls = await chat_history_service.get_prior_kb_source_urls(
            user_id=sample_user_id,
            session_id=sample_session_id,
            db=mock_db,
        )

        assert prior_urls == {
            "https://example.com/1",
            "https://example.com/2",
        }

    @pytest.mark.asyncio
    async def test_deduplicates_same_url_across_turns(
        self,
        chat_history_service,
        sample_user_id,
        sample_session_id,
    ):
        """Same URL in multiple turns should only appear once in result set."""
        turn1_metadata = [{"title": "Source 1", "url": "https://example.com/same"}]
        turn2_metadata = [{"title": "Source 1 Again", "url": "https://example.com/same"}]

        mock_rows = [
            (json.dumps(turn1_metadata),),
            (json.dumps(turn2_metadata),),
        ]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        prior_urls = await chat_history_service.get_prior_kb_source_urls(
            user_id=sample_user_id,
            session_id=sample_session_id,
            db=mock_db,
        )

        assert prior_urls == {"https://example.com/same"}

    @pytest.mark.asyncio
    async def test_handles_null_kb_sources_metadata(
        self,
        chat_history_service,
        sample_user_id,
        sample_session_id,
    ):
        """Should handle rows with NULL kb_sources_metadata gracefully."""
        turn1_metadata = [{"title": "Source 1", "url": "https://example.com/1"}]

        mock_rows = [
            (json.dumps(turn1_metadata),),
            (None,),  # NULL metadata
        ]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        prior_urls = await chat_history_service.get_prior_kb_source_urls(
            user_id=sample_user_id,
            session_id=sample_session_id,
            db=mock_db,
        )

        assert prior_urls == {"https://example.com/1"}

    @pytest.mark.asyncio
    async def test_handles_source_without_url(
        self,
        chat_history_service,
        sample_user_id,
        sample_session_id,
    ):
        """Should skip sources that don't have a URL."""
        prior_metadata = [
            {"title": "Source with URL", "url": "https://example.com/1"},
            {"title": "Source without URL"},  # No URL field
            {"title": "Source with null URL", "url": None},
        ]

        mock_rows = [(json.dumps(prior_metadata),)]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        prior_urls = await chat_history_service.get_prior_kb_source_urls(
            user_id=sample_user_id,
            session_id=sample_session_id,
            db=mock_db,
        )

        assert prior_urls == {"https://example.com/1"}

    @pytest.mark.asyncio
    async def test_handles_already_parsed_dict(
        self,
        chat_history_service,
        sample_user_id,
        sample_session_id,
    ):
        """Should handle kb_metadata that is already a parsed dict (not JSON string)."""
        # Some database drivers may return already-parsed JSONB
        prior_metadata = [
            {"title": "Source 1", "url": "https://example.com/1"},
        ]

        # Return as dict, not string
        mock_rows = [(prior_metadata,)]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        prior_urls = await chat_history_service.get_prior_kb_source_urls(
            user_id=sample_user_id,
            session_id=sample_session_id,
            db=mock_db,
        )

        assert prior_urls == {"https://example.com/1"}

    @pytest.mark.asyncio
    async def test_returns_empty_set_on_database_error(
        self,
        chat_history_service,
        sample_user_id,
        sample_session_id,
    ):
        """Should return empty set on database error (graceful degradation)."""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=Exception("Database error"))

        prior_urls = await chat_history_service.get_prior_kb_source_urls(
            user_id=sample_user_id,
            session_id=sample_session_id,
            db=mock_db,
        )

        # Should not raise, returns empty set
        assert prior_urls == set()

    @pytest.mark.asyncio
    async def test_handles_empty_kb_sources_list(
        self,
        chat_history_service,
        sample_user_id,
        sample_session_id,
    ):
        """Should handle empty kb_sources_metadata list gracefully."""
        mock_rows = [(json.dumps([]),)]  # Empty list
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        prior_urls = await chat_history_service.get_prior_kb_source_urls(
            user_id=sample_user_id,
            session_id=sample_session_id,
            db=mock_db,
        )

        assert prior_urls == set()
