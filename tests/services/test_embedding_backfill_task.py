# mypy: disable-error-code="arg-type,call-overload,misc,assignment"
"""Tests for the embedding backfill scheduled task.

Verifies that missing embeddings (items and chunks) are detected and
repaired automatically via the scheduled backfill task, using proper
pgvector format and ::vector SQL cast.
"""

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

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
