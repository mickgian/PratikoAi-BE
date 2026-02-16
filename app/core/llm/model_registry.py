"""Centralized LLM Model Registry (DEV-257).

Single source of truth for all LLM model metadata, replacing
duplicated model lists across factory, providers, comparison service,
and orchestrator.

Usage:
    from app.core.llm.model_registry import get_model_registry

    registry = get_model_registry()
    entry = registry.resolve("production-chat")  # alias -> ModelEntry
    cost = registry.get_cost_info("openai:gpt-4o")  # -> LLMCostInfo
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from app.core.llm.base import LLMCostInfo, LLMModelTier
from app.core.logging import logger

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelEntry:
    """Metadata for a single LLM model from the registry YAML."""

    model_id: str  # e.g. "openai:gpt-4o"
    provider: str
    model_name: str  # bare name, e.g. "gpt-4o"
    display_name: str
    tier: LLMModelTier
    status: str  # "active" | "deprecated" | "disabled"
    context_window: int
    input_cost_per_1k: float
    output_cost_per_1k: float
    capabilities: dict = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        return self.status == "active"

    @property
    def is_disabled(self) -> bool:
        return self.status == "disabled"

    def to_cost_info(self) -> LLMCostInfo:
        """Convert to LLMCostInfo for backward compatibility with providers."""
        return LLMCostInfo(
            input_cost_per_1k_tokens=self.input_cost_per_1k,
            output_cost_per_1k_tokens=self.output_cost_per_1k,
            model_name=self.model_name,
            tier=self.tier,
        )


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ModelNotFoundError(ValueError):
    """Raised when a model_id or alias cannot be resolved."""

    def __init__(self, key: str, available_models: list[str], available_aliases: list[str]):
        models_str = ", ".join(sorted(available_models)[:10])
        aliases_str = ", ".join(sorted(available_aliases))
        super().__init__(
            f"Model '{key}' not found. Available models: [{models_str}]. Available aliases: [{aliases_str}]."
        )


# ---------------------------------------------------------------------------
# Tier name -> LLMModelTier mapping
# ---------------------------------------------------------------------------

_TIER_MAP: dict[str, LLMModelTier] = {
    "basic": LLMModelTier.BASIC,
    "standard": LLMModelTier.STANDARD,
    "advanced": LLMModelTier.ADVANCED,
    "premium": LLMModelTier.PREMIUM,
}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class ModelRegistry:
    """Loads the YAML model catalog and provides lookup / resolution."""

    def __init__(self, config_path: Path | None = None):
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / "config" / "llm_models.yaml"

        self._config_path = config_path
        self._models: dict[str, ModelEntry] = {}
        self._aliases: dict[str, str] = {}
        self._pipeline_tiers: dict[str, dict[str, Any]] = {}
        self._provider_settings: dict[str, Any] = {}
        self._defaults: dict[str, Any] = {}
        self._is_loaded = False

    # -- public properties --------------------------------------------------

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    @property
    def all_models(self) -> list[ModelEntry]:
        return list(self._models.values())

    @property
    def aliases(self) -> dict[str, str]:
        return dict(self._aliases)

    # -- loading ------------------------------------------------------------

    def load(self) -> None:
        """Load model catalog from YAML with fallback to hardcoded defaults."""
        raw: dict[str, Any] = {}

        if self._config_path.exists():
            try:
                with open(self._config_path) as f:
                    raw = yaml.safe_load(f) or {}
                logger.info("model_registry_loaded_yaml", config_path=str(self._config_path))
            except yaml.YAMLError as e:
                logger.warning("model_registry_yaml_error", error=str(e))
                raw = {}
        else:
            logger.info("model_registry_yaml_not_found", config_path=str(self._config_path))

        # If YAML is missing or has no models section, use hardcoded defaults
        if not raw.get("models"):
            raw = _get_default_catalog()

        self._parse_models(raw.get("models", {}))
        self._aliases = raw.get("aliases", {})
        self._pipeline_tiers = raw.get("pipeline_tiers", {})
        self._provider_settings = raw.get("provider_settings", {})
        self._defaults = raw.get("defaults", {})
        self._is_loaded = True

    # -- resolution ---------------------------------------------------------

    def get(self, model_id: str) -> ModelEntry | None:
        """Get a ModelEntry by exact model_id, or None."""
        return self._models.get(model_id)

    def resolve(self, key: str) -> ModelEntry:
        """Resolve a model_id or alias to a ModelEntry.

        Raises ModelNotFoundError if not found.
        """
        # Try direct model_id first (e.g., "openai:gpt-4o")
        entry = self._models.get(key)
        if entry:
            return entry

        # Try alias (e.g., "production-chat")
        target = self._aliases.get(key)
        if target:
            entry = self._models.get(target)
            if entry:
                return entry
            # Alias points to missing model
            raise ModelNotFoundError(
                key=f"{key} (alias -> {target})",
                available_models=list(self._models.keys()),
                available_aliases=list(self._aliases.keys()),
            )

        # Try bare model name (e.g., "gpt-4o-mini" -> "openai:gpt-4o-mini")
        # This supports env vars like LLM_MODEL_BASIC=gpt-4o-mini
        for model_id, model_entry in self._models.items():
            if model_entry.model_name == key:
                return model_entry

        raise ModelNotFoundError(
            key=key,
            available_models=list(self._models.keys()),
            available_aliases=list(self._aliases.keys()),
        )

    def resolve_production_model(self) -> ModelEntry:
        """Resolve PRODUCTION_LLM_MODEL env var to a ModelEntry."""
        from app.core.config import settings

        return self.resolve(settings.PRODUCTION_LLM_MODEL)

    # -- query helpers ------------------------------------------------------

    def get_models_by_provider(self, provider: str) -> list[ModelEntry]:
        """Return all models (any status) for a given provider."""
        return [m for m in self._models.values() if m.provider == provider]

    def get_active_models(self) -> list[ModelEntry]:
        """Return only active (non-disabled, non-deprecated) models."""
        return [m for m in self._models.values() if m.is_active]

    def get_disabled_providers(self) -> set[str]:
        """Return set of globally disabled provider names."""
        return set(self._provider_settings.get("disabled_providers", []))

    def get_best_models(self) -> dict[str, str]:
        """Return {provider: model_id} for comparison best models."""
        return dict(self._provider_settings.get("best_models", {}))

    def get_display_name(self, key: str) -> str:
        """Get display name for a model_id or alias. Falls back to key itself."""
        try:
            entry = self.resolve(key)
            return entry.display_name
        except ModelNotFoundError:
            return key

    def get_cost_info(self, key: str) -> LLMCostInfo:
        """Resolve key and return LLMCostInfo."""
        return self.resolve(key).to_cost_info()

    def get_model_list_for_provider(self, provider: str) -> list[str]:
        """Return list of *active* model names (bare, no provider prefix) for a provider."""
        return [m.model_name for m in self.get_models_by_provider(provider) if m.is_active]

    # -- pipeline tier helpers (used by LLMModelConfig wrapper) -------------

    def get_pipeline_tier_config(self, tier: str) -> dict[str, Any]:
        """Get resolved pipeline tier config.

        Returns dict with keys: model_id, provider, model_name,
        timeout_ms, temperature, max_tokens, fallback (optional).
        Env vars LLM_MODEL_BASIC / LLM_MODEL_PREMIUM take precedence.
        """
        tier_data = self._pipeline_tiers.get(tier, {})

        # Check env override first
        env_key = f"LLM_MODEL_{tier.upper()}"
        env_override = os.environ.get(env_key)

        if env_override:
            entry = self.resolve(env_override)
            model_id = entry.model_id
        else:
            alias = tier_data.get("alias", "")
            entry = self.resolve(alias) if alias else None  # type: ignore[assignment]
            model_id = (
                entry.model_id
                if entry
                else f"{self._defaults.get('provider', 'openai')}:{self._defaults.get('model', 'gpt-4o-mini')}"
            )

        provider, model_name = model_id.split(":", 1)

        result: dict[str, Any] = {
            "model_id": model_id,
            "provider": provider,
            "model_name": model_name,
            "timeout_ms": tier_data.get("timeout_ms", self._defaults.get("timeout_ms", 30000)),
            "temperature": tier_data.get("temperature", self._defaults.get("temperature", 0.3)),
            "max_tokens": tier_data.get("max_tokens", self._defaults.get("max_tokens", 2000)),
        }

        # Resolve fallback if present
        fallback_data = tier_data.get("fallback")
        if fallback_data:
            fb_alias = fallback_data.get("alias", "")
            fb_entry = self.resolve(fb_alias) if fb_alias else None
            if fb_entry:
                result["fallback"] = {
                    "model_id": fb_entry.model_id,
                    "provider": fb_entry.provider,
                    "model_name": fb_entry.model_name,
                    "timeout_ms": fallback_data.get("timeout_ms", 90000),
                }
            else:
                result["fallback"] = None
        else:
            result["fallback"] = None

        return result

    # -- startup validation -------------------------------------------------

    def validate_startup(self) -> None:
        """Validate that PRODUCTION_LLM_MODEL is resolvable.

        Logs available models and aliases at INFO level.
        Raises ModelNotFoundError if the production model is invalid.
        """
        logger.info(
            "model_registry_available_models",
            model_count=len(self._models),
            models=list(self._models.keys()),
            aliases=list(self._aliases.keys()),
        )

        # This will raise ModelNotFoundError if invalid
        entry = self.resolve_production_model()
        logger.info(
            "model_registry_production_model",
            model_id=entry.model_id,
            display_name=entry.display_name,
            provider=entry.provider,
        )

    # -- internal -----------------------------------------------------------

    def _parse_models(self, models_dict: dict[str, Any]) -> None:
        """Parse the 'models' section of YAML into ModelEntry objects."""
        self._models = {}
        for model_id, data in models_dict.items():
            if ":" not in model_id:
                logger.warning("model_registry_invalid_model_id", model_id=model_id)
                continue

            provider, model_name = model_id.split(":", 1)
            costs = data.get("costs", {})
            tier_str = data.get("tier", "basic")

            self._models[model_id] = ModelEntry(
                model_id=model_id,
                provider=provider,
                model_name=model_name,
                display_name=data.get("display_name", model_id),
                tier=_TIER_MAP.get(tier_str, LLMModelTier.BASIC),
                status=data.get("status", "active"),
                context_window=data.get("context_window", 0),
                input_cost_per_1k=costs.get("input_per_1k_tokens", 0.0),
                output_cost_per_1k=costs.get("output_per_1k_tokens", 0.0),
                capabilities=data.get("capabilities", {}),
            )


# ---------------------------------------------------------------------------
# Hardcoded default catalog (fallback when YAML is missing)
# ---------------------------------------------------------------------------


def _get_default_catalog() -> dict[str, Any]:
    """Minimal hardcoded catalog used when YAML is unavailable."""
    return {
        "version": "2.0",
        "models": {
            "openai:gpt-4o-mini": {
                "provider": "openai",
                "display_name": "GPT-4o Mini",
                "tier": "basic",
                "status": "active",
                "context_window": 128000,
                "costs": {"input_per_1k_tokens": 0.00015, "output_per_1k_tokens": 0.0006},
            },
            "openai:gpt-4o": {
                "provider": "openai",
                "display_name": "GPT-4o",
                "tier": "advanced",
                "status": "active",
                "context_window": 128000,
                "costs": {"input_per_1k_tokens": 0.005, "output_per_1k_tokens": 0.015},
            },
        },
        "aliases": {
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
            },
        },
        "provider_settings": {
            "best_models": {"openai": "openai:gpt-4o"},
            "disabled_providers": [],
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
# Singleton
# ---------------------------------------------------------------------------

_registry_instance: ModelRegistry | None = None


def get_model_registry() -> ModelRegistry:
    """Get the singleton ModelRegistry (auto-loads on first access)."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ModelRegistry()
        _registry_instance.load()
    return _registry_instance


def reset_model_registry() -> None:
    """Reset the singleton (for testing)."""
    global _registry_instance
    _registry_instance = None
