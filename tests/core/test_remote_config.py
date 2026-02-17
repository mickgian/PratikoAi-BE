"""Tests for remote configuration module (Flagsmith integration).

TDD: Tests written FIRST before implementation.
Tests the Flagsmith fallback chain: Flagsmith -> env var -> hardcoded default.
"""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestGetConfig:
    """Tests for get_config() fallback chain."""

    def test_returns_default_when_flagsmith_unavailable(self) -> None:
        """When Flagsmith is not configured, returns env var or default."""
        from app.core.remote_config import get_config

        result = get_config("nonexistent_key", "fallback_value")
        assert result == "fallback_value"

    def test_returns_env_var_over_default(self) -> None:
        """Environment variable takes precedence over hardcoded default."""
        from app.core.remote_config import get_config

        with patch.dict(os.environ, {"TEST_CONFIG_KEY": "from_env"}):
            result = get_config("TEST_CONFIG_KEY", "default_value")
            assert result == "from_env"

    def test_returns_default_for_missing_env_var(self) -> None:
        """Falls back to default when env var is not set."""
        from app.core.remote_config import get_config

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DEFINITELY_NOT_SET_XYZ", None)
            result = get_config("DEFINITELY_NOT_SET_XYZ", "my_default")
            assert result == "my_default"


class TestGetFeatureFlag:
    """Tests for get_feature_flag() boolean evaluation."""

    def test_returns_default_when_flagsmith_unavailable(self) -> None:
        """When Flagsmith is not configured, returns the default boolean."""
        from app.core.remote_config import get_feature_flag

        assert get_feature_flag("some_flag", default=True) is True
        assert get_feature_flag("some_flag", default=False) is False

    def test_returns_env_var_as_bool(self) -> None:
        """Converts env var string to boolean."""
        from app.core.remote_config import get_feature_flag

        with patch.dict(os.environ, {"MY_FLAG": "true"}):
            assert get_feature_flag("MY_FLAG", default=False) is True

        with patch.dict(os.environ, {"MY_FLAG": "false"}):
            assert get_feature_flag("MY_FLAG", default=True) is False


class TestInitFlagsmith:
    """Tests for Flagsmith client initialization."""

    def test_init_without_key_returns_none(self) -> None:
        """No Flagsmith client when server key is not configured."""
        from app.core.remote_config import _init_flagsmith_client

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FLAGSMITH_SERVER_KEY", None)
            client = _init_flagsmith_client()
            assert client is None
