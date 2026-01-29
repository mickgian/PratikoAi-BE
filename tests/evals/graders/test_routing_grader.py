"""Tests for routing grader.

TDD: RED phase - Write tests first, then implement.
"""

import pytest

from evals.graders.routing_grader import (
    EntityMatch,
    RoutingGrader,
    RoutingMetrics,
)
from evals.schemas.test_case import (
    GradeResult,
    TestCase,
    TestCaseCategory,
)


class TestEntityMatch:
    """Tests for EntityMatch data class."""

    def test_create_entity_match(self) -> None:
        """Test creating an entity match."""
        match = EntityMatch(
            expected_text="Legge 104/1992",
            expected_type="legge",
            actual_text="Legge 104/1992",
            actual_type="legge",
            matched=True,
        )
        assert match.expected_text == "Legge 104/1992"
        assert match.matched is True

    def test_unmatched_entity(self) -> None:
        """Test entity that didn't match."""
        match = EntityMatch(
            expected_text="Art. 3",
            expected_type="articolo",
            actual_text=None,
            actual_type=None,
            matched=False,
        )
        assert match.matched is False
        assert match.actual_text is None


class TestRoutingMetrics:
    """Tests for RoutingMetrics data class."""

    def test_create_metrics(self) -> None:
        """Test creating routing metrics."""
        metrics = RoutingMetrics(
            route_correct=True,
            route_accuracy=1.0,
            confidence=0.95,
            confidence_calibration_error=0.05,
            entity_precision=0.9,
            entity_recall=0.8,
            entity_f1=0.85,
            entity_matches=[],
        )
        assert metrics.route_accuracy == 1.0
        assert metrics.entity_f1 == 0.85

    def test_perfect_metrics(self) -> None:
        """Test perfect routing metrics."""
        metrics = RoutingMetrics(
            route_correct=True,
            route_accuracy=1.0,
            confidence=0.98,
            confidence_calibration_error=0.02,
            entity_precision=1.0,
            entity_recall=1.0,
            entity_f1=1.0,
            entity_matches=[],
        )
        assert metrics.route_correct is True
        assert metrics.entity_f1 == 1.0


class TestRoutingGrader:
    """Tests for RoutingGrader."""

    @pytest.fixture
    def grader(self) -> RoutingGrader:
        """Create a routing grader instance."""
        return RoutingGrader()

    def test_grade_correct_route(self, grader: RoutingGrader) -> None:
        """Test grading when route is correct."""
        test_case = TestCase(
            id="ROUTING-001",
            category=TestCaseCategory.ROUTING,
            query="Qual è la scadenza per la rottamazione quinquies?",
            expected_route="technical_research",
        )
        actual_output = {
            "route": "technical_research",
            "confidence": 0.92,
            "entities": [],
        }
        result = grader.grade(test_case, actual_output)
        assert isinstance(result, GradeResult)
        assert result.passed is True
        assert result.score >= 0.9
        assert result.metrics is not None
        assert result.metrics["route_correct"] is True

    def test_grade_incorrect_route(self, grader: RoutingGrader) -> None:
        """Test grading when route is incorrect."""
        test_case = TestCase(
            id="ROUTING-002",
            category=TestCaseCategory.ROUTING,
            query="Qual è la scadenza per la rottamazione quinquies?",
            expected_route="technical_research",
        )
        actual_output = {
            "route": "chitchat",
            "confidence": 0.85,
            "entities": [],
        }
        result = grader.grade(test_case, actual_output)
        assert result.passed is False
        assert result.score < 0.7
        assert result.metrics is not None
        assert result.metrics["route_correct"] is False

    def test_grade_with_entity_matching(self, grader: RoutingGrader) -> None:
        """Test grading with entity extraction evaluation."""
        test_case = TestCase(
            id="ROUTING-003",
            category=TestCaseCategory.ROUTING,
            query="Quali sono i benefici della Legge 104/1992?",
            expected_route="golden_set",
        )
        # Add expected entities to the test case
        test_case_with_entities = test_case.model_copy()
        actual_output = {
            "route": "golden_set",
            "confidence": 0.98,
            "entities": [
                {"text": "Legge 104/1992", "type": "legge", "confidence": 0.98},
            ],
        }
        # Provide expected entities as part of actual_output for comparison
        expected_entities = [
            {"text": "Legge 104/1992", "type": "legge"},
        ]
        result = grader.grade(
            test_case_with_entities,
            actual_output,
            expected_entities=expected_entities,
        )
        assert result.passed is True
        assert result.metrics is not None
        assert result.metrics["entity_f1"] == 1.0

    def test_grade_partial_entity_match(self, grader: RoutingGrader) -> None:
        """Test grading with partial entity matches."""
        test_case = TestCase(
            id="ROUTING-004",
            category=TestCaseCategory.ROUTING,
            query="Art. 3 della Legge 104/1992 sui permessi lavorativi",
            expected_route="golden_set",
        )
        actual_output = {
            "route": "golden_set",
            "confidence": 0.95,
            "entities": [
                {"text": "Legge 104/1992", "type": "legge", "confidence": 0.98},
                # Missing: Art. 3
            ],
        }
        expected_entities = [
            {"text": "Legge 104/1992", "type": "legge"},
            {"text": "Art. 3", "type": "articolo"},
        ]
        result = grader.grade(
            test_case,
            actual_output,
            expected_entities=expected_entities,
        )
        # Precision: 1/1 = 1.0, Recall: 1/2 = 0.5, F1 = 2*(1*0.5)/(1+0.5) = 0.667
        assert result.metrics is not None
        assert result.metrics["entity_precision"] == 1.0
        assert result.metrics["entity_recall"] == 0.5
        assert 0.66 < result.metrics["entity_f1"] < 0.68

    def test_grade_confidence_calibration_good(self, grader: RoutingGrader) -> None:
        """Test confidence calibration when well-calibrated."""
        test_case = TestCase(
            id="ROUTING-005",
            category=TestCaseCategory.ROUTING,
            query="Ciao, come stai?",
            expected_route="chitchat",
        )
        actual_output = {
            "route": "chitchat",
            "confidence": 0.95,
            "entities": [],
        }
        result = grader.grade(test_case, actual_output)
        # Correct route with high confidence = low calibration error
        assert result.metrics is not None
        assert result.metrics["confidence_calibration_error"] < 0.1

    def test_grade_confidence_calibration_overconfident(self, grader: RoutingGrader) -> None:
        """Test confidence calibration when overconfident on wrong answer."""
        test_case = TestCase(
            id="ROUTING-006",
            category=TestCaseCategory.ROUTING,
            query="Come funziona il bonus 110%?",
            expected_route="technical_research",
        )
        actual_output = {
            "route": "chitchat",  # Wrong!
            "confidence": 0.99,  # Very confident but wrong
            "entities": [],
        }
        result = grader.grade(test_case, actual_output)
        # High confidence on wrong answer = high calibration error
        assert result.metrics is not None
        assert result.metrics["confidence_calibration_error"] > 0.5

    def test_grade_missing_route(self, grader: RoutingGrader) -> None:
        """Test grading when actual output has no route."""
        test_case = TestCase(
            id="ROUTING-007",
            category=TestCaseCategory.ROUTING,
            query="Test query",
            expected_route="technical_research",
        )
        actual_output = {"confidence": 0.5, "entities": []}  # Missing route
        result = grader.grade(test_case, actual_output)
        assert result.passed is False
        assert result.score == 0.0
        assert "missing" in result.reasoning.lower()

    def test_grade_empty_output(self, grader: RoutingGrader) -> None:
        """Test grading with empty output."""
        test_case = TestCase(
            id="ROUTING-008",
            category=TestCaseCategory.ROUTING,
            query="Test query",
            expected_route="technical_research",
        )
        result = grader.grade(test_case, {})
        assert result.passed is False
        assert result.score == 0.0

    def test_grade_null_output(self, grader: RoutingGrader) -> None:
        """Test grading with null output."""
        test_case = TestCase(
            id="ROUTING-009",
            category=TestCaseCategory.ROUTING,
            query="Test query",
            expected_route="technical_research",
        )
        result = grader.grade(test_case, None)
        assert result.passed is False
        assert result.score == 0.0

    def test_grade_no_expected_route(self, grader: RoutingGrader) -> None:
        """Test grading when test case has no expected route."""
        test_case = TestCase(
            id="ROUTING-010",
            category=TestCaseCategory.ROUTING,
            query="Test query",
            # No expected_route
        )
        actual_output = {
            "route": "technical_research",
            "confidence": 0.9,
            "entities": [],
        }
        result = grader.grade(test_case, actual_output)
        # Without expected route, can only evaluate entity extraction
        assert result.metrics is not None
        assert result.metrics["route_correct"] is None

    def test_compute_score_weighting(self, grader: RoutingGrader) -> None:
        """Test that score is correctly weighted."""
        test_case = TestCase(
            id="ROUTING-011",
            category=TestCaseCategory.ROUTING,
            query="Legge 104/1992 art. 3",
            expected_route="golden_set",
        )
        actual_output = {
            "route": "golden_set",  # Correct
            "confidence": 0.95,
            "entities": [
                {"text": "Legge 104/1992", "type": "legge", "confidence": 0.95},
            ],
        }
        expected_entities = [
            {"text": "Legge 104/1992", "type": "legge"},
            {"text": "Art. 3", "type": "articolo"},
        ]
        result = grader.grade(
            test_case,
            actual_output,
            expected_entities=expected_entities,
        )
        # Score should weight route accuracy heavily
        # Route: 1.0 (correct) - weight 0.6
        # Entity F1: 0.667 - weight 0.3
        # Confidence: low error - weight 0.1
        assert 0.8 < result.score < 0.95

    def test_grade_case_insensitive_route(self, grader: RoutingGrader) -> None:
        """Test that route comparison is case-insensitive."""
        test_case = TestCase(
            id="ROUTING-012",
            category=TestCaseCategory.ROUTING,
            query="Test query",
            expected_route="TECHNICAL_RESEARCH",
        )
        actual_output = {
            "route": "technical_research",
            "confidence": 0.9,
            "entities": [],
        }
        result = grader.grade(test_case, actual_output)
        assert result.metrics is not None
        assert result.metrics["route_correct"] is True

    def test_grade_all_routes(self, grader: RoutingGrader) -> None:
        """Test grading works for all route types."""
        routes = [
            "chitchat",
            "theoretical_definition",
            "technical_research",
            "calculator",
            "golden_set",
        ]
        for route in routes:
            test_case = TestCase(
                id=f"ROUTING-{route}",
                category=TestCaseCategory.ROUTING,
                query="Test query",
                expected_route=route,
            )
            actual_output = {
                "route": route,
                "confidence": 0.9,
                "entities": [],
            }
            result = grader.grade(test_case, actual_output)
            assert result.passed is True
            assert result.metrics is not None
            assert result.metrics["route_correct"] is True
