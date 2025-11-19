"""Tests for chat schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    Message,
    QueryClassificationMetadata,
    ResponseMetadata,
    StreamResponse,
)


class TestMessage:
    """Test Message schema."""

    def test_message_creation(self):
        """Test creating a valid message."""
        message = Message(role="user", content="Hello")

        assert message.role == "user"
        assert message.content == "Hello"

    def test_message_roles(self):
        """Test all valid message roles."""
        for role in ["user", "assistant", "system"]:
            message = Message(role=role, content="Test")
            assert message.role == role

    def test_message_invalid_role(self):
        """Test invalid role raises validation error."""
        with pytest.raises(ValidationError):
            Message(role="invalid", content="Test")

    def test_message_empty_content_rejected(self):
        """Test empty content is rejected."""
        with pytest.raises(ValidationError):
            Message(role="user", content="")

    def test_message_content_max_length(self):
        """Test content respects max length."""
        # 50000 chars should be valid
        long_content = "a" * 50000
        message = Message(role="user", content=long_content)
        assert len(message.content) == 50000

        # 50001 chars should fail
        with pytest.raises(ValidationError):
            Message(role="user", content="a" * 50001)

    def test_message_rejects_script_tags(self):
        """Test message rejects potentially harmful script tags."""
        with pytest.raises(ValidationError, match="potentially harmful script tags"):
            Message(role="user", content="<script>alert('xss')</script>")

    def test_message_rejects_script_tags_case_insensitive(self):
        """Test script tag rejection is case insensitive."""
        with pytest.raises(ValidationError, match="potentially harmful script tags"):
            Message(role="user", content="<SCRIPT>alert('xss')</SCRIPT>")

    def test_message_rejects_null_bytes(self):
        """Test message rejects null bytes."""
        with pytest.raises(ValidationError, match="null bytes"):
            Message(role="user", content="Test\0content")

    def test_message_allows_special_chars(self):
        """Test message allows normal special characters."""
        content = "Test: à è ì ò ù € @#$%^&*()"
        message = Message(role="user", content=content)
        assert message.content == content

    def test_message_extra_fields_ignored(self):
        """Test extra fields are ignored."""
        message = Message(role="user", content="Test", extra_field="ignored")
        assert message.role == "user"
        assert not hasattr(message, "extra_field")


class TestStreamResponse:
    """Test StreamResponse schema."""

    def test_stream_response_creation(self):
        """Test creating a StreamResponse."""
        response = StreamResponse(content="Hello", done=False)

        assert response.content == "Hello"
        assert response.done is False

    def test_stream_response_default_values(self):
        """Test StreamResponse default values."""
        response = StreamResponse()

        assert response.content == ""
        assert response.done is False

    def test_stream_response_done(self):
        """Test StreamResponse with done flag."""
        response = StreamResponse(content="", done=True)

        assert response.content == ""
        assert response.done is True

    def test_stream_response_empty_content(self):
        """Test StreamResponse allows empty content."""
        response = StreamResponse(content="", done=False)
        assert response.content == ""


class TestChatRequest:
    """Test ChatRequest schema."""

    def test_chat_request_creation(self):
        """Test creating a ChatRequest."""
        messages = [Message(role="user", content="Hello")]
        request = ChatRequest(messages=messages)

        assert len(request.messages) == 1
        assert request.messages[0].content == "Hello"

    def test_chat_request_multiple_messages(self):
        """Test ChatRequest with multiple messages."""
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there"),
            Message(role="user", content="How are you?"),
        ]
        request = ChatRequest(messages=messages)

        assert len(request.messages) == 3

    def test_chat_request_empty_messages_rejected(self):
        """Test ChatRequest requires at least one message."""
        with pytest.raises(ValidationError):
            ChatRequest(messages=[])

    def test_chat_request_validates_message_content(self):
        """Test ChatRequest validates each message."""
        with pytest.raises(ValidationError):
            ChatRequest(messages=[Message(role="user", content="<script>xss</script>")])


class TestChatResponse:
    """Test ChatResponse schema."""

    def test_chat_response_creation(self):
        """Test creating a ChatResponse."""
        messages = [Message(role="assistant", content="Hello")]
        response = ChatResponse(messages=messages)

        assert len(response.messages) == 1
        assert response.metadata is None

    def test_chat_response_with_metadata(self):
        """Test ChatResponse with metadata."""
        messages = [Message(role="assistant", content="Hello")]
        metadata = ResponseMetadata(model_used="gpt-4o-mini", provider="openai", strategy="cost_optimized")
        response = ChatResponse(messages=messages, metadata=metadata)

        assert response.metadata is not None
        assert response.metadata.model_used == "gpt-4o-mini"


class TestQueryClassificationMetadata:
    """Test QueryClassificationMetadata schema."""

    def test_classification_metadata_creation(self):
        """Test creating QueryClassificationMetadata."""
        metadata = QueryClassificationMetadata(domain="tax", action="query", confidence=0.85)

        assert metadata.domain == "tax"
        assert metadata.action == "query"
        assert metadata.confidence == 0.85

    def test_classification_metadata_optional_fields(self):
        """Test optional fields default to None."""
        metadata = QueryClassificationMetadata(domain="legal", action="generate", confidence=0.90)

        assert metadata.sub_domain is None
        assert metadata.document_type is None
        assert metadata.fallback_used is False

    def test_classification_metadata_with_all_fields(self):
        """Test metadata with all fields."""
        metadata = QueryClassificationMetadata(
            domain="tax",
            action="generate",
            confidence=0.95,
            sub_domain="irpef",
            document_type="contract",
            fallback_used=True,
            domain_prompt_used=True,
            reasoning="Clear tax calculation intent",
        )

        assert metadata.sub_domain == "irpef"
        assert metadata.document_type == "contract"
        assert metadata.fallback_used is True
        assert metadata.reasoning == "Clear tax calculation intent"


class TestResponseMetadata:
    """Test ResponseMetadata schema."""

    def test_response_metadata_creation(self):
        """Test creating ResponseMetadata."""
        metadata = ResponseMetadata(model_used="gpt-4o-mini", provider="openai", strategy="cost_optimized")

        assert metadata.model_used == "gpt-4o-mini"
        assert metadata.provider == "openai"
        assert metadata.strategy == "cost_optimized"

    def test_response_metadata_optional_fields(self):
        """Test optional fields default to None."""
        metadata = ResponseMetadata(model_used="claude-3-haiku", provider="anthropic", strategy="quality_first")

        assert metadata.cost_eur is None
        assert metadata.processing_time_ms is None
        assert metadata.classification is None

    def test_response_metadata_with_cost(self):
        """Test metadata with cost information."""
        metadata = ResponseMetadata(
            model_used="gpt-4o-mini", provider="openai", strategy="cost_optimized", cost_eur=0.015
        )

        assert metadata.cost_eur == 0.015

    def test_response_metadata_with_classification(self):
        """Test metadata with classification."""
        classification = QueryClassificationMetadata(domain="tax", action="query", confidence=0.9)
        metadata = ResponseMetadata(
            model_used="gpt-4o-mini", provider="openai", strategy="cost_optimized", classification=classification
        )

        assert metadata.classification is not None
        assert metadata.classification.domain == "tax"


class TestChatSchemaIntegration:
    """Integration tests for chat schemas."""

    def test_full_request_response_flow(self):
        """Test complete request-response flow."""
        # Create request (validated)
        _ = ChatRequest(messages=[Message(role="user", content="What are IRPEF tax brackets?")])

        # Create response
        classification = QueryClassificationMetadata(domain="tax", action="query", confidence=0.95)
        metadata = ResponseMetadata(
            model_used="gpt-4o-mini",
            provider="openai",
            strategy="cost_optimized",
            cost_eur=0.010,
            processing_time_ms=850,
            classification=classification,
        )
        response = ChatResponse(
            messages=[
                Message(role="user", content="What are IRPEF tax brackets?"),
                Message(role="assistant", content="IRPEF has 4 tax brackets..."),
            ],
            metadata=metadata,
        )

        assert len(response.messages) == 2
        assert response.metadata.classification.domain == "tax"

    def test_streaming_response_sequence(self):
        """Test sequence of streaming responses."""
        chunks = [
            StreamResponse(content="IRPEF ", done=False),
            StreamResponse(content="has ", done=False),
            StreamResponse(content="4 brackets", done=False),
            StreamResponse(content="", done=True),
        ]

        # Reconstruct full response
        full_content = "".join(c.content for c in chunks if not c.done)
        assert full_content == "IRPEF has 4 brackets"

        # Last chunk should be done
        assert chunks[-1].done is True
