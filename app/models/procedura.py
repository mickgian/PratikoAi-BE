"""DEV-305: Procedura SQLModel — Interactive procedures with versioning.

Multi-step interactive procedures with JSONB step arrays containing
checklists, documents, and notes.  Supports versioning for updates.
"""

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Column, Date, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class ProceduraCategory(StrEnum):
    """Business category of a procedure."""

    FISCALE = "fiscale"
    LAVORO = "lavoro"
    SOCIETARIO = "societario"
    PREVIDENZA = "previdenza"


class Procedura(SQLModel, table=True):  # type: ignore[call-arg]
    """Interactive procedure definition.

    Attributes:
        id: UUID primary key.
        code: Unique procedure code (e.g. ``APERTURA_PIVA``).
        title: Human-readable title.
        description: Extended description.
        category: FISCALE / LAVORO / SOCIETARIO / PREVIDENZA.
        steps: JSONB array of step objects.
        estimated_time_minutes: Expected completion time.
        version: Integer version for updates.
        is_active: Whether the procedure is published.
        last_updated: Date of last content revision.
    """

    __tablename__ = "procedure"

    # PK
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Identification
    code: str = Field(
        sa_column=Column(String(50), unique=True, nullable=False, index=True),
    )
    title: str = Field(max_length=200)
    description: str = Field(sa_column=Column(Text, nullable=False))

    # Classification
    category: ProceduraCategory = Field(sa_column=Column(String(20), nullable=False))

    # Steps (structured JSONB)
    steps: list = Field(sa_column=Column(JSONB, nullable=False, server_default="[]"))

    # Metadata
    estimated_time_minutes: int = Field(ge=1)
    version: int = Field(default=1, ge=1)
    is_active: bool = Field(default=True)
    last_updated: date | None = Field(
        default=None,
        sa_column=Column(Date, nullable=True),
    )

    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True),
    )

    # Indexes
    __table_args__ = (Index("ix_procedure_category_active", "category", "is_active"),)

    def __repr__(self) -> str:
        return f"<Procedura(code='{self.code}', title='{self.title}')>"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "code": self.code,
            "title": self.title,
            "category": self.category,
            "steps": self.steps,
            "estimated_time_minutes": self.estimated_time_minutes,
            "version": self.version,
            "is_active": self.is_active,
        }
