"""Tests for Financial Validation API endpoints."""

from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.financial_validation import router


@pytest.fixture
def fv_client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestTaxCalculation:
    """Tests for POST /tax/calculate."""

    def test_tax_calculation_success(self, fv_client):
        resp = fv_client.post(
            "/tax/calculate",
            json={"gross_income": 50000},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "tax_amount" in data["result_data"]
        assert data["execution_time_ms"] >= 1

    def test_tax_calculation_low_income(self, fv_client):
        resp = fv_client.post(
            "/tax/calculate",
            json={"gross_income": 10000},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_tax_calculation_high_income(self, fv_client):
        resp = fv_client.post(
            "/tax/calculate",
            json={"gross_income": 100000},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert float(data["result_data"]["effective_rate"]) > 0

    def test_tax_calculation_zero_income_returns_failure(self, fv_client):
        resp = fv_client.post(
            "/tax/calculate",
            json={"gross_income": 0},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert len(data["errors"]) > 0


class TestBusinessValuation:
    """Tests for POST /business/valuation."""

    def test_valuation_success(self, fv_client):
        resp = fv_client.post(
            "/business/valuation",
            json={
                "cash_flows": [100000, 120000, 144000],
                "discount_rate": 0.10,
                "terminal_growth_rate": 0.02,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "enterprise_value" in data["result_data"]

    def test_valuation_zero_terminal_growth(self, fv_client):
        resp = fv_client.post(
            "/business/valuation",
            json={
                "cash_flows": [50000, 60000],
                "discount_rate": 0.08,
                "terminal_growth_rate": 0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True


class TestFinancialAnalysis:
    """Tests for POST /financial/analysis."""

    def test_analysis_success(self, fv_client):
        resp = fv_client.post(
            "/financial/analysis",
            json={
                "balance_sheet": {
                    "current_assets": 500000,
                    "current_liabilities": 300000,
                    "total_assets": 2000000,
                    "shareholders_equity": 1200000,
                },
                "income_statement": {
                    "revenue": 3000000,
                    "net_income": 300000,
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_analysis_balance_only(self, fv_client):
        resp = fv_client.post(
            "/financial/analysis",
            json={
                "balance_sheet": {
                    "current_assets": 500000,
                    "current_liabilities": 200000,
                },
                "income_statement": {},
            },
        )
        assert resp.status_code == 200


class TestLaborCalculation:
    """Tests for POST /labor/calculate."""

    def test_labor_success(self, fv_client):
        resp = fv_client.post(
            "/labor/calculate",
            json={
                "gross_salary": 35000,
                "contract_type": "permanent",
                "hire_date": "2020-01-15",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "tfr_annual_accrual" in data["result_data"]
        assert "net_annual_salary" in data["result_data"]


class TestDocumentParsing:
    """Tests for POST /documents/parse."""

    def test_document_parse_success(self, fv_client):
        resp = fv_client.post(
            "/documents/parse",
            json={
                "document_path": "/path/to/file.xlsx",
                "document_type": "balance_sheet",
                "expected_format": "excel",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True


class TestValidationPipeline:
    """Tests for POST /validate/pipeline."""

    def test_pipeline_sequential(self, fv_client):
        resp = fv_client.post(
            "/validate/pipeline",
            json={
                "tasks": [
                    {
                        "task_type": "tax_calculation",
                        "input_data": {"gross_income": 50000},
                        "priority": "high",
                    },
                    {
                        "task_type": "labor_calculation",
                        "input_data": {"gross_salary": 35000},
                        "priority": "medium",
                    },
                ],
                "execution_mode": "sequential",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_success"] is True
        assert data["total_tasks"] == 2
        assert data["successful_tasks"] == 2
        assert len(data["task_results"]) == 2

    def test_pipeline_parallel(self, fv_client):
        resp = fv_client.post(
            "/validate/pipeline",
            json={
                "tasks": [
                    {
                        "task_type": "tax_calculation",
                        "input_data": {"gross_income": 30000},
                    },
                    {
                        "task_type": "document_parsing",
                        "input_data": {"path": "/test"},
                    },
                ],
                "execution_mode": "parallel",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["execution_mode"] == "parallel"

    def test_pipeline_with_request_id(self, fv_client):
        resp = fv_client.post(
            "/validate/pipeline",
            json={
                "request_id": "test-123",
                "tasks": [
                    {
                        "task_type": "document_parsing",
                        "input_data": {},
                    },
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["request_id"] == "test-123"


class TestEngineStatus:
    """Tests for GET /engine/status."""

    def test_engine_status(self, fv_client):
        resp = fv_client.get("/engine/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert "supported_task_types" in data
        assert "configuration" in data
        assert data["configuration"]["tax_calculations_enabled"] is True
        assert "health_check" in data
        assert "memory_usage_mb" in data["health_check"]

    def test_engine_status_has_all_config_fields(self, fv_client):
        resp = fv_client.get("/engine/status")
        data = resp.json()
        config = data["configuration"]
        assert "business_valuations_enabled" in config
        assert "financial_ratios_enabled" in config
        assert "labor_calculations_enabled" in config
        assert "document_parsing_enabled" in config
        assert "precision_decimal_places" in config
        assert "performance_timeout_seconds" in config
        assert "quality_threshold" in config

    def test_engine_status_health_check_has_timestamp(self, fv_client):
        resp = fv_client.get("/engine/status")
        data = resp.json()
        assert "timestamp" in data["health_check"]


class TestExceptionHandling:
    """Tests to cover except blocks in all endpoints."""

    @patch("app.api.v1.financial_validation.validation_engine")
    def test_tax_calculation_engine_error(self, mock_engine, fv_client):
        mock_engine.execute_single_task.side_effect = RuntimeError("Engine crashed")
        resp = fv_client.post("/tax/calculate", json={"gross_income": 50000})
        assert resp.status_code == 500
        assert "Tax calculation failed" in resp.json()["detail"]

    @patch("app.api.v1.financial_validation.validation_engine")
    def test_business_valuation_engine_error(self, mock_engine, fv_client):
        mock_engine.execute_single_task.side_effect = ValueError("Invalid data")
        resp = fv_client.post(
            "/business/valuation",
            json={"cash_flows": [100000], "discount_rate": 0.10},
        )
        assert resp.status_code == 500
        assert "Business valuation failed" in resp.json()["detail"]

    @patch("app.api.v1.financial_validation.validation_engine")
    def test_financial_analysis_engine_error(self, mock_engine, fv_client):
        mock_engine.execute_single_task.side_effect = Exception("Analysis error")
        resp = fv_client.post(
            "/financial/analysis",
            json={
                "balance_sheet": {"current_assets": 500000},
                "income_statement": {"revenue": 3000000},
            },
        )
        assert resp.status_code == 500
        assert "Financial analysis failed" in resp.json()["detail"]

    @patch("app.api.v1.financial_validation.validation_engine")
    def test_labor_calculation_engine_error(self, mock_engine, fv_client):
        mock_engine.execute_single_task.side_effect = RuntimeError("Labor error")
        resp = fv_client.post(
            "/labor/calculate",
            json={
                "gross_salary": 35000,
                "contract_type": "permanent",
                "hire_date": "2020-01-15",
            },
        )
        assert resp.status_code == 500
        assert "Labor calculation failed" in resp.json()["detail"]

    @patch("app.api.v1.financial_validation.validation_engine")
    def test_document_parsing_engine_error(self, mock_engine, fv_client):
        mock_engine.execute_single_task.side_effect = OSError("File not found")
        resp = fv_client.post(
            "/documents/parse",
            json={
                "document_path": "/nonexistent",
                "document_type": "balance_sheet",
                "expected_format": "excel",
            },
        )
        assert resp.status_code == 500
        assert "Document parsing failed" in resp.json()["detail"]

    @patch("app.api.v1.financial_validation.validation_engine")
    def test_pipeline_engine_error(self, mock_engine, fv_client):
        mock_engine.execute_pipeline.side_effect = RuntimeError("Pipeline failed")
        resp = fv_client.post(
            "/validate/pipeline",
            json={
                "tasks": [
                    {
                        "task_type": "tax_calculation",
                        "input_data": {"gross_income": 50000},
                    }
                ],
            },
        )
        assert resp.status_code == 500
        assert "Validation pipeline failed" in resp.json()["detail"]
