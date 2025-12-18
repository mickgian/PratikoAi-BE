"""Tests for document models."""

from datetime import datetime, timedelta
from uuid import UUID

import pytest

from app.models.document import (
    DOCUMENT_CONFIG,
    ITALIAN_DOCUMENT_PATTERNS,
    Document,
    DocumentAnalysis,
    DocumentProcessingJob,
    DocumentType,
    ItalianDocumentCategory,
    ProcessingStatus,
)


class TestDocumentType:
    """Test DocumentType enum."""

    def test_document_types(self):
        """Test all document types are defined."""
        assert DocumentType.PDF == "pdf"
        assert DocumentType.EXCEL_XLSX == "xlsx"
        assert DocumentType.EXCEL_XLS == "xls"
        assert DocumentType.CSV == "csv"
        assert DocumentType.XML == "xml"


class TestProcessingStatus:
    """Test ProcessingStatus enum."""

    def test_processing_statuses(self):
        """Test all processing statuses are defined."""
        assert ProcessingStatus.UPLOADED == "uploaded"
        assert ProcessingStatus.VALIDATING == "validating"
        assert ProcessingStatus.PROCESSING == "processing"
        assert ProcessingStatus.EXTRACTING == "extracting"
        assert ProcessingStatus.ANALYZING == "analyzing"
        assert ProcessingStatus.COMPLETED == "completed"
        assert ProcessingStatus.FAILED == "failed"
        assert ProcessingStatus.EXPIRED == "expired"


class TestItalianDocumentCategory:
    """Test ItalianDocumentCategory enum."""

    def test_italian_categories(self):
        """Test Italian document categories."""
        assert ItalianDocumentCategory.FATTURA_ELETTRONICA == "fattura_elettronica"
        assert ItalianDocumentCategory.F24 == "f24"
        assert ItalianDocumentCategory.DICHIARAZIONE_730 == "dichiarazione_730"
        assert ItalianDocumentCategory.DICHIARAZIONE_UNICO == "dichiarazione_unico"
        assert ItalianDocumentCategory.BILANCIO == "bilancio"
        assert ItalianDocumentCategory.CERTIFICAZIONE_UNICA == "certificazione_unica"
        assert ItalianDocumentCategory.OTHER == "other"


class TestDocument:
    """Test Document model."""

    def test_document_creation(self):
        """Test creating a Document instance."""
        doc = Document(
            user_id=1,
            filename="test.pdf",
            original_filename="original.pdf",
            file_type=DocumentType.PDF.value,
            file_size=1024,
            mime_type="application/pdf",
            file_hash="abc123",
        )

        assert doc.user_id == 1
        assert doc.filename == "test.pdf"
        assert doc.original_filename == "original.pdf"
        assert doc.file_type == DocumentType.PDF.value

    def test_document_has_uuid(self):
        """Test Document gets a UUID."""
        doc = Document(
            user_id=1,
            filename="test.pdf",
            original_filename="test.pdf",
            file_type="pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_hash="abc123",
        )

        assert isinstance(doc.id, UUID)

    def test_document_default_status(self):
        """Test Document has default processing status."""
        doc = Document(
            user_id=1,
            filename="test.pdf",
            original_filename="test.pdf",
            file_type="pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_hash="abc123",
        )

        assert doc.processing_status == ProcessingStatus.UPLOADED.value

    def test_document_default_expiration(self):
        """Test Document sets default expiration."""
        doc = Document(
            user_id=1,
            filename="test.pdf",
            original_filename="test.pdf",
            file_type="pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_hash="abc123",
        )

        # Should expire in ~48 hours
        # Note: Document uses naive datetime (utcnow)
        now = datetime.utcnow()
        time_until_expiry = (doc.expires_at - now).total_seconds()

        # Allow some tolerance for test execution time
        assert 47.9 * 3600 < time_until_expiry < 48.1 * 3600

    def test_is_expired_property(self):
        """Test is_expired property."""
        # Create expired document
        doc = Document(
            user_id=1,
            filename="test.pdf",
            original_filename="test.pdf",
            file_type="pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_hash="abc123",
        )
        # Note: Document uses naive datetime (utcnow)
        doc.expires_at = datetime.utcnow() - timedelta(hours=1)

        assert doc.is_expired is True

    def test_is_not_expired_property(self):
        """Test document is not expired when future expiration."""
        doc = Document(
            user_id=1,
            filename="test.pdf",
            original_filename="test.pdf",
            file_type="pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_hash="abc123",
        )
        # Note: Document uses naive datetime (utcnow)
        doc.expires_at = datetime.utcnow() + timedelta(hours=1)

        assert doc.is_expired is False

    def test_processing_time_seconds_property(self):
        """Test processing_time_seconds property."""
        doc = Document(
            user_id=1,
            filename="test.pdf",
            original_filename="test.pdf",
            file_type="pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_hash="abc123",
        )

        # No processing times set
        assert doc.processing_time_seconds is None

        # Set processing times (using naive datetime to match model)
        doc.processing_started_at = datetime.utcnow()
        doc.processing_completed_at = doc.processing_started_at + timedelta(seconds=30)

        assert doc.processing_time_seconds == 30

    def test_file_size_mb_property(self):
        """Test file_size_mb property."""
        doc = Document(
            user_id=1,
            filename="test.pdf",
            original_filename="test.pdf",
            file_type="pdf",
            file_size=2 * 1024 * 1024,  # 2 MB
            mime_type="application/pdf",
            file_hash="abc123",
        )

        assert doc.file_size_mb == 2.0

    def test_to_dict_without_content(self):
        """Test to_dict without content."""
        doc = Document(
            user_id=1,
            filename="test.pdf",
            original_filename="test.pdf",
            file_type="pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_hash="abc123",
        )

        result = doc.to_dict(include_content=False)

        assert "original_filename" in result
        assert "file_type" in result
        assert "extracted_text" not in result
        assert "extracted_data" not in result

    def test_to_dict_with_content(self):
        """Test to_dict with content."""
        doc = Document(
            user_id=1,
            filename="test.pdf",
            original_filename="test.pdf",
            file_type="pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_hash="abc123",
            extracted_text="Sample text",
        )

        result = doc.to_dict(include_content=True)

        assert "extracted_text" in result
        assert result["extracted_text"] == "Sample text"


class TestDocumentAnalysis:
    """Test DocumentAnalysis model."""

    def test_analysis_creation(self):
        """Test creating a DocumentAnalysis instance."""
        analysis = DocumentAnalysis(
            document_id=UUID("12345678-1234-1234-1234-123456789012"),
            user_id=1,
            query="What is this document about?",
        )

        assert analysis.user_id == 1
        assert analysis.query == "What is this document about?"

    def test_analysis_has_uuid(self):
        """Test DocumentAnalysis gets a UUID."""
        analysis = DocumentAnalysis(
            document_id=UUID("12345678-1234-1234-1234-123456789012"),
            user_id=1,
            query="Test query",
        )

        assert isinstance(analysis.id, UUID)

    def test_analysis_default_type(self):
        """Test DocumentAnalysis has default analysis type."""
        analysis = DocumentAnalysis(
            document_id=UUID("12345678-1234-1234-1234-123456789012"),
            user_id=1,
            query="Test",
        )

        assert analysis.analysis_type == "general"

    def test_analysis_to_dict(self):
        """Test DocumentAnalysis to_dict method."""
        doc_id = UUID("12345678-1234-1234-1234-123456789012")
        analysis = DocumentAnalysis(
            document_id=doc_id,
            user_id=1,
            query="Test query",
            ai_response="Test response",
        )

        result = analysis.to_dict()

        assert "query" in result
        assert result["query"] == "Test query"
        assert "ai_response" in result
        assert result["document_id"] == str(doc_id)


class TestDocumentProcessingJob:
    """Test DocumentProcessingJob model."""

    def test_job_creation(self):
        """Test creating a DocumentProcessingJob."""
        job = DocumentProcessingJob(
            document_id=UUID("12345678-1234-1234-1234-123456789012"),
            job_type="text_extraction",
        )

        assert job.job_type == "text_extraction"
        assert job.priority == 50  # Default priority

    def test_job_default_status(self):
        """Test DocumentProcessingJob default status."""
        job = DocumentProcessingJob(
            document_id=UUID("12345678-1234-1234-1234-123456789012"),
            job_type="analysis",
        )

        assert job.status == "queued"

    def test_job_default_expiration(self):
        """Test DocumentProcessingJob default expiration."""
        job = DocumentProcessingJob(
            document_id=UUID("12345678-1234-1234-1234-123456789012"),
            job_type="analysis",
        )

        # Should expire in ~24 hours
        # Note: Model uses naive datetime (utcnow)
        now = datetime.utcnow()
        time_until_expiry = (job.expires_at - now).total_seconds()

        # Allow some tolerance
        assert 23.9 * 3600 < time_until_expiry < 24.1 * 3600

    def test_job_max_attempts(self):
        """Test DocumentProcessingJob max attempts."""
        job = DocumentProcessingJob(
            document_id=UUID("12345678-1234-1234-1234-123456789012"),
            job_type="analysis",
        )

        assert job.max_attempts == 3
        assert job.attempts == 0


class TestDocumentConfig:
    """Test DOCUMENT_CONFIG constants."""

    def test_config_has_max_file_size(self):
        """Test config has max file size."""
        assert "MAX_FILE_SIZE_MB" in DOCUMENT_CONFIG
        assert DOCUMENT_CONFIG["MAX_FILE_SIZE_MB"] == 10

    def test_config_has_supported_mime_types(self):
        """Test config has supported MIME types."""
        assert "SUPPORTED_MIME_TYPES" in DOCUMENT_CONFIG
        assert "application/pdf" in DOCUMENT_CONFIG["SUPPORTED_MIME_TYPES"]

    def test_config_has_timeouts(self):
        """Test config has timeout settings."""
        assert "PROCESSING_TIMEOUT_SECONDS" in DOCUMENT_CONFIG
        assert "DEFAULT_EXPIRATION_HOURS" in DOCUMENT_CONFIG


class TestItalianDocumentPatterns:
    """Test ITALIAN_DOCUMENT_PATTERNS."""

    def test_patterns_for_fattura(self):
        """Test patterns for fattura elettronica."""
        patterns = ITALIAN_DOCUMENT_PATTERNS[ItalianDocumentCategory.FATTURA_ELETTRONICA]
        assert len(patterns) > 0
        assert any("fattura" in p for p in patterns)

    def test_patterns_for_f24(self):
        """Test patterns for F24."""
        patterns = ITALIAN_DOCUMENT_PATTERNS[ItalianDocumentCategory.F24]
        assert len(patterns) > 0
        assert any("f24" in p for p in patterns)

    def test_patterns_for_730(self):
        """Test patterns for 730 declaration."""
        patterns = ITALIAN_DOCUMENT_PATTERNS[ItalianDocumentCategory.DICHIARAZIONE_730]
        assert len(patterns) > 0
        assert any("730" in p for p in patterns)
