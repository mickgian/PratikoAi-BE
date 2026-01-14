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
        """Test content respects max length.

        DEV-242 Phase 32: max_length increased from 50000 to 80000 to accommodate
        18 chunks + grounding rules in responses.
        """
        # 80000 chars should be valid
        long_content = "a" * 80000
        message = Message(role="user", content=long_content)
        assert len(message.content) == 80000

        # 80001 chars should fail
        with pytest.raises(ValidationError):
            Message(role="user", content="a" * 80001)

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

    def test_chat_response_backward_compatible(self):
        """Test ChatResponse backward compatibility - old clients work without new fields."""
        # Create response without new proactivity fields (like old API usage)
        messages = [Message(role="assistant", content="Hello")]
        response = ChatResponse(messages=messages)

        # New optional fields should default to None
        assert response.suggested_actions is None
        assert response.interactive_question is None
        assert response.extracted_params is None

        # Serialization should not include None fields (backward compatible)
        response_dict = response.model_dump(exclude_none=True)
        assert "suggested_actions" not in response_dict
        assert "interactive_question" not in response_dict
        assert "extracted_params" not in response_dict

    def test_chat_response_with_suggested_actions(self):
        """Test ChatResponse with suggested_actions."""
        from app.schemas.proactivity import Action, ActionCategory

        messages = [Message(role="assistant", content="Ecco le informazioni IRPEF")]
        actions = [
            Action(
                id="tax_calculate_irpef",
                label="Calcola IRPEF",
                icon="calculator",
                category=ActionCategory.CALCULATE,
                prompt_template="Calcola l'IRPEF per {reddito}",
            ),
            Action(
                id="tax_search_deductions",
                label="Cerca detrazioni",
                icon="search",
                category=ActionCategory.SEARCH,
                prompt_template="Cerca detrazioni fiscali per {categoria}",
            ),
        ]
        response = ChatResponse(messages=messages, suggested_actions=actions)

        assert response.suggested_actions is not None
        assert len(response.suggested_actions) == 2
        assert response.suggested_actions[0].id == "tax_calculate_irpef"
        assert response.suggested_actions[1].category == ActionCategory.SEARCH

    def test_chat_response_with_interactive_question(self):
        """Test ChatResponse with interactive_question."""
        from app.schemas.proactivity import InteractiveOption, InteractiveQuestion

        messages = [Message(role="assistant", content="Per calcolare l'IRPEF...")]
        question = InteractiveQuestion(
            id="irpef_tipo_contribuente",
            trigger_query="calcola irpef",
            text="Che tipo di contribuente sei?",
            question_type="single_choice",
            options=[
                InteractiveOption(id="dipendente", label="Dipendente"),
                InteractiveOption(id="autonomo", label="Autonomo"),
            ],
        )
        response = ChatResponse(messages=messages, interactive_question=question)

        assert response.interactive_question is not None
        assert response.interactive_question.id == "irpef_tipo_contribuente"
        assert len(response.interactive_question.options) == 2

    def test_chat_response_with_extracted_params(self):
        """Test ChatResponse with extracted_params."""
        messages = [Message(role="assistant", content="Hai specificato un reddito di 50000€")]
        extracted = {"reddito": "50000", "anno": "2024"}
        response = ChatResponse(messages=messages, extracted_params=extracted)

        assert response.extracted_params is not None
        assert response.extracted_params["reddito"] == "50000"
        assert response.extracted_params["anno"] == "2024"

    def test_chat_response_with_actions_and_question(self):
        """Test ChatResponse with both actions and question (valid state)."""
        from app.schemas.proactivity import (
            Action,
            ActionCategory,
            InteractiveOption,
            InteractiveQuestion,
        )

        messages = [Message(role="assistant", content="Risposta completa")]
        actions = [
            Action(
                id="tax_calculate",
                label="Calcola",
                icon="calculator",
                category=ActionCategory.CALCULATE,
                prompt_template="Calcola {tipo}",
            )
        ]
        question = InteractiveQuestion(
            id="clarification",
            trigger_query="calcola",
            text="Quale calcolo?",
            question_type="single_choice",
            options=[
                InteractiveOption(id="irpef", label="IRPEF"),
                InteractiveOption(id="iva", label="IVA"),
            ],
        )
        response = ChatResponse(
            messages=messages,
            suggested_actions=actions,
            interactive_question=question,
            extracted_params={"tipo": "fiscale"},
        )

        assert response.suggested_actions is not None
        assert response.interactive_question is not None
        assert response.extracted_params is not None

    def test_chat_response_serialization_excludes_none(self):
        """Test that None values are excluded from serialization."""
        messages = [Message(role="assistant", content="Hello")]
        response = ChatResponse(messages=messages)

        # Using exclude_none should not include None fields
        response_dict = response.model_dump(exclude_none=True)
        assert "suggested_actions" not in response_dict
        assert "interactive_question" not in response_dict
        assert "extracted_params" not in response_dict
        assert "metadata" not in response_dict

        # But messages should be present
        assert "messages" in response_dict

    def test_chat_response_json_serialization(self):
        """Test ChatResponse JSON serialization with proactivity fields."""
        from app.schemas.proactivity import Action, ActionCategory

        messages = [Message(role="assistant", content="Hello")]
        actions = [
            Action(
                id="test_action",
                label="Test",
                icon="test",
                category=ActionCategory.SEARCH,
                prompt_template="Search for {query}",
            )
        ]
        response = ChatResponse(messages=messages, suggested_actions=actions)

        # Should serialize to JSON without errors
        json_str = response.model_dump_json()
        assert "test_action" in json_str
        assert "suggested_actions" in json_str


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
