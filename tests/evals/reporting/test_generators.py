"""Tests for report generators."""

from pathlib import Path

import pytest

from evals.metrics.aggregate import AggregateMetrics, CategoryMetrics
from evals.reporting.generators import (
    HTMLReportGenerator,
    JSONReportGenerator,
    generate_html_report,
    generate_json_report,
)
from evals.schemas.test_case import (
    GradeResult,
    TestCase,
    TestCaseCategory,
    TestCaseResult,
)


@pytest.fixture
def sample_metrics() -> AggregateMetrics:
    """Create sample aggregate metrics."""
    return AggregateMetrics(
        total=10,
        passed=9,
        failed=1,
        overall_pass_rate=0.9,
        overall_mean_score=0.85,
        by_category={
            TestCaseCategory.ROUTING: CategoryMetrics(
                category=TestCaseCategory.ROUTING,
                total=5,
                passed=5,
                failed=0,
                pass_rate=1.0,
                mean_score=0.9,
                min_score=0.8,
                max_score=0.95,
            ),
            TestCaseCategory.RETRIEVAL: CategoryMetrics(
                category=TestCaseCategory.RETRIEVAL,
                total=5,
                passed=4,
                failed=1,
                pass_rate=0.8,
                mean_score=0.8,
                min_score=0.5,
                max_score=0.95,
            ),
        },
        total_duration_ms=5000.0,
        mean_duration_ms=500.0,
        failures=[
            TestCaseResult(
                test_case=TestCase(
                    id="RET-003",
                    category=TestCaseCategory.RETRIEVAL,
                    query="Failed query",
                    is_regression=True,
                ),
                grade=GradeResult(score=0.5, passed=False, reasoning="Low score"),
            )
        ],
        regressions_detected=[],
    )


@pytest.fixture
def sample_results() -> list[TestCaseResult]:
    """Create sample results."""
    return [
        TestCaseResult(
            test_case=TestCase(
                id="R-001",
                category=TestCaseCategory.ROUTING,
                query="Query 1",
            ),
            grade=GradeResult(score=0.9, passed=True),
            duration_ms=100.0,
        ),
    ]


class TestJSONReportGenerator:
    """Tests for JSON report generator."""

    def test_generate_report(
        self,
        sample_metrics: AggregateMetrics,
        sample_results: list[TestCaseResult],
    ) -> None:
        """Test generating JSON report."""
        generator = JSONReportGenerator()
        report = generator.generate(sample_metrics, sample_results)

        assert "run_id" in report
        assert "timestamp" in report
        assert "summary" in report
        assert report["summary"]["total_cases"] == 10
        assert report["summary"]["passed"] == 9
        assert report["summary"]["pass_rate"] == 0.9

    def test_generate_includes_categories(
        self,
        sample_metrics: AggregateMetrics,
        sample_results: list[TestCaseResult],
    ) -> None:
        """Test report includes category breakdown."""
        generator = JSONReportGenerator()
        report = generator.generate(sample_metrics, sample_results)

        assert "by_category" in report
        assert "routing" in report["by_category"]
        assert report["by_category"]["routing"]["pass_rate"] == 1.0

    def test_generate_includes_failures(
        self,
        sample_metrics: AggregateMetrics,
        sample_results: list[TestCaseResult],
    ) -> None:
        """Test report includes failures."""
        generator = JSONReportGenerator()
        report = generator.generate(sample_metrics, sample_results)

        assert "failures" in report
        assert len(report["failures"]) == 1
        assert report["failures"][0]["case_id"] == "RET-003"

    def test_save_to_file(
        self,
        sample_metrics: AggregateMetrics,
        sample_results: list[TestCaseResult],
        tmp_path: Path,
    ) -> None:
        """Test saving JSON report to file."""
        generator = JSONReportGenerator()
        report = generator.generate(sample_metrics, sample_results)
        output = tmp_path / "report.json"

        saved_path = generator.save(report, output)

        assert saved_path.exists()
        assert saved_path.suffix == ".json"


class TestHTMLReportGenerator:
    """Tests for HTML report generator."""

    def test_generate_report(
        self,
        sample_metrics: AggregateMetrics,
        sample_results: list[TestCaseResult],
    ) -> None:
        """Test generating HTML report."""
        generator = HTMLReportGenerator()
        html = generator.generate(sample_metrics, sample_results)

        assert "<html" in html
        assert "90%" in html  # pass rate
        assert "Routing" in html

    def test_generate_includes_failures(
        self,
        sample_metrics: AggregateMetrics,
        sample_results: list[TestCaseResult],
    ) -> None:
        """Test HTML report includes failures."""
        generator = HTMLReportGenerator()
        html = generator.generate(sample_metrics, sample_results)

        assert "RET-003" in html
        assert "Failures" in html

    def test_generate_with_custom_title(
        self,
        sample_metrics: AggregateMetrics,
        sample_results: list[TestCaseResult],
    ) -> None:
        """Test custom title."""
        generator = HTMLReportGenerator()
        html = generator.generate(
            sample_metrics,
            sample_results,
            title="Custom Report Title",
        )

        assert "Custom Report Title" in html

    def test_save_to_file(
        self,
        sample_metrics: AggregateMetrics,
        sample_results: list[TestCaseResult],
        tmp_path: Path,
    ) -> None:
        """Test saving HTML report to file."""
        generator = HTMLReportGenerator()
        html = generator.generate(sample_metrics, sample_results)
        output = tmp_path / "report.html"

        saved_path = generator.save(html, output)

        assert saved_path.exists()
        assert saved_path.suffix == ".html"


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_generate_json_report(
        self,
        sample_metrics: AggregateMetrics,
        sample_results: list[TestCaseResult],
        tmp_path: Path,
    ) -> None:
        """Test generate_json_report function."""
        output = tmp_path / "report.json"

        path = generate_json_report(sample_metrics, sample_results, output)

        assert path.exists()

    def test_generate_html_report(
        self,
        sample_metrics: AggregateMetrics,
        sample_results: list[TestCaseResult],
        tmp_path: Path,
    ) -> None:
        """Test generate_html_report function."""
        output = tmp_path / "report.html"

        path = generate_html_report(sample_metrics, sample_results, output)

        assert path.exists()
