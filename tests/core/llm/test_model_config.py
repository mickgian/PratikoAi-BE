"""TDD Tests for DEV-184: LLM Model Configuration System.

Tests the YAML-based configuration for tiered LLM model selection
per Section 13.10 of PRATIKO_1.5_REFERENCE.md.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml  # type: ignore[import-untyped]


class TestLLMModelConfig:
    """Tests for LLMModelConfig class."""

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create a temporary config directory."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        return config_dir

    @pytest.fixture
    def valid_config_yaml(self):
        """Valid YAML configuration."""
        return {
            "version": "1.0",
            "tiers": {
                "basic": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "timeout_ms": 30000,
                    "temperature": 0.3,
                    "max_tokens": 2000,
                },
                "premium": {
                    "provider": "openai",
                    "model": "gpt-4o",
                    "timeout_ms": 60000,
                    "temperature": 0.2,
                    "max_tokens": 4000,
                    "fallback": {
                        "provider": "anthropic",
                        "model": "claude-3-5-sonnet-20241022",
                    },
                },
            },
            "defaults": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "timeout_ms": 30000,
                "temperature": 0.3,
                "max_tokens": 2000,
            },
        }

    @pytest.fixture
    def config_file(self, temp_config_dir, valid_config_yaml):
        """Create a valid config file."""
        config_path = temp_config_dir / "llm_models.yaml"
        with open(config_path, "w") as f:
            yaml.dump(valid_config_yaml, f)
        return config_path

    def test_load_valid_yaml_config(self, config_file):
        """Test loading a valid YAML configuration file."""
        from app.core.llm.model_config import LLMModelConfig

        config = LLMModelConfig(config_path=config_file)
        config.load()

        assert config.is_loaded
        assert config.get_model("basic") == "gpt-4o-mini"
        assert config.get_model("premium") == "gpt-4o"

    def test_fallback_to_env_vars_when_yaml_missing(self):
        """Test fallback to environment variables when YAML is missing."""
        from app.core.llm.model_config import LLMModelConfig

        with patch.dict(
            os.environ,
            {
                "LLM_MODEL": "gpt-4o-mini",
                "LLM_MODEL_PREMIUM": "gpt-4o",
            },
        ):
            config = LLMModelConfig(config_path=Path("/nonexistent/path.yaml"))
            config.load()

            # Should use env vars as fallback
            assert config.get_model("basic") == "gpt-4o-mini"
            assert config.get_model("premium") == "gpt-4o"

    def test_env_override_takes_precedence(self, config_file):
        """Test that environment variables override YAML values."""
        from app.core.llm.model_config import LLMModelConfig

        with patch.dict(
            os.environ,
            {
                "LLM_MODEL_BASIC": "gpt-4-turbo",  # Use valid model name
                "LLM_MODEL_PREMIUM": "gpt-3.5-turbo",  # Use valid model name
            },
        ):
            config = LLMModelConfig(config_path=config_file)
            config.load()

            # Env vars should take precedence
            assert config.get_model("basic") == "gpt-4-turbo"
            assert config.get_model("premium") == "gpt-3.5-turbo"

    def test_get_model_for_basic_tier(self, config_file):
        """Test getting model for BASIC tier."""
        from app.core.llm.model_config import LLMModelConfig, ModelTier

        config = LLMModelConfig(config_path=config_file)
        config.load()

        model = config.get_model(ModelTier.BASIC)
        assert model == "gpt-4o-mini"

    def test_get_model_for_premium_tier(self, config_file):
        """Test getting model for PREMIUM tier."""
        from app.core.llm.model_config import LLMModelConfig, ModelTier

        config = LLMModelConfig(config_path=config_file)
        config.load()

        model = config.get_model(ModelTier.PREMIUM)
        assert model == "gpt-4o"

    def test_invalid_yaml_uses_defaults(self, temp_config_dir):
        """Test that invalid YAML uses default configuration."""
        from app.core.llm.model_config import LLMModelConfig

        # Create invalid YAML
        config_path = temp_config_dir / "llm_models.yaml"
        with open(config_path, "w") as f:
            f.write("invalid: yaml: content: {{{{")

        config = LLMModelConfig(config_path=config_path)
        config.load()

        # Should use defaults
        assert config.get_model("basic") == "gpt-4o-mini"
        assert config.get_model("premium") == "gpt-4o"

    def test_partial_config_merges_with_defaults(self, temp_config_dir):
        """Test that partial config is merged with defaults."""
        from app.core.llm.model_config import LLMModelConfig

        # Create partial config (only premium tier)
        partial_config = {
            "version": "1.0",
            "tiers": {
                "premium": {
                    "provider": "anthropic",
                    "model": "claude-3-5-sonnet-20241022",
                },
            },
        }
        config_path = temp_config_dir / "llm_models.yaml"
        with open(config_path, "w") as f:
            yaml.dump(partial_config, f)

        config = LLMModelConfig(config_path=config_path)
        config.load()

        # Basic should use default, premium should use config
        assert config.get_model("basic") == "gpt-4o-mini"  # default
        assert config.get_model("premium") == "claude-3-5-sonnet-20241022"

    def test_get_timeout_for_tier(self, config_file):
        """Test getting timeout for a tier."""
        from app.core.llm.model_config import LLMModelConfig, ModelTier

        config = LLMModelConfig(config_path=config_file)
        config.load()

        assert config.get_timeout(ModelTier.BASIC) == 30000
        assert config.get_timeout(ModelTier.PREMIUM) == 60000

    def test_get_temperature_for_tier(self, config_file):
        """Test getting temperature for a tier."""
        from app.core.llm.model_config import LLMModelConfig, ModelTier

        config = LLMModelConfig(config_path=config_file)
        config.load()

        assert config.get_temperature(ModelTier.BASIC) == 0.3
        assert config.get_temperature(ModelTier.PREMIUM) == 0.2

    def test_get_provider_for_tier(self, config_file):
        """Test getting provider for a tier."""
        from app.core.llm.model_config import LLMModelConfig, ModelTier

        config = LLMModelConfig(config_path=config_file)
        config.load()

        assert config.get_provider(ModelTier.BASIC) == "openai"
        assert config.get_provider(ModelTier.PREMIUM) == "openai"

    def test_get_fallback_for_premium(self, config_file):
        """Test getting fallback configuration for premium tier."""
        from app.core.llm.model_config import LLMModelConfig, ModelTier

        config = LLMModelConfig(config_path=config_file)
        config.load()

        fallback = config.get_fallback(ModelTier.PREMIUM)
        assert fallback is not None
        assert fallback["provider"] == "anthropic"
        assert fallback["model"] == "claude-3-5-sonnet-20241022"

    def test_no_fallback_for_basic(self, config_file):
        """Test that basic tier has no fallback."""
        from app.core.llm.model_config import LLMModelConfig, ModelTier

        config = LLMModelConfig(config_path=config_file)
        config.load()

        fallback = config.get_fallback(ModelTier.BASIC)
        assert fallback is None

    def test_validate_against_known_models(self, temp_config_dir):
        """Test validation against known model names."""
        from app.core.llm.model_config import LLMModelConfig

        # Config with unknown model
        bad_config = {
            "version": "1.0",
            "tiers": {
                "basic": {
                    "provider": "openai",
                    "model": "unknown-model-xyz",
                },
            },
        }
        config_path = temp_config_dir / "llm_models.yaml"
        with open(config_path, "w") as f:
            yaml.dump(bad_config, f)

        config = LLMModelConfig(config_path=config_path)
        config.load()

        # Should fall back to default for unknown model
        assert config.get_model("basic") == "gpt-4o-mini"

    def test_config_cached_in_memory(self, config_file):
        """Test that config is cached after first load."""
        from app.core.llm.model_config import LLMModelConfig

        config = LLMModelConfig(config_path=config_file)
        config.load()

        # Modify the file
        with open(config_file, "w") as f:
            yaml.dump({"version": "2.0", "tiers": {}}, f)

        # Config should still return cached values
        assert config.get_model("basic") == "gpt-4o-mini"

    def test_reload_config(self, temp_config_dir):
        """Test explicit config reload."""
        from app.core.llm.model_config import LLMModelConfig

        # Clear LLM_MODEL env vars that might interfere with the test
        env_overrides = {
            "LLM_MODEL": "",
            "LLM_MODEL_BASIC": "",
            "LLM_MODEL_PREMIUM": "",
        }

        with patch.dict(os.environ, env_overrides):
            # Create initial config
            config_path = temp_config_dir / "llm_models.yaml"
            initial_config = {
                "version": "1.0",
                "tiers": {
                    "basic": {"provider": "openai", "model": "gpt-4o-mini"},
                },
                "known_models": {
                    "openai": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
                },
            }
            with open(config_path, "w") as f:
                yaml.dump(initial_config, f)

            config = LLMModelConfig(config_path=config_path)
            config.load()
            assert config.get_model("basic") == "gpt-4o-mini"

            # Modify the file with a different valid model
            new_config = {
                "version": "2.0",
                "tiers": {
                    "basic": {"provider": "openai", "model": "gpt-4-turbo"},
                },
                "known_models": {
                    "openai": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
                },
            }
            with open(config_path, "w") as f:
                yaml.dump(new_config, f)

            # Reload should pick up new values
            config.reload()
            assert config.get_model("basic") == "gpt-4-turbo"


class TestModelTierEnum:
    """Tests for ModelTier enum."""

    def test_model_tier_values(self):
        """Test ModelTier enum values."""
        from app.core.llm.model_config import ModelTier

        assert ModelTier.BASIC.value == "basic"
        assert ModelTier.PREMIUM.value == "premium"

    def test_model_tier_from_string(self):
        """Test creating ModelTier from string."""
        from app.core.llm.model_config import ModelTier

        assert ModelTier("basic") == ModelTier.BASIC
        assert ModelTier("premium") == ModelTier.PREMIUM

    def test_invalid_tier_raises_error(self):
        """Test that invalid tier string raises ValueError."""
        from app.core.llm.model_config import ModelTier

        with pytest.raises(ValueError):
            ModelTier("invalid_tier")


class TestDefaultModelConfig:
    """Tests for default configuration behavior."""

    def test_default_config_values(self):
        """Test default configuration values when no config file."""
        from app.core.llm.model_config import get_default_config

        defaults = get_default_config()

        assert "basic" in defaults["tiers"]
        assert "premium" in defaults["tiers"]
        assert defaults["tiers"]["basic"]["model"] == "gpt-4o-mini"
        assert defaults["tiers"]["premium"]["model"] == "gpt-4o"

    def test_singleton_config_instance(self):
        """Test that get_model_config returns singleton instance."""
        from app.core.llm.model_config import get_model_config

        config1 = get_model_config()
        config2 = get_model_config()

        assert config1 is config2
