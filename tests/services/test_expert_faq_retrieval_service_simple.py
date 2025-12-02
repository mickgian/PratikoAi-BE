"""Simple unit tests for ExpertFAQRetrievalService without full model dependencies.

These tests verify the core service logic without triggering the FAQCandidate
model relationship issues that exist in the test database setup.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.expert_faq_retrieval_service import ExpertFAQRetrievalService


@pytest.mark.asyncio
class TestExpertFAQRetrievalServiceSimple:
    """Simple unit tests for ExpertFAQRetrievalService core functionality."""

    async def test_service_instantiation(self):
        """Test that service can be instantiated with a db_session."""
        mock_session = AsyncMock()
        service = ExpertFAQRetrievalService(mock_session)

        assert service is not None
        assert service.db == mock_session
        assert isinstance(service.embedding_cache, dict)
        assert len(service.embedding_cache) == 0

    async def test_find_matching_faqs_empty_query(self):
        """Test that empty query returns empty results."""
        mock_session = AsyncMock()
        service = ExpertFAQRetrievalService(mock_session)

        # Test empty string
        results = await service.find_matching_faqs("")
        assert results == []

        # Test None (if passed, should handle gracefully)
        results = await service.find_matching_faqs(None)
        assert results == []

        # Test whitespace only
        results = await service.find_matching_faqs("   ")
        assert results == []

    async def test_embedding_cache_works(self):
        """Test that embedding cache stores and retrieves embeddings."""
        mock_session = AsyncMock()
        service = ExpertFAQRetrievalService(mock_session)

        # Mock generate_embedding to return a test embedding
        test_embedding = [0.1] * 1536  # 1536-dimension vector

        with patch("app.services.expert_faq_retrieval_service.generate_embedding") as mock_gen:
            mock_gen.return_value = test_embedding

            # First call should generate embedding
            embedding1 = await service._generate_embedding("test query")
            assert embedding1 == test_embedding
            assert mock_gen.call_count == 1

            # Second call with same text should use cache
            embedding2 = await service._generate_embedding("test query")
            assert embedding2 == test_embedding
            assert mock_gen.call_count == 1  # Still 1, not called again

            # Third call with different text should generate new embedding
            embedding3 = await service._generate_embedding("different query")
            assert embedding3 == test_embedding
            assert mock_gen.call_count == 2  # Now called twice

    async def test_embedding_generation_validates_dimension(self):
        """Test that invalid embedding dimensions are rejected."""
        mock_session = AsyncMock()
        service = ExpertFAQRetrievalService(mock_session)

        # Mock generate_embedding to return wrong dimension
        wrong_embedding = [0.1] * 512  # Wrong dimension (should be 1536)

        with patch("app.services.expert_faq_retrieval_service.generate_embedding") as mock_gen:
            mock_gen.return_value = wrong_embedding

            # Should return None for invalid dimension
            embedding = await service._generate_embedding("test query")
            assert embedding is None

    async def test_embedding_generation_handles_none(self):
        """Test that None from generate_embedding is handled correctly."""
        mock_session = AsyncMock()
        service = ExpertFAQRetrievalService(mock_session)

        with patch("app.services.expert_faq_retrieval_service.generate_embedding") as mock_gen:
            mock_gen.return_value = None

            embedding = await service._generate_embedding("test query")
            assert embedding is None

    async def test_get_by_signature_returns_none(self):
        """Test that signature-based lookup returns None (not yet implemented)."""
        mock_session = AsyncMock()
        service = ExpertFAQRetrievalService(mock_session)

        result = await service.get_by_signature("abc123def456")
        assert result is None

    async def test_find_matching_faqs_handles_embedding_generation_failure(self):
        """Test that find_matching_faqs returns empty list if embedding generation fails."""
        mock_session = AsyncMock()
        service = ExpertFAQRetrievalService(mock_session)

        with patch("app.services.expert_faq_retrieval_service.generate_embedding") as mock_gen:
            mock_gen.return_value = None  # Simulate embedding generation failure

            results = await service.find_matching_faqs("test query")
            assert results == []

    @pytest.mark.skip(reason="Requires question_embedding column on FAQCandidate model - not yet implemented")
    async def test_find_matching_faqs_constructs_correct_query(self):
        """Test that find_matching_faqs constructs the correct SQL query."""
        mock_session = AsyncMock()
        service = ExpertFAQRetrievalService(mock_session)

        # Mock embedding generation
        test_embedding = [0.1] * 1536

        # Mock database query result
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []  # No results
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.expert_faq_retrieval_service.generate_embedding") as mock_gen:
            mock_gen.return_value = test_embedding

            results = await service.find_matching_faqs(query="Cos'è l'IVA?", min_similarity=0.85, max_results=10)

            # Verify query was executed
            assert mock_session.execute.called
            assert results == []

    async def test_service_methods_exist(self):
        """Test that all required service methods exist."""
        mock_session = AsyncMock()
        service = ExpertFAQRetrievalService(mock_session)

        # Check all required methods exist
        assert hasattr(service, "find_matching_faqs")
        assert callable(service.find_matching_faqs)

        assert hasattr(service, "get_by_signature")
        assert callable(service.get_by_signature)

        assert hasattr(service, "_generate_embedding")
        assert callable(service._generate_embedding)
