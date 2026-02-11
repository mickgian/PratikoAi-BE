"""Unit tests for Langfuse configuration module.

Tests cover:
- open_langfuse_trace context manager (v3 best-practice pattern)
- W3C trace_id generation (32-char hex format)
- Session ID, user ID, tags propagation via update_current_trace
- Environment-aware sampling rates
- Graceful degradation
- record_latency_score

Updated for DEV-255: Replaces create_langfuse_handler with open_langfuse_trace.
"""

import os
import re
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Environment


@pytest.fixture(autouse=True)
def _isolate_langfuse_credentials(monkeypatch):
    """DEV-255 Fix 4: Prevent tests from emitting real Langfuse data.

    Clears Langfuse environment variables so that even if credentials are
    configured in the developer's shell, the Langfuse SDK won't connect.
    """
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)


class TestOpenLangfuseTrace:
    """Tests for open_langfuse_trace context manager (DEV-255)."""

    @patch("app.observability.langfuse_config.CallbackHandler")
    @patch("app.observability.langfuse_config.get_client")
    def test_opens_span_with_trace_name(self, mock_get_client: MagicMock, mock_handler_class: MagicMock) -> None:
        """Should call start_as_current_span with name only (no trace_context)."""
        from app.observability.langfuse_config import open_langfuse_trace

        mock_client = MagicMock()
        mock_span = MagicMock()
        mock_client.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_client.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get_current_trace_id.return_value = "a" * 32
        mock_get_client.return_value = mock_client

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret

            with open_langfuse_trace(trace_name="rag-query"):
                pass

        mock_client.start_as_current_span.assert_called_once()
        call_kwargs = mock_client.start_as_current_span.call_args[1]
        assert call_kwargs["name"] == "rag-query"
        # v3 pattern: NO trace_context passed - let SDK create natural root span
        assert "trace_context" not in call_kwargs

    @patch("app.observability.langfuse_config.CallbackHandler")
    @patch("app.observability.langfuse_config.get_client")
    def test_generates_w3c_trace_id(self, mock_get_client: MagicMock, mock_handler_class: MagicMock) -> None:
        """Trace ID should come from client.get_current_trace_id() (W3C format)."""
        from app.observability.langfuse_config import open_langfuse_trace

        mock_client = MagicMock()
        mock_span = MagicMock()
        mock_client.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_client.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
        # v3 SDK: get_current_trace_id() returns the auto-generated trace ID
        mock_client.get_current_trace_id.return_value = "abcd1234abcd1234abcd1234abcd1234"
        mock_get_client.return_value = mock_client

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret

            with open_langfuse_trace(trace_name="rag-query") as ctx:
                trace_id = ctx.trace_id

        # Should call get_current_trace_id() to retrieve the auto-generated ID
        mock_client.get_current_trace_id.assert_called()
        # W3C trace ID: 32 lowercase hex characters
        assert re.match(r"^[0-9a-f]{32}$", trace_id), f"Expected W3C trace_id, got: {trace_id}"

    @patch("app.observability.langfuse_config.CallbackHandler")
    @patch("app.observability.langfuse_config.get_client")
    def test_sets_trace_user_session_tags(self, mock_get_client: MagicMock, mock_handler_class: MagicMock) -> None:
        """Should call update_current_trace with user_id, session_id, tags."""
        from app.observability.langfuse_config import open_langfuse_trace

        mock_client = MagicMock()
        mock_span = MagicMock()
        mock_client.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_client.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get_current_trace_id.return_value = "a" * 32
        mock_get_client.return_value = mock_client

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret

            with open_langfuse_trace(
                trace_name="rag-query",
                session_id="session-123",
                user_id="user-456",
                tags=["streaming"],
            ):
                pass

        mock_client.update_current_trace.assert_called_once()
        call_kwargs = mock_client.update_current_trace.call_args[1]
        assert call_kwargs["name"] == "rag-query"
        assert call_kwargs["user_id"] == "user-456"
        assert call_kwargs["session_id"] == "session-123"
        assert call_kwargs["tags"] == ["streaming"]

    @patch("app.observability.langfuse_config.CallbackHandler")
    @patch("app.observability.langfuse_config.get_client")
    def test_creates_callback_handler_inside_context(
        self, mock_get_client: MagicMock, mock_handler_class: MagicMock
    ) -> None:
        """A CallbackHandler should be created inside the context."""
        from app.observability.langfuse_config import open_langfuse_trace

        mock_client = MagicMock()
        mock_span = MagicMock()
        mock_client.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_client.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get_current_trace_id.return_value = "a" * 32
        mock_get_client.return_value = mock_client
        mock_handler_class.return_value = MagicMock()

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret

            with open_langfuse_trace(trace_name="rag-query") as ctx:
                assert ctx.handler is not None

        mock_handler_class.assert_called_once()

    @patch("app.observability.langfuse_config.CallbackHandler")
    @patch("app.observability.langfuse_config.get_client")
    def test_yields_trace_context_dataclass(self, mock_get_client: MagicMock, mock_handler_class: MagicMock) -> None:
        """Should yield a LangfuseTraceContext with handler, trace_id, and metadata."""
        from app.observability.langfuse_config import LangfuseTraceContext, open_langfuse_trace

        mock_client = MagicMock()
        mock_span = MagicMock()
        mock_client.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_client.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get_current_trace_id.return_value = "a" * 32
        mock_get_client.return_value = mock_client

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret

            with open_langfuse_trace(trace_name="rag-query") as ctx:
                assert isinstance(ctx, LangfuseTraceContext)
                assert ctx.handler is not None
                assert ctx.trace_id  # non-empty
                assert isinstance(ctx.metadata, dict)

    @patch("app.observability.langfuse_config.CallbackHandler")
    @patch("app.observability.langfuse_config.get_client")
    def test_flushes_on_exit(self, mock_get_client: MagicMock, mock_handler_class: MagicMock) -> None:
        """client.flush() should be called when exiting the context."""
        from app.observability.langfuse_config import open_langfuse_trace

        mock_client = MagicMock()
        mock_span = MagicMock()
        mock_client.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_client.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get_current_trace_id.return_value = "a" * 32
        mock_get_client.return_value = mock_client

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret

            with open_langfuse_trace(trace_name="rag-query"):
                mock_client.flush.assert_not_called()

        mock_client.flush.assert_called_once()

    def test_graceful_degradation_no_credentials(self) -> None:
        """Should yield no-op context when Langfuse credentials are missing."""
        from app.observability.langfuse_config import open_langfuse_trace

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = ""
            mock_settings.LANGFUSE_SECRET_KEY = ""  # pragma: allowlist secret

            with open_langfuse_trace(trace_name="rag-query") as ctx:
                assert ctx.handler is None
                assert ctx.trace_id == ""
                assert ctx.metadata == {}

    @patch("app.observability.langfuse_config.get_client")
    def test_graceful_degradation_on_exception(self, mock_get_client: MagicMock) -> None:
        """Should catch and log errors, never raise from the context manager."""
        from app.observability.langfuse_config import open_langfuse_trace

        mock_get_client.side_effect = Exception("Connection failed")

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret

            # Should NOT raise
            with open_langfuse_trace(trace_name="rag-query") as ctx:
                assert ctx.handler is None
                assert ctx.trace_id == ""

    @patch("app.observability.langfuse_config.CallbackHandler")
    @patch("app.observability.langfuse_config.get_client")
    def test_sets_current_trace_id_contextvar(self, mock_get_client: MagicMock, mock_handler_class: MagicMock) -> None:
        """get_current_trace_id() should return the W3C ID inside the context."""
        from app.observability.langfuse_config import get_current_trace_id, open_langfuse_trace

        mock_client = MagicMock()
        mock_span = MagicMock()
        mock_client.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_client.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get_current_trace_id.return_value = "abcd1234abcd1234abcd1234abcd1234"
        mock_get_client.return_value = mock_client

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret

            with open_langfuse_trace(trace_name="rag-query") as ctx:
                current_id = get_current_trace_id()
                assert current_id == ctx.trace_id
                assert re.match(r"^[0-9a-f]{32}$", current_id)

    @patch("app.observability.langfuse_config.CallbackHandler")
    @patch("app.observability.langfuse_config.get_client")
    def test_account_code_used_as_user_id(self, mock_get_client: MagicMock, mock_handler_class: MagicMock) -> None:
        """account_code should be used as user_id when provided."""
        from app.observability.langfuse_config import open_langfuse_trace

        mock_client = MagicMock()
        mock_span = MagicMock()
        mock_client.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_client.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get_current_trace_id.return_value = "a" * 32
        mock_get_client.return_value = mock_client

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret

            with open_langfuse_trace(
                trace_name="rag-query",
                user_id="42",
                account_code="PRA70021-1",
            ):
                pass

        call_kwargs = mock_client.update_current_trace.call_args[1]
        assert call_kwargs["user_id"] == "PRA70021-1"

    @patch("app.observability.langfuse_config.CallbackHandler")
    @patch("app.observability.langfuse_config.get_client")
    def test_query_type_in_metadata_not_tags(self, mock_get_client: MagicMock, mock_handler_class: MagicMock) -> None:
        """'new'/'followup' should be in metadata, not in tags."""
        from app.observability.langfuse_config import open_langfuse_trace

        mock_client = MagicMock()
        mock_span = MagicMock()
        mock_client.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_client.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get_current_trace_id.return_value = "a" * 32
        mock_get_client.return_value = mock_client

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret

            with open_langfuse_trace(
                trace_name="rag-stream",
                tags=["streaming"],
                is_followup=True,
            ) as ctx:
                # query_type should be in metadata
                assert ctx.metadata.get("query_type") == "followup"

        # Tags should NOT contain 'new' or 'followup'
        call_kwargs = mock_client.update_current_trace.call_args[1]
        tags = call_kwargs["tags"]
        assert "new" not in tags
        assert "followup" not in tags
        assert "rag" not in tags

    @patch("app.observability.langfuse_config.CallbackHandler")
    @patch("app.observability.langfuse_config.get_client")
    def test_metadata_includes_pipeline_version(
        self, mock_get_client: MagicMock, mock_handler_class: MagicMock
    ) -> None:
        """Metadata should include pipeline_version and has_attachments."""
        from app.observability.langfuse_config import open_langfuse_trace

        mock_client = MagicMock()
        mock_span = MagicMock()
        mock_client.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_client.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get_current_trace_id.return_value = "a" * 32
        mock_get_client.return_value = mock_client

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret

            with open_langfuse_trace(
                trace_name="rag-query",
                has_attachments=True,
                studio_id="studio-abc",
            ) as ctx:
                assert ctx.metadata["pipeline_version"] == "unified"
                assert ctx.metadata["has_attachments"] is True
                assert ctx.metadata["studio_id"] == "studio-abc"


class TestContextvarReset:
    """Tests for DEV-255: contextvar reset on context exit."""

    @patch("app.observability.langfuse_config.CallbackHandler")
    @patch("app.observability.langfuse_config.get_client")
    def test_contextvar_reset_on_exit(self, mock_get_client: MagicMock, mock_handler_class: MagicMock) -> None:
        """_current_trace_id should be None after context exits (prevent leakage)."""
        from app.observability.langfuse_config import get_current_trace_id, open_langfuse_trace

        mock_client = MagicMock()
        mock_span = MagicMock()
        mock_client.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_client.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.get_current_trace_id.return_value = "a" * 32
        mock_get_client.return_value = mock_client

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret

            # Inside context, trace_id should be set
            with open_langfuse_trace(trace_name="rag-query"):
                inside_id = get_current_trace_id()
                assert inside_id == "a" * 32

            # After exiting context, trace_id should be reset to None
            outside_id = get_current_trace_id()
            assert outside_id is None

    @patch("app.observability.langfuse_config.CallbackHandler")
    @patch("app.observability.langfuse_config.get_client")
    def test_contextvar_reset_on_exception(self, mock_get_client: MagicMock, mock_handler_class: MagicMock) -> None:
        """_current_trace_id should be None even if exception occurs inside context."""
        from contextlib import contextmanager

        from app.observability.langfuse_config import get_current_trace_id, open_langfuse_trace

        mock_client = MagicMock()
        mock_client.get_current_trace_id.return_value = "b" * 32

        # Create a proper context manager mock that propagates exceptions
        @contextmanager
        def mock_span_context(name):
            yield MagicMock()

        mock_client.start_as_current_span = mock_span_context
        mock_get_client.return_value = mock_client

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret

            with (
                pytest.raises(ValueError),
                open_langfuse_trace(trace_name="rag-query"),
            ):
                raise ValueError("Test exception")

            # After exception, trace_id should still be reset to None
            outside_id = get_current_trace_id()
            assert outside_id is None


class TestSamplingRates:
    """Tests for environment-aware sampling rates."""

    def test_development_sampling_rate_is_100_percent(self) -> None:
        """Development environment should have 100% sampling."""
        from app.observability.langfuse_config import get_sampling_rate

        rate = get_sampling_rate(Environment.DEVELOPMENT)
        assert rate == 1.0

    def test_qa_sampling_rate_is_100_percent(self) -> None:
        """QA environment should have 100% sampling."""
        from app.observability.langfuse_config import get_sampling_rate

        rate = get_sampling_rate(Environment.QA)
        assert rate == 1.0

    def test_production_sampling_rate_is_10_percent(self) -> None:
        """Production environment should have 10% sampling by default."""
        from app.observability.langfuse_config import get_sampling_rate

        rate = get_sampling_rate(Environment.PRODUCTION)
        assert rate == 0.1

    def test_custom_sampling_rate_override(self) -> None:
        """Custom sampling rate should override default."""
        from app.observability.langfuse_config import get_sampling_rate

        rate = get_sampling_rate(Environment.PRODUCTION, override_rate=0.5)
        assert rate == 0.5

    def test_invalid_sampling_rate_clamped_to_max(self) -> None:
        """Sampling rate > 1.0 should be clamped to 1.0."""
        from app.observability.langfuse_config import get_sampling_rate

        rate = get_sampling_rate(Environment.PRODUCTION, override_rate=1.5)
        assert rate == 1.0

    def test_negative_sampling_rate_clamped_to_zero(self) -> None:
        """Sampling rate < 0 should be clamped to 0."""
        from app.observability.langfuse_config import get_sampling_rate

        rate = get_sampling_rate(Environment.PRODUCTION, override_rate=-0.5)
        assert rate == 0.0


class TestShouldSample:
    """Tests for sampling decision function."""

    def test_should_sample_always_true_for_dev(self) -> None:
        """Should always sample in development."""
        from app.observability.langfuse_config import should_sample

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.ENVIRONMENT = Environment.DEVELOPMENT
            mock_settings.LANGFUSE_SAMPLING_RATE = None

            results = [should_sample() for _ in range(100)]
            assert all(results)

    def test_should_sample_always_true_for_qa(self) -> None:
        """Should always sample in QA."""
        from app.observability.langfuse_config import should_sample

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.ENVIRONMENT = Environment.QA
            mock_settings.LANGFUSE_SAMPLING_RATE = None

            results = [should_sample() for _ in range(100)]
            assert all(results)

    def test_should_sample_approximately_10_percent_for_prod(self) -> None:
        """Should sample approximately 10% in production."""
        from app.observability.langfuse_config import should_sample

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.ENVIRONMENT = Environment.PRODUCTION
            mock_settings.LANGFUSE_SAMPLING_RATE = 0.1

            results = [should_sample() for _ in range(1000)]
            true_count = sum(results)
            assert 50 <= true_count <= 150, f"Expected ~100 samples, got {true_count}"


class TestRecordLatencyScore:
    """Tests for record_latency_score function (DEV-255)."""

    @patch("app.observability.langfuse_config.get_client")
    def test_creates_score_with_correct_name(self, mock_get_client: MagicMock) -> None:
        """Score should be created with name 'latency-ms'."""
        from app.observability.langfuse_config import record_latency_score

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        record_latency_score(150.5, trace_id="a" * 32)

        mock_client.create_score.assert_called_once()
        call_kwargs = mock_client.create_score.call_args[1]
        assert call_kwargs["name"] == "latency-ms"

    @patch("app.observability.langfuse_config.get_client")
    def test_creates_score_with_numeric_value(self, mock_get_client: MagicMock) -> None:
        """Score value should be the latency in milliseconds."""
        from app.observability.langfuse_config import record_latency_score

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        record_latency_score(250.0, trace_id="b" * 32)

        call_kwargs = mock_client.create_score.call_args[1]
        assert call_kwargs["value"] == 250.0
        assert call_kwargs["data_type"] == "NUMERIC"

    def test_noop_when_no_trace_id(self) -> None:
        """Should not raise or create score when trace_id is None."""
        from app.observability.langfuse_config import record_latency_score

        record_latency_score(100.0, trace_id=None)

    @patch("app.observability.langfuse_config.get_client")
    def test_noop_when_negative_latency(self, mock_get_client: MagicMock) -> None:
        """Should skip recording when latency is negative."""
        from app.observability.langfuse_config import record_latency_score

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        record_latency_score(-5.0, trace_id="c" * 32)

        mock_client.create_score.assert_not_called()

    @patch("app.observability.langfuse_config.get_client")
    def test_logs_warning_on_error(self, mock_get_client: MagicMock) -> None:
        """Should log warning instead of raising on errors."""
        from app.observability.langfuse_config import record_latency_score

        mock_client = MagicMock()
        mock_client.create_score.side_effect = Exception("Network error")
        mock_get_client.return_value = mock_client

        # Should not raise
        record_latency_score(100.0, trace_id="d" * 32)
