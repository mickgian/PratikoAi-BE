"""
Test vector provider selection logic with environment-aware guardrails.

This module tests the provider selection, configuration resolution, and fallback
behavior without making network calls. All external dependencies are mocked.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from app.core.config import Environment


class TestProviderSelection:
    """Test provider selection logic for different environments."""
    
    def test_provider_selection_dev_defaults_to_local(self):
        """Development environment should default to local provider."""
        with patch.dict(os.environ, {"APP_ENV": "development"}, clear=True):
            with patch('app.core.config.get_environment', return_value=Environment.DEVELOPMENT):
                # Mock the provider factory we'll implement
                from app.services.vector_provider_factory import VectorProviderFactory
                
                factory = VectorProviderFactory()
                provider_type = factory.select_provider_type()
                
                assert provider_type == "local"
    
    def test_provider_selection_dev_explicit_pinecone_override(self):
        """Development can override to pinecone with VEC_PROVIDER=pinecone."""
        with patch.dict(os.environ, {
            "APP_ENV": "development",
            "VEC_PROVIDER": "pinecone",
            "PINECONE_API_KEY": "test-key"
        }, clear=True):
            with patch('app.core.config.get_environment', return_value=Environment.DEVELOPMENT):
                from app.services.vector_provider_factory import VectorProviderFactory
                
                factory = VectorProviderFactory()
                provider_type = factory.select_provider_type()
                
                assert provider_type == "pinecone"
    
    def test_provider_selection_staging_uses_pinecone_when_keys_present(self):
        """Staging uses pinecone when API keys are present."""
        with patch.dict(os.environ, {
            "APP_ENV": "staging",
            "PINECONE_API_KEY": "staging-key"
        }, clear=True):
            with patch('app.core.config.get_environment', return_value=Environment.STAGING):
                from app.services.vector_provider_factory import VectorProviderFactory
                
                factory = VectorProviderFactory()
                provider_type = factory.select_provider_type()
                
                assert provider_type == "pinecone"
    
    def test_provider_selection_staging_defaults_local_without_keys(self):
        """Staging defaults to local when Pinecone keys are missing."""
        with patch.dict(os.environ, {"APP_ENV": "staging"}, clear=True):
            with patch('app.core.config.get_environment', return_value=Environment.STAGING):
                from app.services.vector_provider_factory import VectorProviderFactory
                
                factory = VectorProviderFactory()
                provider_type = factory.select_provider_type()
                
                assert provider_type == "local"
    
    def test_provider_selection_preprod_requires_pinecone_or_fallback(self):
        """Preprod requires pinecone but can fallback with warning."""
        with patch.dict(os.environ, {
            "APP_ENV": "production",  # Will be mapped to preprod logic
            "PINECONE_API_KEY": "preprod-key"
        }, clear=True):
            with patch('app.core.config.get_environment', return_value=Environment.PRODUCTION):
                from app.services.vector_provider_factory import VectorProviderFactory
                
                factory = VectorProviderFactory()
                provider_type = factory.select_provider_type()
                
                assert provider_type == "pinecone"


class TestConfigResolution:
    """Test configuration resolution and validation."""
    
    def test_builds_index_name_from_embedder_dim_or_slug(self):
        """Index name should be built from embedding dimensions."""
        from app.services.vector_provider_factory import VectorProviderFactory
        
        factory = VectorProviderFactory()
        
        # Test with dimension
        index_name = factory.build_index_name(embedding_dimension=384)
        assert index_name == "pratikoai-embed-384"
        
        # Test with different dimension
        index_name = factory.build_index_name(embedding_dimension=768)
        assert index_name == "pratikoai-embed-768"
    
    def test_builds_namespace_with_env_and_domain(self):
        """Namespace should include environment, domain, and tenant."""
        from app.services.vector_provider_factory import VectorProviderFactory
        
        factory = VectorProviderFactory()
        
        namespace = factory.build_namespace(
            env="dev",
            domain="fiscale", 
            tenant="default"
        )
        
        assert namespace == "env=dev,domain=fiscale,tenant=default"
    
    def test_builds_namespace_with_different_domains(self):
        """Test namespace building with different domain types."""
        from app.services.vector_provider_factory import VectorProviderFactory
        
        factory = VectorProviderFactory()
        
        # Test different domains
        domains = ["ccnl", "fiscale", "legale", "lavoro"]
        
        for domain in domains:
            namespace = factory.build_namespace(
                env="staging",
                domain=domain,
                tenant="default"
            )
            assert f"domain={domain}" in namespace
            assert "env=staging" in namespace
            assert "tenant=default" in namespace


class TestEmbedderCompatibility:
    """Test embedding model dimension compatibility validation."""
    
    def test_embedder_dimension_mismatch_triggers_error_path(self):
        """Dimension mismatch should trigger error path when strict mode enabled."""
        with patch.dict(os.environ, {"VECTOR_STRICT_EMBEDDER_MATCH": "true"}, clear=True):
            from app.services.vector_provider_factory import VectorProviderFactory
            
            factory = VectorProviderFactory()
            
            # Mock embedding model with different dimension
            mock_model = Mock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            
            # Mock provider with different index dimension
            mock_provider = Mock()
            mock_provider.get_index_dimension.return_value = 768
            
            # Should raise ValueError in strict mode
            with pytest.raises(ValueError, match="Dimension mismatch"):
                factory.validate_embedder_compatibility(mock_provider, mock_model)
    
    def test_embedder_dimension_mismatch_warns_in_permissive_mode(self):
        """Dimension mismatch should warn but continue in permissive mode."""
        with patch.dict(os.environ, {"VECTOR_STRICT_EMBEDDER_MATCH": "false"}, clear=True):
            with patch('app.core.logging.logger') as mock_logger:
                from app.services.vector_provider_factory import VectorProviderFactory
                
                factory = VectorProviderFactory()
                
                # Mock embedding model
                mock_model = Mock()
                mock_model.get_sentence_embedding_dimension.return_value = 384
                
                # Mock provider with different dimension
                mock_provider = Mock()
                mock_provider.get_index_dimension.return_value = 768
                
                # Should not raise, but should warn
                factory.validate_embedder_compatibility(mock_provider, mock_model)
                
                # Verify warning was logged
                mock_logger.warning.assert_called_once()
                args = mock_logger.warning.call_args[0]
                assert "embedder_dimension_mismatch_permissive" in args[0]


class TestFallbackBehavior:
    """Test fallback behavior when Pinecone is unavailable."""
    
    @patch('app.services.vector_providers.pinecone_provider.Pinecone')
    def test_pinecone_unavailable_falls_back_to_local_and_logs_warn(self, mock_pinecone):
        """Should fallback to local provider when Pinecone initialization fails."""
        # Mock Pinecone initialization failure
        mock_pinecone.side_effect = Exception("API connection failed")
        
        with patch('app.core.logging.logger') as mock_logger:
            from app.services.vector_provider_factory import VectorProviderFactory
            
            factory = VectorProviderFactory()
            
            # Set up environment for Pinecone preference
            with patch.dict(os.environ, {
                "VEC_PROVIDER": "pinecone",
                "PINECONE_API_KEY": "test-key"
            }):
                provider = factory.get_provider(Environment.STAGING)
                
                # Should get local provider due to fallback
                assert provider.__class__.__name__ == "LocalVectorProvider"
                
                # Should have logged warning about fallback
                mock_logger.warning.assert_called()
                warning_calls = [call for call in mock_logger.warning.call_args_list 
                               if "falling_back_to_local_provider" in str(call)]
                assert len(warning_calls) > 0
    
    @patch('app.services.vector_providers.pinecone_provider.Pinecone')
    def test_pinecone_failure_in_production_with_strict_mode(self, mock_pinecone):
        """Production environment with strict mode should abort on Pinecone failure."""
        # Mock Pinecone initialization failure
        mock_pinecone.side_effect = Exception("API connection failed")
        
        from app.services.vector_provider_factory import VectorProviderFactory
        
        factory = VectorProviderFactory()
        
        with patch.dict(os.environ, {
            "APP_ENV": "production",
            "PINECONE_API_KEY": "prod-key",
            "VECTOR_STRICT_MODE": "true"
        }):
            # Should raise RuntimeError in strict mode for production
            with pytest.raises(RuntimeError, match="Pinecone required for production"):
                factory.get_provider(Environment.PRODUCTION)


class TestAdapterContracts:
    """Test that adapters implement expected contracts."""
    
    def test_upsert_calls_adapter_with_ids_vectors_metadata(self):
        """Upsert should call adapter with correct parameters."""
        from app.services.vector_providers.local_provider import LocalVectorProvider
        
        provider = LocalVectorProvider()
        
        # Mock the underlying storage
        with patch.object(provider, '_upsert_vectors') as mock_upsert:
            test_data = [
                {
                    "id": "doc-1",
                    "vector": [0.1, 0.2, 0.3],
                    "metadata": {"source": "test", "domain": "fiscale"}
                }
            ]
            
            provider.upsert(test_data)
            
            # Verify upsert was called with correct structure
            mock_upsert.assert_called_once()
            call_args = mock_upsert.call_args[0][0]
            
            assert len(call_args) == 1
            assert call_args[0]["id"] == "doc-1"
            assert call_args[0]["vector"] == [0.1, 0.2, 0.3]
            assert call_args[0]["metadata"]["domain"] == "fiscale"
    
    def test_query_returns_hits_with_scores_and_metadata(self):
        """Query should return hits with scores and metadata."""
        from app.services.vector_providers.local_provider import LocalVectorProvider
        
        provider = LocalVectorProvider()
        
        # Mock query response
        mock_response = [
            {
                "id": "doc-1",
                "score": 0.95,
                "metadata": {"source": "test", "title": "Test Document"}
            }
        ]
        
        with patch.object(provider, '_query_vectors', return_value=mock_response):
            results = provider.query(
                vector=[0.1, 0.2, 0.3],
                top_k=5,
                namespace="env=dev,domain=fiscale,tenant=default"
            )
            
            assert len(results) == 1
            assert results[0]["id"] == "doc-1"
            assert results[0]["score"] == 0.95
            assert "metadata" in results[0]
            assert results[0]["metadata"]["title"] == "Test Document"


class TestPipelineIntegration:
    """Test integration with search pipeline (lightly mocked)."""
    
    @patch('app.services.search_service.VectorProviderFactory')
    def test_search_service_uses_selected_adapter_based_on_env(self, mock_factory):
        """Search service should use provider selected by factory."""
        # Mock provider factory
        mock_provider = Mock()
        mock_factory.return_value.get_provider.return_value = mock_provider
        
        from app.services.search_service import SearchService
        
        # Initialize search service
        search_service = SearchService()
        
        # Verify it uses the factory to get provider
        mock_factory.return_value.get_provider.assert_called_once()
        
        # Verify search service stores the provider
        assert search_service.vector_provider == mock_provider
    
    @patch('app.services.search_service.VectorProviderFactory')
    def test_ccnl_search_returns_hits_after_upsert_mock(self, mock_factory):
        """CCNL search should return results after upserting documents."""
        # Mock vector provider
        mock_provider = Mock()
        mock_provider.query.return_value = [
            {
                "id": "ccnl-1",
                "score": 0.85,
                "metadata": {
                    "domain": "ccnl",
                    "title": "Contratto Metalmeccanici",
                    "article": "Art. 15"
                }
            }
        ]
        mock_factory.return_value.get_provider.return_value = mock_provider
        
        from app.services.search_service import SearchService
        
        search_service = SearchService()
        
        # Mock upsert of CCNL documents
        ccnl_docs = [
            {
                "id": "ccnl-1",
                "text": "Articolo 15 - Orario di lavoro",
                "metadata": {"domain": "ccnl", "contract": "metalmeccanici"}
            }
        ]
        
        # Upsert documents
        search_service.upsert_documents(ccnl_docs)
        
        # Query for CCNL content
        results = search_service.semantic_search(
            query="orario lavoro", 
            domain="ccnl",
            limit=10
        )
        
        # Verify results
        assert len(results) == 1
        assert results[0]["metadata"]["domain"] == "ccnl"
        assert "Contratto Metalmeccanici" in results[0]["metadata"]["title"]
        
        # Verify provider methods were called
        mock_provider.upsert.assert_called_once()
        mock_provider.query.assert_called_once()


# Test configuration and fixtures
@pytest.fixture
def mock_environment():
    """Fixture to provide clean environment for each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_logger():
    """Fixture to provide mocked logger."""
    with patch('app.core.logging.logger') as mock_logger:
        yield mock_logger


# Integration with existing test structure
if __name__ == "__main__":
    pytest.main([__file__, "-v"])