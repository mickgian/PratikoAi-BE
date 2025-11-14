"""
Regulatory Documents Models for Dynamic Knowledge Collection System.

These models store regulatory documents from Italian authorities with
proper versioning, status tracking, and metadata management.
"""

from datetime import (
    datetime,
    timezone,
)
from enum import Enum
from typing import (
    Any,
    Dict,
    Optional,
)

from sqlalchemy import String
from sqlmodel import (
    JSON,
    Column,
    DateTime,
    Field,
    SQLModel,
    Text,
)


class DocumentSource(str, Enum):
    """Enumeration of regulatory document sources."""

    AGENZIA_ENTRATE = "agenzia_entrate"
    INPS = "inps"
    GAZZETTA_UFFICIALE = "gazzetta_ufficiale"
    GOVERNO = "governo"
    INAIL = "inail"
    MINISTERO_ECONOMIA = "ministero_economia"
    OTHER = "other"


class ProcessingStatus(str, Enum):
    """Enumeration of document processing statuses."""

    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class RegulatoryDocument(SQLModel, table=True):
    """Model for regulatory documents from Italian authorities."""

    __tablename__ = "regulatory_documents"

    # Primary identification
    id: Optional[str] = Field(default=None, primary_key=True, max_length=100)

    # Source information
    source: str = Field(description="Source authority (agenzia_entrate, inps, etc.)")
    source_type: str = Field(description="Document type (circolari, risoluzioni, etc.)")

    # Document metadata
    title: str = Field(description="Document title")
    url: str = Field(description="Original document URL", unique=True)
    published_date: Optional[datetime] = Field(default=None, description="Official publication date")

    # Content information
    content: str = Field(sa_column=Column(Text), description="Extracted text content")
    content_hash: str = Field(description="SHA256 hash for duplicate detection")

    # Document classification
    document_number: Optional[str] = Field(default=None, description="Official document number")
    authority: Optional[str] = Field(default=None, description="Publishing authority name")

    # Metadata and version management
    document_metadata: Dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON), description="Additional document metadata"
    )
    version: int = Field(default=1, description="Document version number")
    previous_version_id: Optional[str] = Field(default=None, description="ID of previous version if this is an update")

    # Processing information
    status: ProcessingStatus = Field(default=ProcessingStatus.PENDING, description="Current processing status")
    processed_at: Optional[datetime] = Field(default=None, description="When document was successfully processed")
    processing_errors: Optional[str] = Field(default=None, description="Any errors encountered during processing")

    # Knowledge base integration
    knowledge_item_id: Optional[int] = Field(default=None, description="Associated knowledge_items record ID")

    # Classification and tagging
    topics: Optional[str] = Field(default=None, description="Comma-separated list of topics/keywords")
    importance_score: float = Field(default=0.5, description="Calculated importance score (0.0-1.0)")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
        description="Record creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
        description="Last update timestamp",
    )

    # Archival information
    archived_at: Optional[datetime] = Field(default=None, description="When document was archived")
    archive_reason: Optional[str] = Field(default=None, description="Reason for archiving")


class FeedStatus(SQLModel, table=True):
    """Model for tracking RSS feed monitoring status."""

    __tablename__ = "feed_status"

    # Primary identification
    id: Optional[int] = Field(default=None, primary_key=True)

    # Feed information
    feed_url: str = Field(unique=True, description="RSS feed URL")
    source: Optional[str] = Field(default=None, description="Source authority")
    feed_type: Optional[str] = Field(default=None, description="Type of feed")
    parser: Optional[str] = Field(
        default=None, description="Parser to use (agenzia_normativa, inps, gazzetta_ufficiale, generic)"
    )

    # Status tracking
    status: str = Field(description="Current status (healthy, unhealthy, error)")
    last_checked: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
        description="Last health check timestamp",
    )
    last_success: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True)), description="Last successful fetch timestamp"
    )

    # Performance metrics
    response_time_ms: Optional[float] = Field(default=None, description="Last response time in milliseconds")
    items_found: Optional[int] = Field(default=None, description="Number of items in last successful fetch")

    # Error tracking
    consecutive_errors: int = Field(default=0, description="Count of consecutive errors")
    errors: int = Field(default=0, description="Total error count")
    last_error: Optional[str] = Field(default=None, description="Last error message")
    last_error_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True)), description="Last error timestamp"
    )

    # Configuration
    check_interval_minutes: int = Field(default=240, description="Check interval in minutes")  # 4 hours
    enabled: bool = Field(default=True, description="Whether feed monitoring is enabled")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
        description="Record creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
        description="Last update timestamp",
    )


class DocumentProcessingLog(SQLModel, table=True):
    """Model for logging document processing activities."""

    __tablename__ = "document_processing_log"

    # Primary identification
    id: Optional[int] = Field(default=None, primary_key=True)

    # Document reference
    document_id: Optional[str] = Field(
        default=None, foreign_key="regulatory_documents.id", description="Associated regulatory document ID"
    )
    document_url: str = Field(description="Document URL")

    # Processing information
    operation: str = Field(description="Operation type (create, update, archive, etc.)")
    status: str = Field(description="Operation status (success, failed, partial)")

    # Performance metrics
    processing_time_ms: Optional[float] = Field(default=None, description="Processing time in milliseconds")
    content_length: Optional[int] = Field(default=None, description="Extracted content length")

    # Error information
    error_message: Optional[str] = Field(default=None, description="Error message if operation failed")
    error_details: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON), description="Detailed error information"
    )

    # Context information
    triggered_by: str = Field(description="What triggered this operation (scheduler, manual, api)")
    feed_url: Optional[str] = Field(default=None, description="Source RSS feed URL")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
        description="Log entry timestamp",
    )


class DocumentCollection(SQLModel, table=True):
    """Model for grouping related regulatory documents."""

    __tablename__ = "document_collections"

    # Primary identification
    id: Optional[int] = Field(default=None, primary_key=True)

    # Collection metadata
    name: str = Field(description="Collection name")
    description: Optional[str] = Field(default=None, description="Collection description")

    # Classification
    source: str = Field(description="Primary source authority")
    document_type: str = Field(description="Type of documents in collection")

    # Statistics
    document_count: int = Field(default=0, description="Number of documents")
    total_content_length: int = Field(default=0, description="Total content length")

    # Date ranges
    earliest_document: Optional[datetime] = Field(default=None, description="Publication date of earliest document")
    latest_document: Optional[datetime] = Field(default=None, description="Publication date of latest document")

    # Collection status
    status: str = Field(default="active", description="Collection status")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
        description="Collection creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
        description="Last update timestamp",
    )


# Helper functions for common operations


def create_document_id(source: str, document_number: str, year: int) -> str:
    """Create standardized document ID.

    Args:
        source: Source authority
        document_number: Official document number
        year: Publication year

    Returns:
        Standardized document ID
    """
    # Clean document number for ID
    clean_number = document_number.replace("/", "_").replace(" ", "_")
    return f"{source}_{year}_{clean_number}"


def extract_topics_from_content(content: str) -> str:
    """Extract topics/keywords from document content.

    Args:
        content: Document text content

    Returns:
        Comma-separated list of topics
    """
    # Common Italian tax and legal keywords
    keywords = [
        "IVA",
        "imposta",
        "dichiarazione",
        "redditi",
        "società",
        "fattura",
        "contributi",
        "detrazioni",
        "deduzioni",
        "aliquota",
        "codice fiscale",
        "partita IVA",
        "INPS",
        "INAIL",
        "F24",
        "modello",
        "scadenza",
        "pensione",
        "previdenza",
        "decreto",
        "circolare",
        "risoluzione",
    ]

    found_topics = []
    content_lower = content.lower()

    for keyword in keywords:
        if keyword.lower() in content_lower:
            found_topics.append(keyword)

    return ", ".join(found_topics[:10])  # Limit to 10 topics


def calculate_importance_score(
    source: str, document_type: str, content_length: int, published_date: Optional[datetime] = None
) -> float:
    """Calculate importance score for a document.

    Args:
        source: Source authority
        document_type: Type of document
        content_length: Length of content
        published_date: Publication date

    Returns:
        Importance score between 0.0 and 1.0
    """
    score = 0.5  # Base score

    # Source-based scoring
    source_scores = {"gazzetta_ufficiale": 0.95, "agenzia_entrate": 0.90, "governo": 0.90, "inps": 0.85, "inail": 0.80}

    if source in source_scores:
        score = source_scores[source]

    # Document type scoring
    if document_type in ["decreto_legislativo", "legge", "decreto_legge"]:
        score += 0.05
    elif document_type in ["circolari", "risoluzioni"]:
        score += 0.02

    # Content length consideration
    if content_length > 5000:
        score += 0.03
    elif content_length > 2000:
        score += 0.01

    # Recency consideration
    if published_date:
        days_old = (datetime.now(timezone.utc) - published_date).days
        if days_old < 30:  # Very recent
            score += 0.02
        elif days_old > 365:  # Old documents
            score -= 0.05

    return min(1.0, max(0.1, score))
