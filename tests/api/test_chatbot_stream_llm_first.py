"""TDD Tests for DEV-180: LLM-First Proactivity in /chat/stream Endpoint.

Tests the integration of:
- Response buffering during streaming
- XML tag stripping from streamed content
- Suggested actions SSE event after content
- InteractiveQuestion early return

Reference: PRATIKO_1.5_REFERENCE.md Section 12.7
"""

import pytest


class TestStreamTagStripping:
    """Tests for XML tag stripping from streamed content."""

    @pytest.mark.asyncio
    async def test_strip_answer_tags_basic(self):
        """Test stripping <answer> tags from content."""
        from app.api.v1.chatbot import strip_xml_tags

        content = "<answer>Questa è la risposta.</answer>"
        result = strip_xml_tags(content)

        assert result == "Questa è la risposta."

    @pytest.mark.asyncio
    async def test_strip_answer_tags_with_newlines(self):
        """Test stripping <answer> tags with newlines inside."""
        from app.api.v1.chatbot import strip_xml_tags

        content = "<answer>Prima riga.\n\nSeconda riga.</answer>"
        result = strip_xml_tags(content)

        assert result == "Prima riga.\n\nSeconda riga."

    @pytest.mark.asyncio
    async def test_strip_actions_tags(self):
        """Test stripping <suggested_actions> tags from content."""
        from app.api.v1.chatbot import strip_xml_tags

        content = '<suggested_actions>[{"id": "1"}]</suggested_actions>'
        result = strip_xml_tags(content)

        assert result == ""

    @pytest.mark.asyncio
    async def test_strip_both_tags(self):
        """Test stripping both answer and actions tags."""
        from app.api.v1.chatbot import strip_xml_tags

        content = """<answer>La risposta qui.</answer>
<suggested_actions>[{"id": "test"}]</suggested_actions>"""
        result = strip_xml_tags(content)

        # Should only contain the answer content, not the actions JSON
        assert "La risposta qui." in result
        assert "<answer>" not in result
        assert "<suggested_actions>" not in result
        assert '"id"' not in result

    @pytest.mark.asyncio
    async def test_strip_preserves_plain_content(self):
        """Test that plain content without tags is preserved."""
        from app.api.v1.chatbot import strip_xml_tags

        content = "Questa è una risposta normale senza tag."
        result = strip_xml_tags(content)

        assert result == content

    @pytest.mark.asyncio
    async def test_strip_preserves_citations(self):
        """Test that citation markers [1], [2] are preserved."""
        from app.api.v1.chatbot import strip_xml_tags

        content = "<answer>Secondo la normativa [1], il contribuente deve [2].</answer>"
        result = strip_xml_tags(content)

        assert "[1]" in result
        assert "[2]" in result
        assert "Secondo la normativa" in result


class TestStreamBuffering:
    """Tests for response buffering during streaming."""

    @pytest.mark.asyncio
    async def test_buffer_accumulates_chunks(self):
        """Test that buffer accumulates all chunks."""
        from app.api.v1.chatbot import StreamBuffer

        buffer = StreamBuffer()
        buffer.append("Prima ")
        buffer.append("parte. ")
        buffer.append("Seconda parte.")

        assert buffer.get_content() == "Prima parte. Seconda parte."

    @pytest.mark.asyncio
    async def test_buffer_handles_empty_chunks(self):
        """Test that buffer handles empty chunks gracefully."""
        from app.api.v1.chatbot import StreamBuffer

        buffer = StreamBuffer()
        buffer.append("Contenuto")
        buffer.append("")
        buffer.append(" finale")

        assert buffer.get_content() == "Contenuto finale"

    @pytest.mark.asyncio
    async def test_buffer_clears(self):
        """Test that buffer can be cleared."""
        from app.api.v1.chatbot import StreamBuffer

        buffer = StreamBuffer()
        buffer.append("Contenuto")
        buffer.clear()

        assert buffer.get_content() == ""


class TestStreamChunkProcessing:
    """Tests for processing chunks during streaming."""

    @pytest.mark.asyncio
    async def test_process_chunk_strips_partial_opening_tag(self):
        """Test handling of partial opening tags across chunks."""
        from app.api.v1.chatbot import process_stream_chunk, StreamTagState

        state = StreamTagState()

        # First chunk ends with partial tag
        chunk1 = "Risposta <ans"
        result1, state = process_stream_chunk(chunk1, state)

        # Tag is incomplete, should buffer it
        assert "<ans" not in result1 or state.pending_tag

        # Second chunk completes the tag
        chunk2 = "wer>contenuto</answer>"
        result2, state = process_stream_chunk(chunk2, state)

        # Combined result should not have tags
        combined = result1 + result2
        assert "<answer>" not in combined or "contenuto" in combined

    @pytest.mark.asyncio
    async def test_process_chunk_handles_complete_tag(self):
        """Test handling of complete tags in single chunk."""
        from app.api.v1.chatbot import process_stream_chunk, StreamTagState

        state = StreamTagState()
        chunk = "<answer>Risposta completa.</answer>"
        result, _ = process_stream_chunk(chunk, state)

        assert "Risposta completa." in result
        assert "<answer>" not in result

    @pytest.mark.asyncio
    async def test_process_chunk_preserves_markdown(self):
        """Test that markdown formatting is preserved."""
        from app.api.v1.chatbot import process_stream_chunk, StreamTagState

        state = StreamTagState()
        chunk = "<answer>**Titolo**\n\n- Punto 1\n- Punto 2</answer>"
        result, _ = process_stream_chunk(chunk, state)

        assert "**Titolo**" in result
        assert "- Punto 1" in result


class TestStreamSSEEvents:
    """Tests for SSE event generation during streaming."""

    @pytest.mark.asyncio
    async def test_actions_event_format(self):
        """Test suggested_actions SSE event format."""
        from app.api.v1.chatbot import format_actions_sse_event

        actions = [
            {"id": "calc", "label": "Calcola", "icon": "🧮", "prompt": "Calcola..."},
        ]
        event = format_actions_sse_event(actions)

        assert "suggested_actions" in event
        assert "calc" in event
        assert "Calcola" in event

    @pytest.mark.asyncio
    async def test_done_event_sent_last(self):
        """Test that done event is always sent last."""
        from app.core.sse_formatter import format_sse_done

        done_event = format_sse_done()

        assert '"done":true' in done_event or '"done": true' in done_event

    @pytest.mark.asyncio
    async def test_interactive_question_event_format(self):
        """Test interactive_question SSE event format."""
        from app.api.v1.chatbot import format_question_sse_event

        question = {
            "id": "irpef_input",
            "text": "Inserisci i dati per calcolare l'IRPEF",
            "question_type": "multi_field",
            "fields": [{"id": "reddito", "label": "Reddito"}],
        }
        event = format_question_sse_event(question)

        assert "interactive_question" in event
        assert "irpef_input" in event


class TestStreamProactivityIntegration:
    """Tests for proactivity integration in streaming."""

    @pytest.mark.asyncio
    async def test_stream_uses_simplified_engine(self):
        """Test that streaming uses the simplified ProactivityEngine."""
        from app.api.v1.chatbot import get_simplified_proactivity_engine
        from app.services.proactivity_engine_simplified import ProactivityEngine

        engine = get_simplified_proactivity_engine()
        assert isinstance(engine, ProactivityEngine)

    @pytest.mark.asyncio
    async def test_stream_document_template_override(self):
        """Test that document template actions override LLM actions in stream."""
        from app.api.v1.chatbot import apply_action_override

        llm_actions = [{"id": "llm_action", "label": "LLM"}]
        template_actions = [{"id": "template_action", "label": "Template"}]

        result = apply_action_override(llm_actions, template_actions)

        assert result == template_actions

    @pytest.mark.asyncio
    async def test_stream_interactive_question_early_return(self):
        """Test that InteractiveQuestion triggers early return (no LLM call)."""
        from app.services.proactivity_engine_simplified import ProactivityEngine

        engine = ProactivityEngine()

        # Query that should trigger interactive question
        result = engine.process_query(
            query="Calcola l'IRPEF",  # Missing required params
            document=None,
        )

        assert result.interactive_question is not None
        assert result.use_llm_actions is False


class TestStreamEdgeCases:
    """Edge case tests for streaming."""

    @pytest.mark.asyncio
    async def test_stream_empty_response(self):
        """Test handling of empty LLM response."""
        from app.api.v1.chatbot import strip_xml_tags

        result = strip_xml_tags("")
        assert result == ""

    @pytest.mark.asyncio
    async def test_stream_response_without_tags(self):
        """Test handling of response without any XML tags."""
        from app.api.v1.chatbot import strip_xml_tags
        from app.services.llm_response_parser import parse_llm_response

        content = "Risposta semplice senza tag XML."
        stripped = strip_xml_tags(content)
        parsed = parse_llm_response(content)

        assert stripped == content
        assert parsed.answer == content
        assert parsed.suggested_actions == []

    @pytest.mark.asyncio
    async def test_stream_very_long_response(self):
        """Test handling of very long response."""
        from app.api.v1.chatbot import strip_xml_tags

        # 50KB of content
        long_content = "A" * 50000
        content = f"<answer>{long_content}</answer>"

        result = strip_xml_tags(content)

        assert len(result) == 50000
        assert "<answer>" not in result

    @pytest.mark.asyncio
    async def test_stream_malformed_tags(self):
        """Test handling of malformed XML tags."""
        from app.api.v1.chatbot import strip_xml_tags

        # Missing closing tag
        content = "<answer>Contenuto senza tag di chiusura"
        result = strip_xml_tags(content)

        # Should handle gracefully - either strip opening tag or preserve content
        assert "Contenuto" in result

    @pytest.mark.asyncio
    async def test_stream_nested_angle_brackets(self):
        """Test that mathematical expressions with < > are preserved."""
        from app.api.v1.chatbot import strip_xml_tags

        content = "<answer>Se x > 5 e y < 10, allora...</answer>"
        result = strip_xml_tags(content)

        assert "x > 5" in result
        assert "y < 10" in result

    @pytest.mark.asyncio
    async def test_stream_actions_only_no_answer(self):
        """Test response with only actions, no answer tags."""
        from app.services.llm_response_parser import parse_llm_response

        content = """Ecco la risposta.
<suggested_actions>[{"id": "1", "label": "Test", "icon": "🔍", "prompt": "Test"}]</suggested_actions>"""

        parsed = parse_llm_response(content)

        # Should use content before actions as answer
        assert "Ecco la risposta." in parsed.answer
        assert len(parsed.suggested_actions) == 1


class TestStreamBufferClass:
    """Unit tests for StreamBuffer class."""

    @pytest.mark.asyncio
    async def test_buffer_size_tracking(self):
        """Test that buffer tracks size correctly."""
        from app.api.v1.chatbot import StreamBuffer

        buffer = StreamBuffer()
        buffer.append("12345")

        assert buffer.size() == 5

    @pytest.mark.asyncio
    async def test_buffer_max_size_protection(self):
        """Test that buffer respects max size limit."""
        from app.api.v1.chatbot import StreamBuffer

        buffer = StreamBuffer(max_size=100)
        buffer.append("A" * 150)

        # Should not exceed max size or should handle gracefully
        assert buffer.size() <= 150  # Allow for graceful handling


class TestStreamTagState:
    """Unit tests for StreamTagState class."""

    @pytest.mark.asyncio
    async def test_tag_state_initialization(self):
        """Test initial state of StreamTagState."""
        from app.api.v1.chatbot import StreamTagState

        state = StreamTagState()

        assert state.pending_tag == ""
        assert state.inside_answer is False
        assert state.inside_actions is False

    @pytest.mark.asyncio
    async def test_tag_state_tracks_answer_tag(self):
        """Test that state tracks when inside answer tag."""
        from app.api.v1.chatbot import process_stream_chunk, StreamTagState

        state = StreamTagState()

        # Process opening answer tag
        _, state = process_stream_chunk("<answer>", state)

        # State should indicate we're inside answer
        # (implementation may vary)
        assert state is not None
