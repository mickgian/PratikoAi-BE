"""Feedback schemas for user thumbs-up/thumbs-down on AI responses (DEV-255, DEV-433).

Supports recording user satisfaction scores to Langfuse traces for
quality monitoring and model evaluation, plus detailed feedback with
persistent DB storage.
"""

from uuid import UUID

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


class DetailedFeedbackRequest(BaseModel):
    """Request model for detailed feedback with category and type (DEV-433).

    Persisted to DB + Langfuse (dual-write). DB write is authoritative;
    Langfuse failure does not block persistence.

    Attributes:
        trace_id: Langfuse trace ID of the rated response.
        message_id: Chat message ID being rated.
        feedback_type: One of correct, incomplete, incorrect.
        score: Numeric score (0 or 1).
        user_id: Optional user ID (FK to user.id).
        studio_id: Optional studio ID for multi-tenant isolation.
        category: Optional feedback category label.
        comment: Optional free-text comment (up to 2000 chars).
    """

    trace_id: str = Field(..., description="Langfuse trace ID of the rated response")
    message_id: str = Field(..., description="Chat message ID being rated")
    feedback_type: str = Field(..., description="correct, incomplete, or incorrect")
    score: int = Field(default=0, ge=0, le=1, description="0=negative, 1=positive")
    user_id: int | None = Field(default=None, description="User ID (FK to user.id)")
    studio_id: UUID | None = Field(default=None, description="Studio ID for tenant isolation")
    category: str | None = Field(default=None, max_length=100, description="Feedback category")
    comment: str | None = Field(default=None, max_length=2000, description="Free-text comment")


class UserFeedbackResponse(BaseModel):
    """Response model for feedback submission.

    Attributes:
        success: Whether the feedback was recorded successfully.
        message: Human-readable status message (Italian).
    """

    success: bool
    message: str
