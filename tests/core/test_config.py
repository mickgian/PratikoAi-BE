"""Tests for configuration management."""

import os
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import (
    Environment,
    Settings,
    get_environment,
    parse_dict_of_lists_from_env,
    parse_list_from_env,
)


class TestEnvironmentEnum:
    """Test Environment enum."""

    def test_environment_values(self):
        """Test environment enum values."""
        assert Environment.DEVELOPMENT == "development"
        assert Environment.QA == "qa"
        assert Environment.PRODUCTION == "production"

    def test_environment_is_string(self):
        """Test environment values are strings."""
        assert isinstance(Environment.DEVELOPMENT.value, str)
        assert isinstance(Environment.QA.value, str)


class TestGetEnvironment:
    """Test get_environment function."""

    @patch.dict(os.environ, {"APP_ENV": "development"})
    def test_get_development_environment(self):
        """Test getting development environment."""
        env = get_environment()
        assert env == Environment.DEVELOPMENT

    @patch.dict(os.environ, {"APP_ENV": "qa"})
    def test_get_qa_environment(self):
        """Test getting QA environment."""
        env = get_environment()
        assert env == Environment.QA

    @patch.dict(os.environ, {"APP_ENV": "production"})
    def test_get_production_environment(self):
        """Test getting production environment."""
        env = get_environment()
        assert env == Environment.PRODUCTION

    @patch.dict(os.environ, {"APP_ENV": "prod"})
    def test_get_production_with_short_name(self):
        """Test getting production with 'prod' alias."""
        env = get_environment()
        assert env == Environment.PRODUCTION

    @patch.dict(os.environ, {}, clear=True)
    def test_get_default_environment(self):
        """Test default environment when APP_ENV not set."""
        env = get_environment()
        assert env == Environment.DEVELOPMENT

    @patch.dict(os.environ, {"APP_ENV": "unknown"})
    def test_get_unknown_defaults_to_development(self):
        """Test unknown environment defaults to development."""
        env = get_environment()
        assert env == Environment.DEVELOPMENT

    @patch.dict(os.environ, {"APP_ENV": "PRODUCTION"})
    def test_get_environment_case_insensitive(self):
        """Test environment detection is case insensitive."""
        env = get_environment()
        assert env == Environment.PRODUCTION


class TestParseListFromEnv:
    """Test parse_list_from_env function."""

    @patch.dict(os.environ, {"TEST_LIST": "item1,item2,item3"})
    def test_parse_comma_separated_list(self):
        """Test parsing comma-separated list."""
        result = parse_list_from_env("TEST_LIST")
        assert result == ["item1", "item2", "item3"]

    @patch.dict(os.environ, {"TEST_LIST": "single"})
    def test_parse_single_value(self):
        """Test parsing single value."""
        result = parse_list_from_env("TEST_LIST")
        assert result == ["single"]

    @patch.dict(os.environ, {}, clear=True)
    def test_parse_missing_key_returns_default(self):
        """Test missing key returns default."""
        result = parse_list_from_env("MISSING_KEY", default=["default"])
        assert result == ["default"]

    @patch.dict(os.environ, {}, clear=True)
    def test_parse_missing_key_returns_empty_list(self):
        """Test missing key returns empty list when no default."""
        result = parse_list_from_env("MISSING_KEY")
        assert result == []

    @patch.dict(os.environ, {"TEST_LIST": '"item1,item2"'})
    def test_parse_strips_quotes(self):
        """Test parsing strips surrounding quotes."""
        result = parse_list_from_env("TEST_LIST")
        assert result == ["item1", "item2"]

    @patch.dict(os.environ, {"TEST_LIST": "'item1,item2'"})
    def test_parse_strips_single_quotes(self):
        """Test parsing strips single quotes."""
        result = parse_list_from_env("TEST_LIST")
        assert result == ["item1", "item2"]

    @patch.dict(os.environ, {"TEST_LIST": " item1 , item2 , item3 "})
    def test_parse_strips_whitespace(self):
        """Test parsing strips whitespace from items."""
        result = parse_list_from_env("TEST_LIST")
        assert result == ["item1", "item2", "item3"]

    @patch.dict(os.environ, {"TEST_LIST": "item1,,item3"})
    def test_parse_filters_empty_items(self):
        """Test parsing filters out empty items."""
        result = parse_list_from_env("TEST_LIST")
        assert result == ["item1", "item3"]

    @patch.dict(os.environ, {"TEST_LIST": ""})
    def test_parse_empty_string_returns_default(self):
        """Test parsing empty string returns default."""
        result = parse_list_from_env("TEST_LIST", default=["default"])
        assert result == ["default"]


class TestParseDictOfListsFromEnv:
    """Test parse_dict_of_lists_from_env function."""

    @patch.dict(
        os.environ,
        {
            "PREFIX_CHAT": "30 per minute",
            "PREFIX_LOGIN": "20 per minute",
        },
    )
    def test_parse_dict_of_lists(self):
        """Test parsing dictionary of lists from environment."""
        result = parse_dict_of_lists_from_env("PREFIX_")

        assert "chat" in result
        assert "login" in result
        assert result["chat"] == ["30 per minute"]
        assert result["login"] == ["20 per minute"]

    @patch.dict(os.environ, {"PREFIX_ENDPOINT": "val1,val2,val3"})
    def test_parse_dict_with_comma_separated(self):
        """Test parsing dict with comma-separated values."""
        result = parse_dict_of_lists_from_env("PREFIX_")

        assert result["endpoint"] == ["val1", "val2", "val3"]

    @patch.dict(os.environ, {}, clear=True)
    def test_parse_dict_no_matches_returns_empty(self):
        """Test parsing with no matches returns empty dict."""
        result = parse_dict_of_lists_from_env("PREFIX_")
        assert result == {}

    @patch.dict(os.environ, {}, clear=True)
    def test_parse_dict_with_default(self):
        """Test parsing with default dictionary."""
        default = {"existing": ["value"]}
        result = parse_dict_of_lists_from_env("PREFIX_", default_dict=default)
        assert result == {"existing": ["value"]}

    @patch.dict(os.environ, {"PREFIX_NEW": "value"})
    def test_parse_dict_extends_default(self):
        """Test parsing extends default dictionary."""
        default = {"existing": ["value"]}
        result = parse_dict_of_lists_from_env("PREFIX_", default_dict=default)

        assert "existing" in result
        assert "new" in result

    @patch.dict(os.environ, {"PREFIX_TEST": '"val1,val2"'})
    def test_parse_dict_strips_quotes(self):
        """Test parsing strips quotes from values."""
        result = parse_dict_of_lists_from_env("PREFIX_")
        assert result["test"] == ["val1", "val2"]

    @patch.dict(os.environ, {"PREFIX_TEST": " val1 , val2 "})
    def test_parse_dict_strips_whitespace(self):
        """Test parsing strips whitespace."""
        result = parse_dict_of_lists_from_env("PREFIX_")
        assert result["test"] == ["val1", "val2"]


class TestSettings:
    """Test Settings class initialization."""

    @patch("app.core.config.get_environment")
    @patch("app.core.config.load_env_file")
    def test_settings_initialization(self, mock_load_env, mock_get_env):
        """Test Settings initializes correctly."""
        mock_get_env.return_value = Environment.DEVELOPMENT

        settings = Settings()

        assert settings.ENVIRONMENT == Environment.DEVELOPMENT
        assert hasattr(settings, "PROJECT_NAME")
        assert hasattr(settings, "DEBUG")

    @patch("app.core.config.get_environment")
    @patch("app.core.config.load_env_file")
    @patch.dict(os.environ, {"DEBUG": "true"})
    def test_settings_debug_true(self, mock_load_env, mock_get_env):
        """Test DEBUG setting parsed correctly."""
        mock_get_env.return_value = Environment.DEVELOPMENT

        settings = Settings()
        assert settings.DEBUG is True

    @patch("app.core.config.get_environment")
    @patch("app.core.config.load_env_file")
    @patch.dict(os.environ, {"DEBUG": "false"})
    def test_settings_debug_false(self, mock_load_env, mock_get_env):
        """Test DEBUG false parsing."""
        mock_get_env.return_value = Environment.DEVELOPMENT

        settings = Settings()
        assert settings.DEBUG is False

    @patch("app.core.config.get_environment")
    @patch("app.core.config.load_env_file")
    @patch.dict(os.environ, {"MAX_TOKENS": "5000"})
    def test_settings_integer_parsing(self, mock_load_env, mock_get_env):
        """Test integer settings parsed correctly."""
        mock_get_env.return_value = Environment.DEVELOPMENT

        settings = Settings()
        assert settings.MAX_TOKENS == 5000
        assert isinstance(settings.MAX_TOKENS, int)

    @patch("app.core.config.get_environment")
    @patch("app.core.config.load_env_file")
    @patch.dict(os.environ, {"DEFAULT_LLM_TEMPERATURE": "0.7"})
    def test_settings_float_parsing(self, mock_load_env, mock_get_env):
        """Test float settings parsed correctly."""
        mock_get_env.return_value = Environment.DEVELOPMENT

        settings = Settings()
        assert settings.DEFAULT_LLM_TEMPERATURE == 0.7
        assert isinstance(settings.DEFAULT_LLM_TEMPERATURE, float)

    @patch("app.core.config.get_environment")
    @patch("app.core.config.load_env_file")
    def test_settings_has_llm_config(self, mock_load_env, mock_get_env):
        """Test Settings has LLM configuration."""
        mock_get_env.return_value = Environment.DEVELOPMENT

        settings = Settings()

        assert hasattr(settings, "OPENAI_API_KEY")
        assert hasattr(settings, "OPENAI_MODEL")
        assert hasattr(settings, "ANTHROPIC_API_KEY")
        assert hasattr(settings, "ANTHROPIC_MODEL")

    @patch("app.core.config.get_environment")
    @patch("app.core.config.load_env_file")
    def test_settings_has_database_config(self, mock_load_env, mock_get_env):
        """Test Settings has database configuration."""
        mock_get_env.return_value = Environment.DEVELOPMENT

        settings = Settings()

        assert hasattr(settings, "POSTGRES_URL")
        assert hasattr(settings, "POSTGRES_POOL_SIZE")
        assert hasattr(settings, "REDIS_URL")

    @patch("app.core.config.get_environment")
    @patch("app.core.config.load_env_file")
    def test_settings_has_security_config(self, mock_load_env, mock_get_env):
        """Test Settings has security configuration."""
        mock_get_env.return_value = Environment.DEVELOPMENT

        settings = Settings()

        assert hasattr(settings, "JWT_SECRET_KEY")
        assert hasattr(settings, "JWT_ALGORITHM")
        assert hasattr(settings, "ENABLE_EXTERNAL_AV_SCAN")

    @patch("app.core.config.get_environment")
    @patch("app.core.config.load_env_file")
    @patch.dict(os.environ, {}, clear=True)
    def test_settings_default_values(self, mock_load_env, mock_get_env):
        """Test Settings has sensible defaults."""
        mock_get_env.return_value = Environment.DEVELOPMENT

        settings = Settings()

        assert settings.API_V1_STR == "/api/v1"
        assert settings.MAX_TOKENS == 2000
        assert settings.DEFAULT_LLM_TEMPERATURE == 0.2


class TestApplyEnvironmentSettings:
    """Test apply_environment_settings method."""

    @patch("app.core.config.get_environment")
    @patch("app.core.config.load_env_file")
    @patch.dict(os.environ, {}, clear=True)
    def test_development_settings(self, mock_load_env, mock_get_env):
        """Test development environment settings."""
        mock_get_env.return_value = Environment.DEVELOPMENT

        settings = Settings()

        assert settings.DEBUG is True
        assert settings.LOG_LEVEL == "DEBUG"
        assert settings.LOG_FORMAT == "console"

    @patch("app.core.config.get_environment")
    @patch("app.core.config.load_env_file")
    @patch.dict(os.environ, {}, clear=True)
    def test_production_settings(self, mock_load_env, mock_get_env):
        """Test production environment settings."""
        mock_get_env.return_value = Environment.PRODUCTION

        settings = Settings()

        assert settings.DEBUG is False
        assert settings.LOG_LEVEL == "WARNING"
        assert settings.LOG_FORMAT == "json"

    @patch("app.core.config.get_environment")
    @patch("app.core.config.load_env_file")
    @patch.dict(os.environ, {"DEBUG": "true", "LOG_LEVEL": "INFO"})
    def test_explicit_env_vars_override_environment(self, mock_load_env, mock_get_env):
        """Test explicit environment variables override environment defaults."""
        mock_get_env.return_value = Environment.PRODUCTION

        settings = Settings()

        # Explicit env vars should override production defaults
        assert settings.DEBUG is True
        assert settings.LOG_LEVEL == "INFO"
