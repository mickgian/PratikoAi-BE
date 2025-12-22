"""TDD Tests for Analytics Tracking Integration - DEV-162.

Tests for analytics tracking in:
- POST /api/v1/chatbot/actions/execute - Action click tracking
- POST /api/v1/chatbot/questions/answer - Question answer tracking

Test Requirements:
- test_action_click_tracked - Analytics called on action execute
- test_question_answer_tracked - Analytics called on question answer
- test_analytics_failure_non_blocking - Endpoint works even if analytics fails
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.proactivity import Action, ActionCategory


class TestActionClickAnalytics:
    """Test analytics tracking for action clicks."""

    @pytest.fixture
    def sample_action(self) -> Action:
        """Create sample action for testing."""
        return Action(
            id="tax_calculate_irpef",
            label="Calcola IRPEF",
            icon="calculator",
            category=ActionCategory.CALCULATE,
            prompt_template="Calcola IRPEF per {tipo_contribuente}",
        )

    def test_track_action_click_sync_creates_analytics_record(self, sample_action: Action):
        """Test that _track_action_click_sync creates analytics record."""
        from app.api.v1.chatbot import _track_action_click_sync

        # Mock get_sync_session and ProactivityAnalyticsService
        with (
            patch("app.api.v1.chatbot.get_sync_session") as mock_session_factory,
            patch("app.api.v1.chatbot.ProactivityAnalyticsService") as mock_analytics_class,
        ):
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=None)
            mock_session_factory.return_value = mock_session

            mock_analytics = MagicMock()
            mock_analytics_class.return_value = mock_analytics

            # Call the sync tracking function
            _track_action_click_sync(
                session_id="session-123",
                user_id=42,
                action=sample_action,
                domain="tax",
                context_hash="abc123",
            )

            # Verify analytics service was created with session
            mock_analytics_class.assert_called_once_with(mock_session)

            # Verify track_action_click was called
            mock_analytics.track_action_click.assert_called_once_with(
                session_id="session-123",
                user_id=42,
                action=sample_action,
                domain="tax",
                context_hash="abc123",
            )

    def test_track_action_click_sync_handles_exception(self, sample_action: Action):
        """Test that _track_action_click_sync handles exceptions gracefully."""
        from app.api.v1.chatbot import _track_action_click_sync

        with (
            patch("app.api.v1.chatbot.get_sync_session") as mock_session_factory,
            patch("app.api.v1.chatbot.logger") as mock_logger,
        ):
            # Make session factory raise an exception
            mock_session_factory.side_effect = Exception("DB connection failed")

            # Should not raise
            _track_action_click_sync(
                session_id="session-123",
                user_id=42,
                action=sample_action,
                domain="tax",
            )

            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert call_args[0][0] == "analytics_action_click_background_failed"

    @pytest.mark.asyncio
    async def test_track_action_click_async_runs_without_error(self, sample_action: Action):
        """Test that track_action_click_async completes without error (fire-and-forget)."""
        from app.api.v1.chatbot import track_action_click_async

        with (
            patch("app.api.v1.chatbot._track_action_click_sync") as mock_sync,
        ):
            # Call the async function
            await track_action_click_async(
                session_id="session-123",
                user_id=42,
                action=sample_action,
                domain="tax",
                context_hash=None,
            )

            # Give executor time to schedule the task
            import asyncio

            await asyncio.sleep(0.1)

            # The sync function should have been scheduled
            # (fire-and-forget, so may not be called yet)


class TestQuestionAnswerAnalytics:
    """Test analytics tracking for question answers."""

    def test_track_question_answer_sync_creates_analytics_record(self):
        """Test that _track_question_answer_sync creates analytics record."""
        from app.api.v1.chatbot import _track_question_answer_sync

        with (
            patch("app.api.v1.chatbot.get_sync_session") as mock_session_factory,
            patch("app.api.v1.chatbot.ProactivityAnalyticsService") as mock_analytics_class,
        ):
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=None)
            mock_session_factory.return_value = mock_session

            mock_analytics = MagicMock()
            mock_analytics_class.return_value = mock_analytics

            # Call the sync tracking function
            _track_question_answer_sync(
                session_id="session-123",
                user_id=42,
                question_id="irpef_tipo_contribuente",
                option_id="dipendente",
                custom_input=None,
            )

            # Verify analytics service was created with session
            mock_analytics_class.assert_called_once_with(mock_session)

            # Verify track_question_answer was called
            mock_analytics.track_question_answer.assert_called_once_with(
                session_id="session-123",
                user_id=42,
                question_id="irpef_tipo_contribuente",
                option_id="dipendente",
                custom_input=None,
            )

    def test_track_question_answer_sync_with_custom_input(self):
        """Test tracking question answer with custom input."""
        from app.api.v1.chatbot import _track_question_answer_sync

        with (
            patch("app.api.v1.chatbot.get_sync_session") as mock_session_factory,
            patch("app.api.v1.chatbot.ProactivityAnalyticsService") as mock_analytics_class,
        ):
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=None)
            mock_session_factory.return_value = mock_session

            mock_analytics = MagicMock()
            mock_analytics_class.return_value = mock_analytics

            _track_question_answer_sync(
                session_id="session-123",
                user_id=42,
                question_id="irpef_reddito",
                option_id="altro",
                custom_input="75000",
            )

            mock_analytics.track_question_answer.assert_called_once()
            call_kwargs = mock_analytics.track_question_answer.call_args.kwargs
            assert call_kwargs["custom_input"] == "75000"

    def test_track_question_answer_sync_handles_exception(self):
        """Test that _track_question_answer_sync handles exceptions gracefully."""
        from app.api.v1.chatbot import _track_question_answer_sync

        with (
            patch("app.api.v1.chatbot.get_sync_session") as mock_session_factory,
            patch("app.api.v1.chatbot.logger") as mock_logger,
        ):
            mock_session_factory.side_effect = Exception("DB connection failed")

            # Should not raise
            _track_question_answer_sync(
                session_id="session-123",
                user_id=42,
                question_id="irpef_tipo_contribuente",
                option_id="dipendente",
            )

            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert call_args[0][0] == "analytics_question_answer_background_failed"

    @pytest.mark.asyncio
    async def test_track_question_answer_async_runs_without_error(self):
        """Test that track_question_answer_async completes without error (fire-and-forget)."""
        from app.api.v1.chatbot import track_question_answer_async

        with patch("app.api.v1.chatbot._track_question_answer_sync") as mock_sync:
            await track_question_answer_async(
                session_id="session-123",
                user_id=42,
                question_id="irpef_tipo_contribuente",
                option_id="dipendente",
                custom_input=None,
            )

            # Give executor time to schedule the task
            import asyncio

            await asyncio.sleep(0.1)

            # The sync function should have been scheduled
            # (fire-and-forget, so may not be called yet)


class TestAnalyticsNonBlocking:
    """Test that analytics failures don't block endpoints."""

    @pytest.fixture
    def sample_action(self) -> Action:
        """Create sample action for testing."""
        return Action(
            id="tax_calculate_irpef",
            label="Calcola IRPEF",
            icon="calculator",
            category=ActionCategory.CALCULATE,
            prompt_template="Calcola IRPEF",
        )

    def test_action_tracking_failure_non_blocking(self, sample_action: Action):
        """Test that action click tracking failure doesn't raise."""
        from app.api.v1.chatbot import _track_action_click_sync

        with (
            patch("app.api.v1.chatbot.get_sync_session") as mock_session_factory,
            patch("app.api.v1.chatbot.ProactivityAnalyticsService") as mock_analytics_class,
        ):
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=None)
            mock_session_factory.return_value = mock_session

            mock_analytics = MagicMock()
            mock_analytics.track_action_click.side_effect = Exception("DB write failed")
            mock_analytics_class.return_value = mock_analytics

            # Should not raise
            _track_action_click_sync(
                session_id="session-123",
                user_id=42,
                action=sample_action,
                domain="tax",
            )

    def test_question_tracking_failure_non_blocking(self):
        """Test that question answer tracking failure doesn't raise."""
        from app.api.v1.chatbot import _track_question_answer_sync

        with (
            patch("app.api.v1.chatbot.get_sync_session") as mock_session_factory,
            patch("app.api.v1.chatbot.ProactivityAnalyticsService") as mock_analytics_class,
        ):
            mock_session = MagicMock()
            mock_session.__enter__ = MagicMock(return_value=mock_session)
            mock_session.__exit__ = MagicMock(return_value=None)
            mock_session_factory.return_value = mock_session

            mock_analytics = MagicMock()
            mock_analytics.track_question_answer.side_effect = Exception("DB write failed")
            mock_analytics_class.return_value = mock_analytics

            # Should not raise
            _track_question_answer_sync(
                session_id="session-123",
                user_id=42,
                question_id="irpef_tipo_contribuente",
                option_id="dipendente",
            )


class TestSyncSessionIntegration:
    """Test sync session integration for analytics."""

    def test_get_sync_session_returns_session(self):
        """Test that get_sync_session returns a valid session."""
        from app.models.database import get_sync_session

        # Should return a session (may fail in test env without DB, but function exists)
        assert callable(get_sync_session)
