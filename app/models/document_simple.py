"""
Simplified Document Models for TDD Implementation.

Basic document models that work with the current test suite.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field


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


class Document(SQLModel):
  """Document model with GDPR compliance fields"""
  id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
  user_id: Optional[UUID] = None
  filename: str = ""
  original_filename: str = ""
  file_type: str = ""
  file_size: int = 0
  storage_path: Optional[str] = None
  extracted_text: Optional[str] = None
  extracted_data: Optional[Dict[str, Any]] = None
  processing_status: str = ProcessingStatus.UPLOADED.value
  status: str = DocumentStatus.ACTIVE.value
  expires_at: Optional[datetime] = None
  
  # Audit fields
  created_at: datetime = Field(default_factory=datetime.utcnow)
  updated_at: Optional[datetime] = None
  processed_at: Optional[datetime] = None
  
  # GDPR fields
  deleted_at: Optional[datetime] = None
  deletion_reason: Optional[str] = None
  scheduled_deletion_date: Optional[datetime] = None
  scheduled_deletion_reason: Optional[str] = None
  
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    if not self.expires_at:
      self.expires_at = datetime.utcnow() + timedelta(hours=48)


class DocumentAnalysis(SQLModel):
  """Simple document analysis model for testing"""
  id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
  document_id: Optional[UUID] = None
  user_id: Optional[UUID] = None
  query: str = ""
  analysis_result: Optional[Dict[str, Any]] = None


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
    "text/xml": DocumentType.XML
  },
  "PROCESSING_TIMEOUT_SECONDS": 300,
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