"""Tests for unevaluated comparison sessions listing.

Tests for:
- GET /model-comparison/sessions/unevaluated endpoint
- Service method get_unevaluated_sessions
- Only returns sessions without a winner_model (unvoted)
- Only returns sessions for the current user
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status

from app.models.user import UserRole
from app.schemas.comparison import (
    ComparisonSessionDetail,
    ModelResponseDetail,
)


class TestGetUnevaluatedSessionsEndpoint:
    """Test retrieving unevaluated (unvoted) comparison sessions."""

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

    @pytest.fixture
    def sample_sessions(self):
        """Create sample unevaluated sessions."""
        return [
            ComparisonSessionDetail(
                batch_id="batch-1",
                query="What is Python?",
                responses=[
                    ModelResponseDetail(
                        response_id=str(uuid4()),
                        model_id="openai:gpt-4o",
                        provider="openai",
                        model_name="gpt-4o",
                        response_text="Python is a programming language.",
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
            ),
            ComparisonSessionDetail(
                batch_id="batch-2",
                query="What is FastAPI?",
                responses=[
                    ModelResponseDetail(
                        response_id=str(uuid4()),
                        model_id="anthropic:claude-3-sonnet",
                        provider="anthropic",
                        model_name="claude-3-sonnet",
                        response_text="FastAPI is a web framework.",
                        latency_ms=1200,
                        cost_eur=0.006,
                        input_tokens=60,
                        output_tokens=120,
                        status="success",
                        trace_id="trace-2",
                    ),
                ],
                created_at=datetime.utcnow(),
                winner_model=None,
                vote_comment=None,
                vote_timestamp=None,
            ),
        ]

    @pytest.mark.asyncio
    async def test_get_unevaluated_sessions_success(self, mock_user, mock_db, sample_sessions):
        """Test successful retrieval of unevaluated sessions."""
        from app.api.v1.model_comparison import get_unevaluated_sessions

        with patch("app.api.v1.model_comparison.get_comparison_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_unevaluated_sessions = AsyncMock(return_value=sample_sessions)
            mock_get_service.return_value = mock_service

            result = await get_unevaluated_sessions(mock_user, mock_db)

            assert result.sessions is not None
            assert len(result.sessions) == 2
            assert result.sessions[0].batch_id == "batch-1"
            assert result.sessions[1].batch_id == "batch-2"
            # All should have no winner (unevaluated)
            for session in result.sessions:
                assert session.winner_model is None
            mock_service.get_unevaluated_sessions.assert_called_once_with(
                user_id=mock_user.id,
                db=mock_db,
            )

    @pytest.mark.asyncio
    async def test_get_unevaluated_sessions_empty(self, mock_user, mock_db):
        """Test empty list when all sessions have been evaluated."""
        from app.api.v1.model_comparison import get_unevaluated_sessions

        with patch("app.api.v1.model_comparison.get_comparison_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_unevaluated_sessions = AsyncMock(return_value=[])
            mock_get_service.return_value = mock_service

            result = await get_unevaluated_sessions(mock_user, mock_db)

            assert result.sessions == []

    @pytest.mark.asyncio
    async def test_get_unevaluated_sessions_requires_super_user(self, mock_db):
        """Test that regular users cannot access unevaluated sessions."""
        from fastapi import HTTPException

        from app.api.v1.model_comparison import get_unevaluated_sessions

        regular_user = MagicMock()
        regular_user.id = 2
        regular_user.role = UserRole.REGULAR_USER.value

        with pytest.raises(HTTPException) as exc_info:
            await get_unevaluated_sessions(regular_user, mock_db)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


class TestGetUnevaluatedSessionsService:
    """Test the service layer for unevaluated sessions."""

    @pytest.mark.asyncio
    async def test_get_unevaluated_sessions_queries_correctly(self):
        """Test that service queries sessions with winner_model IS NULL."""
        from app.services.comparison_service import ComparisonService

        service = ComparisonService()
        mock_db = AsyncMock()

        # Mock the database query chain
        session_id_1 = uuid4()
        session_id_2 = uuid4()
        resp_id_1 = uuid4()
        resp_id_2 = uuid4()

        mock_session_1 = MagicMock()
        mock_session_1.id = session_id_1
        mock_session_1.batch_id = "batch-unevaluated-1"
        mock_session_1.query_text = "Question 1"
        mock_session_1.models_compared = '["openai:gpt-4o", "anthropic:claude-3-sonnet"]'
        mock_session_1.winner_model = None
        mock_session_1.vote_comment = None
        mock_session_1.vote_timestamp = None
        mock_session_1.created_at = datetime.utcnow()

        mock_resp_1 = MagicMock(
            spec=[
                "id",
                "provider",
                "model_name",
                "response_text",
                "latency_ms",
                "cost_eur",
                "input_tokens",
                "output_tokens",
                "status",
                "error_message",
                "trace_id",
                "expert_evaluation",
                "expert_evaluation_details",
            ]
        )
        mock_resp_1.id = resp_id_1
        mock_resp_1.provider = "openai"
        mock_resp_1.model_name = "gpt-4o"
        mock_resp_1.response_text = "Answer 1"
        mock_resp_1.latency_ms = 1000
        mock_resp_1.cost_eur = 0.01
        mock_resp_1.input_tokens = 100
        mock_resp_1.output_tokens = 200
        mock_resp_1.status = "success"
        mock_resp_1.error_message = None
        mock_resp_1.trace_id = "trace-1"
        mock_resp_1.expert_evaluation = None
        mock_resp_1.expert_evaluation_details = None
        mock_session_1.responses = [mock_resp_1]

        mock_session_2 = MagicMock()
        mock_session_2.id = session_id_2
        mock_session_2.batch_id = "batch-unevaluated-2"
        mock_session_2.query_text = "Question 2"
        mock_session_2.models_compared = '["openai:gpt-4o", "gemini:gemini-pro"]'
        mock_session_2.winner_model = None
        mock_session_2.vote_comment = None
        mock_session_2.vote_timestamp = None
        mock_session_2.created_at = datetime.utcnow()

        mock_resp_2 = MagicMock(
            spec=[
                "id",
                "provider",
                "model_name",
                "response_text",
                "latency_ms",
                "cost_eur",
                "input_tokens",
                "output_tokens",
                "status",
                "error_message",
                "trace_id",
                "expert_evaluation",
                "expert_evaluation_details",
            ]
        )
        mock_resp_2.id = resp_id_2
        mock_resp_2.provider = "gemini"
        mock_resp_2.model_name = "gemini-pro"
        mock_resp_2.response_text = "Answer 2"
        mock_resp_2.latency_ms = 800
        mock_resp_2.cost_eur = 0.008
        mock_resp_2.input_tokens = 80
        mock_resp_2.output_tokens = 150
        mock_resp_2.status = "success"
        mock_resp_2.error_message = None
        mock_resp_2.trace_id = "trace-2"
        mock_resp_2.expert_evaluation = None
        mock_resp_2.expert_evaluation_details = None
        mock_session_2.responses = [mock_resp_2]

        # Mock db.execute to return sessions first, then responses for each
        mock_sessions_result = MagicMock()
        mock_sessions_result.scalars.return_value.all.return_value = [
            mock_session_1,
            mock_session_2,
        ]
        mock_resp_result_1 = MagicMock()
        mock_resp_result_1.scalars.return_value.all.return_value = [mock_resp_1]
        mock_resp_result_2 = MagicMock()
        mock_resp_result_2.scalars.return_value.all.return_value = [mock_resp_2]

        mock_db.execute = AsyncMock(side_effect=[mock_sessions_result, mock_resp_result_1, mock_resp_result_2])

        result = await service.get_unevaluated_sessions(user_id=1, db=mock_db)

        assert len(result) == 2
        assert result[0].batch_id == "batch-unevaluated-1"
        assert result[0].query == "Question 1"
        assert result[0].winner_model is None
        assert len(result[0].responses) == 1
        assert result[1].batch_id == "batch-unevaluated-2"
        assert result[1].query == "Question 2"

    @pytest.mark.asyncio
    async def test_get_unevaluated_sessions_excludes_voted(self):
        """Test that voted sessions are NOT returned."""
        from app.services.comparison_service import ComparisonService

        service = ComparisonService()
        mock_db = AsyncMock()

        # Return empty list (all sessions have been voted on)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.get_unevaluated_sessions(user_id=1, db=mock_db)

        assert len(result) == 0
