"""Vector database service - DEPRECATED (DEV-BE-68).

This service was removed as part of Pinecone removal.
Vector operations are now handled by PostgreSQL + pgvector.

This stub remains to prevent import errors. Services should migrate to:
- app/retrieval/postgres_retriever.py for hybrid search
- app/core/embed.py for embedding generation
"""

from app.core.logging import logger


class VectorService:
    """DEPRECATED: Pinecone-based vector service (removed in DEV-BE-68)."""

    def __init__(self):
        """Initialize deprecated vector service stub."""
        logger.warning(
            "vector_service_deprecated",
            message="VectorService is deprecated. Use PostgreSQL + pgvector instead.",
            migration_guide="See DEV-BE-67 for migration to pgvector",
        )
        self.pinecone_client = None
        self.index = None
        self.embedding_model = None

    def _initialize_pinecone(self):
        """DEPRECATED: Pinecone initialization removed."""
        pass

    def _initialize_embedding_model(self):
        """DEPRECATED: Use app.core.embed.get_embedding() instead."""
        pass

    def upsert_vectors(self, *args, **kwargs):
        """DEPRECATED: Use PostgreSQL knowledge_chunks table instead."""
        logger.error("vector_service_deprecated_method", method="upsert_vectors")
        raise NotImplementedError(
            "VectorService.upsert_vectors is deprecated. " "Use PostgreSQL knowledge_chunks table with pgvector."
        )

    def query_vectors(self, *args, **kwargs):
        """DEPRECATED: Use app.retrieval.postgres_retriever.PostgresRetriever instead."""
        logger.error("vector_service_deprecated_method", method="query_vectors")
        raise NotImplementedError(
            "VectorService.query_vectors is deprecated. " "Use PostgresRetriever.hybrid_search() instead."
        )

    def search_similar(self, *args, **kwargs):
        """DEPRECATED: Use PostgresRetriever.hybrid_search() instead."""
        logger.error("vector_service_deprecated_method", method="search_similar")
        raise NotImplementedError(
            "VectorService.search_similar is deprecated. " "Use PostgresRetriever.hybrid_search() instead."
        )


# Global instance for backward compatibility
vector_service = VectorService()
