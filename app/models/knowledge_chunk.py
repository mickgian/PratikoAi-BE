"""Knowledge chunk models for hybrid RAG (FTS + vector search).
Stores chunked documents with both tsvector and pgvector embeddings.
"""

from datetime import (
    UTC,
    datetime,
    timezone,
)
from typing import (
    List,
    Optional,
)

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Index,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlmodel import (
    Column,
    Field,
    SQLModel,
    Text,
)


class KnowledgeChunk(SQLModel, table=True):
    """Chunked knowledge for hybrid retrieval.

    Each chunk has:
    - Text content with Italian FTS (tsvector)
    - Vector embedding (1536-d, OpenAI ada-002)
    - References to parent knowledge_item
    - Recency tracking via kb_epoch
    """

    __tablename__ = "knowledge_chunks"

    id: int | None = Field(default=None, primary_key=True)

    # Parent reference
    knowledge_item_id: int | None = Field(
        default=None, foreign_key="knowledge_items.id", description="Parent knowledge item"
    )

    # Chunk content
    chunk_text: str = Field(..., sa_column=Column(Text), description="Chunk text content")
    chunk_index: int = Field(..., description="0-based chunk index within parent document")
    token_count: int = Field(..., description="Approximate token count for this chunk")

    # Search fields (added via migration)
    search_vector: str | None = Field(
        default=None, sa_column=Column(TSVECTOR), description="Italian FTS vector (auto-maintained by trigger)"
    )
    embedding: list[float] | None = Field(
        default=None, sa_column=Column(Vector(1536)), description="1536-d vector embedding (pgvector)"
    )

    # Recency tracking
    kb_epoch: float = Field(..., description="Unix timestamp when chunk was ingested")

    # Metadata
    source_url: str | None = Field(default=None, description="Original document URL")
    document_title: str | None = Field(default=None, description="Parent document title")

    # Quality tracking (for junk detection and repair)
    quality_score: float | None = Field(default=None, description="Chunk-level quality score (0.0-1.0)")
    junk: bool = Field(default=False, description="Flag indicating corrupted/low-quality chunk")
    ocr_used: bool = Field(default=False, description="Flag indicating OCR was used for extraction")

    # Character position tracking (for span references)
    start_char: int | None = Field(default=None, description="Starting character position in source document")
    end_char: int | None = Field(default=None, description="Ending character position in source document")

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), sa_column=Column(DateTime(timezone=True)))

    __table_args__ = (
        # Foreign key index
        Index("idx_chunk_knowledge_item", "knowledge_item_id"),
        # Recency index
        Index("idx_chunk_kb_epoch", "kb_epoch"),
        # Composite for common queries
        Index("idx_chunk_item_index", "knowledge_item_id", "chunk_index"),
        # FTS and vector indexes (created in migration):
        # Index("idx_chunk_search_vector", "search_vector", postgresql_using="gin"),
        # Index("idx_chunk_embedding_ivfflat", "embedding", postgresql_using="ivfflat"),
    )
