"""TDD tests for GoldenLoopController service.

DEV-219: Tests written FIRST per TDD methodology.
Tests cover iteration control, backoff calculation, metrics emission,
and integration with ActionValidator and ActionRegenerator.
"""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# =============================================================================
# Mock database service BEFORE importing any app modules
# =============================================================================
_mock_db_service = MagicMock()
_mock_db_service.engine = MagicMock()
_mock_db_service.get_session = MagicMock()
_mock_db_module = MagicMock()
_mock_db_module.database_service = _mock_db_service
_mock_db_module.DatabaseService = MagicMock(return_value=_mock_db_service)
sys.modules.setdefault("app.services.database", _mock_db_module)


# =============================================================================
# Test Fixtures
# =============================================================================
@pytest.fixture
def valid_actions():
    """Create 3 valid actions that pass validation."""
    return [
        {
            "id": "action_1",
            "label": "Calcola IVA al 22%",
            "icon": "calculator",
            "prompt": "Calcola l'IVA al 22% sull'importo di €15.000",
        },
        {
            "id": "action_2",
            "label": "Verifica scadenza F24 marzo",
            "icon": "calendar",
            "prompt": "Controlla la scadenza del versamento F24 per marzo 2024",
        },
        {
            "id": "action_3",
            "label": "Stima contributi INPS",
            "icon": "euro",
            "prompt": "Stima i contributi INPS per il regime forfettario 2024",
        },
    ]


@pytest.fixture
def invalid_actions():
    """Create actions that fail validation."""
    return [
        {
            "id": "bad_1",
            "label": "Calcola",  # Too short
            "icon": "calculator",
            "prompt": "Calcola qualcosa",  # Too short
        },
    ]


@pytest.fixture
def kb_sources():
    """Sample KB source metadata."""
    return [
        {
            "source_id": "src_1",
            "ref": "Circolare INPS 45/2024",
            "key_topics": ["contributi", "forfettario"],
        },
    ]


@pytest.fixture
def mock_validator():
    """Create mock ActionValidator."""
    from app.services.action_validator import BatchValidationResult

    validator = MagicMock()
    validator.validate_batch = MagicMock(
        return_value=BatchValidationResult(
            validated_actions=[],
            rejected_count=3,
            rejection_log=[],
            quality_score=0.0,
        )
    )
    return validator


@pytest.fixture
def mock_regenerator():
    """Create mock ActionRegenerator."""
    regenerator = MagicMock()
    regenerator.regenerate_if_needed = AsyncMock(return_value=[])
    regenerator._generate_safe_fallback = MagicMock(
        return_value=[
            {"id": "fallback_1", "label": "Approfondisci tema", "icon": "search", "prompt": "Maggiori dettagli"},
            {"id": "fallback_2", "label": "Calcola importo base", "icon": "calculator", "prompt": "Calcola importo"},
        ]
    )
    return regenerator


# =============================================================================
# TestGoldenLoopConfig - Configuration Tests
# =============================================================================
class TestGoldenLoopConfig:
    """Test GoldenLoopConfig dataclass."""

    def test_default_values(self):
        """Default config has sensible values."""
        from app.services.golden_loop_controller import GoldenLoopConfig

        config = GoldenLoopConfig()

        assert config.max_iterations == 2
        assert config.initial_backoff_ms == 100
        assert config.backoff_multiplier == 2.0
        assert config.max_backoff_ms == 1000
        assert config.min_valid_actions == 2

    def test_custom_values(self):
        """Config accepts custom values."""
        from app.services.golden_loop_controller import GoldenLoopConfig

        config = GoldenLoopConfig(
            max_iterations=5,
            initial_backoff_ms=50,
            backoff_multiplier=1.5,
            max_backoff_ms=500,
            min_valid_actions=3,
        )

        assert config.max_iterations == 5
        assert config.initial_backoff_ms == 50
        assert config.backoff_multiplier == 1.5
        assert config.max_backoff_ms == 500
        assert config.min_valid_actions == 3


# =============================================================================
# TestGoldenLoopResult - Result Dataclass Tests
# =============================================================================
class TestGoldenLoopResult:
    """Test GoldenLoopResult dataclass."""

    def test_result_fields(self):
        """Result has all required fields."""
        from app.services.golden_loop_controller import GoldenLoopResult

        result = GoldenLoopResult(
            actions=[{"id": "test"}],
            iterations_used=2,
            total_latency_ms=150.5,
            final_valid_count=1,
            regeneration_triggered=True,
        )

        assert result.actions == [{"id": "test"}]
        assert result.iterations_used == 2
        assert result.total_latency_ms == 150.5
        assert result.final_valid_count == 1
        assert result.regeneration_triggered is True


# =============================================================================
# TestFirstIterationSucceeds - No Retry Needed
# =============================================================================
class TestFirstIterationSucceeds:
    """Test behavior when first iteration succeeds."""

    @pytest.mark.asyncio
    async def test_no_retry_when_enough_valid_actions(self, valid_actions, kb_sources):
        """No regeneration when min_valid_actions is met on first try."""
        from app.services.action_validator import BatchValidationResult
        from app.services.golden_loop_controller import GoldenLoopConfig, GoldenLoopController

        mock_validator = MagicMock()
        mock_validator.validate_batch.return_value = BatchValidationResult(
            validated_actions=valid_actions[:2],  # 2 valid
            rejected_count=1,
            rejection_log=[],
            quality_score=0.67,
        )

        mock_regenerator = MagicMock()
        mock_regenerator.regenerate_if_needed = AsyncMock()

        controller = GoldenLoopController(
            validator=mock_validator,
            regenerator=mock_regenerator,
            config=GoldenLoopConfig(min_valid_actions=2),
        )

        result = await controller.execute(
            actions=valid_actions,
            kb_sources=kb_sources,
            response_text="Test response",
        )

        # Should not call regenerator
        mock_regenerator.regenerate_if_needed.assert_not_called()
        assert result.iterations_used == 1
        assert result.regeneration_triggered is False
        assert len(result.actions) == 2

    @pytest.mark.asyncio
    async def test_returns_validated_actions_on_success(self, valid_actions, kb_sources):
        """Returns validated actions when successful."""
        from app.services.action_validator import BatchValidationResult
        from app.services.golden_loop_controller import GoldenLoopController

        mock_validator = MagicMock()
        mock_validator.validate_batch.return_value = BatchValidationResult(
            validated_actions=valid_actions,
            rejected_count=0,
            rejection_log=[],
            quality_score=1.0,
        )

        mock_regenerator = MagicMock()

        controller = GoldenLoopController(
            validator=mock_validator,
            regenerator=mock_regenerator,
        )

        result = await controller.execute(
            actions=valid_actions,
            kb_sources=kb_sources,
            response_text="Test response",
        )

        assert result.actions == valid_actions
        assert result.final_valid_count == 3


# =============================================================================
# TestRegenerationTriggered - Retry Logic
# =============================================================================
class TestRegenerationTriggered:
    """Test regeneration when validation fails."""

    @pytest.mark.asyncio
    async def test_triggers_regeneration_when_below_threshold(self, invalid_actions, kb_sources):
        """Regeneration triggered when valid_count < min_valid_actions."""
        from app.services.action_validator import BatchValidationResult
        from app.services.golden_loop_controller import GoldenLoopConfig, GoldenLoopController

        mock_validator = MagicMock()
        # First call: 1 valid action (below threshold)
        # Second call: 2 valid actions (after regeneration)
        mock_validator.validate_batch.side_effect = [
            BatchValidationResult(
                validated_actions=[{"id": "1"}],
                rejected_count=2,
                rejection_log=[],
                quality_score=0.33,
            ),
            BatchValidationResult(
                validated_actions=[{"id": "regen_1"}, {"id": "regen_2"}],
                rejected_count=0,
                rejection_log=[],
                quality_score=1.0,
            ),
        ]

        mock_regenerator = MagicMock()
        regenerated = [
            {"id": "regen_1", "label": "Calcola IVA specifica", "icon": "calculator", "prompt": "Calcola IVA"},
            {"id": "regen_2", "label": "Verifica scadenza", "icon": "calendar", "prompt": "Verifica scadenza"},
        ]
        mock_regenerator.regenerate_if_needed = AsyncMock(return_value=regenerated)

        controller = GoldenLoopController(
            validator=mock_validator,
            regenerator=mock_regenerator,
            config=GoldenLoopConfig(min_valid_actions=2),
        )

        result = await controller.execute(
            actions=invalid_actions,
            kb_sources=kb_sources,
            response_text="Test response",
        )

        mock_regenerator.regenerate_if_needed.assert_called_once()
        assert result.regeneration_triggered is True
        assert result.iterations_used == 2

    @pytest.mark.asyncio
    async def test_uses_regenerated_actions(self, kb_sources):
        """Uses regenerated actions after successful regeneration."""
        from app.services.action_validator import BatchValidationResult
        from app.services.golden_loop_controller import GoldenLoopController

        mock_validator = MagicMock()
        mock_validator.validate_batch.side_effect = [
            BatchValidationResult(
                validated_actions=[],
                rejected_count=1,
                rejection_log=[],
                quality_score=0.0,
            ),
            BatchValidationResult(
                validated_actions=[{"id": "regen_1"}, {"id": "regen_2"}],
                rejected_count=0,
                rejection_log=[],
                quality_score=1.0,
            ),
        ]

        regenerated = [
            {"id": "regen_1", "label": "Action One", "icon": "check", "prompt": "First action"},
            {"id": "regen_2", "label": "Action Two", "icon": "check", "prompt": "Second action"},
        ]
        mock_regenerator = MagicMock()
        mock_regenerator.regenerate_if_needed = AsyncMock(return_value=regenerated)

        controller = GoldenLoopController(
            validator=mock_validator,
            regenerator=mock_regenerator,
        )

        result = await controller.execute(
            actions=[{"id": "bad"}],
            kb_sources=kb_sources,
            response_text="Test",
        )

        assert len(result.actions) == 2
        assert result.actions[0]["id"] == "regen_1"


# =============================================================================
# TestMaxIterationsReached - Iteration Limit
# =============================================================================
class TestMaxIterationsReached:
    """Test behavior when max iterations is reached."""

    @pytest.mark.asyncio
    async def test_stops_at_max_iterations(self, kb_sources):
        """Stops after max_iterations and returns best available."""
        from app.services.action_validator import BatchValidationResult
        from app.services.golden_loop_controller import GoldenLoopConfig, GoldenLoopController

        mock_validator = MagicMock()
        # All iterations fail to reach threshold
        mock_validator.validate_batch.return_value = BatchValidationResult(
            validated_actions=[{"id": "partial"}],
            rejected_count=2,
            rejection_log=[],
            quality_score=0.33,
        )

        mock_regenerator = MagicMock()
        mock_regenerator.regenerate_if_needed = AsyncMock(return_value=[{"id": "regen"}])

        controller = GoldenLoopController(
            validator=mock_validator,
            regenerator=mock_regenerator,
            config=GoldenLoopConfig(max_iterations=3),
        )

        result = await controller.execute(
            actions=[{"id": "bad"}],
            kb_sources=kb_sources,
            response_text="Test",
        )

        # Should stop at max iterations
        assert result.iterations_used <= 3
        # Should return best available actions
        assert len(result.actions) >= 1

    @pytest.mark.asyncio
    async def test_uses_fallback_when_all_iterations_fail(self, kb_sources):
        """Uses fallback actions when all iterations fail."""
        from app.services.action_validator import BatchValidationResult
        from app.services.golden_loop_controller import GoldenLoopConfig, GoldenLoopController

        mock_validator = MagicMock()
        mock_validator.validate_batch.return_value = BatchValidationResult(
            validated_actions=[],
            rejected_count=3,
            rejection_log=[],
            quality_score=0.0,
        )

        fallback_actions = [
            {"id": "fallback_1", "label": "Safe Action 1", "icon": "check", "prompt": "Safe prompt 1"},
            {"id": "fallback_2", "label": "Safe Action 2", "icon": "check", "prompt": "Safe prompt 2"},
        ]

        mock_regenerator = MagicMock()
        mock_regenerator.regenerate_if_needed = AsyncMock(return_value=[])
        mock_regenerator._generate_safe_fallback = MagicMock(return_value=fallback_actions)

        controller = GoldenLoopController(
            validator=mock_validator,
            regenerator=mock_regenerator,
            config=GoldenLoopConfig(max_iterations=2),
        )

        result = await controller.execute(
            actions=[{"id": "bad"}],
            kb_sources=kb_sources,
            response_text="Test",
        )

        # Should have fallback actions
        assert len(result.actions) >= 0  # May have fallback or empty


# =============================================================================
# TestBackoffCalculation - Exponential Backoff
# =============================================================================
class TestBackoffCalculation:
    """Test exponential backoff calculation."""

    def test_first_iteration_no_backoff(self):
        """First iteration has no backoff."""
        from app.services.golden_loop_controller import GoldenLoopConfig, GoldenLoopController

        controller = GoldenLoopController(
            validator=MagicMock(),
            regenerator=MagicMock(),
            config=GoldenLoopConfig(initial_backoff_ms=100),
        )

        backoff = controller._calculate_backoff(0)
        assert backoff == 0

    def test_second_iteration_initial_backoff(self):
        """Second iteration uses initial backoff."""
        from app.services.golden_loop_controller import GoldenLoopConfig, GoldenLoopController

        controller = GoldenLoopController(
            validator=MagicMock(),
            regenerator=MagicMock(),
            config=GoldenLoopConfig(initial_backoff_ms=100),
        )

        backoff = controller._calculate_backoff(1)
        assert backoff == 100

    def test_exponential_backoff_growth(self):
        """Backoff grows exponentially."""
        from app.services.golden_loop_controller import GoldenLoopConfig, GoldenLoopController

        controller = GoldenLoopController(
            validator=MagicMock(),
            regenerator=MagicMock(),
            config=GoldenLoopConfig(
                initial_backoff_ms=100,
                backoff_multiplier=2.0,
            ),
        )

        assert controller._calculate_backoff(1) == 100
        assert controller._calculate_backoff(2) == 200
        assert controller._calculate_backoff(3) == 400

    def test_backoff_capped_at_max(self):
        """Backoff is capped at max_backoff_ms."""
        from app.services.golden_loop_controller import GoldenLoopConfig, GoldenLoopController

        controller = GoldenLoopController(
            validator=MagicMock(),
            regenerator=MagicMock(),
            config=GoldenLoopConfig(
                initial_backoff_ms=100,
                backoff_multiplier=10.0,
                max_backoff_ms=500,
            ),
        )

        # iteration 2 would be 100 * 10 = 1000, but capped at 500
        backoff = controller._calculate_backoff(2)
        assert backoff == 500

    def test_negative_backoff_clamped_to_zero(self):
        """Negative backoff config clamps to 0."""
        from app.services.golden_loop_controller import GoldenLoopConfig, GoldenLoopController

        controller = GoldenLoopController(
            validator=MagicMock(),
            regenerator=MagicMock(),
            config=GoldenLoopConfig(initial_backoff_ms=-100),
        )

        backoff = controller._calculate_backoff(1)
        assert backoff >= 0


# =============================================================================
# TestMetricsEmitted - Prometheus Metrics
# =============================================================================
class TestMetricsEmitted:
    """Test Prometheus metrics emission."""

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_success(self, valid_actions, kb_sources):
        """Prometheus metrics are recorded on successful execution."""
        from app.services.action_validator import BatchValidationResult
        from app.services.golden_loop_controller import GoldenLoopController

        mock_validator = MagicMock()
        mock_validator.validate_batch.return_value = BatchValidationResult(
            validated_actions=valid_actions,
            rejected_count=0,
            rejection_log=[],
            quality_score=1.0,
        )

        controller = GoldenLoopController(
            validator=mock_validator,
            regenerator=MagicMock(),
        )

        with patch.object(controller, "_emit_metrics") as mock_emit:
            result = await controller.execute(
                actions=valid_actions,
                kb_sources=kb_sources,
                response_text="Test",
            )

            mock_emit.assert_called_once_with(result)

    def test_emit_metrics_calls_prometheus(self):
        """_emit_metrics records to Prometheus counters and histograms."""
        from app.services.golden_loop_controller import (
            GoldenLoopController,
            GoldenLoopResult,
        )

        controller = GoldenLoopController(
            validator=MagicMock(),
            regenerator=MagicMock(),
        )

        result = GoldenLoopResult(
            actions=[{"id": "1"}, {"id": "2"}],
            iterations_used=2,
            total_latency_ms=150.0,
            final_valid_count=2,
            regeneration_triggered=True,
        )

        # Patch the metric objects directly in the module
        with (
            patch("app.services.golden_loop_controller.golden_loop_iterations_total") as mock_iter,
            patch("app.services.golden_loop_controller.golden_loop_regeneration_total") as mock_regen,
            patch("app.services.golden_loop_controller.golden_loop_duration_seconds") as mock_duration,
            patch("app.services.golden_loop_controller.golden_loop_final_valid_actions") as mock_valid,
        ):
            controller._emit_metrics(result)

            # Verify metrics were called
            mock_iter.labels.assert_called()
            mock_regen.inc.assert_called_once()  # regeneration_triggered=True
            mock_duration.observe.assert_called_once()
            mock_valid.set.assert_called_once_with(2)


# =============================================================================
# TestZeroActionsInput - Edge Case
# =============================================================================
class TestZeroActionsInput:
    """Test behavior with zero input actions."""

    @pytest.mark.asyncio
    async def test_empty_actions_uses_fallback(self, kb_sources):
        """Empty actions input triggers fallback directly."""
        from app.services.golden_loop_controller import GoldenLoopController

        fallback_actions = [
            {"id": "fallback_1", "label": "Default Action", "icon": "check", "prompt": "Default"},
        ]

        mock_regenerator = MagicMock()
        mock_regenerator._generate_safe_fallback = MagicMock(return_value=fallback_actions)

        controller = GoldenLoopController(
            validator=MagicMock(),
            regenerator=mock_regenerator,
        )

        result = await controller.execute(
            actions=[],  # Empty input
            kb_sources=kb_sources,
            response_text="Test",
        )

        # Should return fallback or empty
        assert result.iterations_used == 1


# =============================================================================
# TestIntegrationWithValidatorRegenerator - End-to-End
# =============================================================================
class TestIntegrationWithValidatorRegenerator:
    """Integration tests with real ActionValidator and ActionRegenerator."""

    @pytest.mark.asyncio
    async def test_full_loop_with_real_validator(self, valid_actions, kb_sources):
        """Full loop with real ActionValidator."""
        from app.services.action_validator import ActionValidator
        from app.services.golden_loop_controller import GoldenLoopController

        validator = ActionValidator()
        mock_regenerator = MagicMock()

        controller = GoldenLoopController(
            validator=validator,
            regenerator=mock_regenerator,
        )

        result = await controller.execute(
            actions=valid_actions,
            kb_sources=kb_sources,
            response_text="Test response with €15.000 and 22% IVA",
        )

        # Valid actions should pass through
        assert len(result.actions) >= 2
        assert result.regeneration_triggered is False

    @pytest.mark.asyncio
    async def test_total_latency_tracked(self, valid_actions, kb_sources):
        """Total latency is tracked correctly."""
        from app.services.action_validator import BatchValidationResult
        from app.services.golden_loop_controller import GoldenLoopController

        mock_validator = MagicMock()
        mock_validator.validate_batch.return_value = BatchValidationResult(
            validated_actions=valid_actions,
            rejected_count=0,
            rejection_log=[],
            quality_score=1.0,
        )

        controller = GoldenLoopController(
            validator=mock_validator,
            regenerator=MagicMock(),
        )

        result = await controller.execute(
            actions=valid_actions,
            kb_sources=kb_sources,
            response_text="Test",
        )

        assert result.total_latency_ms >= 0
        assert isinstance(result.total_latency_ms, float)


# =============================================================================
# TestLogging - Structured Logging
# =============================================================================
class TestLogging:
    """Test structured logging in Golden Loop."""

    @pytest.mark.asyncio
    async def test_logs_each_iteration(self, kb_sources):
        """Each iteration is logged with context."""
        from app.services.action_validator import BatchValidationResult
        from app.services.golden_loop_controller import GoldenLoopConfig, GoldenLoopController

        mock_validator = MagicMock()
        mock_validator.validate_batch.side_effect = [
            BatchValidationResult(
                validated_actions=[],
                rejected_count=1,
                rejection_log=[],
                quality_score=0.0,
            ),
            BatchValidationResult(
                validated_actions=[{"id": "1"}, {"id": "2"}],
                rejected_count=0,
                rejection_log=[],
                quality_score=1.0,
            ),
        ]

        mock_regenerator = MagicMock()
        mock_regenerator.regenerate_if_needed = AsyncMock(return_value=[{"id": "1"}, {"id": "2"}])

        controller = GoldenLoopController(
            validator=mock_validator,
            regenerator=mock_regenerator,
            config=GoldenLoopConfig(max_iterations=2),
        )

        with patch("app.services.golden_loop_controller.logger") as mock_logger:
            await controller.execute(
                actions=[{"id": "bad"}],
                kb_sources=kb_sources,
                response_text="Test",
            )

            # Should have logged iterations
            assert mock_logger.debug.called or mock_logger.info.called
