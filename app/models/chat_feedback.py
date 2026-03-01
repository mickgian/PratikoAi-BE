"""DEV-433: ChatFeedback SQLModel — Persistent storage for user feedback on AI responses.

Dual-write: DB + Langfuse. DB always written; Langfuse failure doesn't block persistence.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class FeedbackType(StrEnum):
    """Type of feedback on AI response."""

    CORRECT = "correct"
    INCOMPLETE = "incomplete"
    INCORRECT = "incorrect"


class ChatFeedback(SQLModel, table=True):  # type: ignore[call-arg]
    """Persistent user feedback on AI chat responses.

    Stored in DB alongside Langfuse integration for dual-write reliability.
    """

    __tablename__ = "chat_feedback"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    user_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    studio_id: UUID | None = Field(default=None, foreign_key="studios.id", index=True)

    trace_id: str = Field(max_length=200, index=True)
    message_id: str = Field(max_length=200)

    feedback_type: FeedbackType = Field(
        sa_column=Column(String(20), nullable=False),
    )

    category: str | None = Field(default=None, max_length=100)
    comment: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )

    score: int = Field(default=0)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )

    __table_args__ = (
        Index("ix_chat_feedback_trace", "trace_id"),
        Index("ix_chat_feedback_user_studio", "user_id", "studio_id"),
    )

    def __repr__(self) -> str:
        return f"<ChatFeedback(trace_id='{self.trace_id}', type='{self.feedback_type}')>"
