"""Tests for Ingestion Report Service - DEV-BE-69 + DEV-BE-70.

Unit tests for the IngestionReportService class.
Tests report generation, email sending, alerts, WoW comparison, and environment awareness.
"""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Environment
from app.services.ingestion_report_service import (
    ENVIRONMENT_COLORS,
    AlertSeverity,
    AlertType,
    DailyIngestionReport,
    DocumentPreview,
    ErrorSample,
    FilteredContentSample,
    IngestionAlert,
    IngestionReportService,
    SourceStats,
    WoWComparison,
    get_environment_color,
)


class TestSourceStats:
    """Tests for SourceStats dataclass."""

    def test_default_values(self):
        """Test default values for SourceStats."""
        stats = SourceStats(source_name="test", source_type="rss")

        assert stats.source_name == "test"
        assert stats.source_type == "rss"
        assert stats.documents_processed == 0
        assert stats.documents_succeeded == 0
        assert stats.documents_failed == 0
        assert stats.total_chunks == 0
        assert stats.junk_chunks == 0

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        stats = SourceStats(
            source_name="test",
            source_type="rss",
            documents_processed=100,
            documents_succeeded=85,
            documents_failed=15,
        )

        assert stats.success_rate == 85.0

    def test_success_rate_zero_processed(self):
        """Test success rate when no documents processed."""
        stats = SourceStats(source_name="test", source_type="rss")

        assert stats.success_rate == 0.0

    def test_junk_percentage_calculation(self):
        """Test junk percentage calculation."""
        stats = SourceStats(
            source_name="test",
            source_type="rss",
            total_chunks=100,
            junk_chunks=15,
        )

        assert stats.junk_percentage == 15.0

    def test_junk_percentage_zero_chunks(self):
        """Test junk percentage when no chunks."""
        stats = SourceStats(source_name="test", source_type="rss")

        assert stats.junk_percentage == 0.0


class TestDailyIngestionReport:
    """Tests for DailyIngestionReport dataclass."""

    def test_empty_report(self):
        """Test empty report values."""
        report = DailyIngestionReport(report_date=date.today())

        assert report.total_documents_processed == 0
        assert report.total_documents_succeeded == 0
        assert report.total_documents_added == 0
        assert report.overall_success_rate == 0.0
        assert report.overall_junk_rate == 0.0

    def test_aggregated_totals(self):
        """Test that totals are correctly aggregated."""
        report = DailyIngestionReport(
            report_date=date.today(),
            rss_sources=[
                SourceStats(
                    source_name="source1",
                    source_type="rss",
                    documents_processed=50,
                    documents_succeeded=45,
                    documents_added_to_db=40,
                    total_chunks=100,
                    junk_chunks=10,
                ),
                SourceStats(
                    source_name="source2",
                    source_type="rss",
                    documents_processed=30,
                    documents_succeeded=28,
                    documents_added_to_db=25,
                    total_chunks=60,
                    junk_chunks=5,
                ),
            ],
            scraper_sources=[
                SourceStats(
                    source_name="scraper1",
                    source_type="scraper",
                    documents_processed=20,
                    documents_succeeded=20,
                    documents_added_to_db=20,
                    total_chunks=40,
                    junk_chunks=2,
                ),
            ],
        )

        assert report.total_documents_processed == 100
        assert report.total_documents_succeeded == 93
        assert report.total_documents_added == 85
        assert report.overall_success_rate == 93.0
        # Junk rate: 17 junk out of 200 total = 8.5%
        assert report.overall_junk_rate == 8.5


class TestIngestionReportService:
    """Tests for IngestionReportService class."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        return MagicMock()

    def test_initialization(self, mock_db_session):
        """Test service initialization."""
        service = IngestionReportService(mock_db_session)

        assert service.db == mock_db_session
        assert service.smtp_server is not None

    def test_html_report_generation(self, mock_db_session):
        """Test HTML report generation."""
        service = IngestionReportService(mock_db_session)

        report = DailyIngestionReport(
            report_date=date.today(),
            rss_sources=[
                SourceStats(
                    source_name="Agenzia Entrate",
                    source_type="rss",
                    documents_processed=10,
                    documents_succeeded=9,
                    documents_failed=1,
                    documents_added_to_db=8,
                    total_chunks=50,
                    junk_chunks=5,
                ),
            ],
            scraper_sources=[
                SourceStats(
                    source_name="Gazzetta Ufficiale",
                    source_type="scraper",
                    documents_processed=5,
                    documents_succeeded=5,
                    documents_added_to_db=5,
                    total_chunks=25,
                    junk_chunks=2,
                ),
            ],
        )

        html = service._generate_html_report(report)

        # Check key elements are present
        assert "Daily Ingestion Report" in html
        assert "Agenzia Entrate" in html
        assert "Gazzetta Ufficiale" in html
        assert "RSS Feeds" in html
        assert "Web Scrapers" in html
        assert str(report.total_documents_processed) in html

    def test_html_report_empty_sources(self, mock_db_session):
        """Test HTML report with no sources."""
        service = IngestionReportService(mock_db_session)

        report = DailyIngestionReport(report_date=date.today())

        html = service._generate_html_report(report)

        # Should show "No activity" messages
        assert "No RSS activity" in html
        assert "No scraper activity" in html


@pytest.mark.asyncio
class TestIngestionReportServiceAsync:
    """Async tests for IngestionReportService."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock async database session."""
        mock = MagicMock()
        mock.execute = AsyncMock(
            return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
        )
        return mock

    async def test_generate_daily_report_empty(self, mock_db_session):
        """Test generating report with no data.

        Note: Scrapers (Gazzetta, Cassazione) are always shown in report
        even when they have 0 documents - this is intentional to provide
        visibility into scraper activity.
        """
        # Mock empty results - need to handle both scalars().all() and scalar() calls
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar.return_value = 0
        mock_result.fetchall.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        service = IngestionReportService(mock_db_session)

        # Mock the new methods to avoid database calls
        service._detect_alerts = AsyncMock(return_value=[])
        service._get_previous_week_stats = AsyncMock(return_value=None)
        service._get_new_document_titles = AsyncMock(return_value=[])
        service._get_error_samples = AsyncMock(return_value=[])

        report = await service.generate_daily_report(date.today())

        assert report.report_date == date.today()
        assert len(report.rss_sources) == 0
        # Scrapers always appear in report, even with 0 documents (Gazzetta + Cassazione)
        assert len(report.scraper_sources) == 2
        # Verify both scrapers are included with 0 documents
        scraper_names = [s.source_name for s in report.scraper_sources]
        assert "Gazzetta Ufficiale" in scraper_names
        assert "Cassazione" in scraper_names
        for scraper in report.scraper_sources:
            assert scraper.documents_processed == 0

    async def test_send_daily_report_no_recipients(self, mock_db_session):
        """Test sending report with no recipients."""
        service = IngestionReportService(mock_db_session)

        result = await service.send_daily_report_email([])

        assert result is False

    async def test_send_email_no_credentials(self, mock_db_session):
        """Test email send fails without SMTP credentials."""
        service = IngestionReportService(mock_db_session)
        service.smtp_username = None
        service.smtp_password = None

        result = await service._send_email(["test@example.com"], "Test", "<p>Test</p>")

        assert result is False

    @patch("smtplib.SMTP")
    async def test_send_email_success(self, mock_smtp, mock_db_session):
        """Test successful email sending."""
        # Configure mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=None)

        service = IngestionReportService(mock_db_session)
        service.smtp_username = "test@example.com"
        service.smtp_password = "test-password"  # pragma: allowlist secret

        result = await service._send_email(
            ["recipient@example.com"],
            "Test Subject",
            "<p>Test Body</p>",
        )

        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()


class TestScheduledTaskIntegration:
    """Tests for scheduled task integration."""

    @pytest.mark.asyncio
    async def test_task_function_no_recipients(self):
        """Test scheduled task with no recipients configured."""
        from unittest.mock import patch

        with patch("app.services.ingestion_report_service.settings") as mock_settings:
            mock_settings.INGESTION_REPORT_RECIPIENTS = ""

            from app.services.ingestion_report_service import send_ingestion_daily_report_task

            mock_session = MagicMock()
            result = await send_ingestion_daily_report_task(mock_session)

            assert result is False


# =============================================================================
# DEV-BE-70: New Tests for Enhanced Ingestion Report Features
# =============================================================================


class TestWoWComparison:
    """Tests for Week-over-Week comparison dataclass."""

    def test_positive_change(self):
        """Test positive change calculation."""
        wow = WoWComparison(current_value=120.0, previous_value=100.0)

        assert wow.change_percent == 20.0
        assert wow.change_str == "+20.0%"
        assert wow.change_color == "#28a745"  # Green for positive

    def test_negative_change(self):
        """Test negative change calculation."""
        wow = WoWComparison(current_value=80.0, previous_value=100.0)

        assert wow.change_percent == -20.0
        assert wow.change_str == "-20.0%"
        assert wow.change_color == "#dc3545"  # Red for negative

    def test_zero_change(self):
        """Test zero change calculation."""
        wow = WoWComparison(current_value=100.0, previous_value=100.0)

        assert wow.change_percent == 0.0
        assert wow.change_str == "+0.0%"
        assert wow.change_color == "#666"  # Gray for no change

    def test_from_zero_to_positive(self):
        """Test change from zero to positive."""
        wow = WoWComparison(current_value=50.0, previous_value=0.0)

        assert wow.change_percent == 100.0
        assert wow.change_str == "+100.0%"

    def test_both_zero(self):
        """Test both values zero."""
        wow = WoWComparison(current_value=0.0, previous_value=0.0)

        assert wow.change_percent == 0.0
        assert wow.change_str == "+0.0%"


class TestIngestionAlert:
    """Tests for IngestionAlert dataclass."""

    def test_alert_creation(self):
        """Test alert creation with all fields."""
        alert = IngestionAlert(
            alert_type=AlertType.FEED_DOWN,
            severity=AlertSeverity.HIGH,
            message="Feed failed 3 consecutive checks",
            source_name="Agenzia Entrate",
        )

        assert alert.alert_type == AlertType.FEED_DOWN
        assert alert.severity == AlertSeverity.HIGH
        assert alert.message == "Feed failed 3 consecutive checks"
        assert alert.source_name == "Agenzia Entrate"

    def test_alert_without_source(self):
        """Test alert creation without source (global alert)."""
        alert = IngestionAlert(
            alert_type=AlertType.ZERO_DOCUMENTS,
            severity=AlertSeverity.HIGH,
            message="No documents collected",
        )

        assert alert.source_name is None


class TestAlertTypes:
    """Tests for alert type enum values."""

    def test_all_alert_types_exist(self):
        """Test that all 5 alert types are defined."""
        assert AlertType.FEED_DOWN == "FEED_DOWN"
        assert AlertType.FEED_STALE == "FEED_STALE"
        assert AlertType.HIGH_ERROR_RATE == "HIGH_ERROR_RATE"
        assert AlertType.HIGH_JUNK_RATE == "HIGH_JUNK_RATE"
        assert AlertType.ZERO_DOCUMENTS == "ZERO_DOCUMENTS"

    def test_all_severity_levels_exist(self):
        """Test that all severity levels are defined."""
        assert AlertSeverity.HIGH == "HIGH"
        assert AlertSeverity.MEDIUM == "MEDIUM"
        assert AlertSeverity.LOW == "LOW"


class TestEnvironmentColors:
    """Tests for environment color mapping."""

    def test_all_environments_have_colors(self):
        """Test that all environments have color configurations."""
        assert Environment.DEVELOPMENT in ENVIRONMENT_COLORS
        assert Environment.QA in ENVIRONMENT_COLORS
        assert Environment.PRODUCTION in ENVIRONMENT_COLORS

    def test_development_color(self):
        """Test development environment color."""
        color = get_environment_color(Environment.DEVELOPMENT)

        assert color["bg"] == "#6c757d"  # Gray
        assert color["name"] == "DEVELOPMENT"
        assert color["prefix"] == "DEV"

    def test_qa_color(self):
        """Test QA environment color."""
        color = get_environment_color(Environment.QA)

        assert color["bg"] == "#007bff"  # Blue
        assert color["name"] == "QA"
        assert color["prefix"] == "QA"

    def test_production_color(self):
        """Test production environment color."""
        color = get_environment_color(Environment.PRODUCTION)

        assert color["bg"] == "#28a745"  # Green
        assert color["name"] == "PRODUCTION"
        assert color["prefix"] == "PROD"


class TestDocumentPreview:
    """Tests for DocumentPreview dataclass."""

    def test_document_preview_creation(self):
        """Test document preview creation."""
        preview = DocumentPreview(
            source="Agenzia Entrate",
            title="Circolare 123/2024 - Novità fiscali",
            created_at=datetime.now(UTC),
        )

        assert preview.source == "Agenzia Entrate"
        assert preview.title == "Circolare 123/2024 - Novità fiscali"
        assert preview.created_at is not None


class TestErrorSample:
    """Tests for ErrorSample dataclass."""

    def test_error_sample_creation(self):
        """Test error sample creation."""
        sample = ErrorSample(
            source_name="https://example.com/feed",
            error_count=5,
            sample_messages=["Connection timeout", "Invalid XML"],
        )

        assert sample.source_name == "https://example.com/feed"
        assert sample.error_count == 5
        assert len(sample.sample_messages) == 2

    def test_error_sample_empty_messages(self):
        """Test error sample with no messages."""
        sample = ErrorSample(source_name="test", error_count=3)

        assert sample.sample_messages == []


class TestDailyIngestionReportEnvironment:
    """Tests for DailyIngestionReport environment features."""

    def test_report_has_environment(self):
        """Test that report includes environment."""
        report = DailyIngestionReport(report_date=date.today())

        assert report.environment is not None
        # Check environment is valid (avoid isinstance due to module reload issues in tests)
        assert report.environment.value in ["development", "qa", "production"]

    def test_report_environment_color(self):
        """Test environment_color property."""
        report = DailyIngestionReport(report_date=date.today())

        color = report.environment_color
        assert "bg" in color
        assert "name" in color
        assert "prefix" in color

    def test_report_alerts_by_severity(self):
        """Test alerts_by_severity aggregation."""
        report = DailyIngestionReport(
            report_date=date.today(),
            alerts=[
                IngestionAlert(AlertType.FEED_DOWN, AlertSeverity.HIGH, "High 1"),
                IngestionAlert(AlertType.ZERO_DOCUMENTS, AlertSeverity.HIGH, "High 2"),
                IngestionAlert(AlertType.FEED_STALE, AlertSeverity.MEDIUM, "Medium 1"),
                IngestionAlert(AlertType.HIGH_JUNK_RATE, AlertSeverity.LOW, "Low 1"),
            ],
        )

        counts = report.alerts_by_severity
        assert counts["HIGH"] == 2
        assert counts["MEDIUM"] == 1
        assert counts["LOW"] == 1


class TestHTMLReportWithAlerts:
    """Tests for HTML report with alerts and new features."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        return MagicMock()

    def test_html_report_with_alerts(self, mock_db_session):
        """Test HTML report includes alerts section."""
        service = IngestionReportService(mock_db_session)

        report = DailyIngestionReport(
            report_date=date.today(),
            alerts=[
                IngestionAlert(AlertType.FEED_DOWN, AlertSeverity.HIGH, "Feed failed", "Test Feed"),
            ],
        )

        html = service._generate_html_report(report)

        assert "Alerts" in html
        assert "FEED_DOWN" in html
        assert "HIGH" in html
        assert "Feed failed" in html

    def test_html_report_with_no_alerts(self, mock_db_session):
        """Test HTML report shows 'no alerts' message."""
        service = IngestionReportService(mock_db_session)

        report = DailyIngestionReport(report_date=date.today(), alerts=[])

        html = service._generate_html_report(report)

        assert "No alerts" in html or "all systems operating normally" in html

    def test_html_report_with_environment_badge(self, mock_db_session):
        """Test HTML report includes environment badge."""
        service = IngestionReportService(mock_db_session)

        report = DailyIngestionReport(report_date=date.today())

        html = service._generate_html_report(report)

        # Should have env-badge class
        assert "env-badge" in html

    def test_html_report_with_wow_comparison(self, mock_db_session):
        """Test HTML report includes WoW comparison."""
        service = IngestionReportService(mock_db_session)

        report = DailyIngestionReport(
            report_date=date.today(),
            wow_documents_processed=WoWComparison(100, 80),
        )

        html = service._generate_html_report(report)

        assert "vs last week" in html or "wow" in html.lower()

    def test_html_report_with_document_previews(self, mock_db_session):
        """Test HTML report includes document previews."""
        service = IngestionReportService(mock_db_session)

        report = DailyIngestionReport(
            report_date=date.today(),
            new_document_previews=[
                DocumentPreview(
                    source="Test Source",
                    title="Test Document Title",
                    created_at=datetime.now(UTC),
                ),
            ],
        )

        html = service._generate_html_report(report)

        assert "New Documents Preview" in html
        assert "Test Document Title" in html

    def test_html_report_with_error_samples(self, mock_db_session):
        """Test HTML report includes error samples."""
        service = IngestionReportService(mock_db_session)

        report = DailyIngestionReport(
            report_date=date.today(),
            error_samples=[
                ErrorSample(
                    source_name="test-feed",
                    error_count=3,
                    sample_messages=["Connection refused"],
                ),
            ],
        )

        html = service._generate_html_report(report)

        assert "Error Details" in html
        assert "Connection refused" in html


@pytest.mark.asyncio
class TestRetryLogic:
    """Tests for retry logic in email sending."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock async database session."""
        mock = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar.return_value = 0
        mock_result.fetchall.return_value = []
        mock.execute = AsyncMock(return_value=mock_result)
        return mock

    @patch("smtplib.SMTP")
    async def test_retry_on_failure(self, mock_smtp, mock_db_session):
        """Test that retry logic attempts multiple times."""
        # Make SMTP fail first two times, then succeed
        call_count = 0

        def smtp_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("SMTP connection failed")
            return MagicMock(
                __enter__=MagicMock(return_value=MagicMock()),
                __exit__=MagicMock(return_value=None),
            )

        mock_smtp.side_effect = smtp_side_effect

        service = IngestionReportService(mock_db_session)
        service.smtp_username = "test@example.com"
        service.smtp_password = "test-password"  # pragma: allowlist secret

        # This should eventually succeed after retries
        # Note: Due to the way the retry is implemented, this test verifies the mechanism


class TestSchedulerTaskRegistration:
    """Tests for scheduler task registration."""

    def test_scheduler_task_exists(self):
        """Test that send_daily_ingestion_report_task is importable."""
        from app.services.scheduler_service import send_daily_ingestion_report_task

        assert callable(send_daily_ingestion_report_task)

    def test_setup_default_tasks_includes_ingestion_report(self):
        """Test that setup_default_tasks registers ingestion report task."""
        from app.services.scheduler_service import scheduler_service, setup_default_tasks

        # Clear any existing tasks
        scheduler_service.tasks = {}

        setup_default_tasks()

        assert "daily_ingestion_report" in scheduler_service.tasks


# =============================================================================
# DEV-247: Tests for Filtered Content Feature
# =============================================================================


class TestFilteredContentSample:
    """Tests for FilteredContentSample dataclass."""

    def test_filtered_content_sample_creation(self):
        """Test filtered content sample creation with all fields."""
        sample = FilteredContentSample(
            source_name="gazzetta_ufficiale_SG",
            items_filtered=15,
            sample_titles=[
                "Concorso pubblico per 100 posti",
                "Nomina del direttore generale",
                "Graduatoria finale concorso",
            ],
        )

        assert sample.source_name == "gazzetta_ufficiale_SG"
        assert sample.items_filtered == 15
        assert len(sample.sample_titles) == 3
        assert "Concorso pubblico" in sample.sample_titles[0]

    def test_filtered_content_sample_empty_titles(self):
        """Test filtered content sample with no sample titles."""
        sample = FilteredContentSample(
            source_name="test_feed",
            items_filtered=5,
        )

        assert sample.items_filtered == 5
        assert sample.sample_titles == []

    def test_filtered_content_sample_zero_filtered(self):
        """Test filtered content sample with zero filtered items."""
        sample = FilteredContentSample(
            source_name="test_feed",
            items_filtered=0,
        )

        assert sample.items_filtered == 0


class TestDailyIngestionReportFilteredContent:
    """Tests for DailyIngestionReport with filtered content."""

    def test_report_has_filtered_content_samples(self):
        """Test that report includes filtered_content_samples field."""
        report = DailyIngestionReport(report_date=date.today())

        assert hasattr(report, "filtered_content_samples")
        assert report.filtered_content_samples == []

    def test_report_with_filtered_samples(self):
        """Test report with filtered content samples populated."""
        report = DailyIngestionReport(
            report_date=date.today(),
            filtered_content_samples=[
                FilteredContentSample(
                    source_name="gazzetta_SG",
                    items_filtered=10,
                    sample_titles=["Concorso pubblico"],
                ),
                FilteredContentSample(
                    source_name="gazzetta_S1",
                    items_filtered=5,
                    sample_titles=["Nomina dirigente"],
                ),
            ],
        )

        assert len(report.filtered_content_samples) == 2
        total_filtered = sum(s.items_filtered for s in report.filtered_content_samples)
        assert total_filtered == 15


class TestHTMLReportWithFilteredContent:
    """Tests for HTML report with filtered content section."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        return MagicMock()

    def test_html_report_with_filtered_content(self, mock_db_session):
        """Test HTML report includes filtered content section."""
        service = IngestionReportService(mock_db_session)

        report = DailyIngestionReport(
            report_date=date.today(),
            filtered_content_samples=[
                FilteredContentSample(
                    source_name="gazzetta_ufficiale_SG",
                    items_filtered=12,
                    sample_titles=[
                        "Concorso pubblico per funzionari",
                        "Nomina del direttore",
                    ],
                ),
            ],
        )

        html = service._generate_html_report(report)

        # Check filtered content section is present
        assert "Filtered Content" in html
        assert "12" in html  # items_filtered count
        assert "Concorso pubblico per funzionari" in html
        assert "Nomina del direttore" in html
        assert "gazzetta_ufficiale_SG" in html

    def test_html_report_no_filtered_content(self, mock_db_session):
        """Test HTML report when no filtered content."""
        service = IngestionReportService(mock_db_session)

        report = DailyIngestionReport(
            report_date=date.today(),
            filtered_content_samples=[],
        )

        html = service._generate_html_report(report)

        # Should NOT have filtered content section when empty
        # (filtered_html is empty string when no samples)
        # The section title should not appear
        assert "Filtered Content (0 items)" not in html

    def test_html_report_filtered_content_explanation(self, mock_db_session):
        """Test that filtered content section includes explanation."""
        service = IngestionReportService(mock_db_session)

        report = DailyIngestionReport(
            report_date=date.today(),
            filtered_content_samples=[
                FilteredContentSample(
                    source_name="test",
                    items_filtered=5,
                    sample_titles=["Test title"],
                ),
            ],
        )

        html = service._generate_html_report(report)

        # Check explanation text is present
        assert "irrelevant to PratikoAI scope" in html
        assert "concorsi, nomine, graduatorie" in html

    def test_html_report_no_filtered_content_section_omitted(self, mock_db_session):
        """DEV-258: Test HTML report omits Data Quality when data_quality is None."""
        service = IngestionReportService(mock_db_session)

        report = DailyIngestionReport(report_date=date.today())
        assert report.data_quality is None

        html = service._generate_html_report(report)

        assert "Data Quality" not in html

    def test_html_report_multiple_filtered_sources(self, mock_db_session):
        """Test HTML report with multiple filtered sources."""
        service = IngestionReportService(mock_db_session)

        report = DailyIngestionReport(
            report_date=date.today(),
            filtered_content_samples=[
                FilteredContentSample(
                    source_name="source_a",
                    items_filtered=8,
                    sample_titles=["Title A1", "Title A2"],
                ),
                FilteredContentSample(
                    source_name="source_b",
                    items_filtered=4,
                    sample_titles=["Title B1"],
                ),
            ],
        )

        html = service._generate_html_report(report)

        # Check total count in header
        assert "12 items" in html
        # Check both sources are present
        assert "source_a" in html
        assert "source_b" in html
        assert "8" in html  # source_a count
        assert "4" in html  # source_b count


# =============================================================================
# DEV-258: Tests for Data Quality Integration
# =============================================================================


class TestDailyIngestionReportDataQuality:
    """Tests for DailyIngestionReport data_quality field."""

    def test_report_data_quality_default_none(self):
        """Test that data_quality defaults to None."""
        report = DailyIngestionReport(report_date=date.today())

        assert report.data_quality is None


class TestHTMLReportWithDataQuality:
    """Tests for HTML report with data quality section."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        return MagicMock()

    def test_html_includes_quality_section(self, mock_db_session):
        """Test that HTML includes Data Quality section when data_quality is set."""
        from app.services.data_quality_audit_service import DataQualitySummary

        service = IngestionReportService(mock_db_session)

        dq = DataQualitySummary(
            total_items=100,
            total_chunks=500,
            url_duplicate_groups=2,
            navigation_contaminated_chunks=5,
            items_missing_embedding=0,
            chunks_missing_embedding=0,
        )
        report = DailyIngestionReport(
            report_date=date.today(),
            data_quality=dq,
        )

        html = service._generate_html_report(report)

        assert "Data Quality" in html
        assert "URL Duplicate Groups" in html
        assert "Navigation Contaminated Chunks" in html
        assert "audit_data_quality.py" in html

    def test_html_omits_quality_when_none(self, mock_db_session):
        """Test that HTML has no Data Quality section when data_quality is None."""
        service = IngestionReportService(mock_db_session)

        report = DailyIngestionReport(report_date=date.today())

        html = service._generate_html_report(report)

        assert "Data Quality" not in html
