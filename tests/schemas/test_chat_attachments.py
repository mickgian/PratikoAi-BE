"""Tests for ChatRequest schema with attachment_ids field (DEV-007).

Tests the attachment_ids field validation for the file attachment feature.
"""

import uuid

import pytest
from pydantic import ValidationError

from app.schemas.chat import (
    ChatRequest,
    Message,
)


class TestChatRequestAttachmentIds:
    """Test ChatRequest schema with attachment_ids field."""

    def test_chat_request_without_attachments(self):
        """Test ChatRequest works without attachment_ids (backward compatible)."""
        messages = [Message(role="user", content="Hello")]
        request = ChatRequest(messages=messages)

        assert len(request.messages) == 1
        assert request.attachment_ids is None

    def test_chat_request_with_empty_attachments(self):
        """Test ChatRequest with empty attachment_ids list."""
        messages = [Message(role="user", content="Hello")]
        request = ChatRequest(messages=messages, attachment_ids=[])

        assert request.attachment_ids == []

    def test_chat_request_with_single_attachment(self):
        """Test ChatRequest with single attachment ID."""
        messages = [Message(role="user", content="Analizza questo documento")]
        attachment_id = uuid.uuid4()
        request = ChatRequest(messages=messages, attachment_ids=[attachment_id])

        assert len(request.attachment_ids) == 1
        assert request.attachment_ids[0] == attachment_id

    def test_chat_request_with_multiple_attachments(self):
        """Test ChatRequest with multiple attachment IDs (up to 5)."""
        messages = [Message(role="user", content="Confronta questi documenti")]
        attachment_ids = [uuid.uuid4() for _ in range(5)]
        request = ChatRequest(messages=messages, attachment_ids=attachment_ids)

        assert len(request.attachment_ids) == 5

    def test_chat_request_exceeds_max_attachments(self):
        """Test ChatRequest rejects more than 5 attachments."""
        messages = [Message(role="user", content="Troppi documenti")]
        attachment_ids = [uuid.uuid4() for _ in range(6)]  # 6 exceeds limit

        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(messages=messages, attachment_ids=attachment_ids)

        # Check that error mentions max length
        error_str = str(exc_info.value)
        assert "5" in error_str or "max" in error_str.lower() or "length" in error_str.lower()

    def test_chat_request_with_string_uuid_attachments(self):
        """Test ChatRequest accepts string UUIDs that get converted."""
        messages = [Message(role="user", content="Test")]
        string_uuid = str(uuid.uuid4())
        request = ChatRequest(messages=messages, attachment_ids=[string_uuid])

        assert len(request.attachment_ids) == 1
        # Should be converted to UUID object
        assert isinstance(request.attachment_ids[0], uuid.UUID)

    def test_chat_request_invalid_uuid_rejected(self):
        """Test ChatRequest rejects invalid UUIDs."""
        messages = [Message(role="user", content="Test")]

        with pytest.raises(ValidationError):
            ChatRequest(messages=messages, attachment_ids=["not-a-uuid"])

    def test_chat_request_mixed_valid_invalid_uuid(self):
        """Test ChatRequest rejects if any UUID is invalid."""
        messages = [Message(role="user", content="Test")]
        valid_uuid = uuid.uuid4()

        with pytest.raises(ValidationError):
            ChatRequest(messages=messages, attachment_ids=[valid_uuid, "invalid"])

    def test_chat_request_attachment_ids_type_validation(self):
        """Test attachment_ids must be a list."""
        messages = [Message(role="user", content="Test")]

        with pytest.raises(ValidationError):
            ChatRequest(messages=messages, attachment_ids=uuid.uuid4())  # Not a list

    def test_chat_request_duplicate_attachment_ids_allowed(self):
        """Test that duplicate attachment IDs are allowed (no dedup at schema level)."""
        messages = [Message(role="user", content="Test")]
        same_uuid = uuid.uuid4()
        request = ChatRequest(messages=messages, attachment_ids=[same_uuid, same_uuid])

        # Duplicates allowed at schema level (dedup happens in resolver)
        assert len(request.attachment_ids) == 2

    def test_chat_request_with_attachments_and_system_message(self):
        """Test ChatRequest with system message and attachments."""
        messages = [
            Message(role="system", content="Sei un assistente fiscale italiano."),
            Message(role="user", content="Analizza questa fattura"),
        ]
        attachment_id = uuid.uuid4()
        request = ChatRequest(messages=messages, attachment_ids=[attachment_id])

        assert len(request.messages) == 2
        assert len(request.attachment_ids) == 1


class TestChatRequestAttachmentIntegration:
    """Integration tests for chat requests with attachments."""

    def test_full_request_with_attachments(self):
        """Test complete chat request flow with attachments."""
        # Simulate a user uploading documents and then asking about them
        doc_ids = [uuid.uuid4(), uuid.uuid4()]
        messages = [
            Message(
                role="user",
                content="Ho caricato due fatture. Puoi calcolare l'IVA totale?",
            )
        ]

        request = ChatRequest(messages=messages, attachment_ids=doc_ids)

        assert len(request.messages) == 1
        assert len(request.attachment_ids) == 2
        assert all(isinstance(aid, uuid.UUID) for aid in request.attachment_ids)

    def test_conversation_with_attachments_multi_turn(self):
        """Test multi-turn conversation referencing attachments."""
        doc_id = uuid.uuid4()

        # First turn
        request1 = ChatRequest(
            messages=[
                Message(role="user", content="Analizza questo contratto"),
            ],
            attachment_ids=[doc_id],
        )

        # Second turn (continuing conversation, attachment context maintained)
        request2 = ChatRequest(
            messages=[
                Message(role="user", content="Analizza questo contratto"),
                Message(role="assistant", content="Il contratto contiene..."),
                Message(role="user", content="Quali sono le clausole importanti?"),
            ],
            attachment_ids=[doc_id],  # Same attachment
        )

        assert request1.attachment_ids == request2.attachment_ids

    def test_request_model_dump_includes_attachments(self):
        """Test that model serialization includes attachment_ids."""
        messages = [Message(role="user", content="Test")]
        attachment_id = uuid.uuid4()
        request = ChatRequest(messages=messages, attachment_ids=[attachment_id])

        # Serialize to dict
        data = request.model_dump()

        assert "attachment_ids" in data
        assert len(data["attachment_ids"]) == 1
        assert data["attachment_ids"][0] == attachment_id

    def test_request_model_dump_json_serializable(self):
        """Test that serialization to JSON works with UUIDs."""
        import json

        messages = [Message(role="user", content="Test")]
        attachment_id = uuid.uuid4()
        request = ChatRequest(messages=messages, attachment_ids=[attachment_id])

        # Serialize to JSON
        json_str = request.model_dump_json()
        parsed = json.loads(json_str)

        assert "attachment_ids" in parsed
        assert parsed["attachment_ids"][0] == str(attachment_id)
