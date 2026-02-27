"""DEV-306: ProceduraProgress SQLModel — Tracks user progress through procedures.

Links user, studio, procedura, and optionally client.  Stores current step
and completed steps array for progress resumption.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class ProceduraProgress(SQLModel, table=True):  # type: ignore[call-arg]
    """Tracks a user's progress through a procedure.

    Attributes:
        id: UUID primary key.
        user_id: FK → user.id.
        studio_id: FK → studios.id.
        procedura_id: FK → procedure.id.
        client_id: FK → clients.id (nullable — procedure can be general).
        current_step: Index of current step.
        completed_steps: JSONB array of completed step indices.
        started_at: When the user started this procedure.
        completed_at: When the user finished (nullable).
        notes: Free-text notes (nullable).
    """

    __tablename__ = "procedura_progress"

    # PK
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Required FKs
    user_id: int = Field(foreign_key="user.id", index=True)
    studio_id: UUID = Field(foreign_key="studios.id", index=True)
    procedura_id: UUID = Field(foreign_key="procedure.id", index=True)

    # Optional FK
    client_id: int | None = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("clients.id"), nullable=True, index=True),
    )

    # Progress tracking
    current_step: int = Field(default=0, ge=0)
    completed_steps: list = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )

    # Timestamps
    started_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    completed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    # Notes
    notes: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )

    # DEV-343: Checklist state tracking (JSONB: {"step_idx": {"item_idx": bool}})
    checklist_state: dict = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="{}"),
    )

    # DEV-344: Document verification state (JSONB: {"doc_name": bool})
    document_status: dict = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="{}"),
    )

    # Indexes
    __table_args__ = (
        Index("ix_procedura_progress_user_procedura", "user_id", "procedura_id"),
        Index("ix_procedura_progress_studio", "studio_id"),
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def is_completed(self) -> bool:
        """Return True when the procedure is finished."""
        return self.completed_at is not None

    def __repr__(self) -> str:
        return f"<ProceduraProgress(user_id={self.user_id}, step={self.current_step})>"
