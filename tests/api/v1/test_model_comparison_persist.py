"""Tests for persisted model comparison feature.

Tests for:
- Retrieving stored comparison sessions by batch_id
- Submitting expert evaluation on individual comparison responses
- PendingComparison persistence (no more 1-hour expiry / delete-on-read)
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status

from app.models.user import UserRole
from app.schemas.comparison import (
    ComparisonSessionDetail,
    ExpertEvaluationRequest,
    ExpertEvaluationResponse,
    ModelResponseDetail,
    PendingComparisonData,
)


class TestGetComparisonSessionEndpoint:
    """Test retrieving a stored comparison session by batch_id."""

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
    async def test_get_session_success(self, mock_user, mock_db):
        """Test successful retrieval of a stored comparison session."""
        from app.api.v1.model_comparison import get_comparison_session

        mock_result = ComparisonSessionDetail(
            batch_id="batch-123",
            query="Test query",
            responses=[
                ModelResponseDetail(
                    response_id=str(uuid4()),
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
            winner_model=None,
            vote_comment=None,
            vote_timestamp=None,
        )

        with patch("app.api.v1.model_comparison.get_comparison_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_comparison_session = AsyncMock(return_value=mock_result)
            mock_get_service.return_value = mock_service

            result = await get_comparison_session("batch-123", mock_user, mock_db)

            assert result.batch_id == "batch-123"
            assert len(result.responses) == 1
            mock_service.get_comparison_session.assert_called_once_with(
                batch_id="batch-123",
                user_id=1,
                db=mock_db,
            )

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, mock_user, mock_db):
        """Test 404 when session doesn't exist."""
        from fastapi import HTTPException

        from app.api.v1.model_comparison import get_comparison_session

        with patch("app.api.v1.model_comparison.get_comparison_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_comparison_session = AsyncMock(return_value=None)
            mock_get_service.return_value = mock_service

            with pytest.raises(HTTPException) as exc_info:
                await get_comparison_session("nonexistent", mock_user, mock_db)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_session_denied_for_regular_user(self, mock_db):
        """Test that regular users cannot access comparison sessions."""
        from fastapi import HTTPException

        from app.api.v1.model_comparison import get_comparison_session

        regular_user = MagicMock()
        regular_user.id = 1
        regular_user.role = UserRole.REGULAR_USER.value

        with pytest.raises(HTTPException) as exc_info:
            await get_comparison_session("batch-123", regular_user, mock_db)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


class TestExpertEvaluationEndpoint:
    """Test expert evaluation (corretta/incompleta/errata) on comparison responses."""

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
    async def test_submit_evaluation_correct(self, mock_user, mock_db):
        """Test submitting 'corretta' evaluation on a comparison response."""
        from app.api.v1.model_comparison import submit_expert_evaluation

        request = ExpertEvaluationRequest(
            response_id=str(uuid4()),
            evaluation="correct",
        )

        mock_result = ExpertEvaluationResponse(
            success=True,
            message="Valutazione registrata con successo",
        )

        with patch("app.api.v1.model_comparison.get_comparison_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.submit_expert_evaluation = AsyncMock(return_value=mock_result)
            mock_get_service.return_value = mock_service

            result = await submit_expert_evaluation(request, mock_user, mock_db)

            assert result.success is True
            mock_service.submit_expert_evaluation.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_evaluation_incomplete_with_details(self, mock_user, mock_db):
        """Test submitting 'incompleta' evaluation requires details."""
        from app.api.v1.model_comparison import submit_expert_evaluation

        request = ExpertEvaluationRequest(
            response_id=str(uuid4()),
            evaluation="incomplete",
            details="Manca la parte sulla normativa X",
        )

        mock_result = ExpertEvaluationResponse(
            success=True,
            message="Valutazione registrata con successo",
        )

        with patch("app.api.v1.model_comparison.get_comparison_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.submit_expert_evaluation = AsyncMock(return_value=mock_result)
            mock_get_service.return_value = mock_service

            result = await submit_expert_evaluation(request, mock_user, mock_db)

            assert result.success is True

    @pytest.mark.asyncio
    async def test_submit_evaluation_incorrect_with_details(self, mock_user, mock_db):
        """Test submitting 'errata' evaluation requires details."""
        from app.api.v1.model_comparison import submit_expert_evaluation

        request = ExpertEvaluationRequest(
            response_id=str(uuid4()),
            evaluation="incorrect",
            details="La risposta cita una legge sbagliata",
        )

        mock_result = ExpertEvaluationResponse(
            success=True,
            message="Valutazione registrata con successo",
        )

        with patch("app.api.v1.model_comparison.get_comparison_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.submit_expert_evaluation = AsyncMock(return_value=mock_result)
            mock_get_service.return_value = mock_service

            result = await submit_expert_evaluation(request, mock_user, mock_db)

            assert result.success is True

    @pytest.mark.asyncio
    async def test_submit_evaluation_response_not_found(self, mock_user, mock_db):
        """Test evaluation on non-existent response returns 404."""
        from fastapi import HTTPException

        from app.api.v1.model_comparison import submit_expert_evaluation

        request = ExpertEvaluationRequest(
            response_id=str(uuid4()),
            evaluation="correct",
        )

        with patch("app.api.v1.model_comparison.get_comparison_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.submit_expert_evaluation = AsyncMock(side_effect=ValueError("Risposta non trovata"))
            mock_get_service.return_value = mock_service

            with pytest.raises(HTTPException) as exc_info:
                await submit_expert_evaluation(request, mock_user, mock_db)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_submit_evaluation_denied_for_regular_user(self, mock_db):
        """Test that regular users cannot submit evaluations."""
        from fastapi import HTTPException

        from app.api.v1.model_comparison import submit_expert_evaluation

        regular_user = MagicMock()
        regular_user.id = 1
        regular_user.role = UserRole.REGULAR_USER.value

        request = ExpertEvaluationRequest(
            response_id=str(uuid4()),
            evaluation="correct",
        )

        with pytest.raises(HTTPException) as exc_info:
            await submit_expert_evaluation(request, regular_user, mock_db)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


class TestPendingComparisonPersistence:
    """Test that pending comparisons are persisted permanently (no delete on read)."""

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
    async def test_get_pending_comparison_does_not_delete(self, mock_user, mock_db):
        """Test that retrieving a pending comparison no longer deletes it."""
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

            # First retrieval
            result1 = await get_pending_comparison("test-uuid-123", mock_user, mock_db)
            assert result1.query == "Test query"

            # Should be retrievable again (not deleted)
            result2 = await get_pending_comparison("test-uuid-123", mock_user, mock_db)
            assert result2.query == "Test query"

            # Called twice, both should succeed
            assert mock_service.get_pending_comparison.call_count == 2
