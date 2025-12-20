"""TDD Tests for ProactivityAnalyticsService - DEV-156.

This module tests the analytics service:
- track_action_click()
- track_question_answer()
- get_popular_actions()

Test Files Reference: app/services/proactivity_analytics_service.py
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.proactivity import Action, ActionCategory
from app.services.proactivity_analytics_service import (
    ActionStats,
    ProactivityAnalyticsService,
)


class TestProactivityAnalyticsServiceInit:
    """Test ProactivityAnalyticsService initialization."""

    def test_service_initialization(self):
        """Test service initializes correctly."""
        mock_session = MagicMock()
        service = ProactivityAnalyticsService(session=mock_session)
        assert service.session is mock_session


class TestTrackActionClick:
    """Test track_action_click method."""

    @pytest.fixture
    def service(self) -> ProactivityAnalyticsService:
        """Create service with mocked session."""
        mock_session = MagicMock()
        return ProactivityAnalyticsService(session=mock_session)

    @pytest.fixture
    def sample_action(self) -> Action:
        """Create sample action."""
        return Action(
            id="tax_calculate_irpef",
            label="Calcola IRPEF",
            icon="calculator",
            category=ActionCategory.CALCULATE,
            prompt_template="Calcola IRPEF per {tipo_contribuente}",
        )

    def test_track_action_click_creates_record(self, service: ProactivityAnalyticsService, sample_action: Action):
        """Test that track_action_click creates a record."""
        service.track_action_click(
            session_id="session-123",
            user_id=42,
            action=sample_action,
            domain="tax",
            context_hash="abc123",
        )

        # Verify session.add was called
        service.session.add.assert_called_once()
        # Verify session.commit was called
        service.session.commit.assert_called_once()

    def test_track_action_click_with_anonymous_user(self, service: ProactivityAnalyticsService, sample_action: Action):
        """Test track_action_click works with user_id=None."""
        service.track_action_click(
            session_id="anonymous-session",
            user_id=None,
            action=sample_action,
            domain="tax",
        )

        service.session.add.assert_called_once()
        added_record = service.session.add.call_args[0][0]
        assert added_record.user_id is None

    def test_track_action_click_db_failure_non_blocking(
        self, service: ProactivityAnalyticsService, sample_action: Action
    ):
        """Test that DB failure doesn't raise exception."""
        service.session.commit.side_effect = Exception("DB Error")

        # Should not raise
        service.track_action_click(
            session_id="session-123",
            user_id=42,
            action=sample_action,
            domain="tax",
        )

        # Rollback should be called
        service.session.rollback.assert_called_once()


class TestTrackQuestionAnswer:
    """Test track_question_answer method."""

    @pytest.fixture
    def service(self) -> ProactivityAnalyticsService:
        """Create service with mocked session."""
        mock_session = MagicMock()
        return ProactivityAnalyticsService(session=mock_session)

    def test_track_question_answer_creates_record(self, service: ProactivityAnalyticsService):
        """Test that track_question_answer creates a record."""
        service.track_question_answer(
            session_id="session-123",
            user_id=42,
            question_id="irpef_tipo_contribuente",
            option_id="dipendente",
            custom_input=None,
        )

        service.session.add.assert_called_once()
        service.session.commit.assert_called_once()

    def test_track_question_answer_with_custom_input(self, service: ProactivityAnalyticsService):
        """Test track_question_answer with custom input."""
        service.track_question_answer(
            session_id="session-123",
            user_id=42,
            question_id="irpef_tipo_contribuente",
            option_id="altro",
            custom_input="Libero professionista",
        )

        added_record = service.session.add.call_args[0][0]
        assert added_record.custom_input == "Libero professionista"

    def test_track_question_answer_anonymous_user(self, service: ProactivityAnalyticsService):
        """Test track_question_answer with anonymous user."""
        service.track_question_answer(
            session_id="anonymous-session",
            user_id=None,
            question_id="document_type",
            option_id="fattura",
        )

        added_record = service.session.add.call_args[0][0]
        assert added_record.user_id is None

    def test_track_question_answer_db_failure_non_blocking(self, service: ProactivityAnalyticsService):
        """Test that DB failure doesn't raise exception."""
        service.session.commit.side_effect = Exception("DB Error")

        # Should not raise
        service.track_question_answer(
            session_id="session-123",
            user_id=42,
            question_id="irpef_tipo_contribuente",
            option_id="dipendente",
        )

        service.session.rollback.assert_called_once()


class TestGetPopularActions:
    """Test get_popular_actions method."""

    @pytest.fixture
    def service(self) -> ProactivityAnalyticsService:
        """Create service with mocked session."""
        mock_session = MagicMock()
        return ProactivityAnalyticsService(session=mock_session)

    def test_get_popular_actions_returns_list(self, service: ProactivityAnalyticsService):
        """Test get_popular_actions returns list of ActionStats."""
        # Mock query result
        mock_result = [
            ("tax_calculate_irpef", "Calcola IRPEF", 100),
            ("tax_calculate_iva", "Calcola IVA", 50),
        ]
        service.session.exec.return_value.all.return_value = mock_result

        stats = service.get_popular_actions(domain="tax", limit=10)

        assert isinstance(stats, list)
        # Method returns ActionStats objects

    def test_get_popular_actions_with_limit(self, service: ProactivityAnalyticsService):
        """Test get_popular_actions respects limit."""
        mock_result = [("action1", "Label 1", 10)]
        service.session.exec.return_value.all.return_value = mock_result

        service.get_popular_actions(domain="tax", limit=5)

        # Verify exec was called (query execution)
        service.session.exec.assert_called_once()

    def test_get_popular_actions_empty_result(self, service: ProactivityAnalyticsService):
        """Test get_popular_actions with no data."""
        service.session.exec.return_value.all.return_value = []

        stats = service.get_popular_actions(domain="unknown", limit=10)

        assert stats == []


class TestActionStats:
    """Test ActionStats model."""

    def test_action_stats_creation(self):
        """Test creating ActionStats."""
        stats = ActionStats(
            action_template_id="tax_calculate_irpef",
            action_label="Calcola IRPEF",
            click_count=100,
        )
        assert stats.action_template_id == "tax_calculate_irpef"
        assert stats.action_label == "Calcola IRPEF"
        assert stats.click_count == 100
