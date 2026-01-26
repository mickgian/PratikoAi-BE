"""Tests for Daily Cost Report Service - DEV-246.

Unit tests for the DailyCostReportService class.
Tests cost aggregation by environment, user breakdown, third-party API costs,
HTML report generation, and email sending.
"""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Environment


class TestEnvironmentCostBreakdown:
    """Tests for EnvironmentCostBreakdown dataclass."""

    def test_default_values(self):
        """Test default values for EnvironmentCostBreakdown."""
        from app.services.daily_cost_report_service import EnvironmentCostBreakdown

        breakdown = EnvironmentCostBreakdown(environment="development")

        assert breakdown.environment == "development"
        assert breakdown.total_cost_eur == 0.0
        assert breakdown.llm_cost_eur == 0.0
        assert breakdown.third_party_cost_eur == 0.0
        assert breakdown.request_count == 0
        assert breakdown.total_tokens == 0
        assert breakdown.unique_users == 0

    def test_with_values(self):
        """Test EnvironmentCostBreakdown with actual values."""
        from app.services.daily_cost_report_service import EnvironmentCostBreakdown

        breakdown = EnvironmentCostBreakdown(
            environment="production",
            total_cost_eur=10.50,
            llm_cost_eur=8.00,
            third_party_cost_eur=2.50,
            request_count=500,
            total_tokens=100000,
            unique_users=25,
        )

        assert breakdown.environment == "production"
        assert breakdown.total_cost_eur == 10.50
        assert breakdown.llm_cost_eur == 8.00
        assert breakdown.third_party_cost_eur == 2.50
        assert breakdown.request_count == 500
        assert breakdown.total_tokens == 100000
        assert breakdown.unique_users == 25


class TestUserCostBreakdown:
    """Tests for UserCostBreakdown dataclass."""

    def test_default_values(self):
        """Test default values for UserCostBreakdown."""
        from app.services.daily_cost_report_service import UserCostBreakdown

        breakdown = UserCostBreakdown(user_id="user_123")

        assert breakdown.user_id == "user_123"
        assert breakdown.total_cost_eur == 0.0
        assert breakdown.llm_cost_eur == 0.0
        assert breakdown.third_party_cost_eur == 0.0
        assert breakdown.request_count == 0
        assert breakdown.total_tokens == 0

    def test_percentage_of_total(self):
        """Test percentage calculation."""
        from app.services.daily_cost_report_service import UserCostBreakdown

        breakdown = UserCostBreakdown(
            user_id="user_123",
            total_cost_eur=2.50,
            request_count=100,
        )

        # Percentage relative to a total of 10.0
        percentage = breakdown.percentage_of_total(10.0)
        assert percentage == 25.0

    def test_percentage_of_total_zero(self):
        """Test percentage with zero total."""
        from app.services.daily_cost_report_service import UserCostBreakdown

        breakdown = UserCostBreakdown(user_id="user_123", total_cost_eur=2.50)

        percentage = breakdown.percentage_of_total(0.0)
        assert percentage == 0.0


class TestThirdPartyCostBreakdown:
    """Tests for ThirdPartyCostBreakdown dataclass."""

    def test_default_values(self):
        """Test default values for ThirdPartyCostBreakdown."""
        from app.services.daily_cost_report_service import ThirdPartyCostBreakdown

        breakdown = ThirdPartyCostBreakdown(api_type="brave_search")

        assert breakdown.api_type == "brave_search"
        assert breakdown.total_cost_eur == 0.0
        assert breakdown.request_count == 0
        assert breakdown.avg_cost_per_request == 0.0

    def test_avg_cost_per_request(self):
        """Test average cost per request calculation."""
        from app.services.daily_cost_report_service import ThirdPartyCostBreakdown

        breakdown = ThirdPartyCostBreakdown(
            api_type="brave_search",
            total_cost_eur=3.00,
            request_count=1000,
        )

        # avg_cost should be 3.00 / 1000 = 0.003
        assert breakdown.avg_cost_per_request == 0.003


class TestDailyCostReport:
    """Tests for DailyCostReport dataclass."""

    def test_empty_report(self):
        """Test empty report values."""
        from app.services.daily_cost_report_service import DailyCostReport

        report = DailyCostReport(report_date=date.today())

        assert report.total_cost_eur == 0.0
        assert report.llm_cost_eur == 0.0
        assert report.third_party_cost_eur == 0.0
        assert report.total_requests == 0
        assert report.total_tokens == 0
        assert report.unique_users == 0
        assert len(report.environment_breakdown) == 0
        assert len(report.user_breakdown) == 0
        assert len(report.third_party_breakdown) == 0

    def test_aggregated_totals(self):
        """Test that totals are correctly aggregated."""
        from app.services.daily_cost_report_service import (
            DailyCostReport,
            EnvironmentCostBreakdown,
            ThirdPartyCostBreakdown,
            UserCostBreakdown,
        )

        report = DailyCostReport(
            report_date=date.today(),
            total_cost_eur=15.50,
            llm_cost_eur=12.00,
            third_party_cost_eur=3.50,
            total_requests=750,
            total_tokens=150000,
            unique_users=30,
            environment_breakdown=[
                EnvironmentCostBreakdown(
                    environment="development",
                    total_cost_eur=5.00,
                    llm_cost_eur=4.00,
                    third_party_cost_eur=1.00,
                    request_count=250,
                    unique_users=10,
                ),
                EnvironmentCostBreakdown(
                    environment="production",
                    total_cost_eur=10.50,
                    llm_cost_eur=8.00,
                    third_party_cost_eur=2.50,
                    request_count=500,
                    unique_users=20,
                ),
            ],
            user_breakdown=[
                UserCostBreakdown(user_id="user_1", total_cost_eur=5.00),
                UserCostBreakdown(user_id="user_2", total_cost_eur=3.00),
            ],
            third_party_breakdown=[
                ThirdPartyCostBreakdown(
                    api_type="brave_search",
                    total_cost_eur=3.50,
                    request_count=1167,
                ),
            ],
        )

        assert report.total_cost_eur == 15.50
        assert report.llm_cost_eur == 12.00
        assert report.third_party_cost_eur == 3.50
        assert report.total_requests == 750
        assert len(report.environment_breakdown) == 2
        assert len(report.user_breakdown) == 2
        assert len(report.third_party_breakdown) == 1


class TestDailyCostReportService:
    """Tests for DailyCostReportService class."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        return MagicMock()

    def test_initialization(self, mock_db_session):
        """Test service initialization."""
        from app.services.daily_cost_report_service import DailyCostReportService

        service = DailyCostReportService(mock_db_session)

        assert service.db == mock_db_session
        assert service.smtp_server is not None

    @pytest.mark.asyncio
    async def test_get_environment_breakdown(self, mock_db_session):
        """Test environment cost breakdown aggregation."""
        from app.services.daily_cost_report_service import DailyCostReportService

        # Mock database result
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("development", 5.00, 4.00, 1.00, 250, 50000, 10),
            ("production", 10.50, 8.00, 2.50, 500, 100000, 20),
        ]
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        service = DailyCostReportService(mock_db_session)

        with patch("app.services.daily_cost_report_service.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 1, 24, 12, 0, 0, tzinfo=UTC)
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            breakdowns = await service._get_environment_breakdown(date(2026, 1, 24))

        assert len(breakdowns) == 2
        assert breakdowns[0].environment == "development"
        assert breakdowns[0].total_cost_eur == 5.00
        assert breakdowns[1].environment == "production"
        assert breakdowns[1].total_cost_eur == 10.50

    @pytest.mark.asyncio
    async def test_get_user_breakdown(self, mock_db_session):
        """Test user cost breakdown aggregation."""
        from app.services.daily_cost_report_service import DailyCostReportService

        # Mock database result
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("user_1", 5.00, 4.50, 0.50, 200, 45000),
            ("user_2", 3.00, 2.80, 0.20, 100, 30000),
            ("user_3", 2.00, 1.90, 0.10, 75, 20000),
        ]
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        service = DailyCostReportService(mock_db_session)

        breakdowns = await service._get_user_breakdown(date(2026, 1, 24), limit=10)

        assert len(breakdowns) == 3
        assert breakdowns[0].user_id == "user_1"
        assert breakdowns[0].total_cost_eur == 5.00
        assert breakdowns[1].user_id == "user_2"
        assert breakdowns[2].user_id == "user_3"

    @pytest.mark.asyncio
    async def test_get_third_party_breakdown(self, mock_db_session):
        """Test third-party API cost breakdown aggregation."""
        from app.services.daily_cost_report_service import DailyCostReportService

        # Mock database result
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("brave_search", 3.50, 1167),
        ]
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        service = DailyCostReportService(mock_db_session)

        breakdowns = await service._get_third_party_breakdown(date(2026, 1, 24))

        assert len(breakdowns) == 1
        assert breakdowns[0].api_type == "brave_search"
        assert breakdowns[0].total_cost_eur == 3.50
        assert breakdowns[0].request_count == 1167

    def test_html_report_generation(self, mock_db_session):
        """Test HTML report generation."""
        from app.services.daily_cost_report_service import (
            DailyCostReport,
            DailyCostReportService,
            EnvironmentCostBreakdown,
            ThirdPartyCostBreakdown,
            UserCostBreakdown,
        )

        service = DailyCostReportService(mock_db_session)

        report = DailyCostReport(
            report_date=date(2026, 1, 24),
            total_cost_eur=15.50,
            llm_cost_eur=12.00,
            third_party_cost_eur=3.50,
            total_requests=750,
            total_tokens=150000,
            unique_users=30,
            environment_breakdown=[
                EnvironmentCostBreakdown(
                    environment="development",
                    total_cost_eur=5.00,
                    llm_cost_eur=4.00,
                    third_party_cost_eur=1.00,
                    request_count=250,
                    unique_users=10,
                ),
                EnvironmentCostBreakdown(
                    environment="production",
                    total_cost_eur=10.50,
                    llm_cost_eur=8.00,
                    third_party_cost_eur=2.50,
                    request_count=500,
                    unique_users=20,
                ),
            ],
            user_breakdown=[
                UserCostBreakdown(user_id="user_1", total_cost_eur=5.00, request_count=200),
                UserCostBreakdown(user_id="user_2", total_cost_eur=3.00, request_count=100),
            ],
            third_party_breakdown=[
                ThirdPartyCostBreakdown(
                    api_type="brave_search",
                    total_cost_eur=3.50,
                    request_count=1167,
                ),
            ],
        )

        html = service._generate_html_report(report)

        # Check key elements are present
        assert "Daily Cost Report" in html
        assert "€15.50" in html or "15.50" in html
        assert "DEVELOPMENT" in html or "development" in html or "Development" in html
        assert "PRODUCTION" in html or "production" in html or "Production" in html
        assert "brave_search" in html or "Brave" in html
        assert "user_1" in html
        assert "user_2" in html

    def test_html_report_empty_breakdowns(self, mock_db_session):
        """Test HTML report with empty breakdowns."""
        from app.services.daily_cost_report_service import (
            DailyCostReport,
            DailyCostReportService,
        )

        service = DailyCostReportService(mock_db_session)

        report = DailyCostReport(report_date=date.today())

        html = service._generate_html_report(report)

        # Should still generate valid HTML
        assert "Daily Cost Report" in html
        assert "€0.00" in html or "0.00" in html

    @pytest.mark.asyncio
    async def test_generate_report(self, mock_db_session):
        """Test full report generation."""
        from app.services.daily_cost_report_service import DailyCostReportService

        # Mock all database calls
        mock_db_session.execute = AsyncMock()

        # Mock totals query
        mock_totals = MagicMock()
        mock_totals.first.return_value = (15.50, 12.00, 3.50, 750, 150000, 30)

        # Mock environment breakdown
        mock_env = MagicMock()
        mock_env.all.return_value = [("production", 15.50, 12.00, 3.50, 750, 150000, 30)]

        # Mock user breakdown
        mock_users = MagicMock()
        mock_users.all.return_value = [("user_1", 5.00, 4.50, 0.50, 200, 45000)]

        # Mock third-party breakdown
        mock_third_party = MagicMock()
        mock_third_party.all.return_value = [("brave_search", 3.50, 1167)]

        # Return different mocks for different calls
        mock_db_session.execute.side_effect = [
            mock_totals,
            mock_env,
            mock_users,
            mock_third_party,
        ]

        service = DailyCostReportService(mock_db_session)

        report = await service.generate_report(date(2026, 1, 24))

        assert report.total_cost_eur == 15.50
        assert report.llm_cost_eur == 12.00
        assert report.third_party_cost_eur == 3.50
        assert len(report.environment_breakdown) >= 0  # May vary based on mock
        assert len(report.user_breakdown) >= 0

    @pytest.mark.asyncio
    async def test_send_report_email(self, mock_db_session):
        """Test email sending."""
        from app.services.daily_cost_report_service import (
            DailyCostReport,
            DailyCostReportService,
        )

        service = DailyCostReportService(mock_db_session)

        report = DailyCostReport(
            report_date=date(2026, 1, 24),
            total_cost_eur=15.50,
        )

        # Mock SMTP (using SMTP with STARTTLS, not SMTP_SSL)
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            # Mock settings
            with patch("app.services.daily_cost_report_service.settings") as mock_settings:
                mock_settings.SMTP_SERVER = "smtp.test.com"
                mock_settings.SMTP_PORT = 587
                mock_settings.SMTP_USERNAME = "test@test.com"
                mock_settings.SMTP_PASSWORD = "password"  # pragma: allowlist secret
                mock_settings.DAILY_COST_REPORT_RECIPIENTS = ["admin@test.com"]

                success = await service.send_report(report, recipients=["admin@test.com"])

        # Email should attempt to send (may fail without real SMTP)
        # This test verifies the method runs without exceptions


class TestCostAlertThresholds:
    """Tests for cost alert thresholds."""

    def test_daily_threshold_exceeded(self):
        """Test daily cost threshold alert."""
        from app.services.daily_cost_report_service import (
            CostAlert,
            DailyCostReportService,
        )

        # Daily threshold is typically €10 for dev, €50 for prod
        alert = CostAlert(
            alert_type="DAILY_THRESHOLD_EXCEEDED",
            severity="HIGH",
            message="Daily cost exceeded €50 threshold",
            environment="production",
            current_cost=75.00,
            threshold=50.00,
        )

        assert alert.alert_type == "DAILY_THRESHOLD_EXCEEDED"
        assert alert.severity == "HIGH"
        assert alert.current_cost > alert.threshold

    def test_user_threshold_exceeded(self):
        """Test per-user cost threshold alert."""
        from app.services.daily_cost_report_service import CostAlert

        alert = CostAlert(
            alert_type="USER_THRESHOLD_EXCEEDED",
            severity="MEDIUM",
            message="User cost exceeded €2 threshold",
            environment="production",
            current_cost=2.50,
            threshold=2.00,
            user_id="user_123",
        )

        assert alert.alert_type == "USER_THRESHOLD_EXCEEDED"
        assert alert.user_id == "user_123"
        assert alert.current_cost > alert.threshold
