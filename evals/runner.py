"""Main entry point for running evaluations.

Usage:
    # Quick check (code graders only)
    uv run python -m evals.runner --config fast

    # Full local check with Ollama
    uv run python -m evals.runner --config local --use-ollama

    # PR check
    uv run python -m evals.runner --config pr
"""

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from evals.config import (
    EvalConfig,
    RunMode,
    create_fast_config,
    create_local_config,
    create_nightly_config,
    create_pr_config,
    create_weekly_config,
)
from evals.graders import CitationGrader, RetrievalGrader, RoutingGrader
from evals.metrics.aggregate import AggregateMetrics, aggregate_results
from evals.schemas.test_case import (
    GradeResult,
    GraderType,
    TestCase,
    TestCaseCategory,
    TestCaseResult,
)


@dataclass
class RunResult:
    """Result from running evaluations.

    Attributes:
        success: Whether the evaluation run succeeded
        total: Total number of test cases
        passed: Number that passed
        failed: Number that failed
        pass_rate: Fraction that passed
        duration_seconds: Total duration
        exit_code: Exit code (0 = success, 1 = failure)
        failure_reason: Reason for failure if any
        report_path: Path to generated report
        metrics: Aggregate metrics
    """

    success: bool
    total: int
    passed: int
    failed: int
    pass_rate: float
    duration_seconds: float
    exit_code: int
    failure_reason: str = ""
    report_path: str | None = None
    metrics: AggregateMetrics | None = None


def load_test_cases(path: Path) -> list[TestCase]:
    """Load test cases from file or directory.

    Args:
        path: Path to JSON file or directory containing JSON files

    Returns:
        List of TestCase objects
    """
    if path.is_file():
        with open(path) as f:
            data = json.load(f)
        return [TestCase.model_validate(item) for item in data]

    elif path.is_dir():
        cases = []
        for json_file in path.glob("*.json"):
            with open(json_file) as f:
                data = json.load(f)
            cases.extend(TestCase.model_validate(item) for item in data)
        return cases

    else:
        raise FileNotFoundError(f"Path not found: {path}")


class EvalRunner:
    """Main runner for evaluations.

    Coordinates loading test cases, running graders, and generating reports.

    Example:
        ```python
        config = create_pr_config()
        runner = EvalRunner(config)
        result = await runner.run(test_cases)
        sys.exit(result.exit_code)
        ```
    """

    def __init__(self, config: EvalConfig):
        """Initialize runner with configuration.

        Args:
            config: Evaluation configuration
        """
        self.config = config
        self._init_graders()

    def _init_graders(self) -> None:
        """Initialize graders based on configuration."""
        self.routing_grader = RoutingGrader()
        self.retrieval_grader = RetrievalGrader()
        self.citation_grader = CitationGrader()

    async def run(
        self,
        test_cases: list[TestCase],
        categories: list[TestCaseCategory] | None = None,
        grader_types: list[GraderType] | None = None,
    ) -> RunResult:
        """Run evaluation on test cases.

        Args:
            test_cases: Test cases to evaluate
            categories: Filter to specific categories (optional)
            grader_types: Filter to specific grader types (optional)

        Returns:
            RunResult with evaluation outcome
        """
        start_time = time.time()

        # Filter test cases
        filtered = self._filter_test_cases(
            test_cases=test_cases,
            categories=categories,
            grader_types=grader_types,
        )

        if not filtered:
            return RunResult(
                success=True,
                total=0,
                passed=0,
                failed=0,
                pass_rate=1.0,
                duration_seconds=0.0,
                exit_code=0,
            )

        # Run evaluations
        results = await self._run_evaluations(filtered)

        # Aggregate results
        metrics = aggregate_results(results)

        # Check threshold
        success = metrics.overall_pass_rate >= self.config.fail_threshold
        failure_reason = ""
        if not success:
            failure_reason = (
                f"Pass rate {metrics.overall_pass_rate:.1%} below " f"threshold {self.config.fail_threshold:.1%}"
            )

        # Generate report
        report_path = None
        if self.config.report_dir:
            report_path = self._generate_report(metrics, results)

        duration = time.time() - start_time

        return RunResult(
            success=success,
            total=metrics.total,
            passed=metrics.passed,
            failed=metrics.failed,
            pass_rate=metrics.overall_pass_rate,
            duration_seconds=duration,
            exit_code=0 if success else 1,
            failure_reason=failure_reason,
            report_path=report_path,
            metrics=metrics,
        )

    def _filter_test_cases(
        self,
        test_cases: list[TestCase],
        categories: list[TestCaseCategory] | None,
        grader_types: list[GraderType] | None,
    ) -> list[TestCase]:
        """Filter test cases based on criteria.

        Args:
            test_cases: All test cases
            categories: Category filter
            grader_types: Grader type filter

        Returns:
            Filtered list of test cases
        """
        filtered = test_cases

        # Filter by regression flag
        if self.config.regression_only:
            filtered = [tc for tc in filtered if tc.is_regression]

        # Filter by category
        if categories:
            filtered = [tc for tc in filtered if tc.category in categories]

        # Filter by grader type
        if grader_types:
            filtered = [tc for tc in filtered if tc.grader_type in grader_types]

        return filtered

    async def _run_evaluations(
        self,
        test_cases: list[TestCase],
    ) -> list[TestCaseResult]:
        """Run evaluations on test cases.

        Args:
            test_cases: Test cases to evaluate

        Returns:
            List of TestCaseResult
        """
        results = []

        for test_case in test_cases:
            start = time.time()

            try:
                grade = await self._grade_test_case(test_case)
                duration = (time.time() - start) * 1000  # ms

                results.append(
                    TestCaseResult(
                        test_case=test_case,
                        grade=grade,
                        duration_ms=duration,
                    )
                )

            except Exception as e:
                duration = (time.time() - start) * 1000
                results.append(
                    TestCaseResult(
                        test_case=test_case,
                        grade=GradeResult(
                            score=0.0,
                            passed=False,
                            reasoning=f"Evaluation error: {e}",
                        ),
                        duration_ms=duration,
                    )
                )

        return results

    async def _grade_test_case(self, test_case: TestCase) -> GradeResult:
        """Grade a single test case.

        Args:
            test_case: Test case to grade

        Returns:
            GradeResult from grading
        """
        # For now, return a placeholder - actual implementation would
        # run the system and grade the output
        return GradeResult(
            score=0.0,
            passed=False,
            reasoning="Not implemented - needs system integration",
        )

    def _generate_report(
        self,
        metrics: AggregateMetrics,
        results: list[TestCaseResult],
    ) -> str:
        """Generate evaluation report.

        Args:
            metrics: Aggregate metrics
            results: Individual results

        Returns:
            Path to generated report file
        """
        self.config.report_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.config.report_dir / f"eval_report_{timestamp}.json"

        report_data = {
            "timestamp": datetime.now().isoformat(),
            "mode": self.config.mode.value,
            "summary": {
                "total": metrics.total,
                "passed": metrics.passed,
                "failed": metrics.failed,
                "pass_rate": metrics.overall_pass_rate,
                "mean_score": metrics.overall_mean_score,
            },
            "by_category": {
                cat.value: {
                    "total": cat_metrics.total,
                    "passed": cat_metrics.passed,
                    "failed": cat_metrics.failed,
                    "pass_rate": cat_metrics.pass_rate,
                }
                for cat, cat_metrics in metrics.by_category.items()
            },
            "failures": [
                {
                    "id": r.test_case.id,
                    "category": r.test_case.category.value,
                    "query": r.test_case.query,
                    "score": r.grade.score,
                    "reasoning": r.grade.reasoning,
                }
                for r in metrics.failures
            ],
        }

        with open(report_path, "w") as f:
            json.dump(report_data, f, indent=2)

        return str(report_path)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI."""
    parser = argparse.ArgumentParser(description="Run PratikoAI evaluation suite")
    parser.add_argument(
        "--config",
        choices=["pr", "local", "nightly", "weekly", "fast"],
        default="local",
        help="Configuration preset to use",
    )
    parser.add_argument(
        "--use-ollama",
        action="store_true",
        help="Enable Ollama for model graders",
    )
    parser.add_argument(
        "--graders",
        choices=["code", "model", "all"],
        default="code",
        help="Grader types to use",
    )
    parser.add_argument(
        "--category",
        choices=["routing", "retrieval", "response", "all"],
        default="all",
        help="Test category to run",
    )
    parser.add_argument(
        "--test-dir",
        type=Path,
        default=Path("evals/datasets/regression"),
        help="Directory containing test cases",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    return parser


async def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Create configuration
    config_map = {
        "pr": create_pr_config,
        "local": create_local_config,
        "nightly": create_nightly_config,
        "weekly": create_weekly_config,
        "fast": create_fast_config,
    }
    config = config_map[args.config]()

    # Override with CLI args
    if args.use_ollama:
        config.use_ollama = True
    if args.verbose:
        config.verbose = True

    # Load test cases
    try:
        test_cases = load_test_cases(args.test_dir)
    except FileNotFoundError:
        print(f"No test cases found at {args.test_dir}")
        return 0

    # Filter by category
    categories = None
    if args.category != "all":
        categories = [TestCaseCategory(args.category)]

    # Run evaluations
    runner = EvalRunner(config)
    result = await runner.run(test_cases, categories=categories)

    # Print summary
    print(f"\n{'=' * 60}")
    print(f"Evaluation Results ({config.mode.value} mode)")
    print(f"{'=' * 60}")
    print(f"Total:    {result.total}")
    print(f"Passed:   {result.passed}")
    print(f"Failed:   {result.failed}")
    print(f"Rate:     {result.pass_rate:.1%}")
    print(f"Duration: {result.duration_seconds:.1f}s")

    if result.report_path:
        print(f"Report:   {result.report_path}")

    if not result.success:
        print(f"\n FAILED: {result.failure_reason}")

    return result.exit_code


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
