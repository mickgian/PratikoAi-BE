"""
Document Upload and Processing Models.

Database models for handling document uploads, processing, and metadata
for Italian tax professional document analysis.
"""

from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy.dialects.postgresql import JSONB

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

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    
    # File metadata
    filename: str = Field(max_length=500)  # Stored filename (UUID-based)
    original_filename: str = Field(max_length=500)  # Original user filename
    file_type: str = Field(max_length=20)  # DocumentType enum
    file_size: int = Field()  # Size in bytes
    mime_type: str = Field(max_length=100)
    file_hash: str = Field(max_length=64, index=True)  # SHA-256 hash
    
    # Upload tracking
    upload_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
    upload_ip: Optional[str] = Field(default=None, max_length=45)  # IPv4/IPv6 address
    
    # Processing status
    processing_status: str = Field(default=ProcessingStatus.UPLOADED.value, max_length=20, index=True)
    processing_started_at: Optional[datetime] = Field(default=None)
    processing_completed_at: Optional[datetime] = Field(default=None)
    processing_duration_seconds: Optional[int] = Field(default=None)
    
    # Document classification
    document_category: Optional[str] = Field(default=None, max_length=50)  # ItalianDocumentCategory enum
    document_confidence: Optional[int] = Field(default=None)  # 0-100 confidence score
    
    # Extracted data
    extracted_text: Optional[str] = Field(default=None)
    extracted_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))  # Structured data extraction
    extracted_tables: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))  # Tabular data from Excel/CSV
    
    # Processing results
    processing_log: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))  # Processing steps and results
    error_message: Optional[str] = Field(default=None)
    warnings: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))  # Non-fatal processing warnings
    
    # Security and compliance
    virus_scan_status: str = Field(default="pending", max_length=20)
    virus_scan_result: Optional[str] = Field(default=None, max_length=100)
    is_sensitive_data: bool = Field(default=False)
    
    # Expiration and cleanup
    expires_at: datetime = Field(index=True)
    is_deleted: bool = Field(default=False, index=True)
    deleted_at: Optional[datetime] = Field(default=None)
    
    # Analytics
    analysis_count: int = Field(default=0)
    last_analyzed_at: Optional[datetime] = Field(default=None)
    
    # Relationships
    analyses: List["DocumentAnalysis"] = Relationship(back_populates="document", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.expires_at:
            self.expires_at = datetime.now(UTC) + timedelta(hours=48)  # 48-hour default expiration
    
    @property
    def is_expired(self) -> bool:
        """Check if document has expired"""
        return datetime.now(UTC) > self.expires_at
    
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


class DocumentAnalysis(BaseModel, table=True):
    """Document analysis requests and results"""
    __tablename__ = "document_analyses"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    document_id: UUID = Field(foreign_key="documents.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    
    # Analysis request
    query: str = Field()  # User's analysis question
    analysis_type: str = Field(default="general", max_length=50)
    
    # Analysis timing
    requested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = Field(default=None)
    duration_seconds: Optional[int] = Field(default=None)
    
    # Analysis results
    analysis_result: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))  # Structured analysis results
    ai_response: Optional[str] = Field(default=None)  # Natural language response
    confidence_score: Optional[int] = Field(default=None)  # 0-100 confidence
    
    # Context and metadata
    context_used: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))  # Document excerpts used
    llm_model: Optional[str] = Field(default=None, max_length=50)  # Model used for analysis
    cost: Optional[int] = Field(default=None)  # Cost in micro-euros (€0.000001)
    
    # Quality and validation
    quality_score: Optional[int] = Field(default=None)  # 0-100 quality score
    validation_status: str = Field(default="pending", max_length=20)
    expert_validated: bool = Field(default=False)
    
    # Relationships
    document: Optional["Document"] = Relationship(back_populates="analyses")
    
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


class DocumentProcessingJob(BaseModel, table=True):
    """Document processing job queue"""
    __tablename__ = "document_processing_jobs"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    document_id: UUID = Field(foreign_key="documents.id", index=True)
    
    # Job details
    job_type: str = Field(max_length=50)  # text_extraction, data_extraction, analysis
    priority: int = Field(default=50)  # 1-100, higher = more priority
    
    # Job status
    status: str = Field(default="queued", max_length=20, index=True)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    
    # Job execution
    worker_id: Optional[str] = Field(default=None, max_length=100)  # Processing worker identifier
    attempts: int = Field(default=0)
    max_attempts: int = Field(default=3)
    
    # Results and errors
    result: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))
    error_message: Optional[str] = Field(default=None)
    
    # Expiration
    expires_at: datetime = Field(index=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.expires_at:
            self.expires_at = datetime.now(UTC) + timedelta(hours=24)  # 24-hour job expiration


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