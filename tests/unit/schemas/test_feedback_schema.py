"""Unit tests for UserFeedbackRequest and UserFeedbackResponse schemas.

Tests cover:
- Valid feedback request creation
- Score range validation (0 or 1 only)
- trace_id is mandatory
- Optional comment field
"""

import pytest
from pydantic import ValidationError

from app.schemas.feedback import UserFeedbackRequest, UserFeedbackResponse


class TestUserFeedbackRequest:
    """Tests for UserFeedbackRequest schema."""

    def test_valid_feedback_request(self) -> None:
        """Valid request with trace_id, score, and comment."""
        req = UserFeedbackRequest(
            trace_id="trace-abc-123",
            score=1,
            comment="Molto utile!",
        )
        assert req.trace_id == "trace-abc-123"
        assert req.score == 1
        assert req.comment == "Molto utile!"

    def test_score_range_validation_thumbs_down(self) -> None:
        """Score 0 (thumbs down) should be valid."""
        req = UserFeedbackRequest(trace_id="trace-123", score=0)
        assert req.score == 0

    def test_score_range_validation_thumbs_up(self) -> None:
        """Score 1 (thumbs up) should be valid."""
        req = UserFeedbackRequest(trace_id="trace-123", score=1)
        assert req.score == 1

    def test_score_range_validation_too_high(self) -> None:
        """Score > 1 should be rejected."""
        with pytest.raises(ValidationError):
            UserFeedbackRequest(trace_id="trace-123", score=2)

    def test_score_range_validation_negative(self) -> None:
        """Score < 0 should be rejected."""
        with pytest.raises(ValidationError):
            UserFeedbackRequest(trace_id="trace-123", score=-1)

    def test_trace_id_required(self) -> None:
        """trace_id is mandatory."""
        with pytest.raises(ValidationError):
            UserFeedbackRequest(score=1)  # type: ignore[call-arg]

    def test_optional_comment_none(self) -> None:
        """Comment should be optional (defaults to None)."""
        req = UserFeedbackRequest(trace_id="trace-123", score=1)
        assert req.comment is None

    def test_optional_comment_with_value(self) -> None:
        """Comment should accept a string value."""
        req = UserFeedbackRequest(
            trace_id="trace-123",
            score=0,
            comment="Non pertinente alla domanda.",
        )
        assert req.comment == "Non pertinente alla domanda."


class TestUserFeedbackResponse:
    """Tests for UserFeedbackResponse schema."""

    def test_success_response(self) -> None:
        """Valid success response."""
        resp = UserFeedbackResponse(success=True, message="Feedback registrato con successo.")
        assert resp.success is True
        assert resp.message == "Feedback registrato con successo."

    def test_failure_response(self) -> None:
        """Valid failure response."""
        resp = UserFeedbackResponse(success=False, message="Feedback ricevuto.")
        assert resp.success is False
