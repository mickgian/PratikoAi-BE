"""Tests for comparison service (DEV-256)."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.comparison import (
    ComparisonStatus,
    ModelComparisonSession,
    ModelEloRating,
    UserModelPreference,
)
from app.services.comparison_service import (
    DEFAULT_ELO,
    ELO_K_FACTOR,
    ELO_MAX,
    ELO_MIN,
    ComparisonService,
    get_comparison_service,
)


class TestComparisonServiceHelpers:
    """Test helper methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ComparisonService()

    def test_parse_model_id_valid(self):
        """Test parsing valid model ID."""
        provider, model = self.service._parse_model_id("openai:gpt-4o")

        assert provider == "openai"
        assert model == "gpt-4o"

    def test_parse_model_id_with_colons(self):
        """Test parsing model ID with multiple colons."""
        provider, model = self.service._parse_model_id("anthropic:claude-3:sonnet")

        assert provider == "anthropic"
        assert model == "claude-3:sonnet"

    def test_parse_model_id_invalid(self):
        """Test parsing invalid model ID raises error."""
        with pytest.raises(ValueError, match="Invalid model_id format"):
            self.service._parse_model_id("invalid-model")

    def test_hash_query(self):
        """Test query hashing."""
        hash1 = self.service._hash_query("Test query")
        hash2 = self.service._hash_query("Test query")
        hash3 = self.service._hash_query("Different query")

        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64  # SHA256 hex length

    def test_get_model_display_name_known(self):
        """Test getting display name for known model."""
        name = self.service._get_model_display_name("openai:gpt-4o")

        assert name == "GPT-4o"

    def test_get_model_display_name_unknown(self):
        """Test getting display name for unknown model."""
        name = self.service._get_model_display_name("unknown:model")

        assert name == "unknown:model"


class TestEloCalculation:
    """Test Elo rating calculations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ComparisonService()

    def test_calculate_elo_update_equal_ratings(self):
        """Test Elo update with equal ratings."""
        gain, loss = self.service._calculate_elo_update(1500.0, 1500.0)

        # With equal ratings, expected score is 0.5
        # Gain = K * (1 - 0.5) = 32 * 0.5 = 16
        assert gain == pytest.approx(16.0, rel=0.01)
        assert loss == pytest.approx(16.0, rel=0.01)

    def test_calculate_elo_update_winner_higher(self):
        """Test Elo update when winner has higher rating."""
        gain, loss = self.service._calculate_elo_update(1600.0, 1400.0)

        # Higher rated player gains less for expected win
        assert gain < 16.0
        assert loss < 16.0

    def test_calculate_elo_update_winner_lower(self):
        """Test Elo update when winner has lower rating (upset)."""
        gain, loss = self.service._calculate_elo_update(1400.0, 1600.0)

        # Lower rated player gains more for upset win
        assert gain > 16.0
        assert loss > 16.0

    def test_calculate_elo_update_custom_k_factor(self):
        """Test Elo update with custom K-factor."""
        gain1, _ = self.service._calculate_elo_update(1500.0, 1500.0, k_factor=16)
        gain2, _ = self.service._calculate_elo_update(1500.0, 1500.0, k_factor=32)

        assert gain2 == gain1 * 2


class TestRunComparison:
    """Test run_comparison method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        return db

    @pytest.fixture
    def service(self):
        """Create service with mocked factory."""
        service = ComparisonService()
        return service

    @pytest.mark.asyncio
    async def test_run_comparison_empty_query(self, service, mock_db):
        """Test comparison with empty query raises error."""
        with pytest.raises(ValueError, match="La domanda non può essere vuota"):
            await service.run_comparison("", 1, mock_db)

    @pytest.mark.asyncio
    async def test_run_comparison_query_too_long(self, service, mock_db):
        """Test comparison with query exceeding max length raises error."""
        long_query = "a" * 2001

        with pytest.raises(ValueError, match="supera il limite di 2000 caratteri"):
            await service.run_comparison(long_query, 1, mock_db)

    @pytest.mark.asyncio
    async def test_run_comparison_too_few_models(self, service, mock_db):
        """Test comparison with less than 2 models raises error."""
        with pytest.raises(ValueError, match="Seleziona almeno 2 modelli"):
            await service.run_comparison(
                "Test query",
                1,
                mock_db,
                model_ids=["openai:gpt-4o"],
            )

    @pytest.mark.asyncio
    async def test_run_comparison_too_many_models(self, service, mock_db):
        """Test comparison with more than 6 models raises error."""
        model_ids = [f"openai:model-{i}" for i in range(7)]

        with pytest.raises(ValueError, match="Massimo 6 modelli"):
            await service.run_comparison("Test query", 1, mock_db, model_ids=model_ids)

    @pytest.mark.asyncio
    async def test_run_comparison_parallel_execution(self, service, mock_db):
        """Test that models are called in parallel."""
        from app.schemas.comparison import ModelResponseInfo

        model_ids = ["openai:gpt-4o", "anthropic:claude-3-sonnet"]

        with patch.object(service, "_call_single_model", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = ModelResponseInfo(
                model_id="openai:gpt-4o",
                provider="openai",
                model_name="gpt-4o",
                response_text="Response",
                latency_ms=100,
                cost_eur=0.001,
                input_tokens=10,
                output_tokens=20,
                status="success",
                trace_id="trace-1",
            )

            result = await service.run_comparison("Test query", 1, mock_db, model_ids=model_ids)

            # Should have called both models
            assert mock_call.call_count == 2
            assert result.batch_id is not None
            assert len(result.responses) == 2


class TestSubmitVote:
    """Test submit_vote method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.commit = AsyncMock()
        return db

    @pytest.fixture
    def service(self):
        """Create service."""
        return ComparisonService()

    @pytest.mark.asyncio
    async def test_submit_vote_session_not_found(self, service, mock_db):
        """Test vote for non-existent session raises error."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Sessione di confronto non trovata"):
            await service.submit_vote("batch-123", "openai:gpt-4o", 1, mock_db)

    @pytest.mark.asyncio
    async def test_submit_vote_already_voted(self, service, mock_db):
        """Test double voting raises error."""
        session = MagicMock()
        session.winner_model = "openai:gpt-4o"  # Already voted

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = session
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Voto già registrato"):
            await service.submit_vote("batch-123", "anthropic:claude-3", 1, mock_db)

    @pytest.mark.asyncio
    async def test_submit_vote_winner_not_in_comparison(self, service, mock_db):
        """Test vote for model not in comparison raises error."""
        session = MagicMock()
        session.winner_model = None
        session.models_compared = '["openai:gpt-4o", "anthropic:claude-3"]'

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = session
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Modello non valido"):
            await service.submit_vote("batch-123", "gemini:gemini-pro", 1, mock_db)


class TestGetLeaderboard:
    """Test get_leaderboard method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self):
        """Create service."""
        return ComparisonService()

    @pytest.mark.asyncio
    async def test_get_leaderboard_empty(self, service, mock_db):
        """Test leaderboard with no ratings."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        rankings = await service.get_leaderboard(mock_db)

        assert rankings == []

    @pytest.mark.asyncio
    async def test_get_leaderboard_ordered(self, service, mock_db):
        """Test leaderboard is ordered by Elo rating."""
        rating1 = MagicMock()
        rating1.provider = "openai"
        rating1.model_name = "gpt-4o"
        rating1.elo_rating = 1600.0
        rating1.total_comparisons = 100
        rating1.wins = 60

        rating2 = MagicMock()
        rating2.provider = "anthropic"
        rating2.model_name = "claude-3-sonnet"
        rating2.elo_rating = 1550.0
        rating2.total_comparisons = 80
        rating2.wins = 40

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [rating1, rating2]
        mock_db.execute = AsyncMock(return_value=mock_result)

        rankings = await service.get_leaderboard(mock_db)

        assert len(rankings) == 2
        assert rankings[0].rank == 1
        assert rankings[0].elo_rating == 1600.0
        assert rankings[1].rank == 2
        assert rankings[1].elo_rating == 1550.0

    @pytest.mark.asyncio
    async def test_get_leaderboard_win_rate(self, service, mock_db):
        """Test leaderboard calculates win rate correctly."""
        rating = MagicMock()
        rating.provider = "openai"
        rating.model_name = "gpt-4o"
        rating.elo_rating = 1500.0
        rating.total_comparisons = 100
        rating.wins = 60

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [rating]
        mock_db.execute = AsyncMock(return_value=mock_result)

        rankings = await service.get_leaderboard(mock_db)

        assert rankings[0].win_rate == 0.6

    @pytest.mark.asyncio
    async def test_get_leaderboard_win_rate_zero_comparisons(self, service, mock_db):
        """Test win rate is 0 when no comparisons."""
        rating = MagicMock()
        rating.provider = "openai"
        rating.model_name = "gpt-4o"
        rating.elo_rating = 1500.0
        rating.total_comparisons = 0
        rating.wins = 0

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [rating]
        mock_db.execute = AsyncMock(return_value=mock_result)

        rankings = await service.get_leaderboard(mock_db)

        assert rankings[0].win_rate == 0.0


class TestGetUserStats:
    """Test get_user_stats method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self):
        """Create service."""
        return ComparisonService()

    @pytest.mark.asyncio
    async def test_get_user_stats_empty(self, service, mock_db):
        """Test stats for user with no activity."""
        # Mock all the queries to return 0
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_result.first.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        stats = await service.get_user_stats(1, mock_db)

        assert stats.total_comparisons == 0
        assert stats.total_votes == 0
        assert stats.favorite_model is None


class TestGlobalInstance:
    """Test global service instance."""

    def test_get_comparison_service_singleton(self):
        """Test that get_comparison_service returns singleton."""
        service1 = get_comparison_service()
        service2 = get_comparison_service()

        assert service1 is service2


class TestConstants:
    """Test service constants."""

    def test_elo_constants(self):
        """Test Elo rating constants."""
        assert ELO_K_FACTOR == 32
        assert ELO_MIN == 0
        assert ELO_MAX == 3000
        assert DEFAULT_ELO == 1500.0


class TestBestModelsConfiguration:
    """Test best models configuration (DEV-256)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ComparisonService()

    def test_get_current_model_id_returns_env_value(self):
        """Test get_current_model_id reads from settings."""
        from app.core.config import settings

        result = self.service.get_current_model_id()

        assert result == settings.PRODUCTION_LLM_MODEL

    def test_get_current_model_id_format(self):
        """Test current model ID has provider:model format."""
        result = self.service.get_current_model_id()

        assert ":" in result
        provider, model = result.split(":", 1)
        assert provider in ["openai", "anthropic", "gemini", "mistral"]
        assert len(model) > 0

    def test_get_default_comparison_model_ids_includes_current(self):
        """Test default models include current production model."""
        result = self.service.get_default_comparison_model_ids()
        current = self.service.get_current_model_id()

        assert current in result
        assert result[0] == current  # Current should be first

    def test_get_default_comparison_model_ids_includes_best_models(self):
        """Test default models include best models from each provider."""
        from app.services.comparison_service import BEST_MODELS_BY_PROVIDER

        result = self.service.get_default_comparison_model_ids()

        # Should include at least some best models
        best_model_ids = set(BEST_MODELS_BY_PROVIDER.values())
        included_best = [m for m in result if m in best_model_ids]

        # At least 3 best models should be included (4 minus possible current overlap)
        assert len(included_best) >= 3

    def test_get_default_comparison_model_ids_no_duplicates(self):
        """Test default models have no duplicates."""
        result = self.service.get_default_comparison_model_ids()

        assert len(result) == len(set(result))

    def test_get_default_comparison_model_ids_max_5_models(self):
        """Test default models are at most 5 (current + 4 best)."""
        result = self.service.get_default_comparison_model_ids()

        assert len(result) <= 5


class TestRunComparisonWithExisting:
    """Test run_comparison_with_existing method (DEV-256)."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        return db

    @pytest.fixture
    def service(self):
        """Create service."""
        return ComparisonService()

    @pytest.fixture
    def existing_response(self):
        """Create existing response fixture."""
        from app.schemas.comparison import ExistingModelResponse

        return ExistingModelResponse(
            model_id="openai:gpt-4o",
            response_text="This is the existing response from main chat.",
            latency_ms=500,
            cost_eur=0.01,
            input_tokens=100,
            output_tokens=200,
            trace_id="main-chat-trace-123",
        )

    @pytest.mark.asyncio
    async def test_run_comparison_with_existing_empty_query(self, service, mock_db, existing_response):
        """Test comparison with existing response and empty query raises error."""
        with pytest.raises(ValueError, match="La domanda non può essere vuota"):
            await service.run_comparison_with_existing("", 1, mock_db, existing_response)

    @pytest.mark.asyncio
    async def test_run_comparison_with_existing_query_too_long(self, service, mock_db, existing_response):
        """Test comparison with existing response and query exceeding max length raises error."""
        long_query = "a" * 2001

        with pytest.raises(ValueError, match="supera il limite di 2000 caratteri"):
            await service.run_comparison_with_existing(long_query, 1, mock_db, existing_response)

    @pytest.mark.asyncio
    async def test_run_comparison_with_existing_reuses_response(self, service, mock_db, existing_response):
        """Test that existing response is included in results without re-calling."""
        from app.schemas.comparison import ModelResponseInfo

        with patch.object(service, "_call_single_model", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = ModelResponseInfo(
                model_id="anthropic:claude-opus-4-5-20251101",
                provider="anthropic",
                model_name="claude-opus-4-5-20251101",
                response_text="Response from other model",
                latency_ms=600,
                cost_eur=0.02,
                input_tokens=100,
                output_tokens=200,
                status="success",
                trace_id="trace-2",
            )

            result = await service.run_comparison_with_existing("Test query", 1, mock_db, existing_response)

            # Should NOT have called the existing model
            called_model_ids = [call.args[0] for call in mock_call.call_args_list]
            assert "openai:gpt-4o" not in called_model_ids

            # Should include the existing response
            response_model_ids = [r.model_id for r in result.responses]
            assert "openai:gpt-4o" in response_model_ids

            # Existing response should have original text
            existing_in_result = next(r for r in result.responses if r.model_id == "openai:gpt-4o")
            assert existing_in_result.response_text == existing_response.response_text
            assert existing_in_result.latency_ms == existing_response.latency_ms

    @pytest.mark.asyncio
    async def test_run_comparison_with_existing_calls_other_models(self, service, mock_db, existing_response):
        """Test that other best models are called."""
        from app.schemas.comparison import ModelResponseInfo
        from app.services.comparison_service import BEST_MODELS_BY_PROVIDER

        call_count = 0

        async def mock_call(model_id, query, batch_id, enriched_prompt=None):
            nonlocal call_count
            call_count += 1
            provider, model_name = model_id.split(":", 1)
            return ModelResponseInfo(
                model_id=model_id,
                provider=provider,
                model_name=model_name,
                response_text=f"Response from {model_id}",
                latency_ms=500,
                cost_eur=0.01,
                input_tokens=100,
                output_tokens=200,
                status="success",
                trace_id=f"trace-{model_id}",
            )

        with patch.object(service, "_call_single_model", side_effect=mock_call):
            await service.run_comparison_with_existing("Test query", 1, mock_db, existing_response)

            # Should call other best models (excluding current)
            # DEV-256: Count is dynamic based on BEST_MODELS_BY_PROVIDER (Gemini disabled)
            expected_count = len(BEST_MODELS_BY_PROVIDER)  # All best models except current
            assert call_count == expected_count


class TestAvailableModelsFlags:
    """Test is_best and is_current flags in AvailableModel (DEV-256)."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)
        return db

    @pytest.fixture
    def service(self):
        """Create service with mocked factory."""
        service = ComparisonService()
        return service

    @pytest.mark.asyncio
    async def test_available_models_include_is_best_flag(self, service, mock_db):
        """Test that available models include is_best flag."""
        from app.services.comparison_service import BEST_MODELS_BY_PROVIDER

        with patch.object(service._factory, "create_provider") as mock_create:
            mock_provider = MagicMock()
            mock_provider.supported_models = ["gpt-4-turbo", "gpt-4o"]
            mock_create.return_value = mock_provider

            models = await service.get_available_models(1, mock_db)

            # Check that is_best is set correctly
            for model in models:
                expected_is_best = model.model_id in BEST_MODELS_BY_PROVIDER.values()
                assert model.is_best == expected_is_best

    @pytest.mark.asyncio
    async def test_available_models_include_is_current_flag(self, service, mock_db):
        """Test that available models include is_current flag."""
        current_model = service.get_current_model_id()

        with patch.object(service._factory, "create_provider") as mock_create:
            mock_provider = MagicMock()
            # Include the current model in supported models
            _, model_name = current_model.split(":", 1)
            mock_provider.supported_models = [model_name, "other-model"]
            mock_create.return_value = mock_provider

            models = await service.get_available_models(1, mock_db)

            # Check that is_current is set correctly
            for model in models:
                expected_is_current = model.model_id == current_model
                assert model.is_current == expected_is_current


class TestPendingComparisonMetrics:
    """Test pending comparison with metrics (DEV-256)."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.delete = AsyncMock()
        return db

    @pytest.fixture
    def service(self):
        """Create service."""
        return ComparisonService()

    @pytest.mark.asyncio
    async def test_create_pending_comparison_with_metrics(self, service, mock_db):
        """Test creating pending comparison stores metrics."""
        from app.models.comparison import PendingComparison

        # Track what was added
        added_pending = None

        def capture_add(obj):
            nonlocal added_pending
            if isinstance(obj, PendingComparison):
                added_pending = obj

        mock_db.add.side_effect = capture_add

        # Mock refresh to set ID
        async def mock_refresh(obj):
            obj.id = uuid4()

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)

        await service.create_pending_comparison(
            user_id=1,
            query="Test query",
            response="Test response",
            model_id="openai:gpt-4o",
            db=mock_db,
            enriched_prompt="Full prompt with context",
            latency_ms=1500,
            cost_eur=0.025,
            input_tokens=500,
            output_tokens=250,
            trace_id="trace-abc123",
        )

        # Verify metrics were stored
        assert added_pending is not None
        assert added_pending.latency_ms == 1500
        assert added_pending.cost_eur == 0.025
        assert added_pending.input_tokens == 500
        assert added_pending.output_tokens == 250
        assert added_pending.trace_id == "trace-abc123"

    @pytest.mark.asyncio
    async def test_create_pending_comparison_without_metrics(self, service, mock_db):
        """Test creating pending comparison without metrics uses None defaults."""
        from app.models.comparison import PendingComparison

        added_pending = None

        def capture_add(obj):
            nonlocal added_pending
            if isinstance(obj, PendingComparison):
                added_pending = obj

        mock_db.add.side_effect = capture_add

        async def mock_refresh(obj):
            obj.id = uuid4()

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)

        await service.create_pending_comparison(
            user_id=1,
            query="Test query",
            response="Test response",
            model_id="openai:gpt-4o",
            db=mock_db,
        )

        # Verify metrics are None
        assert added_pending is not None
        assert added_pending.latency_ms is None
        assert added_pending.cost_eur is None
        assert added_pending.input_tokens is None
        assert added_pending.output_tokens is None
        assert added_pending.trace_id is None

    @pytest.mark.asyncio
    async def test_get_pending_comparison_returns_metrics(self, service, mock_db):
        """Test retrieving pending comparison includes metrics."""
        from app.models.comparison import PendingComparison

        # Create mock pending with metrics
        mock_pending = MagicMock(spec=PendingComparison)
        mock_pending.query = "Test query"
        mock_pending.response = "Test response"
        mock_pending.model_id = "openai:gpt-4o"
        mock_pending.enriched_prompt = "Full prompt"
        mock_pending.latency_ms = 1500
        mock_pending.cost_eur = 0.025
        mock_pending.input_tokens = 500
        mock_pending.output_tokens = 250
        mock_pending.trace_id = "trace-abc123"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_pending
        mock_db.execute = AsyncMock(return_value=mock_result)

        data = await service.get_pending_comparison(
            pending_id=str(uuid4()),
            user_id=1,
            db=mock_db,
        )

        # Verify metrics are returned
        assert data is not None
        assert data.latency_ms == 1500
        assert data.cost_eur == 0.025
        assert data.input_tokens == 500
        assert data.output_tokens == 250
        assert data.trace_id == "trace-abc123"

    @pytest.mark.asyncio
    async def test_get_pending_comparison_returns_none_metrics(self, service, mock_db):
        """Test retrieving pending comparison with None metrics."""
        from app.models.comparison import PendingComparison

        mock_pending = MagicMock(spec=PendingComparison)
        mock_pending.query = "Test query"
        mock_pending.response = "Test response"
        mock_pending.model_id = "openai:gpt-4o"
        mock_pending.enriched_prompt = None
        mock_pending.latency_ms = None
        mock_pending.cost_eur = None
        mock_pending.input_tokens = None
        mock_pending.output_tokens = None
        mock_pending.trace_id = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_pending
        mock_db.execute = AsyncMock(return_value=mock_result)

        data = await service.get_pending_comparison(
            pending_id=str(uuid4()),
            user_id=1,
            db=mock_db,
        )

        # Verify None metrics are handled
        assert data is not None
        assert data.latency_ms is None
        assert data.cost_eur is None
        assert data.input_tokens is None
        assert data.output_tokens is None
        assert data.trace_id is None
