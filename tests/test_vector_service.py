"""Tests for vector service functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.vector_service import VectorService, vector_service


class TestVectorService:
    """Test cases for VectorService."""
    
    def test_vector_service_unavailable_when_dependencies_missing(self):
        """Test that vector service reports unavailable when dependencies are missing."""
        with patch('app.services.vector_service.VECTOR_DEPENDENCIES_AVAILABLE', False):
            service = VectorService()
            assert not service.is_available()
            assert service.pinecone_client is None
            assert service.index is None
            assert service.embedding_model is None
    
    def test_vector_service_unavailable_when_no_api_key(self):
        """Test that vector service reports unavailable when API key is missing."""
        with patch('app.services.vector_service.VECTOR_DEPENDENCIES_AVAILABLE', True), \
             patch('app.core.config.settings.PINECONE_API_KEY', ''):
            service = VectorService()
            assert not service.is_available()
    
    @patch('app.services.vector_service.VECTOR_DEPENDENCIES_AVAILABLE', True)
    @patch('app.core.config.settings.PINECONE_API_KEY', 'test-key')
    @patch('app.core.config.settings.PINECONE_INDEX_NAME', 'test-index')
    @patch('app.core.config.settings.VECTOR_DIMENSION', 384)
    @patch('app.core.config.settings.EMBEDDING_MODEL', 'test-model')
    def test_create_embedding_success(self):
        """Test successful embedding creation."""
        mock_embedding_model = Mock()
        mock_embedding_model.encode.return_value.tolist.return_value = [0.1, 0.2, 0.3]
        
        service = VectorService()
        service.embedding_model = mock_embedding_model
        service.pinecone_client = Mock()
        service.index = Mock()
        
        result = service.create_embedding("test text")
        
        assert result == [0.1, 0.2, 0.3]
        mock_embedding_model.encode.assert_called_once_with("test text")
    
    @patch('app.services.vector_service.VECTOR_DEPENDENCIES_AVAILABLE', True)
    @patch('app.core.config.settings.PINECONE_API_KEY', 'test-key')
    def test_create_embedding_empty_text(self):
        """Test embedding creation with empty text."""
        service = VectorService()
        service.embedding_model = Mock()
        service.pinecone_client = Mock()
        service.index = Mock()
        
        result = service.create_embedding("")
        
        assert result is None
    
    @patch('app.services.vector_service.VECTOR_DEPENDENCIES_AVAILABLE', True)
    @patch('app.core.config.settings.PINECONE_API_KEY', 'test-key')
    def test_create_embedding_failure(self):
        """Test embedding creation failure."""
        mock_embedding_model = Mock()
        mock_embedding_model.encode.side_effect = Exception("Model error")
        
        service = VectorService()
        service.embedding_model = mock_embedding_model
        service.pinecone_client = Mock()
        service.index = Mock()
        
        result = service.create_embedding("test text")
        
        assert result is None
    
    @patch('app.services.vector_service.VECTOR_DEPENDENCIES_AVAILABLE', True)
    @patch('app.core.config.settings.PINECONE_API_KEY', 'test-key')
    def test_store_document_success(self):
        """Test successful document storage."""
        mock_embedding_model = Mock()
        mock_embedding_model.encode.return_value.tolist.return_value = [0.1, 0.2, 0.3]
        mock_index = Mock()
        
        service = VectorService()
        service.embedding_model = mock_embedding_model
        service.pinecone_client = Mock()
        service.index = mock_index
        
        result = service.store_document(
            document_id="test-doc",
            text="test content",
            metadata={"type": "test"}
        )
        
        assert result is True
        mock_index.upsert.assert_called_once()
        upsert_args = mock_index.upsert.call_args[1]['vectors']
        assert len(upsert_args) == 1
        assert upsert_args[0][0] == "test-doc"  # document_id
        assert upsert_args[0][1] == [0.1, 0.2, 0.3]  # embedding
        assert "type" in upsert_args[0][2]  # metadata
    
    @patch('app.services.vector_service.VECTOR_DEPENDENCIES_AVAILABLE', True)
    @patch('app.core.config.settings.PINECONE_API_KEY', 'test-key')
    @patch('app.core.config.settings.MAX_SEARCH_RESULTS', 10)
    @patch('app.core.config.settings.VECTOR_SIMILARITY_THRESHOLD', 0.7)
    def test_search_similar_documents_success(self):
        """Test successful similarity search."""
        mock_embedding_model = Mock()
        mock_embedding_model.encode.return_value.tolist.return_value = [0.1, 0.2, 0.3]
        
        mock_match = Mock()
        mock_match.id = "doc-1"
        mock_match.score = 0.85
        mock_match.metadata = {"type": "test", "text": "sample text"}
        
        mock_search_results = Mock()
        mock_search_results.matches = [mock_match]
        
        mock_index = Mock()
        mock_index.query.return_value = mock_search_results
        
        service = VectorService()
        service.embedding_model = mock_embedding_model
        service.pinecone_client = Mock()
        service.index = mock_index
        
        results = service.search_similar_documents("test query")
        
        assert len(results) == 1
        assert results[0]["id"] == "doc-1"
        assert results[0]["score"] == 0.85
        assert results[0]["metadata"]["type"] == "test"
        mock_index.query.assert_called_once()
    
    @patch('app.services.vector_service.VECTOR_DEPENDENCIES_AVAILABLE', True)
    @patch('app.core.config.settings.PINECONE_API_KEY', 'test-key')
    @patch('app.core.config.settings.VECTOR_SIMILARITY_THRESHOLD', 0.7)
    def test_search_similar_documents_low_score_filtered(self):
        """Test that low-score results are filtered out."""
        mock_embedding_model = Mock()
        mock_embedding_model.encode.return_value.tolist.return_value = [0.1, 0.2, 0.3]
        
        mock_low_score_match = Mock()
        mock_low_score_match.id = "doc-1"
        mock_low_score_match.score = 0.5  # Below threshold
        mock_low_score_match.metadata = {"type": "test"}
        
        mock_search_results = Mock()
        mock_search_results.matches = [mock_low_score_match]
        
        mock_index = Mock()
        mock_index.query.return_value = mock_search_results
        
        service = VectorService()
        service.embedding_model = mock_embedding_model
        service.pinecone_client = Mock()
        service.index = mock_index
        
        results = service.search_similar_documents("test query")
        
        assert len(results) == 0  # Low score result filtered out
    
    @patch('app.services.vector_service.VECTOR_DEPENDENCIES_AVAILABLE', True)
    @patch('app.core.config.settings.PINECONE_API_KEY', 'test-key')
    @patch('app.core.config.settings.MAX_SEARCH_RESULTS', 10)
    def test_hybrid_search_semantic_only(self):
        """Test hybrid search with only semantic results."""
        service = VectorService()
        service.embedding_model = Mock()
        service.pinecone_client = Mock()
        service.index = Mock()
        
        # Mock search_similar_documents method
        mock_semantic_results = [
            {"id": "doc-1", "score": 0.9, "metadata": {"type": "test"}}
        ]
        service.search_similar_documents = Mock(return_value=mock_semantic_results)
        
        results = service.hybrid_search("test query")
        
        assert len(results) == 1
        assert results[0]["id"] == "doc-1"
        assert "hybrid_score" in results[0]
        assert results[0]["semantic_score"] == 0.9
        assert results[0]["keyword_score"] == 0.0
    
    @patch('app.services.vector_service.VECTOR_DEPENDENCIES_AVAILABLE', True)
    @patch('app.core.config.settings.PINECONE_API_KEY', 'test-key')
    @patch('app.core.config.settings.MAX_SEARCH_RESULTS', 10)
    def test_hybrid_search_with_keyword_results(self):
        """Test hybrid search combining semantic and keyword results."""
        service = VectorService()
        service.embedding_model = Mock()
        service.pinecone_client = Mock()
        service.index = Mock()
        
        # Mock search_similar_documents method
        mock_semantic_results = [
            {"id": "doc-1", "score": 0.8, "metadata": {"type": "test"}}
        ]
        service.search_similar_documents = Mock(return_value=mock_semantic_results)
        
        keyword_results = [
            {"id": "doc-2", "score": 0.6, "metadata": {"type": "keyword"}}
        ]
        
        results = service.hybrid_search(
            query="test query",
            keyword_results=keyword_results,
            semantic_weight=0.7
        )
        
        assert len(results) == 2
        # Results should be sorted by hybrid_score
        assert all("hybrid_score" in result for result in results)
        assert all("semantic_score" in result for result in results)
        assert all("keyword_score" in result for result in results)
    
    @patch('app.services.vector_service.VECTOR_DEPENDENCIES_AVAILABLE', True)
    @patch('app.core.config.settings.PINECONE_API_KEY', 'test-key')
    def test_store_italian_regulation_success(self):
        """Test storing Italian regulation."""
        service = VectorService()
        service.store_document = Mock(return_value=True)
        
        result = service.store_italian_regulation(
            regulation_id=123,
            title="Test Regulation",
            summary="Test summary",
            full_text="Full regulation text",
            metadata={"year": 2024}
        )
        
        assert result is True
        service.store_document.assert_called_once()
        call_args = service.store_document.call_args
        assert call_args[1]['document_id'] == "regulation_123"
        assert "Test Regulation" in call_args[1]['text']
        assert call_args[1]['metadata']['type'] == "regulation"
        assert call_args[1]['metadata']['regulation_id'] == 123
    
    @patch('app.services.vector_service.VECTOR_DEPENDENCIES_AVAILABLE', True)
    @patch('app.core.config.settings.PINECONE_API_KEY', 'test-key')
    def test_store_tax_rate_info_success(self):
        """Test storing tax rate information."""
        service = VectorService()
        service.store_document = Mock(return_value=True)
        
        result = service.store_tax_rate_info(
            rate_id=456,
            description="Standard VAT rate",
            tax_type="VAT",
            rate_percentage=22.0,
            conditions_text="Applies to most goods and services",
            metadata={"valid_from": "2024-01-01"}
        )
        
        assert result is True
        service.store_document.assert_called_once()
        call_args = service.store_document.call_args
        assert call_args[1]['document_id'] == "tax_rate_456"
        assert "22%" in call_args[1]['text']
        assert call_args[1]['metadata']['type'] == "tax_rate"
        assert call_args[1]['metadata']['rate_percentage'] == 22.0
    
    @patch('app.services.vector_service.VECTOR_DEPENDENCIES_AVAILABLE', True)
    @patch('app.core.config.settings.PINECONE_API_KEY', 'test-key')
    def test_search_italian_knowledge_with_filters(self):
        """Test searching Italian knowledge with type filters."""
        service = VectorService()
        
        mock_results = [
            {
                "id": "regulation_123",
                "score": 0.9,
                "metadata": {
                    "type": "regulation",
                    "title": "Test Regulation",
                    "regulation_id": 123,
                    "authority": "Test Authority"
                }
            }
        ]
        service.search_similar_documents = Mock(return_value=mock_results)
        
        results = service.search_italian_knowledge(
            query="test query",
            knowledge_type="regulation",
            language="italian"
        )
        
        assert len(results) == 1
        assert results[0]["knowledge_type"] == "regulation"
        assert results[0]["regulation_id"] == 123
        assert results[0]["authority"] == "Test Authority"
        
        # Verify search was called with correct filters
        service.search_similar_documents.assert_called_once()
        call_args = service.search_similar_documents.call_args
        assert call_args[1]['filter_metadata']['language'] == "italian"
        assert call_args[1]['filter_metadata']['type'] == "regulation"
    
    @patch('app.services.vector_service.VECTOR_DEPENDENCIES_AVAILABLE', True)
    @patch('app.core.config.settings.PINECONE_API_KEY', 'test-key')
    def test_get_index_stats_success(self):
        """Test getting index statistics."""
        mock_stats = Mock()
        mock_stats.total_vector_count = 1000
        mock_stats.dimension = 384
        mock_stats.index_fullness = 0.1
        mock_stats.namespaces = {}
        
        mock_index = Mock()
        mock_index.describe_index_stats.return_value = mock_stats
        
        service = VectorService()
        service.embedding_model = Mock()
        service.pinecone_client = Mock()
        service.index = mock_index
        
        stats = service.get_index_stats()
        
        assert stats["status"] == "available"
        assert stats["total_vector_count"] == 1000
        assert stats["dimension"] == 384
        assert stats["index_fullness"] == 0.1
    
    def test_get_index_stats_unavailable(self):
        """Test getting index statistics when service is unavailable."""
        service = VectorService()
        # Service is unavailable by default
        
        stats = service.get_index_stats()
        
        assert stats["status"] == "unavailable"
        assert "reason" in stats
    
    @patch('app.services.vector_service.VECTOR_DEPENDENCIES_AVAILABLE', True)
    @patch('app.core.config.settings.PINECONE_API_KEY', 'test-key')
    def test_delete_document_success(self):
        """Test successful document deletion."""
        mock_index = Mock()
        
        service = VectorService()
        service.embedding_model = Mock()
        service.pinecone_client = Mock()
        service.index = mock_index
        
        result = service.delete_document("test-doc-id")
        
        assert result is True
        mock_index.delete.assert_called_once_with(ids=["test-doc-id"])
    
    def test_delete_document_unavailable(self):
        """Test document deletion when service is unavailable."""
        service = VectorService()
        # Service is unavailable by default
        
        result = service.delete_document("test-doc-id")
        
        assert result is False


class TestGlobalVectorService:
    """Test the global vector service instance."""
    
    def test_global_instance_exists(self):
        """Test that global vector service instance exists."""
        assert vector_service is not None
        assert isinstance(vector_service, VectorService)
    
    def test_global_instance_is_singleton(self):
        """Test that importing vector_service returns the same instance."""
        from app.services.vector_service import vector_service as imported_service
        assert vector_service is imported_service


if __name__ == "__main__":
    pytest.main([__file__])