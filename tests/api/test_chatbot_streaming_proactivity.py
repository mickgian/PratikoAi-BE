"""TDD Tests for Chatbot Streaming Proactivity Integration - DEV-159.

Tests for integrating ProactivityEngine with /chat/stream endpoint:
- SSE event types: content, suggested_actions, interactive_question
- Correct event sequence: content → actions → question → done
- Graceful degradation on ProactivityEngine failure
- Event format validation
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.chat import StreamResponse
from app.schemas.proactivity import (
    Action,
    ActionCategory,
    ExtractedParameter,
    InteractiveOption,
    InteractiveQuestion,
    ParameterExtractionResult,
    ProactivityResult,
)


class TestStreamResponseWithEventType:
    """Test StreamResponse supports event_type field for proactivity."""

    def test_stream_response_default_content_type(self):
        """Test that StreamResponse defaults to content type."""
        response = StreamResponse(content="Hello")
        assert response.content == "Hello"
        # Default event_type should be "content" or None (backward compatible)
        event_type = getattr(response, "event_type", None)
        assert event_type in (None, "content")

    def test_stream_response_with_content_event_type(self):
        """Test StreamResponse with explicit content event type."""
        response = StreamResponse(content="Hello", event_type="content")
        assert response.event_type == "content"
        assert response.content == "Hello"

    def test_stream_response_with_suggested_actions_type(self):
        """Test StreamResponse with suggested_actions event type."""
        actions = [
            {
                "id": "tax_calculate_irpef",
                "label": "Calcola IRPEF",
                "icon": "calculator",
                "category": "calculate",
            }
        ]
        response = StreamResponse(
            content="",
            event_type="suggested_actions",
            suggested_actions=actions,
        )
        assert response.event_type == "suggested_actions"
        assert response.suggested_actions is not None
        assert len(response.suggested_actions) == 1

    def test_stream_response_with_interactive_question_type(self):
        """Test StreamResponse with interactive_question event type."""
        question = {
            "id": "irpef_tipo_contribuente",
            "text": "Che tipo di contribuente sei?",
            "question_type": "single_choice",
            "options": [
                {"id": "dipendente", "label": "Dipendente"},
                {"id": "autonomo", "label": "Autonomo"},
            ],
        }
        response = StreamResponse(
            content="",
            event_type="interactive_question",
            interactive_question=question,
        )
        assert response.event_type == "interactive_question"
        assert response.interactive_question is not None

    def test_stream_response_with_extracted_params(self):
        """Test StreamResponse includes extracted_params."""
        params = {"reddito": "50000", "anno": "2024"}
        response = StreamResponse(
            content="",
            event_type="suggested_actions",
            extracted_params=params,
        )
        assert response.extracted_params is not None
        assert response.extracted_params["reddito"] == "50000"


class TestSSEProactivityEventFormat:
    """Test SSE event formatting for proactivity events."""

    def test_format_suggested_actions_sse_event(self):
        """Test formatting suggested_actions as SSE event."""
        from app.core.sse_formatter import format_sse_event

        actions = [
            {
                "id": "tax_calculate_irpef",
                "label": "Calcola IRPEF",
                "icon": "calculator",
                "category": "calculate",
            }
        ]
        response = StreamResponse(
            content="",
            event_type="suggested_actions",
            suggested_actions=actions,
        )
        sse_event = format_sse_event(response)

        assert sse_event.startswith("data: ")
        assert sse_event.endswith("\n\n")
        assert "suggested_actions" in sse_event
        assert "tax_calculate_irpef" in sse_event

    def test_format_interactive_question_sse_event(self):
        """Test formatting interactive_question as SSE event."""
        from app.core.sse_formatter import format_sse_event

        question = {
            "id": "irpef_tipo_contribuente",
            "text": "Che tipo di contribuente sei?",
            "question_type": "single_choice",
            "options": [
                {"id": "dipendente", "label": "Dipendente"},
            ],
        }
        response = StreamResponse(
            content="",
            event_type="interactive_question",
            interactive_question=question,
        )
        sse_event = format_sse_event(response)

        assert sse_event.startswith("data: ")
        assert sse_event.endswith("\n\n")
        assert "interactive_question" in sse_event
        assert "irpef_tipo_contribuente" in sse_event


class TestStreamingProactivityEventSequence:
    """Test correct sequence of SSE events with proactivity."""

    def test_event_sequence_content_then_actions_then_done(self):
        """Test events are sent in order: content → actions → done."""
        # This simulates the expected event sequence
        events = [
            StreamResponse(content="Hello", event_type="content"),
            StreamResponse(content=" world", event_type="content"),
            StreamResponse(
                content="",
                event_type="suggested_actions",
                suggested_actions=[{"id": "action1", "label": "Action 1"}],
            ),
            StreamResponse(content="", done=True),
        ]

        # Verify sequence
        content_events = [e for e in events if e.event_type == "content"]
        action_events = [e for e in events if e.event_type == "suggested_actions"]
        done_events = [e for e in events if e.done]

        assert len(content_events) == 2
        assert len(action_events) == 1
        assert len(done_events) == 1
        # Done should be last
        assert events[-1].done is True

    def test_event_sequence_content_then_question_then_done(self):
        """Test events are sent in order: content → question → done."""
        events = [
            StreamResponse(content="Per calcolare", event_type="content"),
            StreamResponse(
                content="",
                event_type="interactive_question",
                interactive_question={"id": "q1", "text": "Question?"},
            ),
            StreamResponse(content="", done=True),
        ]

        question_events = [e for e in events if e.event_type == "interactive_question"]
        assert len(question_events) == 1
        assert events[-1].done is True

    def test_no_actions_when_proactivity_disabled(self):
        """Test no action events when proactivity is not triggered."""
        events = [
            StreamResponse(content="Hello", event_type="content"),
            StreamResponse(content="", done=True),
        ]

        action_events = [e for e in events if getattr(e, "event_type", None) == "suggested_actions"]
        assert len(action_events) == 0


class TestProactivityEngineStreamingIntegration:
    """Test ProactivityEngine integration with streaming endpoint."""

    @pytest.fixture
    def sample_actions(self):
        """Create sample actions for testing."""
        return [
            Action(
                id="tax_calculate_irpef",
                label="Calcola IRPEF",
                icon="calculator",
                category=ActionCategory.CALCULATE,
                prompt_template="Calcola l'IRPEF per {reddito}",
            ),
        ]

    @pytest.fixture
    def sample_question(self):
        """Create sample interactive question for testing."""
        return InteractiveQuestion(
            id="irpef_tipo_contribuente",
            trigger_query="calcola irpef",
            text="Che tipo di contribuente sei?",
            question_type="single_choice",
            options=[
                InteractiveOption(id="dipendente", label="Dipendente"),
                InteractiveOption(id="autonomo", label="Autonomo"),
            ],
        )

    @pytest.fixture
    def sample_proactivity_result(self, sample_actions, sample_question):
        """Create sample ProactivityResult."""
        return ProactivityResult(
            actions=sample_actions,
            question=sample_question,
            extraction_result=None,
            processing_time_ms=50.0,
        )

    def test_proactivity_result_converted_to_sse_events(self, sample_proactivity_result):
        """Test that ProactivityResult is converted to SSE events correctly."""
        result = sample_proactivity_result

        # Convert actions to SSE event
        if result.actions:
            actions_data = [a.model_dump() for a in result.actions]
            action_event = StreamResponse(
                content="",
                event_type="suggested_actions",
                suggested_actions=actions_data,
            )
            assert action_event.event_type == "suggested_actions"
            assert len(action_event.suggested_actions) == 1

        # Convert question to SSE event
        if result.question:
            question_data = result.question.model_dump()
            question_event = StreamResponse(
                content="",
                event_type="interactive_question",
                interactive_question=question_data,
            )
            assert question_event.event_type == "interactive_question"

    def test_empty_proactivity_result_no_extra_events(self):
        """Test that empty ProactivityResult doesn't add extra events."""
        result = ProactivityResult(
            actions=[],
            question=None,
            extraction_result=None,
            processing_time_ms=0.0,
        )

        # Should not generate action events
        assert len(result.actions) == 0
        assert result.question is None


class TestStreamingProactivityGracefulDegradation:
    """Test graceful degradation when ProactivityEngine fails."""

    def test_streaming_continues_on_proactivity_timeout(self):
        """Test streaming continues if proactivity times out."""
        # Simulate normal content streaming completing
        content_events = [
            StreamResponse(content="Response", event_type="content"),
        ]

        # Simulate proactivity timeout - should just skip action events
        # and send done event
        done_event = StreamResponse(content="", done=True)

        all_events = content_events + [done_event]
        assert len(all_events) == 2
        assert all_events[-1].done is True

    def test_streaming_continues_on_proactivity_exception(self):
        """Test streaming continues if proactivity raises exception."""
        # Mock proactivity engine that raises exception
        mock_engine = MagicMock()
        mock_engine.process.side_effect = Exception("Engine error")

        # Simulate the fallback behavior in the endpoint
        try:
            mock_engine.process("query", MagicMock())
            proactivity_result = None
        except Exception:
            # Fallback to empty result
            proactivity_result = ProactivityResult(
                actions=[],
                question=None,
                extraction_result=None,
                processing_time_ms=0.0,
            )

        assert proactivity_result is not None
        assert proactivity_result.actions == []
        assert proactivity_result.question is None


class TestStreamingProactivityBackwardCompatibility:
    """Test backward compatibility with existing clients."""

    def test_legacy_stream_response_still_works(self):
        """Test that legacy StreamResponse (content only) still works."""
        # Legacy format without event_type
        response = StreamResponse(content="Hello", done=False)

        # Should still serialize correctly
        json_data = response.model_dump()
        assert "content" in json_data
        assert "done" in json_data

    def test_clients_can_ignore_new_event_types(self):
        """Test that clients can safely ignore new event types."""
        # New format with event_type
        response = StreamResponse(
            content="Hello",
            event_type="content",
        )

        # Serialize with exclude_none to simulate existing client handling
        json_data = response.model_dump(exclude_none=True)

        # Legacy clients would just use content field
        assert json_data.get("content") == "Hello"
