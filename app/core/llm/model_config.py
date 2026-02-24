"""LLM Model Configuration System for DEV-184.

DEV-257: Thin wrapper over ModelRegistry for backward compatibility.
All tier resolution now delegates to the centralized registry.

Usage:
    from app.core.llm.model_config import get_model_config, ModelTier

    config = get_model_config()
    model = config.get_model(ModelTier.PREMIUM)
    timeout = config.get_timeout(ModelTier.BASIC)
"""

import os
from enum import Enum
from pathlib import Path
from typing import Any

from app.core.logging import logger


class ModelTier(str, Enum):
    """Model tiers for LLM selection.

    BASIC: For routing, query expansion, HyDE (cost-optimized)
    PREMIUM: For critical synthesis (quality-optimized)
    """

    BASIC = "basic"
    PREMIUM = "premium"


class LLMModelConfig:
    """Backward-compatible wrapper over ModelRegistry.

    Delegates all tier resolution to the centralized registry (DEV-257).
    """

    def __init__(self, config_path: Path | None = None):
        self._config_path = config_path
        self._is_loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    def load(self) -> None:
        """Load configuration (triggers registry load)."""
        from app.core.llm.model_registry import get_model_registry

        # Ensure registry is loaded (singleton auto-loads)
        get_model_registry()
        self._is_loaded = True
        logger.info("llm_model_config_loaded_via_registry")

    def reload(self) -> None:
        self._is_loaded = False
        from app.core.llm.model_registry import reset_model_registry

        reset_model_registry()
        self.load()

    def _get_tier(self, tier: ModelTier | str) -> dict[str, Any]:
        if not self._is_loaded:
            self.load()
        from app.core.llm.model_registry import get_model_registry

        tier_key = tier.value if isinstance(tier, ModelTier) else tier
        return get_model_registry().get_pipeline_tier_config(tier_key)

    def get_model(self, tier: ModelTier | str) -> str:
        return self._get_tier(tier)["model_name"]

    def get_provider(self, tier: ModelTier | str) -> str:
        return self._get_tier(tier)["provider"]

    def get_timeout(self, tier: ModelTier | str) -> int:
        return self._get_tier(tier)["timeout_ms"]

    def get_temperature(self, tier: ModelTier | str) -> float:
        return self._get_tier(tier)["temperature"]

    def get_max_tokens(self, tier: ModelTier | str) -> int:
        return self._get_tier(tier)["max_tokens"]

    def get_fallback(self, tier: ModelTier | str) -> dict[str, Any] | None:
        fb = self._get_tier(tier).get("fallback")
        if fb is None:
            return None
        # Return in legacy format: {provider, model, timeout_ms}
        return {
            "provider": fb["provider"],
            "model": fb["model_name"],
            "timeout_ms": fb.get("timeout_ms", 90000),
        }

    def get_tier_config(self, tier: ModelTier | str) -> dict[str, Any]:
        """Get full tier config in legacy format."""
        tc = self._get_tier(tier)
        result = {
            "provider": tc["provider"],
            "model": tc["model_name"],
            "timeout_ms": tc["timeout_ms"],
            "temperature": tc["temperature"],
            "max_tokens": tc["max_tokens"],
        }
        fb = tc.get("fallback")
        if fb:
            result["fallback"] = {
                "provider": fb["provider"],
                "model": fb["model_name"],
                "timeout_ms": fb.get("timeout_ms", 90000),
            }
        return result


def resolve_model_from_env(
    env_var: str,
    config: LLMModelConfig,
    fallback_tier: ModelTier = ModelTier.BASIC,
) -> tuple[str, str]:
    """Resolve (provider, model_name) from a per-step env var.

    Checks env var first, falls back to tier config.
    Supports provider:model format, bare model names, and aliases.
    """
    from app.core.remote_config import get_config

    value = get_config(env_var, "")
    if value:
        from app.core.llm.model_registry import get_model_registry

        entry = get_model_registry().resolve(value)
        return entry.provider, entry.model_name
    return config.get_provider(fallback_tier), config.get_model(fallback_tier)


# Singleton instance
_config_instance: LLMModelConfig | None = None


def get_model_config() -> LLMModelConfig:
    """Get the singleton LLMModelConfig instance.

    Returns:
        LLMModelConfig instance (loaded)
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = LLMModelConfig()
        _config_instance.load()
    return _config_instance


def reset_model_config() -> None:
    """Reset the singleton instance (for testing)."""
    global _config_instance
    _config_instance = None
