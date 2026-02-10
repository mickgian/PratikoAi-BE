"""Tests for model comparison API endpoints (DEV-256)."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from app.models.user import UserRole
from app.schemas.comparison import (
    AvailableModel,
    ComparisonResponse,
    ComparisonStats,
    ModelRanking,
    ModelResponseInfo,
    PendingComparisonData,
    VoteResponse,
)


class TestRequireSuperUser:
    """Test SUPER_USER role requirement."""

    def test_require_super_user_valid(self):
        """Test SUPER_USER role is allowed."""
        from app.api.v1.model_comparison import _require_super_user

        user = MagicMock()
        user.role = UserRole.SUPER_USER.value

        # Should not raise
        _require_super_user(user)

    def test_require_admin_valid(self):
        """Test ADMIN role is allowed."""
        from app.api.v1.model_comparison import _require_super_user

        user = MagicMock()
        user.role = UserRole.ADMIN.value

        # Should not raise
        _require_super_user(user)

    def test_require_super_user_regular_user_denied(self):
        """Test regular user is denied."""
        from fastapi import HTTPException

        from app.api.v1.model_comparison import _require_super_user

        user = MagicMock()
        user.role = UserRole.REGULAR_USER.value

        with pytest.raises(HTTPException) as exc_info:
            _require_super_user(user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Accesso non autorizzato" in exc_info.value.detail

    def test_require_super_user_expert_denied(self):
        """Test expert user is denied."""
        from fastapi import HTTPException

        from app.api.v1.model_comparison import _require_super_user

        user = MagicMock()
        user.role = UserRole.EXPERT.value

        with pytest.raises(HTTPException) as exc_info:
            _require_super_user(user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


class TestRunComparisonEndpoint:
    """Test run_comparison endpoint."""

    @pytest.fixture
    def mock_user(self):
        """Create mock SUPER_USER."""
        user = MagicMock()
        user.id = 1
        user.role = UserRole.SUPER_USER.value
        return user

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_run_comparison_success(self, mock_user, mock_db):
        """Test successful comparison run."""
        from app.api.v1.model_comparison import run_comparison
        from app.schemas.comparison import ComparisonRequest

        request = ComparisonRequest(
            query="Test query",
            model_ids=["openai:gpt-4o", "anthropic:claude-3-sonnet"],
        )

        mock_result = ComparisonResponse(
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
            ],
            created_at=datetime.utcnow(),
        )

        with patch("app.api.v1.model_comparison.get_comparison_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.run_comparison = AsyncMock(return_value=mock_result)
            mock_get_service.return_value = mock_service

            result = await run_comparison(request, mock_user, mock_db)

            assert result.batch_id == "batch-123"
            mock_service.run_comparison.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_comparison_validation_error(self, mock_user, mock_db):
        """Test comparison with validation error."""
        from fastapi import HTTPException

        from app.api.v1.model_comparison import run_comparison
        from app.schemas.comparison import ComparisonRequest

        request = ComparisonRequest(
            query="Test query",
            model_ids=["openai:gpt-4o", "anthropic:claude-3-sonnet"],
        )

        with patch("app.api.v1.model_comparison.get_comparison_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.run_comparison = AsyncMock(side_effect=ValueError("La domanda non può essere vuota"))
            mock_get_service.return_value = mock_service

            with pytest.raises(HTTPException) as exc_info:
                await run_comparison(request, mock_user, mock_db)

            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_run_comparison_all_models_failed(self, mock_user, mock_db):
        """Test comparison when all models fail."""
        from fastapi import HTTPException

        from app.api.v1.model_comparison import run_comparison
        from app.schemas.comparison import ComparisonRequest

        request = ComparisonRequest(
            query="Test query",
            model_ids=["openai:gpt-4o", "anthropic:claude-3-sonnet"],
        )

        with patch("app.api.v1.model_comparison.get_comparison_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.run_comparison = AsyncMock(
                side_effect=ValueError("Tutti i modelli hanno fallito. Riprova più tardi.")
            )
            mock_get_service.return_value = mock_service

            with pytest.raises(HTTPException) as exc_info:
                await run_comparison(request, mock_user, mock_db)

            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestSubmitVoteEndpoint:
    """Test submit_vote endpoint."""

    @pytest.fixture
    def mock_user(self):
        """Create mock SUPER_USER."""
        user = MagicMock()
        user.id = 1
        user.role = UserRole.SUPER_USER.value
        return user

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_submit_vote_success(self, mock_user, mock_db):
        """Test successful vote submission."""
        from app.api.v1.model_comparison import submit_vote
        from app.schemas.comparison import VoteRequest

        request = VoteRequest(
            batch_id="batch-123",
            winner_model_id="openai:gpt-4o",
        )

        mock_result = VoteResponse(
            success=True,
            message="Voto registrato con successo",
            winner_model_id="openai:gpt-4o",
            elo_changes={"openai:gpt-4o": 16.0, "anthropic:claude-3-sonnet": -16.0},
        )

        with patch("app.api.v1.model_comparison.get_comparison_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.submit_vote = AsyncMock(return_value=mock_result)
            mock_get_service.return_value = mock_service

            result = await submit_vote(request, mock_user, mock_db)

            assert result.success is True
            mock_service.submit_vote.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_vote_session_not_found(self, mock_user, mock_db):
        """Test vote for non-existent session."""
        from fastapi import HTTPException

        from app.api.v1.model_comparison import submit_vote
        from app.schemas.comparison import VoteRequest

        request = VoteRequest(
            batch_id="invalid-batch",
            winner_model_id="openai:gpt-4o",
        )

        with patch("app.api.v1.model_comparison.get_comparison_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.submit_vote = AsyncMock(side_effect=ValueError("Sessione di confronto non trovata"))
            mock_get_service.return_value = mock_service

            with pytest.raises(HTTPException) as exc_info:
                await submit_vote(request, mock_user, mock_db)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_submit_vote_already_voted(self, mock_user, mock_db):
        """Test duplicate vote."""
        from fastapi import HTTPException

        from app.api.v1.model_comparison import submit_vote
        from app.schemas.comparison import VoteRequest

        request = VoteRequest(
            batch_id="batch-123",
            winner_model_id="openai:gpt-4o",
        )

        with patch("app.api.v1.model_comparison.get_comparison_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.submit_vote = AsyncMock(side_effect=ValueError("Voto già registrato per questa sessione"))
            mock_get_service.return_value = mock_service

            with pytest.raises(HTTPException) as exc_info:
                await submit_vote(request, mock_user, mock_db)

            assert exc_info.value.status_code == status.HTTP_409_CONFLICT


class TestGetModelsEndpoint:
    """Test get_models endpoint."""

    @pytest.fixture
    def mock_user(self):
        """Create mock SUPER_USER."""
        user = MagicMock()
        user.id = 1
        user.role = UserRole.SUPER_USER.value
        return user

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_get_models_success(self, mock_user, mock_db):
        """Test getting available models."""
        from app.api.v1.model_comparison import get_models

        mock_models = [
            AvailableModel(
                model_id="openai:gpt-4o",
                provider="openai",
                model_name="gpt-4o",
                display_name="GPT-4o",
                is_enabled=True,
                elo_rating=1550.0,
                total_comparisons=100,
                wins=60,
            ),
        ]

        with patch("app.api.v1.model_comparison.get_comparison_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_available_models = AsyncMock(return_value=mock_models)
            mock_get_service.return_value = mock_service

            result = await get_models(mock_user, mock_db)

            assert len(result.models) == 1
            assert result.models[0].model_id == "openai:gpt-4o"


class TestGetLeaderboardEndpoint:
    """Test get_leaderboard endpoint."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_get_leaderboard_success(self, mock_db):
        """Test getting leaderboard."""
        from app.api.v1.model_comparison import get_leaderboard

        mock_rankings = [
            ModelRanking(
                rank=1,
                model_id="openai:gpt-4o",
                provider="openai",
                model_name="gpt-4o",
                display_name="GPT-4o",
                elo_rating=1600.0,
                total_comparisons=100,
                wins=65,
                win_rate=0.65,
            ),
        ]

        with patch("app.api.v1.model_comparison.get_comparison_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_leaderboard = AsyncMock(return_value=mock_rankings)
            mock_get_service.return_value = mock_service

            result = await get_leaderboard(limit=20, db=mock_db)

            assert len(result.rankings) == 1
            assert result.rankings[0].rank == 1


class TestGetStatsEndpoint:
    """Test get_stats endpoint."""

    @pytest.fixture
    def mock_user(self):
        """Create mock SUPER_USER."""
        user = MagicMock()
        user.id = 1
        user.role = UserRole.SUPER_USER.value
        return user

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_get_stats_success(self, mock_user, mock_db):
        """Test getting user stats."""
        from app.api.v1.model_comparison import get_stats

        mock_stats = ComparisonStats(
            total_comparisons=50,
            total_votes=45,
            comparisons_this_week=10,
            votes_this_week=8,
            favorite_model="openai:gpt-4o",
            favorite_model_vote_count=20,
        )

        with patch("app.api.v1.model_comparison.get_comparison_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_user_stats = AsyncMock(return_value=mock_stats)
            mock_get_service.return_value = mock_service

            result = await get_stats(mock_user, mock_db)

            assert result.stats.total_comparisons == 50
            assert result.stats.favorite_model == "openai:gpt-4o"


class TestUpdatePreferencesEndpoint:
    """Test update_preferences endpoint."""

    @pytest.fixture
    def mock_user(self):
        """Create mock SUPER_USER."""
        user = MagicMock()
        user.id = 1
        user.role = UserRole.SUPER_USER.value
        return user

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_update_preferences_success(self, mock_user, mock_db):
        """Test updating preferences."""
        from app.api.v1.model_comparison import update_preferences
        from app.schemas.comparison import ModelPreferencesRequest

        request = ModelPreferencesRequest(
            enabled_model_ids=["openai:gpt-4o", "anthropic:claude-3-sonnet"],
        )

        with patch("app.api.v1.model_comparison.get_comparison_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.update_preferences = AsyncMock()
            mock_get_service.return_value = mock_service

            result = await update_preferences(request, mock_user, mock_db)

            assert "message" in result
            mock_service.update_preferences.assert_called_once()


class TestPendingComparisonEndpoints:
    """Test pending comparison endpoints."""

    @pytest.fixture
    def mock_user(self):
        """Create mock SUPER_USER."""
        user = MagicMock()
        user.id = 1
        user.role = UserRole.SUPER_USER.value
        return user

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_create_pending_comparison_success(self, mock_user, mock_db):
        """Test creating a pending comparison."""
        from app.api.v1.model_comparison import create_pending_comparison
        from app.schemas.comparison import CreatePendingComparisonRequest

        request = CreatePendingComparisonRequest(
            query="Test query",
            response="Test response from AI",
            model_id="openai:gpt-4o",
        )

        with patch("app.api.v1.model_comparison.get_comparison_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.create_pending_comparison = AsyncMock(return_value="test-uuid-123")
            mock_get_service.return_value = mock_service

            result = await create_pending_comparison(request, mock_user, mock_db)

            assert result.pending_id == "test-uuid-123"
            mock_service.create_pending_comparison.assert_called_once_with(
                user_id=1,
                query="Test query",
                response="Test response from AI",
                model_id="openai:gpt-4o",
                db=mock_db,
                enriched_prompt=None,
                latency_ms=None,
                cost_eur=None,
                input_tokens=None,
                output_tokens=None,
                trace_id=None,
            )

    @pytest.mark.asyncio
    async def test_get_pending_comparison_success(self, mock_user, mock_db):
        """Test getting a pending comparison."""
        from app.api.v1.model_comparison import get_pending_comparison

        mock_data = PendingComparisonData(
            query="Test query",
            response="Test response",
            model_id="openai:gpt-4o",
        )

        with patch("app.api.v1.model_comparison.get_comparison_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_pending_comparison = AsyncMock(return_value=mock_data)
            mock_get_service.return_value = mock_service

            result = await get_pending_comparison("test-uuid-123", mock_user, mock_db)

            assert result.query == "Test query"
            assert result.response == "Test response"
            assert result.model_id == "openai:gpt-4o"
            mock_service.get_pending_comparison.assert_called_once_with(
                pending_id="test-uuid-123",
                user_id=1,
                db=mock_db,
            )

    @pytest.mark.asyncio
    async def test_get_pending_comparison_not_found(self, mock_user, mock_db):
        """Test getting a non-existent pending comparison."""
        from fastapi import HTTPException

        from app.api.v1.model_comparison import get_pending_comparison

        with patch("app.api.v1.model_comparison.get_comparison_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_pending_comparison = AsyncMock(return_value=None)
            mock_get_service.return_value = mock_service

            with pytest.raises(HTTPException) as exc_info:
                await get_pending_comparison("invalid-uuid", mock_user, mock_db)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert "Confronto pendente non trovato" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_pending_comparison_regular_user_denied(self, mock_db):
        """Test that regular users cannot create pending comparisons."""
        from fastapi import HTTPException

        from app.api.v1.model_comparison import create_pending_comparison
        from app.schemas.comparison import CreatePendingComparisonRequest

        regular_user = MagicMock()
        regular_user.id = 1
        regular_user.role = UserRole.REGULAR_USER.value

        request = CreatePendingComparisonRequest(
            query="Test query",
            response="Test response",
            model_id="openai:gpt-4o",
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_pending_comparison(request, regular_user, mock_db)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
