"""DEV-304: Communication SQLModel — Draft/approve workflow with audit trail.

Communications go through a status workflow:
DRAFT → PENDING_REVIEW → APPROVED → SENT (or REJECTED / FAILED).
Creator cannot approve their own communications (self-approval constraint).
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class StatoComunicazione(StrEnum):
    """Communication status workflow."""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"
    FAILED = "failed"


class CanaleInvio(StrEnum):
    """Communication delivery channel."""

    EMAIL = "email"
    WHATSAPP = "whatsapp"


class Communication(SQLModel, table=True):  # type: ignore[call-arg]
    """Communication with approval workflow and audit trail.

    Attributes:
        id: UUID primary key.
        studio_id: FK → studios.id (multi-tenant).
        client_id: FK → clients.id (nullable for bulk comms).
        subject: Communication subject line.
        content: Communication body text.
        channel: Delivery channel (EMAIL / WHATSAPP).
        status: Workflow status.
        created_by: FK → user.id (creator).
        approved_by: FK → user.id (approver, nullable).
        approved_at: Approval timestamp (nullable).
        sent_at: Delivery timestamp (nullable).
        normativa_riferimento: Related regulation reference.
        matching_rule_id: FK → matching_rules.id (nullable).
    """

    __tablename__ = "communications"

    # PK
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Multi-tenant FK
    studio_id: UUID = Field(foreign_key="studios.id", index=True)

    # Target client (nullable for bulk)
    client_id: int | None = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("clients.id"), nullable=True, index=True),
    )

    # Content
    subject: str = Field(max_length=300)
    content: str = Field(sa_column=Column(Text, nullable=False))

    # Channel
    channel: CanaleInvio = Field(sa_column=Column(String(15), nullable=False))

    # Status workflow
    status: StatoComunicazione = Field(
        default=StatoComunicazione.DRAFT,
        sa_column=Column(String(20), nullable=False, server_default="draft"),
    )

    # Audit: creator and approver
    created_by: int = Field(foreign_key="user.id")
    approved_by: int | None = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("user.id"), nullable=True),
    )
    approved_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    sent_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    # Regulation reference
    normativa_riferimento: str | None = Field(default=None, max_length=200)
    matching_rule_id: UUID | None = Field(
        default=None,
        foreign_key="matching_rules.id",
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
    __table_args__ = (
        Index("ix_communications_studio_status", "studio_id", "status"),
        Index("ix_communications_created_by", "created_by"),
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def is_self_approval(self) -> bool:
        """Return True when creator and approver are the same person."""
        if self.approved_by is None:
            return False
        return self.created_by == self.approved_by

    def __repr__(self) -> str:
        st = self.status.value if isinstance(self.status, StatoComunicazione) else self.status
        return f"<Communication(subject='{self.subject}', status='{st}')>"
