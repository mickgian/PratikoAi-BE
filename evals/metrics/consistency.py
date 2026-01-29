"""Consistency metrics for handling non-determinism in LLM outputs.

Implements pass@k and pass^k metrics for evaluating system reliability:
- pass@k: At least 1 of k attempts passes (use for development/capability)
- pass^k: All k attempts must pass (use for production/regression)
"""

import statistics
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Protocol

from evals.schemas.test_case import GradeResult, TestCase


class Grader(Protocol):
    """Protocol for graders that can be used with ConsistencyEvaluator."""

    def grade(
        self,
        test_case: TestCase,
        actual_output: dict[str, Any],
        **kwargs: Any,
    ) -> GradeResult: ...


class AsyncGrader(Protocol):
    """Protocol for async graders."""

    async def grade(
        self,
        test_case: TestCase,
        actual_output: dict[str, Any],
        **kwargs: Any,
    ) -> GradeResult: ...


@dataclass
class ConsistencyResult:
    """Result from consistency evaluation.

    Attributes:
        passed: Whether the consistency check passed
        pass_rate: Fraction of attempts that passed
        attempts: Total number of attempts
        successful_attempts: Number of passing attempts
        individual_results: GradeResult for each attempt
        mean_score: Mean score across all attempts
        score_variance: Variance of scores across attempts
    """

    passed: bool
    pass_rate: float
    attempts: int
    successful_attempts: int
    individual_results: list[GradeResult] = field(default_factory=list)
    mean_score: float = 0.0
    score_variance: float = 0.0


class ConsistencyEvaluator:
    """Evaluator for consistency metrics.

    Handles non-determinism in LLM outputs by running multiple attempts
    and evaluating pass rates.

    Example:
        ```python
        evaluator = ConsistencyEvaluator(k=5)

        # For development: pass@k (any 1 of k passes)
        result = await evaluator.evaluate_pass_at_k(run_fn, grader, test_case)

        # For production: pass^k (all k must pass)
        result = await evaluator.evaluate_pass_all_k(run_fn, grader, test_case)
        ```
    """

    def __init__(self, k: int = 3):
        """Initialize consistency evaluator.

        Args:
            k: Number of attempts for consistency evaluation
        """
        self.k = k

    async def evaluate_pass_at_k(
        self,
        run_fn: Callable[[TestCase], Awaitable[dict[str, Any]]],
        grader: Grader | AsyncGrader,
        test_case: TestCase,
        **grader_kwargs: Any,
    ) -> ConsistencyResult:
        """Evaluate using pass@k metric.

        At least 1 of k attempts must pass. Use for development and
        capability testing where we want to know if the system CAN
        produce correct answers.

        Args:
            run_fn: Async function to run the system
            grader: Grader to evaluate outputs
            test_case: Test case to evaluate
            **grader_kwargs: Additional arguments for grader

        Returns:
            ConsistencyResult with pass@k evaluation
        """
        results = await self._run_attempts(
            run_fn=run_fn,
            grader=grader,
            test_case=test_case,
            early_exit_on_fail=False,  # Run all k attempts
            **grader_kwargs,
        )

        successful = sum(1 for r in results if r.passed)
        passed = successful >= 1  # At least 1 passes

        return self._build_result(
            passed=passed,
            results=results,
        )

    async def evaluate_pass_all_k(
        self,
        run_fn: Callable[[TestCase], Awaitable[dict[str, Any]]],
        grader: Grader | AsyncGrader,
        test_case: TestCase,
        **grader_kwargs: Any,
    ) -> ConsistencyResult:
        """Evaluate using pass^k metric.

        All k attempts must pass. Use for production and regression
        testing where we need RELIABLE correct answers.

        Args:
            run_fn: Async function to run the system
            grader: Grader to evaluate outputs
            test_case: Test case to evaluate
            **grader_kwargs: Additional arguments for grader

        Returns:
            ConsistencyResult with pass^k evaluation
        """
        results = await self._run_attempts(
            run_fn=run_fn,
            grader=grader,
            test_case=test_case,
            early_exit_on_fail=True,  # Exit on first failure
            **grader_kwargs,
        )

        successful = sum(1 for r in results if r.passed)
        # Only passes if we completed all k and all passed
        passed = len(results) == self.k and successful == self.k

        return self._build_result(
            passed=passed,
            results=results,
        )

    async def _run_attempts(
        self,
        run_fn: Callable[[TestCase], Awaitable[dict[str, Any]]],
        grader: Grader | AsyncGrader,
        test_case: TestCase,
        early_exit_on_fail: bool,
        **grader_kwargs: Any,
    ) -> list[GradeResult]:
        """Run k attempts and collect results.

        Args:
            run_fn: Function to run the system
            grader: Grader to evaluate outputs
            test_case: Test case to evaluate
            early_exit_on_fail: Whether to exit on first failure
            **grader_kwargs: Additional arguments for grader

        Returns:
            List of GradeResult for each attempt
        """
        results: list[GradeResult] = []

        for attempt in range(self.k):
            try:
                # Run the system
                output = await run_fn(test_case)

                # Grade the output
                grade = await self._grade_output(
                    grader=grader,
                    test_case=test_case,
                    output=output,
                    **grader_kwargs,
                )
                results.append(grade)

                # Early exit on failure if requested
                if early_exit_on_fail and not grade.passed:
                    break

            except Exception as e:
                # Record failed attempt
                results.append(
                    GradeResult(
                        score=0.0,
                        passed=False,
                        reasoning=f"Execution error: {e}",
                    )
                )
                if early_exit_on_fail:
                    break

        return results

    async def _grade_output(
        self,
        grader: Grader | AsyncGrader,
        test_case: TestCase,
        output: dict[str, Any],
        **grader_kwargs: Any,
    ) -> GradeResult:
        """Grade an output, handling both sync and async graders.

        Args:
            grader: Grader to use
            test_case: Test case
            output: Output to grade
            **grader_kwargs: Additional arguments

        Returns:
            GradeResult from grading
        """
        result = grader.grade(test_case, output, **grader_kwargs)

        # Handle async graders
        if hasattr(result, "__await__"):
            awaited_result: GradeResult = await result  # type: ignore[misc]
            return awaited_result

        # For sync graders, result is already a GradeResult
        return result  # type: ignore[return-value]

    def _build_result(
        self,
        passed: bool,
        results: list[GradeResult],
    ) -> ConsistencyResult:
        """Build ConsistencyResult from individual results.

        Args:
            passed: Whether consistency check passed
            results: List of individual GradeResults

        Returns:
            ConsistencyResult with computed statistics
        """
        successful = sum(1 for r in results if r.passed)
        pass_rate = successful / len(results) if results else 0.0

        scores = [r.score for r in results]
        mean_score = statistics.mean(scores) if scores else 0.0
        variance = statistics.variance(scores) if len(scores) > 1 else 0.0

        return ConsistencyResult(
            passed=passed,
            pass_rate=pass_rate,
            attempts=len(results),
            successful_attempts=successful,
            individual_results=results,
            mean_score=mean_score,
            score_variance=variance,
        )
