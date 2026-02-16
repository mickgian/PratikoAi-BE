"""Tests for E2E test cost tracking in UsageTracker (DEV-257).

Verifies that non-numeric user_ids are mapped to the system test user,
events are labeled environment="test", and billing/quota updates are skipped.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.llm.base import LLMResponse
from app.services.usage_tracker import UsageTracker

SYSTEM_TEST_USER_ID = 50000


class TestConvertUserIdNonNumeric:
    """Test _convert_user_id handles non-numeric IDs by mapping to system test user."""

    @pytest.fixture
    def tracker(self):
        return UsageTracker()

    def test_convert_user_id_non_numeric_returns_system_test_id(self, tracker):
        """Non-numeric string like 'e2e_test_abc' maps to SYSTEM_TEST_USER_ID."""
        result = tracker._convert_user_id("e2e_test_abc")
        assert result == SYSTEM_TEST_USER_ID

    def test_convert_user_id_numeric_string_still_works(self, tracker):
        """Numeric string '123' still converts to int 123."""
        result = tracker._convert_user_id("123")
        assert result == 123

    def test_convert_user_id_int_still_works(self, tracker):
        """Integer 42 passes through unchanged."""
        result = tracker._convert_user_id(42)
        assert result == 42

    def test_convert_user_id_empty_string_returns_system_test_id(self, tracker):
        """Empty string maps to SYSTEM_TEST_USER_ID (not ValueError)."""
        result = tracker._convert_user_id("")
        assert result == SYSTEM_TEST_USER_ID


class TestTrackLlmUsageTestEnvironment:
    """Test that non-numeric user_ids produce environment='test' events."""

    @pytest.fixture
    def tracker(self):
        return UsageTracker()

    @pytest.fixture
    def mock_llm_response(self):
        return LLMResponse(
            content="Test response",
            model="gpt-4o",
            provider="openai",
            tokens_used={"input": 100, "output": 50},
            cost_estimate=0.01,
        )

    def _mock_db(self):
        """Create a mock database context manager."""
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        return mock_db

    @pytest.mark.asyncio
    async def test_track_llm_usage_non_numeric_user_sets_test_environment(self, tracker, mock_llm_response):
        """When user_id is non-numeric, UsageEvent.environment should be 'test'."""
        with (
            patch.object(tracker, "_update_user_quota", new_callable=AsyncMock),
            patch.object(tracker, "_update_daily_summary", new_callable=AsyncMock),
            patch.object(tracker, "_check_cost_alerts", new_callable=AsyncMock),
            patch("app.services.usage_tracker.database_service") as mock_db_service,
        ):
            mock_db_service.get_db.return_value = self._mock_db()

            result = await tracker.track_llm_usage(
                user_id="e2e_test_xyz",
                session_id="session-e2e",
                provider="openai",
                model="gpt-4o",
                llm_response=mock_llm_response,
                response_time_ms=500,
            )

            assert result.environment == "test"
            assert result.user_id == SYSTEM_TEST_USER_ID

    @pytest.mark.asyncio
    async def test_track_llm_usage_test_event_skips_quota_update(self, tracker, mock_llm_response):
        """Test events should NOT call _update_user_quota."""
        with (
            patch.object(tracker, "_update_user_quota", new_callable=AsyncMock) as mock_quota,
            patch.object(tracker, "_update_daily_summary", new_callable=AsyncMock) as mock_summary,
            patch.object(tracker, "_check_cost_alerts", new_callable=AsyncMock) as mock_alerts,
            patch("app.services.usage_tracker.database_service") as mock_db_service,
        ):
            mock_db_service.get_db.return_value = self._mock_db()

            await tracker.track_llm_usage(
                user_id="e2e_test_xyz",
                session_id="session-e2e",
                provider="openai",
                model="gpt-4o",
                llm_response=mock_llm_response,
                response_time_ms=500,
            )

            mock_quota.assert_not_called()
            mock_summary.assert_not_called()
            mock_alerts.assert_not_called()

    @pytest.mark.asyncio
    async def test_track_llm_usage_test_event_skips_rolling_window(self, tracker, mock_llm_response):
        """Test events should NOT write to rolling windows."""
        with (
            patch.object(tracker, "_update_user_quota", new_callable=AsyncMock),
            patch.object(tracker, "_update_daily_summary", new_callable=AsyncMock),
            patch.object(tracker, "_check_cost_alerts", new_callable=AsyncMock),
            patch("app.services.usage_tracker.database_service") as mock_db_service,
            patch("app.services.rolling_window_service.rolling_window_service") as mock_rw,
        ):
            mock_db_service.get_db.return_value = self._mock_db()
            mock_rw.record_usage = AsyncMock()

            await tracker.track_llm_usage(
                user_id="e2e_test_xyz",
                session_id="session-e2e",
                provider="openai",
                model="gpt-4o",
                llm_response=mock_llm_response,
                response_time_ms=500,
            )

            mock_rw.record_usage.assert_not_called()

    @pytest.mark.asyncio
    async def test_track_llm_usage_normal_user_still_updates_quota(self, tracker, mock_llm_response):
        """Normal numeric user_id should still call _update_user_quota."""
        with (
            patch.object(tracker, "_update_user_quota", new_callable=AsyncMock) as mock_quota,
            patch.object(tracker, "_update_daily_summary", new_callable=AsyncMock) as mock_summary,
            patch.object(tracker, "_check_cost_alerts", new_callable=AsyncMock) as mock_alerts,
            patch("app.services.usage_tracker.database_service") as mock_db_service,
        ):
            mock_db_service.get_db.return_value = self._mock_db()

            await tracker.track_llm_usage(
                user_id=123,
                session_id="session-1",
                provider="openai",
                model="gpt-4o",
                llm_response=mock_llm_response,
                response_time_ms=500,
            )

            mock_quota.assert_called_once()
            mock_summary.assert_called_once()
            mock_alerts.assert_called_once()


class TestTrackThirdPartyTestEnvironment:
    """Test that track_third_party_api handles non-numeric user_ids correctly."""

    @pytest.fixture
    def tracker(self):
        return UsageTracker()

    @pytest.mark.asyncio
    async def test_track_third_party_non_numeric_sets_test_environment(self, tracker):
        """Non-numeric user_id in track_third_party_api sets environment='test'."""
        with patch("app.services.usage_tracker.database_service") as mock_db_service:
            mock_db = AsyncMock()
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=None)
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            mock_db_service.get_db.return_value = mock_db

            result = await tracker.track_third_party_api(
                user_id="e2e_test_abc",
                session_id="session-e2e",
                api_type="brave_search",
                cost_eur=0.001,
                response_time_ms=200,
            )

            assert result.user_id == SYSTEM_TEST_USER_ID
            assert result.environment == "test"
            assert result.error_occurred is not True
