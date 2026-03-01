"""Tests for ConsigliService (ADR-038: /consigli insight report).

TDD RED phase: Tests written before implementation.
Tests: data sufficiency gate, stats collection, report generation,
       concurrency guard, GDPR consent, PII anonymization.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def user_id():
    return 42


def _make_history_rows(count: int, days_span: int = 30):
    """Create mock query_history rows for testing."""
    now = datetime.utcnow()
    rows = []
    for i in range(count):
        ts = now - timedelta(days=days_span * i / max(count, 1))
        rows.append(
            MagicMock(
                query=f"query {i}",
                response=f"response {i}",
                timestamp=ts,
                query_type="tax_calculation" if i % 3 == 0 else "general",
                model_used="mistral-large-latest",
                tokens_used=100 + i,
                response_cached=i % 5 == 0,
                session_id=f"session-{i % 3}",
                kb_sources_metadata=[{"source": "ccnl"}] if i % 2 == 0 else None,
            )
        )
    return rows


class TestCanGenerate:
    """Tests for data sufficiency gate."""

    @pytest.mark.asyncio
    async def test_insufficient_queries(self, mock_db, user_id):
        """Refuses when <20 queries."""
        from app.services.consigli_service import consigli_service

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        mock_db.execute.return_value = mock_result

        result = await consigli_service.can_generate(user_id, mock_db)

        assert result["can_generate"] is False
        assert result["query_count"] == 5
        assert "dati sufficienti" in result["message_it"].lower()

    @pytest.mark.asyncio
    async def test_insufficient_history_days(self, mock_db, user_id):
        """Refuses when history span <7 days."""
        from app.services.consigli_service import consigli_service

        # First call returns count >= 20, second returns date range < 7 days
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 25

        now = datetime.utcnow()
        mock_dates_result = MagicMock()
        mock_dates_result.one_or_none.return_value = MagicMock(min_ts=now - timedelta(days=3), max_ts=now)

        mock_db.execute.side_effect = [mock_count_result, mock_dates_result]

        result = await consigli_service.can_generate(user_id, mock_db)

        assert result["can_generate"] is False
        assert result["history_days"] < 7

    @pytest.mark.asyncio
    async def test_sufficient_data(self, mock_db, user_id):
        """Allows when >=20 queries and >=7 days."""
        from app.services.consigli_service import consigli_service

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 50

        now = datetime.utcnow()
        mock_dates_result = MagicMock()
        mock_dates_result.one_or_none.return_value = MagicMock(min_ts=now - timedelta(days=30), max_ts=now)

        mock_db.execute.side_effect = [mock_count_result, mock_dates_result]

        result = await consigli_service.can_generate(user_id, mock_db)

        assert result["can_generate"] is True
        assert result["query_count"] == 50
        assert result["history_days"] >= 7


class TestCollectStats:
    """Tests for statistical data collection."""

    @pytest.mark.asyncio
    async def test_collects_domain_distribution(self, mock_db, user_id):
        """Computes domain distribution from query types."""
        from app.services.consigli_service import consigli_service

        rows = _make_history_rows(30, days_span=30)
        mock_result = MagicMock()
        mock_result.all.return_value = rows
        mock_db.execute.return_value = mock_result

        stats = await consigli_service.collect_stats(user_id, mock_db)

        assert "domain_distribution" in stats
        assert isinstance(stats["domain_distribution"], dict)
        assert sum(stats["domain_distribution"].values()) == 30

    @pytest.mark.asyncio
    async def test_collects_temporal_patterns(self, mock_db, user_id):
        """Computes temporal patterns (hour distribution)."""
        from app.services.consigli_service import consigli_service

        rows = _make_history_rows(30, days_span=30)
        mock_result = MagicMock()
        mock_result.all.return_value = rows
        mock_db.execute.return_value = mock_result

        stats = await consigli_service.collect_stats(user_id, mock_db)

        assert "hourly_distribution" in stats
        assert "session_count" in stats

    @pytest.mark.asyncio
    async def test_collects_quality_signals(self, mock_db, user_id):
        """Computes cache hit rate and other quality metrics."""
        from app.services.consigli_service import consigli_service

        rows = _make_history_rows(30, days_span=30)
        mock_result = MagicMock()
        mock_result.all.return_value = rows
        mock_db.execute.return_value = mock_result

        stats = await consigli_service.collect_stats(user_id, mock_db)

        assert "cache_hit_rate" in stats
        assert 0 <= stats["cache_hit_rate"] <= 1.0

    @pytest.mark.asyncio
    async def test_no_cost_data_in_stats(self, mock_db, user_id):
        """Stats must NOT include cost, token, or pricing data."""
        from app.services.consigli_service import consigli_service

        rows = _make_history_rows(30, days_span=30)
        mock_result = MagicMock()
        mock_result.all.return_value = rows
        mock_db.execute.return_value = mock_result

        stats = await consigli_service.collect_stats(user_id, mock_db)

        stats_str = str(stats).lower()
        assert "cost" not in stats_str
        assert "token" not in stats_str
        assert "price" not in stats_str
        assert "euro" not in stats_str
        assert "€" not in stats_str


class TestGenerateReport:
    """Tests for report generation."""

    @pytest.mark.asyncio
    async def test_returns_html_report(self, mock_db, user_id):
        """Generates self-contained HTML report."""
        from app.services.consigli_service import consigli_service

        with (
            patch.object(
                consigli_service,
                "can_generate",
                return_value={
                    "can_generate": True,
                    "query_count": 50,
                    "history_days": 30,
                    "message_it": "OK",
                },
            ),
            patch.object(
                consigli_service,
                "collect_stats",
                return_value={
                    "total_queries": 50,
                    "domain_distribution": {"tax_calculation": 20, "general": 30},
                    "hourly_distribution": {str(h): 2 for h in range(24)},
                    "session_count": 10,
                    "cache_hit_rate": 0.2,
                    "kb_sources_used": ["ccnl", "normativa"],
                    "history_days": 30,
                    "active_days": 20,
                },
            ),
            patch.object(
                consigli_service,
                "_call_llm_analysis",
                return_value="Analisi personalizzata delle interazioni.",
            ),
        ):
            result = await consigli_service.generate_report(user_id, mock_db)

        assert result["status"] == "success"
        assert result["html_report"] is not None
        assert "<html" in result["html_report"]
        assert 'lang="it"' in result["html_report"]

    @pytest.mark.asyncio
    async def test_insufficient_data_returns_message(self, mock_db, user_id):
        """Returns Italian message when data insufficient."""
        from app.services.consigli_service import consigli_service

        with patch.object(
            consigli_service,
            "can_generate",
            return_value={
                "can_generate": False,
                "query_count": 5,
                "history_days": 2,
                "message_it": "Non ci sono ancora dati sufficienti.",
            },
        ):
            result = await consigli_service.generate_report(user_id, mock_db)

        assert result["status"] == "insufficient_data"
        assert result["html_report"] is None
        assert "dati sufficienti" in result["message_it"].lower()

    @pytest.mark.asyncio
    async def test_no_cost_data_in_html(self, mock_db, user_id):
        """HTML report must NOT contain cost/pricing information."""
        from app.services.consigli_service import consigli_service

        with (
            patch.object(
                consigli_service,
                "can_generate",
                return_value={
                    "can_generate": True,
                    "query_count": 50,
                    "history_days": 30,
                    "message_it": "OK",
                },
            ),
            patch.object(
                consigli_service,
                "collect_stats",
                return_value={
                    "total_queries": 50,
                    "domain_distribution": {"tax_calculation": 20, "general": 30},
                    "hourly_distribution": {str(h): 2 for h in range(24)},
                    "session_count": 10,
                    "cache_hit_rate": 0.2,
                    "kb_sources_used": ["ccnl"],
                    "history_days": 30,
                    "active_days": 20,
                },
            ),
            patch.object(
                consigli_service,
                "_call_llm_analysis",
                return_value="Suggerimenti personalizzati.",
            ),
        ):
            result = await consigli_service.generate_report(user_id, mock_db)

        html = result["html_report"].lower()
        assert "€" not in html
        assert "costo" not in html
        assert "token" not in html
        assert "prezzo" not in html

    @pytest.mark.asyncio
    async def test_llm_output_anonymized(self, mock_db, user_id):
        """LLM output is run through anonymizer before rendering."""
        from app.services.consigli_service import consigli_service

        with (
            patch.object(
                consigli_service,
                "can_generate",
                return_value={
                    "can_generate": True,
                    "query_count": 50,
                    "history_days": 30,
                    "message_it": "OK",
                },
            ),
            patch.object(
                consigli_service,
                "collect_stats",
                return_value={
                    "total_queries": 50,
                    "domain_distribution": {"general": 50},
                    "hourly_distribution": {},
                    "session_count": 5,
                    "cache_hit_rate": 0.1,
                    "kb_sources_used": [],
                    "history_days": 30,
                    "active_days": 15,
                },
            ),
            patch.object(
                consigli_service,
                "_call_llm_analysis",
                return_value="L'utente mario.rossi@email.com usa spesso il sistema.",
            ),
            patch("app.services.consigli_service.anonymizer.anonymize_text") as mock_anon,
        ):
            mock_anon.return_value = MagicMock(anonymized_text="L'utente [EMAIL_REDACTED] usa spesso il sistema.")
            result = await consigli_service.generate_report(user_id, mock_db)

        mock_anon.assert_called_once()
        assert "mario.rossi@email.com" not in result["html_report"]


class TestConcurrencyGuard:
    """Tests for Redis concurrency guard (RC-4)."""

    @pytest.mark.asyncio
    async def test_blocks_concurrent_generation(self, mock_db, user_id):
        """Returns 'generating' status when report already in progress."""
        from app.services.consigli_service import consigli_service

        with patch("app.services.consigli_service.get_redis_client") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get.return_value = b"1"  # Lock exists
            mock_get_redis.return_value = mock_redis

            result = await consigli_service.generate_report(user_id, mock_db)

        assert result["status"] == "generating"
        assert "generazione" in result["message_it"].lower()

    @pytest.mark.asyncio
    async def test_sets_lock_during_generation(self, mock_db, user_id):
        """Sets Redis lock key with TTL during report generation."""
        from app.services.consigli_service import consigli_service

        with (
            patch("app.services.consigli_service.get_redis_client") as mock_get_redis,
            patch.object(
                consigli_service,
                "can_generate",
                return_value={
                    "can_generate": True,
                    "query_count": 50,
                    "history_days": 30,
                    "message_it": "OK",
                },
            ),
            patch.object(
                consigli_service,
                "collect_stats",
                return_value={
                    "total_queries": 50,
                    "domain_distribution": {"general": 50},
                    "hourly_distribution": {},
                    "session_count": 5,
                    "cache_hit_rate": 0.1,
                    "kb_sources_used": [],
                    "history_days": 30,
                    "active_days": 15,
                },
            ),
            patch.object(
                consigli_service,
                "_call_llm_analysis",
                return_value="Analisi.",
            ),
        ):
            mock_redis = AsyncMock()
            mock_redis.get.return_value = None  # No lock
            mock_get_redis.return_value = mock_redis

            await consigli_service.generate_report(user_id, mock_db)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert f"consigli:generating:{user_id}" in str(call_args)
