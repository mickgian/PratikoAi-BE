"""TDD Tests for DEV-185: PremiumModelSelector Service.

Tests the dynamic model selection for synthesis step per Section 13.10.4.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.llm.model_config import LLMModelConfig, ModelTier


class TestSynthesisContext:
    """Tests for SynthesisContext dataclass."""

    def test_synthesis_context_creation(self):
        """Test creating SynthesisContext with required fields."""
        from app.services.premium_model_selector import SynthesisContext

        context = SynthesisContext(total_tokens=5000, query_complexity="medium")

        assert context.total_tokens == 5000
        assert context.query_complexity == "medium"

    def test_synthesis_context_defaults(self):
        """Test SynthesisContext default values."""
        from app.services.premium_model_selector import SynthesisContext

        context = SynthesisContext(total_tokens=1000)

        assert context.total_tokens == 1000
        assert context.query_complexity == "standard"


class TestModelSelection:
    """Tests for ModelSelection dataclass."""

    def test_model_selection_creation(self):
        """Test creating ModelSelection with all fields."""
        from app.services.premium_model_selector import ModelSelection

        selection = ModelSelection(
            model="gpt-4o",
            provider="openai",
            is_fallback=False,
        )

        assert selection.model == "gpt-4o"
        assert selection.provider == "openai"
        assert selection.is_fallback is False

    def test_model_selection_fallback(self):
        """Test ModelSelection with fallback flag."""
        from app.services.premium_model_selector import ModelSelection

        selection = ModelSelection(
            model="claude-3-5-sonnet-20241022",
            provider="anthropic",
            is_fallback=True,
        )

        assert selection.is_fallback is True

    def test_model_selection_degraded_flag(self):
        """Test ModelSelection with degraded flag."""
        from app.services.premium_model_selector import ModelSelection

        selection = ModelSelection(
            model="gpt-4o",
            provider="openai",
            is_fallback=False,
            is_degraded=True,
        )

        assert selection.is_degraded is True


class TestPremiumModelSelector:
    """Tests for PremiumModelSelector class."""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create a mock LLMModelConfig."""
        config = MagicMock(spec=LLMModelConfig)
        config.get_model.return_value = "gpt-4o"
        config.get_provider.return_value = "openai"
        config.get_fallback.return_value = {
            "model": "claude-3-5-sonnet-20241022",
            "provider": "anthropic",
        }
        return config

    def test_selects_gpt4o_by_default(self, mock_config):
        """Test that GPT-4o is selected by default for normal context."""
        from app.services.premium_model_selector import (
            PremiumModelSelector,
            SynthesisContext,
        )

        selector = PremiumModelSelector(config=mock_config)
        context = SynthesisContext(total_tokens=5000)

        selection = selector.select(context)

        assert selection.model == "gpt-4o"
        assert selection.provider == "openai"
        assert selection.is_fallback is False

    def test_selects_claude_for_long_context(self, mock_config):
        """Test that Claude is selected for context >8k tokens."""
        from app.services.premium_model_selector import (
            PremiumModelSelector,
            SynthesisContext,
        )

        selector = PremiumModelSelector(config=mock_config)
        context = SynthesisContext(total_tokens=10000)  # >8000 tokens

        selection = selector.select(context)

        assert selection.model == "claude-3-5-sonnet-20241022"
        assert selection.provider == "anthropic"
        assert selection.is_fallback is False

    def test_selects_gpt4o_at_exactly_8000_tokens(self, mock_config):
        """Test that GPT-4o is selected at exactly 8000 tokens (threshold is >8000)."""
        from app.services.premium_model_selector import (
            PremiumModelSelector,
            SynthesisContext,
        )

        selector = PremiumModelSelector(config=mock_config)
        context = SynthesisContext(total_tokens=8000)  # Exactly 8000

        selection = selector.select(context)

        assert selection.model == "gpt-4o"
        assert selection.provider == "openai"

    def test_selects_claude_at_8001_tokens(self, mock_config):
        """Test that Claude is selected at 8001 tokens (just over threshold)."""
        from app.services.premium_model_selector import (
            PremiumModelSelector,
            SynthesisContext,
        )

        selector = PremiumModelSelector(config=mock_config)
        context = SynthesisContext(total_tokens=8001)

        selection = selector.select(context)

        assert selection.model == "claude-3-5-sonnet-20241022"

    def test_fallback_when_primary_unavailable(self, mock_config):
        """Test fallback to Claude when OpenAI is unavailable."""
        from app.services.premium_model_selector import (
            PremiumModelSelector,
            SynthesisContext,
        )

        selector = PremiumModelSelector(config=mock_config)
        # Mark OpenAI as unavailable
        selector._provider_health["openai"] = False

        context = SynthesisContext(total_tokens=5000)
        selection = selector.select(context)

        assert selection.model == "claude-3-5-sonnet-20241022"
        assert selection.provider == "anthropic"
        assert selection.is_fallback is True

    def test_fallback_when_claude_unavailable_for_long_context(self, mock_config):
        """Test fallback to GPT-4o when Claude is unavailable for long context."""
        from app.services.premium_model_selector import (
            PremiumModelSelector,
            SynthesisContext,
        )

        selector = PremiumModelSelector(config=mock_config)
        # Mark Anthropic as unavailable
        selector._provider_health["anthropic"] = False

        context = SynthesisContext(total_tokens=10000)  # Would normally use Claude
        selection = selector.select(context)

        assert selection.model == "gpt-4o"
        assert selection.provider == "openai"
        assert selection.is_fallback is True

    def test_degraded_flag_when_both_unavailable(self, mock_config):
        """Test degraded flag when both providers are unavailable."""
        from app.services.premium_model_selector import (
            PremiumModelSelector,
            SynthesisContext,
        )

        selector = PremiumModelSelector(config=mock_config)
        # Mark both providers as unavailable
        selector._provider_health["openai"] = False
        selector._provider_health["anthropic"] = False

        context = SynthesisContext(total_tokens=5000)
        selection = selector.select(context)

        assert selection.is_degraded is True
        # Should still return a selection (best effort)
        assert selection.model is not None

    def test_is_available_returns_health_status(self, mock_config):
        """Test is_available returns correct health status."""
        from app.services.premium_model_selector import PremiumModelSelector

        selector = PremiumModelSelector(config=mock_config)

        assert selector.is_available("openai") is True
        assert selector.is_available("anthropic") is True

        selector._provider_health["openai"] = False
        assert selector.is_available("openai") is False

    def test_get_fallback_returns_alternate_model(self, mock_config):
        """Test get_fallback returns the alternate provider's model."""
        from app.services.premium_model_selector import PremiumModelSelector

        selector = PremiumModelSelector(config=mock_config)

        fallback = selector.get_fallback("gpt-4o")
        assert fallback == "claude-3-5-sonnet-20241022"

        fallback = selector.get_fallback("claude-3-5-sonnet-20241022")
        assert fallback == "gpt-4o"

    def test_selection_under_10ms(self, mock_config):
        """Test that model selection decision takes <10ms."""
        from app.services.premium_model_selector import (
            PremiumModelSelector,
            SynthesisContext,
        )

        selector = PremiumModelSelector(config=mock_config)
        context = SynthesisContext(total_tokens=5000)

        # Run selection multiple times and measure
        times = []
        for _ in range(100):
            start = time.perf_counter()
            selector.select(context)
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        max_time = max(times)

        assert avg_time < 10, f"Average selection time {avg_time:.2f}ms exceeds 10ms"
        assert max_time < 50, f"Max selection time {max_time:.2f}ms exceeds 50ms"


class TestPremiumModelSelectorAsync:
    """Async tests for PremiumModelSelector."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LLMModelConfig."""
        config = MagicMock(spec=LLMModelConfig)
        config.get_model.return_value = "gpt-4o"
        config.get_provider.return_value = "openai"
        config.get_fallback.return_value = {
            "model": "claude-3-5-sonnet-20241022",
            "provider": "anthropic",
        }
        return config

    @pytest.mark.asyncio
    async def test_pre_warm_validates_both_providers(self, mock_config):
        """Test that pre_warm validates both OpenAI and Anthropic."""
        from app.services.premium_model_selector import PremiumModelSelector

        selector = PremiumModelSelector(config=mock_config)

        # Mock provider validation
        with patch.object(selector, "_validate_provider", new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = True

            result = await selector.pre_warm()

            assert "openai" in result
            assert "anthropic" in result
            assert result["openai"] is True
            assert result["anthropic"] is True
            assert mock_validate.call_count == 2

    @pytest.mark.asyncio
    async def test_pre_warm_marks_unhealthy_on_failure(self, mock_config):
        """Test that pre_warm marks provider as unhealthy on validation failure."""
        from app.services.premium_model_selector import PremiumModelSelector

        selector = PremiumModelSelector(config=mock_config)

        # Mock provider validation - OpenAI fails, Anthropic succeeds
        async def mock_validate(provider: str) -> bool:
            return provider != "openai"

        with patch.object(selector, "_validate_provider", side_effect=mock_validate):
            result = await selector.pre_warm()

            assert result["openai"] is False
            assert result["anthropic"] is True
            assert selector.is_available("openai") is False
            assert selector.is_available("anthropic") is True

    @pytest.mark.asyncio
    async def test_pre_warm_completes_under_3_seconds(self, mock_config):
        """Test that pre_warm completes in <3 seconds."""
        from app.services.premium_model_selector import PremiumModelSelector

        selector = PremiumModelSelector(config=mock_config)

        # Mock fast validation
        async def fast_validate(provider: str) -> bool:
            await asyncio.sleep(0.1)  # Simulate 100ms API call
            return True

        with patch.object(selector, "_validate_provider", side_effect=fast_validate):
            start = time.perf_counter()
            await selector.pre_warm()
            elapsed = time.perf_counter() - start

            assert elapsed < 3.0, f"Pre-warm took {elapsed:.2f}s, expected <3s"

    @pytest.mark.asyncio
    async def test_pre_warm_handles_timeout(self, mock_config):
        """Test that pre_warm handles provider timeout gracefully."""
        from app.services.premium_model_selector import PremiumModelSelector

        selector = PremiumModelSelector(config=mock_config)

        # Mock slow validation that times out
        async def slow_validate(provider: str) -> bool:
            await asyncio.sleep(10)  # Would timeout
            return True

        with (
            patch.object(selector, "_validate_provider", side_effect=slow_validate),
            patch.object(selector, "_pre_warm_timeout", 0.5),
        ):
            result = await selector.pre_warm()

            # Both should be marked as failed due to timeout
            assert result["openai"] is False
            assert result["anthropic"] is False


class TestPremiumModelSelectorWithRealConfig:
    """Integration tests with real LLMModelConfig."""

    @pytest.fixture
    def real_config(self, tmp_path):
        """Create a real LLMModelConfig with test file."""
        import yaml  # type: ignore[import-untyped]

        config_file = tmp_path / "llm_models.yaml"
        config_data = {
            "version": "1.0",
            "tiers": {
                "premium": {
                    "provider": "openai",
                    "model": "gpt-4o",
                    "fallback": {
                        "provider": "anthropic",
                        "model": "claude-3-5-sonnet-20241022",
                    },
                },
            },
            "known_models": {
                "openai": ["gpt-4o", "gpt-4o-mini"],
                "anthropic": ["claude-3-5-sonnet-20241022"],
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = LLMModelConfig(config_path=config_file)
        config.load()
        return config

    def test_selector_with_real_config(self, real_config):
        """Test selector works with real LLMModelConfig."""
        from app.services.premium_model_selector import (
            PremiumModelSelector,
            SynthesisContext,
        )

        selector = PremiumModelSelector(config=real_config)
        context = SynthesisContext(total_tokens=5000)

        selection = selector.select(context)

        assert selection.model == "gpt-4o"
        assert selection.provider == "openai"
