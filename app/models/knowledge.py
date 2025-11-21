"""Knowledge base models for full-text search.
Supports Italian tax and legal knowledge with PostgreSQL FTS.
"""

from datetime import (
    UTC,
    date,
    datetime,
    timezone,
)
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Date,
    DateTime,
    Index,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlmodel import (
    JSON,
    Column,
    Field,
    SQLModel,
    Text,
)


class KnowledgeItem(SQLModel, table=True):
    """Knowledge base item with full-text search support.

    This model stores processed knowledge from various sources including:
    - Italian official documents
    - FAQ entries
    - Template responses
    - Legal references
    """

    __tablename__ = "knowledge_items"

    id: int | None = Field(default=None, primary_key=True)

    # Content identification
    title: str = Field(..., description="Knowledge item title")
    content: str = Field(..., sa_column=Column(Text), description="Main content")
    category: str = Field(..., description="Knowledge category")
    subcategory: str | None = Field(default=None, description="Knowledge subcategory")

    # Source information
    source: str = Field(..., description="Source of knowledge (official_docs, faq, template, etc.)")
    source_url: str | None = Field(default=None, description="Original source URL")
    source_id: str | None = Field(default=None, description="External source identifier")

    # Content metadata
    language: str = Field(default="it", description="Content language")
    content_type: str = Field(default="text", description="Content type (text, html, markdown)")
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON), description="Content tags")

    # Search and relevance
    search_vector: str | None = Field(
        default=None, sa_column=Column(TSVECTOR), description="Full-text search vector (managed by database trigger)"
    )
    relevance_score: float = Field(default=0.5, description="Base relevance score (0-1)")

    # Hybrid RAG fields
    kb_epoch: float | None = Field(
        default=None, description="Unix timestamp when content was ingested (for recency boost)"
    )
    embedding: list[float] | None = Field(
        default=None, sa_column=Column(Vector(1536)), description="Vector embedding (1536-d, pgvector type)"
    )

    # Usage tracking
    view_count: int = Field(default=0, description="Number of times viewed/retrieved")
    last_accessed: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True)), description="Last access timestamp"
    )

    # Quality metrics
    accuracy_score: float | None = Field(default=None, description="Content accuracy score")
    user_feedback_score: float | None = Field(default=None, description="Average user rating")
    feedback_count: int = Field(default=0, description="Number of user feedback entries")

    # PDF extraction quality (for document sources)
    extraction_method: str | None = Field(
        default=None, description="Extraction method used: 'pdf_text', 'mixed', or 'ocr'"
    )
    text_quality: float | None = Field(default=None, description="Document-level text quality score (0.0-1.0)")
    ocr_pages: list[dict[str, Any]] | None = Field(
        default=None,
        sa_column=Column(JSON),
        description="Pages that required OCR, e.g. [{'page': 3, 'reason': 'low_quality'}]",
    )

    # Publication metadata (extracted from document content)
    publication_date: date | None = Field(
        default=None,
        sa_column=Column(Date),
        description="Publication date extracted from document content (for year filtering)",
    )

    # Relationships and references
    related_items: list[int] = Field(
        default_factory=list, sa_column=Column(JSON), description="IDs of related knowledge items"
    )
    legal_references: list[str] = Field(
        default_factory=list, sa_column=Column(JSON), description="Legal references and citations"
    )

    # Status and versioning
    status: str = Field(default="active", description="Item status (active, archived, draft)")
    version: str = Field(default="1.0", description="Content version")

    # Dates
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), sa_column=Column(DateTime(timezone=True)))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), sa_column=Column(DateTime(timezone=True)))
    reviewed_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True)), description="Last review date"
    )

    # Additional metadata (using 'extra_metadata' to avoid SQLModel conflict)
    extra_metadata: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON), description="Additional metadata"
    )

    __table_args__ = (
        # Primary indexes for search performance
        Index("idx_knowledge_title", "title"),
        Index("idx_knowledge_category", "category", "subcategory"),
        Index("idx_knowledge_source", "source"),
        Index("idx_knowledge_language", "language"),
        Index("idx_knowledge_status", "status"),
        # Performance indexes
        Index("idx_knowledge_relevance", "relevance_score"),
        Index("idx_knowledge_updated", "updated_at"),
        Index("idx_knowledge_access", "last_accessed"),
        # Composite indexes for common queries
        Index("idx_knowledge_category_relevance", "category", "relevance_score"),
        Index("idx_knowledge_status_updated", "status", "updated_at"),
        # Full-text search indexes (added by migration)
        # Index("idx_knowledge_search_vector", "search_vector", postgresql_using="gin"),
        # Index("idx_knowledge_category_search", "category", "search_vector", postgresql_using="gin"),
    )


class KnowledgeQuery(SQLModel):
    """Query model for knowledge search requests"""

    query: str = Field(..., description="Search query string")
    category: str | None = Field(default=None, description="Filter by category")
    subcategory: str | None = Field(default=None, description="Filter by subcategory")
    source: str | None = Field(default=None, description="Filter by source")
    language: str = Field(default="it", description="Search language")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Results offset for pagination")
    min_relevance: float = Field(default=0.01, ge=0.0, le=1.0, description="Minimum relevance score")


class KnowledgeSearchResponse(SQLModel):
    """Response model for knowledge search results"""

    query: str = Field(..., description="Original search query")
    results: list[dict[str, Any]] = Field(..., description="Search results")
    total_count: int = Field(..., description="Total number of matches")
    page_size: int = Field(..., description="Results per page")
    page: int = Field(..., description="Current page number")
    search_time_ms: float = Field(..., description="Search execution time in milliseconds")
    suggestions: list[str] = Field(default_factory=list, description="Search suggestions")


class KnowledgeFeedback(SQLModel, table=True):
    """User feedback on knowledge items"""

    __tablename__ = "knowledge_feedback"

    id: int | None = Field(default=None, primary_key=True)

    # Reference
    knowledge_item_id: int = Field(..., foreign_key="knowledge_items.id")
    user_id: int = Field(..., foreign_key="user.id", description="User who provided feedback")
    session_id: str = Field(..., description="Session ID")

    # Feedback
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    feedback_text: str | None = Field(default=None, sa_column=Column(Text))
    feedback_type: str = Field(..., description="Type: helpful, accurate, outdated, etc.")

    # Context
    search_query: str | None = Field(default=None, description="Original search query")
    context: dict[str, Any] | None = Field(
        default_factory=dict, sa_column=Column(JSON), description="Additional context"
    )

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ip_address: str | None = Field(default=None, description="User IP (anonymized)")
    user_agent: str | None = Field(default=None, description="User agent")

    __table_args__ = (
        Index("idx_feedback_knowledge_item", "knowledge_item_id"),
        Index("idx_feedback_user", "user_id"),
        Index("idx_feedback_rating", "rating"),
        Index("idx_feedback_type", "feedback_type"),
        Index("idx_feedback_created", "created_at"),
    )
