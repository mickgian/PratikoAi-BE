"""Tests for LLM factory and routing functionality."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.llm.base import LLMProviderType
from app.core.llm.factory import LLMFactory, RoutingStrategy, get_llm_factory, get_llm_provider
from app.schemas.chat import Message


class TestLLMFactory:
    """Test cases for the LLM factory."""

    def setup_method(self):
        """Set up test fixtures."""
        self.factory = LLMFactory()

    @patch("app.core.llm.factory.settings")
    def test_get_provider_configs_openai_only(self, mock_settings):
        """Test provider configuration with OpenAI only."""
        mock_settings.LLM_API_KEY = "test-openai-key"
        mock_settings.LLM_MODEL = "gpt-4o-mini"
        mock_settings.ANTHROPIC_API_KEY = ""

        factory = LLMFactory()
        configs = factory._get_provider_configs()

        assert "openai" in configs
        assert "anthropic" not in configs
        assert configs["openai"]["api_key"] == "test-openai-key"

    @patch("app.core.llm.factory.settings")
    def test_get_provider_configs_both_providers(self, mock_settings):
        """Test provider configuration with both providers."""
        mock_settings.LLM_API_KEY = "test-openai-key"
        mock_settings.LLM_MODEL = "gpt-4o-mini"
        mock_settings.ANTHROPIC_API_KEY = "test-anthropic-key"
        mock_settings.ANTHROPIC_MODEL = "claude-3-haiku-20240307"

        factory = LLMFactory()
        configs = factory._get_provider_configs()

        assert "openai" in configs
        assert "anthropic" in configs
        assert configs["openai"]["api_key"] == "test-openai-key"
        assert configs["anthropic"]["api_key"] == "test-anthropic-key"

    @patch("app.core.llm.factory.settings")
    def test_create_openai_provider(self, mock_settings):
        """Test creating OpenAI provider."""
        mock_settings.LLM_API_KEY = "test-openai-key"
        mock_settings.LLM_MODEL = "gpt-4o-mini"
        mock_settings.ANTHROPIC_API_KEY = ""

        factory = LLMFactory()
        provider = factory.create_provider(LLMProviderType.OPENAI)

        assert provider.provider_type == LLMProviderType.OPENAI
        assert provider.api_key == "test-openai-key"
        assert provider.model == "gpt-4o-mini"

    @patch("app.core.llm.factory.settings")
    def test_create_anthropic_provider(self, mock_settings):
        """Test creating Anthropic provider."""
        mock_settings.LLM_API_KEY = "test-openai-key"
        mock_settings.ANTHROPIC_API_KEY = "test-anthropic-key"
        mock_settings.ANTHROPIC_MODEL = "claude-3-haiku-20240307"

        factory = LLMFactory()
        provider = factory.create_provider(LLMProviderType.ANTHROPIC)

        assert provider.provider_type == LLMProviderType.ANTHROPIC
        assert provider.api_key == "test-anthropic-key"
        assert provider.model == "claude-3-haiku-20240307"

    @patch("app.core.llm.factory.settings")
    def test_create_provider_not_configured(self, mock_settings):
        """Test creating provider that's not configured."""
        mock_settings.LLM_API_KEY = ""
        mock_settings.ANTHROPIC_API_KEY = ""

        factory = LLMFactory()

        with pytest.raises(ValueError, match="Provider openai is not configured"):
            factory.create_provider(LLMProviderType.OPENAI)

    def test_create_provider_unsupported_type(self):
        """Test creating unsupported provider type."""
        # LOCAL provider type is not configured, so it raises "not configured" error
        with pytest.raises(ValueError, match=r"Provider local is not configured"):
            self.factory.create_provider(LLMProviderType.LOCAL)

    @patch("app.core.llm.factory.settings")
    def test_get_available_providers(self, mock_settings):
        """Test getting available providers."""
        mock_settings.LLM_API_KEY = "test-openai-key"
        mock_settings.LLM_MODEL = "gpt-4o-mini"
        mock_settings.ANTHROPIC_API_KEY = "test-anthropic-key"
        mock_settings.ANTHROPIC_MODEL = "claude-3-haiku-20240307"

        factory = LLMFactory()
        providers = factory.get_available_providers()

        assert len(providers) == 2
        provider_types = [p.provider_type for p in providers]
        assert LLMProviderType.OPENAI in provider_types
        assert LLMProviderType.ANTHROPIC in provider_types

    @patch("app.core.llm.factory.settings")
    def test_get_optimal_provider_cost_optimized(self, mock_settings):
        """Test getting optimal provider with cost optimization."""
        mock_settings.LLM_API_KEY = "test-openai-key"
        mock_settings.LLM_MODEL = "gpt-4o-mini"
        mock_settings.ANTHROPIC_API_KEY = ""

        factory = LLMFactory()
        messages = [Message(role="user", content="Hello")]

        provider = factory.get_optimal_provider(messages, strategy=RoutingStrategy.COST_OPTIMIZED)

        assert provider.provider_type == LLMProviderType.OPENAI

    @patch("app.core.llm.factory.settings")
    def test_get_optimal_provider_preferred(self, mock_settings):
        """Test getting optimal provider with preferred provider."""
        mock_settings.LLM_API_KEY = "test-openai-key"
        mock_settings.LLM_MODEL = "gpt-4o-mini"
        mock_settings.ANTHROPIC_API_KEY = "test-anthropic-key"
        mock_settings.ANTHROPIC_MODEL = "claude-3-haiku-20240307"

        factory = LLMFactory()
        messages = [Message(role="user", content="Hello")]

        provider = factory.get_optimal_provider(messages, preferred_provider="anthropic")

        assert provider.provider_type == LLMProviderType.ANTHROPIC

    @patch("app.core.llm.factory.settings")
    def test_get_optimal_provider_no_providers(self, mock_settings):
        """Test getting optimal provider with no configured providers."""
        mock_settings.LLM_API_KEY = ""
        mock_settings.ANTHROPIC_API_KEY = ""

        factory = LLMFactory()
        messages = [Message(role="user", content="Hello")]

        with pytest.raises(ValueError, match="No LLM providers are configured"):
            factory.get_optimal_provider(messages)

    @patch("app.core.llm.factory.settings")
    def test_route_quality_first(self, mock_settings):
        """Test quality-first routing strategy."""
        mock_settings.LLM_API_KEY = "test-openai-key"
        mock_settings.LLM_MODEL = "gpt-4o-mini"

        factory = LLMFactory()
        providers = factory.get_available_providers()
        messages = [Message(role="user", content="Complex analysis needed")]

        # Should work even with complex query
        provider = factory._route_quality_first(providers, messages, max_cost_eur=0.1)
        assert provider is not None

    @patch("app.core.llm.factory.settings")
    def test_route_balanced(self, mock_settings):
        """Test balanced routing strategy."""
        mock_settings.LLM_API_KEY = "test-openai-key"
        mock_settings.LLM_MODEL = "gpt-4o-mini"

        factory = LLMFactory()
        providers = factory.get_available_providers()
        messages = [Message(role="user", content="Hello")]

        provider = factory._route_balanced(providers, messages, max_cost_eur=None)
        assert provider is not None

    @patch("app.core.llm.factory.settings")
    def test_route_failover(self, mock_settings):
        """Test failover routing strategy."""
        mock_settings.LLM_API_KEY = "test-openai-key"
        mock_settings.LLM_MODEL = "gpt-4o-mini"

        factory = LLMFactory()
        providers = factory.get_available_providers()
        messages = [Message(role="user", content="Hello")]

        provider = factory._route_failover(providers, messages, max_cost_eur=None)
        assert provider is not None


class TestGlobalFunctions:
    """Test cases for global factory functions."""

    def test_get_llm_factory_singleton(self):
        """Test that get_llm_factory returns singleton."""
        factory1 = get_llm_factory()
        factory2 = get_llm_factory()

        assert factory1 is factory2

    @patch("app.core.llm.factory.get_llm_factory")
    def test_get_llm_provider_convenience(self, mock_get_factory):
        """Test get_llm_provider convenience function."""
        mock_factory = MagicMock()
        mock_provider = MagicMock()
        mock_factory.get_optimal_provider.return_value = mock_provider
        mock_get_factory.return_value = mock_factory

        messages = [Message(role="user", content="Hello")]
        result = get_llm_provider(messages)

        assert result == mock_provider
        mock_factory.get_optimal_provider.assert_called_once_with(
            messages=messages,
            strategy=RoutingStrategy.COST_OPTIMIZED,
            max_cost_eur=None,
            preferred_provider=None,
        )
