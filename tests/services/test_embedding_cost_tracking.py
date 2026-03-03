"""Tests for embedding cost tracking in daily cost reports.

Tracks OpenAI text-embedding-3-small API costs as UsageEvents so they
appear in the daily cost email report for DEV and QA environments.
"""

import importlib
import os
import sys
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.usage import CostCategory, UsageEvent, UsageType

# Force-import the real app.core.embed module (conftest.py mocks it via sys.modules).
# Same approach as tests/core/test_embed.py.
_original_mock = sys.modules.pop("app.core.embed", None)
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "sk-test-dummy-key-for-unit-tests"

try:
    if "app.core.embed" in sys.modules:
        importlib.reload(sys.modules["app.core.embed"])
    else:
        import app.core.embed  # noqa: F811
    _EMBED_AVAILABLE = True
except Exception as _exc:
    _EMBED_AVAILABLE = False
    import warnings

    warnings.warn(f"app.core.embed could not be loaded: {_exc}", stacklevel=1)
    if _original_mock is not None:
        sys.modules["app.core.embed"] = _original_mock

_skip_embed = pytest.mark.skipif(not _EMBED_AVAILABLE, reason="app.core.embed could not be loaded")

# =============================================================================
# 1. CostCategory enum includes EMBEDDING
# =============================================================================


class TestEmbeddingCostCategory:
    """Test that EMBEDDING cost category exists and is usable."""

    def test_embedding_category_exists(self):
        """EMBEDDING must be a valid CostCategory value."""
        assert hasattr(CostCategory, "EMBEDDING")
        assert CostCategory.EMBEDDING == "embedding"

    def test_embedding_category_in_enum_values(self):
        """EMBEDDING must appear in CostCategory enum members."""
        values = [c.value for c in CostCategory]
        assert "embedding" in values

    def test_usage_event_accepts_embedding_category(self):
        """UsageEvent should accept EMBEDDING as cost_category."""
        event = UsageEvent(
            user_id=1,
            event_type=UsageType.API_REQUEST,
            cost_category=CostCategory.EMBEDDING,
            cost_eur=0.001,
        )
        assert event.cost_category == CostCategory.EMBEDDING


# =============================================================================
# 2. UsageTracker.track_embedding_usage()
# =============================================================================


class TestTrackEmbeddingUsage:
    """Test the track_embedding_usage method on UsageTracker."""

    @pytest.mark.asyncio
    async def test_track_single_embedding(self):
        """Track a single embedding API call with token count and cost."""
        from app.services.usage_tracker import usage_tracker

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        with (
            patch("app.services.usage_tracker.database_service") as mock_ds,
            patch("app.services.usage_tracker.settings") as mock_settings,
        ):
            mock_ds.get_db.return_value = mock_db
            mock_settings.ENVIRONMENT = MagicMock(value="development")
            mock_settings.SYSTEM_TEST_USER_ID = 50000

            event = await usage_tracker.track_embedding_usage(
                total_tokens=500,
                model="text-embedding-3-small",
                cost_eur=0.00001,
            )

        assert event.cost_category == CostCategory.EMBEDDING
        assert event.total_tokens == 500
        assert event.model == "text-embedding-3-small"
        assert event.provider == "openai"
        assert event.cost_eur == 0.00001
        assert event.environment == "development"
        assert event.event_type == UsageType.API_REQUEST

    @pytest.mark.asyncio
    async def test_track_batch_embedding(self):
        """Track a batch embedding call with aggregate token count."""
        from app.services.usage_tracker import usage_tracker

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        with (
            patch("app.services.usage_tracker.database_service") as mock_ds,
            patch("app.services.usage_tracker.settings") as mock_settings,
        ):
            mock_ds.get_db.return_value = mock_db
            mock_settings.ENVIRONMENT = MagicMock(value="qa")
            mock_settings.SYSTEM_TEST_USER_ID = 50000

            event = await usage_tracker.track_embedding_usage(
                total_tokens=10000,
                model="text-embedding-3-small",
                cost_eur=0.0002,
                batch_size=20,
            )

        assert event.environment == "qa"
        assert event.total_tokens == 10000
        assert event.cost_eur == 0.0002

    @pytest.mark.asyncio
    async def test_track_embedding_uses_correct_environment(self):
        """Embedding tracking must use settings.ENVIRONMENT, not 'test'."""
        from app.services.usage_tracker import usage_tracker

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        with (
            patch("app.services.usage_tracker.database_service") as mock_ds,
            patch("app.services.usage_tracker.settings") as mock_settings,
        ):
            mock_ds.get_db.return_value = mock_db
            mock_settings.ENVIRONMENT = MagicMock(value="qa")
            mock_settings.SYSTEM_TEST_USER_ID = 50000

            event = await usage_tracker.track_embedding_usage(
                total_tokens=500,
                model="text-embedding-3-small",
                cost_eur=0.00001,
            )

        # Must be "qa", NOT "test" even though we use SYSTEM_TEST_USER_ID
        assert event.environment == "qa"

    @pytest.mark.asyncio
    async def test_track_embedding_error_returns_minimal_event(self):
        """On DB error, return a minimal event without crashing."""
        from app.services.usage_tracker import usage_tracker

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock(side_effect=Exception("DB connection error"))

        with (
            patch("app.services.usage_tracker.database_service") as mock_ds,
            patch("app.services.usage_tracker.settings") as mock_settings,
        ):
            mock_ds.get_db.return_value = mock_db
            mock_settings.ENVIRONMENT = MagicMock(value="development")
            mock_settings.SYSTEM_TEST_USER_ID = 50000

            event = await usage_tracker.track_embedding_usage(
                total_tokens=500,
                model="text-embedding-3-small",
                cost_eur=0.00001,
            )

        # Should not crash, returns minimal event
        assert event.error_occurred is True


# =============================================================================
# 3. embed.py tracks costs after API calls
# =============================================================================


@_skip_embed
class TestEmbedCostTracking:
    """Test that embed.py tracks embedding costs after OpenAI API calls."""

    @pytest.mark.asyncio
    async def test_generate_embedding_tracks_cost(self):
        """generate_embedding should track cost after successful API call."""
        from app.core.embed import generate_embedding

        # Mock OpenAI response
        mock_embedding_data = MagicMock()
        mock_embedding_data.embedding = [0.1] * 1536

        mock_usage = MagicMock()
        mock_usage.total_tokens = 42

        mock_response = MagicMock()
        mock_response.data = [mock_embedding_data]
        mock_response.usage = mock_usage

        with (
            patch("app.core.embed._create_embedding", new_callable=AsyncMock, return_value=mock_response),
            patch("app.core.embed._track_embedding_cost", new_callable=AsyncMock) as mock_track,
        ):
            result = await generate_embedding("test text")

        assert result is not None
        mock_track.assert_called_once()
        call_kwargs = mock_track.call_args
        assert call_kwargs[1]["total_tokens"] == 42
        assert call_kwargs[1]["model"] == "text-embedding-3-small"

    @pytest.mark.asyncio
    async def test_generate_embeddings_batch_tracks_cost(self):
        """generate_embeddings_batch should track cost for each batch."""
        from app.core.embed import generate_embeddings_batch

        # Mock OpenAI response for a batch
        mock_item1 = MagicMock()
        mock_item1.embedding = [0.1] * 1536
        mock_item2 = MagicMock()
        mock_item2.embedding = [0.2] * 1536

        mock_usage = MagicMock()
        mock_usage.total_tokens = 800

        mock_response = MagicMock()
        mock_response.data = [mock_item1, mock_item2]
        mock_response.usage = mock_usage

        with (
            patch("app.core.embed._create_embedding", new_callable=AsyncMock, return_value=mock_response),
            patch("app.core.embed._track_embedding_cost", new_callable=AsyncMock) as mock_track,
        ):
            results = await generate_embeddings_batch(["text 1", "text 2"])

        assert len(results) == 2
        mock_track.assert_called_once()
        call_kwargs = mock_track.call_args
        assert call_kwargs[1]["total_tokens"] == 800

    @pytest.mark.asyncio
    async def test_tracking_failure_does_not_block_embedding(self):
        """If cost tracking fails, the embedding should still be returned."""
        from app.core.embed import generate_embedding

        mock_embedding_data = MagicMock()
        mock_embedding_data.embedding = [0.1] * 1536

        mock_usage = MagicMock()
        mock_usage.total_tokens = 42

        mock_response = MagicMock()
        mock_response.data = [mock_embedding_data]
        mock_response.usage = mock_usage

        with (
            patch("app.core.embed._create_embedding", new_callable=AsyncMock, return_value=mock_response),
            patch(
                "app.core.embed._track_embedding_cost",
                new_callable=AsyncMock,
                side_effect=Exception("tracking failed"),
            ),
        ):
            result = await generate_embedding("test text")

        # Embedding should still succeed even if tracking fails
        assert result is not None
        assert len(result) == 1536


# =============================================================================
# 4. Daily cost report includes embedding costs
# =============================================================================


class TestEmbeddingCostInDailyReport:
    """Test embedding costs in the daily cost report."""

    def test_daily_cost_report_has_embedding_field(self):
        """DailyCostReport must have embedding_cost_eur field."""
        from app.services.daily_cost_report_service import DailyCostReport

        report = DailyCostReport(report_date=date.today())
        assert hasattr(report, "embedding_cost_eur")
        assert report.embedding_cost_eur == 0.0

    def test_environment_breakdown_has_embedding_field(self):
        """EnvironmentCostBreakdown must have embedding_cost_eur field."""
        from app.services.daily_cost_report_service import EnvironmentCostBreakdown

        breakdown = EnvironmentCostBreakdown(environment="development")
        assert hasattr(breakdown, "embedding_cost_eur")
        assert breakdown.embedding_cost_eur == 0.0

    @pytest.mark.asyncio
    async def test_get_totals_includes_embedding_cost(self):
        """_get_totals should return embedding_cost from EMBEDDING category."""
        from app.services.daily_cost_report_service import DailyCostReportService

        mock_db = MagicMock()
        mock_result = MagicMock()
        # Totals row: total_cost, llm_cost, third_party_cost, embedding_cost, total_requests, total_tokens, unique_users
        mock_result.first.return_value = (15.50, 12.00, 3.00, 0.05, 750, 150000, 30)
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = DailyCostReportService(mock_db)
        start_dt = datetime(2026, 3, 2, 0, 0, 0)
        end_dt = datetime(2026, 3, 2, 23, 59, 59)

        totals = await service._get_totals(start_dt, end_dt)

        assert "embedding_cost" in totals
        assert totals["embedding_cost"] == 0.05

    @pytest.mark.asyncio
    async def test_environment_breakdown_includes_embedding_cost(self):
        """_get_environment_breakdown should include embedding cost column."""
        from app.services.daily_cost_report_service import DailyCostReportService

        mock_db = MagicMock()
        mock_result = MagicMock()
        # env, total_cost, llm_cost, third_party_cost, embedding_cost, request_count, total_tokens, unique_users
        mock_result.all.return_value = [
            ("development", 5.05, 4.00, 1.00, 0.05, 250, 50000, 10),
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = DailyCostReportService(mock_db)
        breakdowns = await service._get_environment_breakdown(date(2026, 3, 2))

        assert len(breakdowns) == 1
        assert breakdowns[0].embedding_cost_eur == 0.05

    def test_html_report_contains_embedding_section(self):
        """HTML report must contain an Embedding Costs section."""
        from app.services.daily_cost_report_service import (
            DailyCostReport,
            DailyCostReportService,
            EnvironmentCostBreakdown,
        )

        mock_db = MagicMock()
        service = DailyCostReportService(mock_db)

        report = DailyCostReport(
            report_date=date(2026, 3, 2),
            total_cost_eur=15.55,
            llm_cost_eur=12.00,
            third_party_cost_eur=3.50,
            embedding_cost_eur=0.05,
            total_requests=750,
            total_tokens=150000,
            unique_users=30,
            environment_breakdown=[
                EnvironmentCostBreakdown(
                    environment="development",
                    total_cost_eur=5.05,
                    llm_cost_eur=4.00,
                    third_party_cost_eur=1.00,
                    embedding_cost_eur=0.05,
                    request_count=250,
                    unique_users=10,
                ),
            ],
        )

        html = service._generate_html_report(report)

        assert "Embedding" in html
        assert "0.05" in html


# =============================================================================
# 5. Embedding pricing config
# =============================================================================


class TestEmbeddingPricingConfig:
    """Test embedding pricing configuration."""

    def test_embedding_cost_per_1m_tokens_defined(self):
        """EMBED_COST_PER_1M_TOKENS must be defined in config."""
        from app.core.config import EMBED_COST_PER_1M_TOKENS

        # OpenAI text-embedding-3-small: $0.02 per 1M tokens
        assert EMBED_COST_PER_1M_TOKENS > 0
        assert EMBED_COST_PER_1M_TOKENS == 0.02

    def test_calculate_embedding_cost_usd(self):
        """Test USD cost calculation from token count."""
        from app.core.config import EMBED_COST_PER_1M_TOKENS

        tokens = 500
        cost_usd = tokens * EMBED_COST_PER_1M_TOKENS / 1_000_000
        assert cost_usd == pytest.approx(0.00001, abs=1e-8)

    def test_calculate_embedding_cost_batch(self):
        """Test batch cost calculation (20 texts, ~500 tokens each)."""
        from app.core.config import EMBED_COST_PER_1M_TOKENS

        tokens = 10000  # 20 texts * 500 tokens
        cost_usd = tokens * EMBED_COST_PER_1M_TOKENS / 1_000_000
        assert cost_usd == pytest.approx(0.0002, abs=1e-8)
