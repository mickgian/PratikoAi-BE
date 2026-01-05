"""TDD Tests for DEV-240: Action Quality Metrics.

Tests for action quality metrics service tracking:
- Validation pass rate
- Regeneration rate
- Click-through rate

Coverage Target: 90%+ for new code.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# =============================================================================
# Sample Test Data
# =============================================================================

SAMPLE_VALIDATION_DATA = {
    "total_actions": 100,
    "valid_actions": 85,
    "rejected_actions": 15,
    "pass_rate": 0.85,
}

SAMPLE_REGENERATION_DATA = {
    "total_requests": 50,
    "regeneration_triggered": 10,
    "regeneration_rate": 0.20,
}

SAMPLE_CLICK_DATA = {
    "actions_displayed": 150,
    "actions_clicked": 30,
    "click_through_rate": 0.20,
}


# =============================================================================
# Validation Pass Rate Tests
# =============================================================================


class TestValidationPassRate:
    """Tests for validation pass rate tracking."""

    @pytest.mark.asyncio
    async def test_record_validation_result_pass(self):
        """Should record a successful validation."""
        from app.services.action_quality_metrics import ActionQualityMetrics

        metrics = ActionQualityMetrics()

        metrics.record_validation_result(
            total_actions=4,
            valid_actions=3,
            rejected_actions=1,
        )

        summary = metrics.get_validation_summary()
        assert summary["total_validations"] >= 1
        assert "pass_rate" in summary

    @pytest.mark.asyncio
    async def test_record_validation_result_all_pass(self):
        """Should handle 100% pass rate."""
        from app.services.action_quality_metrics import ActionQualityMetrics

        metrics = ActionQualityMetrics()

        metrics.record_validation_result(
            total_actions=5,
            valid_actions=5,
            rejected_actions=0,
        )

        summary = metrics.get_validation_summary()
        assert summary["pass_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_record_validation_result_all_fail(self):
        """Should handle 0% pass rate."""
        from app.services.action_quality_metrics import ActionQualityMetrics

        metrics = ActionQualityMetrics()

        metrics.record_validation_result(
            total_actions=3,
            valid_actions=0,
            rejected_actions=3,
        )

        summary = metrics.get_validation_summary()
        assert summary["pass_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_validation_pass_rate_calculation(self):
        """Should calculate pass rate correctly."""
        from app.services.action_quality_metrics import ActionQualityMetrics

        metrics = ActionQualityMetrics()

        # 10 validations: 8 passed, 2 rejected
        for _ in range(8):
            metrics.record_validation_result(
                total_actions=1,
                valid_actions=1,
                rejected_actions=0,
            )
        for _ in range(2):
            metrics.record_validation_result(
                total_actions=1,
                valid_actions=0,
                rejected_actions=1,
            )

        summary = metrics.get_validation_summary()
        assert summary["pass_rate"] == pytest.approx(0.8, rel=0.01)


# =============================================================================
# Regeneration Rate Tests
# =============================================================================


class TestRegenerationRate:
    """Tests for regeneration rate tracking."""

    @pytest.mark.asyncio
    async def test_record_regeneration_triggered(self):
        """Should record when regeneration is triggered."""
        from app.services.action_quality_metrics import ActionQualityMetrics

        metrics = ActionQualityMetrics()

        metrics.record_regeneration_attempt(
            triggered=True,
            attempt_number=1,
            success=True,
        )

        summary = metrics.get_regeneration_summary()
        assert summary["total_requests"] >= 1
        assert summary["regenerations_triggered"] >= 1

    @pytest.mark.asyncio
    async def test_record_regeneration_not_needed(self):
        """Should record when regeneration is not needed."""
        from app.services.action_quality_metrics import ActionQualityMetrics

        metrics = ActionQualityMetrics()

        metrics.record_regeneration_attempt(
            triggered=False,
            attempt_number=0,
            success=True,
        )

        summary = metrics.get_regeneration_summary()
        assert summary["regenerations_triggered"] == 0

    @pytest.mark.asyncio
    async def test_regeneration_rate_calculation(self):
        """Should calculate regeneration rate correctly."""
        from app.services.action_quality_metrics import ActionQualityMetrics

        metrics = ActionQualityMetrics()

        # 5 requests, 1 triggered regeneration
        for _ in range(4):
            metrics.record_regeneration_attempt(triggered=False)
        metrics.record_regeneration_attempt(triggered=True, success=True)

        summary = metrics.get_regeneration_summary()
        assert summary["regeneration_rate"] == pytest.approx(0.2, rel=0.01)

    @pytest.mark.asyncio
    async def test_regeneration_success_tracking(self):
        """Should track regeneration success/failure."""
        from app.services.action_quality_metrics import ActionQualityMetrics

        metrics = ActionQualityMetrics()

        # 2 regenerations: 1 success, 1 failure
        metrics.record_regeneration_attempt(triggered=True, success=True)
        metrics.record_regeneration_attempt(triggered=True, success=False)

        summary = metrics.get_regeneration_summary()
        assert summary["regeneration_success_rate"] == pytest.approx(0.5, rel=0.01)


# =============================================================================
# Click-Through Rate Tests
# =============================================================================


class TestClickThroughRate:
    """Tests for click-through rate tracking."""

    @pytest.mark.asyncio
    async def test_record_action_displayed(self):
        """Should record when actions are displayed."""
        from app.services.action_quality_metrics import ActionQualityMetrics

        metrics = ActionQualityMetrics()

        metrics.record_actions_displayed(count=3)

        summary = metrics.get_click_summary()
        assert summary["actions_displayed"] >= 3

    @pytest.mark.asyncio
    async def test_record_action_clicked(self):
        """Should record when an action is clicked."""
        from app.services.action_quality_metrics import ActionQualityMetrics

        metrics = ActionQualityMetrics()

        metrics.record_action_clicked()

        summary = metrics.get_click_summary()
        assert summary["actions_clicked"] >= 1

    @pytest.mark.asyncio
    async def test_click_through_rate_calculation(self):
        """Should calculate click-through rate correctly."""
        from app.services.action_quality_metrics import ActionQualityMetrics

        metrics = ActionQualityMetrics()

        # 10 actions displayed, 2 clicked
        metrics.record_actions_displayed(count=10)
        metrics.record_action_clicked()
        metrics.record_action_clicked()

        summary = metrics.get_click_summary()
        assert summary["click_through_rate"] == pytest.approx(0.2, rel=0.01)

    @pytest.mark.asyncio
    async def test_click_through_rate_zero_displayed(self):
        """Should handle zero displayed actions."""
        from app.services.action_quality_metrics import ActionQualityMetrics

        metrics = ActionQualityMetrics()

        summary = metrics.get_click_summary()
        assert summary["click_through_rate"] == 0.0


# =============================================================================
# Dashboard Summary Tests
# =============================================================================


class TestDashboardSummary:
    """Tests for the overall dashboard summary."""

    @pytest.mark.asyncio
    async def test_get_dashboard_summary_returns_all_sections(self):
        """Dashboard summary should include all key sections."""
        from app.services.action_quality_metrics import ActionQualityMetrics

        metrics = ActionQualityMetrics()

        # Record some data
        metrics.record_validation_result(total_actions=3, valid_actions=2, rejected_actions=1)
        metrics.record_regeneration_attempt(triggered=True, success=True)
        metrics.record_actions_displayed(count=5)
        metrics.record_action_clicked()

        summary = metrics.get_dashboard_summary()

        assert "validation" in summary
        assert "regeneration" in summary
        assert "clicks" in summary
        assert "period_start" in summary
        assert "period_end" in summary

    @pytest.mark.asyncio
    async def test_dashboard_summary_validation_section(self):
        """Validation section should include required metrics."""
        from app.services.action_quality_metrics import ActionQualityMetrics

        metrics = ActionQualityMetrics()
        metrics.record_validation_result(total_actions=4, valid_actions=3, rejected_actions=1)

        summary = metrics.get_dashboard_summary()

        assert "pass_rate" in summary["validation"]
        assert "total_validations" in summary["validation"]
        assert "total_actions" in summary["validation"]

    @pytest.mark.asyncio
    async def test_dashboard_summary_regeneration_section(self):
        """Regeneration section should include required metrics."""
        from app.services.action_quality_metrics import ActionQualityMetrics

        metrics = ActionQualityMetrics()
        metrics.record_regeneration_attempt(triggered=True, success=True)

        summary = metrics.get_dashboard_summary()

        assert "regeneration_rate" in summary["regeneration"]
        assert "total_requests" in summary["regeneration"]

    @pytest.mark.asyncio
    async def test_dashboard_summary_clicks_section(self):
        """Clicks section should include required metrics."""
        from app.services.action_quality_metrics import ActionQualityMetrics

        metrics = ActionQualityMetrics()
        metrics.record_actions_displayed(count=10)
        metrics.record_action_clicked()

        summary = metrics.get_dashboard_summary()

        assert "click_through_rate" in summary["clicks"]
        assert "actions_displayed" in summary["clicks"]
        assert "actions_clicked" in summary["clicks"]


# =============================================================================
# Reset and Period Tests
# =============================================================================


class TestMetricsReset:
    """Tests for metrics reset functionality."""

    @pytest.mark.asyncio
    async def test_reset_metrics(self):
        """Should reset all metrics to zero."""
        from app.services.action_quality_metrics import ActionQualityMetrics

        metrics = ActionQualityMetrics()

        # Add some data
        metrics.record_validation_result(total_actions=5, valid_actions=4, rejected_actions=1)
        metrics.record_regeneration_attempt(triggered=True, success=True)
        metrics.record_actions_displayed(count=10)
        metrics.record_action_clicked()

        # Reset
        metrics.reset()

        summary = metrics.get_dashboard_summary()
        assert summary["validation"]["total_validations"] == 0
        assert summary["regeneration"]["total_requests"] == 0
        assert summary["clicks"]["actions_displayed"] == 0


# =============================================================================
# Service Import Tests
# =============================================================================


class TestServiceImport:
    """Tests for service importability."""

    def test_action_quality_metrics_importable(self):
        """ActionQualityMetrics should be importable."""
        from app.services.action_quality_metrics import ActionQualityMetrics

        metrics = ActionQualityMetrics()
        assert metrics is not None

    def test_get_action_quality_metrics_importable(self):
        """get_action_quality_metrics should be importable."""
        from app.services.action_quality_metrics import get_action_quality_metrics

        metrics = get_action_quality_metrics()
        assert metrics is not None
