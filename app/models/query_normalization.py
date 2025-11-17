"""Database models for Italian Query Normalization tracking.

These models track normalization patterns, performance, and analytics
to support continuous improvement of cache hit rates.
"""

from datetime import UTC, datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import String
from sqlmodel import JSON, Boolean, Column, DateTime, Field, SQLModel, Text


class QueryNormalizationLog(SQLModel, table=True):
    """Log of query normalization operations for analytics and improvement.

    Tracks original queries, normalized forms, applied rules, and performance
    metrics to analyze and improve the normalization system.
    """

    __tablename__ = "query_normalization_log"

    id: int | None = Field(default=None, primary_key=True)

    # Query information
    original_query: str = Field(sa_column=Column(Text), description="Original user query")
    normalized_query: str = Field(sa_column=Column(Text), description="Normalized query form")
    query_hash: str = Field(max_length=64, description="SHA256 hash of original query")
    cache_key: str = Field(max_length=100, description="Generated cache key")

    # Normalization metadata
    applied_rules: dict[str, Any] = Field(
        default_factory=list, sa_column=Column(JSON), description="List of applied normalization rules"
    )
    processing_time_ms: float = Field(description="Processing time in milliseconds")

    # Cache analytics
    cache_hit: bool | None = Field(default=None, description="Whether query resulted in cache hit")
    cache_hit_after_normalization: bool | None = Field(default=None, description="Cache hit after normalization")

    # User context
    user_id: str | None = Field(default=None, max_length=100, description="User who made the query")
    session_id: str | None = Field(default=None, max_length=100, description="Session ID")

    # Language detection
    detected_language: str = Field(default="it", max_length=10, description="Detected query language")
    confidence_score: float = Field(default=1.0, description="Normalization confidence (0-1)")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
        description="Log entry timestamp",
    )


class QueryNormalizationStats(SQLModel, table=True):
    """Aggregated statistics for query normalization performance.

    Daily/hourly aggregations of normalization patterns and performance
    for monitoring and optimization.
    """

    __tablename__ = "query_normalization_stats"

    id: int | None = Field(default=None, primary_key=True)

    # Time period
    period_start: datetime = Field(sa_column=Column(DateTime(timezone=True)), description="Statistics period start")
    period_end: datetime = Field(sa_column=Column(DateTime(timezone=True)), description="Statistics period end")
    period_type: str = Field(max_length=20, description="Period type (hourly, daily, weekly)")

    # Volume metrics
    total_queries: int = Field(default=0, description="Total queries processed")
    normalized_queries: int = Field(default=0, description="Queries that were normalized")

    # Performance metrics
    avg_processing_time_ms: float = Field(default=0.0, description="Average processing time")
    max_processing_time_ms: float = Field(default=0.0, description="Maximum processing time")
    min_processing_time_ms: float = Field(default=0.0, description="Minimum processing time")

    # Cache effectiveness
    cache_hits_before: int = Field(default=0, description="Cache hits before normalization")
    cache_hits_after: int = Field(default=0, description="Cache hits after normalization")
    cache_hit_improvement: float = Field(default=0.0, description="Cache hit rate improvement %")

    # Rule application frequency
    rule_frequency: dict[str, int] = Field(
        default_factory=dict, sa_column=Column(JSON), description="Frequency of each normalization rule"
    )

    # Most common patterns
    common_patterns: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON), description="Most common query patterns"
    )

    # Quality metrics
    avg_confidence_score: float = Field(default=1.0, description="Average confidence score")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
        description="Statistics creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
        description="Last update timestamp",
    )


class QueryNormalizationPattern(SQLModel, table=True):
    """Identified query patterns for continuous learning.

    Tracks recurring query patterns to improve normalization rules
    and identify opportunities for FAQ responses.
    """

    __tablename__ = "query_normalization_patterns"

    id: int | None = Field(default=None, primary_key=True)

    # Pattern information
    pattern_hash: str = Field(max_length=64, unique=True, description="Unique pattern identifier")
    normalized_form: str = Field(sa_column=Column(Text), description="Canonical normalized form")

    # Pattern statistics
    frequency: int = Field(default=1, description="How often this pattern occurs")
    unique_queries: int = Field(default=1, description="Number of unique original queries")

    # Example queries
    example_queries: dict[str, Any] = Field(
        default_factory=list, sa_column=Column(JSON), description="Example original queries"
    )

    # Performance data
    avg_processing_time_ms: float = Field(description="Average processing time for this pattern")
    cache_hit_rate: float = Field(default=0.0, description="Cache hit rate for this pattern")

    # Classification
    category: str | None = Field(default=None, max_length=50, description="Pattern category (tax, legal, general)")
    complexity: str = Field(
        default="medium", max_length=20, description="Pattern complexity (simple, medium, complex)"
    )

    # FAQ potential
    faq_candidate: bool = Field(default=False, description="Whether pattern is FAQ candidate")
    faq_score: float = Field(default=0.0, description="FAQ suitability score (0-1)")

    # Timestamps
    first_seen: datetime = Field(sa_column=Column(DateTime(timezone=True)), description="First occurrence")
    last_seen: datetime = Field(sa_column=Column(DateTime(timezone=True)), description="Most recent occurrence")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
        description="Record creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
        description="Last update timestamp",
    )
