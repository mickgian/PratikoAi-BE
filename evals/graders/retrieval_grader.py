"""Retrieval grader for evaluating document retrieval quality.

Evaluates Step 39a-39c of the LangGraph RAG pipeline - hybrid search
retrieval of relevant documents.

Metrics:
- Precision@k: Fraction of retrieved documents that are relevant
- Recall@k: Fraction of relevant documents that are retrieved
- MRR (Mean Reciprocal Rank): Position of first relevant document
- NDCG (Normalized Discounted Cumulative Gain): Ranking quality
- Source Authority Coverage: Fraction from high-authority sources
"""

import math
from dataclasses import dataclass
from typing import Any

from evals.schemas.test_case import GradeResult, TestCase


@dataclass
class RetrievalMetrics:
    """Metrics from retrieval evaluation.

    Attributes:
        precision_at_k: Fraction of retrieved docs that are relevant
        recall_at_k: Fraction of relevant docs that are retrieved
        mrr: Mean Reciprocal Rank (1/rank of first relevant doc)
        ndcg: Normalized Discounted Cumulative Gain
        source_authority_coverage: Fraction from high-authority sources
        retrieved_count: Number of documents retrieved
        relevant_count: Number of expected relevant documents
        hits_at_k: Number of relevant docs in top k
    """

    precision_at_k: float
    recall_at_k: float
    mrr: float
    ndcg: float
    source_authority_coverage: float
    retrieved_count: int
    relevant_count: int
    hits_at_k: int


class RetrievalGrader:
    """Grader for evaluating retrieval quality.

    Evaluates:
    1. Precision@k - What fraction of retrieved docs are relevant?
    2. Recall@k - What fraction of relevant docs were retrieved?
    3. MRR - How quickly do we find the first relevant doc?
    4. NDCG - How well are relevant docs ranked?
    5. Source authority coverage - Are we getting authoritative sources?

    Score weighting:
    - Recall@k: 35%
    - Precision@k: 25%
    - MRR: 20%
    - NDCG: 15%
    - Authority coverage: 5%
    """

    # Score weights
    RECALL_WEIGHT = 0.35
    PRECISION_WEIGHT = 0.25
    MRR_WEIGHT = 0.20
    NDCG_WEIGHT = 0.15
    AUTHORITY_WEIGHT = 0.05

    # Default k for top-k metrics
    DEFAULT_K = 10

    def grade(
        self,
        test_case: TestCase,
        retrieved_docs: list[dict[str, Any]] | None,
        k: int | None = None,
        high_authority_sources: list[str] | None = None,
    ) -> GradeResult:
        """Grade retrieval results.

        Args:
            test_case: Test case with expected source document IDs
            retrieved_docs: List of retrieved documents with id and score
            k: Number of top documents to consider (default: 10)
            high_authority_sources: List of high-authority source types

        Returns:
            GradeResult with score, pass/fail, reasoning, and metrics
        """
        k = k or self.DEFAULT_K

        if retrieved_docs is None:
            retrieved_docs = []

        if not retrieved_docs:
            return GradeResult(
                score=0.0,
                passed=False,
                reasoning="No documents retrieved.",
                metrics={
                    "precision_at_k": 0.0,
                    "recall_at_k": 0.0,
                    "mrr": 0.0,
                    "ndcg": 0.0,
                    "source_authority_coverage": 0.0,
                    "retrieved_count": 0,
                    "relevant_count": len(test_case.expected_sources or []),
                    "hits_at_k": 0,
                },
            )

        metrics = self._compute_metrics(
            test_case=test_case,
            retrieved_docs=retrieved_docs,
            k=k,
            high_authority_sources=high_authority_sources,
        )

        score = self._compute_score(metrics)
        passed = score >= test_case.pass_threshold
        reasoning = self._generate_reasoning(metrics, k)

        return GradeResult(
            score=score,
            passed=passed,
            reasoning=reasoning,
            metrics={
                "precision_at_k": metrics.precision_at_k,
                "recall_at_k": metrics.recall_at_k,
                "mrr": metrics.mrr,
                "ndcg": metrics.ndcg,
                "source_authority_coverage": metrics.source_authority_coverage,
                "retrieved_count": metrics.retrieved_count,
                "relevant_count": metrics.relevant_count,
                "hits_at_k": metrics.hits_at_k,
            },
        )

    def _compute_metrics(
        self,
        test_case: TestCase,
        retrieved_docs: list[dict[str, Any]],
        k: int,
        high_authority_sources: list[str] | None,
    ) -> RetrievalMetrics:
        """Compute retrieval evaluation metrics.

        Args:
            test_case: Test case with expected sources
            retrieved_docs: List of retrieved documents
            k: Number of top documents to consider
            high_authority_sources: List of high-authority source types

        Returns:
            RetrievalMetrics with all computed values
        """
        expected_sources = test_case.expected_sources or []
        expected_set = {s.lower() for s in expected_sources}

        # Extract doc IDs from retrieved docs
        retrieved_ids = [doc.get("id", "").lower() for doc in retrieved_docs[:k]]
        all_retrieved_ids = [doc.get("id", "").lower() for doc in retrieved_docs]

        # Compute hits (relevant docs in top k)
        hits_at_k = sum(1 for doc_id in retrieved_ids if doc_id in expected_set)

        # Precision@k
        precision = hits_at_k / len(retrieved_ids) if retrieved_ids else 0.0

        # Recall@k (considering all retrieved docs, not just top k)
        all_hits = sum(1 for doc_id in all_retrieved_ids if doc_id in expected_set)
        recall = all_hits / len(expected_sources) if expected_sources else 1.0

        # MRR (Mean Reciprocal Rank)
        mrr = self._compute_mrr(all_retrieved_ids, expected_set)

        # NDCG (Normalized Discounted Cumulative Gain)
        ndcg = self._compute_ndcg(retrieved_ids, expected_set)

        # Source authority coverage
        authority_coverage = self._compute_authority_coverage(
            retrieved_docs[:k],
            high_authority_sources or [],
        )

        return RetrievalMetrics(
            precision_at_k=precision,
            recall_at_k=recall,
            mrr=mrr,
            ndcg=ndcg,
            source_authority_coverage=authority_coverage,
            retrieved_count=len(retrieved_docs),
            relevant_count=len(expected_sources),
            hits_at_k=hits_at_k,
        )

    def _compute_mrr(
        self,
        retrieved_ids: list[str],
        expected_set: set[str],
    ) -> float:
        """Compute Mean Reciprocal Rank.

        MRR = 1 / rank of first relevant document.

        Args:
            retrieved_ids: List of retrieved document IDs
            expected_set: Set of expected document IDs

        Returns:
            MRR score (0.0 if no relevant doc found)
        """
        for rank, doc_id in enumerate(retrieved_ids, start=1):
            if doc_id in expected_set:
                return 1.0 / rank
        return 0.0

    def _compute_ndcg(
        self,
        retrieved_ids: list[str],
        expected_set: set[str],
    ) -> float:
        """Compute Normalized Discounted Cumulative Gain.

        NDCG = DCG / IDCG where:
        - DCG = sum(rel_i / log2(i + 1)) for each position i
        - IDCG = DCG if all relevant docs were at top

        Args:
            retrieved_ids: List of retrieved document IDs
            expected_set: Set of expected document IDs

        Returns:
            NDCG score (0.0 to 1.0)
        """
        if not expected_set:
            return 1.0

        # Compute DCG
        dcg = 0.0
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in expected_set:
                # Binary relevance: 1 if relevant, 0 otherwise
                dcg += 1.0 / math.log2(i + 2)  # i+2 because log2(1) = 0

        # Compute IDCG (ideal DCG - all relevant docs at top)
        num_relevant = min(len(expected_set), len(retrieved_ids))
        idcg = sum(1.0 / math.log2(i + 2) for i in range(num_relevant))

        if idcg == 0:
            return 0.0

        return dcg / idcg

    def _compute_authority_coverage(
        self,
        retrieved_docs: list[dict[str, Any]],
        high_authority_sources: list[str],
    ) -> float:
        """Compute fraction of retrieved docs from high-authority sources.

        Args:
            retrieved_docs: List of retrieved documents
            high_authority_sources: List of high-authority source types

        Returns:
            Fraction of docs from high-authority sources
        """
        if not retrieved_docs or not high_authority_sources:
            return 1.0  # No authority filter, assume all are fine

        authority_set = {s.lower() for s in high_authority_sources}
        high_authority_count = 0

        for doc in retrieved_docs:
            source_type = doc.get("source_type", "").lower()
            if source_type in authority_set:
                high_authority_count += 1

        return high_authority_count / len(retrieved_docs)

    def _compute_score(self, metrics: RetrievalMetrics) -> float:
        """Compute weighted score from metrics.

        Args:
            metrics: Computed retrieval metrics

        Returns:
            Weighted score between 0.0 and 1.0
        """
        score = (
            self.RECALL_WEIGHT * metrics.recall_at_k
            + self.PRECISION_WEIGHT * metrics.precision_at_k
            + self.MRR_WEIGHT * metrics.mrr
            + self.NDCG_WEIGHT * metrics.ndcg
            + self.AUTHORITY_WEIGHT * metrics.source_authority_coverage
        )
        return min(1.0, max(0.0, score))

    def _generate_reasoning(self, metrics: RetrievalMetrics, k: int) -> str:
        """Generate human-readable reasoning from metrics.

        Args:
            metrics: Computed retrieval metrics
            k: Value of k used

        Returns:
            Reasoning string
        """
        parts = [
            f"Retrieved {metrics.retrieved_count} documents "
            f"({metrics.hits_at_k}/{metrics.relevant_count} relevant in top {k})"
        ]

        if metrics.recall_at_k < 1.0:
            parts.append(
                f"Recall@{k}: {metrics.recall_at_k:.2f} "
                f"(missing {metrics.relevant_count - metrics.hits_at_k} relevant docs)"
            )

        if metrics.mrr > 0:
            rank = int(1.0 / metrics.mrr) if metrics.mrr > 0 else "N/A"
            parts.append(f"First relevant doc at rank {rank}")
        else:
            parts.append("No relevant documents found")

        parts.append(f"NDCG: {metrics.ndcg:.2f}")

        return ". ".join(parts) + "."
