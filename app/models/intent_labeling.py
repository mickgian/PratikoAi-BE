"""Database Models for Intent Labeling System.

DEV-253: Expert labeling UI for intent classifier training.
Captures low-confidence HF classifications for expert review.

Models:
- IntentLabel: Enum of valid intent categories
- LabeledQuery: Stores queries for expert labeling
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Index, Text
from sqlmodel import Field, SQLModel


class IntentLabel(str, Enum):
    """Valid intent labels for classification.

    These match the RoutingCategory enum in app.schemas.router
    and the HFIntentClassifier.INTENT_LABELS.
    """

    CHITCHAT = "chitchat"
    THEORETICAL_DEFINITION = "theoretical_definition"
    TECHNICAL_RESEARCH = "technical_research"
    CALCULATOR = "calculator"
    GOLDEN_SET = "golden_set"


class LabeledQuery(SQLModel, table=True):
    """Stores queries captured for expert labeling.

    Low-confidence HF classifications are captured here for experts to review
    and label. The labeled data is used to fine-tune the intent classifier.

    Attributes:
        id: Primary key UUID
        query: The user query text
        predicted_intent: HF classifier's prediction
        confidence: HF classifier's confidence score (0.0-1.0)
        all_scores: Full score distribution from HF classifier
        expert_intent: Expert-assigned intent label (null until labeled)
        labeled_by: User ID of the expert who labeled this query
        labeled_at: Timestamp when labeled
        labeling_notes: Optional notes from the expert
        source_query_id: UUID of the original query (for traceability)
        is_deleted: Soft delete flag
        skip_count: Number of times experts skipped this query
        created_at: When the query was captured
    """

    __tablename__ = "labeled_queries"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Query content
    query: str = Field(sa_column=Column(Text, nullable=False))

    # HF classifier prediction
    predicted_intent: str = Field(max_length=50)
    confidence: float = Field(ge=0.0, le=1.0)
    all_scores: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # Expert labeling fields
    expert_intent: str | None = Field(default=None, max_length=50)
    labeled_by: int | None = Field(default=None, foreign_key="user.id")
    labeled_at: datetime | None = Field(default=None)
    labeling_notes: str | None = Field(default=None, max_length=500)

    # Traceability
    source_query_id: UUID | None = Field(default=None)

    # Soft delete and skip tracking
    is_deleted: bool = Field(default=False, index=True)
    skip_count: int = Field(default=0)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Composite index for efficient queue queries
    # (is_deleted=False, expert_intent=NULL, ORDER BY confidence ASC)
    __table_args__ = (
        Index(
            "ix_labeled_queries_queue",
            "is_deleted",
            "expert_intent",
            "confidence",
        ),
    )
