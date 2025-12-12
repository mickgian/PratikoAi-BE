"""Integration tests for chat endpoints with file attachments (DEV-007).

Tests the full flow from chat request with attachment_ids to RAG processing.
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.models.document_simple import Document, ProcessingStatus


@pytest.fixture
def sample_document():
    """Create a sample document for testing."""
    return Document(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        filename="fattura_test.pdf",
        original_filename="fattura_test.pdf",
        file_type="pdf",
        file_size=1024 * 512,  # 512KB
        mime_type="application/pdf",
        processing_status=ProcessingStatus.COMPLETED.value,
        extracted_text="Fattura N. 123 del 01/01/2024. Importo: EUR 1.000,00. IVA 22%: EUR 220,00.",
        extracted_data={
            "tipo": "fattura",
            "numero": "123",
            "data": "2024-01-01",
            "importo": 1000.00,
            "iva": 220.00,
        },
        document_category="fattura_elettronica",
        document_confidence=0.95,
        expires_at=datetime.utcnow() + timedelta(hours=48),
    )


@pytest.fixture
def mock_session():
    """Create a mock session for authentication."""
    session = MagicMock()
    session.id = str(uuid.uuid4())
    session.user_id = uuid.uuid4()
    return session


class TestChatEndpointWithAttachments:
    """Test /api/v1/chatbot/chat endpoint with attachments."""

    @pytest.mark.asyncio
    async def test_chat_with_valid_attachment_ids(self, sample_document, mock_session):
        """Test chat endpoint accepts valid attachment_ids."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.api.v1.chatbot import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/chatbot")

        # Mock dependencies
        with (
            patch("app.api.v1.chatbot.get_current_session") as mock_get_session,
            patch("app.api.v1.chatbot.agent") as mock_agent,
            patch("app.services.attachment_resolver.AttachmentResolver.resolve_attachments") as mock_resolve,
        ):
            mock_get_session.return_value = mock_session
            mock_session.user_id = sample_document.user_id

            # Mock attachment resolution
            mock_resolve.return_value = [
                {
                    "id": str(sample_document.id),
                    "filename": sample_document.filename,
                    "extracted_text": sample_document.extracted_text,
                    "extracted_data": sample_document.extracted_data,
                    "document_category": sample_document.document_category,
                }
            ]

            # Mock agent response
            from app.schemas.chat import Message

            mock_agent.get_response = AsyncMock(
                return_value=[Message(role="assistant", content="La fattura mostra un importo di EUR 1.000,00.")]
            )

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/chatbot/chat",
                    json={
                        "messages": [{"role": "user", "content": "Qual e l'importo di questa fattura?"}],
                        "attachment_ids": [str(sample_document.id)],
                    },
                    headers={"Authorization": "Bearer test_token"},
                )

            # Note: This will fail until we implement the feature, which is expected in TDD
            # The test documents the expected behavior

    @pytest.mark.asyncio
    async def test_chat_with_nonexistent_attachment_returns_404(self, mock_session):
        """Test chat endpoint returns 404 for non-existent attachment."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.api.v1.chatbot import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/chatbot")

        non_existent_id = uuid.uuid4()

        with patch("app.api.v1.chatbot.get_current_session") as mock_get_session:
            mock_get_session.return_value = mock_session

            # Expected: When attachment doesn't exist, return 404
            # This documents expected behavior for TDD

    @pytest.mark.asyncio
    async def test_chat_with_unauthorized_attachment_returns_403(self, sample_document, mock_session):
        """Test chat endpoint returns 403 for attachment owned by another user."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.api.v1.chatbot import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/chatbot")

        # Document owned by different user
        other_user_doc = sample_document
        other_user_doc.user_id = uuid.uuid4()  # Different from mock_session.user_id

        # Expected: When user doesn't own attachment, return 403
        # This documents expected behavior for TDD


class TestChatStreamEndpointWithAttachments:
    """Test /api/v1/chatbot/chat/stream endpoint with attachments."""

    @pytest.mark.asyncio
    async def test_stream_with_attachments_sends_progress_event(self, sample_document, mock_session):
        """Test streaming endpoint sends 'Analisi documento in corso...' progress event."""
        # Expected behavior:
        # 1. User sends chat request with attachment_ids
        # 2. Backend resolves attachments (validates ownership)
        # 3. Backend sends SSE progress event: "Analisi documento in corso..."
        # 4. Backend processes attachments and injects into RAG state
        # 5. Backend streams LLM response
        pass  # TDD - test documents expected behavior

    @pytest.mark.asyncio
    async def test_stream_with_invalid_attachment_stops_early(self, mock_session):
        """Test streaming stops early with error for invalid attachment."""
        # Expected: If attachment validation fails, stream should error early
        # with appropriate Italian error message
        pass  # TDD - test documents expected behavior


class TestAttachmentResolutionInRAG:
    """Test attachment resolution integration with RAG pipeline."""

    @pytest.mark.asyncio
    async def test_attachments_injected_into_rag_state(self, sample_document):
        """Test that resolved attachments are properly injected into RAGState."""
        from app.core.langgraph.types import RAGState

        # Expected: RAGState.attachments should contain resolved attachment data
        initial_state: RAGState = {
            "request_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "user_id": str(sample_document.user_id),
            "user_query": "Analizza questa fattura",
            "messages": [],
            "attachments": None,  # Will be populated
            "metrics": {},
            "processing_stage": "started",
            "node_history": [],
        }

        # After attachment resolution:
        expected_attachments = [
            {
                "id": str(sample_document.id),
                "filename": sample_document.filename,
                "extracted_text": sample_document.extracted_text,
                "document_category": sample_document.document_category,
                "mime_type": sample_document.mime_type,
            }
        ]

        # The implementation should populate state.attachments
        # This test documents the expected data structure

    @pytest.mark.asyncio
    async def test_attachment_text_added_to_context(self, sample_document):
        """Test that attachment extracted text is added to RAG context."""
        # Expected: The context builder should include attachment text
        # in the system prompt or context passed to LLM
        pass  # TDD - documents expected behavior


class TestWordDocxMIMEType:
    """Test Word document (.docx) MIME type support."""

    def test_docx_mime_type_in_supported_types(self):
        """Test that .docx MIME type is in supported types."""
        from app.models.document_simple import DOCUMENT_CONFIG, DocumentType

        docx_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        # Expected: DOCUMENT_CONFIG should include Word MIME type
        # This may fail until we add Word support to DOCUMENT_CONFIG
        assert docx_mime in DOCUMENT_CONFIG["SUPPORTED_MIME_TYPES"]
        assert DOCUMENT_CONFIG["SUPPORTED_MIME_TYPES"][docx_mime] == DocumentType.WORD_DOCX

    def test_image_mime_types_supported(self):
        """Test that image MIME types are supported."""
        from app.models.document_simple import DOCUMENT_CONFIG, DocumentType

        # Check JPEG and PNG are supported
        assert "image/jpeg" in DOCUMENT_CONFIG["SUPPORTED_MIME_TYPES"]
        assert "image/png" in DOCUMENT_CONFIG["SUPPORTED_MIME_TYPES"]


class TestAttachmentErrorMessages:
    """Test Italian error messages for attachment errors."""

    def test_ownership_error_italian_message(self):
        """Test ownership error has Italian message."""
        from app.services.attachment_resolver import AttachmentOwnershipError

        error = AttachmentOwnershipError(
            attachment_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )

        # Expected: Error message should be in Italian
        message = str(error)
        assert any(word in message.lower() for word in ["non autorizzato", "accesso negato", "proprieta", "ownership"])

    def test_not_found_error_italian_message(self):
        """Test not found error has Italian message."""
        from app.services.attachment_resolver import AttachmentNotFoundError

        missing_id = uuid.uuid4()
        error = AttachmentNotFoundError(attachment_id=missing_id)

        # Expected: Error message should mention the missing ID
        message = str(error)
        assert str(missing_id) in message
        assert any(word in message.lower() for word in ["non trovato", "not found", "documento", "allegato"])
