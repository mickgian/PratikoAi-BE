"""
Test vector search fallback behavior and error handling.

This module tests graceful degradation when Pinecone is unavailable,
network timeouts, API errors, and other failure scenarios.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock, side_effect
from requests.exceptions import ConnectionError, Timeout, HTTPError

from app.core.config import Environment


class TestPineconeFallbackScenarios:
    """Test fallback behavior when Pinecone is unavailable."""
    
    @patch('app.services.vector_providers.pinecone_provider.Pinecone')
    def test_pinecone_api_connection_failure(self, mock_pinecone_class):
        """Test fallback when Pinecone API connection fails during initialization."""
        # Mock Pinecone constructor to raise connection error
        mock_pinecone_class.side_effect = ConnectionError("Unable to connect to Pinecone API")
        
        with patch('app.core.logging.logger') as mock_logger:
            from app.services.vector_provider_factory import VectorProviderFactory
            
            factory = VectorProviderFactory()
            
            with patch.dict(os.environ, {
                "APP_ENV": "staging",
                "VEC_PROVIDER": "pinecone",
                "PINECONE_API_KEY": "test-key"
            }):
                provider = factory.get_provider(Environment.STAGING)
                
                # Should fallback to local provider
                assert provider.__class__.__name__ == "LocalVectorProvider"
                
                # Should log the error and fallback
                mock_logger.error.assert_called()
                mock_logger.warning.assert_called_with("falling_back_to_local_provider")
    
    @patch('app.services.vector_providers.pinecone_provider.Pinecone')
    def test_pinecone_api_timeout(self, mock_pinecone_class):
        """Test fallback when Pinecone API times out."""
        mock_pinecone_class.side_effect = Timeout("Pinecone API timeout")
        
        with patch('app.core.logging.logger') as mock_logger:
            from app.services.vector_provider_factory import VectorProviderFactory
            
            factory = VectorProviderFactory()
            
            with patch.dict(os.environ, {
                "APP_ENV": "development", 
                "VEC_PROVIDER": "pinecone",
                "PINECONE_API_KEY": "test-key"
            }):
                provider = factory.get_provider(Environment.DEVELOPMENT)
                
                # Should fallback to local
                assert provider.__class__.__name__ == "LocalVectorProvider"
                
                # Should log timeout error
                error_calls = mock_logger.error.call_args_list
                assert any("timeout" in str(call).lower() for call in error_calls)
    
    @patch('app.services.vector_providers.pinecone_provider.PineconeProvider')
    def test_pinecone_index_creation_failure(self, mock_provider_class):
        """Test fallback when Pinecone index creation fails."""
        # Mock provider initialization to fail during index creation
        mock_provider = Mock()
        mock_provider_class.side_effect = Exception("Failed to create index: quota exceeded")
        
        with patch('app.core.logging.logger') as mock_logger:
            from app.services.vector_provider_factory import VectorProviderFactory
            
            factory = VectorProviderFactory()
            
            with patch.dict(os.environ, {
                "APP_ENV": "staging",
                "PINECONE_API_KEY": "staging-key"
            }):
                provider = factory.get_provider(Environment.STAGING)
                
                # Should fallback to local provider
                assert provider.__class__.__name__ == "LocalVectorProvider"
                
                # Should log quota/creation error
                mock_logger.error.assert_called()
                error_message = str(mock_logger.error.call_args)
                assert "quota exceeded" in error_message
    
    def test_pinecone_missing_api_key_fallback(self):
        """Test fallback when Pinecone API key is missing."""
        with patch('app.core.logging.logger') as mock_logger:
            from app.services.vector_provider_factory import VectorProviderFactory
            
            factory = VectorProviderFactory()
            
            with patch.dict(os.environ, {
                "APP_ENV": "staging",
                "VEC_PROVIDER": "pinecone"
                # PINECONE_API_KEY intentionally missing
            }, clear=True):
                provider = factory.get_provider(Environment.STAGING)
                
                # Should fallback to local provider  
                assert provider.__class__.__name__ == "LocalVectorProvider"
                
                # Should log warning about missing API key
                mock_logger.warning.assert_called()
                warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
                assert any("api_key" in call.lower() for call in warning_calls)


class TestStrictModeErrorHandling:
    """Test error handling in strict mode vs permissive mode."""
    
    @patch('app.services.vector_providers.pinecone_provider.Pinecone')
    def test_production_strict_mode_prevents_fallback(self, mock_pinecone):
        """Production with strict mode should prevent fallback and raise error."""
        mock_pinecone.side_effect = Exception("Pinecone unavailable")
        
        from app.services.vector_provider_factory import VectorProviderFactory
        
        factory = VectorProviderFactory()
        
        with patch.dict(os.environ, {
            "APP_ENV": "production",
            "PINECONE_API_KEY": "prod-key",
            "VECTOR_STRICT_MODE": "true"
        }):
            # Should raise RuntimeError instead of falling back
            with pytest.raises(RuntimeError, match="Pinecone required for production"):
                factory.get_provider(Environment.PRODUCTION)
    
    @patch('app.services.vector_providers.pinecone_provider.Pinecone')
    def test_production_permissive_mode_allows_fallback(self, mock_pinecone):
        """Production with permissive mode should allow fallback with error log."""
        mock_pinecone.side_effect = Exception("Pinecone unavailable")
        
        with patch('app.core.logging.logger') as mock_logger:
            from app.services.vector_provider_factory import VectorProviderFactory
            
            factory = VectorProviderFactory()
            
            with patch.dict(os.environ, {
                "APP_ENV": "production",
                "PINECONE_API_KEY": "prod-key",
                "VECTOR_STRICT_MODE": "false"
            }):
                provider = factory.get_provider(Environment.PRODUCTION)
                
                # Should fallback to local provider
                assert provider.__class__.__name__ == "LocalVectorProvider"
                
                # Should log error but continue
                mock_logger.error.assert_called()
                mock_logger.warning.assert_called()


class TestGradualDegradation:
    """Test gradual service degradation scenarios."""
    
    @patch('app.services.vector_providers.pinecone_provider.PineconeProvider')
    def test_pinecone_query_failure_with_local_fallback(self, mock_provider_class):
        """Test query fallback when Pinecone query fails but initialization succeeded."""
        # Mock provider that initializes but fails on query
        mock_provider = Mock()
        mock_provider.query.side_effect = Exception("Query timeout")
        mock_provider_class.return_value = mock_provider
        
        with patch('app.core.logging.logger') as mock_logger:
            from app.services.search_service import SearchService
            
            with patch.dict(os.environ, {
                "VEC_PROVIDER": "pinecone",
                "PINECONE_API_KEY": "test-key"
            }):
                search_service = SearchService()
                
                # Mock local fallback
                with patch.object(search_service, '_local_search') as mock_local:
                    mock_local.return_value = [{"id": "local-1", "score": 0.8}]
                    
                    results = search_service.semantic_search("test query")
                    
                    # Should get results from local fallback
                    assert len(results) == 1
                    assert results[0]["id"] == "local-1"
                    
                    # Should have attempted Pinecone first
                    mock_provider.query.assert_called_once()
                    
                    # Should have logged the fallback
                    mock_logger.warning.assert_called()
    
    def test_embedding_model_failure_fallback(self):
        """Test fallback when embedding model fails to load."""
        with patch('sentence_transformers.SentenceTransformer') as mock_transformer:
            mock_transformer.side_effect = Exception("Model download failed")
            
            with patch('app.core.logging.logger') as mock_logger:
                from app.services.vector_provider_factory import VectorProviderFactory
                
                factory = VectorProviderFactory()
                
                with patch.dict(os.environ, {"VEC_PROVIDER": "local"}):
                    # Should still create provider but without embeddings
                    provider = factory.get_provider(Environment.DEVELOPMENT)
                    
                    assert provider is not None
                    
                    # Should log embedding model failure
                    mock_logger.error.assert_called()
                    error_calls = [str(call) for call in mock_logger.error.call_args_list]
                    assert any("embedding" in call.lower() for call in error_calls)


class TestNetworkResilienceScenarios:
    """Test resilience to various network conditions."""
    
    @patch('requests.get')
    def test_pinecone_network_intermittent_failure(self, mock_requests):
        """Test behavior with intermittent network failures."""
        # Mock intermittent failures (fail first 2 calls, succeed on 3rd)
        mock_requests.side_effect = [
            ConnectionError("Network unreachable"),
            Timeout("Connection timeout"), 
            Mock(status_code=200, json=lambda: {"status": "ok"})
        ]
        
        with patch('app.core.logging.logger') as mock_logger:
            from app.services.vector_providers.pinecone_provider import PineconeProvider
            
            # Mock retry logic
            with patch.object(PineconeProvider, '_retry_with_backoff') as mock_retry:
                mock_retry.return_value = True  # Simulate eventual success
                
                provider = PineconeProvider()
                
                # Should eventually succeed with retries
                assert provider is not None
                
                # Should log retry attempts
                mock_logger.warning.assert_called()
    
    def test_pinecone_rate_limiting_handling(self):
        """Test handling of Pinecone API rate limiting."""
        with patch('app.services.vector_providers.pinecone_provider.Pinecone') as mock_pinecone:
            # Mock rate limiting error
            rate_limit_error = HTTPError("429 Too Many Requests")
            rate_limit_error.response = Mock(status_code=429)
            mock_pinecone.return_value.Index.return_value.query.side_effect = rate_limit_error
            
            with patch('app.core.logging.logger') as mock_logger:
                from app.services.vector_provider_factory import VectorProviderFactory
                
                factory = VectorProviderFactory()
                
                with patch.dict(os.environ, {
                    "VEC_PROVIDER": "pinecone",
                    "PINECONE_API_KEY": "test-key"
                }):
                    provider = factory.get_provider(Environment.DEVELOPMENT)
                    
                    # Should handle rate limiting gracefully
                    with patch.object(provider, '_handle_rate_limit') as mock_handler:
                        mock_handler.return_value = []  # Empty results
                        
                        results = provider.query([0.1, 0.2, 0.3], top_k=5)
                        
                        # Should get empty results instead of crashing
                        assert results == []
                        
                        # Should log rate limiting
                        mock_logger.warning.assert_called()


class TestMetricsAndObservability:
    """Test that failures are properly tracked in metrics."""
    
    @patch('app.services.vector_providers.pinecone_provider.Pinecone')
    def test_pinecone_failure_metrics_recorded(self, mock_pinecone):
        """Test that Pinecone failures are recorded in metrics."""
        mock_pinecone.side_effect = ConnectionError("API unreachable")
        
        with patch('app.core.metrics') as mock_metrics:
            from app.services.vector_provider_factory import VectorProviderFactory
            
            factory = VectorProviderFactory()
            
            with patch.dict(os.environ, {
                "VEC_PROVIDER": "pinecone",
                "PINECONE_API_KEY": "test-key"
            }):
                provider = factory.get_provider(Environment.DEVELOPMENT)
                
                # Should record failure metric
                mock_metrics.pinecone_api_errors_total.inc.assert_called_with(
                    labels={"error_type": "connection_error"}
                )
                
                # Should record fallback metric
                mock_metrics.vector_provider_active.set.assert_called_with(
                    1, labels={"provider": "local"}
                )
    
    def test_fallback_duration_metrics(self):
        """Test that fallback duration is tracked."""
        with patch('time.time', side_effect=[1000.0, 1002.5]):  # 2.5 second fallback
            with patch('app.core.metrics') as mock_metrics:
                from app.services.vector_provider_factory import VectorProviderFactory
                
                factory = VectorProviderFactory()
                
                with patch.dict(os.environ, {"VEC_PROVIDER": "local"}):
                    provider = factory.get_provider(Environment.DEVELOPMENT)
                    
                    # Should record fallback timing
                    mock_metrics.vector_fallback_duration.observe.assert_called_with(2.5)


class TestCascadingFailureScenarios:
    """Test handling of cascading failures."""
    
    @patch('app.services.vector_providers.pinecone_provider.Pinecone')
    @patch('app.services.vector_providers.local_provider.LocalVectorProvider')
    def test_both_providers_fail_graceful_degradation(self, mock_local, mock_pinecone):
        """Test graceful degradation when both providers fail."""
        # Both providers fail
        mock_pinecone.side_effect = Exception("Pinecone unavailable")
        mock_local.side_effect = Exception("Local storage corrupted")
        
        with patch('app.core.logging.logger') as mock_logger:
            from app.services.search_service import SearchService
            
            search_service = SearchService()
            
            # Should handle gracefully and return BM25-only results
            with patch.object(search_service, '_bm25_search') as mock_bm25:
                mock_bm25.return_value = [{"id": "bm25-1", "score": 0.6}]
                
                results = search_service.semantic_search("test query")
                
                # Should get BM25 results as final fallback
                assert len(results) == 1
                assert results[0]["id"] == "bm25-1"
                
                # Should log cascading failure
                mock_logger.error.assert_called()
                error_calls = [str(call) for call in mock_logger.error.call_args_list]
                assert any("cascading" in call.lower() for call in error_calls)


# Test fixtures
@pytest.fixture
def mock_metrics():
    """Fixture providing mocked metrics."""
    with patch('app.core.metrics') as mock_metrics:
        yield mock_metrics


@pytest.fixture  
def network_failure_scenarios():
    """Fixture providing various network failure scenarios."""
    return {
        "connection_error": ConnectionError("Network unreachable"),
        "timeout": Timeout("Request timeout"),
        "http_error": HTTPError("HTTP 500 Internal Server Error"),
        "dns_error": ConnectionError("DNS resolution failed")
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])