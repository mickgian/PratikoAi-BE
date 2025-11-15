"""Pinecone vector search provider implementation.

Provides vector search capabilities using Pinecone cloud service with
environment-aware configuration and error handling.
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from pinecone import Pinecone, ServerlessSpec

    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False

from app.core.logging import logger


class PineconeProvider:
    """Pinecone vector search provider."""

    def __init__(
        self,
        api_key: str,
        environment: str = "serverless",
        index_name: str = None,
        dimension: int = 384,
        namespace_prefix: str = "env=",
    ):
        """Initialize Pinecone provider."""
        if not PINECONE_AVAILABLE:
            raise ImportError("Pinecone package not available")

        self.api_key = api_key
        self.environment = environment
        self.index_name = index_name
        self.dimension = dimension
        self.namespace_prefix = namespace_prefix

        self.client = None
        self.index = None

        self._initialize_client()
        self._initialize_index()

        logger.info(
            "pinecone_provider_initialized",
            index_name=self.index_name,
            dimension=self.dimension,
            environment=self.environment,
        )

    def _initialize_client(self):
        """Initialize Pinecone client."""
        try:
            self.client = Pinecone(api_key=self.api_key)
            logger.debug("pinecone_client_initialized")
        except Exception as e:
            logger.error("pinecone_client_init_failed", error=str(e))
            raise

    def _initialize_index(self):
        """Initialize or create Pinecone index."""
        try:
            existing_indexes = self.client.list_indexes().names()

            if self.index_name not in existing_indexes:
                logger.info("creating_pinecone_index", index_name=self.index_name, dimension=self.dimension)

                # Create serverless index
                self.client.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                )

                # Wait for index to be ready
                self._wait_for_index_ready()

            # Connect to index
            self.index = self.client.Index(self.index_name)

            logger.info("pinecone_index_ready", index_name=self.index_name)

        except Exception as e:
            logger.error("pinecone_index_init_failed", error=str(e), index_name=self.index_name)
            raise

    def _wait_for_index_ready(self, max_wait_time: int = 60):
        """Wait for index to be ready after creation."""
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            try:
                desc = self.client.describe_index(self.index_name)
                if desc.status.ready:
                    logger.debug("pinecone_index_ready_confirmed", index_name=self.index_name)
                    return

                logger.debug("pinecone_index_initializing", index_name=self.index_name, status=desc.status.state)
                time.sleep(2)

            except Exception as e:
                logger.warning("pinecone_index_status_check_failed", error=str(e))
                time.sleep(5)

        logger.warning("pinecone_index_ready_timeout", index_name=self.index_name, wait_time=max_wait_time)

    def upsert(self, vectors: list[dict[str, Any]], namespace: str = None) -> bool:
        """Upsert vectors into Pinecone index."""
        try:
            if not self.index:
                logger.error("pinecone_index_not_available")
                return False

            # Prepare vectors for Pinecone format
            pinecone_vectors = []
            for item in vectors:
                doc_id = item["id"]
                vector = item["vector"]
                metadata = item.get("metadata", {})

                # Add provider metadata
                metadata.update(
                    {"upserted_at": datetime.utcnow().isoformat(), "provider": "pinecone", "dimension": len(vector)}
                )

                pinecone_vectors.append({"id": doc_id, "values": vector, "metadata": metadata})

            # Perform upsert with namespace
            effective_namespace = namespace or f"{self.namespace_prefix}default"

            self.index.upsert(vectors=pinecone_vectors, namespace=effective_namespace)

            logger.debug("pinecone_upsert_complete", count=len(vectors), namespace=effective_namespace)

            return True

        except Exception as e:
            logger.error("pinecone_upsert_failed", error=str(e), count=len(vectors), namespace=namespace)
            return False

    def query(
        self, vector: list[float], top_k: int = 10, namespace: str = None, filter_dict: dict[str, Any] = None
    ) -> list[dict[str, Any]]:
        """Query vectors from Pinecone index."""
        try:
            if not self.index:
                logger.error("pinecone_index_not_available")
                return []

            effective_namespace = namespace or f"{self.namespace_prefix}default"

            # Perform query
            response = self.index.query(
                vector=vector,
                top_k=top_k,
                namespace=effective_namespace,
                filter=filter_dict,
                include_values=False,
                include_metadata=True,
            )

            # Format results
            results = []
            for match in response.matches:
                results.append({"id": match.id, "score": float(match.score), "metadata": match.metadata or {}})

            logger.debug(
                "pinecone_query_complete",
                query_vector_dim=len(vector),
                namespace=effective_namespace,
                results=len(results),
                top_k=top_k,
            )

            return results

        except Exception as e:
            logger.error("pinecone_query_failed", error=str(e), namespace=namespace, top_k=top_k)

            # Record API error metrics if available
            try:
                from app.core.metrics import pinecone_api_errors_total

                pinecone_api_errors_total.inc(labels={"error_type": "query_failed"})
            except ImportError:
                pass

            return []

    def get_index_dimension(self) -> int | None:
        """Get the dimension of the Pinecone index."""
        try:
            if not self.client:
                return self.dimension

            desc = self.client.describe_index(self.index_name)
            return desc.dimension

        except Exception as e:
            logger.warning("pinecone_dimension_check_failed", error=str(e))
            return self.dimension  # Fallback to configured dimension

    def test_connection(self) -> bool:
        """Test Pinecone connection and index accessibility."""
        try:
            if not self.client or not self.index:
                return False

            # Test with a simple query
            test_vector = [0.1] * self.dimension

            # Perform test query (should not fail even with empty index)
            self.index.query(vector=test_vector, top_k=1, namespace=f"{self.namespace_prefix}test")

            logger.debug("pinecone_connection_test_ok")
            return True

        except Exception as e:
            logger.error("pinecone_connection_test_failed", error=str(e))
            return False

    def get_index_stats(self) -> dict[str, Any]:
        """Get Pinecone index statistics."""
        try:
            if not self.index:
                return {"error": "Index not available"}

            stats = self.index.describe_index_stats()

            return {
                "provider": "pinecone",
                "index_name": self.index_name,
                "dimension": self.dimension,
                "total_vector_count": stats.total_vector_count,
                "namespaces": dict(stats.namespaces) if stats.namespaces else {},
                "index_fullness": stats.index_fullness,
            }

        except Exception as e:
            logger.error("pinecone_stats_failed", error=str(e))
            return {"error": str(e)}

    def delete_by_ids(self, ids: list[str], namespace: str = None) -> bool:
        """Delete vectors by IDs."""
        try:
            if not self.index:
                logger.error("pinecone_index_not_available")
                return False

            effective_namespace = namespace or f"{self.namespace_prefix}default"

            self.index.delete(ids=ids, namespace=effective_namespace)

            logger.debug("pinecone_delete_complete", count=len(ids), namespace=effective_namespace)

            return True

        except Exception as e:
            logger.error("pinecone_delete_failed", error=str(e), count=len(ids), namespace=namespace)
            return False

    def delete_namespace(self, namespace: str) -> bool:
        """Delete entire namespace."""
        try:
            if not self.index:
                logger.error("pinecone_index_not_available")
                return False

            self.index.delete(delete_all=True, namespace=namespace)

            logger.info("pinecone_namespace_deleted", namespace=namespace)
            return True

        except Exception as e:
            logger.error("pinecone_namespace_delete_failed", error=str(e), namespace=namespace)
            return False

    def _handle_rate_limit(self, retry_count: int = 3) -> list[dict[str, Any]]:
        """Handle rate limiting with exponential backoff."""
        if retry_count <= 0:
            logger.error("pinecone_rate_limit_exceeded")
            return []

        wait_time = (4 - retry_count) * 2  # Exponential backoff
        logger.warning("pinecone_rate_limited", wait_time=wait_time, retries_left=retry_count)

        time.sleep(wait_time)
        return []  # Return empty for now, could implement retry logic

    def _retry_with_backoff(self, operation, max_retries: int = 3) -> bool:
        """Retry operation with exponential backoff."""
        for attempt in range(max_retries):
            try:
                result = operation()
                return result
            except Exception as e:
                wait_time = (2**attempt) * 0.5  # Exponential backoff
                logger.warning(
                    "pinecone_operation_retry",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    wait_time=wait_time,
                    error=str(e),
                )

                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                else:
                    logger.error("pinecone_operation_failed_after_retries", attempts=max_retries, final_error=str(e))
                    raise

        return False
