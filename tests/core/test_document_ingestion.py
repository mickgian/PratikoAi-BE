"""Tests for document ingestion batch embedding and config chunk size.

Covers:
  - P0-A: generate_embeddings_batch called for chunk embeddings (not per-chunk generate_embedding)
  - P0-A: Partial batch failure handling (some embeddings None)
  - P0-B: chunk_document called without hardcoded max_tokens=512 / overlap_tokens=50
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
class TestIngestDocumentBatchEmbedding:
    """Verify ingest_document_with_chunks uses batch embedding for chunks."""

    @patch("app.core.document_ingestion.article_extractor")
    @patch("app.core.document_ingestion.chunk_document")
    @patch("app.core.document_ingestion.generate_embeddings_batch")
    @patch("app.core.document_ingestion.generate_embedding")
    async def test_ingest_calls_batch_embedding_for_chunks(
        self,
        mock_generate_embedding: MagicMock,
        mock_generate_embeddings_batch: MagicMock,
        mock_chunk_document: MagicMock,
        mock_article_extractor: MagicMock,
    ) -> None:
        """generate_embeddings_batch called once with all chunk texts;
        generate_embedding called once (full doc only)."""
        from app.core.document_ingestion import ingest_document_with_chunks

        # Mock article_extractor
        mock_article_extractor.extract_chunk_metadata.return_value = {
            "article_references": [],
            "primary_article": None,
            "has_definitions": False,
            "comma_count": 0,
        }

        # Mock full-doc embedding (single call)
        mock_generate_embedding.return_value = [0.1] * 1536

        # Mock chunks returned by chunk_document
        mock_chunk_document.return_value = [
            {
                "chunk_text": "Chunk one text",
                "chunk_index": 0,
                "token_count": 100,
                "document_title": "Test",
                "start_char": 0,
                "end_char": 100,
                "quality_score": 0.8,
                "junk": False,
                "ocr_used": False,
            },
            {
                "chunk_text": "Chunk two text",
                "chunk_index": 1,
                "token_count": 100,
                "document_title": "Test",
                "start_char": 100,
                "end_char": 200,
                "quality_score": 0.9,
                "junk": False,
                "ocr_used": False,
            },
        ]

        # Mock batch embeddings
        mock_generate_embeddings_batch.return_value = [
            [0.2] * 1536,
            [0.3] * 1536,
        ]

        # Mock DB session
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        # Mock content-hash dedup check (no duplicate)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Mock ID assignment
        added_items = []

        def track_add(item):
            added_items.append(item)
            if hasattr(item, "id") and item.id is None:
                item.id = len(added_items)

        mock_session.add = track_add

        result = await ingest_document_with_chunks(
            session=mock_session,
            title="Test Doc",
            url="https://example.com/doc",
            content="Full document content for testing.",
        )

        assert result is not None

        # generate_embedding called exactly once for the full doc
        mock_generate_embedding.assert_called_once()

        # generate_embeddings_batch called once with all chunk texts
        mock_generate_embeddings_batch.assert_called_once_with(["Chunk one text", "Chunk two text"])

    @patch("app.core.document_ingestion.article_extractor")
    @patch("app.core.document_ingestion.chunk_document")
    @patch("app.core.document_ingestion.generate_embeddings_batch")
    @patch("app.core.document_ingestion.generate_embedding")
    async def test_ingest_handles_partial_batch_failure(
        self,
        mock_generate_embedding: MagicMock,
        mock_generate_embeddings_batch: MagicMock,
        mock_chunk_document: MagicMock,
        mock_article_extractor: MagicMock,
    ) -> None:
        """When batch returns [None, [0.1]*1536], both chunks created,
        one with None embedding."""
        from app.core.document_ingestion import ingest_document_with_chunks

        mock_article_extractor.extract_chunk_metadata.return_value = {
            "article_references": [],
            "primary_article": None,
            "has_definitions": False,
            "comma_count": 0,
        }

        mock_generate_embedding.return_value = [0.1] * 1536

        mock_chunk_document.return_value = [
            {
                "chunk_text": "Chunk one text",
                "chunk_index": 0,
                "token_count": 100,
                "document_title": "Test",
                "start_char": 0,
                "end_char": 100,
                "quality_score": 0.8,
                "junk": False,
                "ocr_used": False,
            },
            {
                "chunk_text": "Chunk two text",
                "chunk_index": 1,
                "token_count": 100,
                "document_title": "Test",
                "start_char": 100,
                "end_char": 200,
                "quality_score": 0.9,
                "junk": False,
                "ocr_used": False,
            },
        ]

        # First chunk fails, second succeeds
        mock_generate_embeddings_batch.return_value = [None, [0.1] * 1536]

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        added_items = []

        def track_add(item):
            added_items.append(item)
            if hasattr(item, "id") and item.id is None:
                item.id = len(added_items)

        mock_session.add = track_add

        result = await ingest_document_with_chunks(
            session=mock_session,
            title="Test Doc",
            url="https://example.com/doc",
            content="Full document content for testing.",
        )

        assert result is not None

        # Find KnowledgeChunk items
        from app.models.knowledge_chunk import KnowledgeChunk

        chunks = [item for item in added_items if isinstance(item, KnowledgeChunk)]
        assert len(chunks) == 2

        # First chunk has None embedding, second has valid embedding
        assert chunks[0].embedding is None
        assert chunks[1].embedding is not None

    @patch("app.core.document_ingestion.article_extractor")
    @patch("app.core.document_ingestion.chunk_document")
    @patch("app.core.document_ingestion.generate_embeddings_batch")
    @patch("app.core.document_ingestion.generate_embedding")
    async def test_ingest_uses_config_chunk_tokens(
        self,
        mock_generate_embedding: MagicMock,
        mock_generate_embeddings_batch: MagicMock,
        mock_chunk_document: MagicMock,
        mock_article_extractor: MagicMock,
    ) -> None:
        """chunk_document called without max_tokens=512 or overlap_tokens=50."""
        from app.core.document_ingestion import ingest_document_with_chunks

        mock_article_extractor.extract_chunk_metadata.return_value = {
            "article_references": [],
            "primary_article": None,
            "has_definitions": False,
            "comma_count": 0,
        }

        mock_generate_embedding.return_value = [0.1] * 1536
        mock_chunk_document.return_value = []
        mock_generate_embeddings_batch.return_value = []

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        added_items = []

        def track_add(item):
            added_items.append(item)
            if hasattr(item, "id") and item.id is None:
                item.id = len(added_items)

        mock_session.add = track_add

        await ingest_document_with_chunks(
            session=mock_session,
            title="Test Doc",
            url="https://example.com/doc",
            content="Full document content for testing.",
        )

        # chunk_document should NOT have been called with max_tokens=512
        mock_chunk_document.assert_called_once()
        call_kwargs = mock_chunk_document.call_args
        # Check that max_tokens and overlap_tokens were NOT passed as 512/50
        if call_kwargs.kwargs.get("max_tokens") is not None:
            assert call_kwargs.kwargs["max_tokens"] != 512
        if call_kwargs.kwargs.get("overlap_tokens") is not None:
            assert call_kwargs.kwargs["overlap_tokens"] != 50
