"""Simplified Document Models for TDD Implementation.

Basic document models that work with the current test suite.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class DocumentType(str, Enum):
    """Supported document types for Italian tax professionals"""

    PDF = "pdf"
    EXCEL_XLSX = "xlsx"
    EXCEL_XLS = "xls"
    CSV = "csv"
    XML = "xml"  # For Fattura Elettronica
    WORD_DOCX = "docx"  # Word documents
    IMAGE_JPEG = "jpeg"  # Images (JPEG)
    IMAGE_PNG = "png"  # Images (PNG)


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


class DocumentStatus(str, Enum):
    """Document lifecycle status including GDPR states"""

    ACTIVE = "active"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    DELETED = "deleted"
    SCHEDULED_DELETION = "scheduled_deletion"


class ItalianDocumentCategory(str, Enum):
    """Italian tax and legal document categories"""

    # Tax documents
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
    # Legal documents
    CITAZIONE = "citazione"
    RICORSO = "ricorso"
    DECRETO_INGIUNTIVO = "decreto_ingiuntivo"
    ATTO_GIUDIZIARIO = "atto_giudiziario"
    DIFFIDA = "diffida"
    CONTRATTO = "contratto"
    VERBALE = "verbale"
    SENTENZA = "sentenza"
    ORDINANZA = "ordinanza"
    PRECETTO = "precetto"
    COMPARSA = "comparsa"
    MEMORIA = "memoria"
    OTHER = "other"


class Document(SQLModel):
    """Document model with GDPR compliance fields"""

    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    user_id: int | None = None  # Must be int to match User.id
    filename: str = ""
    original_filename: str = ""
    file_type: str = ""
    file_size: int = 0
    storage_path: str | None = None
    extracted_text: str | None = None
    extracted_data: dict[str, Any] | None = None
    document_category: str | None = None
    document_confidence: float | None = None
    processing_status: str = ProcessingStatus.UPLOADED.value
    status: str = DocumentStatus.ACTIVE.value
    expires_at: datetime | None = None

    # Processing fields
    processing_started_at: datetime | None = None
    processing_completed_at: datetime | None = None
    processing_duration_seconds: int | None = None
    error_message: str | None = None

    # Analysis tracking
    analysis_count: int = 0
    last_analyzed_at: datetime | None = None

    # GDPR and security
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    upload_ip: str | None = None
    virus_scan_status: str | None = None
    virus_scan_result: str | None = None
    mime_type: str | None = None
    file_hash: str | None = None

    # Audit fields
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None
    processed_at: datetime | None = None

    # Additional GDPR fields
    is_deleted: bool = False

    # GDPR fields
    deleted_at: datetime | None = None
    deletion_reason: str | None = None
    scheduled_deletion_date: datetime | None = None
    scheduled_deletion_reason: str | None = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(hours=48)

    @property
    def is_expired(self) -> bool:
        """Check if document has expired"""
        return self.expires_at and datetime.utcnow() > self.expires_at

    def to_dict(self, include_content: bool = False) -> dict[str, Any]:
        """Convert document to dictionary for API responses"""
        doc_dict = {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "file_size_mb": round(self.file_size / (1024 * 1024), 2) if self.file_size else 0,
            "document_category": self.document_category,
            "document_confidence": self.document_confidence,
            "processing_status": self.processing_status,
            "status": self.status,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired,
            "upload_timestamp": self.upload_timestamp.isoformat(),
            "processing_started_at": self.processing_started_at.isoformat() if self.processing_started_at else None,
            "processing_completed_at": self.processing_completed_at.isoformat()
            if self.processing_completed_at
            else None,
            "processing_duration_seconds": self.processing_duration_seconds,
            "analysis_count": self.analysis_count,
            "last_analyzed_at": self.last_analyzed_at.isoformat() if self.last_analyzed_at else None,
            "error_message": self.error_message,
            "virus_scan_status": self.virus_scan_status,
            "is_deleted": self.is_deleted,
        }

        if include_content:
            doc_dict.update(
                {
                    "extracted_text": self.extracted_text,
                    "extracted_data": self.extracted_data,
                    "storage_path": self.storage_path,
                }
            )

        return doc_dict


class DocumentAnalysis(SQLModel):
    """Document analysis model for storing AI analysis results"""

    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    document_id: UUID | None = None
    user_id: int | None = None  # Must be int to match User.id
    query: str = ""
    analysis_type: str = "general"
    analysis_result: dict[str, Any] | None = None
    ai_response: str | None = None
    confidence_score: float | None = None
    llm_model: str | None = None
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    duration_seconds: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert analysis to dictionary for API responses"""
        return {
            "id": str(self.id),
            "document_id": str(self.document_id) if self.document_id else None,
            "user_id": str(self.user_id) if self.user_id else None,
            "query": self.query,
            "analysis_type": self.analysis_type,
            "analysis_result": self.analysis_result,
            "ai_response": self.ai_response,
            "confidence_score": self.confidence_score,
            "llm_model": self.llm_model,
            "requested_at": self.requested_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
        }


# Configuration
DOCUMENT_CONFIG = {
    "MAX_FILE_SIZE_MB": 10,
    "MAX_FILES_PER_UPLOAD": 5,
    "SUPPORTED_MIME_TYPES": {
        "application/pdf": DocumentType.PDF,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": DocumentType.EXCEL_XLSX,
        "application/vnd.ms-excel": DocumentType.EXCEL_XLS,
        "text/csv": DocumentType.CSV,
        "application/xml": DocumentType.XML,
        "text/xml": DocumentType.XML,
        # Word documents (DEV-007)
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentType.WORD_DOCX,
        # Images (DEV-007)
        "image/jpeg": DocumentType.IMAGE_JPEG,
        "image/png": DocumentType.IMAGE_PNG,
    },
    "PROCESSING_TIMEOUT_SECONDS": 300,
    "CLEANUP_INTERVAL_HOURS": 1,
    "DEFAULT_EXPIRATION_HOURS": 48,
}

# Italian tax and legal document patterns for classification
ITALIAN_DOCUMENT_PATTERNS = {
    # Tax documents
    ItalianDocumentCategory.FATTURA_ELETTRONICA: [
        r"fattura elettronica",
        r"p\.iva",
        r"partita iva",
        r"codice destinatario",
        r"progressivo invio",
        r"formato trasmissione",
    ],
    ItalianDocumentCategory.F24: [r"modello f24", r"f24", r"codice tributo", r"versamento", r"ravvedimento"],
    ItalianDocumentCategory.DICHIARAZIONE_730: [
        r"modello 730",
        r"730",
        r"dichiarazione dei redditi",
        r"sostituto d'imposta",
    ],
    ItalianDocumentCategory.DICHIARAZIONE_UNICO: [
        r"modello unico",
        r"redditi pf",
        r"quadro r[a-z]",
        r"dichiarazione annuale",
    ],
    ItalianDocumentCategory.BILANCIO: [r"stato patrimoniale", r"conto economico", r"bilancio", r"nota integrativa"],
    ItalianDocumentCategory.CERTIFICAZIONE_UNICA: [
        r"certificazione unica",
        r"cu",
        r"sostituto d'imposta",
        r"redditi lavoro dipendente",
    ],
    # Legal documents
    ItalianDocumentCategory.CITAZIONE: [
        r"cita(zione)? in giudizio",
        r"tribunale (civile|penale) di",
        r"convenuto",
        r"attore",
        r"comparire",
        r"udienza fissata",
        r"art\.?\s*163",
        r"art\.?\s*164",
        r"vocatio in ius",
        r"editio actionis",
    ],
    ItalianDocumentCategory.RICORSO: [
        r"ricorso",
        r"ricorrente",
        r"resistente",
        r"tar",
        r"consiglio di stato",
        r"commissione tributaria",
        r"giudice di pace",
        r"impugna(zione)?",
        r"annullamento",
    ],
    ItalianDocumentCategory.DECRETO_INGIUNTIVO: [
        r"decreto ingiuntivo",
        r"ingiunge",
        r"pagamento",
        r"creditore",
        r"debitore",
        r"art\.?\s*633",
        r"monitorio",
        r"opposizione a decreto",
    ],
    ItalianDocumentCategory.DIFFIDA: [
        r"diffida",
        r"messa in mora",
        r"costituzione in mora",
        r"art\.?\s*1219",
        r"adempiere",
        r"entro (il termine|giorni)",
        r"decorso inutilmente",
    ],
    ItalianDocumentCategory.CONTRATTO: [
        r"contratto",
        r"parti contraenti",
        r"oggetto del contratto",
        r"corrispettivo",
        r"clausole",
        r"condizioni generali",
        r"sottoscrizione",
        r"data di stipula",
    ],
    ItalianDocumentCategory.SENTENZA: [
        r"sentenza",
        r"pronuncia",
        r"dispositivo",
        r"motivazione",
        r"p\.q\.m\.",
        r"condanna",
        r"assolve",
        r"rigetta",
        r"accoglie",
    ],
    ItalianDocumentCategory.PRECETTO: [
        r"atto di precetto",
        r"precetto",
        r"titolo esecutivo",
        r"formula esecutiva",
        r"art\.?\s*480",
        r"ingiunzione di pagare",
        r"pignoramento",
    ],
    ItalianDocumentCategory.COMPARSA: [
        r"comparsa di (risposta|costituzione)",
        r"eccezioni",
        r"domande riconvenzionali",
        r"art\.?\s*167",
        r"costituzione in giudizio",
        r"conclusioni",
    ],
}
