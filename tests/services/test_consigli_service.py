"""Tests for ConsigliService (ADR-038: /consigli insight report).

TDD RED phase: Tests written before implementation.
Tests: data sufficiency gate, stats collection, report generation,
       concurrency guard, PII anonymization, rendering helpers.
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


@pytest.fixture
def sample_stats():
    """Standard stats dict for rendering tests."""
    return {
        "total_queries": 50,
        "domain_distribution": {"tax_calculation": 20, "general": 30},
        "hourly_distribution": {"9": 10, "14": 8, "16": 6, "11": 4},
        "session_count": 10,
        "cache_hit_rate": 0.2,
        "kb_sources_used": ["ccnl", "normativa"],
        "history_days": 30,
        "active_days": 20,
    }


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

    @pytest.mark.asyncio
    async def test_null_date_range(self, mock_db, user_id):
        """Handles null date range (all timestamps null)."""
        from app.services.consigli_service import consigli_service

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 25

        mock_dates_result = MagicMock()
        mock_dates_result.one_or_none.return_value = MagicMock(min_ts=None, max_ts=None)

        mock_db.execute.side_effect = [mock_count_result, mock_dates_result]

        result = await consigli_service.can_generate(user_id, mock_db)

        assert result["can_generate"] is False
        assert result["history_days"] == 0


class TestCollectStats:
    """Tests for statistical data collection."""

    @pytest.mark.asyncio
    async def test_collects_domain_distribution(self, mock_db, user_id):
        """Computes domain distribution from query types."""
        from app.services.consigli_service import consigli_service

        rows = _make_history_rows(30, days_span=30)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = rows
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
        mock_result.scalars.return_value.all.return_value = rows
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
        mock_result.scalars.return_value.all.return_value = rows
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
        mock_result.scalars.return_value.all.return_value = rows
        mock_db.execute.return_value = mock_result

        stats = await consigli_service.collect_stats(user_id, mock_db)

        stats_str = str(stats).lower()
        assert "cost" not in stats_str
        assert "token" not in stats_str
        assert "price" not in stats_str
        assert "euro" not in stats_str
        assert "€" not in stats_str

    @pytest.mark.asyncio
    async def test_empty_rows_returns_zero_stats(self, mock_db, user_id):
        """Returns zero values when no query history rows exist."""
        from app.services.consigli_service import consigli_service

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        stats = await consigli_service.collect_stats(user_id, mock_db)

        assert stats["total_queries"] == 0
        assert stats["session_count"] == 0
        assert stats["cache_hit_rate"] == 0
        assert stats["history_days"] == 0
        assert stats["active_days"] == 0


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

    @pytest.mark.asyncio
    async def test_stats_summary_in_response(self, mock_db, user_id):
        """Successful report includes stats_summary."""
        from app.services.consigli_service import consigli_service

        with (
            patch.object(
                consigli_service,
                "can_generate",
                return_value={"can_generate": True, "query_count": 50, "history_days": 30, "message_it": "OK"},
            ),
            patch.object(
                consigli_service,
                "collect_stats",
                return_value={
                    "total_queries": 50,
                    "domain_distribution": {"general": 50},
                    "hourly_distribution": {},
                    "session_count": 10,
                    "cache_hit_rate": 0.1,
                    "kb_sources_used": [],
                    "history_days": 30,
                    "active_days": 20,
                },
            ),
            patch.object(consigli_service, "_call_llm_analysis", return_value="Analisi."),
        ):
            result = await consigli_service.generate_report(user_id, mock_db)

        assert result["stats_summary"] is not None
        assert result["stats_summary"]["total_queries"] == 50
        assert result["stats_summary"]["active_days"] == 20
        assert result["stats_summary"]["session_count"] == 10

    @pytest.mark.asyncio
    async def test_error_returns_error_status(self, mock_db, user_id):
        """Returns error status when exception occurs during generation."""
        from app.services.consigli_service import consigli_service

        with (
            patch.object(
                consigli_service,
                "can_generate",
                return_value={"can_generate": True, "query_count": 50, "history_days": 30, "message_it": "OK"},
            ),
            patch.object(consigli_service, "collect_stats", side_effect=RuntimeError("DB connection lost")),
        ):
            result = await consigli_service.generate_report(user_id, mock_db)

        assert result["status"] == "error"
        assert result["html_report"] is None
        assert "errore" in result["message_it"].lower()

    @pytest.mark.asyncio
    async def test_lock_released_on_error(self, mock_db, user_id):
        """Redis lock is released even when generation fails."""
        from app.services.consigli_service import consigli_service

        with (
            patch("app.services.consigli_service.get_redis_client") as mock_get_redis,
            patch.object(
                consigli_service,
                "can_generate",
                return_value={"can_generate": True, "query_count": 50, "history_days": 30, "message_it": "OK"},
            ),
            patch.object(consigli_service, "collect_stats", side_effect=RuntimeError("fail")),
        ):
            mock_redis = AsyncMock()
            mock_redis.get.return_value = None
            mock_get_redis.return_value = mock_redis

            await consigli_service.generate_report(user_id, mock_db)

        mock_redis.delete.assert_called_once_with(f"consigli:generating:{user_id}")


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

    @pytest.mark.asyncio
    async def test_no_redis_proceeds_without_lock(self, mock_db, user_id):
        """When Redis is unavailable, generation proceeds without locking."""
        from app.services.consigli_service import consigli_service

        with (
            patch("app.services.consigli_service.get_redis_client", return_value=None),
            patch.object(
                consigli_service,
                "can_generate",
                return_value={"can_generate": True, "query_count": 50, "history_days": 30, "message_it": "OK"},
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
            patch.object(consigli_service, "_call_llm_analysis", return_value="Analisi."),
        ):
            result = await consigli_service.generate_report(user_id, mock_db)

        assert result["status"] == "success"


class TestCallLlmAnalysis:
    """Tests for _call_llm_analysis (LLM provider interactions)."""

    @pytest.mark.asyncio
    async def test_mistral_provider_returns_content(self):
        """Calls Mistral provider and returns content."""
        from app.services.consigli_service import consigli_service

        stats = {
            "total_queries": 50,
            "domain_distribution": {"general": 50},
            "hourly_distribution": {"9": 10},
            "session_count": 5,
            "cache_hit_rate": 0.1,
            "kb_sources_used": ["ccnl"],
            "history_days": 30,
            "active_days": 20,
        }

        mock_entry = MagicMock()
        mock_entry.provider = "mistral"
        mock_entry.model_name = "mistral-large-latest"

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Analisi generata dal LLM."

        with (
            patch("app.core.llm.model_registry.get_model_registry") as mock_get_reg,
            patch("mistralai.Mistral") as MockMistral,
            patch("app.core.config.settings") as mock_settings,
        ):
            mock_get_reg.return_value.resolve_production_model.return_value = mock_entry
            mock_settings.MISTRAL_API_KEY = "test-key"
            mock_client = MagicMock()
            mock_client.chat.complete_async = AsyncMock(return_value=mock_response)
            MockMistral.return_value = mock_client

            result = await consigli_service._call_llm_analysis(stats)

        assert result == "Analisi generata dal LLM."

    @pytest.mark.asyncio
    async def test_non_mistral_provider_uses_fallback(self):
        """Non-Mistral providers fall back to basic analysis."""
        from app.services.consigli_service import consigli_service

        stats = {
            "total_queries": 50,
            "domain_distribution": {"general": 50},
            "hourly_distribution": {},
            "session_count": 5,
            "cache_hit_rate": 0.1,
            "kb_sources_used": [],
            "history_days": 30,
            "active_days": 20,
        }

        mock_entry = MagicMock()
        mock_entry.provider = "openai"
        mock_entry.model_name = "gpt-4"

        with patch("app.core.llm.model_registry.get_model_registry") as mock_get_reg:
            mock_get_reg.return_value.resolve_production_model.return_value = mock_entry
            result = await consigli_service._call_llm_analysis(stats)

        assert "50" in result  # fallback contains total_queries

    @pytest.mark.asyncio
    async def test_llm_exception_uses_fallback(self):
        """LLM call exceptions fall back to basic analysis."""
        from app.services.consigli_service import consigli_service

        stats = {
            "total_queries": 50,
            "domain_distribution": {"general": 50},
            "hourly_distribution": {},
            "session_count": 5,
            "cache_hit_rate": 0.1,
            "kb_sources_used": [],
            "history_days": 30,
            "active_days": 20,
        }

        mock_entry = MagicMock()
        mock_entry.provider = "mistral"
        mock_entry.model_name = "mistral-large-latest"

        with (
            patch("app.core.llm.model_registry.get_model_registry") as mock_get_reg,
            patch("mistralai.Mistral") as MockMistral,
            patch("app.core.config.settings") as mock_settings,
        ):
            mock_get_reg.return_value.resolve_production_model.return_value = mock_entry
            mock_settings.MISTRAL_API_KEY = "test-key"
            mock_client = MagicMock()
            mock_client.chat.complete_async = AsyncMock(side_effect=RuntimeError("API down"))
            MockMistral.return_value = mock_client

            result = await consigli_service._call_llm_analysis(stats)

        assert "50" in result  # fallback text

    @pytest.mark.asyncio
    async def test_null_registry_entry_defaults_to_mistral(self):
        """None registry entry defaults to Mistral provider."""
        from app.services.consigli_service import consigli_service

        stats = {
            "total_queries": 30,
            "domain_distribution": {"general": 30},
            "hourly_distribution": {},
            "session_count": 3,
            "cache_hit_rate": 0.0,
            "kb_sources_used": [],
            "history_days": 15,
            "active_days": 10,
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Analisi."

        with (
            patch("app.core.llm.model_registry.get_model_registry") as mock_get_reg,
            patch("mistralai.Mistral") as MockMistral,
            patch("app.core.config.settings") as mock_settings,
        ):
            mock_get_reg.return_value.resolve_production_model.return_value = None
            mock_settings.MISTRAL_API_KEY = "test-key"
            mock_client = MagicMock()
            mock_client.chat.complete_async = AsyncMock(return_value=mock_response)
            MockMistral.return_value = mock_client

            result = await consigli_service._call_llm_analysis(stats)

        assert result == "Analisi."
        MockMistral.assert_called_once_with(api_key="test-key")


class TestCollectStatsEdgeCases:
    """Tests for collect_stats edge cases and branch coverage."""

    @pytest.mark.asyncio
    async def test_rows_with_null_fields(self, mock_db, user_id):
        """Handles rows with null timestamp, session_id, kb_sources."""
        from app.services.consigli_service import consigli_service

        rows = [
            MagicMock(
                query_type=None,
                timestamp=None,
                session_id=None,
                response_cached=False,
                kb_sources_metadata=None,
            ),
            MagicMock(
                query_type="general",
                timestamp=datetime.utcnow(),
                session_id="s1",
                response_cached=True,
                kb_sources_metadata=[{"source": "ccnl"}],
            ),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = rows
        mock_db.execute.return_value = mock_result

        stats = await consigli_service.collect_stats(user_id, mock_db)

        assert stats["total_queries"] == 2
        assert "general" in stats["domain_distribution"]

    @pytest.mark.asyncio
    async def test_kb_sources_with_invalid_entries(self, mock_db, user_id):
        """Handles non-dict entries in kb_sources_metadata."""
        from app.services.consigli_service import consigli_service

        rows = [
            MagicMock(
                query_type="general",
                timestamp=datetime.utcnow(),
                session_id="s1",
                response_cached=False,
                kb_sources_metadata=["not-a-dict", {"no-source-key": True}, {"source": "ccnl"}],
            ),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = rows
        mock_db.execute.return_value = mock_result

        stats = await consigli_service.collect_stats(user_id, mock_db)

        assert stats["kb_sources_used"] == ["ccnl"]


class TestFallbackAnalysis:
    """Tests for _generate_fallback_analysis."""

    def test_generates_italian_text(self):
        from app.services.consigli_service import consigli_service

        stats = {
            "total_queries": 50,
            "domain_distribution": {"tax_calculation": 30, "general": 20},
            "history_days": 30,
            "active_days": 20,
            "cache_hit_rate": 0.25,
        }
        result = consigli_service._generate_fallback_analysis(stats)

        assert "50" in result
        assert "30 giorni" in result
        assert "20 giorni attivi" in result
        assert "25%" in result

    def test_picks_top_domain(self):
        from app.services.consigli_service import consigli_service

        stats = {
            "total_queries": 100,
            "domain_distribution": {"tax_calculation": 60, "general": 40},
            "history_days": 30,
            "active_days": 15,
            "cache_hit_rate": 0.1,
        }
        result = consigli_service._generate_fallback_analysis(stats)

        assert "tax_calculation" in result


class TestRenderHelpers:
    """Tests for module-level rendering helper functions."""

    def test_domain_label_known_key(self):
        from app.services.consigli_service import _domain_label

        assert _domain_label("tax_calculation") == "Calcolo fiscale"
        assert _domain_label("general") == "Domande generali"
        assert _domain_label("ccnl") == "CCNL"

    def test_domain_label_unknown_key(self):
        from app.services.consigli_service import _domain_label

        assert _domain_label("custom_category") == "Custom Category"

    def test_escape_html_chars(self):
        from app.services.consigli_service import _escape

        assert _escape("<script>alert('xss')</script>") == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
        assert _escape("safe text") == "safe text"
        assert _escape('a & b "c"') == "a &amp; b &quot;c&quot;"

    def test_text_to_html_escapes_xss(self):
        """XSS payloads in LLM output are escaped."""
        from app.services.consigli_service import _text_to_html

        result = _text_to_html("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_text_to_html_markdown_headers(self):
        from app.services.consigli_service import _text_to_html

        result = _text_to_html("# Titolo\n## Sottotitolo\n### Sezione")
        assert "<h3>" in result
        assert "<h4>" in result

    def test_text_to_html_bold(self):
        from app.services.consigli_service import _text_to_html

        result = _text_to_html("Testo **importante** qui")
        assert "<strong>importante</strong>" in result

    def test_text_to_html_list_items(self):
        from app.services.consigli_service import _text_to_html

        result = _text_to_html("- Primo\n- Secondo\n* Terzo")
        assert "&bull;" in result
        assert "Primo" in result
        assert "Terzo" in result

    def test_text_to_html_empty_lines_skipped(self):
        from app.services.consigli_service import _text_to_html

        result = _text_to_html("Primo\n\n\nSecondo")
        assert result.count("<p>") == 2

    def test_prepare_domain_rows(self, sample_stats):
        from app.services.consigli_service import _prepare_domain_rows

        rows = _prepare_domain_rows(sample_stats)
        assert "<tr>" in rows
        assert "Domande generali" in rows
        assert "Calcolo fiscale" in rows

    def test_prepare_peak_hours(self, sample_stats):
        from app.services.consigli_service import _prepare_peak_hours

        peak = _prepare_peak_hours(sample_stats)
        assert "9:00" in peak  # Highest count

    def test_prepare_peak_hours_empty(self):
        from app.services.consigli_service import _prepare_peak_hours

        peak = _prepare_peak_hours({"hourly_distribution": {}})
        assert peak == "N/D"

    def test_render_report_html_structure(self, sample_stats):
        from app.services.consigli_service import render_report_html

        html = render_report_html(sample_stats, "Analisi di test.")
        assert "<!DOCTYPE html>" in html
        assert '<html lang="it">' in html
        assert "PratikoAI" in html
        assert "Analisi di test." in html
        assert "50" in html  # total_queries
        assert "20" in html  # active_days

    def test_render_report_html_no_cost_data(self, sample_stats):
        """Template itself must not introduce cost/pricing words."""
        from app.services.consigli_service import render_report_html

        html = render_report_html(sample_stats, "Analisi personalizzata.")
        html_lower = html.lower()
        assert "€" not in html_lower
        assert "costo" not in html_lower
        assert "prezzo" not in html_lower

    def test_render_report_html_kb_sources(self, sample_stats):
        from app.services.consigli_service import render_report_html

        html = render_report_html(sample_stats, "Test.")
        assert "ccnl" in html
        assert "normativa" in html

    def test_render_report_html_no_kb_sources(self):
        from app.services.consigli_service import render_report_html

        stats = {
            "total_queries": 10,
            "domain_distribution": {"general": 10},
            "hourly_distribution": {},
            "session_count": 2,
            "cache_hit_rate": 0.0,
            "kb_sources_used": [],
            "history_days": 10,
            "active_days": 5,
        }
        html = render_report_html(stats, "Test.")
        assert "Nessuna specifica" in html


class TestSchemas:
    """Tests for consigli schemas."""

    def test_report_response_success(self):
        from app.schemas.consigli import ConsigliReportResponse

        resp = ConsigliReportResponse(
            status="success",
            message_it="Report generato.",
            html_report="<html></html>",
            stats_summary={"total_queries": 50, "active_days": 20, "session_count": 10},
        )
        assert resp.status == "success"
        assert resp.html_report is not None

    def test_report_response_minimal(self):
        from app.schemas.consigli import ConsigliReportResponse

        resp = ConsigliReportResponse(
            status="insufficient_data",
            message_it="Dati non sufficienti.",
        )
        assert resp.html_report is None
        assert resp.stats_summary is None

    def test_sufficiency_response(self):
        from app.schemas.consigli import ConsigliSufficiencyResponse

        resp = ConsigliSufficiencyResponse(
            can_generate=True,
            message_it="OK",
            query_count=50,
            history_days=30,
        )
        assert resp.can_generate is True
        assert resp.query_count == 50
