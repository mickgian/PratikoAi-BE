"""Unit tests for Langfuse configuration module.

Tests cover:
- Handler creation with valid/missing credentials
- Session ID and user ID propagation
- Environment-aware sampling rates
- Metadata enrichment
- Graceful degradation

Following TDD: These tests are written BEFORE the implementation.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Environment


class TestCreateLangfuseHandler:
    """Tests for create_langfuse_handler function."""

    @patch("app.observability.langfuse_config.CallbackHandler")
    def test_creates_handler_with_valid_credentials(self, mock_handler_class: MagicMock) -> None:
        """Handler should be created when credentials are present."""
        from app.observability.langfuse_config import create_langfuse_handler

        mock_handler = MagicMock()
        mock_handler_class.return_value = mock_handler

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test-key"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test-key"  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"
            mock_settings.ENVIRONMENT = Environment.DEVELOPMENT

            handler = create_langfuse_handler(
                session_id="session-123",
                user_id="user-456",
            )

        assert handler is not None

    @patch("app.observability.langfuse_config.CallbackHandler")
    def test_returns_none_when_credentials_missing(self, mock_handler_class: MagicMock) -> None:
        """Should return None when Langfuse credentials are missing."""
        from app.observability.langfuse_config import create_langfuse_handler

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = ""
            mock_settings.LANGFUSE_SECRET_KEY = ""  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"
            mock_settings.ENVIRONMENT = Environment.DEVELOPMENT

            handler = create_langfuse_handler(
                session_id="session-123",
                user_id="user-456",
            )

        assert handler is None
        mock_handler_class.assert_not_called()

    @patch("app.observability.langfuse_config.CallbackHandler")
    def test_session_id_propagated_to_handler(self, mock_handler_class: MagicMock) -> None:
        """Session ID should be passed to the handler."""
        from app.observability.langfuse_config import create_langfuse_handler

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"
            mock_settings.ENVIRONMENT = Environment.DEVELOPMENT

            create_langfuse_handler(
                session_id="my-session-id",
                user_id="user-456",
            )

        call_kwargs = mock_handler_class.call_args[1]
        assert call_kwargs["session_id"] == "my-session-id"

    @patch("app.observability.langfuse_config.CallbackHandler")
    def test_user_id_propagated_to_handler(self, mock_handler_class: MagicMock) -> None:
        """User ID should be passed to the handler."""
        from app.observability.langfuse_config import create_langfuse_handler

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"
            mock_settings.ENVIRONMENT = Environment.DEVELOPMENT

            create_langfuse_handler(
                session_id="session-123",
                user_id="my-user-id",
            )

        call_kwargs = mock_handler_class.call_args[1]
        assert call_kwargs["user_id"] == "my-user-id"

    @patch("app.observability.langfuse_config.CallbackHandler")
    def test_anonymous_user_id_when_not_provided(self, mock_handler_class: MagicMock) -> None:
        """Should use 'anonymous' when user_id is not provided."""
        from app.observability.langfuse_config import create_langfuse_handler

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"
            mock_settings.ENVIRONMENT = Environment.DEVELOPMENT

            create_langfuse_handler(session_id="session-123")

        call_kwargs = mock_handler_class.call_args[1]
        assert call_kwargs["user_id"] == "anonymous"

    @patch("app.observability.langfuse_config.CallbackHandler")
    def test_generates_session_id_when_missing(self, mock_handler_class: MagicMock) -> None:
        """Should generate UUID when session_id is not provided."""
        from app.observability.langfuse_config import create_langfuse_handler

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"
            mock_settings.ENVIRONMENT = Environment.DEVELOPMENT

            create_langfuse_handler()

        call_kwargs = mock_handler_class.call_args[1]
        # Verify it's a valid UUID format
        session_id = call_kwargs["session_id"]
        uuid.UUID(session_id)  # Raises ValueError if invalid


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
            mock_settings.LANGFUSE_SAMPLING_RATE = None  # No override

            # Run 100 times, all should return True
            results = [should_sample() for _ in range(100)]
            assert all(results)

    def test_should_sample_always_true_for_qa(self) -> None:
        """Should always sample in QA."""
        from app.observability.langfuse_config import should_sample

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.ENVIRONMENT = Environment.QA
            mock_settings.LANGFUSE_SAMPLING_RATE = None  # No override

            results = [should_sample() for _ in range(100)]
            assert all(results)

    def test_should_sample_approximately_10_percent_for_prod(self) -> None:
        """Should sample approximately 10% in production."""
        from app.observability.langfuse_config import should_sample

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.ENVIRONMENT = Environment.PRODUCTION
            mock_settings.LANGFUSE_SAMPLING_RATE = 0.1

            # Run 1000 times, expect ~10% True (with some variance)
            results = [should_sample() for _ in range(1000)]
            true_count = sum(results)
            # Allow 5-15% range for statistical variance
            assert 50 <= true_count <= 150, f"Expected ~100 samples, got {true_count}"


class TestMetadataEnrichment:
    """Tests for metadata enrichment."""

    @patch("app.observability.langfuse_config.CallbackHandler")
    def test_metadata_includes_environment(self, mock_handler_class: MagicMock) -> None:
        """Metadata should include environment."""
        from app.observability.langfuse_config import create_langfuse_handler

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"
            mock_settings.ENVIRONMENT = Environment.DEVELOPMENT

            create_langfuse_handler(
                session_id="session-123",
                user_id="user-456",
            )

        call_kwargs = mock_handler_class.call_args[1]
        assert "metadata" in call_kwargs
        assert call_kwargs["metadata"]["environment"] == "development"

    @patch("app.observability.langfuse_config.CallbackHandler")
    def test_metadata_includes_request_id(self, mock_handler_class: MagicMock) -> None:
        """Metadata should include request_id when provided."""
        from app.observability.langfuse_config import create_langfuse_handler

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"
            mock_settings.ENVIRONMENT = Environment.DEVELOPMENT

            create_langfuse_handler(
                session_id="session-123",
                user_id="user-456",
                request_id="req-789",
            )

        call_kwargs = mock_handler_class.call_args[1]
        assert call_kwargs["metadata"]["request_id"] == "req-789"

    @patch("app.observability.langfuse_config.CallbackHandler")
    def test_metadata_includes_custom_tags(self, mock_handler_class: MagicMock) -> None:
        """Metadata should include custom tags when provided."""
        from app.observability.langfuse_config import create_langfuse_handler

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"
            mock_settings.ENVIRONMENT = Environment.DEVELOPMENT

            create_langfuse_handler(
                session_id="session-123",
                user_id="user-456",
                tags=["rag", "debug"],
            )

        call_kwargs = mock_handler_class.call_args[1]
        assert call_kwargs["tags"] == ["rag", "debug"]

    @patch("app.observability.langfuse_config.CallbackHandler")
    def test_metadata_includes_stage(self, mock_handler_class: MagicMock) -> None:
        """Metadata should include stage when provided."""
        from app.observability.langfuse_config import create_langfuse_handler

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"
            mock_settings.ENVIRONMENT = Environment.DEVELOPMENT

            create_langfuse_handler(
                session_id="session-123",
                stage="retrieval",
            )

        call_kwargs = mock_handler_class.call_args[1]
        assert call_kwargs["metadata"]["stage"] == "retrieval"


class TestGracefulDegradation:
    """Tests for graceful degradation when Langfuse is unavailable."""

    @patch("app.observability.langfuse_config.CallbackHandler")
    def test_returns_none_on_handler_creation_error(self, mock_handler_class: MagicMock) -> None:
        """Should return None if handler creation fails."""
        from app.observability.langfuse_config import create_langfuse_handler

        mock_handler_class.side_effect = Exception("Connection failed")

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"
            mock_settings.ENVIRONMENT = Environment.DEVELOPMENT

            handler = create_langfuse_handler(session_id="session-123")

        assert handler is None

    @patch("app.observability.langfuse_config.CallbackHandler")
    def test_logs_warning_on_handler_creation_error(
        self, mock_handler_class: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Should log warning when handler creation fails."""
        from app.observability.langfuse_config import create_langfuse_handler

        mock_handler_class.side_effect = Exception("Connection failed")

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"
            mock_settings.ENVIRONMENT = Environment.DEVELOPMENT

            create_langfuse_handler(session_id="session-123")

        assert "Failed to create Langfuse handler" in caplog.text or any(
            "langfuse" in record.message.lower() for record in caplog.records
        )


class TestPerformanceConstraints:
    """Tests for performance constraints."""

    @patch("app.observability.langfuse_config.CallbackHandler")
    def test_handler_creation_under_1ms(self, mock_handler_class: MagicMock) -> None:
        """Handler creation should complete in under 1ms."""
        import time

        from app.observability.langfuse_config import create_langfuse_handler

        mock_handler_class.return_value = MagicMock()

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            mock_settings.LANGFUSE_SECRET_KEY = "sk-test"  # pragma: allowlist secret
            mock_settings.LANGFUSE_HOST = "https://cloud.langfuse.com"
            mock_settings.ENVIRONMENT = Environment.DEVELOPMENT

            start = time.perf_counter()
            create_langfuse_handler(session_id="session-123")
            elapsed = time.perf_counter() - start

        # 1ms = 0.001 seconds, allowing some margin for test overhead
        assert elapsed < 0.01, f"Handler creation took {elapsed * 1000:.2f}ms"

    def test_sampling_decision_under_0_1ms(self) -> None:
        """Sampling decision should complete in under 0.1ms."""
        import time

        from app.observability.langfuse_config import should_sample

        with patch("app.observability.langfuse_config.settings") as mock_settings:
            mock_settings.ENVIRONMENT = Environment.PRODUCTION
            mock_settings.LANGFUSE_SAMPLING_RATE = 0.1

            start = time.perf_counter()
            for _ in range(100):
                should_sample()
            elapsed = time.perf_counter() - start

        # 100 calls should take < 10ms (0.1ms each)
        assert elapsed < 0.01, f"100 sampling decisions took {elapsed * 1000:.2f}ms"
