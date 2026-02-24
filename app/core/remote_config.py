"""Remote configuration via Flagsmith with env var fallback.

Provides a fallback chain for runtime-tunable configuration:
    Flagsmith -> environment variable -> hardcoded default

This allows changing LLM models, feature flags, RAG weights, and
thresholds without redeployment when Flagsmith is configured.

When Flagsmith is not available (no FLAGSMITH_SERVER_KEY), falls back
gracefully to environment variables and defaults.

Uses local evaluation mode for sub-ms latency (~425 req/s vs ~60 req/s
with remote evaluation). The full environment document is downloaded
once and refreshed every 60 seconds.

See ADR-031 for architecture decision.
"""

import logging
import os

# Use stdlib logging to avoid circular import with app.core.logging -> app.core.config
logger = logging.getLogger(__name__)

# Lazy-initialized Flagsmith client (None if not configured)
_flagsmith_client = None
_flagsmith_initialized = False


def _default_flag_handler(feature_name: str):
    """Handle unknown flags gracefully by returning None.

    This is called when a flag key is not found in the local environment
    document. Returns None so the caller falls through to env var / default.

    Args:
        feature_name: The flag key that was not found.

    Returns:
        A default Flag with no value.
    """
    from flagsmith.models import DefaultFlag

    logger.debug("flagsmith_unknown_flag feature=%s", feature_name)
    return DefaultFlag(enabled=False, value=None)


def _init_flagsmith_client():
    """Initialize Flagsmith client if server key is configured.

    Uses local evaluation mode to avoid per-request HTTP calls.
    The environment document is fetched once, then refreshed every 60s.

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
            enable_local_evaluation=True,
            environment_refresh_interval_seconds=60,
            default_flag_handler=_default_flag_handler,
        )
        logger.info("flagsmith_initialized api_url=%s local_eval=True", api_url)
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


def _flagsmith_has_key(key: str) -> bool:
    """Check if Flagsmith has an explicit value for this key (no env fallback).

    Used by apply_environment_settings() to avoid overwriting Flagsmith-sourced values.

    Args:
        key: The Flagsmith feature key to check.

    Returns:
        True if Flagsmith is configured and has a non-None value for this key.
    """
    client = _get_flagsmith()
    if client is None:
        return False
    try:
        flags = client.get_environment_flags()
        value = flags.get_feature_value(key)
        return value is not None
    except Exception:
        return False


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
