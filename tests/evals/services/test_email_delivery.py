"""Tests for evaluation report email delivery.

TDD: RED phase - Write tests first, then implement.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from evals.metrics.aggregate import AggregateMetrics


class TestEvalReportEmailService:
    """Tests for EvalReportEmailService."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings with eval report configuration."""
        settings = MagicMock()
        settings.EVAL_REPORT_RECIPIENTS = "test@example.com,test2@example.com"
        settings.STAKEHOLDER_EMAIL = "stakeholder@example.com"
        settings.EVAL_REPORT_ENABLED = True
        settings.SMTP_SERVER = "smtp.test.com"
        settings.SMTP_PORT = 587
        settings.SMTP_USERNAME = "user"
        settings.SMTP_PASSWORD = "pass"  # pragma: allowlist secret
        settings.FROM_EMAIL = "noreply@test.com"
        return settings

    @pytest.fixture
    def sample_metrics(self) -> AggregateMetrics:
        """Create sample metrics for testing."""
        return AggregateMetrics(
            total=10,
            passed=8,
            failed=2,
            overall_pass_rate=0.8,
            overall_mean_score=0.85,
            by_category={},
            by_grader_type={},
            failures=[],
        )

    @pytest.mark.asyncio
    async def test_get_recipients_from_settings(self, mock_settings) -> None:
        """Test recipients are parsed from EVAL_REPORT_RECIPIENTS setting."""
        with patch("evals.services.email_delivery.settings", mock_settings):
            from evals.services.email_delivery import EvalReportEmailService

            service = EvalReportEmailService()
            assert "test@example.com" in service.recipients
            assert "test2@example.com" in service.recipients
            assert len(service.recipients) == 2

    @pytest.mark.asyncio
    async def test_get_recipients_fallback_to_stakeholder(self, mock_settings) -> None:
        """Test fallback to STAKEHOLDER_EMAIL when EVAL_REPORT_RECIPIENTS is empty."""
        mock_settings.EVAL_REPORT_RECIPIENTS = ""
        with patch("evals.services.email_delivery.settings", mock_settings):
            from evals.services.email_delivery import EvalReportEmailService

            service = EvalReportEmailService()
            assert service.recipients == ["stakeholder@example.com"]

    @pytest.mark.asyncio
    async def test_get_recipients_empty_when_no_config(self, mock_settings) -> None:
        """Test empty recipients when no email configured."""
        mock_settings.EVAL_REPORT_RECIPIENTS = ""
        mock_settings.STAKEHOLDER_EMAIL = ""
        with patch("evals.services.email_delivery.settings", mock_settings):
            from evals.services.email_delivery import EvalReportEmailService

            service = EvalReportEmailService()
            assert service.recipients == []

    @pytest.mark.asyncio
    async def test_send_eval_report_success(self, mock_settings, sample_metrics) -> None:
        """Test successful email delivery."""
        with (
            patch("evals.services.email_delivery.settings", mock_settings),
            patch("evals.services.email_delivery.EmailService") as MockEmailService,
        ):
            mock_email_service = MagicMock()
            mock_email_service._send_email = AsyncMock(return_value=True)
            MockEmailService.return_value = mock_email_service

            from evals.services.email_delivery import EvalReportEmailService

            service = EvalReportEmailService()
            result = await service.send_eval_report(sample_metrics, "nightly")

            assert result is True
            # Should be called for each recipient
            assert mock_email_service._send_email.call_count == 2

    @pytest.mark.asyncio
    async def test_send_eval_report_disabled(self, mock_settings, sample_metrics) -> None:
        """Test no email sent when disabled."""
        mock_settings.EVAL_REPORT_ENABLED = False
        with (
            patch("evals.services.email_delivery.settings", mock_settings),
            patch("evals.services.email_delivery.EmailService") as MockEmailService,
        ):
            mock_email_service = MagicMock()
            mock_email_service._send_email = AsyncMock(return_value=True)
            MockEmailService.return_value = mock_email_service

            from evals.services.email_delivery import EvalReportEmailService

            service = EvalReportEmailService()
            result = await service.send_eval_report(sample_metrics, "nightly")

            assert result is True
            mock_email_service._send_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_eval_report_no_recipients(self, mock_settings, sample_metrics) -> None:
        """Test returns False when no recipients configured."""
        mock_settings.EVAL_REPORT_RECIPIENTS = ""
        mock_settings.STAKEHOLDER_EMAIL = ""
        with (
            patch("evals.services.email_delivery.settings", mock_settings),
            patch("evals.services.email_delivery.EmailService") as MockEmailService,
        ):
            mock_email_service = MagicMock()
            MockEmailService.return_value = mock_email_service

            from evals.services.email_delivery import EvalReportEmailService

            service = EvalReportEmailService()
            result = await service.send_eval_report(sample_metrics, "nightly")

            assert result is False

    @pytest.mark.asyncio
    async def test_send_eval_report_partial_failure(self, mock_settings, sample_metrics) -> None:
        """Test handles partial delivery failure."""
        with (
            patch("evals.services.email_delivery.settings", mock_settings),
            patch("evals.services.email_delivery.EmailService") as MockEmailService,
        ):
            mock_email_service = MagicMock()
            # First call succeeds, second fails
            mock_email_service._send_email = AsyncMock(side_effect=[True, False])
            MockEmailService.return_value = mock_email_service

            from evals.services.email_delivery import EvalReportEmailService

            service = EvalReportEmailService()
            result = await service.send_eval_report(sample_metrics, "nightly")

            assert result is False
            assert mock_email_service._send_email.call_count == 2

    @pytest.mark.asyncio
    async def test_send_eval_report_correct_subject(self, mock_settings, sample_metrics) -> None:
        """Test email subject is correctly formatted."""
        with (
            patch("evals.services.email_delivery.settings", mock_settings),
            patch("evals.services.email_delivery.EmailService") as MockEmailService,
        ):
            mock_email_service = MagicMock()
            mock_email_service._send_email = AsyncMock(return_value=True)
            MockEmailService.return_value = mock_email_service

            from evals.services.email_delivery import EvalReportEmailService

            service = EvalReportEmailService()
            await service.send_eval_report(sample_metrics, "nightly")

            # Check subject contains expected parts
            call_args = mock_email_service._send_email.call_args
            subject = call_args.kwargs.get("subject") or call_args[1].get("subject")
            assert "PratikoAI" in subject
            assert "Nightly" in subject
            assert "Eval Report" in subject

    @pytest.mark.asyncio
    async def test_send_eval_report_uses_format_email_body(self, mock_settings, sample_metrics) -> None:
        """Test email body is generated using format_email_body."""
        with (
            patch("evals.services.email_delivery.settings", mock_settings),
            patch("evals.services.email_delivery.EmailService") as MockEmailService,
            patch("evals.services.email_delivery.format_email_body") as mock_format,
        ):
            mock_email_service = MagicMock()
            mock_email_service._send_email = AsyncMock(return_value=True)
            MockEmailService.return_value = mock_email_service
            mock_format.return_value = "<html>Test</html>"

            from evals.services.email_delivery import EvalReportEmailService

            service = EvalReportEmailService()
            await service.send_eval_report(sample_metrics, "weekly")

            mock_format.assert_called_once_with(sample_metrics, "weekly")

    @pytest.mark.asyncio
    async def test_send_eval_report_weekly_mode(self, mock_settings, sample_metrics) -> None:
        """Test email subject reflects weekly mode."""
        with (
            patch("evals.services.email_delivery.settings", mock_settings),
            patch("evals.services.email_delivery.EmailService") as MockEmailService,
        ):
            mock_email_service = MagicMock()
            mock_email_service._send_email = AsyncMock(return_value=True)
            MockEmailService.return_value = mock_email_service

            from evals.services.email_delivery import EvalReportEmailService

            service = EvalReportEmailService()
            await service.send_eval_report(sample_metrics, "weekly")

            call_args = mock_email_service._send_email.call_args
            subject = call_args.kwargs.get("subject") or call_args[1].get("subject")
            assert "Weekly" in subject
