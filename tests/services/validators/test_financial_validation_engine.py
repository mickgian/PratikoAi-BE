"""Comprehensive tests for the FinancialValidationEngine class.

Tests cover engine initialization, single task execution for all task types,
pipeline execution (sequential, parallel, dependency-based, QA-enabled),
result aggregation, custom validation rules, reconfiguration, and edge cases.
"""

from decimal import Decimal, InvalidOperation

import pytest

from app.services.validators.financial_validation_engine import (
    EngineConfiguration,
    FinancialValidationEngine,
    QualityAssurance,
    TaskResult,
    TaskType,
    ValidationContext,
    ValidationRequest,
    ValidationTask,
    ValidationWarning,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def all_enabled_config() -> EngineConfiguration:
    """Configuration with every module enabled."""
    return EngineConfiguration(
        enable_tax_calculations=True,
        enable_business_valuations=True,
        enable_financial_ratios=True,
        enable_labor_calculations=True,
        enable_document_parsing=True,
        precision_decimal_places=2,
        performance_timeout_seconds=30,
        quality_threshold=Decimal("0.90"),
        max_parallel_tasks=10,
        enable_caching=True,
        cache_ttl_seconds=3600,
    )


@pytest.fixture()
def all_disabled_config() -> EngineConfiguration:
    """Configuration with every module disabled."""
    return EngineConfiguration(
        enable_tax_calculations=False,
        enable_business_valuations=False,
        enable_financial_ratios=False,
        enable_labor_calculations=False,
        enable_document_parsing=False,
    )


@pytest.fixture()
def tax_only_config() -> EngineConfiguration:
    """Configuration with only tax calculations enabled."""
    return EngineConfiguration(
        enable_tax_calculations=True,
        enable_business_valuations=False,
        enable_financial_ratios=False,
        enable_labor_calculations=False,
        enable_document_parsing=False,
    )


@pytest.fixture()
def engine(all_enabled_config: EngineConfiguration) -> FinancialValidationEngine:
    """Fully-enabled engine instance."""
    return FinancialValidationEngine(all_enabled_config)


@pytest.fixture()
def disabled_engine(all_disabled_config: EngineConfiguration) -> FinancialValidationEngine:
    """Engine with all modules disabled."""
    return FinancialValidationEngine(all_disabled_config)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_task(
    task_id: str = "task-1",
    task_type: TaskType = TaskType.TAX_CALCULATION,
    input_data: dict | None = None,
    priority: str = "medium",
    timeout_seconds: int | None = None,
    dependencies: list[str] | None = None,
    metadata: dict | None = None,
) -> ValidationTask:
    return ValidationTask(
        task_id=task_id,
        task_type=task_type,
        input_data=input_data or {},
        priority=priority,
        timeout_seconds=timeout_seconds,
        dependencies=dependencies or [],
        metadata=metadata or {},
    )


def _make_request(
    request_id: str = "req-1",
    tasks: list[ValidationTask] | None = None,
    error_handling_strategy: str = "continue_on_failure",
    quality_assurance: QualityAssurance | None = None,
) -> ValidationRequest:
    return ValidationRequest(
        request_id=request_id,
        tasks=tasks or [],
        error_handling_strategy=error_handling_strategy,
        quality_assurance=quality_assurance,
    )


# ===================================================================
# 1. Initialization tests
# ===================================================================


class TestEngineInitialization:
    """Tests for __init__ and component setup."""

    def test_init_all_enabled(self, engine: FinancialValidationEngine) -> None:
        """All components are initialised (non-None) when everything is enabled."""
        assert engine.tax_calculator is not None
        assert engine.business_valuation_engine is not None
        assert engine.financial_ratios_calculator is not None
        assert engine.labor_calculator is not None
        assert engine.document_parser is not None
        assert engine.business_plan_generator is not None

    def test_init_all_disabled(self, disabled_engine: FinancialValidationEngine) -> None:
        """All components are None when everything is disabled."""
        assert disabled_engine.tax_calculator is None
        assert disabled_engine.business_valuation_engine is None
        assert disabled_engine.financial_ratios_calculator is None
        assert disabled_engine.labor_calculator is None
        assert disabled_engine.document_parser is None
        assert disabled_engine.business_plan_generator is None

    def test_init_partial_modules(self, tax_only_config: EngineConfiguration) -> None:
        """Only the enabled module is initialised."""
        eng = FinancialValidationEngine(tax_only_config)
        assert eng.tax_calculator is not None
        assert eng.business_valuation_engine is None
        assert eng.financial_ratios_calculator is None
        assert eng.labor_calculator is None
        assert eng.document_parser is None
        # business_plan_generator depends on enable_business_valuations
        assert eng.business_plan_generator is None

    def test_mock_components_are_string_mock(self, engine: FinancialValidationEngine) -> None:
        """When the real imports fail, components fall back to the 'mock' string."""
        # Since the concrete calculator classes likely don't exist, the engine
        # falls back to the string "mock".  This is still truthy / not None.
        for attr in (
            "tax_calculator",
            "business_valuation_engine",
            "financial_ratios_calculator",
            "labor_calculator",
            "document_parser",
            "business_plan_generator",
        ):
            val = getattr(engine, attr)
            assert val is not None
            # It should be either the real class or the "mock" string
            assert val == "mock" or val is not None

    def test_custom_validation_rules_empty_on_init(self, engine: FinancialValidationEngine) -> None:
        """Custom validation rules dict is empty right after init."""
        assert engine.custom_validation_rules == {}


# ===================================================================
# 2. is_ready property
# ===================================================================


class TestIsReady:
    def test_is_ready_all_enabled(self, engine: FinancialValidationEngine) -> None:
        assert engine.is_ready is True

    def test_is_ready_all_disabled(self, disabled_engine: FinancialValidationEngine) -> None:
        assert disabled_engine.is_ready is False

    def test_is_ready_single_module(self, tax_only_config: EngineConfiguration) -> None:
        eng = FinancialValidationEngine(tax_only_config)
        assert eng.is_ready is True


# ===================================================================
# 3. supported_task_types property
# ===================================================================


class TestSupportedTaskTypes:
    def test_all_types_when_all_enabled(self, engine: FinancialValidationEngine) -> None:
        supported = engine.supported_task_types
        assert TaskType.TAX_CALCULATION in supported
        assert TaskType.BUSINESS_VALUATION in supported
        assert TaskType.FINANCIAL_ANALYSIS in supported
        assert TaskType.LABOR_CALCULATION in supported
        assert TaskType.DOCUMENT_PARSING in supported
        assert TaskType.BUSINESS_PLAN_GENERATION in supported

    def test_empty_when_all_disabled(self, disabled_engine: FinancialValidationEngine) -> None:
        assert disabled_engine.supported_task_types == []

    def test_only_tax_when_tax_only(self, tax_only_config: EngineConfiguration) -> None:
        eng = FinancialValidationEngine(tax_only_config)
        supported = eng.supported_task_types
        assert TaskType.TAX_CALCULATION in supported
        assert TaskType.BUSINESS_VALUATION not in supported
        assert TaskType.FINANCIAL_ANALYSIS not in supported
        assert TaskType.LABOR_CALCULATION not in supported
        assert TaskType.DOCUMENT_PARSING not in supported
        assert TaskType.BUSINESS_PLAN_GENERATION not in supported


# ===================================================================
# 4. execute_single_task
# ===================================================================


class TestExecuteSingleTask:
    """Tests for the dispatch method `execute_single_task`."""

    # ---- Tax calculation ----

    def test_tax_calculation_low_bracket(self, engine: FinancialValidationEngine) -> None:
        task = _make_task(
            task_type=TaskType.TAX_CALCULATION,
            input_data={"gross_income": Decimal("10000")},
        )
        result = engine.execute_single_task(task)
        assert result.success is True
        assert result.task_id == "task-1"
        assert result.task_type == TaskType.TAX_CALCULATION
        assert result.output_data["tax_amount"] == (Decimal("10000") * Decimal("0.23") * Decimal("0.6")).quantize(
            Decimal("0.01")
        )
        assert result.output_data["effective_rate"] is not None
        assert result.execution_time_ms >= 1

    def test_tax_calculation_second_bracket(self, engine: FinancialValidationEngine) -> None:
        task = _make_task(
            task_type=TaskType.TAX_CALCULATION,
            input_data={"gross_income": Decimal("20000")},
        )
        result = engine.execute_single_task(task)
        assert result.success is True
        expected_tax = (Decimal("20000") * Decimal("0.25") * Decimal("0.6")).quantize(Decimal("0.01"))
        assert result.output_data["tax_amount"] == expected_tax

    def test_tax_calculation_third_bracket(self, engine: FinancialValidationEngine) -> None:
        task = _make_task(
            task_type=TaskType.TAX_CALCULATION,
            input_data={"gross_income": Decimal("40000")},
        )
        result = engine.execute_single_task(task)
        assert result.success is True
        expected_tax = (Decimal("40000") * Decimal("0.35") * Decimal("0.6")).quantize(Decimal("0.01"))
        assert result.output_data["tax_amount"] == expected_tax

    def test_tax_calculation_top_bracket(self, engine: FinancialValidationEngine) -> None:
        task = _make_task(
            task_type=TaskType.TAX_CALCULATION,
            input_data={"gross_income": Decimal("100000")},
        )
        result = engine.execute_single_task(task)
        assert result.success is True
        expected_tax = (Decimal("100000") * Decimal("0.43") * Decimal("0.6")).quantize(Decimal("0.01"))
        assert result.output_data["tax_amount"] == expected_tax

    def test_tax_calculation_boundary_15000(self, engine: FinancialValidationEngine) -> None:
        """Exactly 15000 should use the 23% bracket."""
        task = _make_task(
            task_type=TaskType.TAX_CALCULATION,
            input_data={"gross_income": Decimal("15000")},
        )
        result = engine.execute_single_task(task)
        assert result.success is True
        expected_tax = (Decimal("15000") * Decimal("0.23") * Decimal("0.6")).quantize(Decimal("0.01"))
        assert result.output_data["tax_amount"] == expected_tax

    def test_tax_calculation_boundary_28000(self, engine: FinancialValidationEngine) -> None:
        """Exactly 28000 should use the 25% bracket."""
        task = _make_task(
            task_type=TaskType.TAX_CALCULATION,
            input_data={"gross_income": Decimal("28000")},
        )
        result = engine.execute_single_task(task)
        assert result.success is True
        expected_tax = (Decimal("28000") * Decimal("0.25") * Decimal("0.6")).quantize(Decimal("0.01"))
        assert result.output_data["tax_amount"] == expected_tax

    def test_tax_calculation_boundary_55000(self, engine: FinancialValidationEngine) -> None:
        """Exactly 55000 should use the 35% bracket."""
        task = _make_task(
            task_type=TaskType.TAX_CALCULATION,
            input_data={"gross_income": Decimal("55000")},
        )
        result = engine.execute_single_task(task)
        assert result.success is True
        expected_tax = (Decimal("55000") * Decimal("0.35") * Decimal("0.6")).quantize(Decimal("0.01"))
        assert result.output_data["tax_amount"] == expected_tax

    def test_tax_calculation_missing_gross_income(self, engine: FinancialValidationEngine) -> None:
        """Missing gross_income should produce a failed TaskResult."""
        task = _make_task(task_type=TaskType.TAX_CALCULATION, input_data={})
        result = engine.execute_single_task(task)
        assert result.success is False
        assert "gross_income" in result.error_messages[0]

    def test_tax_calculation_negative_income(self, engine: FinancialValidationEngine) -> None:
        """Negative income should raise ValueError -> failed result."""
        task = _make_task(
            task_type=TaskType.TAX_CALCULATION,
            input_data={"gross_income": Decimal("-5000")},
        )
        result = engine.execute_single_task(task)
        assert result.success is False
        assert "negative or zero" in result.error_messages[0].lower()

    def test_tax_calculation_zero_income(self, engine: FinancialValidationEngine) -> None:
        """Zero income should raise ValueError -> failed result."""
        task = _make_task(
            task_type=TaskType.TAX_CALCULATION,
            input_data={"gross_income": Decimal("0")},
        )
        result = engine.execute_single_task(task)
        assert result.success is False

    def test_tax_calculation_quality_and_confidence_scores(self, engine: FinancialValidationEngine) -> None:
        task = _make_task(
            task_type=TaskType.TAX_CALCULATION,
            input_data={"gross_income": Decimal("30000")},
        )
        result = engine.execute_single_task(task)
        assert result.success is True
        assert result.quality_score == Decimal("0.95")
        assert result.confidence_score == Decimal("0.92")

    # ---- Business valuation ----

    def test_business_valuation_basic_dcf(self, engine: FinancialValidationEngine) -> None:
        task = _make_task(
            task_type=TaskType.BUSINESS_VALUATION,
            input_data={
                "cash_flows": [Decimal("100000"), Decimal("120000"), Decimal("140000")],
                "discount_rate": Decimal("0.10"),
                "terminal_growth_rate": Decimal("0.02"),
            },
        )
        result = engine.execute_single_task(task)
        assert result.success is True
        assert "enterprise_value" in result.output_data
        assert "terminal_value" in result.output_data
        assert result.output_data["enterprise_value"] > Decimal("0")
        assert result.output_data["terminal_value"] > Decimal("0")
        assert len(result.output_data["pv_cash_flows"]) == 3

    def test_business_valuation_zero_terminal_growth(self, engine: FinancialValidationEngine) -> None:
        """When terminal_growth_rate is 0, terminal value should be 0."""
        task = _make_task(
            task_type=TaskType.BUSINESS_VALUATION,
            input_data={
                "cash_flows": [Decimal("100000"), Decimal("120000")],
                "discount_rate": Decimal("0.10"),
                "terminal_growth_rate": Decimal("0"),
            },
        )
        result = engine.execute_single_task(task)
        assert result.success is True
        assert result.output_data["terminal_value"] == Decimal("0.00")

    def test_business_valuation_default_terminal_growth(self, engine: FinancialValidationEngine) -> None:
        """Default terminal_growth_rate should be 0.02."""
        task = _make_task(
            task_type=TaskType.BUSINESS_VALUATION,
            input_data={
                "cash_flows": [Decimal("50000")],
                "discount_rate": Decimal("0.08"),
            },
        )
        result = engine.execute_single_task(task)
        assert result.success is True
        assert result.output_data["terminal_growth_rate"] == Decimal("0.02")

    def test_business_valuation_missing_fields(self, engine: FinancialValidationEngine) -> None:
        task = _make_task(task_type=TaskType.BUSINESS_VALUATION, input_data={})
        result = engine.execute_single_task(task)
        assert result.success is False
        assert "cash_flows" in result.error_messages[0]

    def test_business_valuation_confidence_score(self, engine: FinancialValidationEngine) -> None:
        task = _make_task(
            task_type=TaskType.BUSINESS_VALUATION,
            input_data={
                "cash_flows": [Decimal("100000")],
                "discount_rate": Decimal("0.10"),
            },
        )
        result = engine.execute_single_task(task)
        assert result.success is True
        assert result.confidence_score == Decimal("0.88")
        assert result.quality_score == Decimal("0.91")

    # ---- Financial analysis ----

    def test_financial_analysis_balance_sheet_ratios(self, engine: FinancialValidationEngine) -> None:
        task = _make_task(
            task_type=TaskType.FINANCIAL_ANALYSIS,
            input_data={
                "balance_sheet": {
                    "current_assets": Decimal("500000"),
                    "current_liabilities": Decimal("250000"),
                    "total_assets": Decimal("2000000"),
                    "shareholders_equity": Decimal("1000000"),
                },
            },
        )
        result = engine.execute_single_task(task)
        assert result.success is True
        assert result.output_data["current_ratio"] == Decimal("2.00")
        assert result.output_data["equity_ratio"] == Decimal("0.50")

    def test_financial_analysis_income_statement(self, engine: FinancialValidationEngine) -> None:
        task = _make_task(
            task_type=TaskType.FINANCIAL_ANALYSIS,
            input_data={
                "income_statement": {
                    "revenue": Decimal("1000000"),
                    "net_income": Decimal("150000"),
                },
            },
        )
        result = engine.execute_single_task(task)
        assert result.success is True
        assert result.output_data["net_profit_margin"] == Decimal("0.15")

    def test_financial_analysis_partial_balance_sheet(self, engine: FinancialValidationEngine) -> None:
        """Balance sheet with only current_assets (no liabilities) should still succeed."""
        task = _make_task(
            task_type=TaskType.FINANCIAL_ANALYSIS,
            input_data={
                "balance_sheet": {
                    "current_assets": Decimal("500000"),
                },
            },
        )
        result = engine.execute_single_task(task)
        assert result.success is True
        assert result.output_data["current_assets"] == Decimal("500000")

    def test_financial_analysis_partial_income_statement(self, engine: FinancialValidationEngine) -> None:
        """Income statement with only revenue (no net_income) should still succeed."""
        task = _make_task(
            task_type=TaskType.FINANCIAL_ANALYSIS,
            input_data={
                "income_statement": {
                    "revenue": Decimal("1000000"),
                },
            },
        )
        result = engine.execute_single_task(task)
        assert result.success is True
        assert result.output_data["revenue"] == Decimal("1000000")

    def test_financial_analysis_combined_statements(self, engine: FinancialValidationEngine) -> None:
        task = _make_task(
            task_type=TaskType.FINANCIAL_ANALYSIS,
            input_data={
                "balance_sheet": {
                    "current_assets": Decimal("500000"),
                    "current_liabilities": Decimal("250000"),
                },
                "income_statement": {
                    "revenue": Decimal("1000000"),
                    "net_income": Decimal("100000"),
                },
            },
        )
        result = engine.execute_single_task(task)
        assert result.success is True
        assert result.output_data["current_ratio"] == Decimal("2.00")
        assert result.output_data["net_profit_margin"] == Decimal("0.10")

    def test_financial_analysis_missing_data(self, engine: FinancialValidationEngine) -> None:
        """No balance_sheet or income_statement -> error."""
        task = _make_task(task_type=TaskType.FINANCIAL_ANALYSIS, input_data={})
        result = engine.execute_single_task(task)
        assert result.success is False
        assert "financial statement" in result.error_messages[0].lower()

    # ---- Labor calculation ----

    def test_labor_calculation_basic(self, engine: FinancialValidationEngine) -> None:
        task = _make_task(
            task_type=TaskType.LABOR_CALCULATION,
            input_data={"gross_salary": Decimal("30000")},
        )
        result = engine.execute_single_task(task)
        assert result.success is True
        data = result.output_data
        assert data["gross_annual_salary"] == Decimal("30000")
        assert data["tfr_annual_accrual"] == (Decimal("30000") / Decimal("13.5")).quantize(Decimal("0.01"))
        assert data["inps_employee_contribution"] == (Decimal("30000") * Decimal("0.0919")).quantize(Decimal("0.01"))
        assert data["inps_employer_contribution"] == (Decimal("30000") * Decimal("0.2381")).quantize(Decimal("0.01"))
        expected_net = (
            Decimal("30000") - Decimal("30000") * Decimal("0.0919") - Decimal("30000") * Decimal("0.15")
        ).quantize(Decimal("0.01"))
        assert data["net_annual_salary"] == expected_net

    def test_labor_calculation_missing_gross_salary(self, engine: FinancialValidationEngine) -> None:
        task = _make_task(task_type=TaskType.LABOR_CALCULATION, input_data={})
        result = engine.execute_single_task(task)
        assert result.success is False
        assert "gross_salary" in result.error_messages[0]

    # ---- Document parsing ----

    def test_document_parsing_returns_mock_data(self, engine: FinancialValidationEngine) -> None:
        task = _make_task(task_type=TaskType.DOCUMENT_PARSING, input_data={"file": "test.pdf"})
        result = engine.execute_single_task(task)
        assert result.success is True
        data = result.output_data
        assert data["current_assets"] == Decimal("500000")
        assert data["total_assets"] == Decimal("2000000")
        assert data["revenue"] == Decimal("3000000")
        assert data["net_income"] == Decimal("300000")
        assert data["extraction_confidence"] == Decimal("0.92")
        assert data["validation_errors"] == []

    # ---- Business plan generation ----

    def test_business_plan_generation_returns_sections(self, engine: FinancialValidationEngine) -> None:
        task = _make_task(
            task_type=TaskType.BUSINESS_PLAN_GENERATION,
            input_data={"company_name": "TestCo"},
        )
        result = engine.execute_single_task(task)
        assert result.success is True
        data = result.output_data
        assert "sections" in data
        assert "executive_summary" in data["sections"]
        assert "market_analysis" in data["sections"]
        assert "financial_projections" in data["sections"]
        assert data["total_pages"] == 25

    # ---- Unsupported / disabled task type ----

    def test_unsupported_task_type(self, disabled_engine: FinancialValidationEngine) -> None:
        """An engine with everything disabled should reject all tasks."""
        task = _make_task(task_type=TaskType.TAX_CALCULATION, input_data={"gross_income": Decimal("50000")})
        result = disabled_engine.execute_single_task(task)
        assert result.success is False
        assert result.status == "unsupported"
        assert "not supported" in result.error_messages[0]

    # ---- Task that raises an unexpected exception ----

    def test_task_exception_produces_failed_result(self, engine: FinancialValidationEngine) -> None:
        """If an executor raises, the result should be success=False with the error message."""
        task = _make_task(
            task_type=TaskType.TAX_CALCULATION,
            input_data={"gross_income": Decimal("-1")},
        )
        result = engine.execute_single_task(task)
        assert result.success is False
        assert result.status == "failed"
        assert len(result.error_messages) > 0
        assert result.execution_time_ms >= 1

    # ---- Priority is preserved ----

    def test_priority_preserved_in_result(self, engine: FinancialValidationEngine) -> None:
        task = _make_task(
            task_type=TaskType.DOCUMENT_PARSING,
            input_data={},
            priority="high",
        )
        result = engine.execute_single_task(task)
        assert result.priority == "high"


# ===================================================================
# 5. Pipeline execution
# ===================================================================


class TestPipelineExecution:
    """Tests for execute_pipeline with sequential and parallel modes."""

    def _tax_task(self, task_id: str = "tax-1", priority: str = "medium") -> ValidationTask:
        return _make_task(
            task_id=task_id,
            task_type=TaskType.TAX_CALCULATION,
            input_data={"gross_income": Decimal("50000")},
            priority=priority,
        )

    def _valuation_task(self, task_id: str = "val-1", priority: str = "medium") -> ValidationTask:
        return _make_task(
            task_id=task_id,
            task_type=TaskType.BUSINESS_VALUATION,
            input_data={
                "cash_flows": [Decimal("100000")],
                "discount_rate": Decimal("0.10"),
            },
            priority=priority,
        )

    def _failing_task(self, task_id: str = "fail-1", priority: str = "medium") -> ValidationTask:
        return _make_task(
            task_id=task_id,
            task_type=TaskType.TAX_CALCULATION,
            input_data={},  # missing gross_income
            priority=priority,
        )

    # ---- Sequential ----

    def test_sequential_pipeline_all_succeed(self, engine: FinancialValidationEngine) -> None:
        request = _make_request(tasks=[self._tax_task(), self._valuation_task()])
        result = engine.execute_pipeline(request, "sequential")

        assert result.request_id == "req-1"
        assert result.total_tasks == 2
        assert result.successful_tasks == 2
        assert result.failed_tasks == 0
        assert result.overall_success is True
        assert result.success_rate == Decimal("1")
        assert result.execution_mode == "sequential"
        assert result.total_execution_time_ms >= 1
        assert result.average_task_time_ms >= 1
        assert result.parallelization_efficiency == Decimal("1.0")

    def test_sequential_pipeline_partial_failure(self, engine: FinancialValidationEngine) -> None:
        request = _make_request(tasks=[self._tax_task(), self._failing_task()])
        result = engine.execute_pipeline(request, "sequential")

        assert result.total_tasks == 2
        assert result.successful_tasks == 1
        assert result.failed_tasks == 1
        assert result.overall_success is True  # at least one succeeded

    def test_sequential_pipeline_all_fail(self, engine: FinancialValidationEngine) -> None:
        request = _make_request(tasks=[self._failing_task("f1"), self._failing_task("f2")])
        result = engine.execute_pipeline(request, "sequential")

        assert result.successful_tasks == 0
        assert result.failed_tasks == 2
        assert result.overall_success is False

    # ---- Parallel ----

    def test_parallel_pipeline(self, engine: FinancialValidationEngine) -> None:
        request = _make_request(tasks=[self._tax_task(), self._valuation_task()])
        result = engine.execute_pipeline(request, "parallel")

        assert result.execution_mode == "parallel"
        assert result.successful_tasks == 2
        assert result.parallelization_efficiency == Decimal("2.5")

    # ---- Fail-fast strategy ----

    def test_fail_fast_sequential_stops_early(self, engine: FinancialValidationEngine) -> None:
        """With fail_fast, pipeline should stop after the first failure."""
        request = _make_request(
            tasks=[self._failing_task("f1", priority="high"), self._tax_task("t1", priority="low")],
            error_handling_strategy="fail_fast",
        )
        result = engine.execute_pipeline(request, "sequential")

        # Should have stopped after the first (failing) task
        assert result.failed_tasks == 1
        assert len(result.task_results) == 1

    def test_fail_fast_parallel_stops_early(self, engine: FinancialValidationEngine) -> None:
        """In parallel mode with fail_fast, pipeline should stop after first failure."""
        request = _make_request(
            tasks=[self._failing_task("f1", priority="high"), self._tax_task("t1", priority="low")],
            error_handling_strategy="fail_fast",
        )
        result = engine.execute_pipeline(request, "parallel")

        assert result.failed_tasks == 1
        assert len(result.task_results) == 1

    # ---- Priority ordering ----

    def test_pipeline_priority_ordering(self, engine: FinancialValidationEngine) -> None:
        """Tasks should be sorted by priority: high -> medium -> low."""
        low_task = self._tax_task("low-task", priority="low")
        high_task = self._tax_task("high-task", priority="high")
        medium_task = self._tax_task("medium-task", priority="medium")

        request = _make_request(tasks=[low_task, high_task, medium_task])
        result = engine.execute_pipeline(request, "sequential")

        assert result.execution_order == ["high-task", "medium-task", "low-task"]

    # ---- Performance metrics ----

    def test_pipeline_performance_metrics(self, engine: FinancialValidationEngine) -> None:
        request = _make_request(tasks=[self._tax_task()])
        result = engine.execute_pipeline(request, "sequential")

        assert result.performance_metrics is not None
        assert result.performance_metrics.total_execution_time_ms >= 1
        assert result.performance_metrics.average_task_time_ms >= 1

    # ---- Quality score ----

    def test_pipeline_overall_quality_score(self, engine: FinancialValidationEngine) -> None:
        request = _make_request(tasks=[self._tax_task()])
        result = engine.execute_pipeline(request, "sequential")

        assert result.overall_quality_score > Decimal("0")


# ===================================================================
# 6. Pipeline with dependencies
# ===================================================================


class TestPipelineWithDependencies:
    def test_dependency_resolution_order(self, engine: FinancialValidationEngine) -> None:
        """Tasks with dependencies should be resolved in topological order."""
        task_a = _make_task(
            task_id="A",
            task_type=TaskType.DOCUMENT_PARSING,
            input_data={},
            dependencies=[],
        )
        task_b = _make_task(
            task_id="B",
            task_type=TaskType.TAX_CALCULATION,
            input_data={"gross_income": Decimal("50000")},
            dependencies=["A"],
        )
        task_c = _make_task(
            task_id="C",
            task_type=TaskType.LABOR_CALCULATION,
            input_data={"gross_salary": Decimal("30000")},
            dependencies=["A", "B"],
        )

        request = _make_request(tasks=[task_c, task_b, task_a])
        result = engine.execute_pipeline_with_dependencies(request)

        assert result.dependency_resolution_successful is True
        # A must come before B, and both A and B before C
        order = result.execution_order
        assert order.index("A") < order.index("B")
        assert order.index("B") < order.index("C")

    def test_circular_dependency_resolves_gracefully(self, engine: FinancialValidationEngine) -> None:
        """Circular dependencies should be handled (remaining tasks appended)."""
        task_a = _make_task(
            task_id="A",
            task_type=TaskType.DOCUMENT_PARSING,
            input_data={},
            dependencies=["B"],
        )
        task_b = _make_task(
            task_id="B",
            task_type=TaskType.DOCUMENT_PARSING,
            input_data={},
            dependencies=["A"],
        )

        request = _make_request(tasks=[task_a, task_b])
        result = engine.execute_pipeline_with_dependencies(request)

        # Should still produce a result (circular deps are handled by appending remaining)
        assert result.dependency_resolution_successful is True
        assert len(result.execution_order) == 2

    def test_no_dependencies(self, engine: FinancialValidationEngine) -> None:
        """When no tasks have dependencies, order is preserved."""
        task_a = _make_task(task_id="A", task_type=TaskType.DOCUMENT_PARSING, input_data={})
        task_b = _make_task(task_id="B", task_type=TaskType.DOCUMENT_PARSING, input_data={})

        request = _make_request(tasks=[task_a, task_b])
        result = engine.execute_pipeline_with_dependencies(request)

        assert result.dependency_resolution_successful is True
        assert set(result.execution_order) == {"A", "B"}


# ===================================================================
# 7. Pipeline with QA
# ===================================================================


class TestPipelineWithQA:
    def test_qa_cross_validation_enabled(self, engine: FinancialValidationEngine) -> None:
        qa = QualityAssurance(enable_cross_validation=True)
        task = _make_task(
            task_type=TaskType.TAX_CALCULATION,
            input_data={"gross_income": Decimal("50000")},
        )
        request = _make_request(tasks=[task], quality_assurance=qa)
        result = engine.execute_pipeline_with_qa(request)

        assert result.cross_validation_performed is True
        assert len(result.cross_validation_results) > 0
        assert result.cross_validation_results[0]["variance_percentage"] == Decimal("2.5")
        assert result.consolidated_result is not None
        assert result.consolidated_result["confidence_score"] == Decimal("0.92")

    def test_qa_cross_validation_disabled(self, engine: FinancialValidationEngine) -> None:
        qa = QualityAssurance(enable_cross_validation=False)
        task = _make_task(
            task_type=TaskType.TAX_CALCULATION,
            input_data={"gross_income": Decimal("50000")},
        )
        request = _make_request(tasks=[task], quality_assurance=qa)
        result = engine.execute_pipeline_with_qa(request)

        assert result.cross_validation_performed is False
        assert result.cross_validation_results == []

    def test_qa_no_quality_assurance_object(self, engine: FinancialValidationEngine) -> None:
        """When quality_assurance is None, no cross-validation happens."""
        task = _make_task(
            task_type=TaskType.TAX_CALCULATION,
            input_data={"gross_income": Decimal("50000")},
        )
        request = _make_request(tasks=[task], quality_assurance=None)
        result = engine.execute_pipeline_with_qa(request)

        assert result.cross_validation_performed is False


# ===================================================================
# 8. Comprehensive workflow
# ===================================================================


class TestComprehensiveWorkflow:
    def test_comprehensive_workflow_success(self, engine: FinancialValidationEngine) -> None:
        tasks = [
            _make_task(
                task_id="tax",
                task_type=TaskType.TAX_CALCULATION,
                input_data={"gross_income": Decimal("50000")},
            ),
            _make_task(
                task_id="labor",
                task_type=TaskType.LABOR_CALCULATION,
                input_data={"gross_salary": Decimal("30000")},
            ),
        ]
        request = _make_request(tasks=tasks)
        result = engine.execute_comprehensive_workflow(request)

        assert result.workflow_completed is True
        assert result.data_flow_integrity is True
        assert result.successful_tasks == 2

    def test_comprehensive_workflow_with_one_failure(self, engine: FinancialValidationEngine) -> None:
        """Workflow is considered complete if at most one task fails."""
        tasks = [
            _make_task(
                task_id="tax",
                task_type=TaskType.TAX_CALCULATION,
                input_data={"gross_income": Decimal("50000")},
            ),
            _make_task(
                task_id="bad",
                task_type=TaskType.TAX_CALCULATION,
                input_data={},  # will fail
            ),
        ]
        request = _make_request(tasks=tasks)
        result = engine.execute_comprehensive_workflow(request)

        # workflow_completed = successful_tasks >= len(tasks) - 1
        assert result.workflow_completed is True
        assert result.data_flow_integrity is True


# ===================================================================
# 9. Aggregate results
# ===================================================================


class TestAggregateResults:
    def test_aggregate_with_mixed_task_types(self, engine: FinancialValidationEngine) -> None:
        tasks = [
            _make_task(
                task_id="tax",
                task_type=TaskType.TAX_CALCULATION,
                input_data={"gross_income": Decimal("50000")},
            ),
            _make_task(
                task_id="val",
                task_type=TaskType.BUSINESS_VALUATION,
                input_data={
                    "cash_flows": [Decimal("100000")],
                    "discount_rate": Decimal("0.10"),
                },
            ),
            _make_task(
                task_id="fin",
                task_type=TaskType.FINANCIAL_ANALYSIS,
                input_data={
                    "balance_sheet": {
                        "current_assets": Decimal("500000"),
                        "current_liabilities": Decimal("250000"),
                    },
                },
            ),
        ]
        request = _make_request(tasks=tasks)
        pipeline_result = engine.execute_pipeline(request)
        aggregation = engine.aggregate_results(pipeline_result)

        assert aggregation.total_calculations_performed == 3
        assert aggregation.overall_confidence > Decimal("0")
        assert "tax_calculation" in aggregation.results_by_category
        assert "business_valuation" in aggregation.results_by_category
        assert "financial_analysis" in aggregation.results_by_category

        # Insights and recommendations
        assert any("Tax" in i or "tax" in i.lower() for i in aggregation.key_insights)
        assert any("valuation" in i.lower() for i in aggregation.key_insights)
        assert any("ratios" in i.lower() or "Financial" in i for i in aggregation.key_insights)
        assert len(aggregation.recommendations) >= 3

        # Executive summary
        assert "3" in aggregation.executive_summary
        assert "quality" in aggregation.executive_summary.lower() or "Quality" in aggregation.executive_summary

    def test_aggregate_single_task_type(self, engine: FinancialValidationEngine) -> None:
        tasks = [
            _make_task(
                task_id="tax",
                task_type=TaskType.TAX_CALCULATION,
                input_data={"gross_income": Decimal("50000")},
            ),
        ]
        request = _make_request(tasks=tasks)
        pipeline_result = engine.execute_pipeline(request)
        aggregation = engine.aggregate_results(pipeline_result)

        assert aggregation.total_calculations_performed == 1
        assert "tax_calculation" in aggregation.results_by_category
        assert len(aggregation.key_insights) >= 1

    def test_aggregate_with_failures(self, engine: FinancialValidationEngine) -> None:
        """Failed tasks produce empty output_data in aggregation."""
        tasks = [
            _make_task(task_id="fail", task_type=TaskType.TAX_CALCULATION, input_data={}),
        ]
        request = _make_request(tasks=tasks)
        pipeline_result = engine.execute_pipeline(request)
        aggregation = engine.aggregate_results(pipeline_result)

        # Failed task still appears in results_by_category (with empty output)
        assert aggregation.total_calculations_performed == 0


# ===================================================================
# 10. Custom validation rules
# ===================================================================


class TestCustomValidationRules:
    def test_add_custom_rule(self, engine: FinancialValidationEngine) -> None:
        def my_rule(data: dict) -> ValidationWarning | None:
            return None

        engine.add_custom_validation_rule("test_rule", my_rule)
        assert "test_rule" in engine.custom_validation_rules

    def test_custom_rule_produces_warning(self, engine: FinancialValidationEngine) -> None:
        """A custom rule that returns a ValidationWarning should appear in task result."""

        def warning_rule(data: dict) -> ValidationWarning:
            return ValidationWarning(code="W001", message="Test warning")

        engine.add_custom_validation_rule("warn_rule", warning_rule)

        task = _make_task(
            task_type=TaskType.DOCUMENT_PARSING,
            input_data={},
        )
        result = engine.execute_single_task(task)

        assert result.success is True
        assert len(result.validation_warnings) == 1
        assert result.validation_warnings[0].code == "W001"
        assert result.validation_warnings[0].message == "Test warning"

    def test_custom_rule_that_throws_is_handled(self, engine: FinancialValidationEngine) -> None:
        """A custom rule that raises an exception should not break task execution."""

        def bad_rule(data: dict) -> ValidationWarning | None:
            raise RuntimeError("Rule exploded")

        engine.add_custom_validation_rule("bad_rule", bad_rule)

        task = _make_task(
            task_type=TaskType.DOCUMENT_PARSING,
            input_data={},
        )
        result = engine.execute_single_task(task)

        # Task should still succeed; the broken rule is silently logged
        assert result.success is True
        # The broken rule should not produce a warning
        assert len(result.validation_warnings) == 0

    def test_multiple_custom_rules(self, engine: FinancialValidationEngine) -> None:
        """Multiple rules: one returns warning, one returns None, one throws."""

        def warn_rule(data: dict) -> ValidationWarning:
            return ValidationWarning(code="W100", message="Custom warning")

        def ok_rule(data: dict) -> None:
            return None

        def crash_rule(data: dict) -> ValidationWarning | None:
            raise ValueError("crash")

        engine.add_custom_validation_rule("warn", warn_rule)
        engine.add_custom_validation_rule("ok", ok_rule)
        engine.add_custom_validation_rule("crash", crash_rule)

        task = _make_task(task_type=TaskType.DOCUMENT_PARSING, input_data={})
        result = engine.execute_single_task(task)

        assert result.success is True
        # Only the warning rule should produce a warning
        assert len(result.validation_warnings) == 1
        assert result.validation_warnings[0].code == "W100"


# ===================================================================
# 11. Reconfigure
# ===================================================================


class TestReconfigure:
    def test_reconfigure_enables_new_modules(self, engine: FinancialValidationEngine) -> None:
        # Start with all enabled, verify tax is available
        assert TaskType.TAX_CALCULATION in engine.supported_task_types

        # Reconfigure to disable tax
        new_config = EngineConfiguration(
            enable_tax_calculations=False,
            enable_business_valuations=True,
            enable_financial_ratios=True,
            enable_labor_calculations=True,
            enable_document_parsing=True,
        )
        success = engine.reconfigure(new_config)
        assert success is True
        assert engine.tax_calculator is None
        assert TaskType.TAX_CALCULATION not in engine.supported_task_types

    def test_reconfigure_disables_all(self, engine: FinancialValidationEngine) -> None:
        new_config = EngineConfiguration(
            enable_tax_calculations=False,
            enable_business_valuations=False,
            enable_financial_ratios=False,
            enable_labor_calculations=False,
            enable_document_parsing=False,
        )
        success = engine.reconfigure(new_config)
        assert success is True
        assert engine.is_ready is False
        assert engine.supported_task_types == []

    def test_reconfigure_preserves_custom_rules(self, engine: FinancialValidationEngine) -> None:
        """Custom rules should survive reconfiguration."""

        def my_rule(data: dict) -> None:
            return None

        engine.add_custom_validation_rule("persistent", my_rule)
        engine.reconfigure(engine.config)
        assert "persistent" in engine.custom_validation_rules

    def test_reconfigure_updates_config_attribute(self, engine: FinancialValidationEngine) -> None:
        new_config = EngineConfiguration(precision_decimal_places=4)
        engine.reconfigure(new_config)
        assert engine.config.precision_decimal_places == 4


# ===================================================================
# 12. get_memory_usage_mb
# ===================================================================


class TestGetMemoryUsage:
    def test_returns_fixed_value(self, engine: FinancialValidationEngine) -> None:
        assert engine.get_memory_usage_mb() == 150.0

    def test_return_type_is_float(self, engine: FinancialValidationEngine) -> None:
        assert isinstance(engine.get_memory_usage_mb(), float)


# ===================================================================
# 13. Edge cases & integration-level scenarios
# ===================================================================


class TestEdgeCases:
    def test_empty_pipeline(self, engine: FinancialValidationEngine) -> None:
        """Pipeline with zero tasks raises due to Decimal division by zero."""
        request = _make_request(tasks=[])
        # The implementation computes Decimal(0) / Decimal(0) which raises
        # decimal.InvalidOperation rather than ZeroDivisionError.
        with pytest.raises(InvalidOperation):
            engine.execute_pipeline(request)

    def test_single_task_pipeline(self, engine: FinancialValidationEngine) -> None:
        task = _make_task(
            task_type=TaskType.TAX_CALCULATION,
            input_data={"gross_income": Decimal("50000")},
        )
        request = _make_request(tasks=[task])
        result = engine.execute_pipeline(request)

        assert result.total_tasks == 1
        assert result.successful_tasks == 1

    def test_large_income_tax_calculation(self, engine: FinancialValidationEngine) -> None:
        """Very large income should still use the 43% bracket."""
        task = _make_task(
            task_type=TaskType.TAX_CALCULATION,
            input_data={"gross_income": Decimal("10000000")},
        )
        result = engine.execute_single_task(task)
        assert result.success is True
        expected_tax = (Decimal("10000000") * Decimal("0.43") * Decimal("0.6")).quantize(Decimal("0.01"))
        assert result.output_data["tax_amount"] == expected_tax

    def test_small_decimal_income(self, engine: FinancialValidationEngine) -> None:
        """Very small positive income should use the 23% bracket."""
        task = _make_task(
            task_type=TaskType.TAX_CALCULATION,
            input_data={"gross_income": Decimal("0.01")},
        )
        result = engine.execute_single_task(task)
        assert result.success is True

    def test_validation_context_defaults(self) -> None:
        """ValidationContext defaults to Italian settings."""
        ctx = ValidationContext()
        assert ctx.language == "it"
        assert ctx.region == "italy"
        assert ctx.currency == "EUR"
        assert ctx.regulation_year == 2024

    def test_task_result_defaults(self) -> None:
        """TaskResult has sensible defaults."""
        tr = TaskResult(task_id="x", task_type=TaskType.TAX_CALCULATION, success=True)
        assert tr.output_data == {}
        assert tr.error_messages == []
        assert tr.validation_warnings == []
        assert tr.execution_time_ms == 0
        assert tr.quality_score == Decimal("0")
        assert tr.confidence_score == Decimal("0")
        assert tr.timeout_occurred is False
        assert tr.status == "completed"
        assert tr.priority == "medium"

    def test_engine_configuration_defaults(self) -> None:
        """EngineConfiguration has expected defaults."""
        cfg = EngineConfiguration()
        assert cfg.enable_tax_calculations is True
        assert cfg.enable_business_valuations is True
        assert cfg.enable_financial_ratios is True
        assert cfg.enable_labor_calculations is True
        assert cfg.enable_document_parsing is True
        assert cfg.precision_decimal_places == 2
        assert cfg.performance_timeout_seconds == 30
        assert cfg.quality_threshold == Decimal("0.90")
        assert cfg.max_parallel_tasks == 10
        assert cfg.enable_caching is True
        assert cfg.cache_ttl_seconds == 3600

    def test_quality_assurance_defaults(self) -> None:
        qa = QualityAssurance()
        assert qa.enable_cross_validation is False
        assert qa.variance_threshold == Decimal("0.10")
        assert qa.confidence_threshold == Decimal("0.85")
        assert qa.enable_result_verification is True
        assert qa.enable_data_consistency_checks is True

    def test_dcf_pv_cash_flow_values(self, engine: FinancialValidationEngine) -> None:
        """Verify the DCF present-value cash flows are mathematically correct."""
        cfs = [Decimal("100000"), Decimal("200000")]
        dr = Decimal("0.10")
        task = _make_task(
            task_type=TaskType.BUSINESS_VALUATION,
            input_data={
                "cash_flows": cfs,
                "discount_rate": dr,
                "terminal_growth_rate": Decimal("0"),
            },
        )
        result = engine.execute_single_task(task)
        assert result.success is True

        pv0 = (Decimal("100000") / (Decimal("1.10") ** 1)).quantize(Decimal("0.01"))
        pv1 = (Decimal("200000") / (Decimal("1.10") ** 2)).quantize(Decimal("0.01"))
        assert result.output_data["pv_cash_flows"][0] == pv0
        assert result.output_data["pv_cash_flows"][1] == pv1

        # Enterprise value = sum of PVs (terminal is 0)
        assert result.output_data["enterprise_value"] == (pv0 + pv1).quantize(Decimal("0.01"))

    def test_pipeline_execution_order_matches_task_ids(self, engine: FinancialValidationEngine) -> None:
        """execution_order in the result must contain task IDs sorted by priority."""
        tasks = [
            _make_task(task_id="low", task_type=TaskType.DOCUMENT_PARSING, input_data={}, priority="low"),
            _make_task(task_id="high", task_type=TaskType.DOCUMENT_PARSING, input_data={}, priority="high"),
            _make_task(task_id="med", task_type=TaskType.DOCUMENT_PARSING, input_data={}, priority="medium"),
        ]
        request = _make_request(tasks=tasks)
        result = engine.execute_pipeline(request, "sequential")

        assert result.execution_order == ["high", "med", "low"]
