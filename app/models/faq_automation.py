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
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.ccnl_database import Base


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


class QueryCluster(Base):
    """Clusters of similar user queries identified by pattern analysis.

    Represents groups of semantically similar queries that could
    benefit from a shared FAQ answer.
    """

    __tablename__ = "query_clusters"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    canonical_query = Column(String(500), nullable=False, index=True)
    normalized_form = Column(String(500), nullable=False, index=True)

    # Cluster statistics
    query_count = Column(Integer, nullable=False, default=0)
    first_seen = Column(DateTime(timezone=True), nullable=False, index=True)
    last_seen = Column(DateTime(timezone=True), nullable=False, index=True)

    # Cost analysis
    total_cost_cents = Column(Integer, nullable=False, default=0)
    avg_cost_cents = Column(Integer, nullable=False, default=0)
    potential_savings_cents = Column(Integer, nullable=False, default=0)

    # Quality metrics
    avg_quality_score = Column(Numeric(3, 2), nullable=False, default=0)
    avg_response_time_ms = Column(Integer, nullable=False, default=0)

    # Pattern analysis
    query_variations = Column(ARRAY(String(500)), nullable=False, default=list)
    semantic_tags = Column(ARRAY(String(50)), nullable=False, default=list)
    topic_distribution = Column(JSONB)  # Distribution of topics in cluster

    # Business metrics
    roi_score = Column(Numeric(10, 2), nullable=False, default=0)
    priority_score = Column(Numeric(10, 2), nullable=False, default=0)

    # Processing status
    processing_status = Column(String(20), nullable=False, default="discovered")
    last_analyzed = Column(DateTime(timezone=True), server_default=func.now())

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    faq_candidates = relationship("FAQCandidate", back_populates="query_cluster", cascade="all, delete-orphan")

    # Indexes for performance
    __table_args__ = (
        Index("idx_query_clusters_priority", "priority_score", "roi_score"),
        Index("idx_query_clusters_cost", "potential_savings_cents", "query_count"),
        Index("idx_query_clusters_quality", "avg_quality_score", "processing_status"),
    )

    def __repr__(self):
        return f"<QueryCluster(canonical='{self.canonical_query[:50]}...', count={self.query_count})>"

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


class FAQCandidate(Base):
    """FAQ candidates generated from query cluster analysis.

    Represents potential FAQs that have been identified through
    query pattern analysis and cost-benefit evaluation.
    """

    __tablename__ = "faq_candidates"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    cluster_id = Column(PG_UUID(as_uuid=True), ForeignKey("query_clusters.id"), nullable=False)

    # FAQ content preparation
    suggested_question = Column(Text, nullable=False)
    best_response_content = Column(Text, nullable=False)
    best_response_id = Column(PG_UUID(as_uuid=True))  # Reference to original query

    # Classification and tagging
    suggested_category = Column(String(100))
    suggested_tags = Column(ARRAY(String(50)), default=list)
    regulatory_references = Column(ARRAY(String(200)), default=list)

    # Business case
    frequency = Column(Integer, nullable=False)
    estimated_monthly_savings = Column(Numeric(10, 2), nullable=False, default=0)
    roi_score = Column(Numeric(10, 2), nullable=False, default=0)
    priority_score = Column(Numeric(10, 2), nullable=False, default=0)

    # Generation parameters
    generation_prompt = Column(Text)
    generation_model_suggested = Column(String(50), default="gpt-3.5-turbo")
    quality_threshold = Column(Numeric(3, 2), default=0.85)

    # Status and workflow
    status = Column(String(30), nullable=False, default="pending")
    generation_attempts = Column(Integer, nullable=False, default=0)
    max_generation_attempts = Column(Integer, nullable=False, default=3)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True))  # Candidate expiry

    # Processing metadata
    analysis_metadata = Column(JSONB)  # Analysis details
    generation_metadata = Column(JSONB)  # Generation parameters

    # Relationships
    query_cluster = relationship("QueryCluster", back_populates="faq_candidates")
    generated_faqs = relationship("GeneratedFAQ", back_populates="candidate", cascade="all, delete-orphan")

    # Constraints and indexes
    __table_args__ = (
        Index("idx_faq_candidates_priority", "priority_score", "status"),
        Index("idx_faq_candidates_roi", "roi_score", "estimated_monthly_savings"),
        Index("idx_faq_candidates_status", "status", "created_at"),
    )

    def __repr__(self):
        return f"<FAQCandidate(question='{self.suggested_question[:50]}...', roi={self.roi_score})>"

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


class GeneratedFAQ(Base):
    """FAQs generated by the automated system.

    Stores FAQs created through automated analysis and generation,
    including quality metrics and approval workflow status.
    """

    __tablename__ = "generated_faqs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    candidate_id = Column(PG_UUID(as_uuid=True), ForeignKey("faq_candidates.id"), nullable=False)

    # FAQ content
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(100))
    tags = Column(ARRAY(String(50)), default=list)

    # Quality and validation
    quality_score = Column(Numeric(3, 2), nullable=False)
    quality_details = Column(JSONB)  # Detailed quality metrics
    validation_notes = Column(Text)

    # Legal and regulatory
    regulatory_refs = Column(ARRAY(String(200)), default=list)
    legal_review_required = Column(Boolean, default=False)
    compliance_notes = Column(Text)

    # Generation details
    generation_model = Column(String(50), nullable=False)
    generation_cost_cents = Column(Integer, nullable=False, default=0)
    generation_tokens = Column(Integer)
    generation_time_ms = Column(Integer)

    # Business metrics
    estimated_monthly_savings = Column(Numeric(10, 2), nullable=False, default=0)
    source_query_count = Column(Integer, nullable=False, default=0)

    # Approval workflow
    approval_status = Column(String(30), nullable=False, default="pending_review")
    approved_by = Column(PG_UUID(as_uuid=True), ForeignKey("user.id"))
    approved_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)

    # Publishing
    published = Column(Boolean, default=False)
    published_at = Column(DateTime(timezone=True))
    faq_id = Column(PG_UUID(as_uuid=True), ForeignKey("faq_entries.id"))  # Link to published FAQ

    # Performance tracking
    view_count = Column(Integer, default=0)
    usage_count = Column(Integer, default=0)
    satisfaction_score = Column(Numeric(3, 2))
    feedback_count = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Generation metadata
    generation_metadata = Column(JSONB)  # Full generation details
    auto_generated = Column(Boolean, default=True)

    # Relationships
    candidate = relationship("FAQCandidate", back_populates="generated_faqs")
    # Note: No relationship to User model - it uses SQLModel which is incompatible
    # with SQLAlchemy relationships. Access user via approved_by foreign key instead.
    # Note: No relationship to FAQ/FAQEntry model - it uses SQLModel which is incompatible
    # with SQLAlchemy relationships. Access FAQ via faq_id foreign key instead.
    rss_impacts = relationship("RSSFAQImpact", back_populates="faq", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_generated_faqs_approval", "approval_status", "created_at"),
        Index("idx_generated_faqs_quality", "quality_score", "approval_status"),
        Index("idx_generated_faqs_performance", "usage_count", "satisfaction_score"),
        UniqueConstraint("candidate_id", "question", name="uq_candidate_question"),
    )

    def __repr__(self):
        return f"<GeneratedFAQ(question='{self.question[:50]}...', quality={self.quality_score})>"

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


class RSSFAQImpact(Base):
    """Tracking of RSS updates that impact existing FAQs.

    Records when RSS feed updates potentially affect FAQ accuracy
    and triggers for regeneration or review.
    """

    __tablename__ = "rss_faq_impacts"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    faq_id = Column(PG_UUID(as_uuid=True), ForeignKey("generated_faqs.id"), nullable=False)
    rss_update_id = Column(PG_UUID(as_uuid=True), nullable=False)  # External RSS ID

    # Impact assessment
    impact_level = Column(String(20), nullable=False)  # low, medium, high, critical
    impact_score = Column(Numeric(3, 2), nullable=False)
    confidence_score = Column(Numeric(3, 2), nullable=False)

    # RSS update details
    rss_source = Column(String(200), nullable=False)
    rss_title = Column(Text, nullable=False)
    rss_summary = Column(Text)
    rss_published_date = Column(DateTime(timezone=True), nullable=False)
    rss_url = Column(String(500))

    # Matching details
    matching_tags = Column(ARRAY(String(50)), default=list)
    matching_keywords = Column(ARRAY(String(100)), default=list)
    regulatory_changes = Column(ARRAY(String(200)), default=list)

    # Action taken
    action_required = Column(String(50), nullable=False)  # review, regenerate, ignore
    action_taken = Column(String(50))
    action_date = Column(DateTime(timezone=True))
    action_by = Column(PG_UUID(as_uuid=True), ForeignKey("user.id"))

    # Processing status
    processed = Column(Boolean, default=False)
    processing_notes = Column(Text)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Analysis metadata
    analysis_metadata = Column(JSONB)  # Detailed analysis data

    # Relationships
    faq = relationship("GeneratedFAQ", back_populates="rss_impacts")
    # Note: No relationship to User model - it uses SQLModel which is incompatible
    # with SQLAlchemy relationships. Access user via action_by foreign key instead.

    # Indexes
    __table_args__ = (
        Index("idx_rss_impacts_priority", "impact_level", "action_required", "processed"),
        Index("idx_rss_impacts_date", "rss_published_date", "created_at"),
        Index("idx_rss_impacts_faq", "faq_id", "impact_level"),
    )

    def __repr__(self):
        return f"<RSSFAQImpact(faq_id='{self.faq_id}', impact='{self.impact_level}')>"

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


class FAQGenerationJob(Base):
    """Background jobs for FAQ generation processing.

    Tracks asynchronous FAQ generation jobs including batch processing,
    RSS-triggered updates, and scheduled analysis runs.
    """

    __tablename__ = "faq_generation_jobs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_type = Column(String(50), nullable=False)  # analysis, generation, rss_update, batch
    job_name = Column(String(200), nullable=False)

    # Job parameters
    parameters = Column(JSONB, nullable=False, default=dict)
    priority = Column(Integer, nullable=False, default=5)  # 1-10, higher = more important

    # Processing status
    status = Column(String(30), nullable=False, default="pending")
    progress_percentage = Column(Integer, default=0)
    progress_description = Column(String(200))

    # Execution details
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    execution_time_seconds = Column(Integer)

    # Results and metrics
    items_processed = Column(Integer, default=0)
    items_successful = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    total_cost_cents = Column(Integer, default=0)

    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Results
    result_data = Column(JSONB)  # Job results and summary
    output_references = Column(ARRAY(String(100)), default=list)  # Generated FAQ IDs, etc.

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("user.id"))

    # Background job ID (Celery task ID)
    celery_task_id = Column(String(100), index=True)

    # Relationships
    # Note: No relationship to User model - it uses SQLModel which is incompatible
    # with SQLAlchemy relationships. Access user via created_by foreign key instead.

    # Indexes
    __table_args__ = (
        Index("idx_faq_jobs_status", "status", "priority", "created_at"),
        Index("idx_faq_jobs_type", "job_type", "status"),
        Index("idx_faq_jobs_celery", "celery_task_id"),
    )

    def __repr__(self):
        return f"<FAQGenerationJob(type='{self.job_type}', status='{self.status}')>"

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
