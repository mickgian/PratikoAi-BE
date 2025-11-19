"""Vector search providers package.

Contains implementations for different vector search backends including
PostgreSQL + pgvector and local in-memory storage.

Note: Pinecone provider removed as part of DEV-BE-68.
"""

from .local_provider import LocalVectorProvider

__all__ = ["LocalVectorProvider"]
