"""Data Export Models for GDPR Article 20 Compliance.

This module defines models for handling comprehensive user data exports
with full Italian GDPR compliance, including privacy protection and
secure handling of sensitive information.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import JSON, BigInteger, Column, Date, DateTime, Integer, Numeric, String, Text
from sqlmodel import Field, Relationship, SQLModel


class ExportFormat(str, Enum):
    """Export format options"""

    JSON = "json"
    CSV = "csv"
    BOTH = "both"


class ExportStatus(str, Enum):
    """Export processing status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class PrivacyLevel(str, Enum):
    """Privacy level for data export"""

    FULL = "full"  # Include all data
    ANONYMIZED = "anonymized"  # Mask PII
    MINIMAL = "minimal"  # Essential data only


class DataExportRequest(SQLModel, table=True):
    """Data export requests for GDPR Article 20 compliance.

    Tracks user requests for complete data portability with Italian
    market compliance and privacy protection features.
    """

    __tablename__ = "data_export_requests"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign keys
    user_id: int = Field(foreign_key="user.id")

    # Request configuration (store enums as strings)
    format: str = Field(default=ExportFormat.JSON.value, max_length=20)
    privacy_level: str = Field(default=PrivacyLevel.FULL.value, max_length=20)
    include_sensitive: bool = Field(default=True)
    anonymize_pii: bool = Field(default=False)

    # Date range filtering (optional)
    date_from: date | None = Field(default=None, sa_column=Column(Date, nullable=True))
    date_to: date | None = Field(default=None, sa_column=Column(Date, nullable=True))

    # Italian specific options
    include_fatture: bool = Field(default=True)
    include_f24: bool = Field(default=True)
    include_dichiarazioni: bool = Field(default=True)
    mask_codice_fiscale: bool = Field(default=False)

    # Data categories to include
    include_profile: bool = Field(default=True)
    include_queries: bool = Field(default=True)
    include_documents: bool = Field(default=True)
    include_calculations: bool = Field(default=True)
    include_subscriptions: bool = Field(default=True)
    include_invoices: bool = Field(default=True)
    include_usage_stats: bool = Field(default=True)
    include_faq_interactions: bool = Field(default=True)
    include_knowledge_searches: bool = Field(default=True)

    # Processing status (store enum as string)
    status: str = Field(default=ExportStatus.PENDING.value, max_length=20)
    requested_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow, nullable=False)
    )
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    expires_at: datetime

    # Results
    file_size_bytes: int | None = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    download_url: str | None = Field(default=None, max_length=500)
    download_count: int = Field(default=0)
    max_downloads: int = Field(default=10)

    # Error handling
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)

    # Security and audit
    request_ip: str | None = Field(default=None, max_length=45)  # IPv6 compatible
    user_agent: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    download_ips: list[dict[str, Any]] | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )  # Track download IPs

    # Italian compliance
    gdpr_lawful_basis: str = Field(default="Article 20 - Right to data portability", max_length=100)
    data_controller: str = Field(default="PratikoAI SRL", max_length=255)
    retention_notice: str = Field(
        default="Dati cancellati automaticamente dopo 24 ore",
        sa_column=Column(Text, default="Dati cancellati automaticamente dopo 24 ore"),
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow))
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    )

    # Relationships
    # Note: No relationship to User model - it uses SQLModel which is incompatible
    # with SQLAlchemy relationships. Access user via user_id foreign key instead.

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(hours=24)

    def is_expired(self) -> bool:
        """Check if export has expired"""
        return datetime.utcnow() > self.expires_at

    def is_downloadable(self) -> bool:
        """Check if export is ready for download"""
        return (
            self.status == ExportStatus.COMPLETED.value
            and not self.is_expired()
            and self.download_count < self.max_downloads
        )

    def processing_time_seconds(self) -> int | None:
        """Calculate processing time in seconds"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds())
        return None

    def time_until_expiry(self) -> timedelta | None:
        """Time remaining until expiry"""
        if self.expires_at:
            remaining = self.expires_at - datetime.utcnow()
            return remaining if remaining.total_seconds() > 0 else timedelta(0)
        return None

    def can_retry(self) -> bool:
        """Check if export can be retried"""
        return self.status == ExportStatus.FAILED.value and self.retry_count < self.max_retries

    def increment_download(self, ip_address: str | None = None) -> bool:
        """Increment download count and track IP"""
        if not self.is_downloadable():
            return False

        self.download_count += 1

        if ip_address:
            if not self.download_ips:
                self.download_ips = []
            self.download_ips.append({"ip": ip_address, "timestamp": datetime.utcnow().isoformat()})

        return True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "format": self.format,
            "privacy_level": self.privacy_level,
            "status": self.status,
            "requested_at": self.requested_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "expires_at": self.expires_at.isoformat(),
            "file_size_mb": round(self.file_size_bytes / 1024 / 1024, 2) if self.file_size_bytes else None,
            "download_count": self.download_count,
            "max_downloads": self.max_downloads,
            "is_expired": self.is_expired(),
            "is_downloadable": self.is_downloadable(),
            "processing_time_seconds": self.processing_time_seconds(),
            "time_until_expiry_hours": round(expiry.total_seconds() / 3600, 1)
            if (expiry := self.time_until_expiry())
            else 0,
            "error_message": self.error_message,
            "data_categories": {
                "profile": self.include_profile,
                "queries": self.include_queries,
                "documents": self.include_documents,
                "calculations": self.include_calculations,
                "subscriptions": self.include_subscriptions,
                "invoices": self.include_invoices,
                "usage_stats": self.include_usage_stats,
                "faq_interactions": self.include_faq_interactions,
                "knowledge_searches": self.include_knowledge_searches,
            },
            "italian_options": {
                "include_fatture": self.include_fatture,
                "include_f24": self.include_f24,
                "include_dichiarazioni": self.include_dichiarazioni,
                "mask_codice_fiscale": self.mask_codice_fiscale,
            },
            "privacy_options": {"include_sensitive": self.include_sensitive, "anonymize_pii": self.anonymize_pii},
        }


class ExportAuditLog(SQLModel, table=True):
    """Audit log for data export activities.

    Tracks all export-related activities for compliance and security monitoring.
    """

    __tablename__ = "export_audit_logs"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign keys
    export_request_id: UUID = Field(foreign_key="data_export_requests.id")
    user_id: int = Field(foreign_key="user.id")

    # Activity details
    activity_type: str = Field(max_length=50)  # requested, started, completed, downloaded, expired
    activity_timestamp: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow, nullable=False)
    )

    # Context information
    ip_address: str | None = Field(default=None, max_length=45)
    user_agent: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    session_id: str | None = Field(default=None, max_length=255)

    # Activity-specific data
    activity_data: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))

    # Security flags
    suspicious_activity: bool = Field(default=False)
    security_notes: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    # Relationships
    export_request: Optional["DataExportRequest"] = Relationship()
    # Note: No relationship to User model - it uses SQLModel which is incompatible
    # with SQLAlchemy relationships. Access user via user_id foreign key instead.

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "export_request_id": str(self.export_request_id),
            "user_id": str(self.user_id),
            "activity_type": self.activity_type,
            "activity_timestamp": self.activity_timestamp.isoformat(),
            "ip_address": self.ip_address,
            "activity_data": self.activity_data,
            "suspicious_activity": self.suspicious_activity,
        }


class QueryHistory(SQLModel, table=True):
    """User query history for export.

    Stores user queries and responses for GDPR compliance export.
    """

    __tablename__ = "query_history"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign keys (CASCADE delete for GDPR compliance)
    user_id: int = Field(
        sa_column=Column(
            Integer,
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )

    # Query details
    query: str = Field(sa_column=Column(Text, nullable=False))
    response: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    response_cached: bool = Field(default=False)
    response_time_ms: int | None = Field(default=None)

    # Usage tracking
    tokens_used: int | None = Field(default=None)
    cost_cents: int | None = Field(default=None)
    model_used: str | None = Field(default=None, max_length=100)

    # Context
    session_id: str | None = Field(default=None, max_length=255)
    conversation_id: UUID | None = Field(default=None)

    # DEV-244: KB sources metadata for Fonti display (persisted for chat history)
    kb_sources_metadata: list[dict] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="KB source URLs and metadata for Fonti display",
    )

    # Italian specific
    query_type: str | None = Field(default=None, max_length=50)  # tax_calculation, document_analysis, general
    italian_content: bool = Field(default=True)

    # Timestamps
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow, nullable=False)
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow))

    # Relationships
    # Note: No relationship to User model - it uses SQLModel which is incompatible
    # with SQLAlchemy relationships. Access user via user_id foreign key instead.


class ExportDocumentAnalysis(SQLModel, table=True):
    """Document analysis history for export.

    Metadata only - no actual document content for privacy.
    Note: Renamed from DocumentAnalysis to avoid mapper conflict with
    app.models.document.DocumentAnalysis
    """

    __tablename__ = "export_document_analysis"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign keys
    user_id: int = Field(foreign_key="user.id")

    # Document metadata
    filename: str = Field(max_length=255)
    file_type: str = Field(max_length=100)
    file_size_bytes: int | None = Field(default=None, sa_column=Column(BigInteger, nullable=True))

    # Analysis details
    analysis_type: str = Field(max_length=100)  # italian_invoice, f24, declaration
    processing_time_ms: int | None = Field(default=None)
    analysis_status: str = Field(default="completed", max_length=50)

    # Results summary (no actual content)
    entities_found: int | None = Field(default=None)
    confidence_score: Decimal | None = Field(default=None, sa_column=Column(Numeric(3, 2), nullable=True))

    # Italian specific
    document_category: str | None = Field(default=None, max_length=100)  # fattura, ricevuta, f24, etc.
    tax_year: int | None = Field(default=None)

    # Timestamps
    uploaded_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow, nullable=False)
    )
    analyzed_at: datetime | None = Field(default=None)

    # Relationships
    # Note: No relationship to User model - it uses SQLModel which is incompatible
    # with SQLAlchemy relationships. Access user via user_id foreign key instead.


class TaxCalculation(SQLModel, table=True):
    """Tax calculation history for export.

    Italian tax calculations performed by users.
    """

    __tablename__ = "export_tax_calculations"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign keys
    user_id: int = Field(foreign_key="user.id")

    # Calculation details
    calculation_type: str = Field(max_length=50)  # IVA, IRPEF, IMU, etc.
    input_amount: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))
    result: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))  # Calculation results
    parameters: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))  # Input parameters

    # Italian specific
    tax_year: int | None = Field(default=None)
    region: str | None = Field(default=None, max_length=50)
    municipality: str | None = Field(default=None, max_length=100)

    # Context
    session_id: str | None = Field(default=None, max_length=255)

    # Timestamps
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow, nullable=False)
    )

    # Relationships
    # Note: No relationship to User model - it uses SQLModel which is incompatible
    # with SQLAlchemy relationships. Access user via user_id foreign key instead.


class FAQInteraction(SQLModel, table=True):
    """FAQ interaction history for export.

    Tracks user interactions with FAQ system.
    """

    __tablename__ = "faq_interactions"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign keys
    user_id: int = Field(foreign_key="user.id")

    # FAQ details
    faq_id: str = Field(max_length=100)
    question: str = Field(sa_column=Column(Text, nullable=False))
    answer: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    category: str | None = Field(default=None, max_length=100)

    # Interaction details
    viewed_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow, nullable=False)
    )
    time_spent_seconds: int | None = Field(default=None)
    helpful_rating: int | None = Field(default=None)  # 1-5 scale
    feedback: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    # Italian specific
    italian_content: bool = Field(default=True)
    tax_related: bool = Field(default=False)

    # Relationships
    # Note: No relationship to User model - it uses SQLModel which is incompatible
    # with SQLAlchemy relationships. Access user via user_id foreign key instead.


class KnowledgeBaseSearch(SQLModel, table=True):
    """Knowledge base search history for export.

    Tracks user searches in the knowledge base.
    """

    __tablename__ = "knowledge_base_searches"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign keys
    user_id: int = Field(foreign_key="user.id")

    # Search details
    search_query: str = Field(sa_column=Column(Text, nullable=False))
    results_count: int
    clicked_result_id: str | None = Field(default=None, max_length=100)
    clicked_position: int | None = Field(default=None)

    # Search context
    search_filters: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    search_category: str | None = Field(default=None, max_length=100)

    # Italian specific
    italian_query: bool = Field(default=True)
    regulatory_content: bool = Field(default=False)

    # Timestamps
    searched_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow, nullable=False)
    )

    # Relationships
    # Note: No relationship to User model - it uses SQLModel which is incompatible
    # with SQLAlchemy relationships. Access user via user_id foreign key instead.


class ElectronicInvoice(SQLModel, table=True):
    """Electronic invoice (Fattura Elettronica) history for export.

    Italian electronic invoice metadata and status.
    """

    __tablename__ = "electronic_invoices"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Foreign keys
    user_id: int = Field(foreign_key="user.id")

    # Invoice identification
    invoice_number: str = Field(max_length=50)
    invoice_date: date = Field(sa_column=Column(Date, nullable=False))

    # Electronic invoice specific
    xml_content: str | None = Field(default=None, sa_column=Column(Text, nullable=True))  # Full XML content
    xml_hash: str | None = Field(default=None, max_length=64)  # SHA-256 hash

    # SDI (Sistema di Interscambio) details
    sdi_transmission_id: str | None = Field(default=None, max_length=255)
    sdi_status: str | None = Field(default=None, max_length=50)  # sent, accepted, rejected
    sdi_response: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, default=datetime.utcnow))
    transmitted_at: datetime | None = Field(default=None)
    accepted_at: datetime | None = Field(default=None)

    # Relationships
    # Note: No relationship to User model - it uses SQLModel which is incompatible
    # with SQLAlchemy relationships. Access user via user_id foreign key instead.


# Update User model to include relationships (add to existing User model)
"""
Add these relationships to the existing User model:

# Data export relationships
data_export_requests = relationship("DataExportRequest", back_populates="user")
query_history = relationship("QueryHistory", back_populates="user")
document_analyses = relationship("ExportDocumentAnalysis", back_populates="user")
tax_calculations = relationship("TaxCalculation", back_populates="user")
faq_interactions = relationship("FAQInteraction", back_populates="user")
knowledge_searches = relationship("KnowledgeBaseSearch", back_populates="user")
electronic_invoices = relationship("ElectronicInvoice", back_populates="user")
"""
