"""Tests for the centralized LLM Model Registry (DEV-257).

TDD RED phase: These tests define the expected behavior of ModelRegistry
before implementation.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml  # type: ignore[import-untyped]

from app.core.llm.base import LLMCostInfo, LLMModelTier

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_yaml(path: Path, data: dict) -> Path:
    """Write a dict as YAML to the given path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
    return path


def _minimal_yaml() -> dict:
    """Return a minimal but valid v2.0 YAML config."""
    return {
        "version": "2.0",
        "models": {
            "openai:gpt-4o": {
                "provider": "openai",
                "display_name": "GPT-4o",
                "tier": "advanced",
                "status": "active",
                "context_window": 128000,
                "costs": {
                    "input_per_1k_tokens": 0.005,
                    "output_per_1k_tokens": 0.015,
                },
                "capabilities": {
                    "supports_tools": True,
                    "supports_streaming": True,
                },
            },
            "openai:gpt-4o-mini": {
                "provider": "openai",
                "display_name": "GPT-4o Mini",
                "tier": "basic",
                "status": "active",
                "context_window": 128000,
                "costs": {
                    "input_per_1k_tokens": 0.00015,
                    "output_per_1k_tokens": 0.0006,
                },
                "capabilities": {
                    "supports_tools": True,
                    "supports_streaming": True,
                },
            },
            "anthropic:claude-3-5-sonnet-20241022": {
                "provider": "anthropic",
                "display_name": "Claude 3.5 Sonnet",
                "tier": "advanced",
                "status": "active",
                "context_window": 200000,
                "costs": {
                    "input_per_1k_tokens": 0.003,
                    "output_per_1k_tokens": 0.015,
                },
                "capabilities": {
                    "supports_tools": True,
                    "supports_streaming": True,
                },
            },
            "gemini:gemini-2.5-flash": {
                "provider": "gemini",
                "display_name": "Gemini 2.5 Flash",
                "tier": "basic",
                "status": "disabled",
                "context_window": 1048576,
                "costs": {
                    "input_per_1k_tokens": 0.000075,
                    "output_per_1k_tokens": 0.0003,
                },
                "capabilities": {
                    "supports_tools": True,
                    "supports_streaming": True,
                },
            },
            "mistral:mistral-large-latest": {
                "provider": "mistral",
                "display_name": "Mistral Large",
                "tier": "advanced",
                "status": "active",
                "context_window": 128000,
                "costs": {
                    "input_per_1k_tokens": 0.003,
                    "output_per_1k_tokens": 0.009,
                },
                "capabilities": {
                    "supports_tools": True,
                    "supports_streaming": True,
                },
            },
        },
        "aliases": {
            "production-chat": "mistral:mistral-large-latest",
            "basic-routing": "openai:gpt-4o-mini",
            "premium-synthesis": "openai:gpt-4o",
        },
        "pipeline_tiers": {
            "basic": {
                "alias": "basic-routing",
                "timeout_ms": 30000,
                "temperature": 0.3,
                "max_tokens": 2000,
            },
            "premium": {
                "alias": "premium-synthesis",
                "timeout_ms": 60000,
                "temperature": 0.2,
                "max_tokens": 4000,
                "fallback": {
                    "alias": "anthropic:claude-3-5-sonnet-20241022",
                    "timeout_ms": 90000,
                },
            },
        },
        "provider_settings": {
            "best_models": {
                "openai": "openai:gpt-4o",
                "anthropic": "anthropic:claude-3-5-sonnet-20241022",
                "mistral": "mistral:mistral-large-latest",
            },
            "disabled_providers": ["gemini"],
        },
        "defaults": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "timeout_ms": 30000,
            "temperature": 0.3,
            "max_tokens": 2000,
        },
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_registry():
    """Reset the singleton registry before each test."""
    from app.core.llm.model_registry import reset_model_registry

    reset_model_registry()
    yield
    reset_model_registry()


@pytest.fixture
def config_dir(tmp_path):
    """Temporary config directory."""
    d = tmp_path / "config"
    d.mkdir()
    return d


@pytest.fixture
def config_file(config_dir):
    """Write a minimal v2.0 YAML and return path."""
    return _write_yaml(config_dir / "llm_models.yaml", _minimal_yaml())


@pytest.fixture
def registry(config_file):
    """Return a loaded ModelRegistry from minimal YAML."""
    from app.core.llm.model_registry import ModelRegistry

    reg = ModelRegistry(config_path=config_file)
    reg.load()
    return reg


# ===========================================================================
# TestModelEntry
# ===========================================================================


class TestModelEntry:
    """Tests for the ModelEntry dataclass."""

    def test_is_active_returns_true_for_active_model(self, registry):
        from app.core.llm.model_registry import ModelEntry

        entry = registry.get("openai:gpt-4o")
        assert isinstance(entry, ModelEntry)
        assert entry.is_active is True

    def test_is_active_returns_false_for_disabled_model(self, registry):
        entry = registry.get("gemini:gemini-2.5-flash")
        assert entry.is_active is False

    def test_is_disabled_returns_true_for_disabled_status(self, registry):
        entry = registry.get("gemini:gemini-2.5-flash")
        assert entry.is_disabled is True

    def test_to_cost_info_returns_llm_cost_info(self, registry):
        entry = registry.get("openai:gpt-4o")
        cost_info = entry.to_cost_info()

        assert isinstance(cost_info, LLMCostInfo)
        assert cost_info.model_name == "gpt-4o"
        assert cost_info.input_cost_per_1k_tokens == 0.005
        assert cost_info.output_cost_per_1k_tokens == 0.015
        assert cost_info.tier == LLMModelTier.ADVANCED

    def test_model_name_extracts_name_from_model_id(self, registry):
        entry = registry.get("openai:gpt-4o-mini")
        assert entry.model_name == "gpt-4o-mini"

    def test_provider_extracted_from_model_id(self, registry):
        entry = registry.get("anthropic:claude-3-5-sonnet-20241022")
        assert entry.provider == "anthropic"


# ===========================================================================
# TestModelNotFoundError
# ===========================================================================


class TestModelNotFoundError:
    """Tests for ModelNotFoundError."""

    def test_error_message_lists_available_models(self, registry):
        from app.core.llm.model_registry import ModelNotFoundError

        with pytest.raises(ModelNotFoundError) as exc_info:
            registry.resolve("nonexistent:model")

        error_msg = str(exc_info.value)
        assert "nonexistent:model" in error_msg
        assert "openai:gpt-4o" in error_msg

    def test_error_message_lists_aliases(self, registry):
        from app.core.llm.model_registry import ModelNotFoundError

        with pytest.raises(ModelNotFoundError) as exc_info:
            registry.resolve("bad-alias")

        error_msg = str(exc_info.value)
        assert "production-chat" in error_msg

    def test_is_subclass_of_value_error(self):
        from app.core.llm.model_registry import ModelNotFoundError

        assert issubclass(ModelNotFoundError, ValueError)


# ===========================================================================
# TestModelRegistryLoad
# ===========================================================================


class TestModelRegistryLoad:
    """Tests for ModelRegistry.load()."""

    def test_load_from_yaml(self, config_file):
        from app.core.llm.model_registry import ModelRegistry

        reg = ModelRegistry(config_path=config_file)
        reg.load()
        assert reg.is_loaded is True

    def test_load_counts_models(self, registry):
        assert len(registry.all_models) == 5

    def test_load_with_missing_file_uses_defaults(self, tmp_path):
        from app.core.llm.model_registry import ModelRegistry

        reg = ModelRegistry(config_path=tmp_path / "nonexistent.yaml")
        reg.load()
        assert reg.is_loaded is True
        # Should have hardcoded fallback models
        assert len(reg.all_models) > 0

    def test_load_with_invalid_yaml_uses_defaults(self, config_dir):
        bad_yaml = config_dir / "llm_models.yaml"
        bad_yaml.write_text("{{invalid yaml: [")

        from app.core.llm.model_registry import ModelRegistry

        reg = ModelRegistry(config_path=bad_yaml)
        reg.load()
        assert reg.is_loaded is True

    def test_load_aliases(self, registry):
        assert "production-chat" in registry.aliases
        assert registry.aliases["production-chat"] == "mistral:mistral-large-latest"


# ===========================================================================
# TestResolve
# ===========================================================================


class TestResolve:
    """Tests for ModelRegistry.resolve()."""

    def test_resolve_direct_model_id(self, registry):
        entry = registry.resolve("openai:gpt-4o")
        assert entry.model_id == "openai:gpt-4o"

    def test_resolve_alias(self, registry):
        entry = registry.resolve("production-chat")
        assert entry.model_id == "mistral:mistral-large-latest"

    def test_resolve_bare_model_name(self, registry):
        """Bare model name (e.g., 'gpt-4o') should resolve to fully-qualified model_id."""
        entry = registry.resolve("gpt-4o")
        assert entry.model_id == "openai:gpt-4o"

    def test_resolve_bare_model_name_anthropic(self, registry):
        """Bare Anthropic model name should resolve correctly."""
        entry = registry.resolve("claude-3-5-sonnet-20241022")
        assert entry.model_id == "anthropic:claude-3-5-sonnet-20241022"

    def test_resolve_unknown_raises_model_not_found(self, registry):
        from app.core.llm.model_registry import ModelNotFoundError

        with pytest.raises(ModelNotFoundError):
            registry.resolve("unknown:model-xyz")

    def test_resolve_alias_pointing_to_missing_model_raises(self, config_dir):
        data = _minimal_yaml()
        data["aliases"]["broken-alias"] = "openai:nonexistent-model"
        config_path = _write_yaml(config_dir / "llm_models.yaml", data)

        from app.core.llm.model_registry import ModelNotFoundError, ModelRegistry

        reg = ModelRegistry(config_path=config_path)
        reg.load()

        with pytest.raises(ModelNotFoundError):
            reg.resolve("broken-alias")


# ===========================================================================
# TestGetModelsByProvider
# ===========================================================================


class TestGetModelsByProvider:
    """Tests for get_models_by_provider()."""

    def test_returns_only_models_for_given_provider(self, registry):
        openai_models = registry.get_models_by_provider("openai")
        assert len(openai_models) == 2
        assert all(m.provider == "openai" for m in openai_models)

    def test_returns_empty_list_for_unknown_provider(self, registry):
        result = registry.get_models_by_provider("unknown")
        assert result == []

    def test_returns_all_statuses(self, registry):
        gemini_models = registry.get_models_by_provider("gemini")
        assert len(gemini_models) == 1
        assert gemini_models[0].is_disabled


# ===========================================================================
# TestGetActiveModels
# ===========================================================================


class TestGetActiveModels:
    """Tests for get_active_models()."""

    def test_excludes_disabled_models(self, registry):
        active = registry.get_active_models()
        model_ids = [m.model_id for m in active]
        assert "gemini:gemini-2.5-flash" not in model_ids

    def test_includes_all_active_models(self, registry):
        active = registry.get_active_models()
        assert len(active) == 4  # 2 openai + 1 anthropic + 1 mistral


# ===========================================================================
# TestGetDisabledProviders
# ===========================================================================


class TestGetDisabledProviders:
    """Tests for get_disabled_providers()."""

    def test_returns_disabled_providers_from_config(self, registry):
        disabled = registry.get_disabled_providers()
        assert "gemini" in disabled

    def test_returns_set(self, registry):
        disabled = registry.get_disabled_providers()
        assert isinstance(disabled, set)


# ===========================================================================
# TestGetBestModels
# ===========================================================================


class TestGetBestModels:
    """Tests for get_best_models()."""

    def test_returns_best_model_per_provider(self, registry):
        best = registry.get_best_models()
        assert best["openai"] == "openai:gpt-4o"
        assert best["mistral"] == "mistral:mistral-large-latest"

    def test_returns_dict(self, registry):
        best = registry.get_best_models()
        assert isinstance(best, dict)


# ===========================================================================
# TestGetDisplayName
# ===========================================================================


class TestGetDisplayName:
    """Tests for get_display_name()."""

    def test_returns_display_name_for_known_model(self, registry):
        name = registry.get_display_name("openai:gpt-4o")
        assert name == "GPT-4o"

    def test_returns_model_id_for_unknown_model(self, registry):
        name = registry.get_display_name("unknown:model")
        assert name == "unknown:model"

    def test_resolves_alias_then_returns_display_name(self, registry):
        name = registry.get_display_name("production-chat")
        assert name == "Mistral Large"


# ===========================================================================
# TestGetCostInfo
# ===========================================================================


class TestGetCostInfo:
    """Tests for get_cost_info()."""

    def test_returns_cost_info_for_model(self, registry):
        cost = registry.get_cost_info("openai:gpt-4o-mini")
        assert isinstance(cost, LLMCostInfo)
        assert cost.input_cost_per_1k_tokens == 0.00015
        assert cost.output_cost_per_1k_tokens == 0.0006

    def test_resolves_alias_for_cost_info(self, registry):
        cost = registry.get_cost_info("basic-routing")
        assert cost.model_name == "gpt-4o-mini"


# ===========================================================================
# TestResolveProductionModel
# ===========================================================================


class TestResolveProductionModel:
    """Tests for resolve_production_model()."""

    def test_resolves_direct_model_id(self, registry):
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.PRODUCTION_LLM_MODEL = "openai:gpt-4o"
            entry = registry.resolve_production_model()
            assert entry.model_id == "openai:gpt-4o"

    def test_resolves_alias(self, registry):
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.PRODUCTION_LLM_MODEL = "production-chat"
            entry = registry.resolve_production_model()
            assert entry.model_id == "mistral:mistral-large-latest"

    def test_invalid_model_raises(self, registry):
        from app.core.llm.model_registry import ModelNotFoundError

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.PRODUCTION_LLM_MODEL = "bad:model"
            with pytest.raises(ModelNotFoundError):
                registry.resolve_production_model()


# ===========================================================================
# TestEnvVarOverrides
# ===========================================================================


class TestEnvVarOverrides:
    """Tests for environment variable overrides on pipeline tiers."""

    _CLEAR_TIER_ENVS = {
        "LLM_MODEL_BASIC": "",
        "LLM_MODEL_PREMIUM": "",
    }

    @patch.dict(os.environ, {"LLM_MODEL_BASIC": "openai:gpt-4o", "LLM_MODEL_PREMIUM": ""})
    def test_basic_tier_override(self, registry):
        tier_config = registry.get_pipeline_tier_config("basic")
        assert tier_config["model_id"] == "openai:gpt-4o"

    @patch.dict(os.environ, {"LLM_MODEL_PREMIUM": "anthropic:claude-3-5-sonnet-20241022", "LLM_MODEL_BASIC": ""})
    def test_premium_tier_override(self, registry):
        tier_config = registry.get_pipeline_tier_config("premium")
        assert tier_config["model_id"] == "anthropic:claude-3-5-sonnet-20241022"

    @patch.dict(os.environ, _CLEAR_TIER_ENVS)
    def test_default_basic_tier_from_yaml(self, registry):
        tier_config = registry.get_pipeline_tier_config("basic")
        # basic-routing alias -> openai:gpt-4o-mini
        assert tier_config["model_id"] == "openai:gpt-4o-mini"
        assert tier_config["timeout_ms"] == 30000
        assert tier_config["temperature"] == 0.3

    @patch.dict(os.environ, _CLEAR_TIER_ENVS)
    def test_default_premium_tier_from_yaml(self, registry):
        tier_config = registry.get_pipeline_tier_config("premium")
        # premium-synthesis alias -> openai:gpt-4o
        assert tier_config["model_id"] == "openai:gpt-4o"
        assert tier_config["timeout_ms"] == 60000

    @patch.dict(os.environ, _CLEAR_TIER_ENVS)
    def test_pipeline_tier_fallback(self, registry):
        tier_config = registry.get_pipeline_tier_config("premium")
        assert tier_config["fallback"] is not None
        assert tier_config["fallback"]["model_id"] == "anthropic:claude-3-5-sonnet-20241022"


# ===========================================================================
# TestValidateStartup
# ===========================================================================


class TestValidateStartup:
    """Tests for validate_startup()."""

    def test_valid_config_passes(self, registry):
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.PRODUCTION_LLM_MODEL = "openai:gpt-4o"
            registry.validate_startup()

    def test_alias_passes(self, registry):
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.PRODUCTION_LLM_MODEL = "production-chat"
            registry.validate_startup()

    def test_invalid_production_model_raises(self, registry):
        from app.core.llm.model_registry import ModelNotFoundError

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.PRODUCTION_LLM_MODEL = "bad:nonexistent"
            with pytest.raises(ModelNotFoundError):
                registry.validate_startup()


# ===========================================================================
# TestSingleton
# ===========================================================================


class TestSingleton:
    """Tests for get_model_registry() / reset_model_registry()."""

    def test_get_model_registry_returns_same_instance(self):
        from app.core.llm.model_registry import get_model_registry

        reg1 = get_model_registry()
        reg2 = get_model_registry()
        assert reg1 is reg2

    def test_reset_clears_singleton(self):
        from app.core.llm.model_registry import (
            get_model_registry,
            reset_model_registry,
        )

        reg1 = get_model_registry()
        reset_model_registry()
        reg2 = get_model_registry()
        assert reg1 is not reg2

    def test_get_model_registry_auto_loads(self):
        from app.core.llm.model_registry import get_model_registry

        reg = get_model_registry()
        assert reg.is_loaded is True


# ===========================================================================
# TestGetModelListForProvider
# ===========================================================================


class TestGetModelListForProvider:
    """Tests for get_model_list_for_provider()."""

    def test_returns_list_of_model_names(self, registry):
        models = registry.get_model_list_for_provider("openai")
        assert "gpt-4o" in models
        assert "gpt-4o-mini" in models

    def test_includes_only_active_models(self, registry):
        models = registry.get_model_list_for_provider("gemini")
        # gemini is disabled, so no active models
        assert models == []
