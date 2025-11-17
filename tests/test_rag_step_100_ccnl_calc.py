"""
Comprehensive test suite for RAG STEP 100 — CCNLCalculator.calculate Perform calculations.

Tests the orchestrator function that bridges PostgreSQL CCNL queries with the
calculation engine, following MASTER_GUARDRAILS TDD methodology.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.ccnl_data import CCNLAgreement, CCNLSector, CompanySize, GeographicArea, WorkerCategory
from app.orchestrators.ccnl import step_100__ccnlcalc
from app.services.ccnl_calculator_engine import CalculationPeriod, CompensationBreakdown, EnhancedCCNLCalculator


class TestStep100CCNLCalcUnit:
    """Unit tests for Step 100 CCNLCalc orchestrator function."""

    @pytest.fixture
    def sample_ccnl_context(self):
        """Sample context with CCNL query results from PostgresQuery step."""
        return {
            "request_id": "test-request-123",
            "rag_step": 97,  # PostgresQuery step
            "ccnl_agreement": {
                "id": "ccnl_commercio_2024",
                "sector": "COMMERCIO_TERZIARIO",
                "name": "CCNL Commercio 2024",
                "valid_from": "2024-01-01",
                "valid_until": "2026-12-31",
            },
            "calculation_params": {
                "level_code": "Q2",
                "geographic_area": "NAZIONALE",
                "company_size": "MEDIUM",
                "seniority_months": 24,
                "working_days_per_month": 22,
                "overtime_hours_monthly": 8,
                "include_allowances": True,
                "period": "ANNUAL",
            },
            "ccnl_query_results": {
                "agreements_found": 1,
                "matched_levels": ["Q2"],
                "applicable_sectors": ["COMMERCIO"],
            },
        }

    @pytest.fixture
    def sample_compensation_breakdown(self):
        """Sample compensation calculation result."""
        return CompensationBreakdown(
            base_salary=Decimal("24000.00"),
            thirteenth_month=Decimal("2000.00"),
            fourteenth_month=Decimal("2000.00"),
            overtime=Decimal("1800.00"),
            allowances={"Indennità di Trasporto": Decimal("600.00"), "Indennità Mensa": Decimal("1200.00")},
            deductions={
                "IRPEF": Decimal("4500.00"),
                "INPS": Decimal("2300.00"),
                "Addizionale Regionale": Decimal("200.00"),
            },
            gross_total=Decimal("31600.00"),
            net_total=Decimal("24600.00"),
            period=CalculationPeriod.ANNUAL,
        )

    @pytest.mark.asyncio
    async def test_successful_ccnl_calculation(self, sample_ccnl_context, sample_compensation_breakdown):
        """Test successful CCNL calculation orchestration."""
        with (
            patch("app.models.ccnl_data.CCNLAgreement") as MockCCNLAgreement,
            patch("app.services.ccnl_calculator_engine.EnhancedCCNLCalculator") as MockCalculator,
            patch("app.orchestrators.ccnl.rag_step_log") as mock_log,
            patch("app.orchestrators.ccnl.rag_step_timer") as mock_timer,
        ):
            # Setup mocks
            mock_agreement = MagicMock()
            MockCCNLAgreement.return_value = mock_agreement

            mock_calculator = MagicMock()
            mock_calculator.calculate_comprehensive_compensation.return_value = sample_compensation_breakdown
            MockCalculator.return_value = mock_calculator

            mock_timer.return_value.__enter__ = MagicMock()
            mock_timer.return_value.__exit__ = MagicMock()

            # Execute step
            result = await step_100__ccnlcalc(ctx=sample_ccnl_context)

            # Verify orchestration
            assert result is not None
            assert result["rag_step"] == 100
            assert result["request_id"] == "test-request-123"
            assert "compensation_breakdown" in result
            assert result["calculation_success"] is True

            # Verify calculation results structure
            compensation = result["compensation_breakdown"]
            assert compensation["gross_total"] == Decimal("31600.00")
            assert compensation["net_total"] == Decimal("24600.00")
            assert compensation["base_salary"] == Decimal("24000.00")
            assert "allowances" in compensation
            assert "deductions" in compensation

            # Verify observability
            mock_log.assert_called()
            mock_timer.assert_called_with(
                100,
                "RAG.ccnl.ccnlcalculator.calculate.perform.calculations",
                "CCNLCalc",
                request_id="test-request-123",
                stage="start",
            )

    @pytest.mark.asyncio
    async def test_missing_calculation_params(self):
        """Test handling of missing calculation parameters."""
        ctx = {
            "request_id": "test-request-456",
            "rag_step": 97,
            "ccnl_agreement": {"id": "ccnl_test"},
            # Missing calculation_params
        }

        with patch("app.orchestrators.ccnl.rag_step_log") as mock_log:
            result = await step_100__ccnlcalc(ctx=ctx)

            # Should handle gracefully with default parameters
            assert result is not None
            assert result["calculation_success"] is False
            assert "error" in result
            assert "missing calculation parameters" in result["error"].lower()

            mock_log.assert_called()

    @pytest.mark.asyncio
    async def test_missing_ccnl_agreement(self, sample_ccnl_context):
        """Test handling of missing CCNL agreement data."""
        # Remove ccnl_agreement from context
        del sample_ccnl_context["ccnl_agreement"]

        with patch("app.orchestrators.ccnl.rag_step_log"):
            result = await step_100__ccnlcalc(ctx=sample_ccnl_context)

            assert result is not None
            assert result["calculation_success"] is False
            assert "error" in result
            assert "ccnl agreement" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_calculation_engine_exception(self, sample_ccnl_context):
        """Test handling of calculation engine exceptions."""
        with (
            patch("app.models.ccnl_data.CCNLAgreement"),
            patch("app.services.ccnl_calculator_engine.EnhancedCCNLCalculator") as MockCalculator,
            patch("app.orchestrators.ccnl.rag_step_log"),
        ):
            # Setup calculator to raise exception
            mock_calculator = MagicMock()
            mock_calculator.calculate_comprehensive_compensation.side_effect = Exception("Calculation failed")
            MockCalculator.return_value = mock_calculator

            result = await step_100__ccnlcalc(ctx=sample_ccnl_context)

            assert result is not None
            assert result["calculation_success"] is False
            assert "error" in result
            assert "calculation failed" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_parameter_validation_and_defaults(self):
        """Test parameter validation and application of defaults."""
        ctx = {
            "request_id": "test-request-789",
            "rag_step": 97,
            "ccnl_agreement": {"id": "ccnl_test", "sector": "COMMERCIO"},
            "calculation_params": {
                "level_code": "Q1",
                # Missing optional parameters should get defaults
            },
        }

        with (
            patch("app.models.ccnl_data.CCNLAgreement") as MockCCNLAgreement,
            patch("app.services.ccnl_calculator_engine.EnhancedCCNLCalculator") as MockCalculator,
            patch("app.orchestrators.ccnl.rag_step_log"),
        ):
            mock_agreement = MagicMock()
            MockCCNLAgreement.return_value = mock_agreement

            mock_calculator = MagicMock()
            mock_breakdown = MagicMock()
            mock_breakdown.gross_total = Decimal("30000.00")
            mock_breakdown.net_total = Decimal("22000.00")
            mock_calculator.calculate_comprehensive_compensation.return_value = mock_breakdown
            MockCalculator.return_value = mock_calculator

            await step_100__ccnlcalc(ctx=ctx)

            # Verify defaults were applied during calculation call
            mock_calculator.calculate_comprehensive_compensation.assert_called_once()
            call_args = mock_calculator.calculate_comprehensive_compensation.call_args
            assert call_args.kwargs["seniority_months"] == 0  # Default
            assert call_args.kwargs["working_days_per_month"] == 22  # Default
            assert call_args.kwargs["include_allowances"] is True  # Default


class TestStep100CCNLCalcIntegration:
    """Integration tests for Step 100 in the RAG workflow."""

    @pytest.mark.asyncio
    async def test_postgres_query_to_ccnl_calc_flow(self):
        """Test integration from PostgresQuery step to CCNLCalc step."""
        # Simulate context from PostgresQuery step (Step 97)
        postgres_result_ctx = {
            "request_id": "integration-test-001",
            "rag_step": 97,
            "postgres_query_results": {
                "ccnl_agreements": [
                    {"id": "ccnl_commercio_2024", "sector": "COMMERCIO_TERZIARIO", "name": "CCNL Commercio 2024"}
                ],
                "salary_tables": [{"level_code": "Q2", "base_monthly": 2000.00}],
            },
            "ccnl_agreement": {"id": "ccnl_commercio_2024", "sector": "COMMERCIO"},
            "calculation_params": {"level_code": "Q2", "geographic_area": "NAZIONALE"},
        }

        with (
            patch("app.models.ccnl_data.CCNLAgreement"),
            patch("app.services.ccnl_calculator_engine.EnhancedCCNLCalculator") as MockCalculator,
            patch("app.orchestrators.ccnl.rag_step_log"),
        ):
            mock_calculator = MagicMock()
            mock_breakdown = MagicMock()
            mock_breakdown.gross_total = Decimal("28000.00")
            mock_breakdown.net_total = Decimal("20000.00")
            mock_calculator.calculate_comprehensive_compensation.return_value = mock_breakdown
            MockCalculator.return_value = mock_calculator

            result = await step_100__ccnlcalc(ctx=postgres_result_ctx)

            # Verify flow progression
            assert result["previous_step"] == 97  # PostgresQuery
            assert result["rag_step"] == 100  # CCNLCalc
            assert result["next_step"] == 99  # Should route to ToolResults
            assert "compensation_breakdown" in result

    @pytest.mark.asyncio
    async def test_ccnl_calc_to_tool_results_flow(self):
        """Test integration from CCNLCalc step to ToolResults step."""
        ctx = {
            "request_id": "integration-test-002",
            "rag_step": 97,
            "tool_call": {
                "name": "ccnl_query",
                "args": {"query": "Calculate salary for Q2 level", "level_code": "Q2"},
            },
            "ccnl_agreement": {"id": "ccnl_test"},
            "calculation_params": {"level_code": "Q2"},
        }

        with (
            patch("app.models.ccnl_data.CCNLAgreement"),
            patch("app.services.ccnl_calculator_engine.EnhancedCCNLCalculator") as MockCalculator,
            patch("app.orchestrators.ccnl.rag_step_log"),
        ):
            mock_calculator = MagicMock()
            mock_breakdown = MagicMock()
            mock_breakdown.gross_total = Decimal("32000.00")
            mock_breakdown.net_total = Decimal("24000.00")
            mock_calculator.calculate_comprehensive_compensation.return_value = mock_breakdown
            MockCalculator.return_value = mock_calculator

            result = await step_100__ccnlcalc(ctx=ctx)

            # Verify preparation for ToolResults step
            assert "tool_result_data" in result
            tool_data = result["tool_result_data"]
            assert tool_data["tool_type"] == "CCNL"
            assert "calculation_result" in tool_data
            assert tool_data["success"] is True

    @pytest.mark.asyncio
    async def test_end_to_end_ccnl_calculation_workflow(self):
        """Test complete workflow from query to calculation result."""
        # Complete context as would be received from routing
        complete_ctx = {
            "request_id": "e2e-test-003",
            "rag_step": 97,
            "user_query": "Calculate annual salary for Q2 level CCNL Commercio",
            "tool_call": {
                "name": "ccnl_query",
                "id": "call_123",
                "args": {"query": "Calculate salary Q2 CCNL Commercio", "level_code": "Q2", "ccnl_type": "COMMERCIO"},
            },
            "ccnl_agreement": {
                "id": "ccnl_commercio_2024",
                "sector": "COMMERCIO_TERZIARIO",
                "name": "CCNL Commercio 2024",
                "valid_from": "2024-01-01",
                "valid_until": "2026-12-31",
            },
            "calculation_params": {
                "level_code": "Q2",
                "geographic_area": "NAZIONALE",
                "company_size": "MEDIUM",
                "seniority_months": 18,
                "include_allowances": True,
                "period": "ANNUAL",
            },
            "postgres_query_results": {"agreements_found": 1, "salary_tables_matched": 1},
        }

        with (
            patch("app.models.ccnl_data.CCNLAgreement"),
            patch("app.services.ccnl_calculator_engine.EnhancedCCNLCalculator") as MockCalculator,
            patch("app.orchestrators.ccnl.rag_step_log"),
        ):
            mock_calculator = MagicMock()
            mock_breakdown = CompensationBreakdown(
                base_salary=Decimal("24000.00"),
                thirteenth_month=Decimal("2000.00"),
                fourteenth_month=Decimal("2000.00"),
                overtime=Decimal("800.00"),
                allowances={"Trasporto": Decimal("600.00")},
                deductions={"IRPEF": Decimal("4200.00")},
                gross_total=Decimal("29400.00"),
                net_total=Decimal("22200.00"),
                period=CalculationPeriod.ANNUAL,
            )
            mock_calculator.calculate_comprehensive_compensation.return_value = mock_breakdown
            MockCalculator.return_value = mock_calculator

            result = await step_100__ccnlcalc(ctx=complete_ctx)

            # Verify complete workflow result
            assert result["calculation_success"] is True
            assert result["rag_step"] == 100
            assert result["next_step"] == 99  # Routes to ToolResults

            # Verify calculation output format
            compensation = result["compensation_breakdown"]
            assert compensation["gross_total"] == Decimal("29400.00")
            assert compensation["net_total"] == Decimal("22200.00")
            assert "allowances" in compensation
            assert "deductions" in compensation

            # Verify tool result preparation
            tool_data = result["tool_result_data"]
            assert tool_data["tool_call_id"] == "call_123"
            assert tool_data["tool_type"] == "CCNL"
            assert tool_data["calculation_complete"] is True


class TestStep100CCNLCalcParity:
    """Parity tests to ensure behavioral consistency."""

    @pytest.mark.asyncio
    async def test_calculation_engine_behavior_preservation(self):
        """Verify orchestrator preserves calculation engine behavior exactly."""
        # Test that direct engine call matches orchestrated call
        test_params = {
            "level_code": "Q3",
            "seniority_months": 12,
            "geographic_area": GeographicArea.NAZIONALE,
            "company_size": CompanySize.MEDIUM,
            "working_days_per_month": 22,
            "overtime_hours_monthly": 4,
            "include_allowances": True,
            "period": CalculationPeriod.ANNUAL,
        }

        mock_agreement = MagicMock()

        with (
            patch("app.models.ccnl_data.CCNLAgreement") as MockCCNLAgreement,
            patch("app.services.ccnl_calculator_engine.EnhancedCCNLCalculator") as MockCalculator,
        ):
            MockCCNLAgreement.return_value = mock_agreement

            # Direct calculator call
            EnhancedCCNLCalculator(mock_agreement)
            direct_result = MagicMock()
            direct_result.gross_total = Decimal("33000.00")

            mock_calculator = MagicMock()
            mock_calculator.calculate_comprehensive_compensation.return_value = direct_result
            MockCalculator.return_value = mock_calculator

            # Orchestrated call
            ctx = {
                "request_id": "parity-test-001",
                "rag_step": 97,
                "ccnl_agreement": {"id": "ccnl_test"},
                "calculation_params": test_params,
            }

            orchestrated_result = await step_100__ccnlcalc(ctx=ctx)

            # Both should call the same underlying method with same parameters
            mock_calculator.calculate_comprehensive_compensation.assert_called_once()
            call_kwargs = mock_calculator.calculate_comprehensive_compensation.call_args.kwargs

            # Verify parameters match
            assert call_kwargs["level_code"] == test_params["level_code"]
            assert call_kwargs["seniority_months"] == test_params["seniority_months"]
            assert call_kwargs["working_days_per_month"] == test_params["working_days_per_month"]
            assert call_kwargs["overtime_hours_monthly"] == test_params["overtime_hours_monthly"]
            assert call_kwargs["include_allowances"] == test_params["include_allowances"]

            # Verify orchestrator doesn't modify calculation results
            assert orchestrated_result["compensation_breakdown"]["gross_total"] == direct_result.gross_total

    @pytest.mark.asyncio
    async def test_error_handling_consistency(self):
        """Verify error handling behavior matches expectations."""
        ctx = {
            "request_id": "parity-error-test",
            "rag_step": 97,
            "ccnl_agreement": {"id": "ccnl_test"},
            "calculation_params": {"level_code": "INVALID_LEVEL"},
        }

        with (
            patch("app.models.ccnl_data.CCNLAgreement"),
            patch("app.services.ccnl_calculator_engine.EnhancedCCNLCalculator") as MockCalculator,
            patch("app.orchestrators.ccnl.rag_step_log"),
        ):
            # Simulate calculation engine error
            mock_calculator = MagicMock()
            mock_calculator.calculate_comprehensive_compensation.side_effect = ValueError("Invalid level code")
            MockCalculator.return_value = mock_calculator

            result = await step_100__ccnlcalc(ctx=ctx)

            # Verify consistent error structure
            assert result["calculation_success"] is False
            assert "error" in result
            assert result["next_step"] == 99  # Should still route to ToolResults for error handling
            assert "tool_result_data" in result
            assert result["tool_result_data"]["success"] is False


if __name__ == "__main__":
    pytest.main([__file__])
