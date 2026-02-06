"""Unit tests for feedback service.

Tests cover:
- Feedback creates Langfuse score correctly
- Comment is passed through
- Graceful degradation when Langfuse is unavailable
- Exception handling doesn't propagate
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services.feedback_service import FeedbackService


class TestFeedbackService:
    """Tests for FeedbackService."""

    def setup_method(self) -> None:
        """Create a fresh service instance for each test."""
        self.service = FeedbackService()

    @patch("app.services.feedback_service.get_langfuse_client")
    def test_submit_feedback_creates_langfuse_score(self, mock_get_client: MagicMock) -> None:
        """Should call langfuse create_score with correct parameters."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        result = self.service.submit_feedback(
            trace_id="trace-abc",
            score=1,
            comment=None,
        )

        assert result is True
        mock_client.create_score.assert_called_once()
        call_kwargs = mock_client.create_score.call_args[1]
        assert call_kwargs["name"] == "user-feedback"
        assert call_kwargs["value"] == 1
        assert call_kwargs["trace_id"] == "trace-abc"
        assert call_kwargs["data_type"] == "NUMERIC"

    @patch("app.services.feedback_service.get_langfuse_client")
    def test_submit_feedback_with_comment(self, mock_get_client: MagicMock) -> None:
        """Comment should be passed through to Langfuse score."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        result = self.service.submit_feedback(
            trace_id="trace-abc",
            score=0,
            comment="Non pertinente",
        )

        assert result is True
        call_kwargs = mock_client.create_score.call_args[1]
        assert call_kwargs["comment"] == "Non pertinente"

    @patch("app.services.feedback_service.get_langfuse_client")
    def test_submit_feedback_graceful_degradation(self, mock_get_client: MagicMock) -> None:
        """Should return False when Langfuse client is unavailable."""
        mock_get_client.return_value = None

        result = self.service.submit_feedback(
            trace_id="trace-abc",
            score=1,
        )

        assert result is False

    @patch("app.services.feedback_service.get_langfuse_client")
    def test_submit_feedback_exception_handled(self, mock_get_client: MagicMock) -> None:
        """Exceptions should not propagate, should return False."""
        mock_client = MagicMock()
        mock_client.create_score.side_effect = Exception("Network error")
        mock_get_client.return_value = mock_client

        result = self.service.submit_feedback(
            trace_id="trace-abc",
            score=1,
        )

        assert result is False
