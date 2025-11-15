"""Vector provider factory with environment-aware selection and fallback logic.

Handles provider instantiation, fallback behavior, and startup validation
for vector search operations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Protocol, runtime_checkable

from app.core.config import Environment
from app.core.logging import logger
from app.services.vector_config import VectorConfig, VectorProvider


@runtime_checkable
class VectorSearchProvider(Protocol):
    """Protocol defining the contract for vector search providers."""

    def upsert(self, vectors: list) -> bool:
        """Upsert vectors into the provider."""
        ...

    def query(self, vector: list, top_k: int = 10, namespace: str = None) -> list:
        """Query vectors from the provider."""
        ...

    def get_index_dimension(self) -> int | None:
        """Get the dimension of the vector index."""
        ...

    def test_connection(self) -> bool:
        """Test connection to the provider."""
        ...


class VectorProviderFactory:
    """Factory for creating vector search providers with fallback logic."""

    def __init__(self, config: VectorConfig | None = None):
        """Initialize factory with configuration."""
        self.config = config or VectorConfig()

    def select_provider_type(self) -> str:
        """Select provider type based on configuration and environment."""
        return self.config.get_provider_preference()

    def build_index_name(self, embedding_dimension: int | None = None) -> str:
        """Build index name from embedding dimension."""
        return self.config.generate_index_name(embedding_dimension)

    def build_namespace(self, env: str, domain: str, tenant: str = "default") -> str:
        """Build namespace with environment, domain, and tenant."""
        return self.config.build_namespace(env, domain, tenant)

    def get_provider(self, environment: Environment) -> VectorSearchProvider:
        """Get vector provider with fallback logic."""
        preferred_provider = self.select_provider_type()

        logger.info("vector_provider_selection", preferred=preferred_provider, environment=environment.value)

        if preferred_provider == VectorProvider.PINECONE:
            try:
                return self._create_pinecone_provider()
            except Exception as e:
                return self._handle_pinecone_failure(e, environment)

        return self._create_local_provider()

    def _create_pinecone_provider(self) -> VectorSearchProvider:
        """Create Pinecone provider with validation."""
        if not self.config.is_pinecone_configured():
            missing = self.config.get_missing_pinecone_config()
            raise ValueError(f"Pinecone configuration missing: {', '.join(missing)}")

        try:
            from app.services.vector_providers.pinecone_provider import PineconeProvider

            provider = PineconeProvider(
                api_key=self.config.pinecone_api_key,
                environment=self.config.pinecone_environment,
                index_name=self.config.get_effective_index_name(),
                dimension=self.config.embedding_dimension,
                namespace_prefix=self.config.namespace_prefix,
            )

            logger.info(
                "pinecone_provider_created",
                index_name=self.config.get_effective_index_name(),
                dimension=self.config.embedding_dimension,
            )

            return provider

        except Exception as e:
            logger.error("pinecone_provider_creation_failed", error=str(e))
            raise

    def _create_local_provider(self) -> VectorSearchProvider:
        """Create local vector provider."""
        try:
            from app.services.vector_providers.local_provider import LocalVectorProvider

            provider = LocalVectorProvider(
                embedding_dimension=self.config.embedding_dimension, embedding_model=self.config.embedding_model
            )

            logger.info(
                "local_provider_created", dimension=self.config.embedding_dimension, model=self.config.embedding_model
            )

            return provider

        except Exception as e:
            logger.error("local_provider_creation_failed", error=str(e))
            raise

    def _handle_pinecone_failure(self, error: Exception, environment: Environment) -> VectorSearchProvider:
        """Handle Pinecone provider creation failure with fallback logic."""
        logger.error("pinecone_initialization_failed", error=str(error), environment=environment.value)

        # Check if fallback is allowed
        if not self.config.allow_fallback():
            if environment == Environment.PRODUCTION and self.config.strict_mode:
                logger.error("pinecone_required_for_production")
                raise RuntimeError("Pinecone required for production")

        # Log fallback decision
        logger.warning("falling_back_to_local_provider", original_error=str(error), environment=environment.value)

        # Record metrics if available
        try:
            from app.core.metrics import pinecone_api_errors_total, vector_provider_active

            pinecone_api_errors_total.inc(labels={"error_type": type(error).__name__.lower()})
            vector_provider_active.set(1, labels={"provider": "local"})
        except ImportError:
            pass  # Metrics not available

        return self._create_local_provider()

    def validate_embedder_compatibility(self, provider: VectorSearchProvider, embedding_model) -> None:
        """Validate embedding model compatibility with provider index."""
        if not hasattr(embedding_model, "get_sentence_embedding_dimension"):
            logger.warning("embedding_model_no_dimension_method")
            return

        if not hasattr(provider, "get_index_dimension"):
            logger.debug("provider_no_dimension_method")
            return

        model_dimension = embedding_model.get_sentence_embedding_dimension()
        index_dimension = provider.get_index_dimension()

        if index_dimension is None:
            logger.debug("provider_index_dimension_unknown")
            return

        if model_dimension != index_dimension:
            error_msg = f"Dimension mismatch: model={model_dimension}, index={index_dimension}"

            if self.config.strict_embedder_match:
                logger.error(
                    "embedder_dimension_mismatch_strict", model_dim=model_dimension, index_dim=index_dimension
                )
                raise ValueError(f"{error_msg}. Reindex required.")
            else:
                logger.warning(
                    "embedder_dimension_mismatch_permissive",
                    model_dim=model_dimension,
                    index_dim=index_dimension,
                    message="Consider reindexing for optimal performance",
                )
        else:
            logger.info("embedder_dimension_compatible", dimension=model_dimension)

    def perform_startup_checks(self, provider: VectorSearchProvider, embedding_model=None) -> dict[str, Any]:
        """Perform comprehensive startup validation checks."""
        checks = {
            "provider_type": type(provider).__name__,
            "configuration": self.config.format_for_logging(),
            "status": "ok",
            "warnings": [],
            "errors": [],
        }

        try:
            # Log startup configuration
            logger.info(
                "vector_search_startup",
                **{
                    "provider": type(provider).__name__,
                    "environment": self.config.environment.value,
                    "index_name": self.config.get_effective_index_name(),
                    "namespace_prefix": f"env={self.config.get_current_namespace_env()}",
                    "embedding_model": self.config.embedding_model,
                    "embedding_dimension": self.config.embedding_dimension,
                },
            )

            # Test provider connection
            if hasattr(provider, "test_connection"):
                try:
                    connection_ok = provider.test_connection()
                    if connection_ok:
                        logger.info("vector_provider_connection_ok")
                    else:
                        logger.warning("vector_provider_connection_degraded")
                        checks["warnings"].append("Provider connection degraded")
                except Exception as e:
                    logger.warning("vector_provider_connection_failed", error=str(e))
                    checks["warnings"].append(f"Connection test failed: {str(e)}")

            # Validate embedder compatibility
            if embedding_model:
                try:
                    self.validate_embedder_compatibility(provider, embedding_model)
                    logger.info("embedder_compatibility_check", status="OK")
                except ValueError as e:
                    logger.error("embedder_compatibility_check", status="FAILED", error=str(e))
                    checks["errors"].append(str(e))
                    checks["status"] = "embedder_mismatch"
                except Exception as e:
                    logger.warning("embedder_compatibility_check", status="WARNING", error=str(e))
                    checks["warnings"].append(f"Embedder check warning: {str(e)}")

            # Log final status
            logger.info(
                "startup_checks_complete",
                provider=type(provider).__name__,
                status=checks["status"],
                warnings=len(checks["warnings"]),
                errors=len(checks["errors"]),
            )

        except Exception as e:
            logger.error("startup_checks_failed", error=str(e))
            checks["status"] = "failed"
            checks["errors"].append(f"Startup check failed: {str(e)}")

        return checks
