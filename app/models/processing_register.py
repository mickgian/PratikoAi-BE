"""DEV-376: Processing Register SQLModel — GDPR register of processing activities.

Tracks what data is processed, the purpose, legal basis, and recipients.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class ProcessingRegister(SQLModel, table=True):  # type: ignore[call-arg]
    """GDPR register of processing activities.

    Attributes:
        id: UUID primary key.
        studio_id: FK → studios.id (tenant isolation).
        activity_name: Name of the processing activity.
        purpose: Why the data is processed.
        legal_basis: GDPR legal basis (consent, contract, etc.).
        data_categories: Types of data processed.
        data_subjects: Who the data belongs to.
        retention_period: How long data is kept.
        recipients: Who receives the data.
        third_country_transfers: Whether data leaves EU.
        notes: Additional notes.
    """

    __tablename__ = "processing_register"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    studio_id: UUID = Field(foreign_key="studios.id", index=True)

    activity_name: str = Field(max_length=300)
    purpose: str = Field(sa_column=Column(Text, nullable=False))
    legal_basis: str = Field(max_length=100)

    data_categories: list[str] = Field(
        sa_column=Column(ARRAY(String(100)), nullable=False),
    )
    data_subjects: str = Field(max_length=200)
    retention_period: str = Field(max_length=100)

    recipients: list[str] | None = Field(
        default=None,
        sa_column=Column(ARRAY(String(200)), nullable=True),
    )
    third_country_transfers: bool = Field(default=False)

    notes: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True),
    )

    __table_args__ = (
        Index("ix_processing_register_studio", "studio_id"),
        Index("ix_processing_register_legal_basis", "legal_basis"),
    )

    def __repr__(self) -> str:
        return f"<ProcessingRegister(activity='{self.activity_name}', basis='{self.legal_basis}')>"
