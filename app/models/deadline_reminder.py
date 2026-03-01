"""DEV-438: DeadlineReminder SQLModel — Custom per-deadline user reminders.

One reminder per user per deadline (upsert). Creates SCADENZA notification at remind_at time.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class DeadlineReminder(SQLModel, table=True):  # type: ignore[call-arg]
    """Custom per-deadline reminder set by a user.

    Attributes:
        id: UUID primary key.
        deadline_id: FK → deadlines.id.
        user_id: FK → user.id.
        studio_id: FK → studios.id.
        remind_at: When to send the reminder notification.
        is_active: Whether reminder is active.
        notification_sent: Whether the notification has been sent.
    """

    __tablename__ = "deadline_reminders"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    deadline_id: UUID = Field(foreign_key="deadlines.id", index=True)
    user_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    studio_id: UUID = Field(foreign_key="studios.id", index=True)

    remind_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    is_active: bool = Field(default=True)
    notification_sent: bool = Field(default=False)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True),
    )

    __table_args__ = (
        Index("ix_deadline_reminders_user_deadline", "user_id", "deadline_id", unique=True),
        Index("ix_deadline_reminders_remind_at", "remind_at"),
    )

    def __repr__(self) -> str:
        return f"<DeadlineReminder(deadline_id={self.deadline_id}, user_id={self.user_id})>"
