"""
CCNL Update Models.

Database models for CCNL update system including version tracking,
update events, change logs, and monitoring metrics.
"""

import uuid
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Dict, Any, Optional, List
from sqlalchemy import (
    Column, String, DateTime, Date, Boolean, JSON, 
    ForeignKey, Text, Numeric, Integer, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


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


class CCNLDatabase(Base):
    """Main CCNL database entry."""
    
    __tablename__ = "ccnl_database"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sector_name = Column(String(200), nullable=False)
    ccnl_code = Column(String(50), unique=True, nullable=False)
    official_name = Column(Text, nullable=False)
    current_version_id = Column(UUID(as_uuid=True), nullable=True)  # Remove FK constraint for now
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    versions = relationship("CCNLVersion", back_populates="ccnl_database", cascade="all, delete-orphan")
    update_events = relationship("CCNLUpdateEvent", back_populates="ccnl_database", cascade="all, delete-orphan")
    change_logs = relationship("CCNLChangeLog", back_populates="ccnl_database", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_ccnl_database_sector', 'sector_name'),
        Index('idx_ccnl_database_code', 'ccnl_code'),
        Index('idx_ccnl_database_active', 'is_active'),
    )


class CCNLVersion(Base):
    """CCNL version tracking."""
    
    __tablename__ = "ccnl_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ccnl_id = Column(UUID(as_uuid=True), ForeignKey('ccnl_database.id'), nullable=False)
    version_number = Column(String(20), nullable=False)
    effective_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=True)
    signed_date = Column(Date, nullable=True)
    document_url = Column(Text, nullable=True)
    salary_data = Column(JSON, default=dict, nullable=False)
    working_conditions = Column(JSON, default=dict, nullable=False)
    leave_provisions = Column(JSON, default=dict, nullable=False)
    other_benefits = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_current = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    ccnl_database = relationship("CCNLDatabase", back_populates="versions")
    old_change_logs = relationship("CCNLChangeLog", foreign_keys="CCNLChangeLog.old_version_id", back_populates="old_version")
    new_change_logs = relationship("CCNLChangeLog", foreign_keys="CCNLChangeLog.new_version_id", back_populates="new_version")
    
    # Indexes
    __table_args__ = (
        Index('idx_ccnl_versions_ccnl_id', 'ccnl_id'),
        Index('idx_ccnl_versions_current', 'is_current'),
        Index('idx_ccnl_versions_effective', 'effective_date'),
    )


class CCNLUpdateEvent(Base):
    """CCNL update event tracking."""
    
    __tablename__ = "ccnl_update_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ccnl_id = Column(UUID(as_uuid=True), ForeignKey('ccnl_database.id'), nullable=False)
    source = Column(String(50), nullable=False)  # UpdateSource enum value
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=True)
    content_summary = Column(Text, nullable=True)
    classification_confidence = Column(Numeric(3, 2), nullable=False)
    status = Column(String(20), nullable=False)  # UpdateStatus enum value
    processed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    ccnl_database = relationship("CCNLDatabase", back_populates="update_events")
    
    # Indexes
    __table_args__ = (
        Index('idx_update_events_ccnl_id', 'ccnl_id'),
        Index('idx_update_events_status', 'status'),
        Index('idx_update_events_detected', 'detected_at'),
    )


class CCNLChangeLog(Base):
    """CCNL change log tracking."""
    
    __tablename__ = "ccnl_change_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ccnl_id = Column(UUID(as_uuid=True), ForeignKey('ccnl_database.id'), nullable=False)
    old_version_id = Column(UUID(as_uuid=True), ForeignKey('ccnl_versions.id'), nullable=True)
    new_version_id = Column(UUID(as_uuid=True), ForeignKey('ccnl_versions.id'), nullable=False)
    change_type = Column(String(20), nullable=False)  # ChangeType enum value
    changes_summary = Column(Text, nullable=False)
    detailed_changes = Column(JSON, nullable=False)
    significance_score = Column(Numeric(3, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=True)
    
    # Relationships
    ccnl_database = relationship("CCNLDatabase", back_populates="change_logs")
    old_version = relationship("CCNLVersion", foreign_keys=[old_version_id], back_populates="old_change_logs")
    new_version = relationship("CCNLVersion", foreign_keys=[new_version_id], back_populates="new_change_logs")
    
    # Indexes
    __table_args__ = (
        Index('idx_change_logs_ccnl_id', 'ccnl_id'),
        Index('idx_change_logs_created', 'created_at'),
        Index('idx_change_logs_significance', 'significance_score'),
    )


class CCNLMonitoringMetric(Base):
    """CCNL monitoring metrics."""
    
    __tablename__ = "ccnl_monitoring_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_type = Column(String(50), nullable=False)
    metric_name = Column(String(100), nullable=False)
    value = Column(Numeric(10, 4), nullable=False)
    unit = Column(String(20), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    source = Column(String(50), nullable=True)
    metric_metadata = Column(JSON, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_monitoring_metrics_type', 'metric_type'),
        Index('idx_monitoring_metrics_timestamp', 'timestamp'),
    )