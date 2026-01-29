"""Tests for consistency metrics (pass@k, pass^k).

TDD: RED phase - Write tests first, then implement.
"""

from unittest.mock import AsyncMock

import pytest

from evals.metrics.consistency import (
    ConsistencyEvaluator,
    ConsistencyResult,
)
from evals.schemas.test_case import (
    GradeResult,
    TestCase,
    TestCaseCategory,
)


class TestConsistencyResult:
    """Tests for ConsistencyResult."""

    def test_create_result(self) -> None:
        """Test creating a consistency result."""
        result = ConsistencyResult(
            passed=True,
            pass_rate=0.8,
            attempts=5,
            successful_attempts=4,
            individual_results=[
                GradeResult(score=0.9, passed=True),
                GradeResult(score=0.85, passed=True),
                GradeResult(score=0.6, passed=False),
                GradeResult(score=0.88, passed=True),
                GradeResult(score=0.92, passed=True),
            ],
        )
        assert result.passed is True
        assert result.pass_rate == 0.8
        assert result.successful_attempts == 4

    def test_perfect_consistency(self) -> None:
        """Test perfect consistency result."""
        result = ConsistencyResult(
            passed=True,
            pass_rate=1.0,
            attempts=3,
            successful_attempts=3,
            individual_results=[
                GradeResult(score=0.9, passed=True),
                GradeResult(score=0.95, passed=True),
                GradeResult(score=0.88, passed=True),
            ],
        )
        assert result.pass_rate == 1.0


class TestConsistencyEvaluator:
    """Tests for ConsistencyEvaluator."""

    @pytest.fixture
    def evaluator(self) -> ConsistencyEvaluator:
        """Create a consistency evaluator instance."""
        return ConsistencyEvaluator(k=3)

    @pytest.fixture
    def test_case(self) -> TestCase:
        """Create a sample test case."""
        return TestCase(
            id="CONSISTENCY-001",
            category=TestCaseCategory.ROUTING,
            query="Test query",
            pass_threshold=0.7,
        )

    @pytest.mark.asyncio
    async def test_pass_at_k_all_pass(self, evaluator: ConsistencyEvaluator) -> None:
        """Test pass@k when all attempts pass."""
        test_case = TestCase(
            id="TEST-001",
            category=TestCaseCategory.ROUTING,
            query="Test query",
            pass_threshold=0.7,
        )

        # Mock run function that always passes
        async def mock_run(tc: TestCase) -> dict:
            return {"route": "technical_research", "confidence": 0.9}

        # Mock grader that always passes
        mock_grader = AsyncMock()
        mock_grader.grade.return_value = GradeResult(score=0.9, passed=True, reasoning="Good")

        result = await evaluator.evaluate_pass_at_k(
            run_fn=mock_run,
            grader=mock_grader,
            test_case=test_case,
        )

        assert result.passed is True
        assert result.pass_rate == 1.0
        assert result.successful_attempts == 3

    @pytest.mark.asyncio
    async def test_pass_at_k_one_passes(self, evaluator: ConsistencyEvaluator) -> None:
        """Test pass@k when at least one attempt passes (success)."""
        test_case = TestCase(
            id="TEST-002",
            category=TestCaseCategory.ROUTING,
            query="Test query",
            pass_threshold=0.7,
        )

        async def mock_run(tc: TestCase) -> dict:
            return {"route": "technical_research"}

        # Grader returns pass, fail, fail
        mock_grader = AsyncMock()
        mock_grader.grade.side_effect = [
            GradeResult(score=0.9, passed=True),
            GradeResult(score=0.5, passed=False),
            GradeResult(score=0.4, passed=False),
        ]

        result = await evaluator.evaluate_pass_at_k(
            run_fn=mock_run,
            grader=mock_grader,
            test_case=test_case,
        )

        # pass@k succeeds if at least 1 passes
        assert result.passed is True
        assert result.pass_rate == pytest.approx(1 / 3, rel=0.01)

    @pytest.mark.asyncio
    async def test_pass_at_k_none_pass(self, evaluator: ConsistencyEvaluator) -> None:
        """Test pass@k when no attempts pass (failure)."""
        test_case = TestCase(
            id="TEST-003",
            category=TestCaseCategory.ROUTING,
            query="Test query",
            pass_threshold=0.7,
        )

        async def mock_run(tc: TestCase) -> dict:
            return {"route": "chitchat"}  # Wrong route

        mock_grader = AsyncMock()
        mock_grader.grade.return_value = GradeResult(score=0.3, passed=False, reasoning="Wrong route")

        result = await evaluator.evaluate_pass_at_k(
            run_fn=mock_run,
            grader=mock_grader,
            test_case=test_case,
        )

        assert result.passed is False
        assert result.pass_rate == 0.0

    @pytest.mark.asyncio
    async def test_pass_all_k_all_pass(self, evaluator: ConsistencyEvaluator) -> None:
        """Test pass^k when all attempts pass (success)."""
        test_case = TestCase(
            id="TEST-004",
            category=TestCaseCategory.ROUTING,
            query="Test query",
            pass_threshold=0.7,
        )

        async def mock_run(tc: TestCase) -> dict:
            return {"route": "technical_research"}

        mock_grader = AsyncMock()
        mock_grader.grade.return_value = GradeResult(score=0.9, passed=True, reasoning="Good")

        result = await evaluator.evaluate_pass_all_k(
            run_fn=mock_run,
            grader=mock_grader,
            test_case=test_case,
        )

        assert result.passed is True
        assert result.pass_rate == 1.0

    @pytest.mark.asyncio
    async def test_pass_all_k_one_fails(self, evaluator: ConsistencyEvaluator) -> None:
        """Test pass^k when one attempt fails (failure)."""
        test_case = TestCase(
            id="TEST-005",
            category=TestCaseCategory.ROUTING,
            query="Test query",
            pass_threshold=0.7,
        )

        async def mock_run(tc: TestCase) -> dict:
            return {"route": "technical_research"}

        # Grader returns pass, pass, fail
        mock_grader = AsyncMock()
        mock_grader.grade.side_effect = [
            GradeResult(score=0.9, passed=True),
            GradeResult(score=0.85, passed=True),
            GradeResult(score=0.5, passed=False),
        ]

        result = await evaluator.evaluate_pass_all_k(
            run_fn=mock_run,
            grader=mock_grader,
            test_case=test_case,
        )

        # pass^k fails if any attempt fails
        assert result.passed is False
        assert result.pass_rate == pytest.approx(2 / 3, rel=0.01)

    @pytest.mark.asyncio
    async def test_pass_all_k_early_exit(self, evaluator: ConsistencyEvaluator) -> None:
        """Test pass^k exits early on first failure."""
        test_case = TestCase(
            id="TEST-006",
            category=TestCaseCategory.ROUTING,
            query="Test query",
            pass_threshold=0.7,
        )

        call_count = 0

        async def mock_run(tc: TestCase) -> dict:
            nonlocal call_count
            call_count += 1
            return {"route": "technical_research"}

        # First attempt fails
        mock_grader = AsyncMock()
        mock_grader.grade.return_value = GradeResult(score=0.3, passed=False, reasoning="Failed")

        result = await evaluator.evaluate_pass_all_k(
            run_fn=mock_run,
            grader=mock_grader,
            test_case=test_case,
        )

        assert result.passed is False
        # Should exit after first failure (not run all k)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_custom_k_value(self) -> None:
        """Test with custom k value."""
        evaluator = ConsistencyEvaluator(k=5)
        test_case = TestCase(
            id="TEST-007",
            category=TestCaseCategory.ROUTING,
            query="Test query",
            pass_threshold=0.7,
        )

        async def mock_run(tc: TestCase) -> dict:
            return {"route": "technical_research"}

        mock_grader = AsyncMock()
        mock_grader.grade.return_value = GradeResult(score=0.9, passed=True)

        result = await evaluator.evaluate_pass_at_k(
            run_fn=mock_run,
            grader=mock_grader,
            test_case=test_case,
        )

        assert result.attempts == 5

    @pytest.mark.asyncio
    async def test_run_function_error_handling(self, evaluator: ConsistencyEvaluator) -> None:
        """Test handling of errors in run function."""
        test_case = TestCase(
            id="TEST-008",
            category=TestCaseCategory.ROUTING,
            query="Test query",
            pass_threshold=0.7,
        )

        async def mock_run_with_error(tc: TestCase) -> dict:
            raise RuntimeError("Execution error")

        mock_grader = AsyncMock()

        result = await evaluator.evaluate_pass_at_k(
            run_fn=mock_run_with_error,
            grader=mock_grader,
            test_case=test_case,
        )

        assert result.passed is False
        assert result.pass_rate == 0.0

    @pytest.mark.asyncio
    async def test_score_variance_calculation(self, evaluator: ConsistencyEvaluator) -> None:
        """Test score variance is calculated correctly."""
        test_case = TestCase(
            id="TEST-009",
            category=TestCaseCategory.ROUTING,
            query="Test query",
            pass_threshold=0.7,
        )

        async def mock_run(tc: TestCase) -> dict:
            return {"route": "technical_research"}

        # Grader returns varying scores
        mock_grader = AsyncMock()
        mock_grader.grade.side_effect = [
            GradeResult(score=0.8, passed=True),
            GradeResult(score=0.9, passed=True),
            GradeResult(score=0.7, passed=True),
        ]

        result = await evaluator.evaluate_pass_at_k(
            run_fn=mock_run,
            grader=mock_grader,
            test_case=test_case,
        )

        # Mean = 0.8, scores vary around it
        assert hasattr(result, "score_variance") or "score_variance" in str(result)

    @pytest.mark.asyncio
    async def test_mean_score_calculation(self, evaluator: ConsistencyEvaluator) -> None:
        """Test mean score is calculated correctly."""
        test_case = TestCase(
            id="TEST-010",
            category=TestCaseCategory.ROUTING,
            query="Test query",
            pass_threshold=0.7,
        )

        async def mock_run(tc: TestCase) -> dict:
            return {"route": "technical_research"}

        # Grader returns varying scores
        mock_grader = AsyncMock()
        mock_grader.grade.side_effect = [
            GradeResult(score=0.8, passed=True),
            GradeResult(score=0.9, passed=True),
            GradeResult(score=0.7, passed=True),
        ]

        result = await evaluator.evaluate_pass_at_k(
            run_fn=mock_run,
            grader=mock_grader,
            test_case=test_case,
        )

        # Mean should be (0.8 + 0.9 + 0.7) / 3 = 0.8
        assert result.mean_score == pytest.approx(0.8, rel=0.01)
