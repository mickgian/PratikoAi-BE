"""Database Models for Quality Analysis System with Expert Feedback Loop.

Defines all database models needed for:
- Expert feedback collection
- Failure pattern tracking
- Quality metrics
- Improvement tracking
- Expert validation workflow
"""

import enum
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.ccnl_database import Base


class FeedbackType(enum.Enum):
    """Types of expert feedback"""

    CORRECT = "correct"  # ✅ Correct
    INCOMPLETE = "incomplete"  # ⚠️ Incomplete
    INCORRECT = "incorrect"  # ❌ Incorrect


class ItalianFeedbackCategory(enum.Enum):
    """Italian feedback categories for tax professionals"""

    NORMATIVA_OBSOLETA = "normativa_obsoleta"  # Outdated regulation
    INTERPRETAZIONE_ERRATA = "interpretazione_errata"  # Wrong interpretation
    CASO_MANCANTE = "caso_mancante"  # Missing case
    CALCOLO_SBAGLIATO = "calcolo_sbagliato"  # Wrong calculation
    TROPPO_GENERICO = "troppo_generico"  # Too generic


class ExpertCredentialType(enum.Enum):
    """Types of expert credentials"""

    DOTTORE_COMMERCIALISTA = "dottore_commercialista"
    REVISORE_LEGALE = "revisore_legale"
    CONSULENTE_FISCALE = "consulente_fiscale"
    CONSULENTE_LAVORO = "consulente_lavoro"
    CAF_OPERATOR = "caf_operator"


class ImprovementStatus(enum.Enum):
    """Status of improvement implementations"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ExpertProfile(Base):
    """Expert profiles for validation and trust scoring"""

    __tablename__ = "expert_profiles"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Professional credentials
    credentials: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    credential_types: Mapped[list[ExpertCredentialType]] = mapped_column(
        ARRAY(Enum(ExpertCredentialType)), default=list
    )
    experience_years: Mapped[int] = mapped_column(Integer, default=0)
    specializations: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # Performance metrics
    feedback_count: Mapped[int] = mapped_column(Integer, default=0)
    feedback_accuracy_rate: Mapped[float] = mapped_column(Float, default=0.0)
    average_response_time_seconds: Mapped[int] = mapped_column(Integer, default=0)
    trust_score: Mapped[float] = mapped_column(Float, default=0.5)

    # Professional information
    professional_registration_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    organization: Mapped[str | None] = mapped_column(String(200), nullable=True)
    location_city: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Status and verification
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    expert_feedback: Mapped[list["ExpertFeedback"]] = relationship("ExpertFeedback", back_populates="expert")

    __table_args__ = (
        Index("idx_expert_profiles_trust_score", "trust_score"),
        Index("idx_expert_profiles_specializations", "specializations"),
        Index("idx_expert_profiles_active", "is_active", "is_verified"),
        CheckConstraint("trust_score >= 0.0 AND trust_score <= 1.0", name="trust_score_range"),
        CheckConstraint("feedback_accuracy_rate >= 0.0 AND feedback_accuracy_rate <= 1.0", name="accuracy_rate_range"),
    )


class ExpertFeedback(Base):
    """Expert feedback on AI-generated answers"""

    __tablename__ = "expert_feedback"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    query_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    expert_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("expert_profiles.id"), nullable=False
    )

    # Feedback details
    feedback_type: Mapped[FeedbackType] = mapped_column(Enum(FeedbackType), nullable=False)
    category: Mapped[ItalianFeedbackCategory | None] = mapped_column(Enum(ItalianFeedbackCategory), nullable=True)

    # Original content
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    original_answer: Mapped[str] = mapped_column(Text, nullable=False)

    # Expert input
    expert_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    improvement_suggestions: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    regulatory_references: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # Quality metrics
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    complexity_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5 scale

    # Processing metadata
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feedback_timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # System response
    action_taken: Mapped[str | None] = mapped_column(String(100), nullable=True)
    improvement_applied: Mapped[bool] = mapped_column(Boolean, default=False)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    expert: Mapped["ExpertProfile"] = relationship("ExpertProfile", back_populates="expert_feedback")

    __table_args__ = (
        Index("idx_expert_feedback_query_id", "query_id"),
        Index("idx_expert_feedback_expert_id", "expert_id"),
        Index("idx_expert_feedback_type_category", "feedback_type", "category"),
        Index("idx_expert_feedback_timestamp", "feedback_timestamp"),
        CheckConstraint("confidence_score >= 0.0 AND confidence_score <= 1.0", name="confidence_score_range"),
        CheckConstraint("complexity_rating >= 1 AND complexity_rating <= 5", name="complexity_rating_range"),
        CheckConstraint("time_spent_seconds > 0", name="positive_time_spent"),
    )


class PromptTemplate(Base):
    """Advanced prompt templates with structured reasoning"""

    __tablename__ = "prompt_templates"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")

    # Template content
    template_text: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Categorization
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    specialization_areas: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    complexity_level: Mapped[str] = mapped_column(String(20), default="medium")  # basic, medium, advanced

    # Quality metrics
    clarity_score: Mapped[float] = mapped_column(Float, default=0.0)
    completeness_score: Mapped[float] = mapped_column(Float, default=0.0)
    accuracy_score: Mapped[float] = mapped_column(Float, default=0.0)
    overall_quality_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Usage tracking
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0)
    average_user_rating: Mapped[float] = mapped_column(Float, default=0.0)

    # A/B testing
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    variant_group: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Metadata
    created_by: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_prompt_templates_category", "category"),
        Index("idx_prompt_templates_active", "is_active"),
        Index("idx_prompt_templates_quality", "overall_quality_score"),
        Index("idx_prompt_templates_usage", "usage_count"),
        CheckConstraint("clarity_score >= 0.0 AND clarity_score <= 1.0", name="clarity_score_range"),
        CheckConstraint("completeness_score >= 0.0 AND completeness_score <= 1.0", name="completeness_score_range"),
        CheckConstraint("accuracy_score >= 0.0 AND accuracy_score <= 1.0", name="accuracy_score_range"),
        CheckConstraint(
            "overall_quality_score >= 0.0 AND overall_quality_score <= 1.0", name="overall_quality_score_range"
        ),
        CheckConstraint("success_rate >= 0.0 AND success_rate <= 1.0", name="success_rate_range"),
    )


class FailurePattern(Base):
    """Identified patterns in system failures"""

    __tablename__ = "failure_patterns"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    pattern_name: Mapped[str] = mapped_column(String(200), nullable=False)
    pattern_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Pattern characteristics
    description: Mapped[str] = mapped_column(Text, nullable=False)
    categories: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    example_queries: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)

    # Frequency and impact
    frequency_count: Mapped[int] = mapped_column(Integer, default=0)
    impact_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Analysis metadata
    detection_algorithm: Mapped[str] = mapped_column(String(100), default="manual")
    cluster_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Temporal tracking
    first_detected: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_occurrence: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Resolution tracking
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolution_method: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_failure_patterns_type", "pattern_type"),
        Index("idx_failure_patterns_impact", "impact_score"),
        Index("idx_failure_patterns_frequency", "frequency_count"),
        Index("idx_failure_patterns_resolved", "is_resolved"),
        CheckConstraint("impact_score >= 0.0 AND impact_score <= 1.0", name="impact_score_range"),
        CheckConstraint("confidence_score >= 0.0 AND confidence_score <= 1.0", name="confidence_score_range"),
        CheckConstraint("frequency_count >= 0", name="non_negative_frequency"),
    )


class SystemImprovement(Base):
    """Tracking of system improvements and their outcomes"""

    __tablename__ = "system_improvements"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    improvement_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Improvement details
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)

    # Source and reasoning
    trigger_pattern_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("failure_patterns.id"), nullable=True
    )
    expert_feedback_ids: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    justification: Mapped[str] = mapped_column(Text, nullable=False)

    # Implementation
    implementation_details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[ImprovementStatus] = mapped_column(Enum(ImprovementStatus), default=ImprovementStatus.PENDING)

    # Impact measurement
    target_metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    baseline_metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    actual_metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Confidence and priority
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    priority_score: Mapped[float] = mapped_column(Float, default=0.5)
    estimated_impact: Mapped[float] = mapped_column(Float, default=0.0)

    # Timeline
    planned_start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    planned_completion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_completion_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Approval workflow
    requires_expert_validation: Mapped[bool] = mapped_column(Boolean, default=False)
    expert_approved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    approving_expert_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    approval_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Metadata
    created_by: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_system_improvements_type", "improvement_type"),
        Index("idx_system_improvements_status", "status"),
        Index("idx_system_improvements_priority", "priority_score"),
        Index("idx_system_improvements_pattern", "trigger_pattern_id"),
        CheckConstraint("confidence_score >= 0.0 AND confidence_score <= 1.0", name="improvement_confidence_range"),
        CheckConstraint("priority_score >= 0.0 AND priority_score <= 1.0", name="priority_score_range"),
        CheckConstraint("estimated_impact >= 0.0 AND estimated_impact <= 1.0", name="estimated_impact_range"),
    )


class QualityMetric(Base):
    """Quality metrics tracking over time"""

    __tablename__ = "quality_metrics"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_category: Mapped[str] = mapped_column(String(100), nullable=False)

    # Metric value and context
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    metric_unit: Mapped[str] = mapped_column(String(50), default="score")
    measurement_period: Mapped[str] = mapped_column(String(50), default="daily")

    # Contextualization
    query_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    expert_specialization: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_segment: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Sample size and confidence
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    confidence_interval: Mapped[float | None] = mapped_column(Float, nullable=True)
    standard_deviation: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Benchmarking
    baseline_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    benchmark_percentile: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Temporal tracking
    measurement_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    measurement_window_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    measurement_window_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Metadata
    calculated_by: Mapped[str] = mapped_column(String(100), default="system")
    calculation_method: Mapped[str | None] = mapped_column(String(200), nullable=True)
    data_sources: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_quality_metrics_name_date", "metric_name", "measurement_date"),
        Index("idx_quality_metrics_category", "metric_category"),
        Index("idx_quality_metrics_period", "measurement_period", "measurement_date"),
        CheckConstraint("sample_size >= 0", name="non_negative_sample_size"),
    )


class ExpertValidation(Base):
    """Expert validation records for complex queries"""

    __tablename__ = "expert_validations"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    query_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)

    # Validation request
    validation_type: Mapped[str] = mapped_column(String(100), nullable=False)  # consensus, single_expert, automated
    complexity_level: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5 scale
    specialization_required: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # Expert assignments
    assigned_experts: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    completed_validations: Mapped[int] = mapped_column(Integer, default=0)
    required_validations: Mapped[int] = mapped_column(Integer, default=1)

    # Consensus tracking
    consensus_reached: Mapped[bool] = mapped_column(Boolean, default=False)
    consensus_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    disagreement_areas: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # Final outcome
    validated_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    regulatory_confirmations: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # Quality assurance
    final_confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    expert_agreement_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Timeline
    requested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    target_completion: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, in_progress, completed, expired

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_expert_validations_query", "query_id"),
        Index("idx_expert_validations_status", "status"),
        Index("idx_expert_validations_complexity", "complexity_level"),
        Index("idx_expert_validations_target", "target_completion"),
        CheckConstraint("complexity_level >= 1 AND complexity_level <= 5", name="complexity_level_range"),
        CheckConstraint(
            "consensus_confidence >= 0.0 AND consensus_confidence <= 1.0", name="consensus_confidence_range"
        ),
        CheckConstraint(
            "final_confidence_score >= 0.0 AND final_confidence_score <= 1.0", name="final_confidence_range"
        ),
        CheckConstraint(
            "expert_agreement_score >= 0.0 AND expert_agreement_score <= 1.0", name="agreement_score_range"
        ),
        CheckConstraint("completed_validations <= required_validations", name="logical_validation_counts"),
    )


# Configuration for quality analysis system
@dataclass
class QualityAnalysisConfig:
    """Configuration settings for quality analysis system"""

    # Feedback collection settings
    MAX_FEEDBACK_PROCESSING_TIME_SECONDS: int = 30
    REQUIRED_EXPERT_CREDENTIALS: list[str] = None
    MIN_EXPERT_TRUST_SCORE: float = 0.7

    # Pattern analysis settings
    MIN_PATTERN_FREQUENCY: int = 3
    MIN_PATTERN_CONFIDENCE: float = 0.8
    CLUSTERING_SIMILARITY_THRESHOLD: float = 0.75

    # Improvement settings
    AUTO_IMPROVEMENT_THRESHOLD: float = 0.9
    EXPERT_VALIDATION_THRESHOLD: float = 0.7
    MAX_CONCURRENT_IMPROVEMENTS: int = 5

    # Quality thresholds
    TARGET_ACCURACY_SCORE: float = 0.85
    TARGET_EXPERT_SATISFACTION: float = 0.80
    TARGET_RESPONSE_TIME_MS: int = 300

    # Italian language specific
    ITALIAN_CATEGORIES = [
        "normativa_obsoleta",
        "interpretazione_errata",
        "caso_mancante",
        "calcolo_sbagliato",
        "troppo_generico",
    ]

    def __post_init__(self):
        if self.REQUIRED_EXPERT_CREDENTIALS is None:
            self.REQUIRED_EXPERT_CREDENTIALS = ["dottore_commercialista", "revisore_legale", "consulente_fiscale"]


# Default configuration instance
QUALITY_ANALYSIS_CONFIG = QualityAnalysisConfig()
