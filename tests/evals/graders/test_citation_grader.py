"""Tests for citation grader.

TDD: RED phase - Write tests first, then implement.
"""

import pytest

from evals.graders.citation_grader import (
    CitationGrader,
    CitationMatch,
    CitationMetrics,
)
from evals.schemas.test_case import (
    GradeResult,
    TestCase,
    TestCaseCategory,
)


class TestCitationMatch:
    """Tests for CitationMatch data class."""

    def test_create_valid_citation(self) -> None:
        """Test creating a valid citation match."""
        match = CitationMatch(
            citation_text="Art. 5 D.Lgs. 446/1997",
            found_in_sources=True,
            source_id="DOC-001",
            is_hallucinated=False,
        )
        assert match.citation_text == "Art. 5 D.Lgs. 446/1997"
        assert match.found_in_sources is True
        assert match.is_hallucinated is False

    def test_hallucinated_citation(self) -> None:
        """Test a hallucinated citation."""
        match = CitationMatch(
            citation_text="Legge 999/2099",
            found_in_sources=False,
            source_id=None,
            is_hallucinated=True,
        )
        assert match.is_hallucinated is True
        assert match.source_id is None


class TestCitationMetrics:
    """Tests for CitationMetrics data class."""

    def test_create_metrics(self) -> None:
        """Test creating citation metrics."""
        metrics = CitationMetrics(
            hallucination_rate=0.1,
            valid_citation_ratio=0.9,
            total_citations=10,
            valid_citations=9,
            hallucinated_citations=1,
            citation_matches=[],
        )
        assert metrics.hallucination_rate == 0.1
        assert metrics.valid_citation_ratio == 0.9

    def test_perfect_citations(self) -> None:
        """Test perfect citation metrics."""
        metrics = CitationMetrics(
            hallucination_rate=0.0,
            valid_citation_ratio=1.0,
            total_citations=5,
            valid_citations=5,
            hallucinated_citations=0,
            citation_matches=[],
        )
        assert metrics.hallucination_rate == 0.0


class TestCitationGrader:
    """Tests for CitationGrader."""

    @pytest.fixture
    def grader(self) -> CitationGrader:
        """Create a citation grader instance."""
        return CitationGrader()

    def test_grade_all_valid_citations(self, grader: CitationGrader) -> None:
        """Test grading when all citations are valid."""
        test_case = TestCase(
            id="CITATION-001",
            category=TestCaseCategory.RESPONSE,
            query="Quali sono i benefici della Legge 104?",
            expected_citations=["Legge 104/1992", "Art. 3 L. 104/1992"],
        )
        response = {
            "text": "Secondo la Legge 104/1992, Art. 3 prevede benefici...",
            "citations": [
                {"text": "Legge 104/1992", "source_id": "DOC-001"},
                {"text": "Art. 3 L. 104/1992", "source_id": "DOC-001"},
            ],
        }
        source_docs = [
            {"id": "DOC-001", "content": "Legge 104/1992 Art. 3 benefici..."},
        ]
        result = grader.grade(test_case, response, source_docs)
        assert isinstance(result, GradeResult)
        assert result.passed is True
        assert result.metrics is not None
        assert result.metrics["hallucination_rate"] == 0.0
        assert result.metrics["valid_citation_ratio"] == 1.0

    def test_grade_hallucinated_citation(self, grader: CitationGrader) -> None:
        """Test grading when a citation is hallucinated."""
        test_case = TestCase(
            id="CITATION-002",
            category=TestCaseCategory.RESPONSE,
            query="Test query",
        )
        response = {
            "text": "Come previsto dalla Legge 999/2099...",
            "citations": [
                {"text": "Legge 999/2099", "source_id": None},  # Hallucinated
            ],
        }
        source_docs = [
            {"id": "DOC-001", "content": "Real content without fake law"},
        ]
        result = grader.grade(test_case, response, source_docs)
        assert result.passed is False
        assert result.metrics is not None
        assert result.metrics["hallucination_rate"] == 1.0
        assert result.metrics["hallucinated_citations"] == 1

    def test_grade_mixed_citations(self, grader: CitationGrader) -> None:
        """Test grading with mix of valid and hallucinated citations."""
        test_case = TestCase(
            id="CITATION-003",
            category=TestCaseCategory.RESPONSE,
            query="Test query",
        )
        response = {
            "citations": [
                {"text": "Legge 104/1992", "source_id": "DOC-001"},  # Valid
                {"text": "Art. 99 L. 999/2099", "source_id": None},  # Hallucinated
                {"text": "D.Lgs. 446/1997", "source_id": "DOC-002"},  # Valid
            ],
        }
        source_docs = [
            {"id": "DOC-001", "content": "Legge 104/1992..."},
            {"id": "DOC-002", "content": "D.Lgs. 446/1997..."},
        ]
        result = grader.grade(test_case, response, source_docs)
        # 1 hallucinated out of 3 = 33% hallucination rate
        assert result.metrics is not None
        assert abs(result.metrics["hallucination_rate"] - 0.333) < 0.01
        # 2 valid out of 3 = 67% valid ratio
        assert abs(result.metrics["valid_citation_ratio"] - 0.667) < 0.01

    def test_grade_no_citations(self, grader: CitationGrader) -> None:
        """Test grading when response has no citations."""
        test_case = TestCase(
            id="CITATION-004",
            category=TestCaseCategory.RESPONSE,
            query="Test query",
        )
        response = {
            "text": "A response without any citations.",
            "citations": [],
        }
        source_docs = [{"id": "DOC-001", "content": "..."}]
        result = grader.grade(test_case, response, source_docs)
        # No citations = no hallucinations possible
        assert result.metrics is not None
        assert result.metrics["total_citations"] == 0
        assert result.metrics["hallucination_rate"] == 0.0

    def test_grade_citation_in_text_not_list(self, grader: CitationGrader) -> None:
        """Test extracting citations from text when not in list."""
        test_case = TestCase(
            id="CITATION-005",
            category=TestCaseCategory.RESPONSE,
            query="Test query",
        )
        # Response has citations mentioned in text but not in citations list
        response = {
            "text": "Secondo la Legge 104/1992 e il D.Lgs. 446/1997...",
            "citations": [],  # Empty list
        }
        source_docs = [
            {"id": "DOC-001", "content": "Legge 104/1992..."},
            {"id": "DOC-002", "content": "D.Lgs. 446/1997..."},
        ]
        # Grader should extract citations from text
        result = grader.grade(test_case, response, source_docs)
        assert result.metrics is not None
        assert result.metrics["total_citations"] >= 2

    def test_grade_citation_not_in_sources(self, grader: CitationGrader) -> None:
        """Test when citation reference exists but not in source docs."""
        test_case = TestCase(
            id="CITATION-006",
            category=TestCaseCategory.RESPONSE,
            query="Test query",
        )
        response = {
            "citations": [
                {"text": "Legge 104/1992", "source_id": "DOC-001"},
            ],
        }
        # Source doc doesn't contain the cited law
        source_docs = [
            {"id": "DOC-001", "content": "Completely unrelated content"},
        ]
        result = grader.grade(test_case, response, source_docs)
        # Citation claims source DOC-001 but content doesn't support it
        assert result.metrics is not None
        assert result.metrics["hallucination_rate"] > 0

    def test_grade_empty_response(self, grader: CitationGrader) -> None:
        """Test grading with empty response."""
        test_case = TestCase(
            id="CITATION-007",
            category=TestCaseCategory.RESPONSE,
            query="Test query",
        )
        result = grader.grade(test_case, {}, [])
        assert result.metrics is not None
        assert result.metrics["total_citations"] == 0

    def test_grade_none_response(self, grader: CitationGrader) -> None:
        """Test grading with None response."""
        test_case = TestCase(
            id="CITATION-008",
            category=TestCaseCategory.RESPONSE,
            query="Test query",
        )
        result = grader.grade(test_case, None, [])
        assert result.passed is False
        assert result.score == 0.0

    def test_grade_expected_citations_missing(self, grader: CitationGrader) -> None:
        """Test when expected citations are not present."""
        test_case = TestCase(
            id="CITATION-009",
            category=TestCaseCategory.RESPONSE,
            query="Test query",
            expected_citations=["Legge 104/1992", "Art. 3"],
        )
        response = {
            "text": "A response without the expected citations.",
            "citations": [],
        }
        source_docs = []
        result = grader.grade(test_case, response, source_docs)
        # Missing expected citations should lower score
        assert result.metrics is not None
        assert result.metrics.get("expected_citation_recall", 0.0) == 0.0

    def test_grade_partial_expected_citations(self, grader: CitationGrader) -> None:
        """Test when some expected citations are present."""
        test_case = TestCase(
            id="CITATION-010",
            category=TestCaseCategory.RESPONSE,
            query="Test query",
            expected_citations=["Legge 104/1992", "Art. 3", "D.Lgs. 81"],
        )
        response = {
            "citations": [
                {"text": "Legge 104/1992", "source_id": "DOC-001"},
                # Missing Art. 3 and D.Lgs. 81
            ],
        }
        source_docs = [
            {"id": "DOC-001", "content": "Legge 104/1992..."},
        ]
        result = grader.grade(test_case, response, source_docs)
        # 1 out of 3 expected = 33% recall
        assert result.metrics is not None
        assert abs(result.metrics.get("expected_citation_recall", 0) - 0.333) < 0.01

    def test_grade_score_weighting(self, grader: CitationGrader) -> None:
        """Test that score is correctly weighted."""
        test_case = TestCase(
            id="CITATION-011",
            category=TestCaseCategory.RESPONSE,
            query="Test query",
        )
        response = {
            "citations": [
                {"text": "Legge 104/1992", "source_id": "DOC-001"},
                {"text": "D.Lgs. 446/1997", "source_id": "DOC-002"},
            ],
        }
        source_docs = [
            {"id": "DOC-001", "content": "Legge 104/1992..."},
            {"id": "DOC-002", "content": "D.Lgs. 446/1997..."},
        ]
        result = grader.grade(test_case, response, source_docs)
        # All valid = high score
        assert result.score >= 0.9
        assert result.passed is True

    def test_extract_italian_law_citations(self, grader: CitationGrader) -> None:
        """Test extraction of Italian law citation patterns."""
        test_case = TestCase(
            id="CITATION-012",
            category=TestCaseCategory.RESPONSE,
            query="Test query",
        )
        response = {
            "text": """
            Secondo la Legge 104/1992 e il D.Lgs. 446/1997,
            come previsto dall'Art. 3 comma 2 della L. 234/2021,
            e in base al D.P.R. 633/1972...
            """,
            "citations": [],
        }
        source_docs = [
            {"id": "DOC-001", "content": "Legge 104/1992 D.Lgs. 446/1997 Art. 3 L. 234/2021 D.P.R. 633/1972"},
        ]
        result = grader.grade(test_case, response, source_docs)
        # Should extract multiple citation patterns
        assert result.metrics is not None
        assert result.metrics["total_citations"] >= 4

    def test_case_insensitive_citation_matching(self, grader: CitationGrader) -> None:
        """Test that citation matching is case-insensitive."""
        test_case = TestCase(
            id="CITATION-013",
            category=TestCaseCategory.RESPONSE,
            query="Test query",
        )
        response = {
            "citations": [
                {"text": "legge 104/1992", "source_id": "DOC-001"},  # lowercase
            ],
        }
        source_docs = [
            {"id": "DOC-001", "content": "LEGGE 104/1992..."},  # uppercase
        ]
        result = grader.grade(test_case, response, source_docs)
        assert result.metrics is not None
        assert result.metrics["valid_citation_ratio"] == 1.0
