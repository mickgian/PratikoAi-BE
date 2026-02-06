"""Feedback schemas for user thumbs-up/thumbs-down on AI responses (DEV-255).

Supports recording user satisfaction scores to Langfuse traces for
quality monitoring and model evaluation.
"""

from pydantic import BaseModel, Field


class UserFeedbackRequest(BaseModel):
    """Request model for submitting user feedback on an AI response.

    Attributes:
        trace_id: The Langfuse trace_id of the response being rated.
        score: 0 for thumbs-down, 1 for thumbs-up.
        comment: Optional free-text comment from the user.
    """

    trace_id: str = Field(..., description="Langfuse trace ID of the rated response")
    score: int = Field(..., ge=0, le=1, description="0=thumbs down, 1=thumbs up")
    comment: str | None = Field(default=None, max_length=1000, description="Optional user comment")


class UserFeedbackResponse(BaseModel):
    """Response model for feedback submission.

    Attributes:
        success: Whether the feedback was recorded successfully.
        message: Human-readable status message (Italian).
    """

    success: bool
    message: str
