"""Tests for VectorService deprecated stub.

Validates that the VectorService stub correctly raises NotImplementedError
on all methods and that the module-level singleton exists.
"""

import pytest

from app.services.vector_service import VectorService, vector_service


class TestVectorServiceInit:
    """Tests for VectorService constructor."""

    def test_constructor_sets_attributes_to_none(self):
        """VectorService.__init__ sets pinecone_client, index, embedding_model to None."""
        svc = VectorService()
        assert svc.pinecone_client is None
        assert svc.index is None
        assert svc.embedding_model is None

    def test_constructor_logs_deprecation_warning(self):
        """VectorService.__init__ logs a deprecation warning."""
        from unittest.mock import patch

        with patch("app.services.vector_service.logger") as mock_logger:
            VectorService()
            mock_logger.warning.assert_called_once_with(
                "vector_service_deprecated",
                message="VectorService is deprecated. Use PostgreSQL + pgvector instead.",
                migration_guide="See DEV-BE-67 for migration to pgvector",
            )


class TestVectorServiceInitializeMethods:
    """Tests for the deprecated no-op initialization methods."""

    def test_initialize_pinecone_is_noop(self):
        """_initialize_pinecone does nothing and returns None."""
        svc = VectorService()
        result = svc._initialize_pinecone()
        assert result is None

    def test_initialize_embedding_model_is_noop(self):
        """_initialize_embedding_model does nothing and returns None."""
        svc = VectorService()
        result = svc._initialize_embedding_model()
        assert result is None


class TestVectorServiceDeprecatedMethods:
    """Tests for deprecated methods that raise NotImplementedError."""

    def test_upsert_vectors_raises_not_implemented(self):
        svc = VectorService()
        with pytest.raises(NotImplementedError, match="upsert_vectors is deprecated"):
            svc.upsert_vectors()

    def test_upsert_vectors_raises_with_args(self):
        svc = VectorService()
        with pytest.raises(NotImplementedError):
            svc.upsert_vectors([1, 2, 3], namespace="test")

    def test_query_vectors_raises_not_implemented(self):
        svc = VectorService()
        with pytest.raises(NotImplementedError, match="query_vectors is deprecated"):
            svc.query_vectors()

    def test_query_vectors_raises_with_args(self):
        svc = VectorService()
        with pytest.raises(NotImplementedError):
            svc.query_vectors("some query", top_k=10)

    def test_search_similar_raises_not_implemented(self):
        svc = VectorService()
        with pytest.raises(NotImplementedError, match="search_similar is deprecated"):
            svc.search_similar()

    def test_search_similar_raises_with_args(self):
        svc = VectorService()
        with pytest.raises(NotImplementedError):
            svc.search_similar("text", threshold=0.8)


class TestVectorServiceSingleton:
    """Tests for the module-level singleton."""

    def test_vector_service_singleton_exists(self):
        assert vector_service is not None

    def test_vector_service_singleton_is_vector_service_instance(self):
        assert isinstance(vector_service, VectorService)

    def test_vector_service_singleton_has_none_attributes(self):
        assert vector_service.pinecone_client is None
        assert vector_service.index is None
        assert vector_service.embedding_model is None
