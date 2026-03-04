# mypy: disable-error-code="arg-type,call-overload,misc,assignment"
"""Tests for the embedding backfill scheduled task.

Verifies that missing embeddings (items and chunks) are detected and
repaired automatically via the scheduled backfill task, using proper
pgvector format and ::vector SQL cast.
"""

import json
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.services.ingestion_report_service import EmbeddingBackfillResult
from app.services.scheduler_service import backfill_missing_embeddings_task


@pytest.mark.asyncio
class TestBackfillMissingEmbeddingsTask:
    """Tests for backfill_missing_embeddings_task."""

    def _make_session_mocks(self, item_rows, chunk_rows):
        """Helper to create session and engine mocks with sequential query results."""
        mock_session = AsyncMock()
        call_count = 0

        async def mock_execute(query, params=None):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # SELECT items
                result.fetchall.return_value = item_rows
            elif call_count == len(item_rows) + 2:
                # SELECT chunks (after all item UPDATEs + item SELECT)
                result.fetchall.return_value = chunk_rows
            elif call_count <= len(item_rows) + 1:
                # Item UPDATE calls
                result.rowcount = 1
            else:
                # Chunk UPDATE calls or any remaining
                result.rowcount = 1
                result.fetchall.return_value = []
            return result

        mock_session.execute = AsyncMock(side_effect=mock_execute)
        mock_session.commit = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session_maker = MagicMock(return_value=mock_session_ctx)

        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()

        return mock_session, mock_session_maker, mock_engine

    def _make_settings(self, enabled=True):
        """Create a mock settings object with required attributes."""
        mock_settings = MagicMock()
        mock_settings.EMBEDDING_BACKFILL_ENABLED = enabled
        mock_settings.POSTGRES_URL = "postgresql+asyncpg://test:test@localhost/test"
        return mock_settings

    async def test_backfill_skips_when_no_missing_embeddings(self):
        """Task does nothing when no items/chunks are missing embeddings."""
        mock_session, mock_session_maker, mock_engine = self._make_session_mocks([], [])

        with (
            patch("app.services.scheduler_service.settings", self._make_settings()),
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.orm.sessionmaker", return_value=mock_session_maker),
        ):
            await backfill_missing_embeddings_task()

        mock_session.commit.assert_not_called()

    async def test_backfill_embeds_missing_items(self):
        """Task generates embeddings for items with NULL embedding."""
        item_rows = [(1, "content for item 1"), (2, "content for item 2")]
        mock_session, mock_session_maker, mock_engine = self._make_session_mocks(item_rows, [])
        fake_embeddings = [[0.1] * 1536, [0.2] * 1536]

        with (
            patch("app.services.scheduler_service.settings", self._make_settings()),
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.orm.sessionmaker", return_value=mock_session_maker),
            patch(
                "app.core.embed.generate_embeddings_batch",
                new_callable=AsyncMock,
                return_value=fake_embeddings,
            ) as mock_embed,
        ):
            await backfill_missing_embeddings_task()

        mock_embed.assert_called_once()
        mock_session.commit.assert_called()

    async def test_backfill_uses_vector_cast_in_sql(self):
        """Task uses ::vector cast when updating pgvector columns."""
        item_rows = [(1, "content for item 1")]
        mock_session, mock_session_maker, mock_engine = self._make_session_mocks(item_rows, [])
        fake_embeddings = [[0.1] * 1536]

        with (
            patch("app.services.scheduler_service.settings", self._make_settings()),
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.orm.sessionmaker", return_value=mock_session_maker),
            patch(
                "app.core.embed.generate_embeddings_batch",
                new_callable=AsyncMock,
                return_value=fake_embeddings,
            ),
        ):
            await backfill_missing_embeddings_task()

        # Verify UPDATE calls use ::vector cast
        execute_calls = mock_session.execute.call_args_list
        update_calls = [c for c in execute_calls if c.args and "UPDATE" in str(c.args[0])]
        assert len(update_calls) >= 1, "Expected at least one UPDATE call"
        for update_call in update_calls:
            sql_str = str(update_call.args[0])
            assert "::vector" in sql_str, f"Missing ::vector cast in SQL: {sql_str}"

    async def test_backfill_uses_pgvector_format(self):
        """Task uses embedding_to_pgvector format (no spaces after commas)."""
        item_rows = [(1, "content for item 1")]
        mock_session, mock_session_maker, mock_engine = self._make_session_mocks(item_rows, [])
        fake_embeddings = [[0.1, 0.2, 0.3]]

        with (
            patch("app.services.scheduler_service.settings", self._make_settings()),
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.orm.sessionmaker", return_value=mock_session_maker),
            patch(
                "app.core.embed.generate_embeddings_batch",
                new_callable=AsyncMock,
                return_value=fake_embeddings,
            ),
        ):
            await backfill_missing_embeddings_task()

        # Find the UPDATE call and verify embedding format
        execute_calls = mock_session.execute.call_args_list
        update_calls = [c for c in execute_calls if c.args and "UPDATE" in str(c.args[0])]
        assert len(update_calls) >= 1
        # Check params contain pgvector format (no spaces)
        params = update_calls[0].args[1] if len(update_calls[0].args) > 1 else update_calls[0].kwargs.get("params", {})
        emb_str = params.get("emb", "")
        assert ", " not in emb_str, f"Embedding string has spaces: {emb_str}"
        assert emb_str.startswith("["), f"Expected pgvector format: {emb_str}"

    async def test_backfill_embeds_missing_chunks(self):
        """Task generates embeddings for chunks with NULL embedding."""
        chunk_rows = [(10, "chunk text 1"), (11, "chunk text 2"), (12, "chunk text 3")]
        mock_session, mock_session_maker, mock_engine = self._make_session_mocks([], chunk_rows)
        fake_embeddings = [[0.1] * 1536, [0.2] * 1536, [0.3] * 1536]

        with (
            patch("app.services.scheduler_service.settings", self._make_settings()),
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.orm.sessionmaker", return_value=mock_session_maker),
            patch(
                "app.core.embed.generate_embeddings_batch",
                new_callable=AsyncMock,
                return_value=fake_embeddings,
            ) as mock_embed,
        ):
            await backfill_missing_embeddings_task()

        mock_embed.assert_called_once()
        mock_session.commit.assert_called()

    async def test_backfill_disabled_via_config(self):
        """Task exits early when EMBEDDING_BACKFILL_ENABLED is False."""
        with (
            patch("app.services.scheduler_service.settings", self._make_settings(enabled=False)),
            patch("sqlalchemy.ext.asyncio.create_async_engine") as mock_create_engine,
        ):
            await backfill_missing_embeddings_task()

        mock_create_engine.assert_not_called()

    async def test_backfill_handles_embedding_api_failure(self):
        """Task continues gracefully when embedding API returns None for all."""
        item_rows = [(1, "some content")]
        mock_session, mock_session_maker, mock_engine = self._make_session_mocks(item_rows, [])

        with (
            patch("app.services.scheduler_service.settings", self._make_settings()),
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.orm.sessionmaker", return_value=mock_session_maker),
            patch(
                "app.core.embed.generate_embeddings_batch",
                new_callable=AsyncMock,
                return_value=[None],
            ),
        ):
            # Should not raise even when all embeddings fail
            await backfill_missing_embeddings_task()

    async def test_backfill_handles_api_exception_per_batch(self):
        """Task continues to next batch when embedding API raises an exception."""
        item_rows = [(1, "content 1"), (2, "content 2")]
        mock_session, mock_session_maker, mock_engine = self._make_session_mocks(item_rows, [])

        with (
            patch("app.services.scheduler_service.settings", self._make_settings()),
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.orm.sessionmaker", return_value=mock_session_maker),
            patch(
                "app.core.embed.generate_embeddings_batch",
                new_callable=AsyncMock,
                side_effect=Exception("OpenAI API error"),
            ),
        ):
            # Should not raise - task catches per-batch exceptions
            await backfill_missing_embeddings_task()

    async def test_backfill_handles_exception(self):
        """Task handles unexpected exceptions gracefully."""
        with (
            patch("app.services.scheduler_service.settings", self._make_settings()),
            patch(
                "sqlalchemy.ext.asyncio.create_async_engine",
                side_effect=Exception("DB connection failed"),
            ),
        ):
            # Should not raise - task catches all exceptions
            await backfill_missing_embeddings_task()

    async def test_backfill_per_item_update_failure_counts_as_failed(self):
        """When session.execute fails for UPDATE, item is counted as failed, not lost."""
        item_rows = [(1, "content 1"), (2, "content 2")]
        mock_session, mock_session_maker, mock_engine = self._make_session_mocks(item_rows, [])
        fake_embeddings = [[0.1] * 1536, [0.2] * 1536]

        # Make the UPDATE call fail (session.execute raises on UPDATE)
        original_execute = mock_session.execute
        call_count_track = {"count": 0}

        async def execute_with_update_failure(query, params=None):
            call_count_track["count"] += 1
            query_str = str(query)
            if "UPDATE" in query_str:
                raise Exception("pgvector type mismatch")
            return await original_execute(query, params)

        mock_session.execute = AsyncMock(side_effect=execute_with_update_failure)

        with (
            patch("app.services.scheduler_service.settings", self._make_settings()),
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.orm.sessionmaker", return_value=mock_session_maker),
            patch(
                "app.core.embed.generate_embeddings_batch",
                new_callable=AsyncMock,
                return_value=fake_embeddings,
            ),
            patch("app.services.scheduler_service._store_backfill_result") as mock_store,
        ):
            await backfill_missing_embeddings_task()

        result = mock_store.call_args[0][0]
        assert result.items_found == 2
        assert result.items_failed == 2
        assert result.items_fixed == 0

    async def test_backfill_chunks_still_run_after_items_error(self):
        """Chunk processing runs even if all item updates fail."""
        item_rows = [(1, "content 1")]
        chunk_rows = [(10, "chunk text")]

        # Use query-text-aware mock instead of call-count-based
        mock_session = AsyncMock()

        async def mock_execute(query, params=None):
            query_str = str(query)
            result = MagicMock()
            if "knowledge_items" in query_str and "SELECT" in query_str:
                result.fetchall.return_value = item_rows
            elif "knowledge_chunks" in query_str and "SELECT" in query_str:
                result.fetchall.return_value = chunk_rows
            elif "UPDATE" in query_str:
                result.rowcount = 1
            else:
                result.fetchall.return_value = []
            return result

        mock_session.execute = AsyncMock(side_effect=mock_execute)
        mock_session.commit = AsyncMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_maker = MagicMock(return_value=mock_session_ctx)
        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()

        embed_call_count = {"count": 0}

        async def mock_embed(texts, batch_size=20):
            embed_call_count["count"] += 1
            if embed_call_count["count"] == 1:
                raise Exception("API error for items")
            return [[0.3] * 1536] * len(texts)

        with (
            patch("app.services.scheduler_service.settings", self._make_settings()),
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.orm.sessionmaker", return_value=mock_session_maker),
            patch(
                "app.core.embed.generate_embeddings_batch",
                new_callable=AsyncMock,
                side_effect=mock_embed,
            ),
            patch("app.services.scheduler_service._store_backfill_result") as mock_store,
        ):
            await backfill_missing_embeddings_task()

        result = mock_store.call_args[0][0]
        # Items had an API error
        assert result.items_found == 1
        assert result.items_failed == 1
        # Chunks should still have been processed
        assert result.chunks_found == 1
        assert result.chunks_fixed == 1

    async def test_backfill_stores_error_message_on_crash(self):
        """When backfill crashes, error_message is stored in result."""
        mock_session, mock_session_maker, mock_engine = self._make_session_mocks([], [])
        # Make engine creation succeed but session query fail
        mock_session.execute = AsyncMock(side_effect=Exception("connection reset"))

        with (
            patch("app.services.scheduler_service.settings", self._make_settings()),
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.orm.sessionmaker", return_value=mock_session_maker),
            patch("app.services.scheduler_service._store_backfill_result") as mock_store,
        ):
            await backfill_missing_embeddings_task()

        result = mock_store.call_args[0][0]
        assert result.error_message
        assert "connection reset" in result.error_message

    async def test_backfill_stores_result_in_redis(self):
        """Task stores backfill results in Redis after completion."""
        item_rows = [(1, "content 1"), (2, "content 2")]
        chunk_rows = [(10, "chunk 1")]
        mock_session, mock_session_maker, mock_engine = self._make_session_mocks(item_rows, chunk_rows)
        fake_item_embeddings = [[0.1] * 1536, [0.2] * 1536]
        fake_chunk_embeddings = [[0.3] * 1536]

        with (
            patch("app.services.scheduler_service.settings", self._make_settings()),
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.orm.sessionmaker", return_value=mock_session_maker),
            patch(
                "app.core.embed.generate_embeddings_batch",
                new_callable=AsyncMock,
                side_effect=[fake_item_embeddings, fake_chunk_embeddings],
            ),
            patch("app.services.scheduler_service._store_backfill_result") as mock_store,
        ):
            await backfill_missing_embeddings_task()

        mock_store.assert_called_once()
        result = mock_store.call_args[0][0]
        assert isinstance(result, EmbeddingBackfillResult)
        assert result.items_found == 2
        assert result.items_fixed == 2
        assert result.chunks_found == 1
        assert result.chunks_fixed == 1

    async def test_backfill_stores_result_with_failures(self):
        """Task stores correct failure counts when some embeddings fail."""
        item_rows = [(1, "content 1")]
        mock_session, mock_session_maker, mock_engine = self._make_session_mocks(item_rows, [])

        with (
            patch("app.services.scheduler_service.settings", self._make_settings()),
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.orm.sessionmaker", return_value=mock_session_maker),
            patch(
                "app.core.embed.generate_embeddings_batch",
                new_callable=AsyncMock,
                return_value=[None],
            ),
            patch("app.services.scheduler_service._store_backfill_result") as mock_store,
        ):
            await backfill_missing_embeddings_task()

        result = mock_store.call_args[0][0]
        assert result.items_found == 1
        assert result.items_fixed == 0
        assert result.items_failed == 1

    async def test_backfill_stores_result_when_nothing_to_do(self):
        """Task stores result even when no missing embeddings found."""
        mock_session, mock_session_maker, mock_engine = self._make_session_mocks([], [])

        with (
            patch("app.services.scheduler_service.settings", self._make_settings()),
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.orm.sessionmaker", return_value=mock_session_maker),
            patch("app.services.scheduler_service._store_backfill_result") as mock_store,
        ):
            await backfill_missing_embeddings_task()

        result = mock_store.call_args[0][0]
        assert result.items_found == 0
        assert result.chunks_found == 0


class TestEmbeddingBackfillResult:
    """Tests for EmbeddingBackfillResult dataclass."""

    def test_defaults(self):
        """All fields default to zero."""
        result = EmbeddingBackfillResult()
        assert result.items_found == 0
        assert result.items_fixed == 0
        assert result.items_failed == 0
        assert result.chunks_found == 0
        assert result.chunks_fixed == 0
        assert result.chunks_failed == 0

    def test_to_dict(self):
        """to_dict returns serializable dictionary."""
        result = EmbeddingBackfillResult(items_found=10, items_fixed=8, items_failed=2)
        d = result.to_dict()
        assert d["items_found"] == 10
        assert d["items_fixed"] == 8
        assert d["items_failed"] == 2
        # Should be JSON-serializable
        json.dumps(d)

    def test_from_dict(self):
        """from_dict reconstructs from dictionary."""
        data = {
            "items_found": 5,
            "items_fixed": 4,
            "items_failed": 1,
            "chunks_found": 10,
            "chunks_fixed": 9,
            "chunks_failed": 1,
            "ran_at": "2026-03-03T03:00:00+00:00",
        }
        result = EmbeddingBackfillResult.from_dict(data)
        assert result.items_found == 5
        assert result.chunks_fixed == 9
        assert result.ran_at == "2026-03-03T03:00:00+00:00"

    def test_from_dict_handles_missing_keys(self):
        """from_dict defaults missing keys to zero."""
        result = EmbeddingBackfillResult.from_dict({})
        assert result.items_found == 0
        assert result.chunks_found == 0

    def test_error_message_field(self):
        """error_message captures crash details."""
        result = EmbeddingBackfillResult(items_found=161, error_message="pgvector type mismatch")
        d = result.to_dict()
        assert d["error_message"] == "pgvector type mismatch"
        reconstructed = EmbeddingBackfillResult.from_dict(d)
        assert reconstructed.error_message == "pgvector type mismatch"
