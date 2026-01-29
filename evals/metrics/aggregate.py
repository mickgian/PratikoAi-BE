"""Aggregate metrics for evaluation results.

Provides utilities for combining grader results across test cases
and computing summary statistics by category and grader type.
"""

import statistics
from collections import defaultdict
from dataclasses import dataclass, field

from evals.schemas.test_case import (
    GraderType,
    TestCaseCategory,
    TestCaseResult,
)


@dataclass
class CategoryMetrics:
    """Metrics for a single test category.

    Attributes:
        category: The test category
        total: Total number of test cases
        passed: Number that passed
        failed: Number that failed
        pass_rate: Fraction that passed
        mean_score: Mean score across all cases
        min_score: Minimum score
        max_score: Maximum score
    """

    category: TestCaseCategory
    total: int
    passed: int
    failed: int
    pass_rate: float
    mean_score: float
    min_score: float
    max_score: float


@dataclass
class AggregateMetrics:
    """Aggregate metrics across all test case results.

    Attributes:
        total: Total number of test cases
        passed: Number that passed
        failed: Number that failed
        overall_pass_rate: Fraction that passed
        overall_mean_score: Mean score across all cases
        by_category: Metrics broken down by category
        by_grader_type: Metrics broken down by grader type
        total_duration_ms: Total evaluation duration
        mean_duration_ms: Mean duration per test case
        failures: List of failed test case results
        regressions_detected: Regression tests that failed
    """

    total: int
    passed: int
    failed: int
    overall_pass_rate: float
    overall_mean_score: float
    by_category: dict[TestCaseCategory, CategoryMetrics] = field(default_factory=dict)
    by_grader_type: dict[GraderType, CategoryMetrics] = field(default_factory=dict)
    total_duration_ms: float = 0.0
    mean_duration_ms: float = 0.0
    failures: list[TestCaseResult] = field(default_factory=list)
    regressions_detected: list[TestCaseResult] = field(default_factory=list)


def aggregate_results(results: list[TestCaseResult]) -> AggregateMetrics:
    """Aggregate test case results into summary metrics.

    Args:
        results: List of test case results

    Returns:
        AggregateMetrics with summary statistics
    """
    if not results:
        return AggregateMetrics(
            total=0,
            passed=0,
            failed=0,
            overall_pass_rate=0.0,
            overall_mean_score=0.0,
        )

    # Count passed/failed
    passed = sum(1 for r in results if r.grade.passed)
    failed = len(results) - passed
    pass_rate = passed / len(results)

    # Compute mean score
    scores = [r.grade.score for r in results]
    mean_score = statistics.mean(scores)

    # Duration stats
    durations = [r.duration_ms for r in results]
    total_duration = sum(durations)
    mean_duration = statistics.mean(durations) if durations else 0.0

    # Collect failures
    failures = [r for r in results if not r.grade.passed]

    # Detect regressions (regression tests that failed)
    regressions = [r for r in results if r.test_case.is_regression and not r.grade.passed]

    # Group by category
    by_category = _group_by_category(results)

    # Group by grader type
    by_grader = _group_by_grader_type(results)

    return AggregateMetrics(
        total=len(results),
        passed=passed,
        failed=failed,
        overall_pass_rate=pass_rate,
        overall_mean_score=mean_score,
        by_category=by_category,
        by_grader_type=by_grader,
        total_duration_ms=total_duration,
        mean_duration_ms=mean_duration,
        failures=failures,
        regressions_detected=regressions,
    )


def compute_category_metrics(
    category: TestCaseCategory,
    results: list[TestCaseResult],
) -> CategoryMetrics:
    """Compute metrics for a single category.

    Args:
        category: The category to compute metrics for
        results: List of results in this category

    Returns:
        CategoryMetrics for the category
    """
    if not results:
        return CategoryMetrics(
            category=category,
            total=0,
            passed=0,
            failed=0,
            pass_rate=0.0,
            mean_score=0.0,
            min_score=0.0,
            max_score=0.0,
        )

    passed = sum(1 for r in results if r.grade.passed)
    failed = len(results) - passed
    pass_rate = passed / len(results)

    scores = [r.grade.score for r in results]
    mean_score = statistics.mean(scores)
    min_score = min(scores)
    max_score = max(scores)

    return CategoryMetrics(
        category=category,
        total=len(results),
        passed=passed,
        failed=failed,
        pass_rate=pass_rate,
        mean_score=mean_score,
        min_score=min_score,
        max_score=max_score,
    )


def _group_by_category(
    results: list[TestCaseResult],
) -> dict[TestCaseCategory, CategoryMetrics]:
    """Group results by category and compute metrics.

    Args:
        results: List of test case results

    Returns:
        Dict mapping category to metrics
    """
    grouped: dict[TestCaseCategory, list[TestCaseResult]] = defaultdict(list)

    for result in results:
        grouped[result.test_case.category].append(result)

    return {
        category: compute_category_metrics(category, category_results)
        for category, category_results in grouped.items()
    }


def _group_by_grader_type(
    results: list[TestCaseResult],
) -> dict[GraderType, CategoryMetrics]:
    """Group results by grader type and compute metrics.

    Args:
        results: List of test case results

    Returns:
        Dict mapping grader type to metrics
    """
    grouped: dict[GraderType, list[TestCaseResult]] = defaultdict(list)

    for result in results:
        grouped[result.test_case.grader_type].append(result)

    # Reuse CategoryMetrics structure for grader type grouping
    return {
        grader_type: CategoryMetrics(
            category=TestCaseCategory.ROUTING,  # Placeholder
            total=len(type_results),
            passed=sum(1 for r in type_results if r.grade.passed),
            failed=sum(1 for r in type_results if not r.grade.passed),
            pass_rate=(sum(1 for r in type_results if r.grade.passed) / len(type_results) if type_results else 0.0),
            mean_score=(statistics.mean(r.grade.score for r in type_results) if type_results else 0.0),
            min_score=(min(r.grade.score for r in type_results) if type_results else 0.0),
            max_score=(max(r.grade.score for r in type_results) if type_results else 0.0),
        )
        for grader_type, type_results in grouped.items()
    }
