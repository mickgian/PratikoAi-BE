"""Tests for feed_status.last_checked being updated on every ingestion attempt.

Bug: last_checked was only set at record creation (via default_factory) and never
updated during ingestion runs. last_success was updated on success, but last_checked
stayed frozen at the initial insert timestamp.

Fix: Set last_checked = datetime.now(UTC) at the start of every feed attempt,
in both success and error paths.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


@pytest.fixture
def stale_last_checked() -> datetime:
    """Return a stale last_checked timestamp (30 days ago)."""
    return datetime.now(UTC) - timedelta(days=30)


@pytest.fixture
def mock_feed_status(stale_last_checked: datetime):
    """Create a mock FeedStatus with a stale last_checked."""
    feed = MagicMock()
    feed.id = uuid4()
    feed.source = "test_source"
    feed.feed_type = "news"
    feed.feed_url = "https://example.com/feed.xml"
    feed.last_checked = stale_last_checked
    feed.last_success = None
    feed.consecutive_errors = 0
    feed.errors = 0
    feed.last_error = None
    feed.status = "healthy"
    feed.items_found = 0
    feed.items_filtered = 0
    feed.filtered_samples = None
    feed.enabled = True
    return feed


class TestRunFullIngestionLastChecked:
    """Test that run_full_ingestion.py updates last_checked."""

    @pytest.mark.asyncio
    async def test_last_checked_set_before_ingestion(self, mock_feed_status, stale_last_checked):
        """run_full_ingestion should set last_checked before run_rss_ingestion."""
        from scripts.run_full_ingestion import run_rss_ingestion_all

        mock_session = AsyncMock()

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_feed_status]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "scripts.run_full_ingestion.run_rss_ingestion",
            return_value={
                "status": "success",
                "total_items": 5,
                "new_documents": 2,
                "skipped_existing": 3,
                "failed": 0,
            },
        ):
            result = await run_rss_ingestion_all(session=mock_session, max_items=10)

        assert mock_feed_status.last_checked > stale_last_checked
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_last_checked_set_on_error(self, mock_feed_status, stale_last_checked):
        """run_full_ingestion should keep last_checked even when feed fails."""
        from scripts.run_full_ingestion import run_rss_ingestion_all

        mock_session = AsyncMock()

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_feed_status]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "scripts.run_full_ingestion.run_rss_ingestion",
            side_effect=RuntimeError("Connection refused"),
        ):
            result = await run_rss_ingestion_all(session=mock_session, max_items=10)

        # last_checked was set before the error occurred
        assert mock_feed_status.last_checked > stale_last_checked

    @pytest.mark.asyncio
    async def test_last_checked_updated_close_to_now(self, mock_feed_status, stale_last_checked):
        """last_checked should be set to approximately now, not any other time."""
        from scripts.run_full_ingestion import run_rss_ingestion_all

        mock_session = AsyncMock()

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_feed_status]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        before = datetime.now(UTC)

        with patch(
            "scripts.run_full_ingestion.run_rss_ingestion",
            return_value={
                "status": "success",
                "total_items": 5,
                "new_documents": 2,
                "skipped_existing": 3,
                "failed": 0,
            },
        ):
            await run_rss_ingestion_all(session=mock_session, max_items=10)

        after = datetime.now(UTC)

        # last_checked should be between before and after (i.e. set during the call)
        assert before <= mock_feed_status.last_checked <= after


class TestSchedulerLastCheckedUpdate:
    """Test that scheduler_service updates last_checked in both success and error paths.

    Since collect_rss_feeds_task() uses local imports, we patch at the source module level
    (sqlalchemy.ext.asyncio, app.ingest.rss_normativa, etc.).
    """

    @pytest.mark.asyncio
    async def test_last_checked_updated_on_success(self, mock_feed_status, stale_last_checked):
        """Scheduler should update last_checked before ingestion runs."""
        from app.services.scheduler_service import collect_rss_feeds_task

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_feed_status)

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        # Session for initial feed query
        feeds_session = AsyncMock()
        feeds_session_ctx = AsyncMock()
        feeds_session_ctx.__aenter__ = AsyncMock(return_value=feeds_session)
        feeds_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_feed_status]
        mock_result.scalars.return_value = mock_scalars
        feeds_session.execute = AsyncMock(return_value=mock_result)

        call_count = 0

        def session_factory():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return feeds_session_ctx
            return mock_session_ctx

        mock_engine = AsyncMock()

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.orm.sessionmaker", return_value=session_factory),
            patch(
                "app.ingest.rss_normativa.run_rss_ingestion",
                return_value={
                    "status": "success",
                    "total_items": 5,
                    "new_documents": 2,
                    "skipped_existing": 3,
                    "failed": 0,
                    "skipped_filtered": 0,
                    "filtered_samples": [],
                },
            ),
        ):
            await collect_rss_feeds_task()

        assert mock_feed_status.last_checked > stale_last_checked

    @pytest.mark.asyncio
    async def test_last_checked_updated_on_error(self, mock_feed_status, stale_last_checked):
        """Scheduler should update last_checked even when ingestion fails."""
        from app.services.scheduler_service import collect_rss_feeds_task

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_feed_status)

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        feeds_session = AsyncMock()
        feeds_session_ctx = AsyncMock()
        feeds_session_ctx.__aenter__ = AsyncMock(return_value=feeds_session)
        feeds_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_feed_status]
        mock_result.scalars.return_value = mock_scalars
        feeds_session.execute = AsyncMock(return_value=mock_result)

        call_count = 0

        def session_factory():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return feeds_session_ctx
            return mock_session_ctx

        mock_engine = AsyncMock()

        with (
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.orm.sessionmaker", return_value=session_factory),
            patch(
                "app.ingest.rss_normativa.run_rss_ingestion",
                side_effect=RuntimeError("Connection timeout"),
            ),
        ):
            await collect_rss_feeds_task()

        # last_checked should be updated in the error handler
        assert mock_feed_status.last_checked > stale_last_checked
