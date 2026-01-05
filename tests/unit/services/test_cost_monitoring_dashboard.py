"""TDD Tests for DEV-239: Cost Monitoring Dashboard.

Tests for cost monitoring service with per-query tracking,
model breakdown, and daily/weekly aggregates.

Coverage Target: 90%+ for new code.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# =============================================================================
# Sample Test Data
# =============================================================================

SAMPLE_COST_DATA = {
    "query_costs": [
        {
            "request_id": "req_001",
            "user_id": "user_123",
            "model": "gpt-4o-mini",
            "complexity": "simple",
            "cost_euros": 0.0015,
            "tokens_input": 500,
            "tokens_output": 200,
            "timestamp": datetime.utcnow() - timedelta(hours=1),
        },
        {
            "request_id": "req_002",
            "user_id": "user_123",
            "model": "gpt-4o",
            "complexity": "complex",
            "cost_euros": 0.025,
            "tokens_input": 1000,
            "tokens_output": 500,
            "timestamp": datetime.utcnow() - timedelta(hours=2),
        },
        {
            "request_id": "req_003",
            "user_id": "user_456",
            "model": "gpt-4o",
            "complexity": "multi_domain",
            "cost_euros": 0.035,
            "tokens_input": 1500,
            "tokens_output": 700,
            "timestamp": datetime.utcnow() - timedelta(days=1),
        },
    ]
}


# =============================================================================
# Cost Per Query Tests
# =============================================================================


class TestCostPerQueryTracking:
    """Tests for cost per query tracking."""

    @pytest.mark.asyncio
    async def test_get_query_costs_returns_list(self):
        """Should return list of query costs."""
        from app.services.cost_monitoring_dashboard import CostMonitoringDashboard

        dashboard = CostMonitoringDashboard()

        with patch.object(dashboard, "_fetch_query_costs") as mock_fetch:
            mock_fetch.return_value = SAMPLE_COST_DATA["query_costs"]

            result = await dashboard.get_query_costs(
                user_id="user_123",
                limit=10,
            )

            assert isinstance(result, list)
            assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_get_query_costs_includes_required_fields(self):
        """Each query cost should include required fields."""
        from app.services.cost_monitoring_dashboard import CostMonitoringDashboard

        dashboard = CostMonitoringDashboard()

        with patch.object(dashboard, "_fetch_query_costs") as mock_fetch:
            mock_fetch.return_value = [SAMPLE_COST_DATA["query_costs"][0]]

            result = await dashboard.get_query_costs(user_id="user_123", limit=1)

            assert len(result) == 1
            query = result[0]
            assert "request_id" in query
            assert "model" in query
            assert "cost_euros" in query
            assert "complexity" in query

    @pytest.mark.asyncio
    async def test_get_query_costs_filters_by_user(self):
        """Should filter costs by user_id."""
        from app.services.cost_monitoring_dashboard import CostMonitoringDashboard

        dashboard = CostMonitoringDashboard()

        with patch.object(dashboard, "_fetch_query_costs") as mock_fetch:
            # Only return user_123's costs
            user_costs = [c for c in SAMPLE_COST_DATA["query_costs"] if c["user_id"] == "user_123"]
            mock_fetch.return_value = user_costs

            result = await dashboard.get_query_costs(user_id="user_123", limit=10)

            mock_fetch.assert_called_once()
            # Verify user_id was passed
            call_args = mock_fetch.call_args
            assert call_args[1]["user_id"] == "user_123"


# =============================================================================
# Cost By Model Tests
# =============================================================================


class TestCostByModelBreakdown:
    """Tests for cost breakdown by model."""

    @pytest.mark.asyncio
    async def test_get_cost_by_model_returns_breakdown(self):
        """Should return cost breakdown by model."""
        from app.services.cost_monitoring_dashboard import CostMonitoringDashboard

        dashboard = CostMonitoringDashboard()

        with patch.object(dashboard, "_aggregate_costs_by_model") as mock_agg:
            mock_agg.return_value = {
                "gpt-4o-mini": {"total_cost": 0.015, "query_count": 10, "avg_cost": 0.0015},
                "gpt-4o": {"total_cost": 0.50, "query_count": 20, "avg_cost": 0.025},
            }

            result = await dashboard.get_cost_by_model()

            assert "gpt-4o-mini" in result
            assert "gpt-4o" in result

    @pytest.mark.asyncio
    async def test_cost_by_model_includes_query_count(self):
        """Model breakdown should include query count."""
        from app.services.cost_monitoring_dashboard import CostMonitoringDashboard

        dashboard = CostMonitoringDashboard()

        with patch.object(dashboard, "_aggregate_costs_by_model") as mock_agg:
            mock_agg.return_value = {
                "gpt-4o-mini": {"total_cost": 0.015, "query_count": 10, "avg_cost": 0.0015},
            }

            result = await dashboard.get_cost_by_model()

            assert result["gpt-4o-mini"]["query_count"] == 10

    @pytest.mark.asyncio
    async def test_cost_by_model_includes_average_cost(self):
        """Model breakdown should include average cost per query."""
        from app.services.cost_monitoring_dashboard import CostMonitoringDashboard

        dashboard = CostMonitoringDashboard()

        with patch.object(dashboard, "_aggregate_costs_by_model") as mock_agg:
            mock_agg.return_value = {
                "gpt-4o": {"total_cost": 0.50, "query_count": 20, "avg_cost": 0.025},
            }

            result = await dashboard.get_cost_by_model()

            assert result["gpt-4o"]["avg_cost"] == 0.025


# =============================================================================
# Daily/Weekly Aggregate Tests
# =============================================================================


class TestDailyWeeklyAggregates:
    """Tests for daily and weekly cost aggregates."""

    @pytest.mark.asyncio
    async def test_get_daily_aggregates_returns_list(self):
        """Should return list of daily aggregates."""
        from app.services.cost_monitoring_dashboard import CostMonitoringDashboard

        dashboard = CostMonitoringDashboard()

        with patch.object(dashboard, "_fetch_daily_aggregates") as mock_fetch:
            mock_fetch.return_value = [
                {"date": "2025-01-05", "total_cost": 1.50, "query_count": 100},
                {"date": "2025-01-04", "total_cost": 1.25, "query_count": 85},
            ]

            result = await dashboard.get_daily_aggregates(days=7)

            assert isinstance(result, list)
            assert len(result) >= 1
            assert "date" in result[0]
            assert "total_cost" in result[0]

    @pytest.mark.asyncio
    async def test_get_weekly_aggregates_returns_list(self):
        """Should return list of weekly aggregates."""
        from app.services.cost_monitoring_dashboard import CostMonitoringDashboard

        dashboard = CostMonitoringDashboard()

        with patch.object(dashboard, "_fetch_weekly_aggregates") as mock_fetch:
            mock_fetch.return_value = [
                {"week_start": "2025-01-01", "total_cost": 10.50, "query_count": 700},
            ]

            result = await dashboard.get_weekly_aggregates(weeks=4)

            assert isinstance(result, list)
            assert "week_start" in result[0]
            assert "total_cost" in result[0]

    @pytest.mark.asyncio
    async def test_daily_aggregates_sorted_by_date(self):
        """Daily aggregates should be sorted by date descending."""
        from app.services.cost_monitoring_dashboard import CostMonitoringDashboard

        dashboard = CostMonitoringDashboard()

        with patch.object(dashboard, "_fetch_daily_aggregates") as mock_fetch:
            mock_fetch.return_value = [
                {"date": "2025-01-05", "total_cost": 1.50, "query_count": 100},
                {"date": "2025-01-04", "total_cost": 1.25, "query_count": 85},
                {"date": "2025-01-03", "total_cost": 1.00, "query_count": 70},
            ]

            result = await dashboard.get_daily_aggregates(days=7)

            # Should be most recent first
            dates = [r["date"] for r in result]
            assert dates == sorted(dates, reverse=True)


# =============================================================================
# Cost By Complexity Tests
# =============================================================================


class TestCostByComplexity:
    """Tests for cost breakdown by complexity level."""

    @pytest.mark.asyncio
    async def test_get_cost_by_complexity_returns_breakdown(self):
        """Should return cost breakdown by complexity."""
        from app.services.cost_monitoring_dashboard import CostMonitoringDashboard

        dashboard = CostMonitoringDashboard()

        with patch.object(dashboard, "_aggregate_costs_by_complexity") as mock_agg:
            mock_agg.return_value = {
                "simple": {"total_cost": 0.10, "query_count": 50, "percentage": 60.0},
                "complex": {"total_cost": 0.30, "query_count": 30, "percentage": 30.0},
                "multi_domain": {"total_cost": 0.20, "query_count": 10, "percentage": 10.0},
            }

            result = await dashboard.get_cost_by_complexity()

            assert "simple" in result
            assert "complex" in result
            assert "multi_domain" in result

    @pytest.mark.asyncio
    async def test_cost_by_complexity_includes_percentage(self):
        """Complexity breakdown should include percentage of total."""
        from app.services.cost_monitoring_dashboard import CostMonitoringDashboard

        dashboard = CostMonitoringDashboard()

        with patch.object(dashboard, "_aggregate_costs_by_complexity") as mock_agg:
            mock_agg.return_value = {
                "simple": {"total_cost": 0.10, "query_count": 50, "percentage": 60.0},
            }

            result = await dashboard.get_cost_by_complexity()

            assert "percentage" in result["simple"]


# =============================================================================
# Dashboard Summary Tests
# =============================================================================


class TestDashboardSummary:
    """Tests for the overall dashboard summary."""

    @pytest.mark.asyncio
    async def test_get_dashboard_summary_returns_all_sections(self):
        """Dashboard summary should include all key sections."""
        from app.services.cost_monitoring_dashboard import CostMonitoringDashboard

        dashboard = CostMonitoringDashboard()

        with patch.object(dashboard, "get_cost_by_model") as mock_model, \
             patch.object(dashboard, "get_cost_by_complexity") as mock_complexity, \
             patch.object(dashboard, "get_daily_aggregates") as mock_daily:

            mock_model.return_value = {"gpt-4o": {"total_cost": 1.0}}
            mock_complexity.return_value = {"simple": {"total_cost": 0.5}}
            mock_daily.return_value = [{"date": "2025-01-05", "total_cost": 1.0}]

            result = await dashboard.get_dashboard_summary()

            assert "by_model" in result
            assert "by_complexity" in result
            assert "daily_trend" in result
            assert "total_cost" in result

    @pytest.mark.asyncio
    async def test_dashboard_summary_calculates_total_cost(self):
        """Dashboard summary should calculate total cost."""
        from app.services.cost_monitoring_dashboard import CostMonitoringDashboard

        dashboard = CostMonitoringDashboard()

        with patch.object(dashboard, "_calculate_total_cost") as mock_total:
            mock_total.return_value = 15.50

            with patch.object(dashboard, "get_cost_by_model") as mock_model, \
                 patch.object(dashboard, "get_cost_by_complexity") as mock_complexity, \
                 patch.object(dashboard, "get_daily_aggregates") as mock_daily:

                mock_model.return_value = {}
                mock_complexity.return_value = {}
                mock_daily.return_value = []

                result = await dashboard.get_dashboard_summary()

                assert result["total_cost"] == 15.50


# =============================================================================
# API Response Format Tests
# =============================================================================


class TestAPIResponseFormat:
    """Tests for API response format."""

    @pytest.mark.asyncio
    async def test_response_includes_period_info(self):
        """API response should include period information."""
        from app.services.cost_monitoring_dashboard import CostMonitoringDashboard

        dashboard = CostMonitoringDashboard()

        with patch.object(dashboard, "_calculate_total_cost") as mock_total, \
             patch.object(dashboard, "get_cost_by_model") as mock_model, \
             patch.object(dashboard, "get_cost_by_complexity") as mock_complexity, \
             patch.object(dashboard, "get_daily_aggregates") as mock_daily:

            mock_total.return_value = 0.0
            mock_model.return_value = {}
            mock_complexity.return_value = {}
            mock_daily.return_value = []

            result = await dashboard.get_dashboard_summary()

            assert "period_start" in result
            assert "period_end" in result

    def test_cost_monitoring_dashboard_importable(self):
        """CostMonitoringDashboard should be importable."""
        from app.services.cost_monitoring_dashboard import CostMonitoringDashboard

        dashboard = CostMonitoringDashboard()
        assert dashboard is not None
