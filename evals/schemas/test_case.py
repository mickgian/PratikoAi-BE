"""Test case schema for evaluation framework.

Defines the structure for evaluation test cases following Anthropic's
best practices for AI agent evaluation.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TestCaseCategory(str, Enum):
    """Categories for test cases corresponding to pipeline stages."""

    ROUTING = "routing"  # Step 34a - Query routing decisions
    RETRIEVAL = "retrieval"  # Step 39a-39c - Document retrieval
    RESPONSE = "response"  # Step 64 - Final response generation
    CAPABILITY = "capability"  # Hard cases for continuous improvement
    REGRESSION = "regression"  # Known-good cases that must not regress


class GraderType(str, Enum):
    """Types of graders for evaluation."""

    CODE = "code"  # Deterministic code-based graders (fast, 100% threshold)
    MODEL = "model"  # LLM-as-judge graders (Ollama local or API)
    HUMAN = "human"  # Expert human validation


class TestCase(BaseModel):
    """Schema for a single evaluation test case.

    Attributes:
        id: Unique identifier (e.g., "ROUTING-001")
        category: Test category (routing, retrieval, response, etc.)
        query: Italian query to evaluate
        expected_route: Expected routing decision (for routing tests)
        expected_sources: Expected source document IDs (for retrieval tests)
        expected_citations: Expected citations in response (for citation tests)
        actual_output: Pre-recorded output for golden dataset tests ($0 cost)
        grader_type: Type of grader to use (code, model, human)
        pass_threshold: Minimum score to pass (0.0-1.0)
        k_attempts: Number of attempts for pass@k/pass^k
        is_regression: Whether this is a regression test (must pass 100%)
        source: Origin of the test case (manual, expert_feedback, langfuse, etc.)
    """

    id: str = Field(..., description="Unique test case identifier")
    category: TestCaseCategory = Field(..., description="Test category")
    query: str = Field(..., description="Query to evaluate (Italian)")
    expected_route: str | None = Field(default=None, description="Expected routing decision")
    expected_sources: list[str] | None = Field(default=None, description="Expected source document IDs")
    expected_citations: list[str] | None = Field(default=None, description="Expected citations in response")
    actual_output: dict[str, Any] | None = Field(
        default=None,
        description="Pre-recorded output for golden dataset tests",
    )
    grader_type: GraderType = Field(default=GraderType.CODE, description="Type of grader to use")
    pass_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum score to pass",
    )
    k_attempts: int = Field(
        default=3,
        ge=1,
        description="Number of attempts for consistency evaluation",
    )
    is_regression: bool = Field(
        default=False,
        description="Whether this is a regression test case",
    )
    source: str = Field(
        default="manual",
        description="Origin of the test case",
    )


class GradeResult(BaseModel):
    """Result from grading a single test case.

    Attributes:
        score: Numeric score (0.0-1.0)
        passed: Whether the test passed the threshold
        reasoning: Explanation for the grade
        metrics: Additional metrics from the grader
    """

    score: float = Field(..., ge=0.0, le=1.0, description="Evaluation score")
    passed: bool = Field(..., description="Whether the test passed")
    reasoning: str = Field(default="", description="Explanation for the grade")
    metrics: dict[str, Any] | None = Field(default=None, description="Additional metrics")


class TestCaseResult(BaseModel):
    """Complete result for a test case evaluation.

    Attributes:
        test_case: The original test case
        grade: The grading result
        actual_output: The actual output from the system
        duration_ms: Execution time in milliseconds
    """

    test_case: TestCase = Field(..., description="Original test case")
    grade: GradeResult = Field(..., description="Grading result")
    actual_output: dict[str, Any] | None = Field(default=None, description="Actual output from the system")
    duration_ms: float = Field(default=0.0, description="Execution time in ms")
