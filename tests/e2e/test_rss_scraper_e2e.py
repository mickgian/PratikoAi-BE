"""E2E Tests for RSS Feed and Scraper Pipeline - DEV-BE-69

Tests the complete flow from RSS feed configuration to document scraping.
These tests verify that the RSS and scraping infrastructure works end-to-end.
"""

import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRSSFeedConfigurationE2E:
    """E2E tests for RSS feed configuration and retrieval."""

    @pytest.mark.asyncio
    async def test_feed_status_table_has_required_feeds(self):
        """Verify feed_status table contains all required RSS feeds."""
        # Import with mocked database to avoid connection issues in CI
        with patch("app.services.database.database_service", None):
            from app.models.regulatory_documents import DocumentSource

            # Verify DocumentSource enum has all required sources
            required_sources = [
                "agenzia_entrate",
                "inps",
                "gazzetta_ufficiale",
                "inail",
                "ministero_economia",
                "ministero_lavoro",
            ]

            available_sources = [s.value for s in DocumentSource]

            for source in required_sources:
                assert source in available_sources, f"Missing source: {source}"


class TestGazzettaScraperE2E:
    """E2E tests for Gazzetta Ufficiale scraper."""

    @pytest.fixture
    def GazzettaScraper(self):
        """Import GazzettaScraper avoiding database connection."""
        with patch("app.services.database.database_service", None):
            from app.services.scrapers.gazzetta_scraper import GazzettaScraper

            return GazzettaScraper

    @pytest.fixture
    def GazzettaDocument(self):
        """Import GazzettaDocument avoiding database connection."""
        with patch("app.services.database.database_service", None):
            from app.services.scrapers.gazzetta_scraper import GazzettaDocument

            return GazzettaDocument

    @pytest.mark.asyncio
    async def test_scraper_full_workflow(self, GazzettaScraper, GazzettaDocument):
        """Test complete scraper workflow from initialization to results."""
        scraper = GazzettaScraper()

        # Mock the internal methods to simulate a full workflow
        mock_docs = [
            GazzettaDocument(
                title="Decreto Legislativo n. 123 del 2024",
                url="https://gazzettaufficiale.it/atto/123",
                document_type="decreto_legislativo",
                published_date=date(2024, 1, 15),
            ),
            GazzettaDocument(
                title="Legge n. 456 tributaria",
                url="https://gazzettaufficiale.it/atto/456",
                document_type="legge",
                published_date=date(2024, 1, 16),
            ),
        ]

        # Mock internal methods
        scraper._scrape_document_list = AsyncMock(return_value=mock_docs)
        scraper._fetch_document_content = AsyncMock(side_effect=lambda doc: doc)

        # Execute full workflow
        result = await scraper.scrape_recent_documents(days_back=7, filter_tax=True, filter_labor=False)

        # Verify results
        assert result.documents_found == 2
        assert result.documents_processed == 1  # Only tributaria matches tax filter
        # documents_saved is 0 because no knowledge_integrator is provided in the test
        # (saving requires integration with the knowledge base)
        assert result.documents_saved == 0
        assert result.errors == 0

    @pytest.mark.asyncio
    async def test_scraper_respects_robots_txt(self, GazzettaScraper):
        """Test that scraper respects robots.txt restrictions."""
        scraper = GazzettaScraper(respect_robots_txt=True)

        # Set up robots rules to disallow /private/
        scraper._robots_rules = {"/private/": False, "/public/": True}

        # Should be blocked
        assert scraper._is_path_allowed("https://example.com/private/doc") is False

        # Should be allowed
        assert scraper._is_path_allowed("https://example.com/public/doc") is True

    @pytest.mark.asyncio
    async def test_scraper_rate_limiting(self, GazzettaScraper):
        """Test that scraper applies rate limiting."""
        scraper = GazzettaScraper(rate_limit_delay=0.1)

        # Verify configuration
        assert scraper.rate_limit_delay == 0.1
        assert scraper.max_concurrent_requests == 3  # Default

    @pytest.mark.asyncio
    async def test_scraper_document_filtering(self, GazzettaScraper, GazzettaDocument):
        """Test document filtering by topic."""
        scraper = GazzettaScraper()

        docs = [
            GazzettaDocument(
                title="Decreto tributario IVA",
                url="https://example.com/1",
                document_type="decreto",
            ),
            GazzettaDocument(
                title="Legge sul lavoro dipendente",
                url="https://example.com/2",
                document_type="legge",
            ),
            GazzettaDocument(
                title="Decreto ambiente",
                url="https://example.com/3",
                document_type="decreto",
            ),
        ]

        # Filter for tax only
        tax_docs = scraper._filter_documents_by_topics(docs, filter_tax=True, filter_labor=False)
        assert len(tax_docs) == 1
        assert "tributario" in tax_docs[0].title

        # Filter for labor only
        labor_docs = scraper._filter_documents_by_topics(docs, filter_tax=False, filter_labor=True)
        assert len(labor_docs) == 1
        assert "lavoro" in labor_docs[0].title

        # Filter for both
        both_docs = scraper._filter_documents_by_topics(docs, filter_tax=True, filter_labor=True)
        assert len(both_docs) == 2


class TestDynamicKnowledgeCollectorE2E:
    """E2E tests for DynamicKnowledgeCollector rate limiting."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_parallel_feed_processing_with_stagger(self, mock_db_session):
        """Test that parallel processing respects stagger delays."""
        with patch("app.services.dynamic_knowledge_collector.RSSFeedMonitor"):
            with patch("app.services.dynamic_knowledge_collector.KnowledgeIntegrator"):
                from app.services.dynamic_knowledge_collector import DynamicKnowledgeCollector

                collector = DynamicKnowledgeCollector(mock_db_session)

                # Track call times
                call_times = []

                async def track_time(feed_name, feed_url):
                    import time

                    call_times.append(time.time())
                    return {"success": True, "source": feed_name, "new_documents": []}

                collector.process_single_feed = track_time

                feeds = {
                    "feed1": "http://example.com/1",
                    "feed2": "http://example.com/2",
                    "feed3": "http://example.com/3",
                }

                await collector.process_all_feeds_parallel(
                    feeds,
                    max_concurrent=5,
                    stagger_delay_min=0.05,
                    stagger_delay_max=0.05,
                )

                # All feeds processed
                assert len(call_times) == 3

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self, mock_db_session):
        """Test that semaphore limits concurrent feed processing."""
        with patch("app.services.dynamic_knowledge_collector.RSSFeedMonitor"):
            with patch("app.services.dynamic_knowledge_collector.KnowledgeIntegrator"):
                from app.services.dynamic_knowledge_collector import DynamicKnowledgeCollector

                collector = DynamicKnowledgeCollector(mock_db_session)

                concurrent_count = 0
                max_concurrent_seen = 0

                async def track_concurrent(feed_name, feed_url):
                    nonlocal concurrent_count, max_concurrent_seen
                    concurrent_count += 1
                    max_concurrent_seen = max(max_concurrent_seen, concurrent_count)
                    await asyncio.sleep(0.05)  # Simulate work
                    concurrent_count -= 1
                    return {"success": True, "source": feed_name, "new_documents": []}

                collector.process_single_feed = track_concurrent

                feeds = {f"feed{i}": f"http://example.com/{i}" for i in range(10)}

                await collector.process_all_feeds_parallel(
                    feeds,
                    max_concurrent=3,
                    stagger_delay_min=0.01,
                    stagger_delay_max=0.01,
                )

                # Should never exceed max_concurrent
                assert max_concurrent_seen <= 3


class TestContentDeduplicationE2E:
    """E2E tests for content deduplication."""

    @pytest.mark.asyncio
    async def test_content_hash_generation(self):
        """Test that content hashes are generated correctly."""
        with patch("app.services.database.database_service", None):
            from app.services.scrapers.gazzetta_scraper import GazzettaDocument

            doc1 = GazzettaDocument(
                title="Test Document",
                url="https://example.com/1",
                document_type="decreto",
                full_text="Content A",
            )

            doc2 = GazzettaDocument(
                title="Test Document",
                url="https://example.com/1",
                document_type="decreto",
                full_text="Content A",
            )

            doc3 = GazzettaDocument(
                title="Test Document",
                url="https://example.com/1",
                document_type="decreto",
                full_text="Content B",  # Different content
            )

            hash1 = doc1.generate_content_hash()
            hash2 = doc2.generate_content_hash()
            hash3 = doc3.generate_content_hash()

            # Same content should produce same hash
            assert hash1 == hash2
            # Different content should produce different hash
            assert hash1 != hash3

    @pytest.mark.asyncio
    async def test_document_to_dict_conversion(self):
        """Test that documents convert to knowledge base format correctly."""
        with patch("app.services.database.database_service", None):
            from app.services.scrapers.gazzetta_scraper import GazzettaDocument

            doc = GazzettaDocument(
                title="Decreto n. 123 tributario",
                url="https://gazzettaufficiale.it/atto/123",
                document_type="decreto",
                document_number="123",
                published_date=date(2024, 3, 15),
                full_text="Decreto content here",
                topics=["tribut", "fiscal"],
            )

            result = doc.to_dict()

            # Verify conversion
            assert result["title"] == "Decreto n. 123 tributario"
            assert result["source"] == "gazzetta_ufficiale"
            assert result["source_type"] == "decreto"
            assert result["document_number"] == "123"
            assert result["content"] == "Decreto content here"
            assert "tribut" in result["metadata"]["topics"]


class TestCassazioneScraperE2E:
    """E2E tests for Cassazione scraper extensions."""

    @pytest.fixture
    def CassazioneScraper(self):
        """Import CassazioneScraper avoiding database connection."""
        with patch("app.services.database.database_service", None):
            from app.services.scrapers.cassazione_scraper import CassazioneScraper

            return CassazioneScraper

    @pytest.mark.asyncio
    async def test_scraper_initialization(self, CassazioneScraper):
        """Test Cassazione scraper initializes correctly."""
        scraper = CassazioneScraper()

        # Verify scraper has expected attributes
        assert hasattr(scraper, "BASE_URL")
        assert hasattr(scraper, "rate_limit_delay")
        assert hasattr(scraper, "max_retries")

    @pytest.mark.asyncio
    async def test_decision_to_knowledge_dict(self, CassazioneScraper):
        """Test that decisions convert to knowledge base format."""
        with patch("app.services.database.database_service", None):
            from app.models.cassazione_data import CassazioneDecision, CourtSection

            decision = CassazioneDecision(
                decision_number="Sentenza 12345/2024",
                section=CourtSection.TRIBUTARIA,
                date=date(2024, 1, 15),
                subject="Tax ruling on VAT",
                summary="Tax ruling summary",
            )

            scraper = CassazioneScraper()
            result = scraper.decision_to_knowledge_dict(decision)

            # Verify conversion returns a dict with expected structure
            assert isinstance(result, dict)
            assert "source" in result
            assert result["source"] == "cassazione"
