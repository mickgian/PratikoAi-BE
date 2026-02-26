"""DEV-380: Deadline SQLModel — Tracks deadlines from multiple sources.

Supports regulatory, tax, and client-specific deadlines. ClientDeadline
provides the many-to-many link between clients and deadlines.
"""

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class DeadlineType(StrEnum):
    """Type of deadline."""

    FISCALE = "fiscale"
    ADEMPIMENTO = "adempimento"
    CONTRIBUTIVO = "contributivo"
    SOCIETARIO = "societario"


class DeadlineSource(StrEnum):
    """Source of the deadline."""

    REGULATORY = "regulatory"
    TAX = "tax"
    CLIENT_SPECIFIC = "client_specific"


class Deadline(SQLModel, table=True):  # type: ignore[call-arg]
    """Deadline definition from multiple sources.

    Attributes:
        id: UUID primary key.
        title: Human-readable deadline title.
        description: Extended description (nullable).
        deadline_type: FISCALE / ADEMPIMENTO / CONTRIBUTIVO / SOCIETARIO.
        source: REGULATORY / TAX / CLIENT_SPECIFIC.
        due_date: The actual deadline date.
        recurrence_rule: Recurrence pattern (nullable, e.g. MONTHLY_16).
        is_active: Whether the deadline is currently active.
        created_at / updated_at: Audit timestamps.
    """

    __tablename__ = "deadlines"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    title: str = Field(max_length=300)
    description: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )

    deadline_type: DeadlineType = Field(
        sa_column=Column(String(20), nullable=False),
    )
    source: DeadlineSource = Field(
        sa_column=Column(String(20), nullable=False),
    )

    due_date: date = Field(sa_column=Column(Date, nullable=False))
    recurrence_rule: str | None = Field(default=None, max_length=50)

    is_active: bool = Field(default=True)

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True),
    )

    __table_args__ = (
        Index("ix_deadlines_type_active", "deadline_type", "is_active"),
        Index("ix_deadlines_due_date", "due_date"),
    )

    def __repr__(self) -> str:
        dt = self.deadline_type.value if isinstance(self.deadline_type, DeadlineType) else self.deadline_type
        return f"<Deadline(title='{self.title}', type='{dt}')>"


class ClientDeadline(SQLModel, table=True):  # type: ignore[call-arg]
    """Many-to-many link between clients and deadlines.

    Attributes:
        id: UUID primary key.
        client_id: FK → clients.id.
        deadline_id: FK → deadlines.id.
        studio_id: FK → studios.id (tenant isolation).
        is_completed: Whether the client has met this deadline.
        completed_at: Timestamp of completion (nullable).
        notes: Free-text notes (nullable).
    """

    __tablename__ = "client_deadlines"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    client_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    deadline_id: UUID = Field(foreign_key="deadlines.id", index=True)
    studio_id: UUID = Field(foreign_key="studios.id", index=True)

    is_completed: bool = Field(default=False)
    completed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    notes: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )

    __table_args__ = (
        Index("ix_client_deadlines_studio", "studio_id"),
        Index("ix_client_deadlines_client_deadline", "client_id", "deadline_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<ClientDeadline(client_id={self.client_id}, deadline_id={self.deadline_id})>"
