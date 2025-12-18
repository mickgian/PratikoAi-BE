"""Unit tests for AttachmentResolver service.

Tests attachment resolution, ownership validation, and error handling for the
upload-first file attachment feature (DEV-007).

The AttachmentResolver service resolves uploaded document IDs to their content
and metadata for use in the RAG pipeline, with proper ownership validation.

DEV-007 Issue 4: Added tests for wait-for-processing feature (OpenAI-style).
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.attachment_resolver import (
    AttachmentNotFoundError,
    AttachmentOwnershipError,
    AttachmentResolver,
    AttachmentResolverError,
)


class MockDocument:
    """Mock Document class for testing without database table dependency."""

    def __init__(
        self,
        id=None,
        user_id=None,
        filename="",
        original_filename="",
        file_type="pdf",
        file_size=1024,
        mime_type="application/pdf",
        processing_status="completed",
        extracted_text=None,
        extracted_data=None,
        document_category=None,
        document_confidence=None,
        expires_at=None,
        is_deleted=False,
        is_expired=False,
    ):
        self.id = id or uuid.uuid4()
        self.user_id = user_id or uuid.uuid4()
        self.filename = filename
        self.original_filename = original_filename or filename
        self.file_type = file_type
        self.file_size = file_size
        self.mime_type = mime_type
        self.processing_status = processing_status
        self.extracted_text = extracted_text
        self.extracted_data = extracted_data
        self.document_category = document_category
        self.document_confidence = document_confidence
        self.expires_at = expires_at or (datetime.utcnow() + timedelta(hours=48))
        self.is_deleted = is_deleted
        self._is_expired = is_expired

    @property
    def is_expired(self):
        if self._is_expired:
            return True
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return True
        return False


@pytest.fixture
def attachment_resolver():
    """Fixture for AttachmentResolver instance."""
    return AttachmentResolver()


@pytest.fixture
def sample_user_id():
    """Fixture for sample user ID (UUID)."""
    return uuid.uuid4()


@pytest.fixture
def other_user_id():
    """Fixture for another user's ID (UUID)."""
    return uuid.uuid4()


@pytest.fixture
def sample_document_id():
    """Fixture for sample document ID."""
    return uuid.uuid4()


@pytest.fixture
def sample_document(sample_document_id, sample_user_id):
    """Fixture for sample document owned by sample_user_id."""
    return MockDocument(
        id=sample_document_id,
        user_id=sample_user_id,
        filename="test_document.pdf",
        original_filename="test_document.pdf",
        file_type="pdf",
        file_size=1024 * 1024,  # 1MB
        mime_type="application/pdf",
        processing_status="completed",
        extracted_text="Questo documento contiene informazioni fiscali importanti...",
        extracted_data={"tipo": "fattura", "importo": 1000.00},
        document_category="fattura_elettronica",
        document_confidence=0.95,
        expires_at=datetime.utcnow() + timedelta(hours=48),
    )


@pytest.fixture
def expired_document(sample_document_id, sample_user_id):
    """Fixture for expired document."""
    return MockDocument(
        id=sample_document_id,
        user_id=sample_user_id,
        filename="expired_doc.pdf",
        original_filename="expired_doc.pdf",
        file_type="pdf",
        file_size=512 * 1024,
        mime_type="application/pdf",
        processing_status="expired",
        extracted_text="Old content...",
        expires_at=datetime.utcnow() - timedelta(hours=24),  # Expired
        is_expired=True,
    )


@pytest.fixture
def mock_db():
    """Fixture for mock async database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


class TestAttachmentResolverValidation:
    """Test suite for attachment ownership validation."""

    @pytest.mark.asyncio
    async def test_resolve_single_attachment_success(
        self,
        attachment_resolver,
        sample_document,
        sample_user_id,
        mock_db,
    ):
        """Test successful resolution of a single attachment."""
        # Patch the _fetch_document method to return our mock document
        attachment_resolver._fetch_document = AsyncMock(return_value=sample_document)

        # Act
        attachments = await attachment_resolver.resolve_attachments(
            db=mock_db,
            attachment_ids=[sample_document.id],
            user_id=sample_user_id,
        )

        # Assert
        assert len(attachments) == 1
        assert attachments[0]["id"] == str(sample_document.id)
        assert attachments[0]["filename"] == "test_document.pdf"
        assert attachments[0]["extracted_text"] is not None
        attachment_resolver._fetch_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_resolve_multiple_attachments_success(
        self,
        attachment_resolver,
        sample_user_id,
        mock_db,
    ):
        """Test successful resolution of multiple attachments."""
        # Arrange - Create multiple documents
        doc_ids = [uuid.uuid4() for _ in range(3)]
        documents = [
            MockDocument(
                id=doc_id,
                user_id=sample_user_id,
                filename=f"document_{i}.pdf",
                original_filename=f"document_{i}.pdf",
                file_type="pdf",
                file_size=1024 * (i + 1),
                mime_type="application/pdf",
                processing_status="completed",
                extracted_text=f"Content {i}",
                expires_at=datetime.utcnow() + timedelta(hours=48),
            )
            for i, doc_id in enumerate(doc_ids)
        ]

        # Mock to return documents in sequence
        attachment_resolver._fetch_document = AsyncMock(side_effect=documents)

        # Act
        attachments = await attachment_resolver.resolve_attachments(
            db=mock_db,
            attachment_ids=doc_ids,
            user_id=sample_user_id,
        )

        # Assert
        assert len(attachments) == 3
        assert attachment_resolver._fetch_document.call_count == 3

    @pytest.mark.asyncio
    async def test_resolve_attachment_ownership_denied(
        self,
        attachment_resolver,
        sample_document,
        other_user_id,
        mock_db,
    ):
        """Test that resolving another user's attachment raises ownership error."""
        # Document owned by sample_user_id, but other_user_id is requesting
        attachment_resolver._fetch_document = AsyncMock(return_value=sample_document)

        # Act & Assert
        with pytest.raises(AttachmentOwnershipError) as exc_info:
            await attachment_resolver.resolve_attachments(
                db=mock_db,
                attachment_ids=[sample_document.id],
                user_id=other_user_id,  # Different user trying to access
            )

        assert "non autorizzato" in str(exc_info.value).lower() or "ownership" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_resolve_attachment_not_found(
        self,
        attachment_resolver,
        sample_user_id,
        mock_db,
    ):
        """Test that resolving non-existent attachment raises not found error."""
        non_existent_id = uuid.uuid4()
        attachment_resolver._fetch_document = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(AttachmentNotFoundError) as exc_info:
            await attachment_resolver.resolve_attachments(
                db=mock_db,
                attachment_ids=[non_existent_id],
                user_id=sample_user_id,
            )

        assert str(non_existent_id) in str(exc_info.value)


class TestAttachmentResolverEdgeCases:
    """Test suite for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_resolve_empty_attachment_list(
        self,
        attachment_resolver,
        sample_user_id,
        mock_db,
    ):
        """Test resolving empty attachment list returns empty list."""
        # Act
        attachments = await attachment_resolver.resolve_attachments(
            db=mock_db,
            attachment_ids=[],
            user_id=sample_user_id,
        )

        # Assert
        assert attachments == []

    @pytest.mark.asyncio
    async def test_resolve_expired_attachment_warning(
        self,
        attachment_resolver,
        expired_document,
        sample_user_id,
        mock_db,
    ):
        """Test that expired documents are handled gracefully with warning."""
        # Patch the fetch method
        attachment_resolver._fetch_document = AsyncMock(return_value=expired_document)

        # Act
        attachments = await attachment_resolver.resolve_attachments(
            db=mock_db,
            attachment_ids=[expired_document.id],
            user_id=sample_user_id,
        )

        # Assert - Expired documents should be returned with warning flag
        assert len(attachments) == 1
        assert attachments[0]["is_expired"] is True
        assert "warning" in attachments[0]

    @pytest.mark.asyncio
    async def test_resolve_deleted_attachment(
        self,
        attachment_resolver,
        sample_user_id,
        mock_db,
    ):
        """Test that deleted documents are not returned."""
        # _fetch_document returns None for deleted documents (filtered by query)
        attachment_resolver._fetch_document = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(AttachmentNotFoundError):
            await attachment_resolver.resolve_attachments(
                db=mock_db,
                attachment_ids=[uuid.uuid4()],
                user_id=sample_user_id,
            )

    @pytest.mark.asyncio
    async def test_resolve_processing_incomplete_document_waits_then_returns(
        self,
        attachment_resolver,
        sample_user_id,
        mock_db,
    ):
        """Test handling documents still being processed - waits then returns completed.

        DEV-007 Issue 4: Changed behavior - resolver now waits for processing
        instead of returning immediately with a warning.
        """
        doc_id = uuid.uuid4()
        processing_doc = MockDocument(
            id=doc_id,
            user_id=sample_user_id,
            filename="processing.pdf",
            original_filename="processing.pdf",
            file_type="pdf",
            file_size=2048,
            mime_type="application/pdf",
            processing_status="processing",  # Still processing
            expires_at=datetime.utcnow() + timedelta(hours=48),
        )
        completed_doc = MockDocument(
            id=doc_id,
            user_id=sample_user_id,
            filename="processing.pdf",
            original_filename="processing.pdf",
            file_type="pdf",
            file_size=2048,
            mime_type="application/pdf",
            processing_status="completed",  # Now completed
            extracted_text="Document content",
            expires_at=datetime.utcnow() + timedelta(hours=48),
        )

        # Mock: first returns processing, second returns completed
        attachment_resolver._fetch_document = AsyncMock(side_effect=[processing_doc, completed_doc])
        # Use short poll interval for faster test
        attachment_resolver.processing_poll_interval_seconds = 0.01

        # Act
        attachments = await attachment_resolver.resolve_attachments(
            db=mock_db,
            attachment_ids=[doc_id],
            user_id=sample_user_id,
        )

        # Assert - Should wait and return completed document
        assert len(attachments) == 1
        assert attachments[0]["processing_status"] == "completed"
        assert attachments[0]["extracted_text"] == "Document content"

    @pytest.mark.asyncio
    async def test_resolve_max_attachments_limit(
        self,
        attachment_resolver,
        sample_user_id,
        mock_db,
    ):
        """Test that resolver respects max attachment limit (5)."""
        # Arrange - 6 document IDs (exceeds limit)
        doc_ids = [uuid.uuid4() for _ in range(6)]

        # Act & Assert
        with pytest.raises(AttachmentResolverError) as exc_info:
            await attachment_resolver.resolve_attachments(
                db=mock_db,
                attachment_ids=doc_ids,
                user_id=sample_user_id,
            )

        assert "5" in str(exc_info.value) or "limite" in str(exc_info.value).lower()


class TestAttachmentResolverDataExtraction:
    """Test suite for data extraction from resolved attachments."""

    @pytest.mark.asyncio
    async def test_resolve_returns_extracted_text(
        self,
        attachment_resolver,
        sample_document,
        sample_user_id,
        mock_db,
    ):
        """Test that resolved attachment includes extracted text."""
        attachment_resolver._fetch_document = AsyncMock(return_value=sample_document)

        # Act
        attachments = await attachment_resolver.resolve_attachments(
            db=mock_db,
            attachment_ids=[sample_document.id],
            user_id=sample_user_id,
        )

        # Assert
        assert attachments[0]["extracted_text"] == sample_document.extracted_text

    @pytest.mark.asyncio
    async def test_resolve_returns_metadata(
        self,
        attachment_resolver,
        sample_document,
        sample_user_id,
        mock_db,
    ):
        """Test that resolved attachment includes document metadata."""
        attachment_resolver._fetch_document = AsyncMock(return_value=sample_document)

        # Act
        attachments = await attachment_resolver.resolve_attachments(
            db=mock_db,
            attachment_ids=[sample_document.id],
            user_id=sample_user_id,
        )

        # Assert
        attachment = attachments[0]
        assert attachment["document_category"] == sample_document.document_category
        assert attachment["mime_type"] == sample_document.mime_type
        assert attachment["file_size"] == sample_document.file_size

    @pytest.mark.asyncio
    async def test_resolve_returns_extracted_data(
        self,
        attachment_resolver,
        sample_document,
        sample_user_id,
        mock_db,
    ):
        """Test that resolved attachment includes extracted structured data."""
        attachment_resolver._fetch_document = AsyncMock(return_value=sample_document)

        # Act
        attachments = await attachment_resolver.resolve_attachments(
            db=mock_db,
            attachment_ids=[sample_document.id],
            user_id=sample_user_id,
        )

        # Assert
        assert attachments[0]["extracted_data"] == sample_document.extracted_data


class TestAttachmentResolverDatabaseErrors:
    """Test suite for database error handling."""

    @pytest.mark.asyncio
    async def test_resolve_database_connection_error(
        self,
        attachment_resolver,
        sample_user_id,
        mock_db,
    ):
        """Test handling of database connection errors."""
        # Make _fetch_document raise an exception
        attachment_resolver._fetch_document = AsyncMock(side_effect=Exception("Database connection failed"))

        # Act & Assert
        with pytest.raises(AttachmentResolverError) as exc_info:
            await attachment_resolver.resolve_attachments(
                db=mock_db,
                attachment_ids=[uuid.uuid4()],
                user_id=sample_user_id,
            )

        assert "database" in str(exc_info.value).lower() or "errore" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_resolve_partial_success_with_missing(
        self,
        attachment_resolver,
        sample_document,
        sample_user_id,
        mock_db,
    ):
        """Test handling when some attachments exist and some don't."""
        # First call returns document, second returns None
        existing_doc = sample_document
        non_existent_id = uuid.uuid4()

        # Side effect: first call returns doc, second returns None
        attachment_resolver._fetch_document = AsyncMock(side_effect=[existing_doc, None])

        # Act & Assert - Should raise for missing attachment
        with pytest.raises(AttachmentNotFoundError):
            await attachment_resolver.resolve_attachments(
                db=mock_db,
                attachment_ids=[existing_doc.id, non_existent_id],
                user_id=sample_user_id,
            )


class TestAttachmentResolverWaitForProcessing:
    """Test suite for wait-for-processing feature (DEV-007 Issue 4).

    Tests the OpenAI-style pattern where the resolver waits for document
    processing to complete before returning, with a 60-second timeout.
    """

    @pytest.mark.asyncio
    async def test_resolve_returns_immediately_when_already_completed(
        self,
        attachment_resolver,
        sample_document,
        sample_user_id,
        mock_db,
    ):
        """Documents already completed should resolve immediately without waiting."""
        # sample_document has processing_status="completed"
        attachment_resolver._fetch_document = AsyncMock(return_value=sample_document)

        # Act - measure time to ensure no waiting
        start_time = asyncio.get_event_loop().time()
        attachments = await attachment_resolver.resolve_attachments(
            db=mock_db,
            attachment_ids=[sample_document.id],
            user_id=sample_user_id,
        )
        elapsed = asyncio.get_event_loop().time() - start_time

        # Assert - Should complete almost instantly (< 1 second)
        assert len(attachments) == 1
        assert attachments[0]["processing_status"] == "completed"
        assert elapsed < 1.0, "Should not wait for already completed documents"

    @pytest.mark.asyncio
    async def test_resolve_waits_for_processing_to_complete(
        self,
        attachment_resolver,
        sample_user_id,
        mock_db,
    ):
        """Resolver should poll and wait until document processing completes."""
        doc_id = uuid.uuid4()

        # Create documents at different processing states
        processing_doc = MockDocument(
            id=doc_id,
            user_id=sample_user_id,
            filename="processing.pdf",
            processing_status="processing",
        )
        completed_doc = MockDocument(
            id=doc_id,
            user_id=sample_user_id,
            filename="processing.pdf",
            processing_status="completed",
            extracted_text="Document content after processing",
        )

        # Mock: first call returns "processing", second returns "completed"
        attachment_resolver._fetch_document = AsyncMock(side_effect=[processing_doc, completed_doc])

        # Act
        attachments = await attachment_resolver.resolve_attachments(
            db=mock_db,
            attachment_ids=[doc_id],
            user_id=sample_user_id,
        )

        # Assert - Should have waited and gotten completed document
        assert len(attachments) == 1
        assert attachments[0]["processing_status"] == "completed"
        assert attachments[0]["extracted_text"] == "Document content after processing"
        # Should have called _fetch_document at least twice (initial + poll)
        assert attachment_resolver._fetch_document.call_count >= 2

    @pytest.mark.asyncio
    async def test_resolve_raises_error_on_processing_timeout(
        self,
        attachment_resolver,
        sample_user_id,
        mock_db,
    ):
        """Resolver should raise AttachmentProcessingError after timeout."""
        from app.services.attachment_resolver import AttachmentProcessingError

        doc_id = uuid.uuid4()
        processing_doc = MockDocument(
            id=doc_id,
            user_id=sample_user_id,
            filename="stuck_processing.pdf",
            processing_status="processing",
        )

        # Mock: always returns processing status (never completes)
        attachment_resolver._fetch_document = AsyncMock(return_value=processing_doc)

        # Patch timeout to be very short for test
        with patch.object(
            attachment_resolver,
            "processing_wait_timeout_seconds",
            3,  # 3 second timeout for test
        ):
            # Act & Assert
            with pytest.raises(AttachmentProcessingError) as exc_info:
                await attachment_resolver.resolve_attachments(
                    db=mock_db,
                    attachment_ids=[doc_id],
                    user_id=sample_user_id,
                )

            # Error message should mention timeout or retry
            error_msg = str(exc_info.value).lower()
            assert "scaduta" in error_msg or "timeout" in error_msg or "riprova" in error_msg

    @pytest.mark.asyncio
    async def test_resolve_raises_error_on_failed_processing(
        self,
        attachment_resolver,
        sample_user_id,
        mock_db,
    ):
        """Resolver should raise error if document processing failed."""
        from app.services.attachment_resolver import AttachmentProcessingError

        doc_id = uuid.uuid4()
        failed_doc = MockDocument(
            id=doc_id,
            user_id=sample_user_id,
            filename="failed.pdf",
            processing_status="failed",
        )
        # Add error_message attribute for failed documents
        failed_doc.error_message = "Formato documento non supportato"

        attachment_resolver._fetch_document = AsyncMock(return_value=failed_doc)

        # Act & Assert
        with pytest.raises(AttachmentProcessingError) as exc_info:
            await attachment_resolver.resolve_attachments(
                db=mock_db,
                attachment_ids=[doc_id],
                user_id=sample_user_id,
            )

        # Error message should mention failure
        error_msg = str(exc_info.value).lower()
        assert "fallita" in error_msg or "failed" in error_msg or "errore" in error_msg

    @pytest.mark.asyncio
    async def test_resolve_waits_through_multiple_processing_states(
        self,
        attachment_resolver,
        sample_user_id,
        mock_db,
    ):
        """Resolver should wait through extracting → analyzing → completed."""
        doc_id = uuid.uuid4()

        # Simulate progression through processing states
        extracting_doc = MockDocument(
            id=doc_id, user_id=sample_user_id, filename="doc.xlsx", processing_status="extracting"
        )
        analyzing_doc = MockDocument(
            id=doc_id, user_id=sample_user_id, filename="doc.xlsx", processing_status="analyzing"
        )
        completed_doc = MockDocument(
            id=doc_id,
            user_id=sample_user_id,
            filename="doc.xlsx",
            processing_status="completed",
            extracted_text="Excel content",
            extracted_data={"sheet1": [["A", "B"], [1, 2]]},
        )

        # Mock: progress through states
        attachment_resolver._fetch_document = AsyncMock(side_effect=[extracting_doc, analyzing_doc, completed_doc])

        # Act
        attachments = await attachment_resolver.resolve_attachments(
            db=mock_db,
            attachment_ids=[doc_id],
            user_id=sample_user_id,
        )

        # Assert
        assert len(attachments) == 1
        assert attachments[0]["processing_status"] == "completed"
        assert attachments[0]["extracted_data"] is not None
        assert attachment_resolver._fetch_document.call_count == 3

    @pytest.mark.asyncio
    async def test_wait_for_processing_polls_multiple_times(
        self,
        attachment_resolver,
        sample_user_id,
        mock_db,
    ):
        """Wait should poll multiple times until document is ready."""
        doc_id = uuid.uuid4()

        processing_doc = MockDocument(
            id=doc_id, user_id=sample_user_id, filename="doc.pdf", processing_status="processing"
        )
        completed_doc = MockDocument(
            id=doc_id, user_id=sample_user_id, filename="doc.pdf", processing_status="completed"
        )

        # Return processing twice, then completed on third call
        # This simulates: initial check (processing) -> poll (processing) -> poll (completed)
        attachment_resolver._fetch_document = AsyncMock(side_effect=[processing_doc, processing_doc, completed_doc])

        # Use very short poll interval for faster test
        attachment_resolver.processing_poll_interval_seconds = 0.01

        # Act
        attachments = await attachment_resolver.resolve_attachments(
            db=mock_db,
            attachment_ids=[doc_id],
            user_id=sample_user_id,
        )

        # Assert - Should have polled 3 times total
        # (initial fetch that triggers wait, then 2 polls before completed)
        assert attachment_resolver._fetch_document.call_count == 3
        assert len(attachments) == 1
        assert attachments[0]["processing_status"] == "completed"
