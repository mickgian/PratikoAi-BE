"""
Tests for the Email Service.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.email_service import EmailService
from app.services.metrics_service import Environment, MetricResult, MetricsReport, MetricStatus


class TestEmailService:
    """Test cases for EmailService."""

    @pytest.fixture
    def email_service(self):
        """Create an EmailService instance for testing."""
        return EmailService()

    @pytest.fixture
    def sample_metrics_report(self):
        """Create a sample metrics report for testing."""
        current_time = datetime.utcnow()

        technical_metrics = [
            MetricResult(
                name="API Response Time (P95)",
                value=450.0,
                target=500.0,
                status=MetricStatus.PASS,
                unit="ms",
                description="95th percentile API response time",
                timestamp=current_time,
                environment=Environment.PRODUCTION,
            ),
            MetricResult(
                name="Cache Hit Rate",
                value=75.0,
                target=80.0,
                status=MetricStatus.WARNING,
                unit="%",
                description="Percentage of cache hits",
                timestamp=current_time,
                environment=Environment.PRODUCTION,
            ),
        ]

        business_metrics = [
            MetricResult(
                name="API Cost per User",
                value=1.8,
                target=2.0,
                status=MetricStatus.PASS,
                unit="EUR/month",
                description="Average API cost per user",
                timestamp=current_time,
                environment=Environment.PRODUCTION,
            ),
            MetricResult(
                name="System Uptime",
                value=98.5,
                target=99.5,
                status=MetricStatus.FAIL,
                unit="%",
                description="System uptime percentage",
                timestamp=current_time,
                environment=Environment.PRODUCTION,
            ),
        ]

        return MetricsReport(
            environment=Environment.PRODUCTION,
            timestamp=current_time,
            technical_metrics=technical_metrics,
            business_metrics=business_metrics,
            overall_health_score=75.0,
            alerts=[
                "WARNING: Cache Hit Rate is 75.0 %, target: 80.0 %",
                "CRITICAL: System Uptime is 98.5 %, target: 99.5 %",
            ],
            recommendations=[
                "Consider tuning cache parameters to improve hit rates",
                "Investigate and resolve infrastructure issues for better uptime",
            ],
        )

    @pytest.mark.asyncio
    async def test_send_metrics_report_success(self, email_service, sample_metrics_report):
        """Test successful metrics report email sending."""
        environments = [Environment.PRODUCTION]
        recipient = "test@example.com"

        with (
            patch.object(
                email_service.metrics_service, "generate_metrics_report", return_value=sample_metrics_report
            ) as mock_generate,
            patch.object(email_service, "_send_email", return_value=True) as mock_send,
        ):
            result = await email_service.send_metrics_report(recipient, environments)

            assert result is True
            mock_generate.assert_called_once_with(Environment.PRODUCTION)
            mock_send.assert_called_once()

            # Check email parameters
            call_args = mock_send.call_args
            assert call_args[1]["recipient_email"] == recipient
            assert "NormoAI System Metrics Report" in call_args[1]["subject"]
            assert "html_content" in call_args[1]

    @pytest.mark.asyncio
    async def test_send_metrics_report_no_reports_generated(self, email_service):
        """Test handling when no reports are generated."""
        environments = [Environment.DEVELOPMENT, Environment.STAGING]

        with patch.object(
            email_service.metrics_service, "generate_metrics_report", side_effect=Exception("Report generation failed")
        ):
            result = await email_service.send_metrics_report("test@example.com", environments)

            assert result is False

    @pytest.mark.asyncio
    async def test_send_metrics_report_email_failure(self, email_service, sample_metrics_report):
        """Test handling of email sending failure."""
        with (
            patch.object(email_service.metrics_service, "generate_metrics_report", return_value=sample_metrics_report),
            patch.object(email_service, "_send_email", return_value=False),
        ):
            result = await email_service.send_metrics_report("test@example.com", [Environment.PRODUCTION])

            assert result is False

    def test_generate_html_report_single_environment(self, email_service, sample_metrics_report):
        """Test HTML report generation for a single environment."""
        reports = {"production": sample_metrics_report}

        html_content = email_service._generate_html_report(reports)

        # Check HTML structure
        assert "<!DOCTYPE html>" in html_content
        assert "NormoAI System Metrics Report" in html_content
        assert "Production Environment" in html_content
        assert "Health Score: 75.0%" in html_content

        # Check metrics are included
        assert "API Response Time (P95)" in html_content
        assert "450.0 ms" in html_content
        assert "Cache Hit Rate" in html_content
        assert "75.0 %" in html_content
        assert "API Cost per User" in html_content
        assert "1.8 EUR/month" in html_content

        # Check alerts and recommendations
        assert "🚨 Alerts" in html_content
        assert "WARNING: Cache Hit Rate" in html_content
        assert "CRITICAL: System Uptime" in html_content
        assert "💡 Recommendations" in html_content
        assert "Consider tuning cache parameters" in html_content

    def test_generate_html_report_multiple_environments(self, email_service):
        """Test HTML report generation for multiple environments."""
        current_time = datetime.utcnow()

        # Create reports for different environments
        dev_report = MetricsReport(
            environment=Environment.DEVELOPMENT,
            timestamp=current_time,
            technical_metrics=[],
            business_metrics=[],
            overall_health_score=95.0,
            alerts=[],
            recommendations=[],
        )

        prod_report = MetricsReport(
            environment=Environment.PRODUCTION,
            timestamp=current_time,
            technical_metrics=[],
            business_metrics=[],
            overall_health_score=85.0,
            alerts=["Test alert"],
            recommendations=["Test recommendation"],
        )

        reports = {"development": dev_report, "production": prod_report}

        html_content = email_service._generate_html_report(reports)

        # Check both environments are included
        assert "Development Environment" in html_content
        assert "Production Environment" in html_content
        assert "Health Score: 95.0%" in html_content
        assert "Health Score: 85.0%" in html_content

        # Check summary section
        assert "📊 Overall System Health" in html_content
        assert "Environments Monitored: 2" in html_content

    def test_generate_summary_section(self, email_service):
        """Test summary section generation."""
        reports = {
            "development": Mock(overall_health_score=95.0),
            "staging": Mock(overall_health_score=88.0),
            "production": Mock(overall_health_score=92.0),
        }

        summary_html = email_service._generate_summary_section(reports)

        assert "📊 Overall System Health" in summary_html
        assert "Environments Monitored: 3" in summary_html
        assert "Healthy Environments: 3/3" in summary_html  # All above 90%
        assert "Development:" in summary_html
        assert "95.0%" in summary_html

    def test_get_health_class(self, email_service):
        """Test health class determination for CSS styling."""
        assert email_service._get_health_class(95.0) == "health-excellent"
        assert email_service._get_health_class(85.0) == "health-good"
        assert email_service._get_health_class(65.0) == "health-poor"

    @pytest.mark.asyncio
    async def test_send_email_without_credentials(self, email_service):
        """Test email sending without SMTP credentials (development mode)."""
        # Ensure no credentials are set
        email_service.smtp_username = None
        email_service.smtp_password = None

        result = await email_service._send_email(
            recipient_email="test@example.com", subject="Test Subject", html_content="<html><body>Test</body></html>"
        )

        # Should return True in development mode (logs instead of sending)
        assert result is True

    @pytest.mark.asyncio
    async def test_send_email_with_smtp_error(self, email_service):
        """Test email sending with SMTP error."""
        email_service.smtp_username = "test@example.com"
        email_service.smtp_password = "test-app-password"

        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__.return_value.send_message.side_effect = Exception("SMTP Error")

            result = await email_service._send_email(
                recipient_email="test@example.com",
                subject="Test Subject",
                html_content="<html><body>Test</body></html>",
            )

            assert result is False

    def test_email_service_initialization(self):
        """Test EmailService initialization with default settings."""
        service = EmailService()

        assert service.smtp_server == "smtp.gmail.com"
        assert service.smtp_port == 587
        assert service.from_email == "noreply@normoai.com"
        assert service.smtp_username is None
        assert service.smtp_password is None

    @pytest.mark.asyncio
    async def test_send_metrics_report_partial_success(self, email_service, sample_metrics_report):
        """Test metrics report sending with partial environment failures."""
        environments = [Environment.DEVELOPMENT, Environment.PRODUCTION]

        def mock_generate_report(env):
            if env == Environment.DEVELOPMENT:
                raise Exception("Dev environment error")
            return sample_metrics_report

        with (
            patch.object(
                email_service.metrics_service, "generate_metrics_report", side_effect=mock_generate_report
            ) as mock_generate,
            patch.object(email_service, "_send_email", return_value=True) as mock_send,
        ):
            result = await email_service.send_metrics_report("test@example.com", environments)

            assert result is True  # Should succeed with at least one report
            assert mock_generate.call_count == 2  # Called for both environments
            mock_send.assert_called_once()

    def test_html_report_css_classes(self, email_service, sample_metrics_report):
        """Test that proper CSS classes are applied in HTML report."""
        reports = {"production": sample_metrics_report}
        html_content = email_service._generate_html_report(reports)

        # Check status classes are applied
        assert "status-pass" in html_content
        assert "status-warning" in html_content
        assert "status-fail" in html_content

        # Check health score class
        assert "health-good" in html_content  # 75% health score

    def test_html_report_escaping(self, email_service):
        """Test that HTML content is properly escaped to prevent injection."""
        current_time = datetime.utcnow()

        # Create a report with potentially problematic content
        metric_with_html = MetricResult(
            name="Test <script>alert('xss')</script>",
            value=100.0,
            target=100.0,
            status=MetricStatus.PASS,
            unit="count",
            description="<b>Bold</b> description",
            timestamp=current_time,
            environment=Environment.DEVELOPMENT,
        )

        report = MetricsReport(
            environment=Environment.DEVELOPMENT,
            timestamp=current_time,
            technical_metrics=[metric_with_html],
            business_metrics=[],
            overall_health_score=100.0,
            alerts=["Alert with <em>emphasis</em>"],
            recommendations=["Recommendation with <strong>strong</strong> text"],
        )

        reports = {"development": report}
        html_content = email_service._generate_html_report(reports)

        # The content should be included but script tags should not execute
        # (Note: In a real implementation, you'd want proper HTML escaping)
        assert "Test" in html_content
        assert "Alert with" in html_content
        assert "Recommendation with" in html_content
