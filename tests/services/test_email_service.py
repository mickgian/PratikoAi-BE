"""Tests for email service."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, patch

import pytest

from app.services.email_service import EmailService
from app.services.metrics_service import (
    Environment,
    MetricResult,
    MetricsReport,
    MetricStatus,
)


class TestEmailService:
    """Test EmailService class."""

    @patch("app.services.email_service.settings")
    @patch("app.services.email_service.MetricsService")
    def test_initialization_with_settings(self, mock_metrics_service, mock_settings):
        """Test EmailService initialization with configured settings."""
        mock_settings.SMTP_SERVER = "smtp.test.com"
        mock_settings.SMTP_PORT = 465
        mock_settings.SMTP_USERNAME = "test@test.com"
        mock_settings.SMTP_PASSWORD = "testpass"
        mock_settings.FROM_EMAIL = "sender@test.com"

        service = EmailService()

        assert service.smtp_server == "smtp.test.com"
        assert service.smtp_port == 465
        assert service.smtp_username == "test@test.com"
        assert service.smtp_password == "testpass"
        assert service.from_email == "sender@test.com"

    @pytest.mark.asyncio
    @patch("app.services.email_service.settings")
    @patch("app.services.email_service.MetricsService")
    async def test_send_metrics_report_no_recipients(self, mock_metrics_service, mock_settings):
        """Test sending metrics report with no recipients."""
        service = EmailService()

        result = await service.send_metrics_report(recipient_emails=[], environments=[Environment.DEVELOPMENT])

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.email_service.settings")
    @patch("app.services.email_service.MetricsService")
    async def test_send_metrics_report_no_reports(self, mock_metrics_service, mock_settings):
        """Test sending metrics report when report generation fails."""
        mock_metrics_instance = mock_metrics_service.return_value
        mock_metrics_instance.generate_metrics_report = AsyncMock(side_effect=Exception("Report error"))

        service = EmailService()
        result = await service.send_metrics_report(
            recipient_emails=["test@test.com"], environments=[Environment.DEVELOPMENT]
        )

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.email_service.settings")
    @patch("app.services.email_service.MetricsService")
    async def test_send_metrics_report_success(self, mock_metrics_service, mock_settings):
        """Test successful metrics report sending."""
        mock_settings.SMTP_USERNAME = None
        mock_settings.SMTP_PASSWORD = None

        # Create mock report
        current_time = datetime.utcnow()
        mock_report = MetricsReport(
            environment=Environment.DEVELOPMENT,
            timestamp=current_time,
            overall_health_score=95.0,
            technical_metrics=[
                MetricResult(
                    name="API Latency",
                    value=150.0,
                    target=500.0,
                    unit="ms",
                    status=MetricStatus.PASS,
                    description="Test metric",
                    timestamp=current_time,
                    environment=Environment.DEVELOPMENT,
                )
            ],
            business_metrics=[
                MetricResult(
                    name="Daily Active Users",
                    value=500.0,
                    target=1000.0,
                    unit="users",
                    status=MetricStatus.PASS,
                    description="Test metric",
                    timestamp=current_time,
                    environment=Environment.DEVELOPMENT,
                )
            ],
            alerts=[],
            recommendations=[],
        )

        mock_metrics_instance = mock_metrics_service.return_value
        mock_metrics_instance.generate_metrics_report = AsyncMock(return_value=mock_report)

        service = EmailService()
        with patch.object(service, "_send_email", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            result = await service.send_metrics_report(
                recipient_emails=["test@test.com"], environments=[Environment.DEVELOPMENT]
            )

            assert result is True
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.email_service.settings")
    @patch("app.services.email_service.MetricsService")
    async def test_send_metrics_report_multiple_recipients(self, mock_metrics_service, mock_settings):
        """Test sending metrics report to multiple recipients."""
        mock_settings.SMTP_USERNAME = None
        mock_settings.SMTP_PASSWORD = None

        # Create mock report
        mock_report = MetricsReport(
            environment=Environment.DEVELOPMENT,
            timestamp=datetime.utcnow(),
            overall_health_score=95.0,
            technical_metrics=[],
            business_metrics=[],
            alerts=[],
            recommendations=[],
        )

        mock_metrics_instance = mock_metrics_service.return_value
        mock_metrics_instance.generate_metrics_report = AsyncMock(return_value=mock_report)

        service = EmailService()
        with patch.object(service, "_send_email", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            result = await service.send_metrics_report(
                recipient_emails=["test1@test.com", "test2@test.com"], environments=[Environment.DEVELOPMENT]
            )

            assert result is True
            assert mock_send.call_count == 2

    @pytest.mark.asyncio
    @patch("app.services.email_service.settings")
    @patch("app.services.email_service.MetricsService")
    async def test_send_metrics_report_partial_failure(self, mock_metrics_service, mock_settings):
        """Test metrics report with partial send failure."""
        mock_settings.SMTP_USERNAME = None
        mock_settings.SMTP_PASSWORD = None

        mock_report = MetricsReport(
            environment=Environment.DEVELOPMENT,
            timestamp=datetime.utcnow(),
            overall_health_score=95.0,
            technical_metrics=[],
            business_metrics=[],
            alerts=[],
            recommendations=[],
        )

        mock_metrics_instance = mock_metrics_service.return_value
        mock_metrics_instance.generate_metrics_report = AsyncMock(return_value=mock_report)

        service = EmailService()
        with patch.object(service, "_send_email", new_callable=AsyncMock) as mock_send:
            # First succeeds, second fails
            mock_send.side_effect = [True, False]

            result = await service.send_metrics_report(
                recipient_emails=["test1@test.com", "test2@test.com"], environments=[Environment.DEVELOPMENT]
            )

            assert result is False

    @patch("app.services.email_service.settings")
    @patch("app.services.email_service.MetricsService")
    def test_generate_html_report(self, mock_metrics_service, mock_settings):
        """Test HTML report generation."""
        service = EmailService()

        current_time = datetime.utcnow()
        mock_report = MetricsReport(
            environment=Environment.DEVELOPMENT,
            timestamp=current_time,
            overall_health_score=95.0,
            technical_metrics=[
                MetricResult(
                    name="API Latency",
                    value=150.0,
                    target=500.0,
                    unit="ms",
                    status=MetricStatus.PASS,
                    description="Test",
                    timestamp=current_time,
                    environment=Environment.DEVELOPMENT,
                )
            ],
            business_metrics=[
                MetricResult(
                    name="DAU",
                    value=500.0,
                    target=1000.0,
                    unit="users",
                    status=MetricStatus.PASS,
                    description="Test",
                    timestamp=current_time,
                    environment=Environment.DEVELOPMENT,
                )
            ],
            alerts=["High memory usage"],
            recommendations=["Scale up instances"],
        )

        reports = {"development": mock_report}
        html = service._generate_html_report(reports)

        assert "PratikoAI System Metrics Report" in html
        assert "development" in html.lower()
        assert "API Latency" in html
        assert "High memory usage" in html
        assert "Scale up instances" in html

    @patch("app.services.email_service.settings")
    @patch("app.services.email_service.MetricsService")
    def test_generate_summary_section(self, mock_metrics_service, mock_settings):
        """Test summary section generation."""
        service = EmailService()

        current_time = datetime.utcnow()
        mock_report_1 = MetricsReport(
            environment=Environment.DEVELOPMENT,
            timestamp=current_time,
            overall_health_score=95.0,
            technical_metrics=[],
            business_metrics=[],
            alerts=[],
            recommendations=[],
        )

        mock_report_2 = MetricsReport(
            environment=Environment.PRODUCTION,
            timestamp=current_time,
            overall_health_score=85.0,
            technical_metrics=[],
            business_metrics=[],
            alerts=[],
            recommendations=[],
        )

        reports = {"development": mock_report_1, "production": mock_report_2}
        html = service._generate_summary_section(reports)

        assert "Overall System Health" in html
        assert "2" in html  # 2 environments
        assert "95.0%" in html
        assert "85.0%" in html

    @patch("app.services.email_service.settings")
    @patch("app.services.email_service.MetricsService")
    def test_generate_environment_section(self, mock_metrics_service, mock_settings):
        """Test environment section generation."""
        service = EmailService()

        current_time = datetime.utcnow()
        mock_report = MetricsReport(
            environment=Environment.DEVELOPMENT,
            timestamp=current_time,
            overall_health_score=95.0,
            technical_metrics=[
                MetricResult(
                    name="API Latency",
                    value=150.0,
                    target=500.0,
                    unit="ms",
                    status=MetricStatus.PASS,
                    description="Test",
                    timestamp=current_time,
                    environment=Environment.DEVELOPMENT,
                )
            ],
            business_metrics=[
                MetricResult(
                    name="DAU",
                    value=500.0,
                    target=1000.0,
                    unit="users",
                    status=MetricStatus.PASS,
                    description="Test",
                    timestamp=current_time,
                    environment=Environment.DEVELOPMENT,
                )
            ],
            alerts=["Alert 1"],
            recommendations=["Rec 1"],
        )

        html = service._generate_environment_section("development", mock_report)

        assert "Development Environment" in html
        assert "95.0%" in html
        assert "API Latency" in html
        assert "DAU" in html
        assert "Alert 1" in html
        assert "Rec 1" in html

    @patch("app.services.email_service.settings")
    @patch("app.services.email_service.MetricsService")
    def test_get_health_class(self, mock_metrics_service, mock_settings):
        """Test health score CSS class mapping."""
        service = EmailService()

        assert service._get_health_class(95.0) == "health-excellent"
        assert service._get_health_class(90.0) == "health-excellent"
        assert service._get_health_class(85.0) == "health-good"
        assert service._get_health_class(70.0) == "health-good"
        assert service._get_health_class(65.0) == "health-poor"
        assert service._get_health_class(50.0) == "health-poor"

    @pytest.mark.asyncio
    @patch("app.services.email_service.settings")
    @patch("app.services.email_service.MetricsService")
    async def test_send_email_no_credentials(self, mock_metrics_service, mock_settings):
        """Test email sending without SMTP credentials (dev mode)."""
        service = EmailService()
        service.smtp_username = None
        service.smtp_password = None

        result = await service._send_email(
            recipient_email="test@test.com", subject="Test Subject", html_content="<p>Test</p>"
        )

        # Should return True (logged instead of sent)
        assert result is True

    @pytest.mark.asyncio
    @patch("app.services.email_service.smtplib.SMTP")
    @patch("app.services.email_service.settings")
    @patch("app.services.email_service.MetricsService")
    async def test_send_email_with_credentials_success(self, mock_metrics_service, mock_settings, mock_smtp):
        """Test successful email sending with SMTP credentials."""
        service = EmailService()
        service.smtp_username = "user@test.com"
        service.smtp_password = "password"
        service.smtp_server = "smtp.test.com"
        service.smtp_port = 587

        # Mock SMTP context manager
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = await service._send_email(
            recipient_email="test@test.com", subject="Test Subject", html_content="<p>Test</p>"
        )

        assert result is True
        mock_smtp.assert_called_once_with("smtp.test.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user@test.com", "password")
        mock_server.send_message.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.email_service.smtplib.SMTP")
    @patch("app.services.email_service.settings")
    @patch("app.services.email_service.MetricsService")
    async def test_send_email_smtp_error(self, mock_metrics_service, mock_settings, mock_smtp):
        """Test email sending SMTP error handling."""
        service = EmailService()
        service.smtp_username = "user@test.com"
        service.smtp_password = "password"

        # Mock SMTP to raise error
        mock_smtp.side_effect = Exception("SMTP connection failed")

        result = await service._send_email(
            recipient_email="test@test.com", subject="Test Subject", html_content="<p>Test</p>"
        )

        assert result is False
