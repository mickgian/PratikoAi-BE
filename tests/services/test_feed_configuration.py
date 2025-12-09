"""Test RSS Feed Configuration - DEV-BE-69 Phase 1

TDD tests for verifying feed configuration requirements.

Test Requirements:
- All 13 feeds exist in feed_status (3 Agenzia Entrate + 4 INPS + 1 Ministero Lavoro + 2 MEF + 2 INAIL + 1 Gazzetta)
- Correct parser assigned to each feed
- All feeds are enabled
- Check interval is 240 minutes (4 hours)
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.regulatory_documents import FeedStatus


@pytest.mark.asyncio
class TestRSSFeedConfiguration:
    """Test RSS feed configuration for Phase 1."""

    async def test_total_feed_count(self, db_session: AsyncSession):
        """Test that we have 13 total feeds configured."""
        statement = select(FeedStatus)
        result = await db_session.execute(statement)
        feeds = result.scalars().all()

        assert len(feeds) == 13, (
            f"Expected 13 total feeds, found {len(feeds)}. " f"Feeds: {[f.feed_url for f in feeds]}"
        )

    async def test_inps_feeds_exist(self, db_session: AsyncSession):
        """Test that all 4 INPS feeds are configured."""
        expected_inps_urls = [
            "https://www.inps.it/it/it.rss.news.xml",
            "https://www.inps.it/it/it.rss.circolari.xml",
            "https://www.inps.it/it/it.rss.messaggi.xml",
            "https://www.inps.it/it/it.rss.sentenze.xml",
        ]

        statement = select(FeedStatus).where(FeedStatus.source == "inps")
        result = await db_session.execute(statement)
        inps_feeds = result.scalars().all()
        inps_urls = [feed.feed_url for feed in inps_feeds]

        assert len(inps_feeds) == 4, f"Expected 4 INPS feeds, found {len(inps_feeds)}"

        for url in expected_inps_urls:
            assert url in inps_urls, f"Missing INPS feed: {url}"

    async def test_inps_feeds_use_inps_parser(self, db_session: AsyncSession):
        """Test that all INPS feeds use the 'inps' parser."""
        statement = select(FeedStatus).where(FeedStatus.source == "inps")
        result = await db_session.execute(statement)
        inps_feeds = result.scalars().all()

        for feed in inps_feeds:
            assert feed.parser == "inps", (
                f"INPS feed {feed.feed_url} should use 'inps' parser, " f"found '{feed.parser}'"
            )

    async def test_ministero_lavoro_feed_exists(self, db_session: AsyncSession):
        """Test that Ministero del Lavoro feed is configured."""
        expected_url = "https://www.lavoro.gov.it/_layouts/15/Lavoro.Web/AppPages/RSS"

        statement = select(FeedStatus).where(FeedStatus.feed_url == expected_url)
        result = await db_session.execute(statement)
        feed = result.scalar_one_or_none()

        assert feed is not None, f"Missing Ministero Lavoro feed: {expected_url}"
        assert feed.source == "ministero_lavoro"
        assert feed.feed_type == "news"
        assert feed.parser == "generic"

    async def test_mef_feeds_exist(self, db_session: AsyncSession):
        """Test that both MEF feeds are configured."""
        expected_mef_urls = [
            "https://www.mef.gov.it/rss/rss.asp?t=5",
            "https://www.finanze.gov.it/it/rss.xml",
        ]

        statement = select(FeedStatus).where(FeedStatus.source == "ministero_economia")
        result = await db_session.execute(statement)
        mef_feeds = result.scalars().all()
        mef_urls = [feed.feed_url for feed in mef_feeds]

        assert len(mef_feeds) == 2, f"Expected 2 MEF feeds, found {len(mef_feeds)}"

        for url in expected_mef_urls:
            assert url in mef_urls, f"Missing MEF feed: {url}"

    async def test_mef_feeds_use_generic_parser(self, db_session: AsyncSession):
        """Test that MEF feeds use the 'generic' parser."""
        statement = select(FeedStatus).where(FeedStatus.source == "ministero_economia")
        result = await db_session.execute(statement)
        mef_feeds = result.scalars().all()

        for feed in mef_feeds:
            assert feed.parser == "generic", (
                f"MEF feed {feed.feed_url} should use 'generic' parser, " f"found '{feed.parser}'"
            )

    async def test_inail_feeds_exist(self, db_session: AsyncSession):
        """Test that both INAIL feeds are configured."""
        expected_inail_urls = [
            "https://www.inail.it/portale/it.rss.news.xml",
            "https://www.inail.it/portale/it.rss.eventi.xml",
        ]

        statement = select(FeedStatus).where(FeedStatus.source == "inail")
        result = await db_session.execute(statement)
        inail_feeds = result.scalars().all()
        inail_urls = [feed.feed_url for feed in inail_feeds]

        assert len(inail_feeds) == 2, f"Expected 2 INAIL feeds, found {len(inail_feeds)}"

        for url in expected_inail_urls:
            assert url in inail_urls, f"Missing INAIL feed: {url}"

    async def test_inail_feeds_use_generic_parser(self, db_session: AsyncSession):
        """Test that INAIL feeds use the 'generic' parser."""
        statement = select(FeedStatus).where(FeedStatus.source == "inail")
        result = await db_session.execute(statement)
        inail_feeds = result.scalars().all()

        for feed in inail_feeds:
            assert feed.parser == "generic", (
                f"INAIL feed {feed.feed_url} should use 'generic' parser, " f"found '{feed.parser}'"
            )

    async def test_all_feeds_enabled(self, db_session: AsyncSession):
        """Test that all feeds are enabled."""
        statement = select(FeedStatus)
        result = await db_session.execute(statement)
        feeds = result.scalars().all()

        disabled_feeds = [f for f in feeds if not f.enabled]

        assert len(disabled_feeds) == 0, (
            f"All feeds should be enabled, but found {len(disabled_feeds)} disabled: "
            f"{[f.feed_url for f in disabled_feeds]}"
        )

    async def test_check_interval_240_minutes(self, db_session: AsyncSession):
        """Test that all feeds have check_interval_minutes=240 (4 hours)."""
        statement = select(FeedStatus)
        result = await db_session.execute(statement)
        feeds = result.scalars().all()

        wrong_interval = [f for f in feeds if f.check_interval_minutes != 240]

        assert len(wrong_interval) == 0, (
            f"All feeds should have check_interval_minutes=240, but found: "
            f"{[(f.feed_url, f.check_interval_minutes) for f in wrong_interval]}"
        )

    async def test_feed_source_values(self, db_session: AsyncSession):
        """Test that feed source values are correct."""
        expected_sources = {
            "agenzia_entrate",
            "inps",
            "ministero_lavoro",
            "ministero_economia",
            "inail",
            "gazzetta_ufficiale",
        }

        statement = select(FeedStatus)
        result = await db_session.execute(statement)
        feeds = result.scalars().all()

        actual_sources = {feed.source for feed in feeds}

        # Check that all expected sources are present
        missing_sources = expected_sources - actual_sources
        assert len(missing_sources) == 0, f"Missing expected sources: {missing_sources}"

    async def test_parser_values_valid(self, db_session: AsyncSession):
        """Test that all parser values are valid."""
        valid_parsers = {
            "agenzia_normativa",
            "inps",
            "gazzetta_ufficiale",
            "generic",
        }

        statement = select(FeedStatus)
        result = await db_session.execute(statement)
        feeds = result.scalars().all()

        invalid_parsers = [(f.feed_url, f.parser) for f in feeds if f.parser not in valid_parsers]

        assert len(invalid_parsers) == 0, f"Found feeds with invalid parser values: {invalid_parsers}"

    async def test_no_duplicate_feed_urls(self, db_session: AsyncSession):
        """Test that there are no duplicate feed URLs."""
        statement = select(FeedStatus)
        result = await db_session.execute(statement)
        feeds = result.scalars().all()

        urls = [feed.feed_url for feed in feeds]
        unique_urls = set(urls)

        assert len(urls) == len(
            unique_urls
        ), f"Found duplicate feed URLs. Total: {len(urls)}, Unique: {len(unique_urls)}"

    async def test_feed_type_values_present(self, db_session: AsyncSession):
        """Test that all feeds have feed_type set."""
        statement = select(FeedStatus)
        result = await db_session.execute(statement)
        feeds = result.scalars().all()

        missing_feed_type = [f.feed_url for f in feeds if not f.feed_type]

        assert len(missing_feed_type) == 0, f"Found feeds without feed_type: {missing_feed_type}"

    async def test_agenzia_entrate_feeds_exist(self, db_session: AsyncSession):
        """Test that all 3 Agenzia Entrate feeds are configured."""
        expected_urls = [
            "https://www.agenziaentrate.gov.it/portale/rss/circolari.xml",
            "https://www.agenziaentrate.gov.it/portale/rss/risoluzioni.xml",
            "https://www.agenziaentrate.gov.it/portale/rss/provvedimenti.xml",
        ]

        statement = select(FeedStatus).where(FeedStatus.source == "agenzia_entrate")
        result = await db_session.execute(statement)
        ae_feeds = result.scalars().all()
        ae_urls = [feed.feed_url for feed in ae_feeds]

        assert len(ae_feeds) == 3, f"Expected 3 Agenzia Entrate feeds, found {len(ae_feeds)}"

        for url in expected_urls:
            assert url in ae_urls, f"Missing Agenzia Entrate feed: {url}"

    async def test_agenzia_entrate_uses_agenzia_normativa_parser(self, db_session: AsyncSession):
        """Test that Agenzia Entrate feeds use the 'agenzia_normativa' parser."""
        statement = select(FeedStatus).where(FeedStatus.source == "agenzia_entrate")
        result = await db_session.execute(statement)
        ae_feeds = result.scalars().all()

        for feed in ae_feeds:
            assert feed.parser == "agenzia_normativa", (
                f"Agenzia Entrate feed {feed.feed_url} should use 'agenzia_normativa' parser, "
                f"found '{feed.parser}'"
            )

    async def test_gazzetta_ufficiale_feed_exists(self, db_session: AsyncSession):
        """Test that Gazzetta Ufficiale feed is configured."""
        expected_url = "https://www.gazzettaufficiale.it/rss/serie_generale.xml"

        statement = select(FeedStatus).where(FeedStatus.feed_url == expected_url)
        result = await db_session.execute(statement)
        feed = result.scalar_one_or_none()

        assert feed is not None, f"Missing Gazzetta Ufficiale feed: {expected_url}"
        assert feed.source == "gazzetta_ufficiale"
        assert feed.feed_type == "serie_generale"
        assert feed.parser == "gazzetta_ufficiale"


@pytest.mark.asyncio
class TestSpecificFeedDetails:
    """Test specific feed configurations in detail."""

    async def test_inps_news_feed_details(self, db_session: AsyncSession):
        """Test INPS news feed configuration."""
        statement = select(FeedStatus).where(FeedStatus.feed_url == "https://www.inps.it/it/it.rss.news.xml")
        result = await db_session.execute(statement)
        feed = result.scalar_one_or_none()

        assert feed is not None, "INPS news feed not found"
        assert feed.source == "inps"
        assert feed.feed_type == "news"
        assert feed.parser == "inps"
        assert feed.enabled is True
        assert feed.check_interval_minutes == 240

    async def test_inps_messaggi_feed_details(self, db_session: AsyncSession):
        """Test INPS messaggi feed configuration."""
        statement = select(FeedStatus).where(FeedStatus.feed_url == "https://www.inps.it/it/it.rss.messaggi.xml")
        result = await db_session.execute(statement)
        feed = result.scalar_one_or_none()

        assert feed is not None, "INPS messaggi feed not found"
        assert feed.source == "inps"
        assert feed.feed_type == "messaggi"
        assert feed.parser == "inps"
        assert feed.enabled is True
        assert feed.check_interval_minutes == 240

    async def test_inps_sentenze_feed_details(self, db_session: AsyncSession):
        """Test INPS sentenze feed configuration."""
        statement = select(FeedStatus).where(FeedStatus.feed_url == "https://www.inps.it/it/it.rss.sentenze.xml")
        result = await db_session.execute(statement)
        feed = result.scalar_one_or_none()

        assert feed is not None, "INPS sentenze feed not found"
        assert feed.source == "inps"
        assert feed.feed_type == "sentenze"
        assert feed.parser == "inps"
        assert feed.enabled is True
        assert feed.check_interval_minutes == 240

    async def test_mef_documenti_feed_details(self, db_session: AsyncSession):
        """Test MEF documenti feed configuration."""
        statement = select(FeedStatus).where(FeedStatus.feed_url == "https://www.mef.gov.it/rss/rss.asp?t=5")
        result = await db_session.execute(statement)
        feed = result.scalar_one_or_none()

        assert feed is not None, "MEF documenti feed not found"
        assert feed.source == "ministero_economia"
        assert feed.feed_type == "documenti"
        assert feed.parser == "generic"
        assert feed.enabled is True
        assert feed.check_interval_minutes == 240

    async def test_mef_aggiornamenti_feed_details(self, db_session: AsyncSession):
        """Test MEF aggiornamenti feed configuration."""
        statement = select(FeedStatus).where(FeedStatus.feed_url == "https://www.finanze.gov.it/it/rss.xml")
        result = await db_session.execute(statement)
        feed = result.scalar_one_or_none()

        assert feed is not None, "MEF aggiornamenti feed not found"
        assert feed.source == "ministero_economia"
        assert feed.feed_type == "aggiornamenti"
        assert feed.parser == "generic"
        assert feed.enabled is True
        assert feed.check_interval_minutes == 240

    async def test_inail_notizie_feed_details(self, db_session: AsyncSession):
        """Test INAIL notizie feed configuration."""
        statement = select(FeedStatus).where(FeedStatus.feed_url == "https://www.inail.it/portale/it.rss.news.xml")
        result = await db_session.execute(statement)
        feed = result.scalar_one_or_none()

        assert feed is not None, "INAIL notizie feed not found"
        assert feed.source == "inail"
        assert feed.feed_type == "news"
        assert feed.parser == "generic"
        assert feed.enabled is True
        assert feed.check_interval_minutes == 240

    async def test_inail_eventi_feed_details(self, db_session: AsyncSession):
        """Test INAIL eventi feed configuration."""
        statement = select(FeedStatus).where(FeedStatus.feed_url == "https://www.inail.it/portale/it.rss.eventi.xml")
        result = await db_session.execute(statement)
        feed = result.scalar_one_or_none()

        assert feed is not None, "INAIL eventi feed not found"
        assert feed.source == "inail"
        assert feed.feed_type == "eventi"
        assert feed.parser == "generic"
        assert feed.enabled is True
        assert feed.check_interval_minutes == 240
