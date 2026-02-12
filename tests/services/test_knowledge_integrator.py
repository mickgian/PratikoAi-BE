"""Tests for knowledge integrator batch embedding, config chunk size, and content-hash dedup.

Covers:
  - P0-A: generate_embeddings_batch called for chunk embeddings in update_knowledge_base()
  - P0-A: generate_embeddings_batch called for chunk embeddings in handle_document_update()
  - P0-B: chunk_document called without hardcoded max_tokens=512 in both methods
  - P1-A: Content-hash dedup in _find_existing_document() and update_knowledge_base()
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.knowledge_integrator import KnowledgeIntegrator


def _make_mock_db():
    """Create a mock DB session with common setup."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    mock_db.refresh = AsyncMock()
    return mock_db


def _setup_track_add(mock_db, id_offset=0):
    """Set up item tracking on mock_db.add."""
    added_items: list[object] = []

    def track_add(item):
        added_items.append(item)
        if hasattr(item, "id") and item.id is None:
            item.id = len(added_items) + id_offset

    mock_db.add = track_add
    return added_items


def _setup_execute_returns(mock_db, return_value):
    """Set mock_db.execute to return a result with scalar_one_or_none."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = return_value
    mock_db.execute = AsyncMock(return_value=mock_result)


@pytest.mark.asyncio
class TestUpdateKnowledgeBaseBatchEmbedding:
    """Verify update_knowledge_base() uses batch embedding for chunks."""

    @patch("app.services.knowledge_integrator.generate_embeddings_batch")
    @patch("app.services.knowledge_integrator.generate_embedding")
    @patch("app.services.knowledge_integrator.chunk_document")
    async def test_update_kb_calls_batch_embedding(
        self,
        mock_chunk_document: MagicMock,
        mock_generate_embedding: MagicMock,
        mock_generate_embeddings_batch: MagicMock,
    ) -> None:
        """Batch called for chunks in update_knowledge_base()."""
        mock_generate_embedding.return_value = [0.1] * 1536
        mock_chunk_document.return_value = [
            {
                "chunk_text": "Chunk A",
                "chunk_index": 0,
                "token_count": 50,
                "document_title": "Test",
                "start_char": 0,
                "end_char": 50,
                "quality_score": 0.8,
                "junk": False,
                "ocr_used": False,
            },
            {
                "chunk_text": "Chunk B",
                "chunk_index": 1,
                "token_count": 50,
                "document_title": "Test",
                "start_char": 50,
                "end_char": 100,
                "quality_score": 0.9,
                "junk": False,
                "ocr_used": False,
            },
        ]
        mock_generate_embeddings_batch.return_value = [
            [0.2] * 1536,
            [0.3] * 1536,
        ]

        mock_db = _make_mock_db()
        _setup_execute_returns(mock_db, None)
        _setup_track_add(mock_db)

        integrator = KnowledgeIntegrator(mock_db)

        with (
            patch.object(integrator, "_create_regulatory_document", new_callable=AsyncMock),
            patch.object(integrator, "invalidate_relevant_caches", new_callable=AsyncMock),
        ):
            result = await integrator.update_knowledge_base(
                {
                    "title": "Test Doc",
                    "url": "https://example.com/doc",
                    "content": "Full document content.",
                    "source": "test",
                }
            )

        assert result["success"] is True
        assert result["action"] == "created"
        mock_generate_embedding.assert_called_once()
        mock_generate_embeddings_batch.assert_called_once_with(["Chunk A", "Chunk B"])

    @patch("app.services.knowledge_integrator.generate_embeddings_batch")
    @patch("app.services.knowledge_integrator.generate_embedding")
    @patch("app.services.knowledge_integrator.chunk_document")
    async def test_update_kb_uses_config_chunk_tokens(
        self,
        mock_chunk_document: MagicMock,
        mock_generate_embedding: MagicMock,
        mock_generate_embeddings_batch: MagicMock,
    ) -> None:
        """No hardcoded max_tokens=512 in update_knowledge_base()."""
        mock_generate_embedding.return_value = [0.1] * 1536
        mock_chunk_document.return_value = []
        mock_generate_embeddings_batch.return_value = []

        mock_db = _make_mock_db()
        _setup_execute_returns(mock_db, None)
        _setup_track_add(mock_db)

        integrator = KnowledgeIntegrator(mock_db)

        with (
            patch.object(integrator, "_create_regulatory_document", new_callable=AsyncMock),
            patch.object(integrator, "invalidate_relevant_caches", new_callable=AsyncMock),
        ):
            await integrator.update_knowledge_base(
                {
                    "title": "Test Doc",
                    "url": "https://example.com/doc",
                    "content": "Full document content.",
                    "source": "test",
                }
            )

        mock_chunk_document.assert_called_once()
        call_kwargs = mock_chunk_document.call_args
        if call_kwargs.kwargs.get("max_tokens") is not None:
            assert call_kwargs.kwargs["max_tokens"] != 512
        if call_kwargs.kwargs.get("overlap_tokens") is not None:
            assert call_kwargs.kwargs["overlap_tokens"] != 50


@pytest.mark.asyncio
class TestHandleDocumentUpdateBatchEmbedding:
    """Verify handle_document_update() uses batch embedding for chunks."""

    @patch("app.services.knowledge_integrator.generate_embeddings_batch")
    @patch("app.services.knowledge_integrator.generate_embedding")
    @patch("app.services.knowledge_integrator.chunk_document")
    async def test_handle_update_calls_batch_embedding(
        self,
        mock_chunk_document: MagicMock,
        mock_generate_embedding: MagicMock,
        mock_generate_embeddings_batch: MagicMock,
    ) -> None:
        """Batch called for chunks in handle_document_update()."""
        mock_generate_embedding.return_value = [0.1] * 1536
        mock_chunk_document.return_value = [
            {
                "chunk_text": "Updated chunk",
                "chunk_index": 0,
                "token_count": 50,
                "document_title": "Test",
                "start_char": 0,
                "end_char": 50,
                "quality_score": 0.85,
                "junk": False,
                "ocr_used": False,
            },
        ]
        mock_generate_embeddings_batch.return_value = [[0.5] * 1536]

        existing_item = MagicMock()
        existing_item.id = 42
        existing_item.category = "test_category"
        existing_item.subcategory = "test_sub"
        existing_item.source = "test"
        existing_item.version = 1
        existing_item.status = "active"
        existing_item.extra_metadata = {}

        mock_db = _make_mock_db()
        _setup_execute_returns(mock_db, existing_item)
        _setup_track_add(mock_db, id_offset=100)

        integrator = KnowledgeIntegrator(mock_db)

        with (
            patch.object(integrator, "_update_regulatory_document", new_callable=AsyncMock),
            patch.object(integrator, "invalidate_relevant_caches", new_callable=AsyncMock),
        ):
            result = await integrator.handle_document_update(
                {
                    "title": "Updated Doc",
                    "url": "https://example.com/doc",
                    "content": "Updated content.",
                    "source": "test",
                }
            )

        assert result["success"] is True
        assert result["action"] == "updated"
        mock_generate_embedding.assert_called_once()
        mock_generate_embeddings_batch.assert_called_once_with(["Updated chunk"])

    @patch("app.services.knowledge_integrator.generate_embeddings_batch")
    @patch("app.services.knowledge_integrator.generate_embedding")
    @patch("app.services.knowledge_integrator.chunk_document")
    async def test_handle_update_uses_config_chunk_tokens(
        self,
        mock_chunk_document: MagicMock,
        mock_generate_embedding: MagicMock,
        mock_generate_embeddings_batch: MagicMock,
    ) -> None:
        """No hardcoded max_tokens=512 in handle_document_update()."""
        mock_generate_embedding.return_value = [0.1] * 1536
        mock_chunk_document.return_value = []
        mock_generate_embeddings_batch.return_value = []

        existing_item = MagicMock()
        existing_item.id = 42
        existing_item.category = "test_category"
        existing_item.subcategory = "test_sub"
        existing_item.source = "test"
        existing_item.version = 1
        existing_item.status = "active"
        existing_item.extra_metadata = {}

        mock_db = _make_mock_db()
        _setup_execute_returns(mock_db, existing_item)
        _setup_track_add(mock_db, id_offset=100)

        integrator = KnowledgeIntegrator(mock_db)

        with (
            patch.object(integrator, "_update_regulatory_document", new_callable=AsyncMock),
            patch.object(integrator, "invalidate_relevant_caches", new_callable=AsyncMock),
        ):
            await integrator.handle_document_update(
                {
                    "title": "Updated Doc",
                    "url": "https://example.com/doc",
                    "content": "Updated content.",
                    "source": "test",
                }
            )

        mock_chunk_document.assert_called_once()
        call_kwargs = mock_chunk_document.call_args
        if call_kwargs.kwargs.get("max_tokens") is not None:
            assert call_kwargs.kwargs["max_tokens"] != 512
        if call_kwargs.kwargs.get("overlap_tokens") is not None:
            assert call_kwargs.kwargs["overlap_tokens"] != 50


@pytest.mark.asyncio
class TestContentHashDedup:
    """P1-A: Verify content-hash deduplication works in KnowledgeIntegrator."""

    @patch("app.services.knowledge_integrator.generate_embeddings_batch")
    @patch("app.services.knowledge_integrator.generate_embedding")
    @patch("app.services.knowledge_integrator.chunk_document")
    async def test_update_kb_skips_duplicate_content_hash(
        self,
        mock_chunk_document: MagicMock,
        mock_generate_embedding: MagicMock,
        mock_generate_embeddings_batch: MagicMock,
    ) -> None:
        """update_knowledge_base() skips when content_hash already exists in DB."""
        mock_generate_embedding.return_value = [0.1] * 1536
        mock_chunk_document.return_value = []
        mock_generate_embeddings_batch.return_value = []

        existing_item = MagicMock()
        existing_item.id = 99
        existing_item.status = "active"

        mock_db = AsyncMock()
        mock_db.rollback = AsyncMock()
        _setup_execute_returns(mock_db, existing_item)

        integrator = KnowledgeIntegrator(mock_db)

        result = await integrator.update_knowledge_base(
            {
                "title": "Same Doc Different URL",
                "url": "https://different-site.com/same-doc",
                "content": "Identical content that already exists.",
                "source": "test",
            }
        )

        assert result["success"] is True
        assert result["action"] == "skipped"

    @patch("app.services.knowledge_integrator.generate_embeddings_batch")
    @patch("app.services.knowledge_integrator.generate_embedding")
    @patch("app.services.knowledge_integrator.chunk_document")
    async def test_update_kb_sets_content_hash_on_new_item(
        self,
        mock_chunk_document: MagicMock,
        mock_generate_embedding: MagicMock,
        mock_generate_embeddings_batch: MagicMock,
    ) -> None:
        """update_knowledge_base() sets content_hash on newly created KnowledgeItem."""
        mock_generate_embedding.return_value = [0.1] * 1536
        mock_chunk_document.return_value = []
        mock_generate_embeddings_batch.return_value = []

        mock_db = _make_mock_db()
        _setup_execute_returns(mock_db, None)
        added_items = _setup_track_add(mock_db)

        integrator = KnowledgeIntegrator(mock_db)

        with (
            patch.object(integrator, "_create_regulatory_document", new_callable=AsyncMock),
            patch.object(integrator, "invalidate_relevant_caches", new_callable=AsyncMock),
        ):
            await integrator.update_knowledge_base(
                {
                    "title": "New Doc",
                    "url": "https://example.com/new",
                    "content": "New document content.",
                    "source": "test",
                }
            )

        from app.models.knowledge import KnowledgeItem

        ki_items = [i for i in added_items if isinstance(i, KnowledgeItem)]
        assert len(ki_items) >= 1
        assert ki_items[0].content_hash is not None
        assert len(ki_items[0].content_hash) == 64  # SHA-256 hex digest
