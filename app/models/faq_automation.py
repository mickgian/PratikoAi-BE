"""FAQ Automation Models for Automated FAQ Generation System.

This module defines database models for the automated FAQ generation system
that analyzes user queries, identifies patterns, and generates FAQs automatically.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel


class FAQGenerationStatus(Enum):
    """Status of FAQ generation process"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FAQApprovalStatus(Enum):
    """Status of FAQ approval workflow"""

    PENDING_REVIEW = "pending_review"
    AUTO_APPROVED = "auto_approved"
    MANUALLY_APPROVED = "manually_approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class RSSImpactLevel(Enum):
    """Level of RSS update impact on FAQs"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class QueryCluster(SQLModel, table=True):
    """Clusters of similar user queries identified by pattern analysis.

    Represents groups of semantically similar queries that could
    benefit from a shared FAQ answer.
    """

    __tablename__ = "query_clusters"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Core fields
    canonical_query: str = Field(max_length=500, index=True)
    normalized_form: str = Field(max_length=500, index=True)

    # Cluster statistics
    query_count: int = Field(default=0)
    first_seen: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True)
    )
    last_seen: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True)
    )

    # Cost analysis
    total_cost_cents: int = Field(default=0)
    avg_cost_cents: int = Field(default=0)
    potential_savings_cents: int = Field(default=0)

    # Quality metrics
    avg_quality_score: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(3, 2), nullable=False, default=0)
    )
    avg_response_time_ms: int = Field(default=0)

    # Pattern analysis (PostgreSQL arrays)
    query_variations: List[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String(500)), nullable=False, default=list)
    )
    semantic_tags: List[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String(50)), nullable=False, default=list)
    )
    topic_distribution: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True)
    )

    # Business metrics
    roi_score: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(10, 2), nullable=False, default=0)
    )
    priority_score: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(10, 2), nullable=False, default=0)
    )

    # Processing status
    processing_status: str = Field(max_length=20, default="discovered")
    last_analyzed: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    )

    # Relationships
    faq_candidates: List["FAQCandidate"] = Relationship(
        back_populates="query_cluster",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_query_clusters_priority", "priority_score", "roi_score"),
        Index("idx_query_clusters_cost", "potential_savings_cents", "query_count"),
        Index("idx_query_clusters_quality", "avg_quality_score", "processing_status"),
    )

    def calculate_monthly_savings(self, days_window: int = 30) -> Decimal:
        """Calculate estimated monthly savings"""
        if self.query_count == 0 or days_window == 0:
            return Decimal("0")

        monthly_queries = self.query_count * (30 / days_window)
        current_cost = monthly_queries * (self.avg_cost_cents / 100)
        faq_cost = monthly_queries * Decimal("0.0003")  # GPT-3.5 variation cost

        return max(current_cost - faq_cost, Decimal("0"))

    def update_statistics(self, new_queries: list[dict[str, Any]]):
        """Update cluster statistics with new query data"""
        if not new_queries:
            return

        # Update counts
        self.query_count += len(new_queries)

        # Update costs
        new_total_cost = sum(q.get("cost_cents", 0) for q in new_queries)
        self.total_cost_cents += new_total_cost
        self.avg_cost_cents = self.total_cost_cents // self.query_count

        # Update quality metrics
        quality_scores = [q.get("quality_score", 0) for q in new_queries if q.get("quality_score")]
        if quality_scores:
            all_quality = [float(self.avg_quality_score)] * (self.query_count - len(new_queries))
            all_quality.extend(quality_scores)
            self.avg_quality_score = Decimal(str(sum(all_quality) / len(all_quality)))

        # Update potential savings
        self.potential_savings_cents = int(self.calculate_monthly_savings() * 100)

        # Update timestamps
        timestamps = [q.get("timestamp") for q in new_queries if q.get("timestamp")]
        if timestamps:
            self.last_seen = max(timestamps)

    def to_dict(self):
        return {
            "id": str(self.id),
            "canonical_query": self.canonical_query,
            "normalized_form": self.normalized_form,
            "query_count": self.query_count,
            "query_variations": self.query_variations[:10],  # Limit variations
            "semantic_tags": self.semantic_tags,
            "avg_cost_cents": self.avg_cost_cents,
            "potential_savings_cents": self.potential_savings_cents,
            "avg_quality_score": float(self.avg_quality_score),
            "roi_score": float(self.roi_score),
            "priority_score": float(self.priority_score),
            "processing_status": self.processing_status,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
        }


class FAQCandidate(SQLModel, table=True):
    """FAQ candidates generated from query cluster analysis.

    Represents potential FAQs that have been identified through
    query pattern analysis and cost-benefit evaluation.
    """

    __tablename__ = "faq_candidates"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign keys
    cluster_id: UUID = Field(foreign_key="query_clusters.id")

    # FAQ content preparation
    suggested_question: str = Field(sa_column=Column(Text, nullable=False))
    best_response_content: str = Field(sa_column=Column(Text, nullable=False))
    best_response_id: Optional[UUID] = Field(default=None)  # Reference to original query

    # Classification and tagging
    suggested_category: Optional[str] = Field(default=None, max_length=100)
    suggested_tags: List[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String(50)), default=list)
    )
    regulatory_references: List[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String(200)), default=list)
    )

    # Business case
    frequency: int
    estimated_monthly_savings: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(10, 2), nullable=False, default=0)
    )
    roi_score: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(10, 2), nullable=False, default=0)
    )
    priority_score: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(10, 2), nullable=False, default=0)
    )

    # Generation parameters
    generation_prompt: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    generation_model_suggested: str = Field(max_length=50, default="gpt-3.5-turbo")
    quality_threshold: Decimal = Field(
        default=Decimal("0.85"),
        sa_column=Column(Numeric(3, 2), default=0.85)
    )

    # Status and workflow
    status: str = Field(max_length=30, default="pending")
    generation_attempts: int = Field(default=0)
    max_generation_attempts: int = Field(default=3)

    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    # Processing metadata
    analysis_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True)
    )
    generation_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True)
    )

    # Relationships
    query_cluster: "QueryCluster" = Relationship(back_populates="faq_candidates")
    generated_faqs: List["GeneratedFAQ"] = Relationship(
        back_populates="candidate",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    # Constraints and indexes
    __table_args__ = (
        Index("idx_faq_candidates_priority", "priority_score", "status"),
        Index("idx_faq_candidates_roi", "roi_score", "estimated_monthly_savings"),
        Index("idx_faq_candidates_status", "status", "created_at"),
    )

    def can_generate(self) -> bool:
        """Check if candidate can be processed for generation"""
        return (
            self.status == "pending"
            and self.generation_attempts < self.max_generation_attempts
            and (not self.expires_at or self.expires_at > datetime.utcnow())
        )

    def calculate_priority(self) -> Decimal:
        """Calculate generation priority score"""
        # Priority = ROI × frequency × quality × urgency_factor
        urgency_factor = 1.0
        if self.expires_at:
            days_until_expiry = (self.expires_at - datetime.utcnow()).days
            urgency_factor = max(0.1, 1.0 - (days_until_expiry / 30))

        priority = float(self.roi_score) * self.frequency * urgency_factor

        return Decimal(str(priority))

    def to_dict(self):
        return {
            "id": str(self.id),
            "cluster_id": str(self.cluster_id),
            "suggested_question": self.suggested_question,
            "suggested_category": self.suggested_category,
            "suggested_tags": self.suggested_tags,
            "frequency": self.frequency,
            "estimated_monthly_savings": float(self.estimated_monthly_savings),
            "roi_score": float(self.roi_score),
            "priority_score": float(self.priority_score),
            "status": self.status,
            "generation_attempts": self.generation_attempts,
            "can_generate": self.can_generate(),
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class GeneratedFAQ(SQLModel, table=True):
    """FAQs generated by the automated system.

    Stores FAQs created through automated analysis and generation,
    including quality metrics and approval workflow status.
    """

    __tablename__ = "generated_faqs"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign keys
    candidate_id: UUID = Field(foreign_key="faq_candidates.id")

    # FAQ content
    question: str = Field(sa_column=Column(Text, nullable=False))
    answer: str = Field(sa_column=Column(Text, nullable=False))
    category: Optional[str] = Field(default=None, max_length=100)
    tags: List[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String(50)), default=list)
    )

    # Quality and validation
    quality_score: Decimal = Field(
        sa_column=Column(Numeric(3, 2), nullable=False)
    )
    quality_details: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True)
    )
    validation_notes: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    # Legal and regulatory
    regulatory_refs: List[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String(200)), default=list)
    )
    legal_review_required: bool = Field(default=False)
    compliance_notes: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    # Generation details
    generation_model: str = Field(max_length=50)
    generation_cost_cents: int = Field(default=0)
    generation_tokens: Optional[int] = Field(default=None)
    generation_time_ms: Optional[int] = Field(default=None)

    # Business metrics
    estimated_monthly_savings: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(10, 2), nullable=False, default=0)
    )
    source_query_count: int = Field(default=0)

    # Approval workflow
    approval_status: str = Field(max_length=30, default="pending_review")
    approved_by: Optional[int] = Field(default=None, foreign_key="user.id")
    approved_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    rejection_reason: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    # Publishing
    published: bool = Field(default=False)
    published_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    faq_id: Optional[str] = Field(default=None, max_length=100, foreign_key="faq_entries.id")  # Link to published FAQ

    # Performance tracking
    view_count: int = Field(default=0)
    usage_count: int = Field(default=0)
    satisfaction_score: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(3, 2), nullable=True)
    )
    feedback_count: int = Field(default=0)

    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    )

    # Generation metadata
    generation_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True)
    )
    auto_generated: bool = Field(default=True)

    # Relationships
    candidate: "FAQCandidate" = Relationship(back_populates="generated_faqs")
    rss_impacts: List["RSSFAQImpact"] = Relationship(
        back_populates="faq",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    # Indexes
    __table_args__ = (
        Index("idx_generated_faqs_approval", "approval_status", "created_at"),
        Index("idx_generated_faqs_quality", "quality_score", "approval_status"),
        Index("idx_generated_faqs_performance", "usage_count", "satisfaction_score"),
        UniqueConstraint("candidate_id", "question", name="uq_candidate_question"),
    )

    def should_auto_approve(self) -> bool:
        """Determine if FAQ should be auto-approved based on quality"""
        return (
            self.quality_score >= Decimal("0.95")
            and self.source_query_count >= 10
            and not self.legal_review_required
            and self.estimated_monthly_savings >= Decimal("5.0")
        )

    def calculate_impact_score(self) -> Decimal:
        """Calculate potential impact score"""
        quality_factor = float(self.quality_score)
        usage_factor = min(self.source_query_count / 10.0, 2.0)  # Cap at 2x
        savings_factor = min(float(self.estimated_monthly_savings) / 10.0, 3.0)  # Cap at 3x

        return Decimal(str(quality_factor * usage_factor * savings_factor))

    def to_dict(self):
        return {
            "id": str(self.id),
            "candidate_id": str(self.candidate_id),
            "question": self.question,
            "answer": self.answer,
            "category": self.category,
            "tags": self.tags,
            "quality_score": float(self.quality_score),
            "regulatory_refs": self.regulatory_refs,
            "generation_model": self.generation_model,
            "generation_cost_cents": self.generation_cost_cents,
            "estimated_monthly_savings": float(self.estimated_monthly_savings),
            "approval_status": self.approval_status,
            "published": self.published,
            "auto_generated": self.auto_generated,
            "view_count": self.view_count,
            "usage_count": self.usage_count,
            "satisfaction_score": float(self.satisfaction_score) if self.satisfaction_score else None,
            "created_at": self.created_at.isoformat(),
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }


class RSSFAQImpact(SQLModel, table=True):
    """Tracking of RSS updates that impact existing FAQs.

    Records when RSS feed updates potentially affect FAQ accuracy
    and triggers for regeneration or review.
    """

    __tablename__ = "rss_faq_impacts"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign keys
    faq_id: UUID = Field(foreign_key="generated_faqs.id")
    rss_update_id: UUID  # External RSS ID

    # Impact assessment
    impact_level: str = Field(max_length=20)  # low, medium, high, critical
    impact_score: Decimal = Field(
        sa_column=Column(Numeric(3, 2), nullable=False)
    )
    confidence_score: Decimal = Field(
        sa_column=Column(Numeric(3, 2), nullable=False)
    )

    # RSS update details
    rss_source: str = Field(max_length=200)
    rss_title: str = Field(sa_column=Column(Text, nullable=False))
    rss_summary: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    rss_published_date: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    rss_url: Optional[str] = Field(default=None, max_length=500)

    # Matching details
    matching_tags: List[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String(50)), default=list)
    )
    matching_keywords: List[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String(100)), default=list)
    )
    regulatory_changes: List[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String(200)), default=list)
    )

    # Action taken
    action_required: str = Field(max_length=50)  # review, regenerate, ignore
    action_taken: Optional[str] = Field(default=None, max_length=50)
    action_date: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    action_by: Optional[int] = Field(default=None, foreign_key="user.id")

    # Processing status
    processed: bool = Field(default=False)
    processing_notes: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    )

    # Analysis metadata
    analysis_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True)
    )

    # Relationships
    faq: "GeneratedFAQ" = Relationship(back_populates="rss_impacts")

    # Indexes
    __table_args__ = (
        Index("idx_rss_impacts_priority", "impact_level", "action_required", "processed"),
        Index("idx_rss_impacts_date", "rss_published_date", "created_at"),
        Index("idx_rss_impacts_faq", "faq_id", "impact_level"),
    )

    def requires_immediate_action(self) -> bool:
        """Check if impact requires immediate action"""
        return (
            self.impact_level in ["high", "critical"]
            and not self.processed
            and self.confidence_score >= Decimal("0.8")
        )

    def calculate_urgency_score(self) -> Decimal:
        """Calculate urgency of action needed"""
        impact_weights = {"low": 0.2, "medium": 0.5, "high": 0.8, "critical": 1.0}

        impact_weight = impact_weights.get(self.impact_level, 0.2)
        confidence_weight = float(self.confidence_score)

        # Time decay - more urgent if RSS update is recent
        hours_since_update = (datetime.utcnow() - self.rss_published_date).total_seconds() / 3600
        time_factor = max(0.1, 1.0 - (hours_since_update / 72))  # Decay over 72 hours

        return Decimal(str(impact_weight * confidence_weight * time_factor))

    def to_dict(self):
        return {
            "id": str(self.id),
            "faq_id": str(self.faq_id),
            "rss_update_id": str(self.rss_update_id),
            "impact_level": self.impact_level,
            "impact_score": float(self.impact_score),
            "confidence_score": float(self.confidence_score),
            "rss_source": self.rss_source,
            "rss_title": self.rss_title,
            "rss_published_date": self.rss_published_date.isoformat(),
            "matching_tags": self.matching_tags,
            "regulatory_changes": self.regulatory_changes,
            "action_required": self.action_required,
            "action_taken": self.action_taken,
            "processed": self.processed,
            "requires_immediate_action": self.requires_immediate_action(),
            "urgency_score": float(self.calculate_urgency_score()),
            "created_at": self.created_at.isoformat(),
        }


class FAQGenerationJob(SQLModel, table=True):
    """Background jobs for FAQ generation processing.

    Tracks asynchronous FAQ generation jobs including batch processing,
    RSS-triggered updates, and scheduled analysis runs.
    """

    __tablename__ = "faq_generation_jobs"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Core fields
    job_type: str = Field(max_length=50)  # analysis, generation, rss_update, batch
    job_name: str = Field(max_length=200)

    # Job parameters
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, default=dict)
    )
    priority: int = Field(default=5)  # 1-10, higher = more important

    # Processing status
    status: str = Field(max_length=30, default="pending")
    progress_percentage: int = Field(default=0)
    progress_description: Optional[str] = Field(default=None, max_length=200)

    # Execution details
    started_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    execution_time_seconds: Optional[int] = Field(default=None)

    # Results and metrics
    items_processed: int = Field(default=0)
    items_successful: int = Field(default=0)
    items_failed: int = Field(default=0)
    total_cost_cents: int = Field(default=0)

    # Error handling
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)

    # Results
    result_data: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True)
    )
    output_references: List[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String(100)), default=list)
    )

    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    )
    created_by: Optional[int] = Field(default=None, foreign_key="user.id")

    # Background job ID (Celery task ID)
    celery_task_id: Optional[str] = Field(default=None, max_length=100, index=True)

    # Indexes
    __table_args__ = (
        Index("idx_faq_jobs_status", "status", "priority", "created_at"),
        Index("idx_faq_jobs_type", "job_type", "status"),
        Index("idx_faq_jobs_celery", "celery_task_id"),
    )

    def can_retry(self) -> bool:
        """Check if job can be retried"""
        return self.status == "failed" and self.retry_count < self.max_retries

    def calculate_success_rate(self) -> Decimal:
        """Calculate job success rate"""
        if self.items_processed == 0:
            return Decimal("0")

        return Decimal(str(self.items_successful / self.items_processed))

    def to_dict(self):
        return {
            "id": str(self.id),
            "job_type": self.job_type,
            "job_name": self.job_name,
            "status": self.status,
            "progress_percentage": self.progress_percentage,
            "progress_description": self.progress_description,
            "items_processed": self.items_processed,
            "items_successful": self.items_successful,
            "items_failed": self.items_failed,
            "success_rate": float(self.calculate_success_rate()),
            "total_cost_cents": self.total_cost_cents,
            "execution_time_seconds": self.execution_time_seconds,
            "retry_count": self.retry_count,
            "can_retry": self.can_retry(),
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


# Configuration and Constants

FAQ_AUTOMATION_CONFIG = {
    "pattern_analysis": {
        "min_frequency": 5,
        "time_window_days": 30,
        "similarity_threshold": 0.85,
        "min_quality_score": 0.8,
    },
    "generation": {
        "quality_threshold": 0.85,
        "auto_approve_threshold": 0.95,
        "max_generation_attempts": 3,
        "cheap_model": "gpt-3.5-turbo",
        "expensive_model": "gpt-4",
        "max_tokens": 500,
    },
    "rss_integration": {
        "high_impact_threshold": 0.7,
        "medium_impact_threshold": 0.3,
        "update_check_hours": 4,
        "max_updates_per_batch": 50,
    },
    "business_rules": {
        "min_roi_score": 0.5,
        "max_candidates_per_run": 20,
        "candidate_expiry_days": 7,
        "min_monthly_savings": 1.0,
    },
}


# Helper Functions


def calculate_faq_priority(
    frequency: int, avg_cost_cents: int, quality_score: float, time_factor: float = 1.0
) -> Decimal:
    """Calculate FAQ generation priority score"""
    monthly_savings = frequency * (avg_cost_cents / 100 - 0.0003) * time_factor
    quality_factor = min(quality_score / 0.85, 1.2)  # Bonus for high quality

    return Decimal(str(monthly_savings * quality_factor * frequency))


def estimate_generation_cost(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    """Estimate cost of FAQ generation"""
    pricing = {
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},  # per 1K tokens
        "gpt-4": {"input": 0.03, "output": 0.06},
    }

    if model not in pricing:
        model = "gpt-3.5-turbo"  # Default

    input_cost = (input_tokens / 1000) * pricing[model]["input"]
    output_cost = (output_tokens / 1000) * pricing[model]["output"]

    return Decimal(str(input_cost + output_cost))
