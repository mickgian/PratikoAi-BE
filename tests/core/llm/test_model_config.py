"""Tests for DEV-184: LLM Model Configuration System.

DEV-257: Updated to test the thin wrapper over ModelRegistry.
The wrapper preserves the public API but delegates to the registry.
"""

import os
from unittest.mock import patch

import pytest

from app.core.llm.model_config import LLMModelConfig, ModelTier


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset singletons before each test to prevent leakage."""
    from app.core.llm.model_config import reset_model_config
    from app.core.llm.model_registry import reset_model_registry

    reset_model_config()
    reset_model_registry()
    yield
    reset_model_config()
    reset_model_registry()


# Clear env vars that may interfere with default tier resolution
_CLEAR_ENV = {
    "LLM_MODEL_BASIC": "",
    "LLM_MODEL_PREMIUM": "",
}


class TestLLMModelConfig:
    """Tests for LLMModelConfig class (thin wrapper over ModelRegistry)."""

    @patch.dict(os.environ, _CLEAR_ENV)
    def test_load_marks_as_loaded(self):
        config = LLMModelConfig()
        assert config.is_loaded is False
        config.load()
        assert config.is_loaded is True

    @patch.dict(os.environ, _CLEAR_ENV)
    def test_get_model_for_basic_tier(self):
        config = LLMModelConfig()
        config.load()
        model = config.get_model(ModelTier.BASIC)
        # basic-routing alias -> openai:gpt-4o-mini
        assert model == "gpt-4o-mini"

    @patch.dict(os.environ, _CLEAR_ENV)
    def test_get_model_for_premium_tier(self):
        config = LLMModelConfig()
        config.load()
        model = config.get_model(ModelTier.PREMIUM)
        # premium-synthesis alias -> openai:gpt-4o
        assert model == "gpt-4o"

    @patch.dict(os.environ, _CLEAR_ENV)
    def test_get_provider_for_basic_tier(self):
        config = LLMModelConfig()
        config.load()
        assert config.get_provider(ModelTier.BASIC) == "openai"

    @patch.dict(os.environ, _CLEAR_ENV)
    def test_get_provider_for_premium_tier(self):
        config = LLMModelConfig()
        config.load()
        assert config.get_provider(ModelTier.PREMIUM) == "openai"

    @patch.dict(os.environ, _CLEAR_ENV)
    def test_get_timeout_for_tiers(self):
        config = LLMModelConfig()
        config.load()
        assert config.get_timeout(ModelTier.BASIC) == 30000
        assert config.get_timeout(ModelTier.PREMIUM) == 60000

    @patch.dict(os.environ, _CLEAR_ENV)
    def test_get_temperature_for_tiers(self):
        config = LLMModelConfig()
        config.load()
        assert config.get_temperature(ModelTier.BASIC) == 0.3
        assert config.get_temperature(ModelTier.PREMIUM) == 0.2

    @patch.dict(os.environ, _CLEAR_ENV)
    def test_get_max_tokens_for_tiers(self):
        config = LLMModelConfig()
        config.load()
        assert config.get_max_tokens(ModelTier.BASIC) == 2000
        assert config.get_max_tokens(ModelTier.PREMIUM) == 4000

    @patch.dict(os.environ, _CLEAR_ENV)
    def test_get_fallback_for_premium(self):
        config = LLMModelConfig()
        config.load()
        fallback = config.get_fallback(ModelTier.PREMIUM)
        assert fallback is not None
        assert fallback["provider"] == "anthropic"
        assert fallback["model"] == "claude-3-5-sonnet-20241022"

    @patch.dict(os.environ, _CLEAR_ENV)
    def test_no_fallback_for_basic(self):
        config = LLMModelConfig()
        config.load()
        fallback = config.get_fallback(ModelTier.BASIC)
        assert fallback is None

    @patch.dict(os.environ, _CLEAR_ENV)
    def test_get_tier_config_returns_legacy_format(self):
        config = LLMModelConfig()
        config.load()
        tc = config.get_tier_config(ModelTier.BASIC)
        assert "provider" in tc
        assert "model" in tc
        assert "timeout_ms" in tc
        assert "temperature" in tc
        assert "max_tokens" in tc

    @patch.dict(os.environ, {"LLM_MODEL_BASIC": "openai:gpt-4o", **_CLEAR_ENV, "LLM_MODEL_BASIC": "openai:gpt-4o"})
    def test_env_override_basic(self):
        config = LLMModelConfig()
        config.load()
        assert config.get_model("basic") == "gpt-4o"

    @patch.dict(os.environ, {**_CLEAR_ENV, "LLM_MODEL_PREMIUM": "anthropic:claude-3-5-sonnet-20241022"})
    def test_env_override_premium(self):
        config = LLMModelConfig()
        config.load()
        assert config.get_model("premium") == "claude-3-5-sonnet-20241022"

    @patch.dict(os.environ, _CLEAR_ENV)
    def test_auto_loads_on_first_get(self):
        config = LLMModelConfig()
        # Should auto-load when calling get_model without explicit load()
        model = config.get_model("basic")
        assert model == "gpt-4o-mini"
        assert config.is_loaded is True

    @patch.dict(os.environ, _CLEAR_ENV)
    def test_string_tier_accepted(self):
        config = LLMModelConfig()
        config.load()
        assert config.get_model("basic") == "gpt-4o-mini"
        assert config.get_model("premium") == "gpt-4o"


class TestModelTierEnum:
    """Tests for ModelTier enum."""

    def test_model_tier_values(self):
        assert ModelTier.BASIC.value == "basic"
        assert ModelTier.PREMIUM.value == "premium"

    def test_model_tier_from_string(self):
        assert ModelTier("basic") == ModelTier.BASIC
        assert ModelTier("premium") == ModelTier.PREMIUM

    def test_invalid_tier_raises_error(self):
        with pytest.raises(ValueError):
            ModelTier("invalid_tier")


class TestModelConfigSingleton:
    """Tests for singleton behavior."""

    def test_singleton_returns_same_instance(self):
        from app.core.llm.model_config import get_model_config

        config1 = get_model_config()
        config2 = get_model_config()
        assert config1 is config2

    def test_reset_clears_singleton(self):
        from app.core.llm.model_config import get_model_config, reset_model_config

        config1 = get_model_config()
        reset_model_config()
        config2 = get_model_config()
        assert config1 is not config2
