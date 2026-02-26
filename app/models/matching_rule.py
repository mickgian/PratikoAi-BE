"""DEV-303: MatchingRule SQLModel — Normative matching engine rules.

Defines flexible matching rules with JSONB conditions supporting AND/OR
operators and field comparisons.  Used by the proactive-matching engine
to identify relevant normative updates for clients.
"""

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Column, Date, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class RuleType(StrEnum):
    """Classification of matching rules."""

    NORMATIVA = "normativa"
    SCADENZA = "scadenza"
    OPPORTUNITA = "opportunita"


class MatchingRule(SQLModel, table=True):  # type: ignore[call-arg]
    """Matching rule for the normative matching engine.

    Attributes:
        id: UUID primary key.
        name: Unique human-readable name (e.g. ``R001 — Rottamazione Quater``).
        description: Extended description of the rule.
        rule_type: NORMATIVA / SCADENZA / OPPORTUNITA.
        conditions: JSONB dict with AND/OR operators and field comparisons.
        priority: 1-100, higher = more important.
        is_active: Whether the rule is currently active.
        valid_from / valid_to: Temporal validity window.
        categoria: Business category tag.
        fonte_normativa: Originating regulation reference.
    """

    __tablename__ = "matching_rules"

    # PK
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Core fields
    name: str = Field(
        sa_column=Column(String(200), unique=True, nullable=False, index=True),
    )
    description: str = Field(sa_column=Column(Text, nullable=False))
    rule_type: RuleType = Field(sa_column=Column(String(20), nullable=False))

    # Conditions (flexible JSONB)
    conditions: dict = Field(sa_column=Column(JSONB, nullable=False))

    # Priority & activation
    priority: int = Field(default=50, ge=1, le=100)
    is_active: bool = Field(default=True)

    # Validity window
    valid_from: date = Field(sa_column=Column(Date, nullable=False))
    valid_to: date | None = Field(
        default=None,
        sa_column=Column(Date, nullable=True),
    )

    # Classification
    categoria: str = Field(max_length=50)
    fonte_normativa: str = Field(max_length=200)

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
        Index("ix_matching_rules_type_active", "rule_type", "is_active"),
        Index("ix_matching_rules_priority", "priority"),
    )

    def __repr__(self) -> str:
        rt = self.rule_type.value if isinstance(self.rule_type, RuleType) else self.rule_type
        return f"<MatchingRule(name='{self.name}', type='{rt}')>"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "rule_type": self.rule_type,
            "conditions": self.conditions,
            "priority": self.priority,
            "is_active": self.is_active,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "categoria": self.categoria,
            "fonte_normativa": self.fonte_normativa,
        }
