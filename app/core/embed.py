"""Embedding utilities for hybrid RAG.

Generates vector embeddings using configurable OpenAI embedding models.
"""

import os
from typing import (
    List,
    Optional,
    cast,
)

import numpy as np
from openai import AsyncOpenAI

from app.core.config import (
    EMBED_DIM,
    EMBED_MODEL,
)
from app.core.logging import logger

# Initialize OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def generate_embedding(text: str) -> list[float] | None:
    """Generate embedding for a single text.

    Args:
        text: Input text to embed

    Returns:
        1536-d embedding vector, or None if failed
    """
    if not text or not text.strip():
        return None

    try:
        # Truncate text if too long (OpenAI limit is ~8k tokens)
        if len(text) > 30000:  # ~8k tokens
            text = text[:30000]

        response = await client.embeddings.create(model=EMBED_MODEL, input=text)

        embedding = cast(list[float], response.data[0].embedding)
        return embedding

    except Exception as e:
        logger.error("Error generating embedding: %s", e, exc_info=True)
        return None


async def generate_embeddings_batch(texts: list[str], batch_size: int = 20) -> list[list[float] | None]:
    """Generate embeddings for multiple texts in batches.

    Args:
        texts: List of input texts
        batch_size: Number of texts to process per API call

    Returns:
        List of embeddings (1536-d vectors), same length as input
    """
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]

        # Filter empty texts
        batch_texts = [t if t and t.strip() else " " for t in batch]

        try:
            response = await client.embeddings.create(model=EMBED_MODEL, input=batch_texts)

            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

        except Exception as e:
            logger.error("Error generating batch embeddings: %s", e, exc_info=True)
            # Return None for failed batch
            all_embeddings.extend([None] * len(batch))

    return all_embeddings


def embedding_to_pgvector(embedding: list[float]) -> str | None:
    """Convert embedding list to pgvector format.

    Args:
        embedding: 1536-d embedding vector

    Returns:
        String in pgvector format: '[0.1,0.2,...]', or None if empty
    """
    if not embedding:
        return None

    # Convert to string format for pgvector
    return "[" + ",".join(str(x) for x in embedding) + "]"


def pgvector_to_embedding(pgvector_str: str) -> list[float] | None:
    """Convert pgvector string to embedding list.

    Args:
        pgvector_str: String in format '[0.1,0.2,...]'

    Returns:
        List of floats, or None if empty
    """
    if not pgvector_str:
        return None

    # Remove brackets and split
    vector_str = pgvector_str.strip("[]")
    return [float(x) for x in vector_str.split(",")]


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity score (0-1)
    """
    v1 = np.array(vec1)
    v2 = np.array(vec2)

    dot_product = float(np.dot(v1, v2))
    norm1 = float(np.linalg.norm(v1))
    norm2 = float(np.linalg.norm(v2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


async def embed_text_for_storage(text: str) -> str | None:
    """Generate embedding and convert to pgvector format for database storage.

    Args:
        text: Input text

    Returns:
        Embedding in pgvector string format, or None if failed
    """
    embedding = await generate_embedding(text)
    if not embedding:
        return None

    return embedding_to_pgvector(embedding)


def validate_embedding(embedding: list[float]) -> bool:
    """Validate that an embedding is correct.

    Args:
        embedding: Embedding vector to validate

    Returns:
        True if valid
    """
    if not embedding:
        return False

    if len(embedding) != EMBED_DIM:
        return False

    # Check for NaN or inf values
    return not any(np.isnan(x) or np.isinf(x) for x in embedding)
