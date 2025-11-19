"""Tests for vector provider factory."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from app.core.config import Environment
from app.services.vector_config import VectorConfig, VectorProvider
from app.services.vector_provider_factory import VectorProviderFactory, VectorSearchProvider


class TestVectorProviderFactory:
    """Test VectorProviderFactory class."""

    def test_initialization_with_config(self):
        """Test factory initialization with config."""
        config = VectorConfig()
        factory = VectorProviderFactory(config=config)

        assert factory.config == config

    def test_initialization_without_config(self):
        """Test factory initialization creates default config."""
        factory = VectorProviderFactory()

        assert factory.config is not None
        assert isinstance(factory.config, VectorConfig)

    def test_select_provider_type(self):
        """Test provider type selection."""
        config = Mock()
        config.get_provider_preference.return_value = VectorProvider.LOCAL

        factory = VectorProviderFactory(config=config)
        provider_type = factory.select_provider_type()

        assert provider_type == VectorProvider.LOCAL
        config.get_provider_preference.assert_called_once()

    def test_build_index_name(self):
        """Test index name building."""
        config = Mock()
        config.generate_index_name.return_value = "pratikoai-embed-384"

        factory = VectorProviderFactory(config=config)
        index_name = factory.build_index_name(embedding_dimension=384)

        assert index_name == "pratikoai-embed-384"
        config.generate_index_name.assert_called_once_with(384)

    def test_build_namespace(self):
        """Test namespace building."""
        config = Mock()
        config.build_namespace.return_value = "dev-ccnl-default"

        factory = VectorProviderFactory(config=config)
        namespace = factory.build_namespace(env="dev", domain="ccnl", tenant="default")

        assert namespace == "dev-ccnl-default"
        config.build_namespace.assert_called_once_with("dev", "ccnl", "default")

    @patch("app.services.vector_provider_factory.VectorProviderFactory._create_local_provider")
    def test_get_provider_local(self, mock_create_local):
        """Test getting local provider."""
        mock_provider = Mock(spec=VectorSearchProvider)
        mock_create_local.return_value = mock_provider

        config = Mock()
        config.get_provider_preference.return_value = VectorProvider.LOCAL

        factory = VectorProviderFactory(config=config)
        provider = factory.get_provider(Environment.DEVELOPMENT)

        assert provider == mock_provider
        mock_create_local.assert_called_once()

    @patch("app.services.vector_provider_factory.VectorProviderFactory._create_pinecone_provider")
    def test_get_provider_pinecone_success(self, mock_create_pinecone):
        """Test getting Pinecone provider successfully."""
        mock_provider = Mock(spec=VectorSearchProvider)
        mock_create_pinecone.return_value = mock_provider

        config = Mock()
        config.get_provider_preference.return_value = VectorProvider.PINECONE

        factory = VectorProviderFactory(config=config)
        provider = factory.get_provider(Environment.PRODUCTION)

        assert provider == mock_provider
        mock_create_pinecone.assert_called_once()

    @patch("app.services.vector_provider_factory.VectorProviderFactory._handle_pinecone_failure")
    @patch("app.services.vector_provider_factory.VectorProviderFactory._create_pinecone_provider")
    def test_get_provider_pinecone_failure_fallback(self, mock_create_pinecone, mock_handle_failure):
        """Test Pinecone failure triggers fallback."""
        error = ValueError("Pinecone config missing")
        mock_create_pinecone.side_effect = error

        mock_fallback_provider = Mock(spec=VectorSearchProvider)
        mock_handle_failure.return_value = mock_fallback_provider

        config = Mock()
        config.get_provider_preference.return_value = VectorProvider.PINECONE

        factory = VectorProviderFactory(config=config)
        provider = factory.get_provider(Environment.DEVELOPMENT)

        assert provider == mock_fallback_provider
        mock_handle_failure.assert_called_once_with(error, Environment.DEVELOPMENT)

    def test_create_pinecone_provider_not_configured(self):
        """Test Pinecone provider creation fails when not configured."""
        config = Mock()
        config.is_pinecone_configured.return_value = False
        config.get_missing_pinecone_config.return_value = ["PINECONE_API_KEY"]

        factory = VectorProviderFactory(config=config)

        with pytest.raises(ValueError, match="Pinecone configuration missing"):
            factory._create_pinecone_provider()

    @patch("app.services.vector_providers.pinecone_provider.PineconeProvider")
    def test_create_pinecone_provider_success(self, mock_pinecone_class):
        """Test successful Pinecone provider creation."""
        mock_provider = Mock(spec=VectorSearchProvider)
        mock_pinecone_class.return_value = mock_provider

        config = Mock()
        config.is_pinecone_configured.return_value = True
        config.pinecone_api_key = "test-key"  # pragma: allowlist secret
        config.pinecone_environment = "serverless"
        config.get_effective_index_name.return_value = "test-index"
        config.embedding_dimension = 384
        config.namespace_prefix = "test-"

        factory = VectorProviderFactory(config=config)
        provider = factory._create_pinecone_provider()

        assert provider == mock_provider
        mock_pinecone_class.assert_called_once_with(
            api_key="test-key",
            environment="serverless",
            index_name="test-index",
            dimension=384,
            namespace_prefix="test-",
        )

    @patch("app.services.vector_providers.local_provider.LocalVectorProvider")
    def test_create_local_provider_success(self, mock_local_class):
        """Test successful local provider creation."""
        mock_provider = Mock(spec=VectorSearchProvider)
        mock_local_class.return_value = mock_provider

        config = Mock()
        config.embedding_dimension = 384
        config.embedding_model = "test-model"

        factory = VectorProviderFactory(config=config)
        provider = factory._create_local_provider()

        assert provider == mock_provider
        mock_local_class.assert_called_once_with(embedding_dimension=384, embedding_model="test-model")

    @patch("app.services.vector_providers.local_provider.LocalVectorProvider")
    def test_create_local_provider_failure(self, mock_local_class):
        """Test local provider creation failure."""
        mock_local_class.side_effect = Exception("Import error")

        config = Mock()
        config.embedding_dimension = 384
        config.embedding_model = "test-model"

        factory = VectorProviderFactory(config=config)

        with pytest.raises(Exception, match="Import error"):
            factory._create_local_provider()

    @patch("app.services.vector_provider_factory.VectorProviderFactory._create_local_provider")
    def test_handle_pinecone_failure_fallback_allowed(self, mock_create_local):
        """Test Pinecone failure fallback when allowed."""
        mock_provider = Mock(spec=VectorSearchProvider)
        mock_create_local.return_value = mock_provider

        config = Mock()
        config.allow_fallback.return_value = True
        config.strict_mode = False

        factory = VectorProviderFactory(config=config)
        error = Exception("Pinecone error")
        provider = factory._handle_pinecone_failure(error, Environment.DEVELOPMENT)

        assert provider == mock_provider
        mock_create_local.assert_called_once()

    def test_handle_pinecone_failure_production_strict_mode(self):
        """Test Pinecone failure in production strict mode raises."""
        config = Mock()
        config.allow_fallback.return_value = False
        config.strict_mode = True

        factory = VectorProviderFactory(config=config)
        error = Exception("Pinecone error")

        with pytest.raises(RuntimeError, match="Pinecone required for production"):
            factory._handle_pinecone_failure(error, Environment.PRODUCTION)

    def test_validate_embedder_compatibility_no_methods(self):
        """Test embedder validation when methods don't exist."""
        provider = Mock(spec=[])  # No methods
        embedding_model = Mock(spec=[])

        factory = VectorProviderFactory()
        # Should not raise, just log warnings
        factory.validate_embedder_compatibility(provider, embedding_model)

    def test_validate_embedder_compatibility_no_index_dimension(self):
        """Test embedder validation when index dimension is None."""
        provider = Mock()
        provider.get_index_dimension.return_value = None

        embedding_model = Mock()
        embedding_model.get_sentence_embedding_dimension.return_value = 384

        factory = VectorProviderFactory()
        # Should not raise
        factory.validate_embedder_compatibility(provider, embedding_model)

    def test_validate_embedder_compatibility_match(self):
        """Test embedder validation with matching dimensions."""
        provider = Mock()
        provider.get_index_dimension.return_value = 384

        embedding_model = Mock()
        embedding_model.get_sentence_embedding_dimension.return_value = 384

        factory = VectorProviderFactory()
        # Should not raise
        factory.validate_embedder_compatibility(provider, embedding_model)

    def test_validate_embedder_compatibility_mismatch_permissive(self):
        """Test embedder validation mismatch in permissive mode."""
        provider = Mock()
        provider.get_index_dimension.return_value = 384

        embedding_model = Mock()
        embedding_model.get_sentence_embedding_dimension.return_value = 512

        config = Mock()
        config.strict_embedder_match = False

        factory = VectorProviderFactory(config=config)
        # Should not raise, just log warning
        factory.validate_embedder_compatibility(provider, embedding_model)

    def test_validate_embedder_compatibility_mismatch_strict(self):
        """Test embedder validation mismatch in strict mode."""
        provider = Mock()
        provider.get_index_dimension.return_value = 384

        embedding_model = Mock()
        embedding_model.get_sentence_embedding_dimension.return_value = 512

        config = Mock()
        config.strict_embedder_match = True

        factory = VectorProviderFactory(config=config)

        with pytest.raises(ValueError, match="Dimension mismatch"):
            factory.validate_embedder_compatibility(provider, embedding_model)

    def test_perform_startup_checks_basic(self):
        """Test basic startup checks."""
        provider = Mock(spec=VectorSearchProvider)
        provider.test_connection.return_value = True

        config = Mock()
        config.format_for_logging.return_value = {"test": "config"}
        config.environment = Environment.DEVELOPMENT
        config.get_effective_index_name.return_value = "test-index"
        config.get_current_namespace_env.return_value = "dev"
        config.embedding_model = "test-model"
        config.embedding_dimension = 384

        factory = VectorProviderFactory(config=config)
        checks = factory.perform_startup_checks(provider)

        assert checks["status"] == "ok"
        assert checks["provider_type"] == type(provider).__name__
        assert len(checks["errors"]) == 0

    def test_perform_startup_checks_connection_failed(self):
        """Test startup checks with connection failure."""
        provider = Mock(spec=VectorSearchProvider)
        provider.test_connection.side_effect = Exception("Connection failed")

        config = Mock()
        config.format_for_logging.return_value = {}
        config.environment = Environment.DEVELOPMENT
        config.get_effective_index_name.return_value = "test-index"
        config.get_current_namespace_env.return_value = "dev"
        config.embedding_model = "test-model"
        config.embedding_dimension = 384

        factory = VectorProviderFactory(config=config)
        checks = factory.perform_startup_checks(provider)

        assert len(checks["warnings"]) > 0
        assert any("Connection test failed" in w for w in checks["warnings"])

    def test_perform_startup_checks_with_embedding_model(self):
        """Test startup checks with embedding model validation."""
        provider = Mock(spec=VectorSearchProvider)
        provider.test_connection.return_value = True
        provider.get_index_dimension.return_value = 384

        embedding_model = Mock()
        embedding_model.get_sentence_embedding_dimension.return_value = 384

        config = Mock()
        config.format_for_logging.return_value = {}
        config.environment = Environment.DEVELOPMENT
        config.get_effective_index_name.return_value = "test-index"
        config.get_current_namespace_env.return_value = "dev"
        config.embedding_model = "test-model"
        config.embedding_dimension = 384
        config.strict_embedder_match = False

        factory = VectorProviderFactory(config=config)
        checks = factory.perform_startup_checks(provider, embedding_model=embedding_model)

        assert checks["status"] == "ok"
        assert len(checks["errors"]) == 0
