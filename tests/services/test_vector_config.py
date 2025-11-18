"""Tests for vector configuration service."""

import pytest
from unittest.mock import patch
import os

from app.services.vector_config import (
    VectorConfig,
    VectorProvider,
)
from app.core.config import Environment


class TestVectorProvider:
    """Test VectorProvider enum."""

    def test_provider_values(self):
        """Test vector provider enum values."""
        assert VectorProvider.LOCAL == "local"
        assert VectorProvider.PINECONE == "pinecone"


class TestVectorConfig:
    """Test VectorConfig class."""

    @patch.dict(os.environ, {}, clear=True)
    @patch('app.services.vector_config.get_environment')
    def test_config_initialization_defaults(self, mock_env):
        """Test VectorConfig initializes with defaults."""
        mock_env.return_value = Environment.DEVELOPMENT

        config = VectorConfig()

        assert config.environment == Environment.DEVELOPMENT
        assert config.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
        assert config.embedding_dimension == 384
        assert config.strict_embedder_match is True
        assert config.strict_mode is False

    @patch.dict(os.environ, {
        "VEC_PROVIDER": "pinecone",
        "PINECONE_API_KEY": "test-key",
        "PINECONE_ENVIRONMENT": "serverless",
        "EMBEDDING_DIMENSION": "1536",
    })
    @patch('app.services.vector_config.get_environment')
    def test_config_initialization_from_env(self, mock_env):
        """Test VectorConfig loads from environment variables."""
        mock_env.return_value = Environment.DEVELOPMENT

        config = VectorConfig()

        assert config.vec_provider_override == "pinecone"
        assert config.pinecone_api_key == "test-key"
        assert config.pinecone_environment == "serverless"
        assert config.embedding_dimension == 1536

    @patch.dict(os.environ, {"VEC_PROVIDER": "local"}, clear=True)
    @patch('app.services.vector_config.get_environment')
    def test_get_provider_preference_override(self, mock_env):
        """Test explicit provider override takes precedence."""
        mock_env.return_value = Environment.PRODUCTION

        config = VectorConfig()
        provider = config.get_provider_preference()

        # Even in production, override should force local
        assert provider == "local"

    @patch.dict(os.environ, {}, clear=True)
    @patch('app.services.vector_config.get_environment')
    def test_get_provider_preference_development(self, mock_env):
        """Test development environment defaults to local."""
        mock_env.return_value = Environment.DEVELOPMENT

        config = VectorConfig()
        provider = config.get_provider_preference()

        assert provider == VectorProvider.LOCAL

    @patch.dict(os.environ, {
        "PINECONE_API_KEY": "test-key",
        "PINECONE_ENVIRONMENT": "serverless",
    }, clear=True)
    @patch('app.services.vector_config.get_environment')
    def test_get_provider_preference_qa_with_pinecone(self, mock_env):
        """Test QA environment with Pinecone configured."""
        mock_env.return_value = Environment.QA

        config = VectorConfig()
        provider = config.get_provider_preference()

        assert provider == VectorProvider.PINECONE

    @patch.dict(os.environ, {}, clear=True)
    @patch('app.services.vector_config.get_environment')
    def test_get_provider_preference_qa_without_pinecone(self, mock_env):
        """Test QA environment without Pinecone falls back to local."""
        mock_env.return_value = Environment.QA

        config = VectorConfig()
        provider = config.get_provider_preference()

        assert provider == VectorProvider.LOCAL

    @patch.dict(os.environ, {}, clear=True)
    @patch('app.services.vector_config.get_environment')
    def test_get_provider_preference_production(self, mock_env):
        """Test production environment uses Pinecone."""
        mock_env.return_value = Environment.PRODUCTION

        config = VectorConfig()
        provider = config.get_provider_preference()

        assert provider == VectorProvider.PINECONE

    @patch.dict(os.environ, {}, clear=True)
    @patch('app.services.vector_config.get_environment')
    def test_get_provider_preference_preprod(self, mock_env):
        """Test preprod environment mirrors production."""
        mock_env.return_value = Environment.PREPROD

        config = VectorConfig()
        provider = config.get_provider_preference()

        assert provider == VectorProvider.PINECONE

    @patch.dict(os.environ, {
        "PINECONE_API_KEY": "test-key",
        "PINECONE_ENVIRONMENT": "serverless",
    }, clear=True)
    @patch('app.services.vector_config.get_environment')
    def test_is_pinecone_configured_true(self, mock_env):
        """Test Pinecone configuration check when configured."""
        mock_env.return_value = Environment.DEVELOPMENT

        config = VectorConfig()

        assert config.is_pinecone_configured() is True

    @patch.dict(os.environ, {}, clear=True)
    @patch('app.services.vector_config.get_environment')
    def test_is_pinecone_configured_false(self, mock_env):
        """Test Pinecone configuration check when not configured."""
        mock_env.return_value = Environment.DEVELOPMENT

        config = VectorConfig()

        assert config.is_pinecone_configured() is False

    @patch.dict(os.environ, {"PINECONE_API_KEY": "test-key"}, clear=True)
    @patch('app.services.vector_config.get_environment')
    def test_is_pinecone_configured_partial(self, mock_env):
        """Test Pinecone configuration check with partial config."""
        mock_env.return_value = Environment.DEVELOPMENT

        config = VectorConfig()

        # Has default "serverless" for environment, so should be True
        assert config.is_pinecone_configured() is True

    @patch.dict(os.environ, {}, clear=True)
    @patch('app.services.vector_config.get_environment')
    def test_get_missing_pinecone_config(self, mock_env):
        """Test getting list of missing Pinecone config."""
        mock_env.return_value = Environment.DEVELOPMENT

        config = VectorConfig()
        missing = config.get_missing_pinecone_config()

        # Only API key is missing (environment has default "serverless")
        assert "PINECONE_API_KEY" in missing

    @patch.dict(os.environ, {"PINECONE_API_KEY": "test-key"}, clear=True)
    @patch('app.services.vector_config.get_environment')
    def test_get_missing_pinecone_config_partial(self, mock_env):
        """Test missing config with partial configuration."""
        mock_env.return_value = Environment.DEVELOPMENT

        config = VectorConfig()
        missing = config.get_missing_pinecone_config()

        # API key provided, environment has default, so nothing is missing
        assert len(missing) == 0

    @patch.dict(os.environ, {}, clear=True)
    @patch('app.services.vector_config.get_environment')
    def test_generate_index_name_default(self, mock_env):
        """Test generating index name with default dimension."""
        mock_env.return_value = Environment.DEVELOPMENT

        config = VectorConfig()
        index_name = config.generate_index_name()

        assert index_name == "pratikoai-embed-384"

    @patch.dict(os.environ, {}, clear=True)
    @patch('app.services.vector_config.get_environment')
    def test_generate_index_name_custom_dimension(self, mock_env):
        """Test generating index name with custom dimension."""
        mock_env.return_value = Environment.DEVELOPMENT

        config = VectorConfig()
        index_name = config.generate_index_name(dimension=1536)

        assert index_name == "pratikoai-embed-1536"

    @patch.dict(os.environ, {}, clear=True)
    @patch('app.services.vector_config.get_environment')
    def test_generate_index_name_from_model(self, mock_env):
        """Test generating index name from model."""
        mock_env.return_value = Environment.DEVELOPMENT

        config = VectorConfig()
        index_name = config.generate_index_name_from_model("text-embedding-3-small")

        # Falls back to dimension-based naming
        assert "pratikoai-embed" in index_name

    @patch.dict(os.environ, {}, clear=True)
    @patch('app.services.vector_config.get_environment')
    def test_build_namespace_valid(self, mock_env):
        """Test building valid namespace."""
        mock_env.return_value = Environment.DEVELOPMENT

        config = VectorConfig()
        namespace = config.build_namespace("dev", "ccnl", "default")

        assert namespace is not None
        assert "dev" in namespace or "ccnl" in namespace

    @patch.dict(os.environ, {}, clear=True)
    @patch('app.services.vector_config.get_environment')
    def test_build_namespace_invalid_domain(self, mock_env):
        """Test building namespace with invalid domain."""
        mock_env.return_value = Environment.DEVELOPMENT

        config = VectorConfig()

        with pytest.raises(ValueError, match="Invalid domain"):
            config.build_namespace("dev", "invalid_domain", "default")

    @patch.dict(os.environ, {}, clear=True)
    @patch('app.services.vector_config.get_environment')
    def test_build_namespace_invalid_env(self, mock_env):
        """Test building namespace with invalid environment."""
        mock_env.return_value = Environment.DEVELOPMENT

        config = VectorConfig()

        with pytest.raises(ValueError, match="Invalid environment" if hasattr(config, 'build_namespace') else ""):
            config.build_namespace("invalid", "ccnl", "default")

    @patch.dict(os.environ, {"DEBUG_VECTOR_SEARCH": "true"}, clear=True)
    @patch('app.services.vector_config.get_environment')
    def test_debug_mode_enabled(self, mock_env):
        """Test debug mode can be enabled."""
        mock_env.return_value = Environment.DEVELOPMENT

        config = VectorConfig()

        assert config.debug_mode is True

    @patch.dict(os.environ, {"VECTOR_STRICT_MODE": "true"}, clear=True)
    @patch('app.services.vector_config.get_environment')
    def test_strict_mode_enabled(self, mock_env):
        """Test strict mode can be enabled."""
        mock_env.return_value = Environment.DEVELOPMENT

        config = VectorConfig()

        assert config.strict_mode is True
