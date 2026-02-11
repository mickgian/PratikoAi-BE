"""Unit tests for LLM provider Langfuse generation reporting (DEV-255).

Tests that OpenAI and Anthropic providers report token usage to Langfuse
via start_generation() with explicit trace_context for non-tool-call LLM invocations.
This creates proper "generation" type observations that enable automatic cost calculation.
"""

from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from app.schemas.chat import Message


class TestOpenAIProviderLangfuseReporting:
    """Tests for OpenAI provider _report_langfuse_generation."""

    def test_skips_when_no_trace_id(self) -> None:
        """Should skip reporting when trace_id is None (no active trace)."""
        from app.core.llm.providers.openai_provider import OpenAIProvider

        with patch("app.core.llm.providers.openai_provider.get_client") as mock_get_client:
            OpenAIProvider._report_langfuse_generation(
                model="gpt-4o-mini",
                input_messages=[],
                output_content="test",
                prompt_tokens=0,
                completion_tokens=0,
                trace_id=None,  # No active trace
            )
            # Should NOT call Langfuse client
            mock_get_client.assert_not_called()

    def test_reports_when_trace_id_provided(self) -> None:
        """Should report generation via start_generation() with trace_context when trace_id is provided."""
        from app.core.llm.providers.openai_provider import OpenAIProvider

        with patch("app.core.llm.providers.openai_provider.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_generation = MagicMock()
            mock_client.start_generation.return_value = mock_generation
            mock_get_client.return_value = mock_client

            OpenAIProvider._report_langfuse_generation(
                model="gpt-4o-mini",
                input_messages=[{"role": "user", "content": "hello"}],
                output_content="Hi there!",
                prompt_tokens=10,
                completion_tokens=5,
                trace_id="test-trace-123",
            )

        # Verify start_generation called WITH trace_context for explicit binding
        mock_client.start_generation.assert_called_once()
        call_kwargs = mock_client.start_generation.call_args[1]
        assert call_kwargs["name"] == "openai-chat"
        assert call_kwargs["model"] == "gpt-4o-mini"
        assert call_kwargs["input"] == {"messages": [{"role": "user", "content": "hello"}]}
        assert call_kwargs["trace_context"] == {"trace_id": "test-trace-123"}

        # Verify update() called with output and usage_details (native generation params)
        mock_generation.update.assert_called_once()
        update_kwargs = mock_generation.update.call_args[1]
        assert update_kwargs["output"] == "Hi there!"
        assert update_kwargs["usage_details"]["input"] == 10
        assert update_kwargs["usage_details"]["output"] == 5

        # Verify generation.end() was called
        mock_generation.end.assert_called_once()

    def test_nests_under_parent_span_when_provided(self) -> None:
        """Should include parent_span_id in trace_context to nest generation under parent span."""
        from app.core.llm.providers.openai_provider import OpenAIProvider

        with patch("app.core.llm.providers.openai_provider.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_generation = MagicMock()
            mock_client.start_generation.return_value = mock_generation
            mock_get_client.return_value = mock_client

            OpenAIProvider._report_langfuse_generation(
                model="gpt-4o-mini",
                input_messages=[{"role": "user", "content": "hello"}],
                output_content="Hi there!",
                prompt_tokens=10,
                completion_tokens=5,
                trace_id="test-trace-123",
                parent_span_id="abc123def456789a",  # 16-char hex span ID
            )

        # Verify trace_context includes BOTH trace_id AND parent_span_id
        call_kwargs = mock_client.start_generation.call_args[1]
        assert call_kwargs["trace_context"] == {
            "trace_id": "test-trace-123",
            "parent_span_id": "abc123def456789a",
        }

    def test_reports_generation_with_token_usage(self) -> None:
        """Should report input_tokens/output_tokens via generation.update() usage_details."""
        from app.core.llm.providers.openai_provider import OpenAIProvider

        with patch("app.core.llm.providers.openai_provider.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_generation = MagicMock()
            mock_client.start_generation.return_value = mock_generation
            mock_get_client.return_value = mock_client

            OpenAIProvider._report_langfuse_generation(
                model="gpt-4o-mini",
                input_messages=[{"role": "user", "content": "hello"}],
                output_content="Hi there!",
                prompt_tokens=10,
                completion_tokens=5,
                trace_id="test-trace-456",
            )

        mock_client.start_generation.assert_called_once()
        call_kwargs = mock_client.start_generation.call_args[1]
        assert call_kwargs["name"] == "openai-chat"
        assert call_kwargs["model"] == "gpt-4o-mini"

        # Token usage reported via update() with native usage_details param
        update_kwargs = mock_generation.update.call_args[1]
        assert update_kwargs["usage_details"] == {
            "input": 10,
            "output": 5,
        }

    def test_reports_model_name(self) -> None:
        """Should include the model name as a native generation parameter."""
        from app.core.llm.providers.openai_provider import OpenAIProvider

        with patch("app.core.llm.providers.openai_provider.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_generation = MagicMock()
            mock_client.start_generation.return_value = mock_generation
            mock_get_client.return_value = mock_client

            OpenAIProvider._report_langfuse_generation(
                model="gpt-4o",
                input_messages=[],
                output_content="response",
                prompt_tokens=0,
                completion_tokens=0,
                trace_id="test-trace-789",
            )

        call_kwargs = mock_client.start_generation.call_args[1]
        assert call_kwargs["model"] == "gpt-4o"

    def test_graceful_degradation_no_langfuse(self) -> None:
        """Should not raise when Langfuse is unavailable."""
        from app.core.llm.providers.openai_provider import OpenAIProvider

        with patch("app.core.llm.providers.openai_provider.get_client", side_effect=Exception("No client")):
            # Should NOT raise
            OpenAIProvider._report_langfuse_generation(
                model="gpt-4o-mini",
                input_messages=[],
                output_content="test",
                prompt_tokens=0,
                completion_tokens=0,
            )

    @pytest.mark.asyncio
    async def test_no_report_for_tool_calls(self) -> None:
        """Tool call path uses LangChain which auto-reports; no manual report needed."""
        from app.core.llm.providers.openai_provider import OpenAIProvider

        provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "tool result"
        mock_response.tool_calls = [{"id": "1", "name": "search", "args": {}}]
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        provider._langchain_client = MagicMock()
        provider._langchain_client.bind_tools = MagicMock(return_value=mock_llm)

        tools = [MagicMock(name="search")]

        with patch("app.core.llm.providers.openai_provider.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            messages = [Message(role="user", content="search for something")]
            await provider.chat_completion(messages, tools=tools)

            # No manual generation report for tool calls (LangChain handles it)
            mock_client.start_generation.assert_not_called()


class TestAnthropicProviderLangfuseReporting:
    """Tests for Anthropic provider _report_langfuse_generation."""

    def test_skips_when_no_trace_id(self) -> None:
        """Should skip reporting when trace_id is None (no active trace)."""
        from app.core.llm.providers.anthropic_provider import AnthropicProvider

        with patch("app.core.llm.providers.anthropic_provider.get_client") as mock_get_client:
            AnthropicProvider._report_langfuse_generation(
                model="claude-3-haiku-20240307",
                input_messages=[],
                output_content="test",
                input_tokens=0,
                output_tokens=0,
                trace_id=None,  # No active trace
            )
            # Should NOT call Langfuse client
            mock_get_client.assert_not_called()

    def test_reports_when_trace_id_provided(self) -> None:
        """Should report generation via start_generation() with trace_context when trace_id is provided."""
        from app.core.llm.providers.anthropic_provider import AnthropicProvider

        with patch("app.core.llm.providers.anthropic_provider.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_generation = MagicMock()
            mock_client.start_generation.return_value = mock_generation
            mock_get_client.return_value = mock_client

            AnthropicProvider._report_langfuse_generation(
                model="claude-3-haiku-20240307",
                input_messages=[{"role": "user", "content": "hello"}],
                output_content="Hi there!",
                input_tokens=10,
                output_tokens=5,
                trace_id="test-trace-123",
            )

        # Verify start_generation called WITH trace_context for explicit binding
        mock_client.start_generation.assert_called_once()
        call_kwargs = mock_client.start_generation.call_args[1]
        assert call_kwargs["name"] == "anthropic-chat"
        assert call_kwargs["model"] == "claude-3-haiku-20240307"
        assert call_kwargs["input"] == {"messages": [{"role": "user", "content": "hello"}]}
        assert call_kwargs["trace_context"] == {"trace_id": "test-trace-123"}

        # Verify update() called with output and usage_details (native generation params)
        mock_generation.update.assert_called_once()
        update_kwargs = mock_generation.update.call_args[1]
        assert update_kwargs["output"] == "Hi there!"
        assert update_kwargs["usage_details"]["input"] == 10
        assert update_kwargs["usage_details"]["output"] == 5

        # Verify generation.end() was called
        mock_generation.end.assert_called_once()

    def test_nests_under_parent_span_when_provided(self) -> None:
        """Should include parent_span_id in trace_context to nest generation under parent span."""
        from app.core.llm.providers.anthropic_provider import AnthropicProvider

        with patch("app.core.llm.providers.anthropic_provider.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_generation = MagicMock()
            mock_client.start_generation.return_value = mock_generation
            mock_get_client.return_value = mock_client

            AnthropicProvider._report_langfuse_generation(
                model="claude-3-haiku-20240307",
                input_messages=[{"role": "user", "content": "hello"}],
                output_content="Hi there!",
                input_tokens=10,
                output_tokens=5,
                trace_id="test-trace-123",
                parent_span_id="abc123def456789a",  # 16-char hex span ID
            )

        # Verify trace_context includes BOTH trace_id AND parent_span_id
        call_kwargs = mock_client.start_generation.call_args[1]
        assert call_kwargs["trace_context"] == {
            "trace_id": "test-trace-123",
            "parent_span_id": "abc123def456789a",
        }

    def test_reports_generation_with_token_usage(self) -> None:
        """Should report input_tokens/output_tokens via generation.update() usage_details."""
        from app.core.llm.providers.anthropic_provider import AnthropicProvider

        with patch("app.core.llm.providers.anthropic_provider.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_generation = MagicMock()
            mock_client.start_generation.return_value = mock_generation
            mock_get_client.return_value = mock_client

            AnthropicProvider._report_langfuse_generation(
                model="claude-3-haiku-20240307",
                input_messages=[{"role": "user", "content": "hello"}],
                output_content="Hi there!",
                input_tokens=10,
                output_tokens=5,
                trace_id="test-trace-456",
            )

        mock_client.start_generation.assert_called_once()
        call_kwargs = mock_client.start_generation.call_args[1]
        assert call_kwargs["name"] == "anthropic-chat"
        assert call_kwargs["model"] == "claude-3-haiku-20240307"

        # Token usage reported via update() with native usage_details param
        update_kwargs = mock_generation.update.call_args[1]
        assert update_kwargs["usage_details"] == {
            "input": 10,
            "output": 5,
        }

    def test_reports_model_name(self) -> None:
        """Should include the model name as a native generation parameter."""
        from app.core.llm.providers.anthropic_provider import AnthropicProvider

        with patch("app.core.llm.providers.anthropic_provider.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_generation = MagicMock()
            mock_client.start_generation.return_value = mock_generation
            mock_get_client.return_value = mock_client

            AnthropicProvider._report_langfuse_generation(
                model="claude-3-5-sonnet-20241022",
                input_messages=[],
                output_content="response",
                input_tokens=0,
                output_tokens=0,
                trace_id="test-trace-789",
            )

        call_kwargs = mock_client.start_generation.call_args[1]
        assert call_kwargs["model"] == "claude-3-5-sonnet-20241022"

    def test_graceful_degradation_no_langfuse(self) -> None:
        """Should not raise when Langfuse is unavailable."""
        from app.core.llm.providers.anthropic_provider import AnthropicProvider

        with patch("app.core.llm.providers.anthropic_provider.get_client", side_effect=Exception("No client")):
            # Should NOT raise
            AnthropicProvider._report_langfuse_generation(
                model="claude-3-haiku-20240307",
                input_messages=[],
                output_content="test",
                input_tokens=0,
                output_tokens=0,
            )

    @pytest.mark.asyncio
    async def test_reports_after_chat_completion(self) -> None:
        """chat_completion should call _report_langfuse_generation for non-tool calls."""
        from app.core.llm.providers.anthropic_provider import AnthropicProvider

        provider = AnthropicProvider(api_key="test-key", model="claude-3-haiku-20240307")

        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="Hello!")]
        mock_response.usage = MagicMock(input_tokens=15, output_tokens=8)
        mock_response.stop_reason = "end_turn"

        provider._client = MagicMock()
        provider._client.messages = MagicMock()
        provider._client.messages.create = AsyncMock(return_value=mock_response)

        with patch.object(AnthropicProvider, "_report_langfuse_generation") as mock_report:
            messages = [Message(role="user", content="hello")]
            await provider.chat_completion(messages)

            mock_report.assert_called_once_with(
                model="claude-3-haiku-20240307",
                input_messages=[{"role": "user", "content": "hello"}],
                output_content="Hello!",
                input_tokens=15,
                output_tokens=8,
                trace_id=ANY,  # trace_id from get_current_trace_id() contextvar
                parent_span_id=ANY,  # parent_span_id from get_current_observation_id() contextvar
                input_cost=ANY,  # DEV-256: cost passed for explicit Langfuse tracking
                output_cost=ANY,
            )
