"""Tests for aggregate metrics.

TDD: RED phase - Write tests first, then implement.
"""

import pytest

from evals.metrics.aggregate import (
    AggregateMetrics,
    CategoryMetrics,
    aggregate_results,
    compute_category_metrics,
)
from evals.schemas.test_case import (
    GradeResult,
    TestCase,
    TestCaseCategory,
    TestCaseResult,
)


class TestCategoryMetrics:
    """Tests for CategoryMetrics."""

    def test_create_category_metrics(self) -> None:
        """Test creating category metrics."""
        metrics = CategoryMetrics(
            category=TestCaseCategory.ROUTING,
            total=10,
            passed=9,
            failed=1,
            pass_rate=0.9,
            mean_score=0.88,
            min_score=0.72,
            max_score=0.98,
        )
        assert metrics.pass_rate == 0.9
        assert metrics.mean_score == 0.88


class TestAggregateMetrics:
    """Tests for AggregateMetrics."""

    def test_create_aggregate_metrics(self) -> None:
        """Test creating aggregate metrics."""
        metrics = AggregateMetrics(
            total=50,
            passed=48,
            failed=2,
            overall_pass_rate=0.96,
            overall_mean_score=0.89,
            by_category={},
            by_grader_type={},
        )
        assert metrics.overall_pass_rate == 0.96
        assert metrics.failed == 2


class TestAggregateFunctions:
    """Tests for aggregate functions."""

    @pytest.fixture
    def sample_results(self) -> list[TestCaseResult]:
        """Create sample test case results."""
        return [
            TestCaseResult(
                test_case=TestCase(
                    id="ROUTING-001",
                    category=TestCaseCategory.ROUTING,
                    query="Query 1",
                ),
                grade=GradeResult(score=0.95, passed=True),
                duration_ms=100.0,
            ),
            TestCaseResult(
                test_case=TestCase(
                    id="ROUTING-002",
                    category=TestCaseCategory.ROUTING,
                    query="Query 2",
                ),
                grade=GradeResult(score=0.85, passed=True),
                duration_ms=120.0,
            ),
            TestCaseResult(
                test_case=TestCase(
                    id="ROUTING-003",
                    category=TestCaseCategory.ROUTING,
                    query="Query 3",
                ),
                grade=GradeResult(score=0.45, passed=False),
                duration_ms=80.0,
            ),
            TestCaseResult(
                test_case=TestCase(
                    id="RETRIEVAL-001",
                    category=TestCaseCategory.RETRIEVAL,
                    query="Query 4",
                ),
                grade=GradeResult(score=0.90, passed=True),
                duration_ms=200.0,
            ),
            TestCaseResult(
                test_case=TestCase(
                    id="RETRIEVAL-002",
                    category=TestCaseCategory.RETRIEVAL,
                    query="Query 5",
                ),
                grade=GradeResult(score=0.88, passed=True),
                duration_ms=180.0,
            ),
        ]

    def test_aggregate_results(self, sample_results: list[TestCaseResult]) -> None:
        """Test aggregating all results."""
        metrics = aggregate_results(sample_results)

        assert metrics.total == 5
        assert metrics.passed == 4
        assert metrics.failed == 1
        assert metrics.overall_pass_rate == 0.8
        # Mean score: (0.95 + 0.85 + 0.45 + 0.90 + 0.88) / 5 = 0.806
        assert abs(metrics.overall_mean_score - 0.806) < 0.01

    def test_aggregate_results_by_category(self, sample_results: list[TestCaseResult]) -> None:
        """Test aggregation includes category breakdown."""
        metrics = aggregate_results(sample_results)

        assert TestCaseCategory.ROUTING in metrics.by_category
        assert TestCaseCategory.RETRIEVAL in metrics.by_category

        routing = metrics.by_category[TestCaseCategory.ROUTING]
        assert routing.total == 3
        assert routing.passed == 2
        assert routing.failed == 1
        # Routing pass rate: 2/3 = 0.667
        assert abs(routing.pass_rate - 0.667) < 0.01

        retrieval = metrics.by_category[TestCaseCategory.RETRIEVAL]
        assert retrieval.total == 2
        assert retrieval.passed == 2
        assert retrieval.pass_rate == 1.0

    def test_compute_category_metrics(self, sample_results: list[TestCaseResult]) -> None:
        """Test computing metrics for a single category."""
        routing_results = [r for r in sample_results if r.test_case.category == TestCaseCategory.ROUTING]
        metrics = compute_category_metrics(TestCaseCategory.ROUTING, routing_results)

        assert metrics.category == TestCaseCategory.ROUTING
        assert metrics.total == 3
        assert metrics.passed == 2
        assert metrics.min_score == 0.45
        assert metrics.max_score == 0.95

    def test_aggregate_empty_results(self) -> None:
        """Test aggregating empty results list."""
        metrics = aggregate_results([])

        assert metrics.total == 0
        assert metrics.passed == 0
        assert metrics.failed == 0
        assert metrics.overall_pass_rate == 0.0
        assert metrics.overall_mean_score == 0.0

    def test_aggregate_all_passed(self) -> None:
        """Test aggregating when all tests pass."""
        results = [
            TestCaseResult(
                test_case=TestCase(
                    id=f"TEST-{i}",
                    category=TestCaseCategory.ROUTING,
                    query=f"Query {i}",
                ),
                grade=GradeResult(score=0.9, passed=True),
            )
            for i in range(5)
        ]
        metrics = aggregate_results(results)

        assert metrics.passed == 5
        assert metrics.failed == 0
        assert metrics.overall_pass_rate == 1.0

    def test_aggregate_all_failed(self) -> None:
        """Test aggregating when all tests fail."""
        results = [
            TestCaseResult(
                test_case=TestCase(
                    id=f"TEST-{i}",
                    category=TestCaseCategory.ROUTING,
                    query=f"Query {i}",
                ),
                grade=GradeResult(score=0.3, passed=False),
            )
            for i in range(5)
        ]
        metrics = aggregate_results(results)

        assert metrics.passed == 0
        assert metrics.failed == 5
        assert metrics.overall_pass_rate == 0.0

    def test_aggregate_duration_stats(self, sample_results: list[TestCaseResult]) -> None:
        """Test duration statistics are calculated."""
        metrics = aggregate_results(sample_results)

        # Total duration: 100 + 120 + 80 + 200 + 180 = 680ms
        assert metrics.total_duration_ms == 680.0
        # Mean: 680 / 5 = 136ms
        assert metrics.mean_duration_ms == 136.0

    def test_aggregate_includes_failures_list(self, sample_results: list[TestCaseResult]) -> None:
        """Test that failures are listed in aggregate."""
        metrics = aggregate_results(sample_results)

        assert len(metrics.failures) == 1
        assert metrics.failures[0].test_case.id == "ROUTING-003"

    def test_aggregate_regression_detection(self) -> None:
        """Test regression detection (comparing to baseline)."""
        current = [
            TestCaseResult(
                test_case=TestCase(
                    id="ROUTING-001",
                    category=TestCaseCategory.ROUTING,
                    query="Query 1",
                    is_regression=True,
                ),
                grade=GradeResult(score=0.45, passed=False),  # Failed!
            ),
        ]

        metrics = aggregate_results(current)

        # Regression tests that fail should be flagged
        assert len(metrics.regressions_detected) == 1
        assert metrics.regressions_detected[0].test_case.id == "ROUTING-001"
