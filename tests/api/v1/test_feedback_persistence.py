"""DEV-433: Tests for detailed feedback persistence endpoint.

Covers:
- Creation saves to DB (mock db)
- Feedback type enum validation
- Langfuse failure does not block DB persistence
- Upsert behavior (duplicate trace_id + message_id)
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Pre-populate sys.modules to prevent real DB connection attempts at import.
# This MUST happen before any app module import.
# ---------------------------------------------------------------------------
if "app.services.database" not in sys.modules:
    _mock_db_module = MagicMock()
    _mock_db_module.database_service = MagicMock(is_connected=True)
    sys.modules["app.services.database"] = _mock_db_module

from uuid import uuid4

import pytest

from app.models.chat_feedback import FeedbackType
from app.schemas.feedback import DetailedFeedbackRequest, UserFeedbackResponse


class TestSubmitDetailedFeedback:
    """Test POST /feedback/detailed endpoint."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock async database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        return db

    @pytest.fixture
    def valid_request(self) -> DetailedFeedbackRequest:
        """Create a valid detailed feedback request."""
        return DetailedFeedbackRequest(
            trace_id="trace-abc-123",
            message_id="msg-def-456",
            feedback_type="correct",
            score=1,
            user_id=1,
            studio_id=uuid4(),
            category="accuracy",
            comment="Risposta perfetta.",
        )

    @pytest.mark.asyncio
    async def test_creation_saves_to_db(self, mock_db: AsyncMock, valid_request: DetailedFeedbackRequest) -> None:
        """Happy path: feedback is persisted to DB and returns success."""
        from app.api.v1.feedback import submit_detailed_feedback

        with patch("app.api.v1.feedback.feedback_service") as mock_service:
            mock_service.submit_feedback = MagicMock(return_value=True)

            result = await submit_detailed_feedback(body=valid_request, db=mock_db)

            assert isinstance(result, UserFeedbackResponse)
            assert result.success is True
            assert "successo" in result.message

            # Verify DB operations were called
            mock_db.add.assert_called_once()
            mock_db.flush.assert_awaited_once()
            mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_db_receives_correct_model(self, mock_db: AsyncMock, valid_request: DetailedFeedbackRequest) -> None:
        """The ChatFeedback model passed to db.add has correct fields."""
        from app.api.v1.feedback import submit_detailed_feedback

        with patch("app.api.v1.feedback.feedback_service") as mock_service:
            mock_service.submit_feedback = MagicMock(return_value=True)

            await submit_detailed_feedback(body=valid_request, db=mock_db)

            # Extract the ChatFeedback instance passed to db.add
            added_obj = mock_db.add.call_args[0][0]
            assert added_obj.trace_id == "trace-abc-123"
            assert added_obj.message_id == "msg-def-456"
            assert added_obj.feedback_type == FeedbackType.CORRECT
            assert added_obj.score == 1
            assert added_obj.user_id == 1
            assert added_obj.category == "accuracy"
            assert added_obj.comment == "Risposta perfetta."

    @pytest.mark.asyncio
    async def test_feedback_type_correct(self, mock_db: AsyncMock) -> None:
        """feedback_type='correct' maps to FeedbackType.CORRECT."""
        from app.api.v1.feedback import submit_detailed_feedback

        request = DetailedFeedbackRequest(
            trace_id="trace-1",
            message_id="msg-1",
            feedback_type="correct",
            score=1,
        )

        with patch("app.api.v1.feedback.feedback_service") as mock_service:
            mock_service.submit_feedback = MagicMock(return_value=True)

            await submit_detailed_feedback(body=request, db=mock_db)

            added_obj = mock_db.add.call_args[0][0]
            assert added_obj.feedback_type == FeedbackType.CORRECT

    @pytest.mark.asyncio
    async def test_feedback_type_incomplete(self, mock_db: AsyncMock) -> None:
        """feedback_type='incomplete' maps to FeedbackType.INCOMPLETE."""
        from app.api.v1.feedback import submit_detailed_feedback

        request = DetailedFeedbackRequest(
            trace_id="trace-2",
            message_id="msg-2",
            feedback_type="incomplete",
            score=0,
        )

        with patch("app.api.v1.feedback.feedback_service") as mock_service:
            mock_service.submit_feedback = MagicMock(return_value=True)

            await submit_detailed_feedback(body=request, db=mock_db)

            added_obj = mock_db.add.call_args[0][0]
            assert added_obj.feedback_type == FeedbackType.INCOMPLETE

    @pytest.mark.asyncio
    async def test_feedback_type_incorrect(self, mock_db: AsyncMock) -> None:
        """feedback_type='incorrect' maps to FeedbackType.INCORRECT."""
        from app.api.v1.feedback import submit_detailed_feedback

        request = DetailedFeedbackRequest(
            trace_id="trace-3",
            message_id="msg-3",
            feedback_type="incorrect",
            score=0,
            comment="Legge citata sbagliata.",
        )

        with patch("app.api.v1.feedback.feedback_service") as mock_service:
            mock_service.submit_feedback = MagicMock(return_value=True)

            await submit_detailed_feedback(body=request, db=mock_db)

            added_obj = mock_db.add.call_args[0][0]
            assert added_obj.feedback_type == FeedbackType.INCORRECT

    @pytest.mark.asyncio
    async def test_invalid_feedback_type_raises(self) -> None:
        """Invalid feedback_type string raises ValueError during enum conversion."""
        from app.api.v1.feedback import submit_detailed_feedback

        request = DetailedFeedbackRequest(
            trace_id="trace-bad",
            message_id="msg-bad",
            feedback_type="invalid_type",
            score=0,
        )

        mock_db = AsyncMock()
        mock_db.add = MagicMock()

        with pytest.raises(ValueError, match="invalid_type"):
            await submit_detailed_feedback(body=request, db=mock_db)

    @pytest.mark.asyncio
    async def test_langfuse_failure_db_still_works(self, mock_db: AsyncMock) -> None:
        """Langfuse exception does not block DB persistence."""
        from app.api.v1.feedback import submit_detailed_feedback

        request = DetailedFeedbackRequest(
            trace_id="trace-langfuse-fail",
            message_id="msg-langfuse-fail",
            feedback_type="correct",
            score=1,
        )

        with patch("app.api.v1.feedback.feedback_service") as mock_service:
            mock_service.submit_feedback = MagicMock(side_effect=Exception("Langfuse connection timeout"))

            result = await submit_detailed_feedback(body=request, db=mock_db)

            # DB still committed
            assert result.success is True
            mock_db.add.assert_called_once()
            mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_langfuse_called_with_correct_args(
        self, mock_db: AsyncMock, valid_request: DetailedFeedbackRequest
    ) -> None:
        """Langfuse submit_feedback is called with trace_id, score, and comment."""
        from app.api.v1.feedback import submit_detailed_feedback

        with patch("app.api.v1.feedback.feedback_service") as mock_service:
            mock_service.submit_feedback = MagicMock(return_value=True)

            await submit_detailed_feedback(body=valid_request, db=mock_db)

            mock_service.submit_feedback.assert_called_once_with(
                trace_id="trace-abc-123",
                score=1,
                comment="Risposta perfetta.",
            )

    @pytest.mark.asyncio
    async def test_nullable_user_and_studio(self, mock_db: AsyncMock) -> None:
        """Feedback with no user_id or studio_id is valid (anonymous)."""
        from app.api.v1.feedback import submit_detailed_feedback

        request = DetailedFeedbackRequest(
            trace_id="trace-anon",
            message_id="msg-anon",
            feedback_type="incomplete",
            score=0,
        )

        with patch("app.api.v1.feedback.feedback_service") as mock_service:
            mock_service.submit_feedback = MagicMock(return_value=True)

            result = await submit_detailed_feedback(body=request, db=mock_db)

            assert result.success is True
            added_obj = mock_db.add.call_args[0][0]
            assert added_obj.user_id is None
            assert added_obj.studio_id is None

    @pytest.mark.asyncio
    async def test_response_message_in_italian(self, mock_db: AsyncMock) -> None:
        """Response message is in Italian."""
        from app.api.v1.feedback import submit_detailed_feedback

        request = DetailedFeedbackRequest(
            trace_id="trace-it",
            message_id="msg-it",
            feedback_type="correct",
            score=1,
        )

        with patch("app.api.v1.feedback.feedback_service") as mock_service:
            mock_service.submit_feedback = MagicMock(return_value=True)

            result = await submit_detailed_feedback(body=request, db=mock_db)

            assert "registrato" in result.message.lower() or "successo" in result.message.lower()

    @pytest.mark.asyncio
    async def test_upsert_multiple_feedback_same_trace(self, mock_db: AsyncMock) -> None:
        """Multiple feedback entries for the same trace_id are allowed (append, not replace)."""
        from app.api.v1.feedback import submit_detailed_feedback

        with patch("app.api.v1.feedback.feedback_service") as mock_service:
            mock_service.submit_feedback = MagicMock(return_value=True)

            request1 = DetailedFeedbackRequest(
                trace_id="trace-dup",
                message_id="msg-dup",
                feedback_type="correct",
                score=1,
            )
            request2 = DetailedFeedbackRequest(
                trace_id="trace-dup",
                message_id="msg-dup",
                feedback_type="incorrect",
                score=0,
                comment="Ci ho ripensato.",
            )

            result1 = await submit_detailed_feedback(body=request1, db=mock_db)
            result2 = await submit_detailed_feedback(body=request2, db=mock_db)

            assert result1.success is True
            assert result2.success is True
            # Two separate DB adds (append behavior)
            assert mock_db.add.call_count == 2

    @pytest.mark.asyncio
    async def test_default_score_zero(self, mock_db: AsyncMock) -> None:
        """When score is not provided, it defaults to 0."""
        from app.api.v1.feedback import submit_detailed_feedback

        request = DetailedFeedbackRequest(
            trace_id="trace-default-score",
            message_id="msg-default-score",
            feedback_type="incorrect",
        )

        with patch("app.api.v1.feedback.feedback_service") as mock_service:
            mock_service.submit_feedback = MagicMock(return_value=True)

            await submit_detailed_feedback(body=request, db=mock_db)

            added_obj = mock_db.add.call_args[0][0]
            assert added_obj.score == 0
