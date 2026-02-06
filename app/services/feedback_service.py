"""Feedback service for recording user satisfaction scores to Langfuse (DEV-255).

Provides graceful degradation: returns False on any failure, never raises.
"""

import logging

from app.observability.langfuse_spans import get_langfuse_client

logger = logging.getLogger(__name__)


class FeedbackService:
    """Service for submitting user feedback scores to Langfuse."""

    def submit_feedback(
        self,
        trace_id: str,
        score: int,
        comment: str | None = None,
    ) -> bool:
        """Submit user feedback as a Langfuse score.

        Args:
            trace_id: The Langfuse trace_id to attach the score to.
            score: 0 for thumbs-down, 1 for thumbs-up.
            comment: Optional free-text comment.

        Returns:
            True if feedback was recorded, False on any failure.
        """
        client = get_langfuse_client()
        if client is None:
            logger.warning("feedback_langfuse_unavailable", extra={"trace_id": trace_id})
            return False

        try:
            client.create_score(
                name="user-feedback",
                value=score,
                trace_id=trace_id,
                data_type="NUMERIC",
                comment=comment,
            )
            logger.info(
                "feedback_recorded",
                extra={"trace_id": trace_id, "score": score, "has_comment": comment is not None},
            )
            return True
        except Exception as e:
            logger.warning(
                "feedback_recording_failed",
                extra={
                    "trace_id": trace_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return False


feedback_service = FeedbackService()
