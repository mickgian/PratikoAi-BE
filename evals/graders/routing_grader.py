"""Routing grader for evaluating query routing decisions.

Evaluates Step 34a of the LangGraph RAG pipeline - LLM Router semantic
classification of user queries into routing categories.

Metrics:
- Route accuracy: Did the router select the correct category?
- Confidence calibration: Is the confidence score well-calibrated?
- Entity F1: Are the extracted entities correct?
"""

from dataclasses import dataclass
from typing import Any

from evals.schemas.test_case import GradeResult, TestCase


@dataclass
class EntityMatch:
    """Result of matching an expected entity to actual entities.

    Attributes:
        expected_text: Text of the expected entity
        expected_type: Type of the expected entity
        actual_text: Text of the matched actual entity (if found)
        actual_type: Type of the matched actual entity (if found)
        matched: Whether a match was found
    """

    expected_text: str
    expected_type: str
    actual_text: str | None
    actual_type: str | None
    matched: bool


@dataclass
class RoutingMetrics:
    """Metrics from routing evaluation.

    Attributes:
        route_correct: Whether the route was classified correctly
        route_accuracy: Binary accuracy score (1.0 if correct, 0.0 if not)
        confidence: Confidence score from the router
        confidence_calibration_error: Error between confidence and actual accuracy
        entity_precision: Precision of entity extraction
        entity_recall: Recall of entity extraction
        entity_f1: F1 score of entity extraction
        entity_matches: Detailed entity matching results
    """

    route_correct: bool | None
    route_accuracy: float
    confidence: float
    confidence_calibration_error: float
    entity_precision: float
    entity_recall: float
    entity_f1: float
    entity_matches: list[EntityMatch]


class RoutingGrader:
    """Grader for evaluating routing decisions.

    Evaluates:
    1. Route accuracy - Did the router classify the query correctly?
    2. Confidence calibration - Is the confidence score well-calibrated?
    3. Entity F1 - Are the extracted entities correct?

    Score weighting:
    - Route accuracy: 60%
    - Entity F1: 30%
    - Confidence calibration: 10%
    """

    # Score weights
    ROUTE_WEIGHT = 0.6
    ENTITY_WEIGHT = 0.3
    CONFIDENCE_WEIGHT = 0.1

    def grade(
        self,
        test_case: TestCase,
        actual_output: dict[str, Any] | None,
        expected_entities: list[dict[str, str]] | None = None,
    ) -> GradeResult:
        """Grade a routing decision.

        Args:
            test_case: Test case with expected route
            actual_output: Actual router output with route, confidence, entities
            expected_entities: Optional list of expected entities for F1 calculation

        Returns:
            GradeResult with score, pass/fail, reasoning, and metrics
        """
        if actual_output is None or not actual_output:
            return GradeResult(
                score=0.0,
                passed=False,
                reasoning="Actual output is missing or empty.",
                metrics={
                    "route_correct": None,
                    "route_accuracy": 0.0,
                    "confidence": 0.0,
                    "confidence_calibration_error": 1.0,
                    "entity_precision": 0.0,
                    "entity_recall": 0.0,
                    "entity_f1": 0.0,
                    "entity_matches": [],
                },
            )

        actual_route = actual_output.get("route")
        if actual_route is None:
            return GradeResult(
                score=0.0,
                passed=False,
                reasoning="Route is missing from actual output.",
                metrics={
                    "route_correct": None,
                    "route_accuracy": 0.0,
                    "confidence": actual_output.get("confidence", 0.0),
                    "confidence_calibration_error": 1.0,
                    "entity_precision": 0.0,
                    "entity_recall": 0.0,
                    "entity_f1": 0.0,
                    "entity_matches": [],
                },
            )

        metrics = self._compute_metrics(
            test_case=test_case,
            actual_output=actual_output,
            expected_entities=expected_entities,
        )

        score = self._compute_score(metrics)
        passed = score >= test_case.pass_threshold
        reasoning = self._generate_reasoning(metrics)

        return GradeResult(
            score=score,
            passed=passed,
            reasoning=reasoning,
            metrics={
                "route_correct": metrics.route_correct,
                "route_accuracy": metrics.route_accuracy,
                "confidence": metrics.confidence,
                "confidence_calibration_error": metrics.confidence_calibration_error,
                "entity_precision": metrics.entity_precision,
                "entity_recall": metrics.entity_recall,
                "entity_f1": metrics.entity_f1,
                "entity_matches": [
                    {
                        "expected_text": m.expected_text,
                        "expected_type": m.expected_type,
                        "actual_text": m.actual_text,
                        "actual_type": m.actual_type,
                        "matched": m.matched,
                    }
                    for m in metrics.entity_matches
                ],
            },
        )

    def _compute_metrics(
        self,
        test_case: TestCase,
        actual_output: dict[str, Any],
        expected_entities: list[dict[str, str]] | None,
    ) -> RoutingMetrics:
        """Compute routing evaluation metrics.

        Args:
            test_case: Test case with expected route
            actual_output: Actual router output
            expected_entities: Expected entities for F1 calculation

        Returns:
            RoutingMetrics with all computed values
        """
        actual_route = actual_output.get("route", "").lower()
        confidence = actual_output.get("confidence", 0.0)
        actual_entities = actual_output.get("entities", [])

        # Route accuracy
        route_correct = None
        route_accuracy = 0.0
        if test_case.expected_route:
            expected_route = test_case.expected_route.lower()
            route_correct = actual_route == expected_route
            route_accuracy = 1.0 if route_correct else 0.0

        # Confidence calibration error
        # Calibration error = |confidence - actual_accuracy|
        if route_correct is not None:
            calibration_error = abs(confidence - route_accuracy)
        else:
            calibration_error = 0.0

        # Entity matching
        entity_matches: list[EntityMatch] = []
        entity_precision = 1.0
        entity_recall = 1.0
        entity_f1 = 1.0

        if expected_entities:
            true_positives = 0
            for expected in expected_entities:
                matched = self._find_entity_match(expected, actual_entities)
                entity_matches.append(matched)
                if matched.matched:
                    true_positives += 1

            precision = (
                true_positives / len(actual_entities) if actual_entities else (1.0 if not expected_entities else 0.0)
            )
            recall = true_positives / len(expected_entities) if expected_entities else 1.0
            if precision + recall > 0:
                f1 = 2 * (precision * recall) / (precision + recall)
            else:
                f1 = 0.0

            entity_precision = precision
            entity_recall = recall
            entity_f1 = f1

        return RoutingMetrics(
            route_correct=route_correct,
            route_accuracy=route_accuracy,
            confidence=confidence,
            confidence_calibration_error=calibration_error,
            entity_precision=entity_precision,
            entity_recall=entity_recall,
            entity_f1=entity_f1,
            entity_matches=entity_matches,
        )

    def _find_entity_match(
        self,
        expected: dict[str, str],
        actual_entities: list[dict[str, Any]],
    ) -> EntityMatch:
        """Find a match for an expected entity in actual entities.

        Args:
            expected: Expected entity with text and type
            actual_entities: List of actual extracted entities

        Returns:
            EntityMatch indicating whether a match was found
        """
        expected_text = expected.get("text", "").lower()
        expected_type = expected.get("type", "").lower()

        for actual in actual_entities:
            actual_text = actual.get("text", "").lower()
            actual_type = actual.get("type", "").lower()

            # Match by text (case-insensitive) and type
            if expected_text == actual_text and expected_type == actual_type:
                return EntityMatch(
                    expected_text=expected.get("text", ""),
                    expected_type=expected.get("type", ""),
                    actual_text=actual.get("text"),
                    actual_type=actual.get("type"),
                    matched=True,
                )

        # No match found
        return EntityMatch(
            expected_text=expected.get("text", ""),
            expected_type=expected.get("type", ""),
            actual_text=None,
            actual_type=None,
            matched=False,
        )

    def _compute_score(self, metrics: RoutingMetrics) -> float:
        """Compute weighted score from metrics.

        Args:
            metrics: Computed routing metrics

        Returns:
            Weighted score between 0.0 and 1.0
        """
        # If we don't have an expected route, base score on entities only
        if metrics.route_correct is None:
            return metrics.entity_f1

        # Weighted combination
        score = (
            self.ROUTE_WEIGHT * metrics.route_accuracy
            + self.ENTITY_WEIGHT * metrics.entity_f1
            + self.CONFIDENCE_WEIGHT * (1.0 - metrics.confidence_calibration_error)
        )
        return min(1.0, max(0.0, score))

    def _generate_reasoning(self, metrics: RoutingMetrics) -> str:
        """Generate human-readable reasoning from metrics.

        Args:
            metrics: Computed routing metrics

        Returns:
            Reasoning string
        """
        parts = []

        if metrics.route_correct is True:
            parts.append(f"Route correctly classified (confidence: {metrics.confidence:.2f})")
        elif metrics.route_correct is False:
            parts.append(f"Route incorrectly classified (confidence: {metrics.confidence:.2f})")
        else:
            parts.append("No expected route to compare")

        if metrics.entity_f1 < 1.0:
            parts.append(
                f"Entity extraction: precision={metrics.entity_precision:.2f}, "
                f"recall={metrics.entity_recall:.2f}, F1={metrics.entity_f1:.2f}"
            )

        if metrics.confidence_calibration_error > 0.3:
            parts.append(f"Confidence calibration error: {metrics.confidence_calibration_error:.2f}")

        return ". ".join(parts) + "."
