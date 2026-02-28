"""DEV-354: Tests for ROI Metrics Service.

Tests: time saved, communications sent, regulations tracked.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.roi_metrics_service import RoiMetricsService


@pytest.fixture
def svc():
    return RoiMetricsService()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db


class TestCalculateMetrics:
    @pytest.mark.asyncio
    async def test_get_studio_metrics(self, svc, mock_db):
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=10)))
        metrics = await svc.get_studio_metrics(mock_db, studio_id=uuid.uuid4())
        assert isinstance(metrics, dict)
        assert "total_clients" in metrics
        assert "communications_sent" in metrics
        assert "calculations_performed" in metrics

    @pytest.mark.asyncio
    async def test_time_saved_estimate(self, svc, mock_db):
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=50)))
        estimate = await svc.estimate_time_saved(mock_db, studio_id=uuid.uuid4())
        assert isinstance(estimate, dict)
        assert "hours_saved" in estimate
        assert estimate["hours_saved"] >= 0

    @pytest.mark.asyncio
    async def test_get_studio_metrics_calc_history_error_handled(self, svc, mock_db):
        """When calculation history query fails, it should still return metrics with 0."""
        # First two calls succeed (clients, communications), third fails (calculations)
        ok_result = MagicMock(scalar_one_or_none=MagicMock(return_value=5))
        mock_db.execute = AsyncMock(side_effect=[ok_result, ok_result, Exception("DB error")])
        metrics = await svc.get_studio_metrics(mock_db, studio_id=uuid.uuid4())
        assert isinstance(metrics, dict)
        assert metrics["total_clients"] == 5
        assert metrics["calculations_performed"] == 0


class TestMonthlyReport:
    @pytest.mark.asyncio
    async def test_monthly_report_structure(self, svc, mock_db):
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=0)))
        report = await svc.get_monthly_report(mock_db, studio_id=uuid.uuid4(), year=2026, month=2)
        assert isinstance(report, dict)
        assert "period" in report
        assert "metrics" in report
