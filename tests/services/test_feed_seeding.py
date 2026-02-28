"""Tests for automatic RSS feed seeding on app startup.

Ensures that ensure_feeds_seeded() idempotently upserts the canonical 16 feeds
into feed_status on every deployment, preventing the QA/prod "empty feeds" problem.

TDD: RED phase — tests written before implementation.
"""

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.regulatory_documents import FeedStatus


@pytest_asyncio.fixture
async def empty_feed_status(db_session: AsyncSession):
    """Ensure feed_status table is empty before test."""
    await db_session.execute(text("DELETE FROM feed_status"))
    await db_session.commit()
    yield db_session


@pytest_asyncio.fixture
async def partial_feed_status(db_session: AsyncSession):
    """Seed only 2 of 16 feeds to simulate partial data loss."""
    await db_session.execute(text("DELETE FROM feed_status"))
    await db_session.execute(
        text(
            """
            INSERT INTO feed_status (
                feed_url, source, feed_type, parser, status, enabled,
                consecutive_errors, errors, check_interval_minutes
            ) VALUES (
                'https://www.inps.it/it/it.rss.news.xml', 'inps', 'news', 'inps',
                'healthy', true, 0, 0, 240
            )
            """
        )
    )
    await db_session.commit()
    yield db_session


@pytest.mark.asyncio
class TestEnsureFeedsSeeded:
    """Test ensure_feeds_seeded() runtime seeding."""

    async def test_seeds_all_16_feeds_from_empty(self, empty_feed_status: AsyncSession):
        """When feed_status is empty, all 16 canonical feeds are inserted."""
        from app.core.feed_registry import ensure_feeds_seeded

        session = empty_feed_status
        result = await ensure_feeds_seeded(session)

        assert result["seeded"] == 16

        count = (await session.execute(text("SELECT COUNT(*) FROM feed_status"))).scalar()
        assert count == 16

    async def test_idempotent_no_duplicates(self, empty_feed_status: AsyncSession):
        """Running ensure_feeds_seeded() twice does not create duplicates."""
        from app.core.feed_registry import ensure_feeds_seeded

        session = empty_feed_status
        await ensure_feeds_seeded(session)
        result = await ensure_feeds_seeded(session)

        # Second run should seed 0 new
        assert result["seeded"] == 0

        count = (await session.execute(text("SELECT COUNT(*) FROM feed_status"))).scalar()
        assert count == 16

    async def test_fills_missing_feeds(self, partial_feed_status: AsyncSession):
        """When some feeds exist, only missing ones are inserted."""
        from app.core.feed_registry import ensure_feeds_seeded

        session = partial_feed_status
        result = await ensure_feeds_seeded(session)

        # 1 feed already existed, 15 should be new
        assert result["seeded"] == 15

        count = (await session.execute(text("SELECT COUNT(*) FROM feed_status"))).scalar()
        assert count == 16

    async def test_preserves_existing_feed_status(self, partial_feed_status: AsyncSession):
        """Existing feed's runtime state (status, last_success, errors) is preserved."""
        from app.core.feed_registry import ensure_feeds_seeded

        session = partial_feed_status

        # The pre-seeded INPS news feed has status='healthy'
        await ensure_feeds_seeded(session)

        stmt = select(FeedStatus).where(FeedStatus.feed_url == "https://www.inps.it/it/it.rss.news.xml")
        feed = (await session.execute(stmt)).scalar_one()

        # Status should be preserved (not overwritten to 'pending')
        assert feed.status == "healthy"

    async def test_all_seeded_feeds_are_enabled(self, empty_feed_status: AsyncSession):
        """All newly seeded feeds should be enabled."""
        from app.core.feed_registry import ensure_feeds_seeded

        session = empty_feed_status
        await ensure_feeds_seeded(session)

        stmt = select(FeedStatus).where(FeedStatus.enabled == False)  # noqa: E712
        disabled = (await session.execute(stmt)).scalars().all()

        assert len(disabled) == 0

    async def test_canonical_feed_count_is_16(self):
        """The canonical feed registry contains exactly 16 feeds."""
        from app.core.feed_registry import CANONICAL_FEEDS

        assert len(CANONICAL_FEEDS) == 16

    async def test_canonical_feeds_have_required_fields(self):
        """Every canonical feed has feed_url, source, feed_type, parser, check_interval_minutes."""
        from app.core.feed_registry import CANONICAL_FEEDS

        required_keys = {"feed_url", "source", "feed_type", "parser", "check_interval_minutes"}
        for feed in CANONICAL_FEEDS:
            missing = required_keys - set(feed.keys())
            assert not missing, f"Feed {feed.get('feed_url', '?')} missing keys: {missing}"
