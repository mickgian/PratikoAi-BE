"""DEV-324: ProactiveSuggestion SQLModel — Stores background matching results.

Matches found by the proactive-matching background job are stored here for
professionals to review.  Separate from Communications (which are for sending).
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Float, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class ProactiveSuggestion(SQLModel, table=True):  # type: ignore[call-arg]
    """Proactive suggestion from background matching job.

    Attributes:
        id: UUID primary key.
        studio_id: FK → studios.id (multi-tenant).
        knowledge_item_id: FK → knowledge_items.id.
        matched_client_ids: JSONB array of matched client IDs.
        match_score: Relevance score (0.0–1.0).
        suggestion_text: Human-readable suggestion text.
        is_read: Whether the professional has seen it.
        is_dismissed: Whether the professional dismissed it.
        created_at: Timestamp of creation.
    """

    __tablename__ = "proactive_suggestions"

    # PK
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Multi-tenant FK
    studio_id: UUID = Field(foreign_key="studios.id", index=True)

    # Knowledge item reference
    knowledge_item_id: int = Field(foreign_key="knowledge_items.id", index=True)

    # Matched clients (JSONB array of IDs)
    matched_client_ids: list = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )

    # Match score
    match_score: float = Field(
        sa_column=Column(Float, nullable=False),
    )

    # Suggestion text
    suggestion_text: str = Field(sa_column=Column(Text, nullable=False))

    # Status flags
    is_read: bool = Field(default=False)
    is_dismissed: bool = Field(default=False)

    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )

    # Indexes
    __table_args__ = (
        Index("ix_proactive_suggestions_studio_read", "studio_id", "is_read"),
        Index("ix_proactive_suggestions_score", "match_score"),
    )

    def __repr__(self) -> str:
        return f"<ProactiveSuggestion(knowledge_item_id={self.knowledge_item_id}, score={self.match_score})>"
