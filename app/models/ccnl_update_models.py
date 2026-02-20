"""CCNL Update Models.

Database models for CCNL update system including version tracking,
update events, change logs, and monitoring metrics.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID as UUIDType
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlmodel import Field, Relationship, SQLModel


class UpdateSource(Enum):
    """Sources for CCNL updates."""

    CGIL_RSS = "cgil_rss"
    CISL_RSS = "cisl_rss"
    UIL_RSS = "uil_rss"
    UGL_RSS = "ugl_rss"
    CONFINDUSTRIA_NEWS = "confindustria_news"
    CONFCOMMERCIO_NEWS = "confcommercio_news"
    CONFARTIGIANATO_NEWS = "confartigianato_news"
    CONFAPI_NEWS = "confapi_news"
    CNEL_OFFICIAL = "cnel_official"
    MINISTRY_LABOR = "ministry_labor"
    MANUAL_ENTRY = "manual_entry"


class UpdateStatus(Enum):
    """Status of CCNL update processing."""

    DETECTED = "detected"
    PROCESSING = "processing"
    VERIFIED = "verified"
    INTEGRATED = "integrated"
    FAILED = "failed"
    DISMISSED = "dismissed"


class ChangeType(Enum):
    """Types of CCNL changes."""

    RENEWAL = "renewal"
    AMENDMENT = "amendment"
    SALARY_UPDATE = "salary_update"
    NEW_AGREEMENT = "new_agreement"
    CORRECTION = "correction"
    TEMPORARY = "temporary"


class CCNLDatabase(SQLModel, table=True):
    """Main CCNL database entry."""

    __tablename__ = "ccnl_database"

    # Primary key
    id: UUIDType = Field(default_factory=uuid4, primary_key=True)

    # Core fields
    sector_name: str = Field(max_length=200)
    ccnl_code: str = Field(max_length=50, unique=True)
    official_name: str = Field(sa_column=Column(Text, nullable=False))
    current_version_id: UUIDType | None = Field(default=None)  # No FK constraint

    # Timestamps
    created_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow, nullable=False))
    updated_at: datetime = Field(
        sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    )

    # Status
    is_active: bool = Field(default=True)

    # Relationships
    versions: list["CCNLVersion"] = Relationship(
        back_populates="ccnl_database", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    update_events: list["CCNLUpdateEvent"] = Relationship(
        back_populates="ccnl_database", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    change_logs: list["CCNLChangeLog"] = Relationship(
        back_populates="ccnl_database", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    # Indexes
    __table_args__ = (
        Index("idx_ccnl_database_sector", "sector_name"),
        Index("idx_ccnl_database_code", "ccnl_code"),
        Index("idx_ccnl_database_active", "is_active"),
    )


class CCNLVersion(SQLModel, table=True):
    """CCNL version tracking."""

    __tablename__ = "ccnl_versions"

    # Primary key
    id: UUIDType = Field(default_factory=uuid4, primary_key=True)

    # Foreign keys
    ccnl_id: UUIDType = Field(foreign_key="ccnl_database.id")

    # Core fields
    version_number: str = Field(max_length=20)
    effective_date: date = Field(sa_column=Column(Date, nullable=False))
    expiry_date: date | None = Field(default=None, sa_column=Column(Date, nullable=True))
    signed_date: date | None = Field(default=None, sa_column=Column(Date, nullable=True))
    document_url: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    # JSON fields
    salary_data: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, default=dict, nullable=False))
    working_conditions: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, default=dict, nullable=False)
    )
    leave_provisions: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, default=dict, nullable=False)
    )
    other_benefits: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, default=dict, nullable=False))

    # Timestamps
    created_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow, nullable=False))

    # Status
    is_current: bool = Field(default=False)

    # Relationships
    ccnl_database: "CCNLDatabase" = Relationship(back_populates="versions")
    old_change_logs: list["CCNLChangeLog"] = Relationship(
        back_populates="old_version", sa_relationship_kwargs={"foreign_keys": "CCNLChangeLog.old_version_id"}
    )
    new_change_logs: list["CCNLChangeLog"] = Relationship(
        back_populates="new_version", sa_relationship_kwargs={"foreign_keys": "CCNLChangeLog.new_version_id"}
    )

    # Indexes
    __table_args__ = (
        Index("idx_ccnl_versions_ccnl_id", "ccnl_id"),
        Index("idx_ccnl_versions_current", "is_current"),
        Index("idx_ccnl_versions_effective", "effective_date"),
    )


class CCNLUpdateEvent(SQLModel, table=True):
    """CCNL update event tracking."""

    __tablename__ = "ccnl_update_events"

    # Primary key
    id: UUIDType = Field(default_factory=uuid4, primary_key=True)

    # Foreign keys
    ccnl_id: UUIDType = Field(foreign_key="ccnl_database.id")

    # Core fields
    source: str = Field(max_length=50)  # UpdateSource enum value
    detected_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow, nullable=False))
    title: str = Field(sa_column=Column(Text, nullable=False))
    url: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    content_summary: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    classification_confidence: Decimal = Field(sa_column=Column(Numeric(3, 2), nullable=False))
    status: str = Field(max_length=20)  # UpdateStatus enum value
    processed_at: datetime | None = Field(default=None, sa_column=Column(DateTime, nullable=True))
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    # Relationships
    ccnl_database: "CCNLDatabase" = Relationship(back_populates="update_events")

    # Indexes
    __table_args__ = (
        Index("idx_update_events_ccnl_id", "ccnl_id"),
        Index("idx_update_events_status", "status"),
        Index("idx_update_events_detected", "detected_at"),
    )


class CCNLChangeLog(SQLModel, table=True):
    """CCNL change log tracking."""

    __tablename__ = "ccnl_change_logs"

    # Primary key
    id: UUIDType = Field(default_factory=uuid4, primary_key=True)

    # Foreign keys
    ccnl_id: UUIDType = Field(foreign_key="ccnl_database.id")
    old_version_id: UUIDType | None = Field(default=None, foreign_key="ccnl_versions.id")
    new_version_id: UUIDType = Field(foreign_key="ccnl_versions.id")

    # Core fields
    change_type: str = Field(max_length=20)  # ChangeType enum value
    changes_summary: str = Field(sa_column=Column(Text, nullable=False))

    # JSON field
    detailed_changes: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))

    significance_score: Decimal = Field(sa_column=Column(Numeric(3, 2), nullable=False))

    # Timestamps
    created_at: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow, nullable=False))
    created_by: str | None = Field(default=None, max_length=100)

    # Relationships
    ccnl_database: "CCNLDatabase" = Relationship(back_populates="change_logs")
    old_version: Optional["CCNLVersion"] = Relationship(
        back_populates="old_change_logs", sa_relationship_kwargs={"foreign_keys": "CCNLChangeLog.old_version_id"}
    )
    new_version: "CCNLVersion" = Relationship(
        back_populates="new_change_logs", sa_relationship_kwargs={"foreign_keys": "CCNLChangeLog.new_version_id"}
    )

    # Indexes
    __table_args__ = (
        Index("idx_change_logs_ccnl_id", "ccnl_id"),
        Index("idx_change_logs_created", "created_at"),
        Index("idx_change_logs_significance", "significance_score"),
    )


class CCNLMonitoringMetric(SQLModel, table=True):
    """CCNL monitoring metrics."""

    __tablename__ = "ccnl_monitoring_metrics"

    # Primary key
    id: UUIDType = Field(default_factory=uuid4, primary_key=True)

    # Core fields
    metric_type: str = Field(max_length=50)
    metric_name: str = Field(max_length=100)
    value: Decimal = Field(sa_column=Column(Numeric(10, 4), nullable=False))
    unit: str | None = Field(default=None, max_length=20)
    timestamp: datetime = Field(sa_column=Column(DateTime, default=datetime.utcnow, nullable=False))
    source: str | None = Field(default=None, max_length=50)

    # JSON field
    metric_metadata: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))

    # Indexes
    __table_args__ = (
        Index("idx_monitoring_metrics_type", "metric_type"),
        Index("idx_monitoring_metrics_timestamp", "timestamp"),
    )
