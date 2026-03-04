"""Tests for S2: Separate DB sessions for parallel KB retrieval.

Validates that BM25, vector, HyDE, and authority searches run concurrently
using independent DB sessions instead of sequentially sharing one session.
"""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.hyde_generator import HyDEResult
from app.services.multi_query_generator import QueryVariants
from app.services.parallel_retrieval import ParallelRetrievalService


def _make_query_variants(query: str = "test query") -> QueryVariants:
    return QueryVariants(
        bm25_query=query,
        vector_query=query,
        entity_query=query,
        original_query=query,
    )


def _make_hyde_result(skipped: bool = False) -> HyDEResult:
    return HyDEResult(
        hypothetical_document="" if skipped else "Un documento ipotetico",
        word_count=0 if skipped else 100,
        skipped=skipped,
        skip_reason="test" if skipped else None,
    )


def _mock_session_factory():
    """Create a mock async session factory."""

    @asynccontextmanager
    async def factory():
        yield MagicMock()

    return factory


class TestParallelKBSearches:
    """Tests for parallel KB search execution with separate sessions."""

    @pytest.mark.asyncio
    async def test_kb_searches_run_concurrently_with_session_factory(self):
        """With session_factory, all KB searches run concurrently."""
        call_log = []

        async def mock_search_bm25(self_ref, queries):
            call_log.append("bm25_start")
            await asyncio.sleep(0.02)
            call_log.append("bm25_end")
            return []

        async def mock_search_vector(self_ref, queries):
            call_log.append("vector_start")
            await asyncio.sleep(0.02)
            call_log.append("vector_end")
            return []

        async def mock_search_hyde(self_ref, hyde):
            call_log.append("hyde_start")
            await asyncio.sleep(0.02)
            call_log.append("hyde_end")
            return []

        async def mock_search_authority(self_ref, queries, limit_per_source=2):
            call_log.append("auth_start")
            await asyncio.sleep(0.02)
            call_log.append("auth_end")
            return []

        async def mock_search_brave(self_ref, queries, **kwargs):
            call_log.append("brave_start")
            await asyncio.sleep(0.02)
            call_log.append("brave_end")
            return []

        service = ParallelRetrievalService(
            search_service=MagicMock(),
            embedding_service=None,
            session_factory=_mock_session_factory(),
        )

        with (
            patch.object(ParallelRetrievalService, "_search_bm25", mock_search_bm25),
            patch.object(ParallelRetrievalService, "_search_vector", mock_search_vector),
            patch.object(ParallelRetrievalService, "_search_hyde", mock_search_hyde),
            patch.object(ParallelRetrievalService, "_search_authority_sources", mock_search_authority),
            patch.object(ParallelRetrievalService, "_search_brave", mock_search_brave),
            patch("app.services.parallel_retrieval.SearchService", create=True),
        ):
            await service._execute_parallel_searches(_make_query_variants(), _make_hyde_result())

        # All starts should occur before all ends (concurrent execution)
        starts = [i for i, x in enumerate(call_log) if x.endswith("_start")]
        ends = [i for i, x in enumerate(call_log) if x.endswith("_end")]
        assert max(starts) < min(ends), f"Not concurrent: {call_log}"

    @pytest.mark.asyncio
    async def test_sequential_fallback_without_session_factory(self):
        """Without session_factory, falls back to sequential execution."""
        call_order = []

        async def mock_search_bm25(self_ref, queries):
            call_order.append("bm25")
            return []

        async def mock_search_vector(self_ref, queries):
            call_order.append("vector")
            return []

        async def mock_search_hyde(self_ref, hyde):
            call_order.append("hyde")
            return []

        async def mock_search_authority(self_ref, queries, limit_per_source=2):
            call_order.append("authority")
            return []

        async def mock_search_brave(self_ref, queries, **kwargs):
            call_order.append("brave")
            return []

        # No session_factory → sequential
        service = ParallelRetrievalService(
            search_service=MagicMock(),
            embedding_service=None,
        )

        with (
            patch.object(ParallelRetrievalService, "_search_bm25", mock_search_bm25),
            patch.object(ParallelRetrievalService, "_search_vector", mock_search_vector),
            patch.object(ParallelRetrievalService, "_search_hyde", mock_search_hyde),
            patch.object(ParallelRetrievalService, "_search_authority_sources", mock_search_authority),
            patch.object(ParallelRetrievalService, "_search_brave", mock_search_brave),
        ):
            results = await service._execute_parallel_searches(_make_query_variants(), _make_hyde_result())

        # Should still return 5 result lists
        assert len(results) == 5
        # KB searches should be in order (sequential)
        kb_order = [x for x in call_order if x != "brave"]
        assert kb_order == ["bm25", "vector", "hyde", "authority"]

    @pytest.mark.asyncio
    async def test_individual_search_failure_doesnt_block_others(self):
        """One search failing should not prevent others from completing."""

        async def mock_search_bm25(self_ref, queries):
            raise RuntimeError("BM25 session error")

        async def mock_search_vector(self_ref, queries):
            return [{"document_id": "v1", "content": "vector result", "score": 0.9}]

        async def mock_search_hyde(self_ref, hyde):
            return []

        async def mock_search_authority(self_ref, queries, limit_per_source=2):
            return []

        async def mock_search_brave(self_ref, queries, **kwargs):
            return []

        service = ParallelRetrievalService(
            search_service=MagicMock(),
            embedding_service=None,
            session_factory=_mock_session_factory(),
        )

        with (
            patch.object(ParallelRetrievalService, "_search_bm25", mock_search_bm25),
            patch.object(ParallelRetrievalService, "_search_vector", mock_search_vector),
            patch.object(ParallelRetrievalService, "_search_hyde", mock_search_hyde),
            patch.object(ParallelRetrievalService, "_search_authority_sources", mock_search_authority),
            patch.object(ParallelRetrievalService, "_search_brave", mock_search_brave),
            patch("app.services.parallel_retrieval.SearchService", create=True),
        ):
            results = await service._execute_parallel_searches(_make_query_variants(), _make_hyde_result())

        # Should have 5 result lists (bm25=empty due to error, vector, hyde, authority, brave)
        assert len(results) == 5
        # BM25 failed → empty
        assert results[0] == []
        # Vector succeeded
        assert len(results[1]) == 1

    @pytest.mark.asyncio
    async def test_returns_five_result_lists(self):
        """Should always return exactly 5 result lists in correct order."""

        async def mock_search(self_ref, *args, **kwargs):
            return []

        service = ParallelRetrievalService(
            search_service=MagicMock(),
            embedding_service=None,
        )

        with (
            patch.object(ParallelRetrievalService, "_search_bm25", mock_search),
            patch.object(ParallelRetrievalService, "_search_vector", mock_search),
            patch.object(ParallelRetrievalService, "_search_hyde", mock_search),
            patch.object(ParallelRetrievalService, "_search_authority_sources", mock_search),
            patch.object(ParallelRetrievalService, "_search_brave", mock_search),
        ):
            results = await service._execute_parallel_searches(_make_query_variants(), _make_hyde_result())

        assert len(results) == 5
