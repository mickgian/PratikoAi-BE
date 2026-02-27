"""DEV-374: Data Breach Notification Model.

Tracks breach incidents with status progression and GDPR 72-hour
notification deadline. Supports severity levels and affected data tracking.
"""

from datetime import UTC, datetime, timedelta, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class BreachSeverity(StrEnum):
    """Breach severity level."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BreachStatus(StrEnum):
    """Breach handling status."""

    DETECTED = "detected"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    AUTHORITY_NOTIFIED = "authority_notified"
    RESOLVED = "resolved"


class BreachNotification(SQLModel, table=True):  # type: ignore[call-arg]
    """Data breach notification with GDPR compliance tracking.

    Attributes:
        id: UUID primary key.
        studio_id: FK → studios.id (tenant).
        title: Brief description of the breach.
        description: Detailed description.
        severity: LOW / MEDIUM / HIGH / CRITICAL.
        status: DETECTED / INVESTIGATING / CONTAINED / AUTHORITY_NOTIFIED / RESOLVED.
        reported_by: FK → user.id.
        detected_at: When the breach was detected.
        authority_notified_at: When authority was notified (nullable).
        resolved_at: When the breach was resolved (nullable).
        affected_records_count: Number of affected records (nullable).
        data_categories: JSONB list of affected data types (nullable).
    """

    __tablename__ = "breach_notifications"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    studio_id: UUID = Field(foreign_key="studios.id", index=True)

    title: str = Field(max_length=300)
    description: str = Field(sa_column=Column(Text, nullable=False))

    severity: BreachSeverity = Field(
        sa_column=Column(String(10), nullable=False),
    )
    status: BreachStatus = Field(
        default=BreachStatus.DETECTED,
        sa_column=Column(String(25), nullable=False, server_default="detected"),
    )

    reported_by: int = Field(foreign_key="user.id")

    detected_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    authority_notified_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    resolved_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    affected_records_count: int | None = Field(default=None)
    data_categories: list | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )

    __table_args__ = (
        Index("ix_breach_notifications_studio_status", "studio_id", "status"),
        Index("ix_breach_notifications_severity", "severity"),
    )

    @property
    def notification_deadline(self) -> datetime | None:
        """GDPR requires authority notification within 72 hours of detection."""
        if self.detected_at is None:
            return None
        detected = self.detected_at
        if detected.tzinfo is None:
            detected = detected.replace(tzinfo=UTC)
        return detected + timedelta(hours=72)

    def __repr__(self) -> str:
        sev = self.severity.value if isinstance(self.severity, BreachSeverity) else self.severity
        return f"<BreachNotification(title='{self.title}', severity='{sev}')>"
