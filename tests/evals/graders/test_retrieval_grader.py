"""Tests for retrieval grader.

TDD: RED phase - Write tests first, then implement.
"""

import pytest

from evals.graders.retrieval_grader import (
    RetrievalGrader,
    RetrievalMetrics,
)
from evals.schemas.test_case import (
    GradeResult,
    TestCase,
    TestCaseCategory,
)


class TestRetrievalMetrics:
    """Tests for RetrievalMetrics data class."""

    def test_create_metrics(self) -> None:
        """Test creating retrieval metrics."""
        metrics = RetrievalMetrics(
            precision_at_k=0.8,
            recall_at_k=0.6,
            mrr=0.75,
            ndcg=0.82,
            source_authority_coverage=0.9,
            retrieved_count=10,
            relevant_count=5,
            hits_at_k=4,
        )
        assert metrics.precision_at_k == 0.8
        assert metrics.mrr == 0.75
        assert metrics.ndcg == 0.82

    def test_perfect_retrieval(self) -> None:
        """Test perfect retrieval metrics."""
        metrics = RetrievalMetrics(
            precision_at_k=1.0,
            recall_at_k=1.0,
            mrr=1.0,
            ndcg=1.0,
            source_authority_coverage=1.0,
            retrieved_count=5,
            relevant_count=5,
            hits_at_k=5,
        )
        assert metrics.precision_at_k == 1.0
        assert metrics.recall_at_k == 1.0


class TestRetrievalGrader:
    """Tests for RetrievalGrader."""

    @pytest.fixture
    def grader(self) -> RetrievalGrader:
        """Create a retrieval grader instance."""
        return RetrievalGrader()

    def test_grade_perfect_retrieval(self, grader: RetrievalGrader) -> None:
        """Test grading when all expected documents are retrieved."""
        test_case = TestCase(
            id="RETRIEVAL-001",
            category=TestCaseCategory.RETRIEVAL,
            query="Qual è la scadenza per la rottamazione quinquies?",
            expected_sources=["DOC-001", "DOC-002", "DOC-003"],
        )
        retrieved_docs = [
            {"id": "DOC-001", "score": 0.95},
            {"id": "DOC-002", "score": 0.90},
            {"id": "DOC-003", "score": 0.85},
            {"id": "DOC-004", "score": 0.70},
        ]
        result = grader.grade(test_case, retrieved_docs)
        assert isinstance(result, GradeResult)
        assert result.passed is True
        assert result.metrics is not None
        assert result.metrics["recall_at_k"] == 1.0
        # Precision: 3 relevant out of 4 retrieved = 0.75
        assert result.metrics["precision_at_k"] == 0.75

    def test_grade_partial_retrieval(self, grader: RetrievalGrader) -> None:
        """Test grading when only some expected documents are retrieved."""
        test_case = TestCase(
            id="RETRIEVAL-002",
            category=TestCaseCategory.RETRIEVAL,
            query="Come calcolare l'IRAP?",
            expected_sources=["DOC-A", "DOC-B", "DOC-C", "DOC-D"],
        )
        retrieved_docs = [
            {"id": "DOC-A", "score": 0.95},
            {"id": "DOC-B", "score": 0.90},
            {"id": "DOC-X", "score": 0.85},  # Not expected
        ]
        result = grader.grade(test_case, retrieved_docs)
        # Recall: 2/4 = 0.5
        assert result.metrics is not None
        assert result.metrics["recall_at_k"] == 0.5
        # Precision: 2/3 = 0.667
        assert abs(result.metrics["precision_at_k"] - 0.667) < 0.01

    def test_grade_no_relevant_docs(self, grader: RetrievalGrader) -> None:
        """Test grading when no expected documents are retrieved."""
        test_case = TestCase(
            id="RETRIEVAL-003",
            category=TestCaseCategory.RETRIEVAL,
            query="Test query",
            expected_sources=["DOC-X", "DOC-Y"],
        )
        retrieved_docs = [
            {"id": "DOC-A", "score": 0.95},
            {"id": "DOC-B", "score": 0.90},
        ]
        result = grader.grade(test_case, retrieved_docs)
        assert result.passed is False
        assert result.metrics is not None
        assert result.metrics["recall_at_k"] == 0.0
        assert result.metrics["precision_at_k"] == 0.0
        assert result.metrics["mrr"] == 0.0

    def test_grade_mrr_first_position(self, grader: RetrievalGrader) -> None:
        """Test MRR when relevant doc is in first position."""
        test_case = TestCase(
            id="RETRIEVAL-004",
            category=TestCaseCategory.RETRIEVAL,
            query="Test query",
            expected_sources=["DOC-TARGET"],
        )
        retrieved_docs = [
            {"id": "DOC-TARGET", "score": 0.99},  # First position
            {"id": "DOC-B", "score": 0.80},
        ]
        result = grader.grade(test_case, retrieved_docs)
        assert result.metrics is not None
        assert result.metrics["mrr"] == 1.0

    def test_grade_mrr_third_position(self, grader: RetrievalGrader) -> None:
        """Test MRR when first relevant doc is in third position."""
        test_case = TestCase(
            id="RETRIEVAL-005",
            category=TestCaseCategory.RETRIEVAL,
            query="Test query",
            expected_sources=["DOC-TARGET"],
        )
        retrieved_docs = [
            {"id": "DOC-A", "score": 0.99},
            {"id": "DOC-B", "score": 0.95},
            {"id": "DOC-TARGET", "score": 0.90},  # Third position
            {"id": "DOC-D", "score": 0.85},
        ]
        result = grader.grade(test_case, retrieved_docs)
        # MRR = 1/3 = 0.333
        assert result.metrics is not None
        assert abs(result.metrics["mrr"] - 0.333) < 0.01

    def test_grade_ndcg_perfect_ranking(self, grader: RetrievalGrader) -> None:
        """Test NDCG when ranking is perfect."""
        test_case = TestCase(
            id="RETRIEVAL-006",
            category=TestCaseCategory.RETRIEVAL,
            query="Test query",
            expected_sources=["DOC-1", "DOC-2"],
        )
        retrieved_docs = [
            {"id": "DOC-1", "score": 0.99},  # Relevant at rank 1
            {"id": "DOC-2", "score": 0.95},  # Relevant at rank 2
            {"id": "DOC-X", "score": 0.90},  # Not relevant
        ]
        result = grader.grade(test_case, retrieved_docs)
        assert result.metrics is not None
        assert result.metrics["ndcg"] == 1.0

    def test_grade_ndcg_imperfect_ranking(self, grader: RetrievalGrader) -> None:
        """Test NDCG when relevant docs are not at top."""
        test_case = TestCase(
            id="RETRIEVAL-007",
            category=TestCaseCategory.RETRIEVAL,
            query="Test query",
            expected_sources=["DOC-1", "DOC-2"],
        )
        retrieved_docs = [
            {"id": "DOC-X", "score": 0.99},  # Not relevant at rank 1
            {"id": "DOC-1", "score": 0.95},  # Relevant at rank 2
            {"id": "DOC-Y", "score": 0.90},  # Not relevant
            {"id": "DOC-2", "score": 0.85},  # Relevant at rank 4
        ]
        result = grader.grade(test_case, retrieved_docs)
        # NDCG should be less than 1.0 since ranking is not ideal
        assert result.metrics is not None
        assert result.metrics["ndcg"] < 1.0
        assert result.metrics["ndcg"] > 0.0

    def test_grade_empty_retrieved(self, grader: RetrievalGrader) -> None:
        """Test grading with no retrieved documents."""
        test_case = TestCase(
            id="RETRIEVAL-008",
            category=TestCaseCategory.RETRIEVAL,
            query="Test query",
            expected_sources=["DOC-A"],
        )
        result = grader.grade(test_case, [])
        assert result.passed is False
        assert result.score == 0.0
        assert result.metrics is not None
        assert result.metrics["retrieved_count"] == 0

    def test_grade_no_expected_sources(self, grader: RetrievalGrader) -> None:
        """Test grading when test case has no expected sources."""
        test_case = TestCase(
            id="RETRIEVAL-009",
            category=TestCaseCategory.RETRIEVAL,
            query="Test query",
            # No expected_sources
        )
        retrieved_docs = [
            {"id": "DOC-A", "score": 0.95},
        ]
        result = grader.grade(test_case, retrieved_docs)
        # Without expected sources, can only evaluate retrieval happened
        assert result.metrics is not None
        assert result.metrics["retrieved_count"] == 1

    def test_grade_with_custom_k(self, grader: RetrievalGrader) -> None:
        """Test grading with custom k value."""
        test_case = TestCase(
            id="RETRIEVAL-010",
            category=TestCaseCategory.RETRIEVAL,
            query="Test query",
            expected_sources=["DOC-1", "DOC-2", "DOC-3"],
        )
        retrieved_docs = [
            {"id": "DOC-1", "score": 0.99},
            {"id": "DOC-X", "score": 0.95},
            {"id": "DOC-2", "score": 0.90},
            {"id": "DOC-Y", "score": 0.85},
            {"id": "DOC-3", "score": 0.80},  # At position 5
        ]
        # With k=3, only consider first 3 documents
        result = grader.grade(test_case, retrieved_docs, k=3)
        # Only DOC-1 and DOC-2 are in top 3, DOC-3 is at position 5
        assert result.metrics is not None
        assert result.metrics["hits_at_k"] == 2  # DOC-1 and DOC-2

    def test_grade_source_authority_coverage(self, grader: RetrievalGrader) -> None:
        """Test source authority coverage calculation."""
        test_case = TestCase(
            id="RETRIEVAL-011",
            category=TestCaseCategory.RETRIEVAL,
            query="Test query",
            expected_sources=["INPS-001", "ADE-001", "NORMATTIVA-001"],
        )
        retrieved_docs = [
            {"id": "INPS-001", "score": 0.95, "source_type": "inps"},
            {"id": "ADE-001", "score": 0.90, "source_type": "agenzia_entrate"},
            {"id": "DOC-X", "score": 0.85, "source_type": "other"},
        ]
        high_authority_sources = ["inps", "agenzia_entrate", "normattiva"]
        result = grader.grade(
            test_case,
            retrieved_docs,
            high_authority_sources=high_authority_sources,
        )
        # 2 out of 3 retrieved are high authority
        assert result.metrics is not None
        assert abs(result.metrics["source_authority_coverage"] - 0.667) < 0.01

    def test_grade_dict_output_format(self, grader: RetrievalGrader) -> None:
        """Test grading with dict-style output (from actual system)."""
        test_case = TestCase(
            id="RETRIEVAL-012",
            category=TestCaseCategory.RETRIEVAL,
            query="Test query",
            expected_sources=["DOC-A"],
        )
        actual_output = {
            "documents": [
                {"id": "DOC-A", "score": 0.95, "content": "..."},
                {"id": "DOC-B", "score": 0.90, "content": "..."},
            ]
        }
        # Grader should handle dict with "documents" key
        result = grader.grade(test_case, actual_output["documents"])
        assert result.metrics is not None
        assert result.metrics["retrieved_count"] == 2

    def test_grade_score_weighting(self, grader: RetrievalGrader) -> None:
        """Test that score is correctly weighted."""
        test_case = TestCase(
            id="RETRIEVAL-013",
            category=TestCaseCategory.RETRIEVAL,
            query="Test query",
            expected_sources=["DOC-1", "DOC-2"],
        )
        retrieved_docs = [
            {"id": "DOC-1", "score": 0.99},
            {"id": "DOC-2", "score": 0.95},
        ]
        result = grader.grade(test_case, retrieved_docs)
        # Perfect retrieval should give high score
        assert result.score >= 0.9
        assert result.passed is True

    def test_grade_none_retrieved(self, grader: RetrievalGrader) -> None:
        """Test grading with None as retrieved docs."""
        test_case = TestCase(
            id="RETRIEVAL-014",
            category=TestCaseCategory.RETRIEVAL,
            query="Test query",
            expected_sources=["DOC-A"],
        )
        result = grader.grade(test_case, None)
        assert result.passed is False
        assert result.score == 0.0

    def test_case_insensitive_doc_ids(self, grader: RetrievalGrader) -> None:
        """Test that document ID matching is case-insensitive."""
        test_case = TestCase(
            id="RETRIEVAL-015",
            category=TestCaseCategory.RETRIEVAL,
            query="Test query",
            expected_sources=["DOC-ABC"],
        )
        retrieved_docs = [
            {"id": "doc-abc", "score": 0.95},  # lowercase
        ]
        result = grader.grade(test_case, retrieved_docs)
        assert result.metrics is not None
        assert result.metrics["recall_at_k"] == 1.0
