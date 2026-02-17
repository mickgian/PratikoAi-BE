"""Remote configuration via Flagsmith with env var fallback.

Provides a fallback chain for runtime-tunable configuration:
    Flagsmith -> environment variable -> hardcoded default

This allows changing LLM models, feature flags, RAG weights, and
thresholds without redeployment when Flagsmith is configured.

When Flagsmith is not available (no FLAGSMITH_SERVER_KEY), falls back
gracefully to environment variables and defaults.

See ADR-031 for architecture decision.
"""

import logging
import os

# Use stdlib logging to avoid circular import with app.core.logging -> app.core.config
logger = logging.getLogger(__name__)

# Lazy-initialized Flagsmith client (None if not configured)
_flagsmith_client = None
_flagsmith_initialized = False


def _init_flagsmith_client():
    """Initialize Flagsmith client if server key is configured.

    Returns:
        Flagsmith client instance, or None if not configured.
    """
    server_key = os.getenv("FLAGSMITH_SERVER_KEY")
    if not server_key:
        return None

    api_url = os.getenv("FLAGSMITH_API_URL", "http://flagsmith:8000/api/v1/")

    try:
        from flagsmith import Flagsmith

        client = Flagsmith(
            environment_key=server_key,
            api_url=api_url,
        )
        logger.info("flagsmith_initialized api_url=%s", api_url)
        return client
    except ImportError:
        logger.warning("flagsmith_sdk_not_installed")
        return None
    except Exception as e:
        logger.error("flagsmith_init_failed error=%s", str(e))
        return None


def _get_flagsmith():
    """Get or initialize the Flagsmith client (lazy singleton)."""
    global _flagsmith_client, _flagsmith_initialized
    if not _flagsmith_initialized:
        _flagsmith_client = _init_flagsmith_client()
        _flagsmith_initialized = True
    return _flagsmith_client


def get_config(key: str, default: str) -> str:
    """Get a configuration value with Flagsmith -> env var -> default fallback.

    Args:
        key: Configuration key (used as both Flagsmith feature key and env var name).
        default: Hardcoded default if neither Flagsmith nor env var provides a value.

    Returns:
        The configuration value string.
    """
    # Try Flagsmith first
    client = _get_flagsmith()
    if client is not None:
        try:
            flags = client.get_environment_flags()
            value = flags.get_feature_value(key)
            if value is not None:
                return str(value)
        except Exception:
            pass  # Fall through to env var

    # Fall back to environment variable
    env_value = os.getenv(key)
    if env_value is not None:
        return env_value

    # Fall back to hardcoded default
    return default


def get_feature_flag(key: str, default: bool = False) -> bool:
    """Get a boolean feature flag with Flagsmith -> env var -> default fallback.

    Args:
        key: Feature flag key.
        default: Default boolean value if not configured anywhere.

    Returns:
        Boolean flag value.
    """
    # Try Flagsmith first
    client = _get_flagsmith()
    if client is not None:
        try:
            flags = client.get_environment_flags()
            if flags.is_feature_enabled(key):
                return True
            # Flagsmith returns False for unknown flags, so check if it's explicitly set
            value = flags.get_feature_value(key)
            if value is not None:
                return str(value).lower() in ("true", "1", "yes", "on")
        except Exception:
            pass  # Fall through to env var

    # Fall back to environment variable
    env_value = os.getenv(key)
    if env_value is not None:
        return env_value.lower() in ("true", "1", "yes", "on", "t")

    return default
