"""Tests for comparison schemas (DEV-256)."""

from datetime import datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas.comparison import (
    AvailableModel,
    AvailableModelsResponse,
    ComparisonRequest,
    ComparisonResponse,
    ComparisonStats,
    ComparisonStatsResponse,
    LeaderboardResponse,
    ModelPreferencesRequest,
    ModelRanking,
    ModelResponseInfo,
    VoteRequest,
    VoteResponse,
)


class TestComparisonRequest:
    """Test ComparisonRequest schema."""

    def test_valid_request(self):
        """Test creating a valid comparison request."""
        request = ComparisonRequest(
            query="What is the VAT rate in Italy?",
            model_ids=["openai:gpt-4o", "anthropic:claude-3-sonnet"],
        )

        assert request.query == "What is the VAT rate in Italy?"
        assert len(request.model_ids) == 2

    def test_request_without_model_ids(self):
        """Test request without explicit model_ids uses user preferences."""
        request = ComparisonRequest(query="Test query")

        assert request.model_ids is None

    def test_request_query_too_long(self):
        """Test query exceeding max length raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ComparisonRequest(query="a" * 2001)

        assert "String should have at most 2000 characters" in str(exc_info.value)

    def test_request_query_empty(self):
        """Test empty query raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ComparisonRequest(query="")

        assert "String should have at least 1 character" in str(exc_info.value)

    def test_request_too_few_models(self):
        """Test request with less than 2 models raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ComparisonRequest(
                query="Test query",
                model_ids=["openai:gpt-4o"],
            )

        assert "List should have at least 2 items" in str(exc_info.value)

    def test_request_too_many_models(self):
        """Test request with more than 6 models raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ComparisonRequest(
                query="Test query",
                model_ids=[
                    "openai:gpt-4o",
                    "openai:gpt-4-turbo",
                    "anthropic:claude-3-sonnet",
                    "anthropic:claude-3-opus",
                    "gemini:gemini-pro",
                    "mistral:mistral-large",
                    "gemini:gemini-flash",
                ],
            )

        assert "List should have at most 6 items" in str(exc_info.value)


class TestVoteRequest:
    """Test VoteRequest schema."""

    def test_valid_vote(self):
        """Test creating a valid vote request."""
        request = VoteRequest(
            batch_id="batch-123",
            winner_model_id="openai:gpt-4o",
        )

        assert request.batch_id == "batch-123"
        assert request.winner_model_id == "openai:gpt-4o"
        assert request.comment is None

    def test_vote_with_comment(self):
        """Test vote request with optional comment."""
        request = VoteRequest(
            batch_id="batch-123",
            winner_model_id="openai:gpt-4o",
            comment="This response was more accurate",
        )

        assert request.comment == "This response was more accurate"

    def test_vote_comment_too_long(self):
        """Test comment exceeding max length raises error."""
        with pytest.raises(ValidationError) as exc_info:
            VoteRequest(
                batch_id="batch-123",
                winner_model_id="openai:gpt-4o",
                comment="a" * 1001,
            )

        assert "String should have at most 1000 characters" in str(exc_info.value)


class TestModelPreferencesRequest:
    """Test ModelPreferencesRequest schema."""

    def test_valid_preferences(self):
        """Test creating valid preferences request."""
        request = ModelPreferencesRequest(
            enabled_model_ids=["openai:gpt-4o", "anthropic:claude-3-sonnet"],
        )

        assert len(request.enabled_model_ids) == 2

    def test_preferences_too_few_models(self):
        """Test preferences with less than 2 models raises error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPreferencesRequest(enabled_model_ids=["openai:gpt-4o"])

        assert "List should have at least 2 items" in str(exc_info.value)


class TestModelResponseInfo:
    """Test ModelResponseInfo schema."""

    def test_successful_response(self):
        """Test successful model response info."""
        response = ModelResponseInfo(
            model_id="openai:gpt-4o",
            provider="openai",
            model_name="gpt-4o",
            response_text="This is the response",
            latency_ms=1500,
            cost_eur=0.005,
            input_tokens=100,
            output_tokens=200,
            status="success",
            trace_id="trace-123",
        )

        assert response.status == "success"
        assert response.error_message is None

    def test_error_response(self):
        """Test error model response info."""
        response = ModelResponseInfo(
            model_id="openai:gpt-4o",
            provider="openai",
            model_name="gpt-4o",
            response_text="",
            latency_ms=0,
            cost_eur=None,
            input_tokens=None,
            output_tokens=None,
            status="error",
            error_message="Rate limit exceeded",
            trace_id="trace-123",
        )

        assert response.status == "error"
        assert response.error_message == "Rate limit exceeded"


class TestComparisonResponse:
    """Test ComparisonResponse schema."""

    def test_comparison_response(self):
        """Test creating comparison response."""
        response = ComparisonResponse(
            batch_id="batch-123",
            query="Test query",
            responses=[
                ModelResponseInfo(
                    model_id="openai:gpt-4o",
                    provider="openai",
                    model_name="gpt-4o",
                    response_text="Response 1",
                    latency_ms=1000,
                    cost_eur=0.005,
                    input_tokens=50,
                    output_tokens=100,
                    status="success",
                    trace_id="trace-1",
                ),
                ModelResponseInfo(
                    model_id="anthropic:claude-3-sonnet",
                    provider="anthropic",
                    model_name="claude-3-sonnet",
                    response_text="Response 2",
                    latency_ms=1200,
                    cost_eur=0.006,
                    input_tokens=50,
                    output_tokens=120,
                    status="success",
                    trace_id="trace-2",
                ),
            ],
            created_at=datetime.utcnow(),
        )

        assert response.batch_id == "batch-123"
        assert len(response.responses) == 2


class TestVoteResponse:
    """Test VoteResponse schema."""

    def test_successful_vote(self):
        """Test successful vote response."""
        response = VoteResponse(
            success=True,
            message="Voto registrato con successo",
            winner_model_id="openai:gpt-4o",
            elo_changes={"openai:gpt-4o": 16.5, "anthropic:claude-3-sonnet": -16.5},
        )

        assert response.success is True
        assert response.elo_changes["openai:gpt-4o"] == 16.5


class TestAvailableModel:
    """Test AvailableModel schema."""

    def test_available_model(self):
        """Test creating available model info."""
        model = AvailableModel(
            model_id="openai:gpt-4o",
            provider="openai",
            model_name="gpt-4o",
            display_name="GPT-4o",
            is_enabled=True,
            elo_rating=1550.0,
            total_comparisons=100,
            wins=60,
        )

        assert model.model_id == "openai:gpt-4o"
        assert model.elo_rating == 1550.0

    def test_available_model_defaults(self):
        """Test available model default values."""
        model = AvailableModel(
            model_id="openai:gpt-4o",
            provider="openai",
            model_name="gpt-4o",
            display_name="GPT-4o",
        )

        assert model.is_enabled is True
        assert model.elo_rating is None
        assert model.total_comparisons == 0
        assert model.wins == 0


class TestModelRanking:
    """Test ModelRanking schema."""

    def test_model_ranking(self):
        """Test creating model ranking."""
        ranking = ModelRanking(
            rank=1,
            model_id="openai:gpt-4o",
            provider="openai",
            model_name="gpt-4o",
            display_name="GPT-4o",
            elo_rating=1650.0,
            total_comparisons=200,
            wins=130,
            win_rate=0.65,
        )

        assert ranking.rank == 1
        assert ranking.win_rate == 0.65


class TestLeaderboardResponse:
    """Test LeaderboardResponse schema."""

    def test_leaderboard_response(self):
        """Test creating leaderboard response."""
        response = LeaderboardResponse(
            rankings=[
                ModelRanking(
                    rank=1,
                    model_id="openai:gpt-4o",
                    provider="openai",
                    model_name="gpt-4o",
                    display_name="GPT-4o",
                    elo_rating=1650.0,
                    total_comparisons=200,
                    wins=130,
                    win_rate=0.65,
                ),
                ModelRanking(
                    rank=2,
                    model_id="anthropic:claude-3-sonnet",
                    provider="anthropic",
                    model_name="claude-3-sonnet",
                    display_name="Claude 3 Sonnet",
                    elo_rating=1580.0,
                    total_comparisons=180,
                    wins=100,
                    win_rate=0.56,
                ),
            ],
            last_updated=datetime.utcnow(),
        )

        assert len(response.rankings) == 2
        assert response.rankings[0].rank == 1


class TestComparisonStats:
    """Test ComparisonStats schema."""

    def test_comparison_stats(self):
        """Test creating comparison stats."""
        stats = ComparisonStats(
            total_comparisons=50,
            total_votes=45,
            comparisons_this_week=10,
            votes_this_week=8,
            favorite_model="openai:gpt-4o",
            favorite_model_vote_count=20,
        )

        assert stats.total_comparisons == 50
        assert stats.favorite_model == "openai:gpt-4o"

    def test_comparison_stats_defaults(self):
        """Test comparison stats default values."""
        stats = ComparisonStats(
            total_comparisons=0,
            total_votes=0,
            comparisons_this_week=0,
            votes_this_week=0,
        )

        assert stats.favorite_model is None
        assert stats.favorite_model_vote_count == 0
