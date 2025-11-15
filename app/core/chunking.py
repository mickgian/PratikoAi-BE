"""Text chunking utilities for hybrid RAG.

Splits long documents into smaller chunks suitable for:
- Vector embedding (1536-d, ~8k tokens max)
- FTS indexing
- Retrieval

Uses token-based chunking with overlap to preserve context.

Quality gates: Computes quality metrics for each chunk and optionally
drops junk chunks based on JUNK_DROP_CHUNK config.
"""

import logging
import re
from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    List,
)

from app.core.config import (
    CHUNK_OVERLAP,
    CHUNK_TOKENS,
    JUNK_DROP_CHUNK,
)
from app.core.text.extract_pdf import text_metrics

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""

    text: str
    chunk_index: int
    token_count: int
    start_char: int
    end_char: int


def estimate_tokens(text: str) -> int:
    """Estimate token count for text.

    Uses a simple heuristic: ~4 characters per token for Italian text.
    This is approximate but sufficient for chunking.

    Args:
        text: Input text

    Returns:
        Estimated token count
    """
    # Simple estimation: ~4 chars per token
    return len(text) // 4


def chunk_text(text: str, max_tokens: int = None, overlap_tokens: int = None) -> list[TextChunk]:
    """Chunk text into smaller pieces with overlap.

    Args:
        text: Input text to chunk
        max_tokens: Maximum tokens per chunk (defaults to config.CHUNK_TOKENS)
        overlap_tokens: Number of tokens to overlap between chunks (defaults to config.CHUNK_OVERLAP fraction)

    Returns:
        List of TextChunk objects
    """
    if not text or not text.strip():
        return []

    # Use config defaults if not provided
    if max_tokens is None:
        max_tokens = CHUNK_TOKENS

    if overlap_tokens is None:
        # CHUNK_OVERLAP is a fraction (e.g., 0.12 = 12%)
        overlap_tokens = int(max_tokens * CHUNK_OVERLAP)

    # Estimate max characters per chunk
    max_chars = max_tokens * 4
    overlap_chars = overlap_tokens * 4

    # Split text into sentences (Italian-aware)
    sentences = split_into_sentences(text)

    chunks = []
    current_chunk = []
    current_length = 0
    chunk_start = 0

    for sentence in sentences:
        sentence_length = len(sentence)

        # If adding this sentence would exceed max, create a chunk
        if current_length + sentence_length > max_chars and current_chunk:
            # Create chunk
            chunk_content = " ".join(current_chunk)
            chunks.append(
                TextChunk(
                    text=chunk_content,
                    chunk_index=len(chunks),
                    token_count=estimate_tokens(chunk_content),
                    start_char=chunk_start,
                    end_char=chunk_start + len(chunk_content),
                )
            )

            # Start new chunk with overlap
            # Keep last few sentences for context
            overlap_sentences = []
            overlap_length = 0
            for s in reversed(current_chunk):
                if overlap_length + len(s) <= overlap_chars:
                    overlap_sentences.insert(0, s)
                    overlap_length += len(s) + 1
                else:
                    break

            current_chunk = overlap_sentences
            current_length = overlap_length
            chunk_start = chunk_start + len(chunk_content) - overlap_length

        # Add sentence to current chunk
        current_chunk.append(sentence)
        current_length += sentence_length + 1  # +1 for space

    # Add final chunk if any
    if current_chunk:
        chunk_content = " ".join(current_chunk)
        chunks.append(
            TextChunk(
                text=chunk_content,
                chunk_index=len(chunks),
                token_count=estimate_tokens(chunk_content),
                start_char=chunk_start,
                end_char=chunk_start + len(chunk_content),
            )
        )

    return chunks


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences (Italian-aware).

    Args:
        text: Input text

    Returns:
        List of sentences
    """
    # Italian sentence boundaries
    # Handle common abbreviations that shouldn't split sentences
    abbreviations = [
        "art.",
        "artt.",
        "lett.",
        "c.",
        "cc.",
        "n.",
        "nn.",
        "pag.",
        "vol.",
        "cfr.",
        "es.",
        "ecc.",
        "etc.",
        "dott.",
        "prof.",
        "avv.",
        "ing.",
        "dr.",
        "sig.",
        "D.L.",
        "D.Lgs.",
        "L.",
        "D.M.",
        "D.P.R.",
    ]

    # Temporarily replace abbreviations
    protected_text = text
    for i, abbr in enumerate(abbreviations):
        protected_text = protected_text.replace(abbr, f"__ABR{i}__")

    # Split on sentence boundaries
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", protected_text)

    # Restore abbreviations
    restored_sentences = []
    for sentence in sentences:
        for i, abbr in enumerate(abbreviations):
            sentence = sentence.replace(f"__ABR{i}__", abbr)
        restored_sentences.append(sentence.strip())

    # Filter out empty sentences
    return [s for s in restored_sentences if s]


def chunk_document(
    content: str, title: str = "", max_tokens: int = None, overlap_tokens: int = None, ocr_used: bool = False
) -> list[dict[str, Any]]:
    """Chunk a document and prepare for database insertion with quality gates.

    Quality gates:
    - Computes quality_score for each chunk
    - If JUNK_DROP_CHUNK=True and chunk looks like junk, skips it
    - Sets junk=False for kept chunks, ocr_used flag

    Args:
        content: Document text content
        title: Document title (optional)
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Overlap tokens between chunks
        ocr_used: Whether OCR was used for extraction (applied to all chunks)

    Returns:
        List of chunk dictionaries ready for insertion (junk chunks excluded if JUNK_DROP_CHUNK=True)
    """
    chunks = chunk_text(content, max_tokens, overlap_tokens)

    # Convert to dict format with quality gates
    chunk_dicts = []
    dropped_junk_count = 0

    for chunk in chunks:
        # Compute quality metrics
        metrics = text_metrics(chunk.text)

        # Apply junk filter if configured
        if JUNK_DROP_CHUNK and metrics["looks_junk"]:
            dropped_junk_count += 1
            continue

        chunk_dicts.append(
            {
                "chunk_text": chunk.text,
                "chunk_index": chunk.chunk_index,
                "token_count": chunk.token_count,
                "document_title": title if title else None,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
                # Quality fields
                "quality_score": metrics["quality_score"],
                "junk": False,  # Not junk (we filtered it if it was)
                "ocr_used": ocr_used,
            }
        )

    if dropped_junk_count > 0:
        logger.info(f"Dropped {dropped_junk_count} junk chunks from document '{title}'")

    return chunk_dicts


def validate_chunks(chunks: list[TextChunk], max_tokens: int = 512) -> bool:
    """Validate that chunks meet requirements.

    Args:
        chunks: List of chunks to validate
        max_tokens: Maximum allowed tokens per chunk

    Returns:
        True if all chunks are valid
    """
    for chunk in chunks:
        if chunk.token_count > max_tokens:
            return False
        if not chunk.text or not chunk.text.strip():
            return False

    return True
