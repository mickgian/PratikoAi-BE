"""Tests for simplified document models."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.models.document_simple import (
    DOCUMENT_CONFIG,
    ITALIAN_DOCUMENT_PATTERNS,
    Document,
    DocumentAnalysis,
    DocumentStatus,
    DocumentType,
    ItalianDocumentCategory,
    ProcessingStatus,
)


class TestDocumentType:
    """Test DocumentType enum."""

    def test_document_type_values(self):
        """Test that document types have correct values."""
        assert DocumentType.PDF.value == "pdf"
        assert DocumentType.EXCEL_XLSX.value == "xlsx"
        assert DocumentType.EXCEL_XLS.value == "xls"
        assert DocumentType.CSV.value == "csv"
        assert DocumentType.XML.value == "xml"

    def test_document_type_enum_members(self):
        """Test that all expected document types exist."""
        expected = {"PDF", "EXCEL_XLSX", "EXCEL_XLS", "CSV", "XML", "WORD_DOCX", "IMAGE_JPEG", "IMAGE_PNG"}
        actual = {member.name for member in DocumentType}
        assert actual == expected


class TestProcessingStatus:
    """Test ProcessingStatus enum."""

    def test_processing_status_values(self):
        """Test that processing statuses have correct values."""
        assert ProcessingStatus.UPLOADED.value == "uploaded"
        assert ProcessingStatus.VALIDATING.value == "validating"
        assert ProcessingStatus.PROCESSING.value == "processing"
        assert ProcessingStatus.EXTRACTING.value == "extracting"
        assert ProcessingStatus.ANALYZING.value == "analyzing"
        assert ProcessingStatus.COMPLETED.value == "completed"
        assert ProcessingStatus.FAILED.value == "failed"
        assert ProcessingStatus.EXPIRED.value == "expired"

    def test_processing_status_enum_members(self):
        """Test that all expected processing statuses exist."""
        expected = {
            "UPLOADED",
            "VALIDATING",
            "PROCESSING",
            "EXTRACTING",
            "ANALYZING",
            "COMPLETED",
            "FAILED",
            "EXPIRED",
        }
        actual = {member.name for member in ProcessingStatus}
        assert actual == expected


class TestDocumentStatus:
    """Test DocumentStatus enum."""

    def test_document_status_values(self):
        """Test that document statuses have correct values."""
        assert DocumentStatus.ACTIVE.value == "active"
        assert DocumentStatus.PROCESSING.value == "processing"
        assert DocumentStatus.COMPLETED.value == "completed"
        assert DocumentStatus.FAILED.value == "failed"
        assert DocumentStatus.EXPIRED.value == "expired"
        assert DocumentStatus.DELETED.value == "deleted"
        assert DocumentStatus.SCHEDULED_DELETION.value == "scheduled_deletion"

    def test_document_status_enum_members(self):
        """Test that all expected document statuses exist."""
        expected = {
            "ACTIVE",
            "PROCESSING",
            "COMPLETED",
            "FAILED",
            "EXPIRED",
            "DELETED",
            "SCHEDULED_DELETION",
        }
        actual = {member.name for member in DocumentStatus}
        assert actual == expected


class TestItalianDocumentCategory:
    """Test ItalianDocumentCategory enum."""

    def test_italian_document_category_tax_values(self):
        """Test tax document category values."""
        assert ItalianDocumentCategory.FATTURA_ELETTRONICA.value == "fattura_elettronica"
        assert ItalianDocumentCategory.F24.value == "f24"
        assert ItalianDocumentCategory.DICHIARAZIONE_730.value == "dichiarazione_730"
        assert ItalianDocumentCategory.DICHIARAZIONE_UNICO.value == "dichiarazione_unico"
        assert ItalianDocumentCategory.BILANCIO.value == "bilancio"
        assert ItalianDocumentCategory.CERTIFICAZIONE_UNICA.value == "certificazione_unica"

    def test_italian_document_category_legal_values(self):
        """Test legal document category values."""
        assert ItalianDocumentCategory.CITAZIONE.value == "citazione"
        assert ItalianDocumentCategory.RICORSO.value == "ricorso"
        assert ItalianDocumentCategory.DECRETO_INGIUNTIVO.value == "decreto_ingiuntivo"
        assert ItalianDocumentCategory.SENTENZA.value == "sentenza"
        assert ItalianDocumentCategory.CONTRATTO.value == "contratto"

    def test_italian_document_category_enum_members_count(self):
        """Test that all expected categories exist."""
        # Should have 24 categories (11 tax + 12 legal + OTHER)
        assert len(ItalianDocumentCategory) == 24


class TestDocument:
    """Test Document model."""

    def test_create_document_minimal(self):
        """Test creating document with minimal fields."""
        doc = Document(
            filename="test.pdf",
            original_filename="test.pdf",
            file_type="pdf",
        )

        assert doc.filename == "test.pdf"
        assert doc.original_filename == "test.pdf"
        assert doc.file_type == "pdf"
        assert doc.file_size == 0  # Default
        assert doc.processing_status == ProcessingStatus.UPLOADED.value
        assert doc.status == DocumentStatus.ACTIVE.value
        assert doc.is_deleted is False
        assert doc.analysis_count == 0

    def test_document_auto_expiration(self):
        """Test that document automatically gets expiration date."""
        doc = Document(filename="test.pdf")

        assert doc.expires_at is not None
        # Should expire in about 48 hours
        expected_expiry = datetime.utcnow() + timedelta(hours=48)
        time_diff = abs((doc.expires_at - expected_expiry).total_seconds())
        assert time_diff < 5  # Within 5 seconds

    def test_document_with_user(self):
        """Test document with user ID."""
        user_id = 12345  # User.id is int, not UUID
        doc = Document(
            user_id=user_id,
            filename="user_doc.pdf",
        )

        assert doc.user_id == user_id

    def test_document_with_file_info(self):
        """Test document with complete file information."""
        doc = Document(
            filename="invoice.pdf",
            original_filename="Fattura_2025_001.pdf",
            file_type="pdf",
            file_size=1024000,  # 1MB
            mime_type="application/pdf",
            file_hash="abc123def456",
        )

        assert doc.file_size == 1024000
        assert doc.mime_type == "application/pdf"
        assert doc.file_hash == "abc123def456"

    def test_document_with_storage_path(self):
        """Test document with storage path."""
        doc = Document(
            filename="test.pdf",
            storage_path="/uploads/2025/01/abc123-test.pdf",
        )

        assert doc.storage_path == "/uploads/2025/01/abc123-test.pdf"

    def test_document_with_extracted_data(self):
        """Test document with extracted text and data."""
        extracted_data = {
            "category": "fattura_elettronica",
            "partita_iva": "IT12345678901",
            "total_amount": 1234.56,
        }

        doc = Document(
            filename="invoice.pdf",
            extracted_text="Fattura Elettronica n. 001/2025...",
            extracted_data=extracted_data,
            document_category="fattura_elettronica",
            document_confidence=0.95,
        )

        assert doc.extracted_text is not None
        assert doc.extracted_data == extracted_data
        assert doc.document_category == "fattura_elettronica"
        assert doc.document_confidence == 0.95

    def test_document_processing_lifecycle(self):
        """Test document processing status changes."""
        doc = Document(filename="test.pdf")
        assert doc.processing_status == ProcessingStatus.UPLOADED.value

        # Simulate processing
        doc.processing_status = ProcessingStatus.PROCESSING.value
        doc.processing_started_at = datetime.utcnow()
        assert doc.processing_status == ProcessingStatus.PROCESSING.value

        # Simulate completion
        doc.processing_status = ProcessingStatus.COMPLETED.value
        doc.processing_completed_at = datetime.utcnow()
        doc.processing_duration_seconds = 15
        assert doc.processing_status == ProcessingStatus.COMPLETED.value
        assert doc.processing_duration_seconds == 15

    def test_document_processing_failure(self):
        """Test document processing failure."""
        doc = Document(filename="test.pdf")

        doc.processing_status = ProcessingStatus.FAILED.value
        doc.error_message = "Failed to extract text from PDF"

        assert doc.processing_status == ProcessingStatus.FAILED.value
        assert doc.error_message is not None

    def test_document_analysis_tracking(self):
        """Test document analysis count tracking."""
        doc = Document(filename="test.pdf")
        assert doc.analysis_count == 0

        doc.analysis_count += 1
        doc.last_analyzed_at = datetime.utcnow()

        assert doc.analysis_count == 1
        assert doc.last_analyzed_at is not None

    def test_document_upload_tracking(self):
        """Test document upload tracking."""
        doc = Document(
            filename="test.pdf",
            upload_ip="192.168.1.100",
        )

        assert doc.upload_timestamp is not None
        assert isinstance(doc.upload_timestamp, datetime)
        assert doc.upload_ip == "192.168.1.100"

    def test_document_virus_scan(self):
        """Test document virus scan fields."""
        doc = Document(
            filename="test.pdf",
            virus_scan_status="completed",
            virus_scan_result="clean",
        )

        assert doc.virus_scan_status == "completed"
        assert doc.virus_scan_result == "clean"

    def test_document_is_expired_false(self):
        """Test is_expired property when not expired."""
        doc = Document(filename="test.pdf")
        # Freshly created document should not be expired
        assert doc.is_expired is False

    def test_document_is_expired_true(self):
        """Test is_expired property when expired."""
        doc = Document(filename="test.pdf")
        # Set expiration to past
        doc.expires_at = datetime.utcnow() - timedelta(hours=1)

        assert doc.is_expired is True

    def test_document_is_expired_future_date(self):
        """Test is_expired property with future expiration date."""
        doc = Document(filename="test.pdf")
        # Set expiration to future
        doc.expires_at = datetime.utcnow() + timedelta(hours=100)

        # Should not be expired
        assert doc.is_expired is False

    def test_document_gdpr_deletion(self):
        """Test GDPR deletion fields."""
        doc = Document(
            filename="test.pdf",
            is_deleted=True,
            deleted_at=datetime.utcnow(),
            deletion_reason="User requested deletion",
            status=DocumentStatus.DELETED.value,
        )

        assert doc.is_deleted is True
        assert doc.deleted_at is not None
        assert doc.deletion_reason == "User requested deletion"
        assert doc.status == DocumentStatus.DELETED.value

    def test_document_scheduled_deletion(self):
        """Test scheduled deletion fields."""
        scheduled_date = datetime.utcnow() + timedelta(days=30)

        doc = Document(
            filename="test.pdf",
            status=DocumentStatus.SCHEDULED_DELETION.value,
            scheduled_deletion_date=scheduled_date,
            scheduled_deletion_reason="GDPR retention period expired",
        )

        assert doc.status == DocumentStatus.SCHEDULED_DELETION.value
        assert doc.scheduled_deletion_date == scheduled_date
        assert "GDPR" in doc.scheduled_deletion_reason

    def test_document_to_dict_minimal(self):
        """Test to_dict conversion without content."""
        doc = Document(
            filename="test.pdf",
            original_filename="test.pdf",
            file_type="pdf",
            file_size=1024000,
        )

        doc_dict = doc.to_dict(include_content=False)

        assert "id" in doc_dict
        assert doc_dict["filename"] == "test.pdf"
        assert doc_dict["file_size"] == 1024000
        assert doc_dict["file_size_mb"] == 0.98  # ~1MB
        assert "extracted_text" not in doc_dict
        assert "extracted_data" not in doc_dict
        assert "storage_path" not in doc_dict

    def test_document_to_dict_with_content(self):
        """Test to_dict conversion with content."""
        doc = Document(
            filename="test.pdf",
            extracted_text="Test content",
            extracted_data={"key": "value"},
            storage_path="/uploads/test.pdf",
        )

        doc_dict = doc.to_dict(include_content=True)

        assert doc_dict["extracted_text"] == "Test content"
        assert doc_dict["extracted_data"] == {"key": "value"}
        assert doc_dict["storage_path"] == "/uploads/test.pdf"

    def test_document_to_dict_timestamps(self):
        """Test to_dict timestamp conversion."""
        now = datetime.utcnow()
        doc = Document(
            filename="test.pdf",
            processing_started_at=now,
            processing_completed_at=now + timedelta(seconds=10),
            last_analyzed_at=now,
        )

        doc_dict = doc.to_dict()

        assert "upload_timestamp" in doc_dict
        assert doc_dict["processing_started_at"] is not None
        assert doc_dict["processing_completed_at"] is not None
        assert doc_dict["last_analyzed_at"] is not None

    def test_document_to_dict_handles_none_values(self):
        """Test to_dict handles None values correctly."""
        doc = Document(
            filename="test.pdf",
            user_id=None,
            processing_started_at=None,
            processing_completed_at=None,
            last_analyzed_at=None,
        )

        doc_dict = doc.to_dict()

        assert doc_dict["user_id"] is None
        assert doc_dict["processing_started_at"] is None
        assert doc_dict["processing_completed_at"] is None
        assert doc_dict["last_analyzed_at"] is None
        # expires_at should be set automatically, not None
        assert doc_dict["expires_at"] is not None

    def test_document_file_size_mb_calculation(self):
        """Test file size MB calculation in to_dict."""
        doc = Document(
            filename="test.pdf",
            file_size=5242880,  # 5MB
        )

        doc_dict = doc.to_dict()

        assert doc_dict["file_size_mb"] == 5.0

    def test_document_file_size_mb_zero(self):
        """Test file size MB when file_size is 0."""
        doc = Document(filename="test.pdf", file_size=0)

        doc_dict = doc.to_dict()

        assert doc_dict["file_size_mb"] == 0


class TestDocumentAnalysis:
    """Test DocumentAnalysis model."""

    def test_create_analysis_minimal(self):
        """Test creating analysis with required fields."""
        analysis = DocumentAnalysis(
            query="Analizza questo documento",
        )

        assert analysis.query == "Analizza questo documento"
        assert analysis.analysis_type == "general"  # Default
        assert analysis.requested_at is not None
        assert isinstance(analysis.requested_at, datetime)
        assert analysis.completed_at is None
        assert analysis.duration_seconds is None

    def test_analysis_with_document(self):
        """Test analysis with document and user references."""
        doc_id = uuid4()
        user_id = 12345  # User.id is int, not UUID

        analysis = DocumentAnalysis(
            document_id=doc_id,
            user_id=user_id,
            query="Extract invoice data",
        )

        assert analysis.document_id == doc_id
        assert analysis.user_id == user_id

    def test_analysis_with_result(self):
        """Test analysis with results."""
        result_data = {
            "invoice_number": "001/2025",
            "total_amount": 1234.56,
            "tax": 271.60,
        }

        analysis = DocumentAnalysis(
            query="Extract invoice data",
            analysis_type="invoice_extraction",
            analysis_result=result_data,
            ai_response="Estratti i seguenti dati dalla fattura...",
            confidence_score=0.92,
            llm_model="gpt-4",
        )

        assert analysis.analysis_type == "invoice_extraction"
        assert analysis.analysis_result == result_data
        assert analysis.ai_response is not None
        assert analysis.confidence_score == 0.92
        assert analysis.llm_model == "gpt-4"

    def test_analysis_completion_tracking(self):
        """Test analysis completion tracking."""
        analysis = DocumentAnalysis(
            query="Test query",
            completed_at=datetime.utcnow(),
            duration_seconds=5,
        )

        assert analysis.completed_at is not None
        assert analysis.duration_seconds == 5

    def test_analysis_to_dict(self):
        """Test to_dict conversion."""
        doc_id = uuid4()
        user_id = 12345  # User.id is int, not UUID

        analysis = DocumentAnalysis(
            document_id=doc_id,
            user_id=user_id,
            query="Test query",
            analysis_type="test",
            analysis_result={"key": "value"},
            ai_response="Response text",
            confidence_score=0.85,
            llm_model="gpt-3.5-turbo",
        )

        analysis_dict = analysis.to_dict()

        assert "id" in analysis_dict
        assert analysis_dict["document_id"] == str(doc_id)
        assert analysis_dict["user_id"] == str(user_id)
        assert analysis_dict["query"] == "Test query"
        assert analysis_dict["analysis_type"] == "test"
        assert analysis_dict["analysis_result"] == {"key": "value"}
        assert analysis_dict["ai_response"] == "Response text"
        assert analysis_dict["confidence_score"] == 0.85
        assert analysis_dict["llm_model"] == "gpt-3.5-turbo"

    def test_analysis_to_dict_timestamps(self):
        """Test to_dict timestamp conversion."""
        now = datetime.utcnow()
        analysis = DocumentAnalysis(
            query="Test",
            completed_at=now,
        )

        analysis_dict = analysis.to_dict()

        assert "requested_at" in analysis_dict
        assert "completed_at" in analysis_dict
        assert analysis_dict["completed_at"] is not None

    def test_analysis_to_dict_handles_none(self):
        """Test to_dict handles None values."""
        analysis = DocumentAnalysis(
            query="Test",
            document_id=None,
            user_id=None,
            completed_at=None,
        )

        analysis_dict = analysis.to_dict()

        assert analysis_dict["document_id"] is None
        assert analysis_dict["user_id"] is None
        assert analysis_dict["completed_at"] is None


class TestDocumentConfig:
    """Test DOCUMENT_CONFIG constant."""

    def test_config_has_required_keys(self):
        """Test that config has all required keys."""
        required_keys = {
            "MAX_FILE_SIZE_MB",
            "MAX_FILES_PER_UPLOAD",
            "SUPPORTED_MIME_TYPES",
            "PROCESSING_TIMEOUT_SECONDS",
            "CLEANUP_INTERVAL_HOURS",
            "DEFAULT_EXPIRATION_HOURS",
        }

        assert set(DOCUMENT_CONFIG.keys()) == required_keys

    def test_config_values(self):
        """Test config values."""
        assert DOCUMENT_CONFIG["MAX_FILE_SIZE_MB"] == 10
        assert DOCUMENT_CONFIG["MAX_FILES_PER_UPLOAD"] == 5
        assert DOCUMENT_CONFIG["PROCESSING_TIMEOUT_SECONDS"] == 300
        assert DOCUMENT_CONFIG["CLEANUP_INTERVAL_HOURS"] == 1
        assert DOCUMENT_CONFIG["DEFAULT_EXPIRATION_HOURS"] == 48

    def test_config_supported_mime_types(self):
        """Test supported MIME types mapping."""
        mime_types = DOCUMENT_CONFIG["SUPPORTED_MIME_TYPES"]

        assert mime_types["application/pdf"] == DocumentType.PDF
        assert (
            mime_types["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"] == DocumentType.EXCEL_XLSX
        )
        assert mime_types["application/vnd.ms-excel"] == DocumentType.EXCEL_XLS
        assert mime_types["text/csv"] == DocumentType.CSV
        assert mime_types["application/xml"] == DocumentType.XML
        assert mime_types["text/xml"] == DocumentType.XML


class TestItalianDocumentPatterns:
    """Test ITALIAN_DOCUMENT_PATTERNS constant."""

    def test_patterns_has_tax_categories(self):
        """Test that patterns include tax document categories."""
        assert ItalianDocumentCategory.FATTURA_ELETTRONICA in ITALIAN_DOCUMENT_PATTERNS
        assert ItalianDocumentCategory.F24 in ITALIAN_DOCUMENT_PATTERNS
        assert ItalianDocumentCategory.DICHIARAZIONE_730 in ITALIAN_DOCUMENT_PATTERNS
        assert ItalianDocumentCategory.BILANCIO in ITALIAN_DOCUMENT_PATTERNS
        assert ItalianDocumentCategory.CERTIFICAZIONE_UNICA in ITALIAN_DOCUMENT_PATTERNS

    def test_patterns_has_legal_categories(self):
        """Test that patterns include legal document categories."""
        assert ItalianDocumentCategory.CITAZIONE in ITALIAN_DOCUMENT_PATTERNS
        assert ItalianDocumentCategory.RICORSO in ITALIAN_DOCUMENT_PATTERNS
        assert ItalianDocumentCategory.DECRETO_INGIUNTIVO in ITALIAN_DOCUMENT_PATTERNS
        assert ItalianDocumentCategory.SENTENZA in ITALIAN_DOCUMENT_PATTERNS
        assert ItalianDocumentCategory.CONTRATTO in ITALIAN_DOCUMENT_PATTERNS

    def test_fattura_elettronica_patterns(self):
        """Test Fattura Elettronica patterns."""
        patterns = ITALIAN_DOCUMENT_PATTERNS[ItalianDocumentCategory.FATTURA_ELETTRONICA]

        assert any("fattura elettronica" in p for p in patterns)
        assert any("p\\.iva" in p or "partita iva" in p for p in patterns)
        assert any("codice destinatario" in p for p in patterns)

    def test_citazione_patterns(self):
        """Test Citazione (summons) patterns."""
        patterns = ITALIAN_DOCUMENT_PATTERNS[ItalianDocumentCategory.CITAZIONE]

        assert any("cita" in p for p in patterns)
        assert any("tribunale" in p for p in patterns)
        assert any("convenuto" in p or "attore" in p for p in patterns)

    def test_contratto_patterns(self):
        """Test Contratto (contract) patterns."""
        patterns = ITALIAN_DOCUMENT_PATTERNS[ItalianDocumentCategory.CONTRATTO]

        assert any("contratto" in p for p in patterns)
        assert any("parti contraenti" in p for p in patterns)
        assert any("clausole" in p or "condizioni" in p for p in patterns)

    def test_sentenza_patterns(self):
        """Test Sentenza (judgment) patterns."""
        patterns = ITALIAN_DOCUMENT_PATTERNS[ItalianDocumentCategory.SENTENZA]

        assert any("sentenza" in p for p in patterns)
        assert any("dispositivo" in p for p in patterns)
        assert any("condanna" in p or "accoglie" in p or "rigetta" in p for p in patterns)

    def test_all_patterns_are_lists(self):
        """Test that all pattern values are lists."""
        for category, patterns in ITALIAN_DOCUMENT_PATTERNS.items():
            assert isinstance(patterns, list)
            assert len(patterns) > 0

    def test_all_patterns_are_strings(self):
        """Test that all patterns are strings."""
        for category, patterns in ITALIAN_DOCUMENT_PATTERNS.items():
            for pattern in patterns:
                assert isinstance(pattern, str)
