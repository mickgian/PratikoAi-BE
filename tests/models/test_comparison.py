"""Tests for comparison models (DEV-256)."""

import json
from datetime import datetime
from uuid import UUID

import pytest

from app.models.comparison import (
    ComparisonStatus,
    ModelComparisonResponse,
    ModelComparisonSession,
    ModelEloRating,
    UserModelPreference,
)


class TestModelComparisonSession:
    """Test ModelComparisonSession model."""

    def test_session_creation(self):
        """Test creating a ModelComparisonSession instance."""
        session = ModelComparisonSession(
            batch_id="batch-123",
            user_id=1,
            query_text="Test query",
            query_hash="abc123",
            models_compared='["openai:gpt-4o", "anthropic:claude-3-sonnet"]',
        )

        assert session.batch_id == "batch-123"
        assert session.user_id == 1
        assert session.query_text == "Test query"
        assert isinstance(session.id, UUID)
        assert hasattr(session, "created_at")

    def test_session_default_values(self):
        """Test session has correct default values."""
        session = ModelComparisonSession(
            batch_id="batch-123",
            user_id=1,
            query_text="Test query",
            query_hash="abc123",
            models_compared='["openai:gpt-4o"]',
        )

        assert session.winner_model is None
        assert session.vote_timestamp is None
        assert session.vote_comment is None

    def test_session_with_vote(self):
        """Test session with vote recorded."""
        vote_time = datetime.utcnow()
        session = ModelComparisonSession(
            batch_id="batch-123",
            user_id=1,
            query_text="Test query",
            query_hash="abc123",
            models_compared='["openai:gpt-4o", "anthropic:claude-3-sonnet"]',
            winner_model="openai:gpt-4o",
            vote_timestamp=vote_time,
            vote_comment="Clear and concise response",
        )

        assert session.winner_model == "openai:gpt-4o"
        assert session.vote_timestamp == vote_time
        assert session.vote_comment == "Clear and concise response"

    def test_session_models_compared_json(self):
        """Test models_compared stores JSON correctly."""
        models = ["openai:gpt-4o", "anthropic:claude-3-sonnet", "gemini:gemini-pro"]
        session = ModelComparisonSession(
            batch_id="batch-123",
            user_id=1,
            query_text="Test query",
            query_hash="abc123",
            models_compared=json.dumps(models),
        )

        parsed_models = json.loads(session.models_compared)
        assert parsed_models == models

    def test_session_has_responses_relationship(self):
        """Test session has responses relationship."""
        session = ModelComparisonSession(
            batch_id="batch-123",
            user_id=1,
            query_text="Test query",
            query_hash="abc123",
            models_compared="[]",
        )

        assert hasattr(session, "responses")
        assert isinstance(session.responses, list)


class TestModelComparisonResponse:
    """Test ModelComparisonResponse model."""

    def test_response_creation(self):
        """Test creating a ModelComparisonResponse instance."""
        response = ModelComparisonResponse(
            session_id=UUID("12345678-1234-1234-1234-123456789abc"),
            provider="openai",
            model_name="gpt-4o",
            response_text="This is the response",
            trace_id="trace-123",
            latency_ms=1500,
        )

        assert response.provider == "openai"
        assert response.model_name == "gpt-4o"
        assert response.response_text == "This is the response"
        assert response.latency_ms == 1500
        assert isinstance(response.id, UUID)

    def test_response_default_status(self):
        """Test response has success status by default."""
        response = ModelComparisonResponse(
            session_id=UUID("12345678-1234-1234-1234-123456789abc"),
            provider="openai",
            model_name="gpt-4o",
            response_text="Response",
            trace_id="trace-123",
        )

        assert response.status == ComparisonStatus.SUCCESS.value

    def test_response_with_error(self):
        """Test response with error status."""
        response = ModelComparisonResponse(
            session_id=UUID("12345678-1234-1234-1234-123456789abc"),
            provider="openai",
            model_name="gpt-4o",
            response_text="",
            trace_id="trace-123",
            status=ComparisonStatus.ERROR.value,
            error_message="Rate limit exceeded",
        )

        assert response.status == ComparisonStatus.ERROR.value
        assert response.error_message == "Rate limit exceeded"

    def test_response_with_timeout(self):
        """Test response with timeout status."""
        response = ModelComparisonResponse(
            session_id=UUID("12345678-1234-1234-1234-123456789abc"),
            provider="anthropic",
            model_name="claude-3-sonnet",
            response_text="",
            trace_id="trace-456",
            status=ComparisonStatus.TIMEOUT.value,
            error_message="Request timed out after 30s",
        )

        assert response.status == ComparisonStatus.TIMEOUT.value

    def test_response_with_usage_info(self):
        """Test response with token usage and cost."""
        response = ModelComparisonResponse(
            session_id=UUID("12345678-1234-1234-1234-123456789abc"),
            provider="openai",
            model_name="gpt-4o",
            response_text="Response",
            trace_id="trace-123",
            latency_ms=2000,
            cost_eur=0.005,
            input_tokens=100,
            output_tokens=200,
        )

        assert response.cost_eur == 0.005
        assert response.input_tokens == 100
        assert response.output_tokens == 200

    def test_response_nullable_fields(self):
        """Test response nullable fields default to None."""
        response = ModelComparisonResponse(
            session_id=UUID("12345678-1234-1234-1234-123456789abc"),
            provider="openai",
            model_name="gpt-4o",
            response_text="Response",
            trace_id="trace-123",
        )

        assert response.cost_eur is None
        assert response.input_tokens is None
        assert response.output_tokens is None
        assert response.error_message is None


class TestModelEloRating:
    """Test ModelEloRating model."""

    def test_elo_rating_creation(self):
        """Test creating a ModelEloRating instance."""
        rating = ModelEloRating(
            provider="openai",
            model_name="gpt-4o",
        )

        assert rating.provider == "openai"
        assert rating.model_name == "gpt-4o"
        assert rating.elo_rating == 1500.0  # Default

    def test_elo_rating_defaults(self):
        """Test Elo rating default values."""
        rating = ModelEloRating(
            provider="openai",
            model_name="gpt-4o",
        )

        assert rating.elo_rating == 1500.0
        assert rating.total_comparisons == 0
        assert rating.wins == 0
        assert hasattr(rating, "last_updated")

    def test_elo_rating_with_stats(self):
        """Test Elo rating with statistics."""
        rating = ModelEloRating(
            provider="openai",
            model_name="gpt-4o",
            elo_rating=1650.5,
            total_comparisons=100,
            wins=65,
        )

        assert rating.elo_rating == 1650.5
        assert rating.total_comparisons == 100
        assert rating.wins == 65

    def test_elo_rating_win_rate_calculation(self):
        """Test calculating win rate from rating stats."""
        rating = ModelEloRating(
            provider="openai",
            model_name="gpt-4o",
            total_comparisons=100,
            wins=60,
        )

        # Win rate calculation would be done in service layer
        expected_win_rate = rating.wins / rating.total_comparisons
        assert expected_win_rate == 0.6


class TestUserModelPreference:
    """Test UserModelPreference model."""

    def test_preference_creation(self):
        """Test creating a UserModelPreference instance."""
        pref = UserModelPreference(
            user_id=1,
            provider="openai",
            model_name="gpt-4o",
        )

        assert pref.user_id == 1
        assert pref.provider == "openai"
        assert pref.model_name == "gpt-4o"

    def test_preference_default_enabled(self):
        """Test preference is enabled by default."""
        pref = UserModelPreference(
            user_id=1,
            provider="openai",
            model_name="gpt-4o",
        )

        assert pref.is_enabled is True

    def test_preference_disabled(self):
        """Test creating disabled preference."""
        pref = UserModelPreference(
            user_id=1,
            provider="anthropic",
            model_name="claude-3-opus",
            is_enabled=False,
        )

        assert pref.is_enabled is False


class TestComparisonStatus:
    """Test ComparisonStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert ComparisonStatus.SUCCESS.value == "success"
        assert ComparisonStatus.ERROR.value == "error"
        assert ComparisonStatus.TIMEOUT.value == "timeout"

    def test_status_is_string_enum(self):
        """Test status enum inherits from str."""
        assert isinstance(ComparisonStatus.SUCCESS, str)
        assert ComparisonStatus.SUCCESS == "success"
