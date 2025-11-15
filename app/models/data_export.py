"""Data Export Models for GDPR Article 20 Compliance.

This module defines models for handling comprehensive user data exports
with full Italian GDPR compliance, including privacy protection and
secure handling of sensitive information.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import JSON, BigInteger, Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from app.models.ccnl_database import Base


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


class DataExportRequest(Base):
    """Data export requests for GDPR Article 20 compliance.

    Tracks user requests for complete data portability with Italian
    market compliance and privacy protection features.
    """

    __tablename__ = "data_export_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Request configuration
    format = Column(SQLEnum(ExportFormat), default=ExportFormat.JSON, nullable=False)
    privacy_level = Column(SQLEnum(PrivacyLevel), default=PrivacyLevel.FULL, nullable=False)
    include_sensitive = Column(Boolean, default=True, nullable=False)
    anonymize_pii = Column(Boolean, default=False, nullable=False)

    # Date range filtering (optional)
    date_from = Column(Date, nullable=True)
    date_to = Column(Date, nullable=True)

    # Italian specific options
    include_fatture = Column(Boolean, default=True, nullable=False)
    include_f24 = Column(Boolean, default=True, nullable=False)
    include_dichiarazioni = Column(Boolean, default=True, nullable=False)
    mask_codice_fiscale = Column(Boolean, default=False, nullable=False)

    # Data categories to include
    include_profile = Column(Boolean, default=True, nullable=False)
    include_queries = Column(Boolean, default=True, nullable=False)
    include_documents = Column(Boolean, default=True, nullable=False)
    include_calculations = Column(Boolean, default=True, nullable=False)
    include_subscriptions = Column(Boolean, default=True, nullable=False)
    include_invoices = Column(Boolean, default=True, nullable=False)
    include_usage_stats = Column(Boolean, default=True, nullable=False)
    include_faq_interactions = Column(Boolean, default=True, nullable=False)
    include_knowledge_searches = Column(Boolean, default=True, nullable=False)

    # Processing status
    status = Column(SQLEnum(ExportStatus), default=ExportStatus.PENDING, nullable=False)
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)

    # Results
    file_size_bytes = Column(BigInteger, nullable=True)
    download_url = Column(String(500), nullable=True)
    download_count = Column(Integer, default=0, nullable=False)
    max_downloads = Column(Integer, default=10, nullable=False)

    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)

    # Security and audit
    request_ip = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    download_ips = Column(JSON, nullable=True)  # Track download IPs

    # Italian compliance
    gdpr_lawful_basis = Column(String(100), default="Article 20 - Right to data portability")
    data_controller = Column(String(255), default="PratikoAI SRL")
    retention_notice = Column(Text, default="Dati cancellati automaticamente dopo 24 ore")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="data_export_requests")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(hours=24)

    @hybrid_property
    def is_expired(self) -> bool:
        """Check if export has expired"""
        return datetime.utcnow() > self.expires_at

    @hybrid_property
    def is_downloadable(self) -> bool:
        """Check if export is ready for download"""
        return (
            self.status == ExportStatus.COMPLETED and not self.is_expired and self.download_count < self.max_downloads
        )

    @hybrid_property
    def processing_time_seconds(self) -> int | None:
        """Calculate processing time in seconds"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds())
        return None

    @hybrid_property
    def time_until_expiry(self) -> timedelta | None:
        """Time remaining until expiry"""
        if self.expires_at:
            remaining = self.expires_at - datetime.utcnow()
            return remaining if remaining.total_seconds() > 0 else timedelta(0)
        return None

    def can_retry(self) -> bool:
        """Check if export can be retried"""
        return self.status == ExportStatus.FAILED and self.retry_count < self.max_retries

    def increment_download(self, ip_address: str = None) -> bool:
        """Increment download count and track IP"""
        if not self.is_downloadable:
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
            "format": self.format.value,
            "privacy_level": self.privacy_level.value,
            "status": self.status.value,
            "requested_at": self.requested_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "expires_at": self.expires_at.isoformat(),
            "file_size_mb": round(self.file_size_bytes / 1024 / 1024, 2) if self.file_size_bytes else None,
            "download_count": self.download_count,
            "max_downloads": self.max_downloads,
            "is_expired": self.is_expired,
            "is_downloadable": self.is_downloadable,
            "processing_time_seconds": self.processing_time_seconds,
            "time_until_expiry_hours": round(self.time_until_expiry.total_seconds() / 3600, 1)
            if self.time_until_expiry
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


class ExportAuditLog(Base):
    """Audit log for data export activities.

    Tracks all export-related activities for compliance and security monitoring.
    """

    __tablename__ = "export_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    export_request_id = Column(UUID(as_uuid=True), ForeignKey("data_export_requests.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Activity details
    activity_type = Column(String(50), nullable=False)  # requested, started, completed, downloaded, expired
    activity_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Context information
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    session_id = Column(String(255), nullable=True)

    # Activity-specific data
    activity_data = Column(JSON, nullable=True)

    # Security flags
    suspicious_activity = Column(Boolean, default=False)
    security_notes = Column(Text, nullable=True)

    # Relationships
    export_request = relationship("DataExportRequest")
    user = relationship("User")

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


class QueryHistory(Base):
    """User query history for export.

    Stores user queries and responses for GDPR compliance export.
    """

    __tablename__ = "query_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Query details
    query = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    response_cached = Column(Boolean, default=False)
    response_time_ms = Column(Integer, nullable=True)

    # Usage tracking
    tokens_used = Column(Integer, nullable=True)
    cost_cents = Column(Integer, nullable=True)
    model_used = Column(String(100), nullable=True)

    # Context
    session_id = Column(String(255), nullable=True)
    conversation_id = Column(UUID(as_uuid=True), nullable=True)

    # Italian specific
    query_type = Column(String(50), nullable=True)  # tax_calculation, document_analysis, general
    italian_content = Column(Boolean, default=True)

    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="query_history")


class DocumentAnalysis(Base):
    """Document analysis history for export.

    Metadata only - no actual document content for privacy.
    """

    __tablename__ = "document_analysis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Document metadata
    filename = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=True)

    # Analysis details
    analysis_type = Column(String(100), nullable=False)  # italian_invoice, f24, declaration
    processing_time_ms = Column(Integer, nullable=True)
    analysis_status = Column(String(50), default="completed")

    # Results summary (no actual content)
    entities_found = Column(Integer, nullable=True)
    confidence_score = Column(Numeric(3, 2), nullable=True)

    # Italian specific
    document_category = Column(String(100), nullable=True)  # fattura, ricevuta, f24, etc.
    tax_year = Column(Integer, nullable=True)

    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    analyzed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="document_analyses")


class TaxCalculation(Base):
    """Tax calculation history for export.

    Italian tax calculations performed by users.
    """

    __tablename__ = "tax_calculations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Calculation details
    calculation_type = Column(String(50), nullable=False)  # IVA, IRPEF, IMU, etc.
    input_amount = Column(Numeric(12, 2), nullable=False)
    result = Column(JSON, nullable=False)  # Calculation results
    parameters = Column(JSON, nullable=True)  # Input parameters

    # Italian specific
    tax_year = Column(Integer, nullable=True)
    region = Column(String(50), nullable=True)
    municipality = Column(String(100), nullable=True)

    # Context
    session_id = Column(String(255), nullable=True)

    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="tax_calculations")


class FAQInteraction(Base):
    """FAQ interaction history for export.

    Tracks user interactions with FAQ system.
    """

    __tablename__ = "faq_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # FAQ details
    faq_id = Column(String(100), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)

    # Interaction details
    viewed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    time_spent_seconds = Column(Integer, nullable=True)
    helpful_rating = Column(Integer, nullable=True)  # 1-5 scale
    feedback = Column(Text, nullable=True)

    # Italian specific
    italian_content = Column(Boolean, default=True)
    tax_related = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="faq_interactions")


class KnowledgeBaseSearch(Base):
    """Knowledge base search history for export.

    Tracks user searches in the knowledge base.
    """

    __tablename__ = "knowledge_base_searches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Search details
    search_query = Column(Text, nullable=False)
    results_count = Column(Integer, nullable=False)
    clicked_result_id = Column(String(100), nullable=True)
    clicked_position = Column(Integer, nullable=True)

    # Search context
    search_filters = Column(JSON, nullable=True)
    search_category = Column(String(100), nullable=True)

    # Italian specific
    italian_query = Column(Boolean, default=True)
    regulatory_content = Column(Boolean, default=False)

    # Timestamps
    searched_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="knowledge_searches")


class ElectronicInvoice(Base):
    """Electronic invoice (Fattura Elettronica) history for export.

    Italian electronic invoice metadata and status.
    """

    __tablename__ = "electronic_invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Invoice identification
    invoice_number = Column(String(50), nullable=False)
    invoice_date = Column(Date, nullable=False)

    # Electronic invoice specific
    xml_content = Column(Text, nullable=True)  # Full XML content
    xml_hash = Column(String(64), nullable=True)  # SHA-256 hash

    # SDI (Sistema di Interscambio) details
    sdi_transmission_id = Column(String(255), nullable=True)
    sdi_status = Column(String(50), nullable=True)  # sent, accepted, rejected
    sdi_response = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    transmitted_at = Column(DateTime, nullable=True)
    accepted_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="electronic_invoices")


# Update User model to include relationships (add to existing User model)
"""
Add these relationships to the existing User model:

# Data export relationships
data_export_requests = relationship("DataExportRequest", back_populates="user")
query_history = relationship("QueryHistory", back_populates="user")
document_analyses = relationship("DocumentAnalysis", back_populates="user")
tax_calculations = relationship("TaxCalculation", back_populates="user")
faq_interactions = relationship("FAQInteraction", back_populates="user")
knowledge_searches = relationship("KnowledgeBaseSearch", back_populates="user")
electronic_invoices = relationship("ElectronicInvoice", back_populates="user")
"""
