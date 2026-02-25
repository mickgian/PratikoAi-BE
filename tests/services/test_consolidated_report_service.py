# mypy: disable-error-code="arg-type,call-overload,misc,assignment"
"""Tests for Consolidated Report Service.

Consolidates DEV, QA, and PRODUCTION daily reports into a single email
with collapsible sections per environment.
"""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Environment
from app.services.consolidated_report_service import (
    ConsolidatedReportService,
    EnvironmentReportConfig,
)

# =============================================================================
# EnvironmentReportConfig Tests
# =============================================================================


class TestEnvironmentReportConfig:
    """Tests for EnvironmentReportConfig dataclass."""

    def test_creation_with_required_fields(self):
        """Test config creation with all required fields."""
        config = EnvironmentReportConfig(
            environment=Environment.QA,
            postgres_url="postgresql+asyncpg://user:pass@host:5432/db",
        )

        assert config.environment == Environment.QA
        assert config.postgres_url == "postgresql+asyncpg://user:pass@host:5432/db"
        assert config.enabled is True

    def test_creation_disabled(self):
        """Test config creation with enabled=False."""
        config = EnvironmentReportConfig(
            environment=Environment.PRODUCTION,
            postgres_url="",
            enabled=False,
        )

        assert config.environment == Environment.PRODUCTION
        assert config.enabled is False

    def test_postgres_url_auto_conversion(self):
        """Test that postgresql:// is auto-converted to postgresql+asyncpg://."""
        config = EnvironmentReportConfig(
            environment=Environment.DEVELOPMENT,
            postgres_url="postgresql://user:pass@host:5432/db",
        )

        assert config.async_postgres_url == "postgresql+asyncpg://user:pass@host:5432/db"

    def test_postgres_url_already_async(self):
        """Test that postgresql+asyncpg:// is left unchanged."""
        config = EnvironmentReportConfig(
            environment=Environment.QA,
            postgres_url="postgresql+asyncpg://user:pass@host:5432/db",
        )

        assert config.async_postgres_url == "postgresql+asyncpg://user:pass@host:5432/db"


# =============================================================================
# ConsolidatedReportService Tests
# =============================================================================


class TestConsolidatedReportService:
    """Tests for ConsolidatedReportService class."""

    def test_initialization(self):
        """Test service initialization with environment configs."""
        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
            EnvironmentReportConfig(
                environment=Environment.QA,
                postgres_url="postgresql+asyncpg://qa:pass@localhost/qa",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)

        assert len(service.env_configs) == 2

    def test_initialization_with_disabled_env(self):
        """Test that disabled environments are filtered out."""
        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
                enabled=True,
            ),
            EnvironmentReportConfig(
                environment=Environment.PRODUCTION,
                postgres_url="",
                enabled=False,
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)

        # Only enabled configs are active
        assert len(service.active_configs) == 1
        assert service.active_configs[0].environment == Environment.DEVELOPMENT

    def test_production_placeholder_always_included(self):
        """Test that PRODUCTION placeholder is always shown in the email."""
        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)

        # All 3 environments should be in display order (DEV, QA, PROD)
        assert len(service.display_environments) == 3


# =============================================================================
# Ingestion Report HTML Generation Tests
# =============================================================================


class TestConsolidatedIngestionReportHTML:
    """Tests for consolidated ingestion report HTML generation."""

    def test_html_contains_all_environment_sections(self):
        """Test that HTML has sections for DEV, QA, and PROD."""
        from app.services.ingestion_report_service import (
            DailyIngestionReport,
            SourceStats,
        )

        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
            EnvironmentReportConfig(
                environment=Environment.QA,
                postgres_url="postgresql+asyncpg://qa:pass@localhost/qa",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)

        # Create mock reports for each environment
        dev_report = DailyIngestionReport(
            report_date=date(2026, 2, 24),
            environment=Environment.DEVELOPMENT,
            rss_sources=[
                SourceStats(
                    source_name="test_feed",
                    source_type="rss",
                    documents_processed=10,
                    documents_succeeded=9,
                    documents_added_to_db=8,
                ),
            ],
        )
        qa_report = DailyIngestionReport(
            report_date=date(2026, 2, 24),
            environment=Environment.QA,
            rss_sources=[
                SourceStats(
                    source_name="test_feed",
                    source_type="rss",
                    documents_processed=20,
                    documents_succeeded=18,
                    documents_added_to_db=15,
                ),
            ],
        )

        env_reports = {
            Environment.DEVELOPMENT: dev_report,
            Environment.QA: qa_report,
        }

        html = service._generate_consolidated_ingestion_html(env_reports, date(2026, 2, 24))

        # All three environments should appear
        assert "DEVELOPMENT" in html
        assert "QA" in html
        assert "PRODUCTION" in html

    def test_html_uses_details_tags_for_collapsible_sections(self):
        """Test that HTML uses <details> tags for collapsible sections."""
        from app.services.ingestion_report_service import DailyIngestionReport

        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)

        dev_report = DailyIngestionReport(
            report_date=date(2026, 2, 24),
            environment=Environment.DEVELOPMENT,
        )

        env_reports = {Environment.DEVELOPMENT: dev_report}

        html = service._generate_consolidated_ingestion_html(env_reports, date(2026, 2, 24))

        # Must have <details> and <summary> tags
        assert "<details" in html
        assert "<summary" in html
        # Should NOT have 'open' attribute (collapsed by default)
        assert "<details open" not in html.lower()

    def test_html_production_placeholder_when_not_provisioned(self):
        """Test PRODUCTION section shows placeholder when not provisioned."""
        from app.services.ingestion_report_service import DailyIngestionReport

        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)

        dev_report = DailyIngestionReport(
            report_date=date(2026, 2, 24),
            environment=Environment.DEVELOPMENT,
        )

        env_reports = {Environment.DEVELOPMENT: dev_report}

        html = service._generate_consolidated_ingestion_html(env_reports, date(2026, 2, 24))

        assert "Not yet provisioned" in html

    def test_html_summary_shows_key_metrics(self):
        """Test that <summary> line shows key metrics for quick glance."""
        from app.services.ingestion_report_service import (
            DailyIngestionReport,
            SourceStats,
        )

        configs = [
            EnvironmentReportConfig(
                environment=Environment.QA,
                postgres_url="postgresql+asyncpg://qa:pass@localhost/qa",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)

        qa_report = DailyIngestionReport(
            report_date=date(2026, 2, 24),
            environment=Environment.QA,
            rss_sources=[
                SourceStats(
                    source_name="test",
                    source_type="rss",
                    documents_processed=25,
                    documents_succeeded=23,
                    documents_added_to_db=20,
                ),
            ],
        )

        env_reports = {Environment.QA: qa_report}

        html = service._generate_consolidated_ingestion_html(env_reports, date(2026, 2, 24))

        # Summary should show processed count and success rate
        assert "25 processed" in html
        assert "20 added" in html

    def test_html_subject_line_no_env_prefix(self):
        """Test that consolidated email subject has no env-specific prefix."""
        from app.services.ingestion_report_service import DailyIngestionReport

        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)

        subject = service._get_ingestion_subject(date(2026, 2, 24), has_alerts=False)

        # Should NOT have [DEV] or [QA] prefix
        assert "[DEV]" not in subject
        assert "[QA]" not in subject
        assert "PratikoAI" in subject
        assert "Ingestion Report" in subject

    def test_html_subject_with_alerts(self):
        """Test subject line includes warning emoji when alerts exist."""
        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)

        subject = service._get_ingestion_subject(date(2026, 2, 24), has_alerts=True)

        assert "⚠️" in subject


# =============================================================================
# Cost Report HTML Generation Tests
# =============================================================================


class TestConsolidatedCostReportHTML:
    """Tests for consolidated cost report HTML generation."""

    def test_html_contains_all_environment_sections(self):
        """Test that cost report HTML has sections for DEV, QA, and PROD."""
        from app.services.daily_cost_report_service import (
            DailyCostReport,
            EnvironmentCostBreakdown,
        )

        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
            EnvironmentReportConfig(
                environment=Environment.QA,
                postgres_url="postgresql+asyncpg://qa:pass@localhost/qa",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)

        dev_report = DailyCostReport(
            report_date=date(2026, 2, 24),
            total_cost_eur=5.00,
            llm_cost_eur=4.00,
            third_party_cost_eur=1.00,
            total_requests=250,
            unique_users=10,
        )
        qa_report = DailyCostReport(
            report_date=date(2026, 2, 24),
            total_cost_eur=15.00,
            llm_cost_eur=12.00,
            third_party_cost_eur=3.00,
            total_requests=500,
            unique_users=20,
        )

        env_reports = {
            Environment.DEVELOPMENT: dev_report,
            Environment.QA: qa_report,
        }

        html = service._generate_consolidated_cost_html(env_reports, date(2026, 2, 24))

        assert "DEVELOPMENT" in html
        assert "QA" in html
        assert "PRODUCTION" in html

    def test_cost_html_uses_details_tags(self):
        """Test that cost report HTML uses <details> for collapsible sections."""
        from app.services.daily_cost_report_service import DailyCostReport

        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)

        dev_report = DailyCostReport(
            report_date=date(2026, 2, 24),
            total_cost_eur=5.00,
        )

        env_reports = {Environment.DEVELOPMENT: dev_report}

        html = service._generate_consolidated_cost_html(env_reports, date(2026, 2, 24))

        assert "<details" in html
        assert "<summary" in html
        assert "<details open" not in html.lower()

    def test_cost_summary_shows_total_across_envs(self):
        """Test that cost report shows a grand total across all environments."""
        from app.services.daily_cost_report_service import DailyCostReport

        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
            EnvironmentReportConfig(
                environment=Environment.QA,
                postgres_url="postgresql+asyncpg://qa:pass@localhost/qa",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)

        dev_report = DailyCostReport(
            report_date=date(2026, 2, 24),
            total_cost_eur=5.50,
            total_requests=100,
            unique_users=5,
        )
        qa_report = DailyCostReport(
            report_date=date(2026, 2, 24),
            total_cost_eur=10.50,
            total_requests=200,
            unique_users=15,
        )

        env_reports = {
            Environment.DEVELOPMENT: dev_report,
            Environment.QA: qa_report,
        }

        html = service._generate_consolidated_cost_html(env_reports, date(2026, 2, 24))

        # Grand total should be €16.00
        assert "16.00" in html

    def test_cost_subject_line(self):
        """Test cost report subject line."""
        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)

        subject = service._get_cost_subject(date(2026, 2, 24), total_cost=16.00, has_alerts=False)

        assert "[DEV]" not in subject
        assert "Cost Report" in subject
        assert "16.00" in subject


# =============================================================================
# Email Sending Tests
# =============================================================================


class TestConsolidatedEmailSending:
    """Tests for consolidated email sending."""

    def test_send_email_no_recipients(self):
        """Test email send returns False with no recipients."""
        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)

        result = service._send_email([], "Test Subject", "<p>Test</p>")

        assert result is False

    def test_send_email_no_smtp_credentials(self):
        """Test email send returns False without SMTP credentials."""
        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)
        service.smtp_username = ""
        service.smtp_password = ""

        result = service._send_email(["test@example.com"], "Test Subject", "<p>Test</p>")

        assert result is False

    @patch("smtplib.SMTP")
    def test_send_email_success(self, mock_smtp):
        """Test successful email sending."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=None)

        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)
        service.smtp_username = "test@example.com"
        service.smtp_password = "test-password"  # pragma: allowlist secret

        result = service._send_email(
            ["recipient@example.com"],
            "Test Subject",
            "<p>Test Body</p>",
        )

        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()


# =============================================================================
# Async Integration Tests
# =============================================================================


@pytest.mark.asyncio
class TestConsolidatedReportServiceAsync:
    """Async tests for consolidated report service."""

    async def test_generate_ingestion_report_for_env(self):
        """Test generating ingestion report for a single environment."""
        from app.services.ingestion_report_service import DailyIngestionReport

        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)

        # Mock the DB session and IngestionReportService
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar.return_value = 0
        mock_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        report = await service._generate_ingestion_report_for_session(mock_session, Environment.DEVELOPMENT)

        assert isinstance(report, DailyIngestionReport)
        assert report.report_date is not None

    async def test_generate_cost_report_for_env(self):
        """Test generating cost report for a single environment."""
        from app.services.daily_cost_report_service import DailyCostReport

        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)

        # Mock the DB session
        mock_session = MagicMock()
        mock_totals = MagicMock()
        mock_totals.first.return_value = (5.00, 4.00, 1.00, 100, 50000, 5)
        mock_env = MagicMock()
        mock_env.all.return_value = []
        mock_users = MagicMock()
        mock_users.all.return_value = []
        mock_tp = MagicMock()
        mock_tp.all.return_value = []

        mock_session.execute = AsyncMock(side_effect=[mock_totals, mock_env, mock_users, mock_tp])

        report = await service._generate_cost_report_for_session(mock_session)

        assert isinstance(report, DailyCostReport)
        assert report.total_cost_eur == 5.00


# =============================================================================
# Scheduler Integration Tests
# =============================================================================


class TestConsolidatedSchedulerIntegration:
    """Tests for scheduler task integration."""

    def test_consolidated_ingestion_task_importable(self):
        """Test that consolidated task function is importable."""
        from app.services.scheduler_service import send_consolidated_ingestion_report_task

        assert callable(send_consolidated_ingestion_report_task)

    def test_consolidated_cost_task_importable(self):
        """Test that consolidated cost task function is importable."""
        from app.services.scheduler_service import send_consolidated_cost_report_task

        assert callable(send_consolidated_cost_report_task)

    def test_setup_registers_consolidated_tasks(self):
        """Test that setup_default_tasks registers consolidated tasks when enabled."""
        from app.services.scheduler_service import scheduler_service, setup_default_tasks

        # Clear existing tasks
        scheduler_service.tasks = {}

        with patch("app.services.scheduler_service.settings") as mock_settings:
            mock_settings.CONSOLIDATED_REPORT_ENABLED = True
            mock_settings.CONSOLIDATED_REPORT_DEV_DB_URL = "postgresql://dev/db"
            mock_settings.CONSOLIDATED_REPORT_QA_DB_URL = "postgresql://qa/db"
            mock_settings.CONSOLIDATED_REPORT_PROD_DB_URL = ""
            mock_settings.INGESTION_REPORT_ENABLED = True
            mock_settings.INGESTION_REPORT_TIME = "06:00"
            mock_settings.INGESTION_REPORT_RECIPIENTS = "test@test.com"
            mock_settings.DAILY_COST_REPORT_ENABLED = True
            mock_settings.DAILY_COST_REPORT_TIME = "07:00"
            mock_settings.DAILY_COST_REPORT_RECIPIENTS = "test@test.com"
            mock_settings.RSS_COLLECTION_TIME = "01:00"
            mock_settings.EVAL_REPORT_ENABLED = False
            mock_settings.EVAL_REPORT_TIME = "06:00"
            mock_settings.EMBEDDING_BACKFILL_ENABLED = False
            mock_settings.EMBEDDING_BACKFILL_TIME = "03:00"
            mock_settings.METRICS_REPORT_ENABLED = True
            mock_settings.METRICS_REPORT_TIME = "06:00"
            mock_settings.METRICS_REPORT_RECIPIENTS = "admin@test.com"

            setup_default_tasks()

        assert "consolidated_ingestion_report" in scheduler_service.tasks
        assert "consolidated_cost_report" in scheduler_service.tasks


# =============================================================================
# Ingestion Report - Branch Coverage Tests (alerts, errors, etc.)
# =============================================================================


class TestIngestionEnvSectionBranches:
    """Tests covering branches in _build_ingestion_env_section."""

    def _make_service(self):
        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
        ]
        return ConsolidatedReportService(env_configs=configs)

    def test_high_severity_alerts_badge(self):
        """Test that HIGH severity alerts produce a red badge."""
        from app.services.ingestion_report_service import (
            AlertSeverity,
            AlertType,
            DailyIngestionReport,
            IngestionAlert,
            SourceStats,
        )

        service = self._make_service()

        report = DailyIngestionReport(
            report_date=date(2026, 2, 24),
            environment=Environment.DEVELOPMENT,
            rss_sources=[
                SourceStats(
                    source_name="feed1",
                    source_type="rss",
                    documents_processed=10,
                    documents_succeeded=9,
                    documents_added_to_db=8,
                ),
            ],
            alerts=[
                IngestionAlert(
                    alert_type=AlertType.FEED_DOWN,
                    severity=AlertSeverity.HIGH,
                    message="Feed is down",
                    source_name="feed1",
                ),
            ],
        )

        env_reports = {Environment.DEVELOPMENT: report}
        html = service._generate_consolidated_ingestion_html(env_reports, date(2026, 2, 24))

        assert "#dc3545" in html  # Red badge for HIGH severity
        assert "1 alert" in html

    def test_medium_severity_alerts_badge(self):
        """Test that non-HIGH severity alerts produce a yellow badge."""
        from app.services.ingestion_report_service import (
            AlertSeverity,
            AlertType,
            DailyIngestionReport,
            IngestionAlert,
            SourceStats,
        )

        service = self._make_service()

        report = DailyIngestionReport(
            report_date=date(2026, 2, 24),
            environment=Environment.DEVELOPMENT,
            rss_sources=[
                SourceStats(
                    source_name="feed1",
                    source_type="rss",
                    documents_processed=10,
                    documents_succeeded=5,
                    documents_added_to_db=4,
                ),
            ],
            alerts=[
                IngestionAlert(
                    alert_type=AlertType.HIGH_ERROR_RATE,
                    severity=AlertSeverity.MEDIUM,
                    message="Error rate above threshold",
                    source_name="feed1",
                ),
                IngestionAlert(
                    alert_type=AlertType.FEED_STALE,
                    severity=AlertSeverity.LOW,
                    message="Feed is stale",
                    source_name="feed1",
                ),
            ],
        )

        env_reports = {Environment.DEVELOPMENT: report}
        html = service._generate_consolidated_ingestion_html(env_reports, date(2026, 2, 24))

        assert "#ffc107" in html  # Yellow badge for non-HIGH
        assert "2 alerts" in html  # Plural
        assert "Alerts (2)" in html

    def test_error_samples_section(self):
        """Test that error_samples produce an error details section."""
        from app.services.ingestion_report_service import (
            DailyIngestionReport,
            ErrorSample,
            SourceStats,
        )

        service = self._make_service()

        report = DailyIngestionReport(
            report_date=date(2026, 2, 24),
            environment=Environment.DEVELOPMENT,
            rss_sources=[
                SourceStats(
                    source_name="feed1",
                    source_type="rss",
                    documents_processed=10,
                    documents_succeeded=7,
                    documents_added_to_db=6,
                ),
            ],
            error_samples=[
                ErrorSample(
                    source_name="feed1",
                    error_count=3,
                    sample_messages=["Timeout connecting to server", "Invalid XML"],
                ),
            ],
        )

        env_reports = {Environment.DEVELOPMENT: report}
        html = service._generate_consolidated_ingestion_html(env_reports, date(2026, 2, 24))

        assert "Error Details" in html
        assert "feed1" in html
        assert "Timeout connecting to server" in html

    def test_filtered_content_section(self):
        """Test that filtered_content_samples produce a filtered section."""
        from app.services.ingestion_report_service import (
            DailyIngestionReport,
            FilteredContentSample,
            SourceStats,
        )

        service = self._make_service()

        report = DailyIngestionReport(
            report_date=date(2026, 2, 24),
            environment=Environment.DEVELOPMENT,
            rss_sources=[
                SourceStats(
                    source_name="feed1",
                    source_type="rss",
                    documents_processed=10,
                    documents_succeeded=8,
                    documents_added_to_db=5,
                ),
            ],
            filtered_content_samples=[
                FilteredContentSample(
                    source_name="feed1",
                    items_filtered=5,
                    sample_titles=["Concorso pubblico 2026", "Nomina dirigente"],
                ),
                FilteredContentSample(
                    source_name="feed2",
                    items_filtered=2,
                    sample_titles=[],
                ),
            ],
        )

        env_reports = {Environment.DEVELOPMENT: report}
        html = service._generate_consolidated_ingestion_html(env_reports, date(2026, 2, 24))

        assert "Filtered Content (7 items)" in html
        assert "Concorso pubblico 2026" in html
        assert "No samples" in html  # For feed2 with empty titles

    def test_new_document_previews_section(self):
        """Test that new_document_previews produce a documents section."""
        from app.services.ingestion_report_service import (
            DailyIngestionReport,
            DocumentPreview,
            SourceStats,
        )

        service = self._make_service()

        report = DailyIngestionReport(
            report_date=date(2026, 2, 24),
            environment=Environment.DEVELOPMENT,
            rss_sources=[
                SourceStats(
                    source_name="feed1",
                    source_type="rss",
                    documents_processed=5,
                    documents_succeeded=5,
                    documents_added_to_db=5,
                ),
            ],
            new_document_previews=[
                DocumentPreview(
                    source="feed1",
                    title="New regulation on workplace safety",
                    created_at=datetime(2026, 2, 24, 10, 0, tzinfo=UTC),
                ),
            ],
        )

        env_reports = {Environment.DEVELOPMENT: report}
        html = service._generate_consolidated_ingestion_html(env_reports, date(2026, 2, 24))

        assert "New Documents" in html
        assert "New regulation on workplace safety" in html

    def test_data_quality_section(self):
        """Test that data_quality produces a data quality section."""
        from app.services.data_quality_audit_service import DataQualitySummary
        from app.services.ingestion_report_service import DailyIngestionReport, SourceStats

        service = self._make_service()

        dq = DataQualitySummary(
            total_items=100,
            total_chunks=500,
            url_duplicate_groups=3,
            navigation_contaminated_chunks=15,
            items_missing_embedding=2,
            chunks_missing_embedding=5,
        )

        report = DailyIngestionReport(
            report_date=date(2026, 2, 24),
            environment=Environment.DEVELOPMENT,
            rss_sources=[
                SourceStats(
                    source_name="feed1",
                    source_type="rss",
                    documents_processed=10,
                    documents_succeeded=10,
                    documents_added_to_db=10,
                ),
            ],
            data_quality=dq,
        )

        env_reports = {Environment.DEVELOPMENT: report}
        html = service._generate_consolidated_ingestion_html(env_reports, date(2026, 2, 24))

        assert "Data Quality" in html
        assert "100" in html  # total_items
        assert "500" in html  # total_chunks
        assert "URL Duplicate Groups" in html

    def test_data_quality_status_ok(self):
        """Test _build_data_quality_html with zero-value metrics shows OK."""
        from app.services.data_quality_audit_service import DataQualitySummary

        service = self._make_service()

        dq = DataQualitySummary(
            total_items=50,
            total_chunks=200,
            url_duplicate_groups=0,
            navigation_contaminated_chunks=0,
            items_missing_embedding=0,
            chunks_missing_embedding=0,
        )

        html = service._build_data_quality_html(dq)

        assert "OK" in html
        assert "#28a745" in html  # Green for OK

    def test_wow_indicators_displayed(self):
        """Test that WoW comparison indicators are shown."""
        from app.services.ingestion_report_service import (
            DailyIngestionReport,
            SourceStats,
            WoWComparison,
        )

        service = self._make_service()

        report = DailyIngestionReport(
            report_date=date(2026, 2, 24),
            environment=Environment.DEVELOPMENT,
            rss_sources=[
                SourceStats(
                    source_name="feed1",
                    source_type="rss",
                    documents_processed=20,
                    documents_succeeded=18,
                    documents_added_to_db=15,
                ),
            ],
            wow_documents_processed=WoWComparison(current_value=20, previous_value=10),
            wow_documents_added=WoWComparison(current_value=15, previous_value=12),
            wow_success_rate=WoWComparison(current_value=90.0, previous_value=85.0),
            wow_junk_rate=WoWComparison(current_value=5.0, previous_value=10.0),
        )

        env_reports = {Environment.DEVELOPMENT: report}
        html = service._generate_consolidated_ingestion_html(env_reports, date(2026, 2, 24))

        # WoW indicators should appear
        assert "+100.0%" in html  # 20 vs 10 = +100%

    def test_scraper_sources_displayed(self):
        """Test that scraper sources appear in the report."""
        from app.services.ingestion_report_service import DailyIngestionReport, SourceStats

        service = self._make_service()

        report = DailyIngestionReport(
            report_date=date(2026, 2, 24),
            environment=Environment.DEVELOPMENT,
            scraper_sources=[
                SourceStats(
                    source_name="gazzetta_scraper",
                    source_type="scraper",
                    documents_processed=15,
                    documents_succeeded=12,
                    documents_failed=3,
                    documents_added_to_db=10,
                ),
            ],
        )

        env_reports = {Environment.DEVELOPMENT: report}
        html = service._generate_consolidated_ingestion_html(env_reports, date(2026, 2, 24))

        assert "gazzetta_scraper" in html
        assert "Web Scrapers (1 sources)" in html

    def test_low_success_rate_color(self):
        """Test that low success rate (<70%) gets red color."""
        from app.services.ingestion_report_service import DailyIngestionReport, SourceStats

        service = self._make_service()

        report = DailyIngestionReport(
            report_date=date(2026, 2, 24),
            environment=Environment.DEVELOPMENT,
            rss_sources=[
                SourceStats(
                    source_name="bad_feed",
                    source_type="rss",
                    documents_processed=100,
                    documents_succeeded=50,
                    documents_failed=50,
                    documents_added_to_db=30,
                ),
            ],
        )

        env_reports = {Environment.DEVELOPMENT: report}
        html = service._generate_consolidated_ingestion_html(env_reports, date(2026, 2, 24))

        # 50% success rate should be red
        assert "#dc3545" in html


# =============================================================================
# Cost Report - Branch Coverage Tests
# =============================================================================


class TestCostEnvSectionBranches:
    """Tests covering branches in _build_cost_env_section."""

    def _make_service(self):
        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
        ]
        return ConsolidatedReportService(env_configs=configs)

    def test_cost_report_with_user_breakdown(self):
        """Test cost report with actual user breakdown data."""
        from app.services.daily_cost_report_service import DailyCostReport, UserCostBreakdown

        service = self._make_service()

        report = DailyCostReport(
            report_date=date(2026, 2, 24),
            total_cost_eur=20.00,
            llm_cost_eur=15.00,
            third_party_cost_eur=5.00,
            total_requests=500,
            total_tokens=100000,
            unique_users=3,
            user_breakdown=[
                UserCostBreakdown(
                    user_id="user-1",
                    total_cost_eur=12.00,
                    request_count=300,
                    total_tokens=60000,
                ),
                UserCostBreakdown(
                    user_id="user-2",
                    total_cost_eur=8.00,
                    request_count=200,
                    total_tokens=40000,
                ),
            ],
        )

        env_reports = {Environment.DEVELOPMENT: report}
        html = service._generate_consolidated_cost_html(env_reports, date(2026, 2, 24))

        assert "user-1" in html
        assert "user-2" in html
        assert "Top Users by Cost" in html

    def test_cost_report_with_third_party_breakdown(self):
        """Test cost report with third-party API breakdown."""
        from app.services.daily_cost_report_service import (
            DailyCostReport,
            ThirdPartyCostBreakdown,
        )

        service = self._make_service()

        report = DailyCostReport(
            report_date=date(2026, 2, 24),
            total_cost_eur=10.00,
            llm_cost_eur=8.00,
            third_party_cost_eur=2.00,
            total_requests=100,
            total_tokens=50000,
            unique_users=5,
            third_party_breakdown=[
                ThirdPartyCostBreakdown(
                    api_type="Tavily Search",
                    total_cost_eur=1.50,
                    request_count=30,
                ),
                ThirdPartyCostBreakdown(
                    api_type="Jina Reader",
                    total_cost_eur=0.50,
                    request_count=20,
                ),
            ],
        )

        env_reports = {Environment.DEVELOPMENT: report}
        html = service._generate_consolidated_cost_html(env_reports, date(2026, 2, 24))

        assert "Tavily Search" in html
        assert "Jina Reader" in html
        assert "Third-Party APIs" in html

    def test_cost_report_with_alerts(self):
        """Test cost report with cost alerts."""
        from app.services.daily_cost_report_service import CostAlert, DailyCostReport

        service = self._make_service()

        report = DailyCostReport(
            report_date=date(2026, 2, 24),
            total_cost_eur=60.00,
            llm_cost_eur=50.00,
            third_party_cost_eur=10.00,
            total_requests=1000,
            total_tokens=500000,
            unique_users=10,
            alerts=[
                CostAlert(
                    alert_type="DAILY_THRESHOLD_EXCEEDED",
                    severity="HIGH",
                    message="Daily cost €60.00 exceeds threshold €50.00",
                    current_cost=60.00,
                    threshold=50.00,
                ),
                CostAlert(
                    alert_type="USER_THRESHOLD_EXCEEDED",
                    severity="MEDIUM",
                    message="User user-1 cost €5.00 exceeds €2.00/day",
                    current_cost=5.00,
                    threshold=2.00,
                    user_id="user-1",
                ),
            ],
        )

        env_reports = {Environment.DEVELOPMENT: report}
        html = service._generate_consolidated_cost_html(env_reports, date(2026, 2, 24))

        assert "Cost Alerts" in html
        assert "Daily cost" in html
        assert "#dc3545" in html  # HIGH severity color
        assert "#ffc107" in html  # MEDIUM severity color

    def test_cost_subject_with_alerts(self):
        """Test cost report subject with alerts emoji."""
        service = self._make_service()

        subject = service._get_cost_subject(date(2026, 2, 24), total_cost=60.00, has_alerts=True)

        assert "⚠️" in subject
        assert "60.00" in subject


# =============================================================================
# Async Send Methods - Full Flow Tests
# =============================================================================


@pytest.mark.asyncio
class TestConsolidatedSendFlows:
    """Tests for the full async send_consolidated_*_report flows."""

    async def test_send_ingestion_report_no_recipients(self):
        """Test send returns False with empty recipients."""
        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)
        result = await service.send_consolidated_ingestion_report([])

        assert result is False

    async def test_send_cost_report_no_recipients(self):
        """Test cost report send returns False with empty recipients."""
        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)
        result = await service.send_consolidated_cost_report([])

        assert result is False

    async def test_send_ingestion_report_env_failure_handled(self):
        """Test that env DB connection failure is caught and logged."""
        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)
        service.smtp_username = ""
        service.smtp_password = ""

        # Mock _create_session to raise
        with patch.object(service, "_create_session", side_effect=Exception("Connection refused")):
            result = await service.send_consolidated_ingestion_report(["test@example.com"])

        # Should still return False (no SMTP) but not crash
        assert result is False

    async def test_send_cost_report_env_failure_handled(self):
        """Test that cost report env failure is caught and logged."""
        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)
        service.smtp_username = ""
        service.smtp_password = ""

        with patch.object(service, "_create_session", side_effect=Exception("Connection refused")):
            result = await service.send_consolidated_cost_report(["test@example.com"])

        assert result is False

    async def test_send_ingestion_report_full_success(self):
        """Test full ingestion report send flow with mocked session and SMTP."""
        from app.services.ingestion_report_service import DailyIngestionReport

        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)
        service.smtp_username = "test@example.com"
        service.smtp_password = "test-pass"  # pragma: allowlist secret

        mock_report = DailyIngestionReport(
            report_date=date(2026, 2, 24),
            environment=Environment.DEVELOPMENT,
        )

        # Mock session context manager
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch.object(service, "_create_session", return_value=mock_session),
            patch.object(service, "_generate_ingestion_report_for_session", return_value=mock_report),
            patch.object(service, "_send_email", return_value=True) as mock_send,
        ):
            result = await service.send_consolidated_ingestion_report(["admin@example.com"])

        assert result is True
        mock_send.assert_called_once()

    async def test_send_cost_report_full_success(self):
        """Test full cost report send flow with mocked session and SMTP."""
        from app.services.daily_cost_report_service import DailyCostReport

        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)
        service.smtp_username = "test@example.com"
        service.smtp_password = "test-pass"  # pragma: allowlist secret

        mock_report = DailyCostReport(
            report_date=date(2026, 2, 24),
            total_cost_eur=5.00,
        )

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch.object(service, "_create_session", return_value=mock_session),
            patch.object(service, "_generate_cost_report_for_session", return_value=mock_report),
            patch.object(service, "_send_email", return_value=True) as mock_send,
        ):
            result = await service.send_consolidated_cost_report(["admin@example.com"])

        assert result is True
        mock_send.assert_called_once()

    async def test_create_session_returns_session(self):
        """Test _create_session creates an async session."""
        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)

        mock_session = MagicMock()
        mock_engine_instance = MagicMock()

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine_instance) as mock_engine,
            patch("sqlalchemy.orm.sessionmaker", return_value=MagicMock(return_value=mock_session)),
        ):
            session = await service._create_session(configs[0])

            assert session is mock_session
            mock_engine.assert_called_once()


# =============================================================================
# Email Send Error Handling
# =============================================================================


class TestEmailSendErrorHandling:
    """Tests for email send error handling."""

    @patch("smtplib.SMTP")
    def test_send_email_smtp_error(self, mock_smtp):
        """Test that SMTP errors are caught and logged."""
        mock_smtp.return_value.__enter__ = MagicMock(side_effect=Exception("SMTP connection failed"))
        mock_smtp.return_value.__exit__ = MagicMock(return_value=None)

        configs = [
            EnvironmentReportConfig(
                environment=Environment.DEVELOPMENT,
                postgres_url="postgresql+asyncpg://dev:pass@localhost/dev",
            ),
        ]

        service = ConsolidatedReportService(env_configs=configs)
        service.smtp_username = "test@example.com"
        service.smtp_password = "test-pass"  # pragma: allowlist secret

        result = service._send_email(
            ["recipient@example.com"],
            "Test Subject",
            "<p>Test</p>",
        )

        assert result is False
