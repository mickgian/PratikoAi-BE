"""DEV-422: Notification SQLModel — In-app notifications for professionals.

Supports 4 notification types: SCADENZA, MATCH, COMUNICAZIONE, NORMATIVA.
Polymorphic reference to source entity via reference_id + reference_type.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class NotificationType(StrEnum):
    """Notification category type."""

    SCADENZA = "scadenza"
    MATCH = "match"
    COMUNICAZIONE = "comunicazione"
    NORMATIVA = "normativa"


class NotificationPriority(StrEnum):
    """Notification priority level."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Notification(SQLModel, table=True):  # type: ignore[call-arg]
    """In-app notification for professionals.

    Attributes:
        id: UUID primary key.
        user_id: FK → user.id (notification recipient).
        studio_id: FK → studios.id (multi-tenant isolation).
        notification_type: SCADENZA / MATCH / COMUNICAZIONE / NORMATIVA.
        priority: LOW / MEDIUM / HIGH / URGENT.
        title: Short notification title.
        description: Extended description (nullable).
        reference_id: Polymorphic FK to source entity (nullable).
        reference_type: Source entity type string (nullable).
        is_read: Whether the user has read it.
        read_at: Timestamp of read (nullable).
        dismissed: Whether the user dismissed it.
        created_at / updated_at: Audit timestamps.
    """

    __tablename__ = "notifications"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    user_id: int = Field(foreign_key="user.id", index=True)
    studio_id: UUID = Field(foreign_key="studios.id", index=True)

    notification_type: NotificationType = Field(
        sa_column=Column(String(20), nullable=False),
    )
    priority: NotificationPriority = Field(
        sa_column=Column(String(10), nullable=False),
    )

    title: str = Field(max_length=300)
    description: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )

    reference_id: UUID | None = Field(default=None, index=True)
    reference_type: str | None = Field(default=None, max_length=50)

    is_read: bool = Field(default=False)
    read_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    dismissed: bool = Field(default=False)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True),
    )

    __table_args__ = (
        Index("ix_notifications_user_unread", "user_id", "is_read"),
        Index("ix_notifications_studio_type", "studio_id", "notification_type"),
        Index("ix_notifications_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Notification(type={self.notification_type}, title='{self.title}')>"
