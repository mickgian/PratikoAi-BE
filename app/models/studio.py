"""DEV-300: Studio SQLModel — Multi-tenant root entity.

The Studio represents a professional studio (commercialista office) and is
the tenant root for row-level data isolation.  Every client, communication,
and workflow record references a studio_id FK.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class Studio(SQLModel, table=True):  # type: ignore[call-arg]
    """Professional studio — tenant root entity.

    Attributes:
        id: UUID primary key.
        name: Human-readable studio name.
        slug: URL-safe unique identifier (e.g. ``studio-rossi``).
        settings: Arbitrary JSONB preferences (theme, locale, …).
        max_clients: Upper bound of clients allowed (default 100).
        created_at / updated_at: Audit timestamps.
    """

    __tablename__ = "studios"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Core fields
    name: str = Field(max_length=200)
    slug: str = Field(
        max_length=100,
        sa_column=Column(String(100), unique=True, nullable=False, index=True),
    )

    # Configuration
    settings: dict | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    max_clients: int = Field(default=100)

    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True),
    )

    # ------------------------------------------------------------------
    # Table-level indexes
    # ------------------------------------------------------------------
    __table_args__ = (Index("ix_studios_name", "name"),)

    def __repr__(self) -> str:
        return f"<Studio(name='{self.name}', slug='{self.slug}')>"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "slug": self.slug,
            "settings": self.settings,
            "max_clients": self.max_clients,
        }
