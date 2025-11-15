"""Database models for Intelligent FAQ System.

These models support FAQ entries, usage tracking, analytics, and obsolescence detection
for the Italian tax/legal domain with response variation and cost optimization.
"""

from datetime import UTC, datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import Float, Integer, String
from sqlmodel import ARRAY, JSON, Boolean, Column, DateTime, Field, SQLModel, Text


class UpdateSensitivity(str, Enum):
    """FAQ update sensitivity levels for obsolescence checking."""

    LOW = "low"  # Check monthly
    MEDIUM = "medium"  # Check weekly
    HIGH = "high"  # Check daily


class FAQEntry(SQLModel, table=True):
    """Main FAQ entries table storing questions, answers, and metadata.

    Supports semantic search, categorization, versioning, and obsolescence detection.
    """

    __tablename__ = "faq_entries"

    # Primary identification
    id: str | None = Field(default_factory=lambda: str(uuid4()), primary_key=True, max_length=100)

    # Core content
    question: str = Field(sa_column=Column(Text), description="The FAQ question")
    answer: str = Field(sa_column=Column(Text), description="The FAQ answer")
    category: str = Field(default="generale", max_length=100, description="FAQ category")
    tags: list[str] = Field(
        default_factory=list, sa_column=Column(ARRAY(String)), description="Tags for filtering and search"
    )
    language: str = Field(default="it", max_length=10, description="Content language")

    # Validation and regulatory tracking
    last_validated: datetime | None = Field(
        default_factory=lambda: datetime.now(UTC).date(), description="Last validation date"
    )
    needs_review: bool = Field(default=False, description="Whether FAQ needs review")
    regulatory_refs: dict[str, Any] = Field(
        default_factory=list, sa_column=Column(JSON), description="References to regulatory documents"
    )
    update_sensitivity: UpdateSensitivity = Field(
        default=UpdateSensitivity.MEDIUM, description="How sensitive FAQ is to regulatory changes"
    )

    # Usage analytics
    hit_count: int = Field(default=0, description="Total number of times FAQ was used")
    last_used: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True)), description="Last time FAQ was accessed"
    )
    avg_helpfulness: float | None = Field(default=None, description="Average helpfulness score (0.0-1.0)")

    # Versioning
    version: int = Field(default=1, description="Current version number")
    previous_version_id: str | None = Field(default=None, description="Previous version ID for version history")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
        description="Last update timestamp",
    )

    # Search optimization - PostgreSQL full-text search vector
    # Generated automatically by database trigger
    search_vector: str | None = Field(default=None, description="Full-text search vector (auto-generated)")

    # Similarity score (used in search results, not stored)
    similarity_score: float | None = Field(
        default=None, exclude=True, description="Similarity score for search results"
    )


class FAQUsageLog(SQLModel, table=True):
    """Log of FAQ usage for analytics, billing, and user feedback."""

    __tablename__ = "faq_usage_logs"

    # Primary identification
    id: str | None = Field(default_factory=lambda: str(uuid4()), primary_key=True, max_length=100)

    # References
    faq_id: str = Field(foreign_key="faq_entries.id", description="FAQ entry that was used")
    user_id: str | None = Field(default=None, foreign_key="users.id", description="User who accessed the FAQ")

    # Usage details
    used_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
        description="When FAQ was accessed",
    )
    response_variation: str = Field(sa_column=Column(Text), description="The actual response sent to user")
    from_cache: bool = Field(default=False, description="Whether variation came from cache")

    # Cost tracking
    variation_cost_euros: float = Field(default=0.0003, description="Cost of variation generation in EUR")
    variation_cost_cents: int = Field(default=3, description="Cost in 0.01 cent units (for precision)")

    # User feedback
    was_helpful: bool | None = Field(default=None, description="User feedback: was the response helpful?")
    followup_needed: bool | None = Field(default=None, description="User indicated need for followup")
    comments: str | None = Field(default=None, sa_column=Column(Text), description="User comments/feedback")
    feedback_submitted_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True)), description="When feedback was submitted"
    )


class FAQVersionHistory(SQLModel, table=True):
    """Version history for FAQ entries to track changes over time."""

    __tablename__ = "faq_version_history"

    # Primary identification
    id: str | None = Field(default_factory=lambda: str(uuid4()), primary_key=True, max_length=100)

    # References
    faq_id: str = Field(foreign_key="faq_entries.id", description="FAQ entry this version belongs to")

    # Version details
    version: int = Field(description="Version number")
    question: str = Field(sa_column=Column(Text), description="Question at this version")
    answer: str = Field(sa_column=Column(Text), description="Answer at this version")
    tags: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)), description="Tags at this version")
    regulatory_refs: dict[str, Any] = Field(
        default_factory=list, sa_column=Column(JSON), description="Regulatory references at this version"
    )

    # Change tracking
    change_reason: str | None = Field(
        default=None, sa_column=Column(Text), description="Reason for this version change"
    )
    changed_by: str | None = Field(default=None, description="User who made this change")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
        description="When this version was created",
    )


class FAQObsolescenceCheck(SQLModel, table=True):
    """Track obsolescence checks for FAQ entries against regulatory updates."""

    __tablename__ = "faq_obsolescence_checks"

    # Primary identification
    id: str | None = Field(default_factory=lambda: str(uuid4()), primary_key=True, max_length=100)

    # References
    faq_id: str = Field(foreign_key="faq_entries.id", description="FAQ entry that was checked")

    # Check results
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
        description="When obsolescence check was performed",
    )
    is_potentially_obsolete: bool = Field(default=False, description="Whether FAQ might be obsolete")
    confidence_score: float = Field(default=0.0, description="Confidence in obsolescence detection (0.0-1.0)")
    reason: str | None = Field(default=None, sa_column=Column(Text), description="Reason for potential obsolescence")

    # Affecting updates
    affecting_updates: dict[str, Any] = Field(
        default_factory=list, sa_column=Column(JSON), description="Regulatory updates that might affect this FAQ"
    )

    # Action taken
    action_taken: str | None = Field(
        default=None, description="Action taken based on check (review_flagged, auto_updated, etc.)"
    )
    reviewed_by: str | None = Field(default=None, description="Admin who reviewed the obsolescence alert")
    reviewed_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True)), description="When obsolescence alert was reviewed"
    )


class FAQCategory(SQLModel, table=True):
    """FAQ categories for organization and filtering."""

    __tablename__ = "faq_categories"

    # Primary identification
    id: int | None = Field(default=None, primary_key=True)

    # Category details
    name: str = Field(unique=True, max_length=100, description="Category identifier")
    display_name: str = Field(max_length=200, description="Human-readable category name")
    description: str | None = Field(default=None, sa_column=Column(Text), description="Category description")

    # Organization
    parent_category: str | None = Field(default=None, description="Parent category for hierarchical organization")
    sort_order: int = Field(default=0, description="Display order")

    # Statistics (updated periodically)
    faq_count: int = Field(default=0, description="Number of FAQs in this category")
    total_hits: int = Field(default=0, description="Total hits across all FAQs")
    avg_helpfulness: float | None = Field(default=None, description="Average helpfulness across category")

    # Status
    is_active: bool = Field(default=True, description="Whether category is active")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
        description="Last update timestamp",
    )


class FAQVariationCache(SQLModel, table=True):
    """Cache for GPT-3.5 generated response variations to avoid repeated LLM calls."""

    __tablename__ = "faq_variation_cache"

    # Primary identification
    id: str | None = Field(default_factory=lambda: str(uuid4()), primary_key=True, max_length=100)

    # Cache key components
    faq_id: str = Field(foreign_key="faq_entries.id", description="FAQ entry this variation is for")
    user_id: str | None = Field(
        default=None, foreign_key="users.id", description="User this variation was generated for"
    )
    cache_key: str = Field(unique=True, max_length=200, description="Unique cache key for this variation")

    # Cached content
    original_answer: str = Field(sa_column=Column(Text), description="Original FAQ answer")
    variation_text: str = Field(sa_column=Column(Text), description="Generated variation")

    # Generation details
    model_used: str = Field(default="gpt-3.5-turbo", description="LLM model used for generation")
    tokens_used: int | None = Field(default=None, description="Tokens consumed for generation")
    generation_cost_euros: float = Field(default=0.0003, description="Cost of generating this variation")

    # Cache management
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
        description="When variation was cached",
    )
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC) + datetime.timedelta(hours=24),
        sa_column=Column(DateTime(timezone=True)),
        description="When cache entry expires",
    )
    hit_count: int = Field(default=0, description="How many times this cached variation was used")
    last_used: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True)), description="Last time cached variation was accessed"
    )


class FAQAnalyticsSummary(SQLModel, table=True):
    """Aggregated analytics for FAQ system performance and cost tracking."""

    __tablename__ = "faq_analytics_summary"

    # Primary identification
    id: int | None = Field(default=None, primary_key=True)

    # Time period
    period_start: datetime = Field(sa_column=Column(DateTime(timezone=True)), description="Analytics period start")
    period_end: datetime = Field(sa_column=Column(DateTime(timezone=True)), description="Analytics period end")
    period_type: str = Field(max_length=20, description="Period type (daily, weekly, monthly)")

    # Volume metrics
    total_queries: int = Field(default=0, description="Total queries handled")
    faq_responses: int = Field(default=0, description="Responses from FAQ system")
    full_llm_responses: int = Field(default=0, description="Responses from full LLM")
    cache_hits: int = Field(default=0, description="Variation cache hits")
    cache_misses: int = Field(default=0, description="Variation cache misses")

    # Performance metrics
    avg_response_time_ms: float = Field(default=0.0, description="Average response time")
    avg_search_time_ms: float = Field(default=0.0, description="Average search time")
    cache_hit_rate: float = Field(default=0.0, description="Cache hit rate (0.0-1.0)")

    # Cost metrics
    total_variation_costs_euros: float = Field(default=0.0, description="Total variation costs")
    total_full_llm_costs_euros: float = Field(default=0.0, description="Total full LLM costs")
    cost_savings_euros: float = Field(default=0.0, description="Cost savings vs all full LLM")
    cost_savings_percent: float = Field(default=0.0, description="Cost savings percentage")

    # Quality metrics
    avg_helpfulness_score: float = Field(default=0.0, description="Average helpfulness")
    followup_rate: float = Field(default=0.0, description="Rate of followup requests")
    obsolescence_flags: int = Field(default=0, description="Number of obsolescence flags")

    # Popular content
    top_categories: dict[str, Any] = Field(
        default_factory=list, sa_column=Column(JSON), description="Most popular FAQ categories"
    )
    top_faqs: dict[str, Any] = Field(default_factory=list, sa_column=Column(JSON), description="Most accessed FAQs")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
        description="When summary was generated",
    )


# Helper functions for common operations


def generate_faq_cache_key(faq_id: str, user_id: str, context: str = "") -> str:
    """Generate cache key for FAQ variations."""
    import hashlib

    key_components = f"{faq_id}:{user_id}:{context}"
    key_hash = hashlib.md5(key_components.encode()).hexdigest()[:16]
    return f"faq_var:{key_hash}"


def calculate_cost_savings(
    total_queries: int,
    faq_responses: int,
    variation_cost_per_query: float = 0.0003,
    full_llm_cost_per_query: float = 0.002,
) -> dict[str, float]:
    """Calculate cost savings from FAQ system usage."""
    full_llm_responses = total_queries - faq_responses

    # Assume 30% of FAQ responses need variations
    variations_needed = int(faq_responses * 0.30)

    actual_costs = (variations_needed * variation_cost_per_query) + (full_llm_responses * full_llm_cost_per_query)

    hypothetical_costs = total_queries * full_llm_cost_per_query

    savings = hypothetical_costs - actual_costs
    savings_percent = (savings / hypothetical_costs) * 100 if hypothetical_costs > 0 else 0

    return {
        "actual_costs_euros": actual_costs,
        "hypothetical_costs_euros": hypothetical_costs,
        "savings_euros": savings,
        "savings_percent": savings_percent,
        "variation_costs_euros": variations_needed * variation_cost_per_query,
        "full_llm_costs_euros": full_llm_responses * full_llm_cost_per_query,
    }


def get_faq_search_vector(question: str, answer: str, tags: list[str]) -> str:
    """Generate search vector content for PostgreSQL full-text search."""
    # This would be handled by database triggers in production
    # but included here for completeness
    search_content = f"{question} {answer} {' '.join(tags)}"
    return search_content.lower()
