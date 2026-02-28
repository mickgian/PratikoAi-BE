"""DEV-357: Activity Timeline Model.

Aggregates recent actions (communications, procedures, matches) for
the dashboard timeline display.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class ActivityType(StrEnum):
    """Type of activity tracked."""

    COMMUNICATION_SENT = "communication_sent"
    COMMUNICATION_DRAFT = "communication_draft"
    PROCEDURA_STARTED = "procedura_started"
    PROCEDURA_COMPLETED = "procedura_completed"
    MATCH_FOUND = "match_found"
    CLIENT_CREATED = "client_created"
    CLIENT_UPDATED = "client_updated"
    DOCUMENT_UPLOADED = "document_uploaded"


class ActivityTimeline(SQLModel, table=True):  # type: ignore[call-arg]
    """Activity timeline entry for dashboard.

    Attributes:
        id: UUID primary key.
        studio_id: FK -> studios.id (multi-tenant).
        user_id: FK -> user.id (who performed the action).
        activity_type: Type of activity.
        title: Short description of activity.
        description: Extended description (nullable).
        reference_id: Polymorphic FK to source entity.
        reference_type: Source entity type string.
        metadata: Additional JSONB metadata.
        created_at: When the activity occurred.
    """

    __tablename__ = "activity_timeline"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    studio_id: UUID = Field(foreign_key="studios.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    activity_type: ActivityType = Field(
        sa_column=Column(String(30), nullable=False),
    )

    title: str = Field(max_length=300)
    description: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )

    reference_id: UUID | None = Field(default=None, index=True)
    reference_type: str | None = Field(default=None, max_length=50)

    metadata_json: dict | None = Field(
        default=None,
        sa_column=Column("metadata", JSONB, nullable=True),
    )

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )

    __table_args__ = (
        Index("ix_activity_timeline_studio_created", "studio_id", "created_at"),
        Index("ix_activity_timeline_type", "activity_type"),
    )

    def __repr__(self) -> str:
        return f"<ActivityTimeline(type={self.activity_type}, title='{self.title}')>"
