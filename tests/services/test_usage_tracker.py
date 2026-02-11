"""Tests for usage tracker service (DEV-257).

Tests user_id type conversion and usage tracking functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.llm.base import LLMResponse
from app.models.usage import CostCategory, UsageEvent, UsageType
from app.services.usage_tracker import UsageTracker, usage_tracker


class TestTrackLlmUsageUserIdConversion:
    """Test user_id type conversion in track_llm_usage (DEV-257)."""

    @pytest.fixture
    def tracker(self):
        """Create tracker instance."""
        return UsageTracker()

    @pytest.fixture
    def mock_llm_response(self):
        """Create mock LLM response."""
        return LLMResponse(
            content="Test response",
            model="gpt-4o",
            provider="openai",
            tokens_used={"input": 100, "output": 50},
            cost_estimate=0.01,
        )

    @pytest.mark.asyncio
    async def test_track_llm_usage_with_string_user_id(self, tracker, mock_llm_response):
        """Test that string user_id is converted to int."""
        with (
            patch.object(tracker, "_update_user_quota", new_callable=AsyncMock),
            patch.object(tracker, "_update_daily_summary", new_callable=AsyncMock),
            patch.object(tracker, "_check_cost_alerts", new_callable=AsyncMock),
            patch("app.services.usage_tracker.database_service") as mock_db_service,
        ):
            # Setup mock database
            mock_db = AsyncMock()
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=None)
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            mock_db_service.get_db.return_value = mock_db

            result = await tracker.track_llm_usage(
                user_id="123",  # String user_id
                session_id="session-1",
                provider="openai",
                model="gpt-4o",
                llm_response=mock_llm_response,
                response_time_ms=500,
            )

            # Verify UsageEvent was created with int user_id
            assert result.user_id == 123
            assert isinstance(result.user_id, int)

    @pytest.mark.asyncio
    async def test_track_llm_usage_with_int_user_id(self, tracker, mock_llm_response):
        """Test that int user_id works correctly."""
        with (
            patch.object(tracker, "_update_user_quota", new_callable=AsyncMock),
            patch.object(tracker, "_update_daily_summary", new_callable=AsyncMock),
            patch.object(tracker, "_check_cost_alerts", new_callable=AsyncMock),
            patch("app.services.usage_tracker.database_service") as mock_db_service,
        ):
            mock_db = AsyncMock()
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=None)
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            mock_db_service.get_db.return_value = mock_db

            result = await tracker.track_llm_usage(
                user_id=456,  # Int user_id
                session_id="session-1",
                provider="openai",
                model="gpt-4o",
                llm_response=mock_llm_response,
                response_time_ms=500,
            )

            assert result.user_id == 456
            assert isinstance(result.user_id, int)

    @pytest.mark.asyncio
    async def test_track_llm_usage_with_invalid_string_user_id(self, tracker, mock_llm_response):
        """Test that invalid string user_id raises ValueError."""
        with pytest.raises(ValueError, match="Invalid user_id"):
            await tracker.track_llm_usage(
                user_id="not-a-number",
                session_id="session-1",
                provider="openai",
                model="gpt-4o",
                llm_response=mock_llm_response,
                response_time_ms=500,
            )

    @pytest.mark.asyncio
    async def test_track_llm_usage_with_empty_string_user_id(self, tracker, mock_llm_response):
        """Test that empty string user_id raises ValueError."""
        with pytest.raises(ValueError, match="Invalid user_id"):
            await tracker.track_llm_usage(
                user_id="",
                session_id="session-1",
                provider="openai",
                model="gpt-4o",
                llm_response=mock_llm_response,
                response_time_ms=500,
            )


class TestTrackLlmUsageTokenExtraction:
    """Test token extraction from LLM response."""

    @pytest.fixture
    def tracker(self):
        """Create tracker instance."""
        return UsageTracker()

    @pytest.mark.asyncio
    async def test_track_llm_usage_extracts_tokens_from_dict(self, tracker):
        """Test token extraction when tokens_used is a dict."""
        llm_response = LLMResponse(
            content="Test",
            model="gpt-4o",
            provider="openai",
            tokens_used={"input": 100, "output": 50},
            cost_estimate=0.01,
        )

        with (
            patch.object(tracker, "_update_user_quota", new_callable=AsyncMock),
            patch.object(tracker, "_update_daily_summary", new_callable=AsyncMock),
            patch.object(tracker, "_check_cost_alerts", new_callable=AsyncMock),
            patch("app.services.usage_tracker.database_service") as mock_db_service,
        ):
            mock_db = AsyncMock()
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=None)
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            mock_db_service.get_db.return_value = mock_db

            result = await tracker.track_llm_usage(
                user_id=1,
                session_id="session-1",
                provider="openai",
                model="gpt-4o",
                llm_response=llm_response,
                response_time_ms=500,
            )

            assert result.input_tokens == 100
            assert result.output_tokens == 50
            assert result.total_tokens == 150

    @pytest.mark.asyncio
    async def test_track_llm_usage_cache_hit_zero_tokens(self, tracker):
        """Test that cache hits report zero tokens."""
        llm_response = LLMResponse(
            content="Cached response",
            model="gpt-4o",
            provider="openai",
            tokens_used={"input": 100, "output": 50},
            cost_estimate=0.01,
        )

        with (
            patch.object(tracker, "_update_user_quota", new_callable=AsyncMock),
            patch.object(tracker, "_update_daily_summary", new_callable=AsyncMock),
            patch.object(tracker, "_check_cost_alerts", new_callable=AsyncMock),
            patch("app.services.usage_tracker.database_service") as mock_db_service,
        ):
            mock_db = AsyncMock()
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=None)
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            mock_db_service.get_db.return_value = mock_db

            result = await tracker.track_llm_usage(
                user_id=1,
                session_id="session-1",
                provider="openai",
                model="gpt-4o",
                llm_response=llm_response,
                response_time_ms=10,
                cache_hit=True,
            )

            assert result.input_tokens == 0
            assert result.output_tokens == 0
            assert result.total_tokens == 0
            assert result.cost_eur == 0.0


class TestTrackLlmUsageErrorHandling:
    """Test error handling in track_llm_usage."""

    @pytest.fixture
    def tracker(self):
        """Create tracker instance."""
        return UsageTracker()

    @pytest.mark.asyncio
    async def test_track_llm_usage_database_error_returns_error_event(self, tracker):
        """Test that database errors return an error event."""
        llm_response = LLMResponse(
            content="Test",
            model="gpt-4o",
            provider="openai",
            tokens_used={"input": 100, "output": 50},
            cost_estimate=0.01,
        )

        with patch("app.services.usage_tracker.database_service") as mock_db_service:
            mock_db = AsyncMock()
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=None)
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock(side_effect=Exception("Database connection failed"))
            mock_db_service.get_db.return_value = mock_db

            result = await tracker.track_llm_usage(
                user_id=1,
                session_id="session-1",
                provider="openai",
                model="gpt-4o",
                llm_response=llm_response,
                response_time_ms=500,
            )

            assert result.error_occurred is True
            assert "Database connection failed" in result.error_type


class TestTrackThirdPartyApiUserIdConversion:
    """Test user_id type conversion in track_third_party_api (DEV-257)."""

    @pytest.fixture
    def tracker(self):
        """Create tracker instance."""
        return UsageTracker()

    @pytest.mark.asyncio
    async def test_track_third_party_api_with_string_user_id(self, tracker):
        """Test that string user_id is converted to int."""
        with patch("app.services.usage_tracker.database_service") as mock_db_service:
            mock_db = AsyncMock()
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=None)
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            mock_db_service.get_db.return_value = mock_db

            result = await tracker.track_third_party_api(
                user_id="789",  # String user_id
                session_id="session-1",
                api_type="brave_search",
                cost_eur=0.001,
                response_time_ms=200,
            )

            assert result.user_id == 789
            assert isinstance(result.user_id, int)

    @pytest.mark.asyncio
    async def test_track_third_party_api_with_invalid_user_id(self, tracker):
        """Test that invalid user_id raises ValueError."""
        with pytest.raises(ValueError, match="Invalid user_id"):
            await tracker.track_third_party_api(
                user_id="invalid",
                session_id="session-1",
                api_type="brave_search",
                cost_eur=0.001,
                response_time_ms=200,
            )


class TestTrackApiRequestUserIdConversion:
    """Test user_id type conversion in track_api_request (DEV-257)."""

    @pytest.fixture
    def tracker(self):
        """Create tracker instance."""
        return UsageTracker()

    @pytest.mark.asyncio
    async def test_track_api_request_with_string_user_id(self, tracker):
        """Test that string user_id is converted to int."""
        with patch("app.services.usage_tracker.database_service") as mock_db_service:
            mock_db = AsyncMock()
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=None)
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db_service.get_db.return_value = mock_db

            result = await tracker.track_api_request(
                user_id="999",  # String user_id
                session_id="session-1",
                endpoint="/api/chat",
                method="POST",
                response_time_ms=100,
                request_size=1024,
                response_size=2048,
            )

            assert result.user_id == 999
            assert isinstance(result.user_id, int)


class TestGlobalUsageTracker:
    """Test global usage_tracker instance."""

    def test_global_usage_tracker_exists(self):
        """Test that global usage_tracker is available."""
        assert usage_tracker is not None
        assert isinstance(usage_tracker, UsageTracker)
