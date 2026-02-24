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

    def test_init_with_local_evaluation_mode(self) -> None:
        """Flagsmith client uses local evaluation with 60s refresh."""
        from app.core.remote_config import _init_flagsmith_client

        mock_flagsmith_cls = MagicMock()
        mock_client = MagicMock()
        mock_flagsmith_cls.return_value = mock_client

        with (
            patch.dict(
                os.environ,
                {
                    "FLAGSMITH_SERVER_KEY": "ser.test-key",
                    "FLAGSMITH_API_URL": "http://flagsmith:8000/api/v1/",
                },
            ),
            patch("app.core.remote_config.Flagsmith", mock_flagsmith_cls, create=True),
            patch.dict("sys.modules", {"flagsmith": MagicMock(Flagsmith=mock_flagsmith_cls)}),
        ):
            # Re-import to pick up the mock
            import importlib

            import app.core.remote_config as rc

            importlib.reload(rc)

            result = rc._init_flagsmith_client()

            # Verify the Flagsmith constructor was called with local eval params
            mock_flagsmith_cls.assert_called_once()
            call_kwargs = mock_flagsmith_cls.call_args
            assert call_kwargs.kwargs["enable_local_evaluation"] is True
            assert call_kwargs.kwargs["environment_refresh_interval_seconds"] == 60
            assert call_kwargs.kwargs["default_flag_handler"] is not None
            assert call_kwargs.kwargs["environment_key"] == "ser.test-key"
            assert result is mock_client


class TestFlagsmithHasKey:
    """Tests for _flagsmith_has_key() helper."""

    def test_returns_false_when_flagsmith_unavailable(self) -> None:
        """When Flagsmith is not configured, always returns False."""
        from app.core.remote_config import _flagsmith_has_key

        # No FLAGSMITH_SERVER_KEY → client is None → returns False
        assert _flagsmith_has_key("ANY_KEY") is False

    def test_returns_false_for_unknown_key(self) -> None:
        """Returns False when Flagsmith client raises or returns None value."""
        from app.core.remote_config import _flagsmith_has_key

        mock_client = MagicMock()
        mock_flags = MagicMock()
        mock_flags.get_feature_value.return_value = None
        mock_client.get_environment_flags.return_value = mock_flags

        with patch("app.core.remote_config._get_flagsmith", return_value=mock_client):
            assert _flagsmith_has_key("UNKNOWN_KEY") is False
            mock_flags.get_feature_value.assert_called_once_with("UNKNOWN_KEY")

    def test_returns_true_when_key_exists(self) -> None:
        """Returns True when Flagsmith has a non-None value for the key."""
        from app.core.remote_config import _flagsmith_has_key

        mock_client = MagicMock()
        mock_flags = MagicMock()
        mock_flags.get_feature_value.return_value = "some_value"
        mock_client.get_environment_flags.return_value = mock_flags

        with patch("app.core.remote_config._get_flagsmith", return_value=mock_client):
            assert _flagsmith_has_key("EXISTING_KEY") is True

    def test_returns_false_on_exception(self) -> None:
        """Returns False when Flagsmith raises an exception."""
        from app.core.remote_config import _flagsmith_has_key

        mock_client = MagicMock()
        mock_client.get_environment_flags.side_effect = Exception("connection error")

        with patch("app.core.remote_config._get_flagsmith", return_value=mock_client):
            assert _flagsmith_has_key("ANY_KEY") is False


class TestDefaultFlagHandler:
    """Tests for the default_flag_handler used when a flag key is unknown."""

    def test_default_flag_handler_returns_disabled_flag(self) -> None:
        """Unknown flags return a DefaultFlag with enabled=False and value=None."""
        from unittest.mock import patch as mock_patch

        mock_default_flag_cls = MagicMock()
        mock_flag = MagicMock()
        mock_default_flag_cls.return_value = mock_flag

        with mock_patch.dict(
            "sys.modules",
            {
                "flagsmith": MagicMock(),
                "flagsmith.models": MagicMock(DefaultFlag=mock_default_flag_cls),
            },
        ):
            import importlib

            import app.core.remote_config as rc

            importlib.reload(rc)

            result = rc._default_flag_handler("UNKNOWN_KEY")

            mock_default_flag_cls.assert_called_once_with(enabled=False, value=None)
            assert result is mock_flag
