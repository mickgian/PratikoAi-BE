"""Tests for evaluation test case schemas.

TDD: RED phase - Write tests first, then implement.
"""

import pytest
from pydantic import ValidationError

from evals.schemas.test_case import (
    GradeResult,
    GraderType,
    TestCase,
    TestCaseCategory,
    TestCaseResult,
)


class TestTestCaseCategory:
    """Tests for TestCaseCategory enum."""

    def test_routing_category(self) -> None:
        """Test routing category exists."""
        assert TestCaseCategory.ROUTING.value == "routing"

    def test_retrieval_category(self) -> None:
        """Test retrieval category exists."""
        assert TestCaseCategory.RETRIEVAL.value == "retrieval"

    def test_response_category(self) -> None:
        """Test response category exists."""
        assert TestCaseCategory.RESPONSE.value == "response"

    def test_capability_category(self) -> None:
        """Test capability category exists."""
        assert TestCaseCategory.CAPABILITY.value == "capability"

    def test_regression_category(self) -> None:
        """Test regression category exists."""
        assert TestCaseCategory.REGRESSION.value == "regression"


class TestGraderType:
    """Tests for GraderType enum."""

    def test_code_grader(self) -> None:
        """Test code grader type exists."""
        assert GraderType.CODE.value == "code"

    def test_model_grader(self) -> None:
        """Test model grader type exists."""
        assert GraderType.MODEL.value == "model"

    def test_human_grader(self) -> None:
        """Test human grader type exists."""
        assert GraderType.HUMAN.value == "human"


class TestTestCase:
    """Tests for TestCase model."""

    def test_create_minimal_test_case(self) -> None:
        """Test creating a test case with minimal required fields."""
        test_case = TestCase(
            id="ROUTING-001",
            category=TestCaseCategory.ROUTING,
            query="Qual è la scadenza per la rottamazione quinquies?",
        )
        assert test_case.id == "ROUTING-001"
        assert test_case.category == TestCaseCategory.ROUTING
        assert test_case.query == "Qual è la scadenza per la rottamazione quinquies?"
        assert test_case.expected_route is None
        assert test_case.expected_sources is None
        assert test_case.expected_citations is None
        assert test_case.grader_type == GraderType.CODE
        assert test_case.pass_threshold == 0.7
        assert test_case.k_attempts == 3
        assert test_case.is_regression is False
        assert test_case.source == "manual"

    def test_create_full_test_case(self) -> None:
        """Test creating a test case with all fields."""
        test_case = TestCase(
            id="RETRIEVAL-042",
            category=TestCaseCategory.RETRIEVAL,
            query="Come calcolare l'IRAP per professionisti?",
            expected_route="knowledge_base",
            expected_sources=["INPS-circular-2024-01", "ADE-resolution-2024-05"],
            expected_citations=["Art. 5 D.Lgs. 446/1997", "Art. 2 L. 234/2021"],
            grader_type=GraderType.MODEL,
            pass_threshold=0.8,
            k_attempts=5,
            is_regression=True,
            source="expert_feedback",
        )
        assert test_case.id == "RETRIEVAL-042"
        assert test_case.category == TestCaseCategory.RETRIEVAL
        assert test_case.expected_route == "knowledge_base"
        assert test_case.expected_sources is not None
        assert len(test_case.expected_sources) == 2
        assert test_case.expected_citations is not None
        assert len(test_case.expected_citations) == 2
        assert test_case.grader_type == GraderType.MODEL
        assert test_case.pass_threshold == 0.8
        assert test_case.k_attempts == 5
        assert test_case.is_regression is True
        assert test_case.source == "expert_feedback"

    def test_id_required(self) -> None:
        """Test that id is required."""
        with pytest.raises(ValidationError) as exc_info:
            TestCase(
                category=TestCaseCategory.ROUTING,
                query="Some query",
            )
        assert "id" in str(exc_info.value)

    def test_category_required(self) -> None:
        """Test that category is required."""
        with pytest.raises(ValidationError) as exc_info:
            TestCase(
                id="TEST-001",
                query="Some query",
            )
        assert "category" in str(exc_info.value)

    def test_query_required(self) -> None:
        """Test that query is required."""
        with pytest.raises(ValidationError) as exc_info:
            TestCase(
                id="TEST-001",
                category=TestCaseCategory.ROUTING,
            )
        assert "query" in str(exc_info.value)

    def test_pass_threshold_validation_min(self) -> None:
        """Test pass_threshold must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            TestCase(
                id="TEST-001",
                category=TestCaseCategory.ROUTING,
                query="Some query",
                pass_threshold=-0.1,
            )
        assert "pass_threshold" in str(exc_info.value)

    def test_pass_threshold_validation_max(self) -> None:
        """Test pass_threshold must be <= 1."""
        with pytest.raises(ValidationError) as exc_info:
            TestCase(
                id="TEST-001",
                category=TestCaseCategory.ROUTING,
                query="Some query",
                pass_threshold=1.5,
            )
        assert "pass_threshold" in str(exc_info.value)

    def test_k_attempts_validation_min(self) -> None:
        """Test k_attempts must be >= 1."""
        with pytest.raises(ValidationError) as exc_info:
            TestCase(
                id="TEST-001",
                category=TestCaseCategory.ROUTING,
                query="Some query",
                k_attempts=0,
            )
        assert "k_attempts" in str(exc_info.value)

    def test_model_dump(self) -> None:
        """Test serialization to dict."""
        test_case = TestCase(
            id="TEST-001",
            category=TestCaseCategory.ROUTING,
            query="Test query",
            expected_route="chitchat",
        )
        data = test_case.model_dump()
        assert data["id"] == "TEST-001"
        assert data["category"] == "routing"
        assert data["query"] == "Test query"
        assert data["expected_route"] == "chitchat"

    def test_model_validate_from_dict(self) -> None:
        """Test deserialization from dict."""
        data = {
            "id": "TEST-001",
            "category": "routing",
            "query": "Test query",
            "expected_route": "knowledge_base",
            "is_regression": True,
        }
        test_case = TestCase.model_validate(data)
        assert test_case.id == "TEST-001"
        assert test_case.category == TestCaseCategory.ROUTING
        assert test_case.is_regression is True


class TestGradeResult:
    """Tests for GradeResult model."""

    def test_create_passing_result(self) -> None:
        """Test creating a passing grade result."""
        result = GradeResult(
            score=0.95,
            passed=True,
            reasoning="All criteria met successfully.",
            metrics={"accuracy": 0.95, "f1": 0.92},
        )
        assert result.score == 0.95
        assert result.passed is True
        assert result.reasoning == "All criteria met successfully."
        assert result.metrics is not None
        assert result.metrics["accuracy"] == 0.95

    def test_create_failing_result(self) -> None:
        """Test creating a failing grade result."""
        result = GradeResult(
            score=0.45,
            passed=False,
            reasoning="Citation not found in source documents.",
        )
        assert result.score == 0.45
        assert result.passed is False
        assert result.metrics is None

    def test_score_validation_range(self) -> None:
        """Test score must be between 0 and 1."""
        with pytest.raises(ValidationError):
            GradeResult(score=1.5, passed=True)
        with pytest.raises(ValidationError):
            GradeResult(score=-0.1, passed=True)


class TestTestCaseResult:
    """Tests for TestCaseResult model."""

    def test_create_result(self) -> None:
        """Test creating a test case result."""
        test_case = TestCase(
            id="TEST-001",
            category=TestCaseCategory.ROUTING,
            query="Test query",
        )
        grade = GradeResult(score=0.85, passed=True, reasoning="Good result.")
        result = TestCaseResult(
            test_case=test_case,
            grade=grade,
            actual_output={"route": "knowledge_base"},
            duration_ms=125.5,
        )
        assert result.test_case.id == "TEST-001"
        assert result.grade.passed is True
        assert result.actual_output is not None
        assert result.actual_output["route"] == "knowledge_base"
        assert result.duration_ms == 125.5

    def test_result_without_output(self) -> None:
        """Test creating result when grading failed."""
        test_case = TestCase(
            id="TEST-001",
            category=TestCaseCategory.ROUTING,
            query="Test query",
        )
        grade = GradeResult(score=0.0, passed=False, reasoning="Execution error.")
        result = TestCaseResult(
            test_case=test_case,
            grade=grade,
            duration_ms=50.0,
        )
        assert result.actual_output is None
        assert result.grade.passed is False
