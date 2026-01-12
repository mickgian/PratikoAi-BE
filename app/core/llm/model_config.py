"""LLM Model Configuration System for DEV-184.

Provides YAML-based configuration for tiered LLM model selection
per Section 13.10 of PRATIKO_1.5_REFERENCE.md.

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

import yaml  # type: ignore[import-untyped]

from app.core.logging import logger


class ModelTier(str, Enum):
    """Model tiers for LLM selection.

    BASIC: For routing, query expansion, HyDE (cost-optimized)
    PREMIUM: For critical synthesis (quality-optimized)
    """

    BASIC = "basic"
    PREMIUM = "premium"


def get_default_config() -> dict[str, Any]:
    """Get default configuration values.

    Returns:
        Default configuration dictionary
    """
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
                "max_tokens": 6000,  # DEV-242 Phase 19: Increased for detailed responses
                "fallback": {
                    "provider": "anthropic",
                    "model": "claude-3-5-sonnet-20241022",
                    "timeout_ms": 90000,
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
        "known_models": {
            "openai": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
            "anthropic": [
                "claude-3-5-sonnet-20241022",
                "claude-3-haiku-20240307",
                "claude-3-opus-20240229",
            ],
        },
    }


class LLMModelConfig:
    """LLM Model Configuration loader and manager.

    Loads configuration from YAML file with environment variable overrides.
    Implements caching and fallback behavior.
    """

    def __init__(self, config_path: Path | None = None):
        """Initialize the configuration loader.

        Args:
            config_path: Path to YAML config file. If None, uses default location.
        """
        if config_path is None:
            # Default path: config/llm_models.yaml relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / "config" / "llm_models.yaml"

        self._config_path = config_path
        self._config: dict[str, Any] = {}
        self._is_loaded = False
        self._defaults = get_default_config()

    @property
    def is_loaded(self) -> bool:
        """Check if configuration has been loaded."""
        return self._is_loaded

    def load(self) -> None:
        """Load configuration from YAML file with fallbacks.

        Loads in order of precedence:
        1. Environment variables (highest priority)
        2. YAML configuration file
        3. Default values (lowest priority)
        """
        # Start with defaults
        self._config = self._deep_copy(self._defaults)

        # Try to load from YAML file
        if self._config_path.exists():
            try:
                with open(self._config_path) as f:
                    yaml_config = yaml.safe_load(f)
                    if yaml_config:
                        self._merge_config(yaml_config)
                        logger.info(
                            "Loaded LLM config from YAML",
                            extra={"config_path": str(self._config_path)},
                        )
            except yaml.YAMLError as e:
                logger.warning(
                    "Invalid YAML in config file, using defaults",
                    extra={"error": str(e), "config_path": str(self._config_path)},
                )
        else:
            logger.info(
                "Config file not found, using defaults and env vars",
                extra={"config_path": str(self._config_path)},
            )

        # Apply environment variable overrides
        self._apply_env_overrides()

        # Validate models against known list
        self._validate_models()

        self._is_loaded = True

    def reload(self) -> None:
        """Force reload configuration from file."""
        self._is_loaded = False
        self.load()

    def get_model(self, tier: ModelTier | str) -> str:
        """Get the model name for a tier.

        Args:
            tier: Model tier (BASIC or PREMIUM)

        Returns:
            Model name string
        """
        if not self._is_loaded:
            self.load()

        tier_key = tier.value if isinstance(tier, ModelTier) else tier
        tier_config = self._config.get("tiers", {}).get(tier_key, {})
        return tier_config.get("model", self._defaults["defaults"]["model"])

    def get_provider(self, tier: ModelTier | str) -> str:
        """Get the provider for a tier.

        Args:
            tier: Model tier (BASIC or PREMIUM)

        Returns:
            Provider name string
        """
        if not self._is_loaded:
            self.load()

        tier_key = tier.value if isinstance(tier, ModelTier) else tier
        tier_config = self._config.get("tiers", {}).get(tier_key, {})
        return tier_config.get("provider", self._defaults["defaults"]["provider"])

    def get_timeout(self, tier: ModelTier | str) -> int:
        """Get the timeout in milliseconds for a tier.

        Args:
            tier: Model tier (BASIC or PREMIUM)

        Returns:
            Timeout in milliseconds
        """
        if not self._is_loaded:
            self.load()

        tier_key = tier.value if isinstance(tier, ModelTier) else tier
        tier_config = self._config.get("tiers", {}).get(tier_key, {})
        return tier_config.get("timeout_ms", self._defaults["defaults"]["timeout_ms"])

    def get_temperature(self, tier: ModelTier | str) -> float:
        """Get the temperature for a tier.

        Args:
            tier: Model tier (BASIC or PREMIUM)

        Returns:
            Temperature float value
        """
        if not self._is_loaded:
            self.load()

        tier_key = tier.value if isinstance(tier, ModelTier) else tier
        tier_config = self._config.get("tiers", {}).get(tier_key, {})
        return tier_config.get("temperature", self._defaults["defaults"]["temperature"])

    def get_max_tokens(self, tier: ModelTier | str) -> int:
        """Get the max tokens for a tier.

        Args:
            tier: Model tier (BASIC or PREMIUM)

        Returns:
            Max tokens integer
        """
        if not self._is_loaded:
            self.load()

        tier_key = tier.value if isinstance(tier, ModelTier) else tier
        tier_config = self._config.get("tiers", {}).get(tier_key, {})
        return tier_config.get("max_tokens", self._defaults["defaults"]["max_tokens"])

    def get_fallback(self, tier: ModelTier | str) -> dict[str, Any] | None:
        """Get the fallback configuration for a tier.

        Args:
            tier: Model tier (BASIC or PREMIUM)

        Returns:
            Fallback config dict or None if no fallback
        """
        if not self._is_loaded:
            self.load()

        tier_key = tier.value if isinstance(tier, ModelTier) else tier
        tier_config = self._config.get("tiers", {}).get(tier_key, {})
        return tier_config.get("fallback")

    def get_tier_config(self, tier: ModelTier | str) -> dict[str, Any]:
        """Get the full configuration for a tier.

        Args:
            tier: Model tier (BASIC or PREMIUM)

        Returns:
            Complete tier configuration dictionary
        """
        if not self._is_loaded:
            self.load()

        tier_key = tier.value if isinstance(tier, ModelTier) else tier
        return self._config.get("tiers", {}).get(tier_key, self._defaults["defaults"])

    def _merge_config(self, yaml_config: dict[str, Any]) -> None:
        """Merge YAML config into current config.

        Args:
            yaml_config: Configuration loaded from YAML
        """
        if "tiers" in yaml_config:
            for tier_key, tier_config in yaml_config["tiers"].items():
                if tier_key in self._config["tiers"]:
                    self._config["tiers"][tier_key].update(tier_config)
                else:
                    self._config["tiers"][tier_key] = tier_config

        if "defaults" in yaml_config:
            self._config["defaults"].update(yaml_config["defaults"])

        if "known_models" in yaml_config:
            self._config["known_models"] = yaml_config["known_models"]

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides."""
        # Check for tier-specific overrides
        for tier in ["basic", "premium"]:
            tier_upper = tier.upper()

            # Model override
            env_model = os.environ.get(f"LLM_MODEL_{tier_upper}")
            if env_model:
                if tier not in self._config["tiers"]:
                    self._config["tiers"][tier] = {}
                self._config["tiers"][tier]["model"] = env_model

            # Provider override
            env_provider = os.environ.get(f"LLM_PROVIDER_{tier_upper}")
            if env_provider:
                if tier not in self._config["tiers"]:
                    self._config["tiers"][tier] = {}
                self._config["tiers"][tier]["provider"] = env_provider

        # Legacy single model env var for basic tier
        legacy_model = os.environ.get("LLM_MODEL")
        if legacy_model and "LLM_MODEL_BASIC" not in os.environ:
            if "basic" not in self._config["tiers"]:
                self._config["tiers"]["basic"] = {}
            self._config["tiers"]["basic"]["model"] = legacy_model

    def _validate_models(self) -> None:
        """Validate model names against known models list."""
        known_models = self._config.get("known_models", {})

        for tier_key, tier_config in self._config.get("tiers", {}).items():
            provider = tier_config.get("provider", "openai")
            model = tier_config.get("model", "")

            provider_models = known_models.get(provider, [])
            if provider_models and model and model not in provider_models:
                logger.warning(
                    f"Unknown model '{model}' for provider '{provider}' in tier '{tier_key}'. " f"Using default.",
                    extra={"tier": tier_key, "model": model, "provider": provider},
                )
                # Fall back to default model
                self._config["tiers"][tier_key]["model"] = self._defaults["defaults"]["model"]

    def _deep_copy(self, obj: dict[str, Any]) -> dict[str, Any]:
        """Create a deep copy of a dictionary.

        Args:
            obj: Dictionary to copy

        Returns:
            Deep copy of the dictionary
        """
        import copy

        return copy.deepcopy(obj)


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
