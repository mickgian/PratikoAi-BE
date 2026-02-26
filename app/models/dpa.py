"""DEV-372: Data Processing Agreement (DPA) Model.

Tracks DPA versions and studio acceptance records.
Required before processing any client data (GDPR compliance).
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class DPAStatus(StrEnum):
    """DPA lifecycle status."""

    DRAFT = "draft"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REVOKED = "revoked"


class DPA(SQLModel, table=True):  # type: ignore[call-arg]
    """Data Processing Agreement with version tracking.

    Attributes:
        id: UUID primary key.
        title: Agreement title.
        version: Version string (e.g. "1.0", "2.1").
        content: Full agreement text.
        status: DRAFT / ACTIVE / SUPERSEDED / REVOKED.
        effective_from: Date agreement takes effect (nullable).
        created_at / updated_at: Audit timestamps.
    """

    __tablename__ = "dpas"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    title: str = Field(max_length=300)
    version: str = Field(max_length=20)
    content: str = Field(sa_column=Column(Text, nullable=False))

    status: DPAStatus = Field(
        default=DPAStatus.DRAFT,
        sa_column=Column(String(20), nullable=False, server_default="draft"),
    )

    effective_from: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True),
    )

    __table_args__ = (
        Index("ix_dpas_status", "status"),
        Index("ix_dpas_version", "version"),
    )

    def __repr__(self) -> str:
        return f"<DPA(title='{self.title}', version='{self.version}')>"


class DPAAcceptance(SQLModel, table=True):  # type: ignore[call-arg]
    """Record of a studio accepting a DPA version.

    Attributes:
        id: UUID primary key.
        dpa_id: FK → dpas.id.
        studio_id: FK → studios.id.
        accepted_by: FK → user.id.
        accepted_at: Timestamp of acceptance.
        ip_address: IP from which acceptance was made.
        user_agent: Browser user agent (nullable).
    """

    __tablename__ = "dpa_acceptances"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    dpa_id: UUID = Field(foreign_key="dpas.id", index=True)
    studio_id: UUID = Field(foreign_key="studios.id", index=True)
    accepted_by: int = Field(foreign_key="user.id")

    accepted_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )

    ip_address: str = Field(max_length=45)
    user_agent: str | None = Field(default=None, max_length=500)

    __table_args__ = (Index("ix_dpa_acceptances_studio_dpa", "studio_id", "dpa_id"),)

    def __repr__(self) -> str:
        return f"<DPAAcceptance(dpa_id={self.dpa_id}, studio_id={self.studio_id})>"
