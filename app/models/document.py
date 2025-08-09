"""
Document Upload and Processing Models.

Database models for handling document uploads, processing, and metadata
for Italian tax professional document analysis.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Relationship, Column, JSON
from sqlalchemy import String, Integer, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID, JSONB

from app.models.base import BaseModel


class DocumentType(str, Enum):
    """Supported document types for Italian tax professionals"""
    PDF = "pdf"
    EXCEL_XLSX = "xlsx"
    EXCEL_XLS = "xls"
    CSV = "csv"
    XML = "xml"  # For Fattura Elettronica


class ProcessingStatus(str, Enum):
    """Document processing status"""
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    PROCESSING = "processing"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class ItalianDocumentCategory(str, Enum):
    """Italian tax document categories"""
    FATTURA_ELETTRONICA = "fattura_elettronica"
    F24 = "f24"
    DICHIARAZIONE_730 = "dichiarazione_730"
    DICHIARAZIONE_UNICO = "dichiarazione_unico"
    BILANCIO = "bilancio"
    STATO_PATRIMONIALE = "stato_patrimoniale"
    CONTO_ECONOMICO = "conto_economico"
    LIBRO_GIORNALE = "libro_giornale"
    CERTIFICAZIONE_UNICA = "certificazione_unica"
    REGISTRO_IVA = "registro_iva"
    QUADRO_RW = "quadro_rw"
    OTHER = "other"


class Document(BaseModel, table=True):
    """Document upload and processing tracking"""
    __tablename__ = "documents"

    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # File metadata
    filename = Column(String(500), nullable=False)  # Stored filename (UUID-based)
    original_filename = Column(String(500), nullable=False)  # Original user filename
    file_type = Column(String(20), nullable=False)  # DocumentType enum
    file_size = Column(Integer, nullable=False)  # Size in bytes
    mime_type = Column(String(100), nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash
    
    # Upload tracking
    upload_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    upload_ip = Column(String(45))  # IPv4/IPv6 address
    
    # Processing status
    processing_status = Column(String(20), default=ProcessingStatus.UPLOADED.value, nullable=False, index=True)
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    processing_duration_seconds = Column(Integer, nullable=True)
    
    # Document classification
    document_category = Column(String(50), nullable=True)  # ItalianDocumentCategory enum
    document_confidence = Column(Integer, nullable=True)  # 0-100 confidence score
    
    # Extracted data
    extracted_text = Column(Text, nullable=True)
    extracted_data = Column(JSONB, nullable=True)  # Structured data extraction
    extracted_tables = Column(JSONB, nullable=True)  # Tabular data from Excel/CSV
    
    # Processing results
    processing_log = Column(JSONB, nullable=True)  # Processing steps and results
    error_message = Column(Text, nullable=True)
    warnings = Column(JSONB, nullable=True)  # Non-fatal processing warnings
    
    # Security and compliance
    virus_scan_status = Column(String(20), default="pending", nullable=False)
    virus_scan_result = Column(String(100), nullable=True)
    is_sensitive_data = Column(Boolean, default=False, nullable=False)
    
    # Expiration and cleanup
    expires_at = Column(DateTime, nullable=False, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
    
    # Analytics
    analysis_count = Column(Integer, default=0, nullable=False)
    last_analyzed_at = Column(DateTime, nullable=True)
    
    # Relationships
    analyses = relationship("DocumentAnalysis", back_populates="document", cascade="all, delete-orphan")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(hours=48)  # 48-hour default expiration
    
    @property
    def is_expired(self) -> bool:
        """Check if document has expired"""
        return datetime.utcnow() > self.expires_at
    
    @property
    def processing_time_seconds(self) -> Optional[int]:
        """Calculate processing time in seconds"""
        if self.processing_started_at and self.processing_completed_at:
            return int((self.processing_completed_at - self.processing_started_at).total_seconds())
        return None
    
    @property
    def file_size_mb(self) -> float:
        """File size in megabytes"""
        return self.file_size / (1024 * 1024)
    
    def to_dict(self, include_content: bool = False) -> Dict[str, Any]:
        """Convert document to dictionary"""
        data = {
            "id": str(self.id),
            "original_filename": self.original_filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "file_size_mb": self.file_size_mb,
            "mime_type": self.mime_type,
            "upload_timestamp": self.upload_timestamp.isoformat() if self.upload_timestamp else None,
            "processing_status": self.processing_status,
            "document_category": self.document_category,
            "document_confidence": self.document_confidence,
            "processing_duration_seconds": self.processing_time_seconds,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired,
            "analysis_count": self.analysis_count,
            "last_analyzed_at": self.last_analyzed_at.isoformat() if self.last_analyzed_at else None
        }
        
        if include_content:
            data.update({
                "extracted_text": self.extracted_text,
                "extracted_data": self.extracted_data,
                "extracted_tables": self.extracted_tables
            })
        
        return data


class DocumentAnalysis(Base):
    """Document analysis requests and results"""
    __tablename__ = "document_analyses"

    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    document_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    user_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Analysis request
    query = Column(Text, nullable=False)  # User's analysis question
    analysis_type = Column(String(50), default="general", nullable=False)
    
    # Analysis timing
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Analysis results
    analysis_result = Column(JSONB, nullable=True)  # Structured analysis results
    ai_response = Column(Text, nullable=True)  # Natural language response
    confidence_score = Column(Integer, nullable=True)  # 0-100 confidence
    
    # Context and metadata
    context_used = Column(JSONB, nullable=True)  # Document excerpts used
    llm_model = Column(String(50), nullable=True)  # Model used for analysis
    cost = Column(Integer, nullable=True)  # Cost in micro-euros (€0.000001)
    
    # Quality and validation
    quality_score = Column(Integer, nullable=True)  # 0-100 quality score
    validation_status = Column(String(20), default="pending", nullable=False)
    expert_validated = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="analyses")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis to dictionary"""
        return {
            "id": str(self.id),
            "document_id": str(self.document_id),
            "query": self.query,
            "analysis_type": self.analysis_type,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "analysis_result": self.analysis_result,
            "ai_response": self.ai_response,
            "confidence_score": self.confidence_score,
            "quality_score": self.quality_score,
            "cost": self.cost,
            "expert_validated": self.expert_validated
        }


class DocumentProcessingJob(Base):
    """Document processing job queue"""
    __tablename__ = "document_processing_jobs"

    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    document_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    
    # Job details
    job_type = Column(String(50), nullable=False)  # text_extraction, data_extraction, analysis
    priority = Column(Integer, default=50, nullable=False)  # 1-100, higher = more priority
    
    # Job status
    status = Column(String(20), default="queued", nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Job execution
    worker_id = Column(String(100), nullable=True)  # Processing worker identifier
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    
    # Results and errors
    result = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Expiration
    expires_at = Column(DateTime, nullable=False, index=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(hours=24)  # 24-hour job expiration


# Document processing configuration
DOCUMENT_CONFIG = {
    "MAX_FILE_SIZE_MB": 10,
    "MAX_FILES_PER_UPLOAD": 5,
    "SUPPORTED_MIME_TYPES": {
        "application/pdf": DocumentType.PDF,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": DocumentType.EXCEL_XLSX,
        "application/vnd.ms-excel": DocumentType.EXCEL_XLS,
        "text/csv": DocumentType.CSV,
        "application/xml": DocumentType.XML,
        "text/xml": DocumentType.XML
    },
    "PROCESSING_TIMEOUT_SECONDS": 300,  # 5 minutes
    "CLEANUP_INTERVAL_HOURS": 1,
    "DEFAULT_EXPIRATION_HOURS": 48
}

# Italian tax document patterns for classification
ITALIAN_DOCUMENT_PATTERNS = {
    ItalianDocumentCategory.FATTURA_ELETTRONICA: [
        r"fattura elettronica", r"p\.iva", r"partita iva", r"codice destinatario",
        r"progressivo invio", r"formato trasmissione"
    ],
    ItalianDocumentCategory.F24: [
        r"modello f24", r"f24", r"codice tributo", r"versamento", r"ravvedimento"
    ],
    ItalianDocumentCategory.DICHIARAZIONE_730: [
        r"modello 730", r"730", r"dichiarazione dei redditi", r"sostituto d'imposta"
    ],
    ItalianDocumentCategory.DICHIARAZIONE_UNICO: [
        r"modello unico", r"redditi pf", r"quadro r[a-z]", r"dichiarazione annuale"
    ],
    ItalianDocumentCategory.BILANCIO: [
        r"stato patrimoniale", r"conto economico", r"bilancio", r"nota integrativa"
    ],
    ItalianDocumentCategory.CERTIFICAZIONE_UNICA: [
        r"certificazione unica", r"cu", r"sostituto d'imposta", r"redditi lavoro dipendente"
    ]
}