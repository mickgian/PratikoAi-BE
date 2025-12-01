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
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel


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


class ExpertProfile(SQLModel, table=True):
    """Expert profiles for validation and trust scoring"""

    __tablename__ = "expert_profiles"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign keys
    user_id: int = Field(foreign_key="user.id")

    # Professional credentials (arrays require sa_column)
    credentials: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String), default=list))
    credential_types: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String), default=list),  # Store as strings
    )
    experience_years: int = Field(default=0)
    specializations: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String), default=list))

    # Performance metrics
    feedback_count: int = Field(default=0)
    feedback_accuracy_rate: float = Field(default=0.0)
    average_response_time_seconds: int = Field(default=0)
    trust_score: float = Field(default=0.5)

    # Professional information
    professional_registration_number: str | None = Field(default=None, max_length=50)
    organization: str | None = Field(default=None, max_length=200)
    location_city: str | None = Field(default=None, max_length=100)

    # Status and verification
    is_verified: bool = Field(default=False)
    verification_date: datetime | None = Field(default=None, sa_column=Column(DateTime, nullable=True))
    is_active: bool = Field(default=True)

    # Timestamps
    created_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now()))

    # Relationships
    expert_feedback: list["ExpertFeedback"] = Relationship(back_populates="expert")

    __table_args__ = (
        Index("idx_expert_profiles_trust_score", "trust_score"),
        Index("idx_expert_profiles_specializations", "specializations"),
        Index("idx_expert_profiles_active", "is_active", "is_verified"),
        CheckConstraint("trust_score >= 0.0 AND trust_score <= 1.0", name="trust_score_range"),
        CheckConstraint("feedback_accuracy_rate >= 0.0 AND feedback_accuracy_rate <= 1.0", name="accuracy_rate_range"),
    )


class ExpertFeedback(SQLModel, table=True):
    """Expert feedback on AI-generated answers - POWERS THE CORRETTA BUTTON"""

    __tablename__ = "expert_feedback"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign keys
    query_id: UUID
    expert_id: UUID = Field(foreign_key="expert_profiles.id")

    # Feedback details (use SQLAlchemy Enum to match database ENUM types)
    # Use values_callable to serialize enum VALUE (lowercase) instead of NAME (uppercase)
    feedback_type: FeedbackType = Field(
        sa_column=Column(
            Enum(FeedbackType, name="feedback_type", values_callable=lambda e: [member.value for member in e]),
            nullable=False,
        )
    )
    category: ItalianFeedbackCategory | None = Field(
        default=None,
        sa_column=Column(
            Enum(
                ItalianFeedbackCategory,
                name="italian_feedback_category",
                values_callable=lambda e: [member.value for member in e],
            ),
            nullable=True,
        ),
    )

    # Original content
    query_text: str = Field(sa_column=Column(Text, nullable=False))
    original_answer: str = Field(sa_column=Column(Text, nullable=False))

    # Expert input
    expert_answer: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    improvement_suggestions: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(Text), default=list))
    regulatory_references: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String), default=list))

    # Quality metrics
    confidence_score: float = Field(default=0.0)
    time_spent_seconds: int
    complexity_rating: int | None = Field(default=None)  # 1-5 scale

    # Processing metadata
    processing_time_ms: int | None = Field(default=None)
    feedback_timestamp: datetime = Field(sa_column=Column(DateTime, server_default=func.now()))

    # System response
    action_taken: str | None = Field(default=None, max_length=100)
    improvement_applied: bool = Field(default=False)

    # Task generation fields (for QUERY_ISSUES_ROADMAP.md integration)
    additional_details: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    generated_task_id: str | None = Field(default=None, max_length=50)
    task_creation_attempted: bool = Field(default=False)
    task_creation_success: bool | None = Field(default=None)
    task_creation_error: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    generated_faq_id: str | None = Field(default=None, max_length=100)

    # Timestamps
    created_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now()))

    # Relationships
    expert: "ExpertProfile" = Relationship(back_populates="expert_feedback")

    __table_args__ = (
        Index("idx_expert_feedback_query_id", "query_id"),
        Index("idx_expert_feedback_expert_id", "expert_id"),
        Index("idx_expert_feedback_type_category", "feedback_type", "category"),
        Index("idx_expert_feedback_timestamp", "feedback_timestamp"),
        Index("idx_expert_feedback_improvement_applied", "improvement_applied"),
        CheckConstraint("confidence_score >= 0.0 AND confidence_score <= 1.0", name="confidence_score_range"),
        CheckConstraint("complexity_rating >= 1 AND complexity_rating <= 5", name="complexity_rating_range"),
        CheckConstraint("time_spent_seconds > 0", name="positive_time_spent"),
    )


class PromptTemplate(SQLModel, table=True):
    """Advanced prompt templates with structured reasoning"""

    __tablename__ = "prompt_templates"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Core fields
    name: str = Field(max_length=200, unique=True)
    version: str = Field(max_length=20, default="1.0")

    # Template content
    template_text: str = Field(sa_column=Column(Text, nullable=False))
    variables: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String), default=list))
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    # Categorization
    category: str = Field(max_length=100)
    specialization_areas: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String), default=list))
    complexity_level: str = Field(max_length=20, default="medium")  # basic, medium, advanced

    # Quality metrics
    clarity_score: float = Field(default=0.0)
    completeness_score: float = Field(default=0.0)
    accuracy_score: float = Field(default=0.0)
    overall_quality_score: float = Field(default=0.0)

    # Usage tracking
    usage_count: int = Field(default=0)
    success_rate: float = Field(default=0.0)
    average_user_rating: float = Field(default=0.0)

    # A/B testing
    is_active: bool = Field(default=True)
    variant_group: str | None = Field(default=None, max_length=50)

    # Timestamps
    created_by: UUID | None = Field(default=None)
    created_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now()))

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


class FailurePattern(SQLModel, table=True):
    """Identified patterns in system failures"""

    __tablename__ = "failure_patterns"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Core fields
    pattern_name: str = Field(max_length=200)
    pattern_type: str = Field(max_length=100)

    # Pattern characteristics
    description: str = Field(sa_column=Column(Text, nullable=False))
    categories: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String), default=list))
    example_queries: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(Text), default=list))

    # Frequency and impact
    frequency_count: int = Field(default=0)
    impact_score: float = Field(default=0.0)
    confidence_score: float = Field(default=0.0)

    # Analysis metadata
    detection_algorithm: str = Field(max_length=100, default="manual")
    cluster_id: str | None = Field(default=None, max_length=100)

    # Temporal tracking
    first_detected: datetime = Field(sa_column=Column(DateTime, server_default=func.now()))
    last_occurrence: datetime = Field(sa_column=Column(DateTime, server_default=func.now()))

    # Resolution tracking
    is_resolved: bool = Field(default=False)
    resolution_date: datetime | None = Field(default=None, sa_column=Column(DateTime, nullable=True))
    resolution_method: str | None = Field(default=None, max_length=200)

    # Timestamps
    created_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now()))

    __table_args__ = (
        Index("idx_failure_patterns_type", "pattern_type"),
        Index("idx_failure_patterns_impact", "impact_score"),
        Index("idx_failure_patterns_frequency", "frequency_count"),
        Index("idx_failure_patterns_resolved", "is_resolved"),
        CheckConstraint("impact_score >= 0.0 AND impact_score <= 1.0", name="impact_score_range"),
        CheckConstraint("confidence_score >= 0.0 AND confidence_score <= 1.0", name="confidence_score_range"),
        CheckConstraint("frequency_count >= 0", name="non_negative_frequency"),
    )


class SystemImprovement(SQLModel, table=True):
    """Tracking of system improvements and their outcomes"""

    __tablename__ = "system_improvements"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Core fields
    improvement_type: str = Field(max_length=100)

    # Improvement details
    title: str = Field(max_length=200)
    description: str = Field(sa_column=Column(Text, nullable=False))
    category: str = Field(max_length=100)

    # Source and reasoning
    trigger_pattern_id: UUID | None = Field(default=None, foreign_key="failure_patterns.id")
    expert_feedback_ids: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String), default=list))
    justification: str = Field(sa_column=Column(Text, nullable=False))

    # Implementation (JSON requires sa_column)
    implementation_details: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, default=dict))
    status: str = Field(max_length=20, default="pending")  # ImprovementStatus enum value

    # Impact measurement
    target_metrics: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, default=dict))
    baseline_metrics: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    actual_metrics: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))

    # Confidence and priority
    confidence_score: float = Field(default=0.0)
    priority_score: float = Field(default=0.5)
    estimated_impact: float = Field(default=0.0)

    # Timeline
    planned_start_date: datetime | None = Field(default=None, sa_column=Column(DateTime, nullable=True))
    actual_start_date: datetime | None = Field(default=None, sa_column=Column(DateTime, nullable=True))
    planned_completion_date: datetime | None = Field(default=None, sa_column=Column(DateTime, nullable=True))
    actual_completion_date: datetime | None = Field(default=None, sa_column=Column(DateTime, nullable=True))

    # Approval workflow
    requires_expert_validation: bool = Field(default=False)
    expert_approved: bool | None = Field(default=None)
    approving_expert_id: UUID | None = Field(default=None)
    approval_date: datetime | None = Field(default=None, sa_column=Column(DateTime, nullable=True))

    # Timestamps
    created_by: UUID | None = Field(default=None)
    created_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now()))

    __table_args__ = (
        Index("idx_system_improvements_type", "improvement_type"),
        Index("idx_system_improvements_status", "status"),
        Index("idx_system_improvements_priority", "priority_score"),
        Index("idx_system_improvements_pattern", "trigger_pattern_id"),
        CheckConstraint("confidence_score >= 0.0 AND confidence_score <= 1.0", name="improvement_confidence_range"),
        CheckConstraint("priority_score >= 0.0 AND priority_score <= 1.0", name="priority_score_range"),
        CheckConstraint("estimated_impact >= 0.0 AND estimated_impact <= 1.0", name="estimated_impact_range"),
    )


class QualityMetric(SQLModel, table=True):
    """Quality metrics tracking over time"""

    __tablename__ = "quality_metrics"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Core fields
    metric_name: str = Field(max_length=100)
    metric_category: str = Field(max_length=100)

    # Metric value and context
    metric_value: float
    metric_unit: str = Field(max_length=50, default="score")
    measurement_period: str = Field(max_length=50, default="daily")

    # Contextualization
    query_category: str | None = Field(default=None, max_length=100)
    expert_specialization: str | None = Field(default=None, max_length=100)
    user_segment: str | None = Field(default=None, max_length=100)

    # Sample size and confidence
    sample_size: int = Field(default=0)
    confidence_interval: float | None = Field(default=None)
    standard_deviation: float | None = Field(default=None)

    # Benchmarking
    baseline_value: float | None = Field(default=None)
    target_value: float | None = Field(default=None)
    benchmark_percentile: float | None = Field(default=None)

    # Temporal tracking
    measurement_date: datetime = Field(sa_column=Column(DateTime, nullable=False))
    measurement_window_start: datetime = Field(sa_column=Column(DateTime, nullable=False))
    measurement_window_end: datetime = Field(sa_column=Column(DateTime, nullable=False))

    # Metadata
    calculated_by: str = Field(max_length=100, default="system")
    calculation_method: str | None = Field(default=None, max_length=200)
    data_sources: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String), default=list))

    created_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now()))

    __table_args__ = (
        Index("idx_quality_metrics_name_date", "metric_name", "measurement_date"),
        Index("idx_quality_metrics_category", "metric_category"),
        Index("idx_quality_metrics_period", "measurement_period", "measurement_date"),
        CheckConstraint("sample_size >= 0", name="non_negative_sample_size"),
    )


class ExpertValidation(SQLModel, table=True):
    """Expert validation records for complex queries"""

    __tablename__ = "expert_validations"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Core fields
    query_id: UUID

    # Validation request
    validation_type: str = Field(max_length=100)  # consensus, single_expert, automated
    complexity_level: int  # 1-5 scale
    specialization_required: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String), default=list))

    # Expert assignments
    assigned_experts: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String), default=list))
    completed_validations: int = Field(default=0)
    required_validations: int = Field(default=1)

    # Consensus tracking
    consensus_reached: bool = Field(default=False)
    consensus_confidence: float = Field(default=0.0)
    disagreement_areas: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String), default=list))

    # Final outcome
    validated_answer: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    validation_notes: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    regulatory_confirmations: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String), default=list))

    # Quality assurance
    final_confidence_score: float = Field(default=0.0)
    expert_agreement_score: float = Field(default=0.0)

    # Timeline
    requested_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now()))
    target_completion: datetime = Field(sa_column=Column(DateTime, nullable=False))
    completed_at: datetime | None = Field(default=None, sa_column=Column(DateTime, nullable=True))

    # Status
    status: str = Field(max_length=50, default="pending")  # pending, in_progress, completed, expired

    # Timestamps
    created_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now()))

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


class ExpertGeneratedTask(SQLModel, table=True):
    """Tasks automatically generated from expert feedback for QUERY_ISSUES_ROADMAP.md tracking"""

    __tablename__ = "expert_generated_tasks"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Task identification
    task_id: str = Field(max_length=50, unique=True, index=True)  # e.g., "QUERY-08"
    task_name: str = Field(max_length=200)

    # Source references
    feedback_id: UUID = Field(foreign_key="expert_feedback.id")
    expert_id: UUID = Field(foreign_key="expert_profiles.id")

    # Content snapshot
    question: str = Field(sa_column=Column(Text, nullable=False))
    answer: str = Field(sa_column=Column(Text, nullable=False))
    additional_details: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    # File tracking
    file_path: str = Field(max_length=500, default="QUERY_ISSUES_ROADMAP.md")

    # Timestamps
    created_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now()))
    updated_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now()))

    __table_args__ = (
        Index("idx_expert_generated_tasks_feedback_id", "feedback_id"),
        Index("idx_expert_generated_tasks_expert_id", "expert_id"),
        Index("idx_expert_generated_tasks_created_at", "created_at"),
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
