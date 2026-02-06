"""Unit tests for Langfuse custom spans module.

Tests cover:
- Custom span creation for non-LLM operations
- Span context management
- Metadata enrichment on spans
- Nested span support
- Graceful degradation

Updated for Langfuse SDK v3.x:
- Uses client.start_span() with trace_context instead of client.trace().span()
"""

from contextlib import contextmanager
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest


class TestCreateSpan:
    """Tests for create_span function (v3 SDK)."""

    @patch("app.observability.langfuse_spans.get_client")
    def test_creates_span_with_name(self, mock_get_client_fn: MagicMock) -> None:
        """Should create a span with the given name using start_span()."""
        from app.observability.langfuse_spans import create_span

        mock_client = MagicMock()
        mock_get_client_fn.return_value = mock_client

        with patch("app.observability.langfuse_spans.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"

            create_span(
                name="retrieval_step",
                trace_id="trace-123",
            )

        # v3 SDK: should call start_span() with trace_context
        mock_client.start_span.assert_called()
        call_kwargs = mock_client.start_span.call_args[1]
        assert call_kwargs["name"] == "retrieval_step"
        assert call_kwargs["trace_context"] == {"trace_id": "trace-123"}

    @patch("app.observability.langfuse_spans.get_langfuse_client")
    def test_span_includes_input_data(self, mock_get_client: MagicMock) -> None:
        """Span should include input data when provided."""
        from app.observability.langfuse_spans import create_span

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        create_span(
            name="retrieval_step",
            trace_id="trace-123",
            input_data={"query": "test query"},
        )

        call_kwargs = mock_client.start_span.call_args[1]
        assert call_kwargs["input"] == {"query": "test query"}

    @patch("app.observability.langfuse_spans.get_langfuse_client")
    def test_span_includes_metadata(self, mock_get_client: MagicMock) -> None:
        """Span should include metadata when provided."""
        from app.observability.langfuse_spans import create_span

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        create_span(
            name="retrieval_step",
            trace_id="trace-123",
            metadata={"stage": "S040", "node": "build_context"},
        )

        call_kwargs = mock_client.start_span.call_args[1]
        assert call_kwargs["metadata"]["stage"] == "S040"
        assert call_kwargs["metadata"]["node"] == "build_context"


class TestSpanContextManager:
    """Tests for span_context context manager (v3 SDK)."""

    @patch("app.observability.langfuse_spans.get_langfuse_client")
    def test_span_context_creates_and_ends_span(self, mock_get_client: MagicMock) -> None:
        """Context manager should create span on enter and end on exit."""
        from app.observability.langfuse_spans import span_context

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_span = MagicMock()
        mock_client.start_span.return_value = mock_span

        with patch("app.observability.langfuse_spans.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"

            with span_context(name="test_span", trace_id="trace-123"):
                pass

        mock_span.end.assert_called_once()

    @patch("app.observability.langfuse_spans.get_langfuse_client")
    def test_span_context_captures_output(self, mock_get_client: MagicMock) -> None:
        """Context manager should capture output when set."""
        from app.observability.langfuse_spans import span_context

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_span = MagicMock()
        mock_client.start_span.return_value = mock_span

        with patch("app.observability.langfuse_spans.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"

            with span_context(name="test_span", trace_id="trace-123") as span:
                span.set_output({"result": "success"})

        # The output should have been set
        mock_span.update.assert_called()

    @patch("app.observability.langfuse_spans.get_langfuse_client")
    def test_span_context_handles_exceptions_gracefully(self, mock_get_client: MagicMock) -> None:
        """Context manager should end span even on exception."""
        from app.observability.langfuse_spans import span_context

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_span = MagicMock()
        mock_client.start_span.return_value = mock_span

        with patch("app.observability.langfuse_spans.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"

            with (
                pytest.raises(ValueError),
                span_context(name="test_span", trace_id="trace-123"),
            ):
                raise ValueError("Test error")

        # Span should still be ended
        mock_span.end.assert_called_once()


class TestNodeSpan:
    """Tests for node_span helper for LangGraph nodes (v3 SDK)."""

    @patch("app.observability.langfuse_spans.get_langfuse_client")
    def test_node_span_includes_step_number(self, mock_get_client: MagicMock) -> None:
        """Node span should include step number in metadata."""
        from app.observability.langfuse_spans import node_span

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_span = MagicMock()
        mock_client.start_span.return_value = mock_span

        with patch("app.observability.langfuse_spans.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"

            with node_span(
                node_name="build_context",
                step_number="S040",
                trace_id="trace-123",
            ):
                pass

        call_kwargs = mock_client.start_span.call_args[1]
        assert call_kwargs["metadata"]["step_number"] == "S040"

    @patch("app.observability.langfuse_spans.get_langfuse_client")
    def test_node_span_formats_name_correctly(self, mock_get_client: MagicMock) -> None:
        """Node span name should include step number prefix."""
        from app.observability.langfuse_spans import node_span

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_span = MagicMock()
        mock_client.start_span.return_value = mock_span

        with patch("app.observability.langfuse_spans.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"

            with node_span(
                node_name="build_context",
                step_number="S040",
                trace_id="trace-123",
            ):
                pass

        call_kwargs = mock_client.start_span.call_args[1]
        assert call_kwargs["name"] == "S040_build_context"


class TestRetrievalSpan:
    """Tests for retrieval_span helper for search operations (v3 SDK)."""

    @patch("app.observability.langfuse_spans.get_langfuse_client")
    def test_retrieval_span_includes_query(self, mock_get_client: MagicMock) -> None:
        """Retrieval span should include the search query."""
        from app.observability.langfuse_spans import retrieval_span

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_span = MagicMock()
        mock_client.start_span.return_value = mock_span

        with patch("app.observability.langfuse_spans.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"

            with retrieval_span(
                query="rottamazione quater",
                trace_id="trace-123",
            ):
                pass

        call_kwargs = mock_client.start_span.call_args[1]
        assert call_kwargs["input"]["query"] == "rottamazione quater"

    @patch("app.observability.langfuse_spans.get_langfuse_client")
    def test_retrieval_span_includes_search_type(self, mock_get_client: MagicMock) -> None:
        """Retrieval span should include the search type in metadata."""
        from app.observability.langfuse_spans import retrieval_span

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_span = MagicMock()
        mock_client.start_span.return_value = mock_span

        with patch("app.observability.langfuse_spans.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"

            with retrieval_span(
                query="test query",
                trace_id="trace-123",
                search_type="hybrid",
            ):
                pass

        call_kwargs = mock_client.start_span.call_args[1]
        assert call_kwargs["metadata"]["search_type"] == "hybrid"

    @patch("app.observability.langfuse_spans.get_langfuse_client")
    def test_retrieval_span_captures_results_count(self, mock_get_client: MagicMock) -> None:
        """Retrieval span should allow capturing results count."""
        from app.observability.langfuse_spans import retrieval_span

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_span = MagicMock()
        mock_client.start_span.return_value = mock_span

        with patch("app.observability.langfuse_spans.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"

            with retrieval_span(
                query="test query",
                trace_id="trace-123",
            ) as span:
                span.set_output({"results_count": 15})

        mock_span.update.assert_called()


class TestGracefulDegradation:
    """Tests for graceful degradation of spans."""

    def test_span_context_noop_when_client_unavailable(self) -> None:
        """Span context should be a no-op when client is unavailable."""
        from app.observability.langfuse_spans import span_context

        with patch("app.observability.langfuse_spans.get_langfuse_client") as mock_get_client:
            mock_get_client.return_value = None

            # Should not raise, just no-op
            with span_context(name="test_span", trace_id="trace-123") as span:
                span.set_output({"result": "success"})

    def test_node_span_noop_when_client_unavailable(self) -> None:
        """Node span should be a no-op when client is unavailable."""
        from app.observability.langfuse_spans import node_span

        with patch("app.observability.langfuse_spans.get_langfuse_client") as mock_get_client:
            mock_get_client.return_value = None

            # Should not raise, just no-op
            with node_span(
                node_name="build_context",
                step_number="S040",
                trace_id="trace-123",
            ):
                pass

    def test_retrieval_span_noop_when_client_unavailable(self) -> None:
        """Retrieval span should be a no-op when client is unavailable."""
        from app.observability.langfuse_spans import retrieval_span

        with patch("app.observability.langfuse_spans.get_langfuse_client") as mock_get_client:
            mock_get_client.return_value = None

            # Should not raise, just no-op
            with retrieval_span(
                query="test query",
                trace_id="trace-123",
            ):
                pass


class TestSpanLevel:
    """Tests for span level/severity (v3 SDK)."""

    @patch("app.observability.langfuse_spans.get_langfuse_client")
    def test_span_can_set_error_level(self, mock_get_client: MagicMock) -> None:
        """Span should allow setting error level."""
        from app.observability.langfuse_spans import span_context

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_span = MagicMock()
        mock_client.start_span.return_value = mock_span

        with patch("app.observability.langfuse_spans.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"

            with span_context(name="test_span", trace_id="trace-123", level="ERROR"):
                pass

        call_kwargs = mock_client.start_span.call_args[1]
        assert call_kwargs["level"] == "ERROR"


class TestTraceIdGeneration:
    """Tests for trace ID handling (v3 SDK)."""

    @patch("app.observability.langfuse_spans.get_langfuse_client")
    def test_uses_provided_trace_id(self, mock_get_client: MagicMock) -> None:
        """Should use the provided trace_id via trace_context."""
        from app.observability.langfuse_spans import span_context

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_span = MagicMock()
        mock_client.start_span.return_value = mock_span

        with patch("app.observability.langfuse_spans.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"

            with span_context(name="test_span", trace_id="my-trace-id"):
                pass

        # v3 SDK: trace_id passed via trace_context parameter
        call_kwargs = mock_client.start_span.call_args[1]
        assert call_kwargs["trace_context"] == {"trace_id": "my-trace-id"}
