"""Comprehensive tests for ExpertFAQRetrievalServiceOptimized.

Covers all methods, branches, error paths, caching logic, entity extraction,
semantic search, batch operations, Redis connection handling, and Prometheus metrics.
All external dependencies are mocked - no real DB, Redis, or LLM connections needed.

Target: >= 90% code coverage of expert_faq_retrieval_service_optimized.py
"""

import hashlib
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Patch heavy/unavailable modules BEFORE importing the service under test.
# We import inside fixtures/tests to ensure patches are active.
# ---------------------------------------------------------------------------

_mock_settings = MagicMock()
_mock_settings.CACHE_ENABLED = True
_mock_settings.REDIS_URL = "redis://localhost:6379/0"
_mock_settings.REDIS_PASSWORD = ""
_mock_settings.REDIS_DB = 0
_mock_settings.REDIS_MAX_CONNECTIONS = 10
_mock_settings.FAQ_EMBEDDING_CACHE_TTL = 3600
_mock_settings.FAQ_RESULT_CACHE_TTL = 300
_mock_settings.FAQ_MIN_SIMILARITY = 0.85
_mock_settings.FAQ_MAX_RESULTS = 10

# Patch settings at the module level so the class sees it at import time
with patch("app.core.config.settings", _mock_settings):
    from app.services.expert_faq_retrieval_service_optimized import (
        ExpertFAQRetrievalServiceOptimized,
    )


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch):
    """Patch settings globally for every test."""
    monkeypatch.setattr(
        "app.services.expert_faq_retrieval_service_optimized.settings",
        _mock_settings,
    )


@pytest.fixture
def mock_db():
    """Create a mock async DB session."""
    db = AsyncMock()
    return db


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    r = AsyncMock()
    r.ping = AsyncMock()
    r.get = AsyncMock(return_value=None)
    r.setex = AsyncMock()
    r.close = AsyncMock()
    return r


@pytest.fixture
def service(mock_db):
    """Create an ExpertFAQRetrievalServiceOptimized instance with mocked DB, Redis disabled."""
    svc = ExpertFAQRetrievalServiceOptimized(db_session=mock_db)
    svc._redis_available = False
    return svc


@pytest.fixture
def service_with_redis(mock_db, mock_redis):
    """Create service with Redis enabled and a pre-set mock client."""
    svc = ExpertFAQRetrievalServiceOptimized(db_session=mock_db)
    svc._redis_available = True
    svc._redis_client = mock_redis
    return svc


# ===========================================================================
# __init__ tests
# ===========================================================================


class TestInit:
    """Tests for service initialization."""

    def test_init_with_defaults(self, mock_db):
        svc = ExpertFAQRetrievalServiceOptimized(db_session=mock_db)
        assert svc.db is mock_db
        assert svc.embedding_cache_ttl == 3600
        assert svc.result_cache_ttl == 300
        assert svc.default_min_similarity == 0.85
        assert svc.default_max_results == 10
        assert svc._redis_client is None

    def test_init_redis_disabled_when_cache_disabled(self, mock_db):
        _mock_settings.CACHE_ENABLED = False
        try:
            svc = ExpertFAQRetrievalServiceOptimized(db_session=mock_db)
            assert svc._redis_available is False
        finally:
            _mock_settings.CACHE_ENABLED = True

    def test_init_redis_enabled_when_cache_enabled(self, mock_db):
        svc = ExpertFAQRetrievalServiceOptimized(db_session=mock_db)
        # REDIS_AVAILABLE is True (redis.asyncio is importable) and CACHE_ENABLED is True
        assert svc._redis_available is True


# ===========================================================================
# _get_redis tests
# ===========================================================================


class TestGetRedis:
    """Tests for Redis connection management."""

    @pytest.mark.asyncio
    async def test_get_redis_returns_none_when_unavailable(self, service):
        service._redis_available = False
        result = await service._get_redis()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_redis_returns_existing_client(self, service_with_redis, mock_redis):
        result = await service_with_redis._get_redis()
        assert result is mock_redis

    @pytest.mark.asyncio
    async def test_get_redis_creates_new_connection(self, service, mock_redis):
        service._redis_client = None
        service._redis_available = True

        with patch(
            "app.services.expert_faq_retrieval_service_optimized.redis.from_url",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ):
            result = await service._get_redis()

        assert result is mock_redis
        mock_redis.ping.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_redis_handles_connection_failure(self, service):
        service._redis_client = None
        service._redis_available = True

        with patch(
            "app.services.expert_faq_retrieval_service_optimized.redis.from_url",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Connection refused"),
        ):
            result = await service._get_redis()

        assert result is None
        assert service._redis_available is False


# ===========================================================================
# _generate_result_cache_key tests
# ===========================================================================


class TestGenerateResultCacheKey:
    """Tests for result cache key generation."""

    def test_cache_key_format(self, service):
        key = service._generate_result_cache_key("test query", 0.85, 10)
        query_hash = hashlib.sha256(b"test query").hexdigest()
        assert key == f"faq_result:v1:{query_hash}:0.85:10"

    def test_cache_key_strips_and_lowercases(self, service):
        key1 = service._generate_result_cache_key("  Test Query  ", 0.85, 10)
        key2 = service._generate_result_cache_key("test query", 0.85, 10)
        assert key1 == key2

    def test_different_queries_produce_different_keys(self, service):
        key1 = service._generate_result_cache_key("query A", 0.85, 10)
        key2 = service._generate_result_cache_key("query B", 0.85, 10)
        assert key1 != key2

    def test_different_similarity_produce_different_keys(self, service):
        key1 = service._generate_result_cache_key("q", 0.85, 10)
        key2 = service._generate_result_cache_key("q", 0.90, 10)
        assert key1 != key2

    def test_different_max_results_produce_different_keys(self, service):
        key1 = service._generate_result_cache_key("q", 0.85, 10)
        key2 = service._generate_result_cache_key("q", 0.85, 5)
        assert key1 != key2


# ===========================================================================
# _generate_embedding_cache_key tests
# ===========================================================================


class TestGenerateEmbeddingCacheKey:
    """Tests for embedding cache key generation."""

    def test_embedding_cache_key_format(self, service):
        key = service._generate_embedding_cache_key("hello world")
        text_hash = hashlib.sha256(b"hello world").hexdigest()
        assert key == f"embedding:v1:{text_hash}"

    def test_embedding_cache_key_strips_text(self, service):
        key1 = service._generate_embedding_cache_key("  hello  ")
        key2 = service._generate_embedding_cache_key("hello")
        assert key1 == key2

    def test_embedding_cache_key_is_case_sensitive(self, service):
        """Embedding key does NOT lowercase (unlike result key)."""
        key1 = service._generate_embedding_cache_key("Test")
        key2 = service._generate_embedding_cache_key("test")
        assert key1 != key2


# ===========================================================================
# _get_cached_results tests
# ===========================================================================


class TestGetCachedResults:
    """Tests for result cache retrieval."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_redis(self, service):
        service._redis_available = False
        result = await service._get_cached_results("q", 0.85, 10)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_cached_data(self, service_with_redis, mock_redis):
        cached = [{"faq_id": "abc", "question": "test"}]
        mock_redis.get = AsyncMock(return_value=json.dumps(cached).encode())

        result = await service_with_redis._get_cached_results("q", 0.85, 10)
        assert result == cached

    @pytest.mark.asyncio
    async def test_returns_none_on_cache_miss(self, service_with_redis, mock_redis):
        mock_redis.get = AsyncMock(return_value=None)

        result = await service_with_redis._get_cached_results("q", 0.85, 10)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_redis_error(self, service_with_redis, mock_redis):
        mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))

        result = await service_with_redis._get_cached_results("q", 0.85, 10)
        assert result is None


# ===========================================================================
# _cache_results tests
# ===========================================================================


class TestCacheResults:
    """Tests for result caching."""

    @pytest.mark.asyncio
    async def test_does_nothing_when_no_redis(self, service):
        service._redis_available = False
        await service._cache_results("q", 0.85, 10, [])
        # Should not raise

    @pytest.mark.asyncio
    async def test_caches_results_with_ttl(self, service_with_redis, mock_redis):
        results = [{"faq_id": "1", "question": "q"}]
        await service_with_redis._cache_results("q", 0.85, 10, results)

        mock_redis.setex.assert_awaited_once()
        args = mock_redis.setex.call_args
        assert args[0][1] == service_with_redis.result_cache_ttl

    @pytest.mark.asyncio
    async def test_handles_redis_error_gracefully(self, service_with_redis, mock_redis):
        mock_redis.setex = AsyncMock(side_effect=Exception("Redis write error"))

        # Should not raise
        await service_with_redis._cache_results("q", 0.85, 10, [{"test": True}])


# ===========================================================================
# _generate_embedding_cached tests
# ===========================================================================


class TestGenerateEmbeddingCached:
    """Tests for embedding generation with caching."""

    @pytest.mark.asyncio
    async def test_returns_cached_embedding_from_redis(self, service_with_redis, mock_redis):
        embedding = [0.1] * 1536
        mock_redis.get = AsyncMock(return_value=json.dumps(embedding).encode())

        result = await service_with_redis._generate_embedding_cached("test text")
        assert result == embedding

    @pytest.mark.asyncio
    @patch("app.services.expert_faq_retrieval_service_optimized.generate_embedding")
    async def test_generates_and_caches_embedding(self, mock_gen_embed, service_with_redis, mock_redis):
        embedding = [0.2] * 1536
        mock_gen_embed.return_value = embedding
        mock_redis.get = AsyncMock(return_value=None)

        result = await service_with_redis._generate_embedding_cached("test text")
        assert result == embedding
        mock_redis.setex.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("app.services.expert_faq_retrieval_service_optimized.generate_embedding")
    async def test_returns_none_when_embedding_is_none(self, mock_gen_embed, service):
        mock_gen_embed.return_value = None
        result = await service._generate_embedding_cached("test")
        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.expert_faq_retrieval_service_optimized.generate_embedding")
    async def test_returns_none_for_wrong_dimension(self, mock_gen_embed, service):
        mock_gen_embed.return_value = [0.1] * 512  # Wrong dimension
        result = await service._generate_embedding_cached("test")
        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.expert_faq_retrieval_service_optimized.generate_embedding")
    async def test_returns_none_on_embedding_generation_error(self, mock_gen_embed, service):
        mock_gen_embed.side_effect = Exception("API error")
        result = await service._generate_embedding_cached("test")
        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.expert_faq_retrieval_service_optimized.generate_embedding")
    async def test_handles_redis_read_error(self, mock_gen_embed, service_with_redis, mock_redis):
        """Redis read fails but embedding generation succeeds."""
        embedding = [0.3] * 1536
        mock_gen_embed.return_value = embedding
        mock_redis.get = AsyncMock(side_effect=Exception("Redis read error"))

        result = await service_with_redis._generate_embedding_cached("test")
        assert result == embedding

    @pytest.mark.asyncio
    @patch("app.services.expert_faq_retrieval_service_optimized.generate_embedding")
    async def test_handles_redis_write_error(self, mock_gen_embed, service_with_redis, mock_redis):
        """Redis cache write fails but embedding is still returned."""
        embedding = [0.4] * 1536
        mock_gen_embed.return_value = embedding
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock(side_effect=Exception("Redis write error"))

        result = await service_with_redis._generate_embedding_cached("test")
        assert result == embedding

    @pytest.mark.asyncio
    @patch("app.services.expert_faq_retrieval_service_optimized.generate_embedding")
    async def test_no_redis_cache_write_when_redis_unavailable(self, mock_gen_embed, service):
        """When redis is not available, no caching attempt is made."""
        embedding = [0.5] * 1536
        mock_gen_embed.return_value = embedding

        result = await service._generate_embedding_cached("test")
        assert result == embedding

    @pytest.mark.asyncio
    @patch("app.services.expert_faq_retrieval_service_optimized.generate_embedding")
    async def test_prometheus_embedding_latency(self, mock_gen_embed, service, monkeypatch):
        """Prometheus embedding latency histogram is observed when available."""
        monkeypatch.setattr(
            "app.services.expert_faq_retrieval_service_optimized.PROMETHEUS_AVAILABLE",
            True,
        )
        mock_histogram = MagicMock()
        monkeypatch.setattr(
            "app.services.expert_faq_retrieval_service_optimized.faq_embedding_generation_latency",
            mock_histogram,
        )
        embedding = [0.1] * 1536
        mock_gen_embed.return_value = embedding

        result = await service._generate_embedding_cached("test text")
        assert result == embedding
        mock_histogram.observe.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.expert_faq_retrieval_service_optimized.generate_embedding")
    async def test_prometheus_cache_hit_counter(self, mock_gen_embed, service_with_redis, mock_redis, monkeypatch):
        """Prometheus cache hit counter is incremented on embedding cache hit."""
        monkeypatch.setattr(
            "app.services.expert_faq_retrieval_service_optimized.PROMETHEUS_AVAILABLE",
            True,
        )
        mock_counter = MagicMock()
        monkeypatch.setattr(
            "app.services.expert_faq_retrieval_service_optimized.faq_cache_hits",
            mock_counter,
        )
        embedding = [0.1] * 1536
        mock_redis.get = AsyncMock(return_value=json.dumps(embedding).encode())

        result = await service_with_redis._generate_embedding_cached("test")
        assert result == embedding
        mock_counter.labels.assert_called_with(cache_type="embedding")

    @pytest.mark.asyncio
    @patch("app.services.expert_faq_retrieval_service_optimized.generate_embedding")
    async def test_prometheus_cache_miss_counter(self, mock_gen_embed, service_with_redis, mock_redis, monkeypatch):
        """Prometheus cache miss counter is incremented on embedding cache miss."""
        monkeypatch.setattr(
            "app.services.expert_faq_retrieval_service_optimized.PROMETHEUS_AVAILABLE",
            True,
        )
        mock_counter = MagicMock()
        monkeypatch.setattr(
            "app.services.expert_faq_retrieval_service_optimized.faq_cache_misses",
            mock_counter,
        )
        mock_histogram = MagicMock()
        monkeypatch.setattr(
            "app.services.expert_faq_retrieval_service_optimized.faq_embedding_generation_latency",
            mock_histogram,
        )
        embedding = [0.1] * 1536
        mock_gen_embed.return_value = embedding
        mock_redis.get = AsyncMock(return_value=None)

        result = await service_with_redis._generate_embedding_cached("test")
        assert result == embedding
        mock_counter.labels.assert_called_with(cache_type="embedding")


# ===========================================================================
# _extract_entities tests
# ===========================================================================


class TestExtractEntities:
    """Tests for Italian legal entity extraction from text."""

    def test_extract_risoluzione(self, service):
        entities = service._extract_entities("Risoluzione n. 63 del 2024")
        assert "63" in entities["document_numbers"]

    def test_extract_circolare(self, service):
        entities = service._extract_entities("circolare 12 dell'Agenzia")
        assert "12" in entities["document_numbers"]

    def test_extract_interpello(self, service):
        entities = service._extract_entities("interpello n.45")
        assert "45" in entities["document_numbers"]

    def test_extract_multiple_document_types(self, service):
        text = "risoluzione 63 circolare 12 interpello 7"
        entities = service._extract_entities(text)
        assert "63" in entities["document_numbers"]
        assert "12" in entities["document_numbers"]
        assert "7" in entities["document_numbers"]

    def test_extract_years_in_range(self, service):
        entities = service._extract_entities("Anno 2024 e 2025")
        assert "2024" in entities["years"]
        assert "2025" in entities["years"]

    def test_extract_years_boundary(self, service):
        entities = service._extract_entities("2020 e 2030")
        assert "2020" in entities["years"]
        assert "2030" in entities["years"]

    def test_year_outside_range_not_extracted(self, service):
        entities = service._extract_entities("Nel 2019 e 2031")
        assert "2019" not in entities["years"]
        assert "2031" not in entities["years"]

    def test_extract_article_numbers(self, service):
        entities = service._extract_entities("art. 1 e articolo 12, comma 3")
        assert "1" in entities["article_numbers"]
        assert "12" in entities["article_numbers"]
        assert "3" in entities["article_numbers"]

    def test_extract_decree_numbers(self, service):
        entities = service._extract_entities("decreto n. 123 e DL 45")
        assert "123" in entities["decree_numbers"]
        assert "45" in entities["decree_numbers"]

    def test_extract_dlgs_pattern(self, service):
        entities = service._extract_entities("D.Lgs. n. 81")
        assert "81" in entities["decree_numbers"]

    def test_no_entities(self, service):
        entities = service._extract_entities("domanda generica sull'IVA")
        assert len(entities["document_numbers"]) == 0
        assert len(entities["years"]) == 0
        assert len(entities["article_numbers"]) == 0
        assert len(entities["decree_numbers"]) == 0

    def test_empty_text(self, service):
        entities = service._extract_entities("")
        for v in entities.values():
            assert len(v) == 0


# ===========================================================================
# _validate_entity_match tests
# ===========================================================================


class TestValidateEntityMatch:
    """Tests for entity-based FAQ match validation."""

    def test_no_entities_in_query_passes(self, service):
        assert service._validate_entity_match("cos'e l'IVA?", "che cos'e l'IVA?") is True

    def test_matching_document_numbers(self, service):
        query = "Risoluzione n. 63 del 2024"
        faq = "La risoluzione 63 del 2024 chiarisce..."
        assert service._validate_entity_match(query, faq) is True

    def test_mismatching_document_numbers(self, service):
        query = "Risoluzione n. 63 del 2024"
        faq = "La risoluzione 99 del 2024 chiarisce..."
        assert service._validate_entity_match(query, faq) is False

    def test_query_has_entities_faq_has_none(self, service):
        query = "circolare 12 del 2024"
        faq = "Come si calcola l'IVA?"
        assert service._validate_entity_match(query, faq) is False

    def test_matching_years(self, service):
        query = "normativa 2025"
        faq = "la normativa 2025 prevede..."
        assert service._validate_entity_match(query, faq) is True

    def test_mismatching_years(self, service):
        query = "normativa 2025"
        faq = "la normativa 2024 prevede..."
        assert service._validate_entity_match(query, faq) is False

    def test_partial_entity_match(self, service):
        """At least one entity value must overlap per type."""
        query = "art. 1 e art. 2"
        faq = "art. 1 del TUIR"
        assert service._validate_entity_match(query, faq) is True

    def test_multiple_entity_types_all_must_match(self, service):
        """All non-empty entity types must have at least one matching value."""
        query = "Risoluzione 63 del 2024"
        faq = "Risoluzione 63 del 2025"  # document matches but year does not
        assert service._validate_entity_match(query, faq) is False

    def test_both_no_entities(self, service):
        assert service._validate_entity_match("come stai?", "come va?") is True


# ===========================================================================
# _semantic_search tests
# ===========================================================================


class TestSemanticSearch:
    """Tests for pgvector semantic similarity search.

    We patch FAQCandidate to avoid accessing real SQLModel class attributes
    which require pgvector extension.
    """

    @staticmethod
    def _make_select_patch(mock_db, rows):
        """Create patches for select + FAQCandidate that bypass SQLAlchemy validation.

        We mock the entire select function to return a chainable mock, and
        mock FAQCandidate with proper __le__ support on cosine_distance returns.
        """
        # Mock select to return a chainable query builder
        mock_stmt = MagicMock()
        mock_stmt.where.return_value = mock_stmt
        mock_stmt.order_by.return_value = mock_stmt
        mock_stmt.limit.return_value = mock_stmt

        mock_select = MagicMock(return_value=mock_stmt)

        # Build FAQCandidate mock with proper cosine_distance that supports <=
        mock_faq_cls = MagicMock()
        mock_cosine_result = MagicMock()
        mock_cosine_result.__le__ = MagicMock(return_value=MagicMock())
        mock_cosine_result.__sub__ = MagicMock(return_value=MagicMock())
        mock_cosine_result.label = MagicMock(return_value=MagicMock())

        mock_embedding_attr = MagicMock()
        mock_embedding_attr.cosine_distance.return_value = mock_cosine_result
        mock_embedding_attr.isnot.return_value = MagicMock()
        mock_faq_cls.question_embedding = mock_embedding_attr
        mock_faq_cls.status = MagicMock()
        mock_faq_cls.status.in_ = MagicMock(return_value=MagicMock())

        # Mock db.execute result
        mock_result = MagicMock()
        mock_result.fetchall.return_value = rows
        mock_db.execute = AsyncMock(return_value=mock_result)

        from contextlib import contextmanager

        @contextmanager
        def _cm():
            with (
                patch("app.services.expert_faq_retrieval_service_optimized.select", mock_select),
                patch("app.services.expert_faq_retrieval_service_optimized.FAQCandidate", mock_faq_cls),
            ):
                yield

        return _cm()

    @pytest.mark.asyncio
    async def test_returns_faq_results(self, service, mock_db):
        from uuid import uuid4

        row = MagicMock()
        row.id = uuid4()
        row.suggested_question = "Come funziona l'IVA?"
        row.best_response_content = "L'IVA funziona cosi..."
        row.suggested_category = "fiscale"
        row.regulatory_references = ["art. 1"]
        row.priority_score = 0.9
        row.status = "auto_approved"
        row.similarity = 0.95

        with self._make_select_patch(mock_db, [row]):
            results = await service._semantic_search(
                query_embedding=[0.1] * 1536,
                min_similarity=0.85,
                max_results=10,
                query="",
            )

        assert len(results) == 1
        assert results[0]["faq_id"] == str(row.id)
        assert results[0]["question"] == "Come funziona l'IVA?"
        assert results[0]["answer"] == "L'IVA funziona cosi..."
        assert results[0]["similarity_score"] == 0.95
        assert results[0]["category"] == "fiscale"
        assert results[0]["regulatory_references"] == ["art. 1"]
        assert results[0]["priority_score"] == 0.9
        assert results[0]["approval_status"] == "auto_approved"

    @pytest.mark.asyncio
    async def test_filters_entity_mismatches(self, service, mock_db):
        from uuid import uuid4

        row = MagicMock()
        row.id = uuid4()
        row.suggested_question = "Risoluzione 99 del 2024"
        row.best_response_content = "Answer"
        row.suggested_category = "fiscale"
        row.regulatory_references = None
        row.priority_score = None
        row.status = "auto_approved"
        row.similarity = 0.90

        with self._make_select_patch(mock_db, [row]):
            results = await service._semantic_search(
                query_embedding=[0.1] * 1536,
                min_similarity=0.85,
                max_results=10,
                query="Risoluzione 63 del 2024",
            )

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_handles_null_fields(self, service, mock_db):
        from uuid import uuid4

        row = MagicMock()
        row.id = uuid4()
        row.suggested_question = "Domanda"
        row.best_response_content = "Risposta"
        row.suggested_category = None
        row.regulatory_references = None
        row.priority_score = None
        row.status = "manually_approved"
        row.similarity = 0.88

        with self._make_select_patch(mock_db, [row]):
            results = await service._semantic_search(
                query_embedding=[0.1] * 1536,
                min_similarity=0.85,
                max_results=10,
                query="",
            )

        assert len(results) == 1
        assert results[0]["regulatory_references"] == []
        assert results[0]["priority_score"] == 0.0

    @pytest.mark.asyncio
    async def test_returns_empty_on_db_error(self, service, mock_db):
        mock_db.execute = AsyncMock(side_effect=Exception("DB error"))

        with self._make_select_patch(mock_db, []):
            # Override execute again to raise
            mock_db.execute = AsyncMock(side_effect=Exception("DB error"))
            results = await service._semantic_search(
                query_embedding=[0.1] * 1536,
                min_similarity=0.85,
                max_results=10,
                query="test",
            )

        assert results == []

    @pytest.mark.asyncio
    async def test_empty_rows(self, service, mock_db):
        with self._make_select_patch(mock_db, []):
            results = await service._semantic_search(
                query_embedding=[0.1] * 1536,
                min_similarity=0.85,
                max_results=10,
                query="test",
            )
        assert results == []

    @pytest.mark.asyncio
    async def test_multiple_rows_with_mixed_entity_matches(self, service, mock_db):
        """Multiple rows: one matches entities, one does not."""
        from uuid import uuid4

        row_match = MagicMock()
        row_match.id = uuid4()
        row_match.suggested_question = "Risoluzione 63 del 2024 IVA"
        row_match.best_response_content = "Answer matching"
        row_match.suggested_category = "fiscale"
        row_match.regulatory_references = []
        row_match.priority_score = 0.8
        row_match.status = "auto_approved"
        row_match.similarity = 0.95

        row_no_match = MagicMock()
        row_no_match.id = uuid4()
        row_no_match.suggested_question = "Risoluzione 99 del 2025 IRPEF"
        row_no_match.best_response_content = "Answer not matching"
        row_no_match.suggested_category = "fiscale"
        row_no_match.regulatory_references = []
        row_no_match.priority_score = 0.7
        row_no_match.status = "auto_approved"
        row_no_match.similarity = 0.90

        with self._make_select_patch(mock_db, [row_match, row_no_match]):
            results = await service._semantic_search(
                query_embedding=[0.1] * 1536,
                min_similarity=0.85,
                max_results=10,
                query="Risoluzione 63 del 2024",
            )

        assert len(results) == 1
        assert results[0]["faq_id"] == str(row_match.id)


# ===========================================================================
# find_matching_faqs tests
# ===========================================================================


class TestFindMatchingFaqs:
    """Tests for the main FAQ search method."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_string(self, service):
        assert await service.find_matching_faqs("") == []

    @pytest.mark.asyncio
    async def test_returns_empty_for_whitespace(self, service):
        assert await service.find_matching_faqs("   ") == []

    @pytest.mark.asyncio
    async def test_returns_empty_for_none(self, service):
        assert await service.find_matching_faqs(None) == []

    @pytest.mark.asyncio
    async def test_uses_default_params(self, service):
        with (
            patch.object(service, "_get_cached_results", new_callable=AsyncMock, return_value=None),
            patch.object(service, "_generate_embedding_cached", new_callable=AsyncMock, return_value=[0.1] * 1536),
            patch.object(service, "_semantic_search", new_callable=AsyncMock, return_value=[]) as mock_search,
            patch.object(service, "_cache_results", new_callable=AsyncMock),
        ):
            await service.find_matching_faqs("test query")
            call_kwargs = mock_search.call_args[1]
            assert call_kwargs["min_similarity"] == 0.85
            assert call_kwargs["max_results"] == 10

    @pytest.mark.asyncio
    async def test_uses_custom_params(self, service):
        with (
            patch.object(service, "_get_cached_results", new_callable=AsyncMock, return_value=None),
            patch.object(service, "_generate_embedding_cached", new_callable=AsyncMock, return_value=[0.1] * 1536),
            patch.object(service, "_semantic_search", new_callable=AsyncMock, return_value=[]) as mock_search,
            patch.object(service, "_cache_results", new_callable=AsyncMock),
        ):
            await service.find_matching_faqs("test", min_similarity=0.90, max_results=5)
            call_kwargs = mock_search.call_args[1]
            assert call_kwargs["min_similarity"] == 0.90
            assert call_kwargs["max_results"] == 5

    @pytest.mark.asyncio
    async def test_returns_cached_results_on_hit(self, service):
        cached = [{"faq_id": "cached", "question": "Cached Q"}]

        with patch.object(service, "_get_cached_results", new_callable=AsyncMock, return_value=cached):
            result = await service.find_matching_faqs("test query")

        assert result == cached

    @pytest.mark.asyncio
    async def test_returns_empty_when_embedding_fails(self, service):
        with (
            patch.object(service, "_get_cached_results", new_callable=AsyncMock, return_value=None),
            patch.object(service, "_generate_embedding_cached", new_callable=AsyncMock, return_value=None),
        ):
            result = await service.find_matching_faqs("test query")
            assert result == []

    @pytest.mark.asyncio
    async def test_performs_search_and_caches_results(self, service):
        search_results = [{"faq_id": "1", "question": "Q1", "similarity_score": 0.92}]

        with (
            patch.object(service, "_get_cached_results", new_callable=AsyncMock, return_value=None),
            patch.object(service, "_generate_embedding_cached", new_callable=AsyncMock, return_value=[0.1] * 1536),
            patch.object(service, "_semantic_search", new_callable=AsyncMock, return_value=search_results),
            patch.object(service, "_cache_results", new_callable=AsyncMock) as mock_cache,
        ):
            result = await service.find_matching_faqs("test query")
            assert result == search_results
            mock_cache.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self, service):
        with patch.object(service, "_get_cached_results", new_callable=AsyncMock, side_effect=Exception("Boom")):
            result = await service.find_matching_faqs("test query")
            assert result == []

    @pytest.mark.asyncio
    async def test_long_query_handled(self, service):
        long_query = "a" * 10000
        with (
            patch.object(service, "_get_cached_results", new_callable=AsyncMock, return_value=None),
            patch.object(service, "_generate_embedding_cached", new_callable=AsyncMock, return_value=[0.1] * 1536),
            patch.object(service, "_semantic_search", new_callable=AsyncMock, return_value=[]),
            patch.object(service, "_cache_results", new_callable=AsyncMock),
        ):
            result = await service.find_matching_faqs(long_query)
            assert result == []


# ===========================================================================
# find_matching_faqs Prometheus branches
# ===========================================================================


class TestFindMatchingFaqsPrometheus:
    """Tests covering Prometheus-related branches in find_matching_faqs."""

    @pytest.mark.asyncio
    async def test_prometheus_disabled_result_cache_hit(self, service, monkeypatch):
        monkeypatch.setattr(
            "app.services.expert_faq_retrieval_service_optimized.PROMETHEUS_AVAILABLE",
            False,
        )
        cached = [{"faq_id": "1"}]
        with patch.object(service, "_get_cached_results", new_callable=AsyncMock, return_value=cached):
            result = await service.find_matching_faqs("test")
        assert result == cached

    @pytest.mark.asyncio
    async def test_prometheus_enabled_result_cache_hit(self, service, monkeypatch):
        monkeypatch.setattr(
            "app.services.expert_faq_retrieval_service_optimized.PROMETHEUS_AVAILABLE",
            True,
        )
        mock_counter = MagicMock()
        mock_histogram = MagicMock()
        monkeypatch.setattr(
            "app.services.expert_faq_retrieval_service_optimized.faq_cache_hits",
            mock_counter,
        )
        monkeypatch.setattr(
            "app.services.expert_faq_retrieval_service_optimized.faq_retrieval_latency",
            mock_histogram,
        )
        cached = [{"faq_id": "1"}]
        with patch.object(service, "_get_cached_results", new_callable=AsyncMock, return_value=cached):
            result = await service.find_matching_faqs("test")
        assert result == cached
        mock_counter.labels.assert_called_with(cache_type="result")
        mock_histogram.labels.assert_called()

    @pytest.mark.asyncio
    async def test_prometheus_cache_miss_counter(self, service, monkeypatch):
        monkeypatch.setattr(
            "app.services.expert_faq_retrieval_service_optimized.PROMETHEUS_AVAILABLE",
            True,
        )
        mock_miss_counter = MagicMock()
        mock_histogram = MagicMock()
        monkeypatch.setattr(
            "app.services.expert_faq_retrieval_service_optimized.faq_cache_misses",
            mock_miss_counter,
        )
        monkeypatch.setattr(
            "app.services.expert_faq_retrieval_service_optimized.faq_retrieval_latency",
            mock_histogram,
        )

        with (
            patch.object(service, "_get_cached_results", new_callable=AsyncMock, return_value=None),
            patch.object(service, "_generate_embedding_cached", new_callable=AsyncMock, return_value=[0.1] * 1536),
            patch.object(service, "_semantic_search", new_callable=AsyncMock, return_value=[]),
            patch.object(service, "_cache_results", new_callable=AsyncMock),
        ):
            await service.find_matching_faqs("test")
            mock_miss_counter.labels.assert_called_with(cache_type="result")

    @pytest.mark.asyncio
    async def test_prometheus_latency_on_search_completion(self, service, monkeypatch):
        """faq_retrieval_latency is observed after successful search (cache miss path)."""
        monkeypatch.setattr(
            "app.services.expert_faq_retrieval_service_optimized.PROMETHEUS_AVAILABLE",
            True,
        )
        mock_histogram = MagicMock()
        mock_miss_counter = MagicMock()
        monkeypatch.setattr(
            "app.services.expert_faq_retrieval_service_optimized.faq_retrieval_latency",
            mock_histogram,
        )
        monkeypatch.setattr(
            "app.services.expert_faq_retrieval_service_optimized.faq_cache_misses",
            mock_miss_counter,
        )
        service._redis_available = True  # So cache_status becomes "embedding_hit"

        with (
            patch.object(service, "_get_cached_results", new_callable=AsyncMock, return_value=None),
            patch.object(service, "_generate_embedding_cached", new_callable=AsyncMock, return_value=[0.1] * 1536),
            patch.object(service, "_semantic_search", new_callable=AsyncMock, return_value=[{"faq_id": "1"}]),
            patch.object(service, "_cache_results", new_callable=AsyncMock),
        ):
            result = await service.find_matching_faqs("test")
            assert len(result) == 1
            mock_histogram.labels.assert_called()


# ===========================================================================
# find_matching_faqs_batch tests
# ===========================================================================


class TestFindMatchingFaqsBatch:
    """Tests for batch FAQ search."""

    @pytest.mark.asyncio
    async def test_empty_queries_returns_empty(self, service):
        result = await service.find_matching_faqs_batch([])
        assert result == []

    @pytest.mark.asyncio
    @patch("app.services.expert_faq_retrieval_service_optimized.generate_embeddings_batch")
    async def test_batch_search_with_results(self, mock_batch_embed, service):
        mock_batch_embed.return_value = [[0.1] * 1536, [0.2] * 1536]

        with patch.object(service, "_semantic_search", new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = [
                [{"faq_id": "1"}],
                [{"faq_id": "2"}],
            ]
            results = await service.find_matching_faqs_batch(["q1", "q2"])

        assert len(results) == 2
        assert results[0] == [{"faq_id": "1"}]
        assert results[1] == [{"faq_id": "2"}]

    @pytest.mark.asyncio
    @patch("app.services.expert_faq_retrieval_service_optimized.generate_embeddings_batch")
    async def test_batch_with_failed_embedding(self, mock_batch_embed, service):
        mock_batch_embed.return_value = [[0.1] * 1536, None]

        with patch.object(service, "_semantic_search", new_callable=AsyncMock, return_value=[{"faq_id": "1"}]):
            results = await service.find_matching_faqs_batch(["q1", "q2"])

        assert len(results) == 2
        assert results[0] == [{"faq_id": "1"}]
        assert results[1] == []

    @pytest.mark.asyncio
    @patch("app.services.expert_faq_retrieval_service_optimized.generate_embeddings_batch")
    async def test_batch_uses_default_params(self, mock_batch_embed, service):
        mock_batch_embed.return_value = [[0.1] * 1536]

        with patch.object(service, "_semantic_search", new_callable=AsyncMock, return_value=[]) as mock_search:
            await service.find_matching_faqs_batch(["q1"])
            call_kwargs = mock_search.call_args[1]
            assert call_kwargs["min_similarity"] == 0.85
            assert call_kwargs["max_results"] == 10

    @pytest.mark.asyncio
    @patch("app.services.expert_faq_retrieval_service_optimized.generate_embeddings_batch")
    async def test_batch_uses_custom_params(self, mock_batch_embed, service):
        mock_batch_embed.return_value = [[0.1] * 1536]

        with patch.object(service, "_semantic_search", new_callable=AsyncMock, return_value=[]) as mock_search:
            await service.find_matching_faqs_batch(["q1"], min_similarity=0.9, max_results=3)
            call_kwargs = mock_search.call_args[1]
            assert call_kwargs["min_similarity"] == 0.9
            assert call_kwargs["max_results"] == 3

    @pytest.mark.asyncio
    @patch("app.services.expert_faq_retrieval_service_optimized.generate_embeddings_batch")
    async def test_batch_handles_exception(self, mock_batch_embed, service):
        mock_batch_embed.side_effect = Exception("Batch error")

        results = await service.find_matching_faqs_batch(["q1", "q2"])
        assert results == [[], []]


# ===========================================================================
# close tests
# ===========================================================================


class TestClose:
    """Tests for Redis connection cleanup."""

    @pytest.mark.asyncio
    async def test_close_redis_connection(self, service_with_redis, mock_redis):
        await service_with_redis.close()
        mock_redis.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_when_no_client(self, service):
        service._redis_client = None
        await service.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_close_handles_error(self, service_with_redis, mock_redis):
        mock_redis.close = AsyncMock(side_effect=Exception("Close error"))
        await service_with_redis.close()  # Should not raise
