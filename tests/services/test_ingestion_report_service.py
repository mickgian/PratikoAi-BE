"""Tests for Ingestion Report Service - DEV-BE-69.

Unit tests for the IngestionReportService class.
Tests report generation and email sending functionality.
"""

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ingestion_report_service import (
    DailyIngestionReport,
    IngestionReportService,
    SourceStats,
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
        """Test generating report with no data."""
        # Mock empty results - need to handle both scalars().all() and scalar() calls
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar.return_value = 0
        mock_result.fetchall.return_value = []
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        service = IngestionReportService(mock_db_session)
        report = await service.generate_daily_report(date.today())

        assert report.report_date == date.today()
        assert len(report.rss_sources) == 0
        assert len(report.scraper_sources) == 0

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
        mock_server.sendmail.assert_called_once()


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
